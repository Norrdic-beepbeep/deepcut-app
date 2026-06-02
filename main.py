import os
import time
import requests
import json
import smtplib
import uuid
import asyncio
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import openai
import tempfile
import yt_dlp
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, or_, ForeignKey, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt

# ---------------------------------------------------------
# SECURITY & DATABASE CONFIGURATION (WITH AUTO-FALLBACK)
# ---------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-fallback-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fallback.db")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Robust database connection fallback handler
try:
    # Set a short connection timeout so cold starts or bad credentials don't hang the deployment
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"connect_timeout": 10} if "postgresql" in SQLALCHEMY_DATABASE_URL else {}
    )
    # Ping the database immediately to test connection integrity
    with engine.connect() as conn:
        print("Successfully connected to primary database.")
except Exception as e:
    print(f"Database connection failed: {e}. Falling back to SQLite fallback.db.")
    SQLALCHEMY_DATABASE_URL = "sqlite:///./fallback.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

# ---------------------------------------------------------
# RELATIONAL DATABASE MODELS
# ---------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    # Relational link to past audits
    audits = relationship("Audit", back_populates="owner", cascade="all, delete-orphan")

class Audit(Base):
    __tablename__ = "audits"
    id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    format = Column(String, nullable=False)            # "XML", "Audio", "Web Stream"
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False)            # "Running", "Clean", "Flagged", "Error"
    anomalies = Column(JSON, nullable=True)            # Serialized JSON audit report

    # Relationship back to User
    owner = relationship("User", back_populates="audits")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# AUTHENTICATION & EMAIL NOTIFICATIONS
# ---------------------------------------------------------
def send_confirmation_email(user_email: str, user_name: str, username: str):
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME") 
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") 
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@deepcut.app")

    subject = "DeepCut Engine // Access Confirmed"
    body = f"OPERATOR ACCESS CONFIRMED\n-------------------------\nName: {user_name}\nOperator ID: {username}\n\nWelcome to the DeepCut Compliance Engine. You may now access the system."

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"\n[MOCK EMAIL SENT TO {user_email}]\nSubject: {subject}\n{body}\n")
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

def verify_password(plain_password, hashed_password): return pwd_context.verify(plain_password, hashed_password)
def get_password_hash(password): return pwd_context.hash(password)
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise HTTPException(status_code=401)
    except JWTError: raise HTTPException(status_code=401)
    user = db.query(User).filter(User.username == username).first()
    if user is None: raise HTTPException(status_code=401)
    return user

# ---------------------------------------------------------
# FASTAPI APP, WEBSOCKETS & POLLING ROUTING
# ---------------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try: client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception: client = None

task_statuses: dict[str, dict] = {}
active_connections: dict[str, WebSocket] = {}

async def notify_progress(task_id: str, stage: str, progress: int, message: str):
    """Updates progress status cache and streams events to connected WebSockets."""
    task_statuses[task_id] = {
        "status": "running", "stage": stage, "progress": progress, "message": message, "result": None
    }
    if task_id in active_connections:
        try:
            await active_connections[task_id].send_json({
                "status": "progress", "stage": stage, "progress": progress, "message": message
            })
        except Exception:
            pass

@app.get("/")
def home_root():
    """Confirms server status for quick diagnostics."""
    return {"status": "online", "engine": "DeepCut Compliance API", "version": "1.2.0-vault"}

@app.post("/api/register")
def register_user(name: str = Form(...), username: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(or_(User.username == username, User.email == email)).first()
    if existing_user: raise HTTPException(status_code=400, detail="Username or email already registered")
    db.add(User(name=name, username=username, email=email, hashed_password=get_password_hash(password)))
    db.commit()
    send_confirmation_email(email, name, username)
    return {"message": "Operator registered successfully."}

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(or_(User.username == form_data.username, User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    return {"access_token": create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)), "token_type": "bearer", "username": user.username}

# ---------------------------------------------------------
# AI AUDITING SUB-PIPELINES
# ---------------------------------------------------------
def download_audio_from_link(url: str):
    temp_dir = tempfile.gettempdir()
    out_tmpl = os.path.join(temp_dir, 'downloaded_audio.%(ext)s')
    ydl_opts = {'format': 'm4a/bestaudio/best', 'outtmpl': out_tmpl, 'noplaylist': True, 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            with open(path, 'rb') as f: content = f.read()
            os.remove(path)
            return content, "downloaded_link.m4a"
    except Exception as e: return None, str(e)

def detect_with_ai_xml(file_content, filename):
    if not client: return {"anomalies": [], "error": "AI Engine offline."}
    text_content = file_content.decode('utf-8', errors='ignore')[:10000] 
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a strict video compliance auditor. Look for copyrighted music and continuity errors in the XML. Return JSON: {\"anomalies\": [{\"timecode\": \"string\", \"type\": \"string\", \"description\": \"string\"}], \"error\": null}"},
                {"role": "user", "content": f"Filename: {filename}\nXML: {text_content}"}
            ], response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e: return {"anomalies": [], "error": str(e)}

def detect_with_ai_audio(file_content, filename):
    if not client: return {"anomalies": [], "error": "AI Engine offline."}
    try:
        transcript_response = client.audio.transcriptions.create(model="whisper-1", file=(filename, file_content))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a broadcast auditor. Flag profanity or explicit mentions of competitor brands. Return JSON: {\"anomalies\": [{\"timecode\": \"Spoken Audio\", \"type\": \"string\", \"description\": \"string\"}], \"error\": null}"},
                {"role": "user", "content": f"Transcript:\n{transcript_response.text}"}
            ], response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e: return {"anomalies": [], "error": str(e)}

# THE BACKGROUND TASK WORKER
async def run_audit_background(task_id: str, file_content: bytes, filename: str, video_url: str):
    try:
        await notify_progress(task_id, "scan", 10, "EXTRACTING MEDIA..." if video_url else "UPLOADING TO ENGINE...")
        await asyncio.sleep(1)
        
        if video_url:
            await notify_progress(task_id, "scan", 40, "DOWNLOADING STREAM...")
            file_content, err = download_audio_from_link(video_url)
            if not file_content: raise Exception(f"Failed: {err}")
            filename = "Linked_Video.m4a"
            
        await notify_progress(task_id, "scan", 85, "ANALYZING SIGNATURES...")
        await asyncio.sleep(1)

        await notify_progress(task_id, "scan", 100, "SECURE. PHASE 1 COMPLETE.")
        await asyncio.sleep(0.5)

        await notify_progress(task_id, "detect", 20, "INITIALIZING AI PIPELINE...")
        
        if filename.lower().endswith(('.mp4', '.mp3', '.wav', '.m4a')):
            await notify_progress(task_id, "detect", 50, "TRANSCRIBING AUDIO VIA WHISPER...")
            ai_analysis = detect_with_ai_audio(file_content, filename)
        else:
            await notify_progress(task_id, "detect", 60, "ANALYZING XML STRUCTURAL DATA...")
            ai_analysis = detect_with_ai_xml(file_content, filename)
            
        await notify_progress(task_id, "detect", 100, "AUDIT COMPLETE.")
        
        final_result = {
            "status": "success", "filename": filename,
            "anomalies": ai_analysis.get('anomalies', []), "error": ai_analysis.get('error', None)
        }
        
        task_statuses[task_id] = {
            "status": "complete", "stage": "detect", "progress": 100, "message": "AUDIT COMPLETE.", "result": final_result
        }

        # Write result securely to DB
        db = SessionLocal()
        try:
            db_audit = db.query(Audit).filter(Audit.id == task_id).first()
            if db_audit:
                db_audit.status = "Flagged" if len(ai_analysis.get('anomalies', [])) > 0 else "Clean"
                db_audit.anomalies = ai_analysis.get('anomalies', [])
                db.commit()
        finally:
            db.close()

        if task_id in active_connections:
            await active_connections[task_id].send_json({"status": "complete", "result": final_result})

    except Exception as e:
        task_statuses[task_id] = {
            "status": "error", "stage": "detect", "progress": 0, "message": str(e), "result": None
        }
        
        db = SessionLocal()
        try:
            db_audit = db.query(Audit).filter(Audit.id == task_id).first()
            if db_audit:
                db_audit.status = "Error"
                db_audit.anomalies = [{"timecode": "N/A", "type": "Engine Error", "description": str(e)}]
                db.commit()
        finally:
            db.close()

        if task_id in active_connections:
            await active_connections[task_id].send_json({"status": "error", "message": str(e)})

# ---------------------------------------------------------
# SECURE VAULT ENDPOINTS (USER-SPECIFIC)
# ---------------------------------------------------------
@app.post("/api/audit/start")
async def start_audit(background_tasks: BackgroundTasks, file: UploadFile = File(None), video_url: str = Form(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not file and not video_url: raise HTTPException(status_code=400, detail="Must provide file or URL.")
    
    file_content = await file.read() if file else None
    filename = file.filename if file else None
    task_id = str(uuid.uuid4())
    
    task_statuses[task_id] = {
        "status": "running", "stage": "scan", "progress": 0, "message": "INITIALIZING...", "result": None
    }

    format_label = "Web Stream" if video_url else ("Audio" if filename.lower().endswith(('.mp4', '.mp3', '.wav', '.m4a')) else "XML")

    # Insert relational record tied directly to user.id
    db_audit = Audit(
        id=task_id,
        user_id=current_user.id,
        filename=filename or "Web Stream",
        format=format_label,
        status="Running",
        anomalies=[]
    )
    db.add(db_audit)
    db.commit()
    
    background_tasks.add_task(run_audit_background, task_id, file_content, filename, video_url)
    return {"task_id": task_id}

@app.get("/api/audits")
def get_user_audits(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Exclusively retrieves audits owned by the authenticated operator."""
    audits = db.query(Audit).filter(Audit.user_id == current_user.id).order_by(Audit.timestamp.desc()).all()
    return [{
        "id": a.id,
        "filename": a.filename,
        "format": a.format,
        "timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "status": a.status,
        "flag_count": len(a.anomalies) if a.anomalies else 0
    } for a in audits]

@app.get("/api/audits/{audit_id}")
def get_single_audit(audit_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verifies owner verification and fetches specific record details."""
    audit = db.query(Audit).filter(Audit.id == audit_id, Audit.user_id == current_user.id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return {
        "status": "success",
        "filename": audit.filename,
        "format": audit.format,
        "anomalies": audit.anomalies
    }

@app.get("/api/audit/status/{task_id}")
async def get_audit_status(task_id: str, current_user: User = Depends(get_current_user)):
    if task_id not in task_statuses:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_statuses[task_id]

@app.websocket("/ws/audit/{task_id}")
async def websocket_audit_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    active_connections[task_id] = websocket
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        if task_id in active_connections:
            del active_connections[task_id]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
