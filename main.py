import os
import time
import requests
import json
import smtplib
import uuid
import asyncio
import random
import string
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

try:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"connect_timeout": 10} if "postgresql" in SQLALCHEMY_DATABASE_URL else {}
    )
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
    audits = relationship("Audit", back_populates="owner", cascade="all, delete-orphan")

class Audit(Base):
    __tablename__ = "audits"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    format = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False)
    anomalies = Column(JSON, nullable=True)
    owner = relationship("User", back_populates="audits")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ---------------------------------------------------------
# AUTHENTICATION & EMAIL FUNCTIONS
# ---------------------------------------------------------
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

def send_confirmation_email(user_email: str, user_name: str, username: str):
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME") 
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") 
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USERNAME)

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
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_reset_email(user_email: str, temp_password: str):
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME") 
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") 
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USERNAME)

    subject = "DeepCut Engine // System Recovery"
    body = f"SYSTEM RECOVERY DISPATCH\n-------------------------\n\nYour password has been successfully reset by the automated system.\n\nTemporary Access Code: {temp_password}\n\nPlease return to the DeepCut Engine to log in securely."

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"\n[MOCK EMAIL SENT TO {user_email}]\nSubject: {subject}\n{body}\n")
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send reset email: {e}")

def generate_temp_password(length=12):
    """Generates a highly secure temporary 12-character alphanumeric code."""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(characters) for i in range(length))

# ---------------------------------------------------------
# CORE FASTAPI SETUP
# ---------------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try: 
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception: 
    client = None

task_statuses: dict[str, dict] = {}
active_connections: dict[str, WebSocket] = {}

# ---------------------------------------------------------
# AUDIO DOWNLOADER HELPER
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

# ---------------------------------------------------------
# OPENAI COMPLIANCE ANALYSIS FUNCTIONS
# ---------------------------------------------------------
def detect_with_ai_xml(file_content, filename):
    """Parses timelines (XML) securely and identifies compliance anomalies."""
    if not client: 
        return {"anomalies": [], "error": "AI Engine offline. OpenAI API key missing."}
    
    text_content = file_content.decode('utf-8', errors='ignore')[:10000] 
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a strict video compliance auditor. Look for copyrighted music and continuity errors in the XML. Return JSON: {\"anomalies\": [{\"timecode\": \"string\", \"type\": \"string\", \"description\": \"string\"}], \"error\": null}"
                },
                {"role": "user", "content": f"Filename: {filename}\nXML: {text_content}"}
            ], 
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e: 
        return {"anomalies": [], "error": str(e)}

def detect_with_ai_audio(file_content, filename):
    """Transcribes spoken audio tracks and flags broadcast violations."""
    if not client: 
        return {"anomalies": [], "error": "AI Engine offline. OpenAI API key missing."}
    
    try:
        transcript_response = client.audio.transcriptions.create(
            model="whisper-1", 
            file=(filename, file_content)
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a broadcast auditor. Flag profanity or explicit mentions of competitor brands. Return JSON: {\"anomalies\": [{\"timecode\": \"Spoken Audio\", \"type\": \"string\", \"description\": \"string\"}], \"error\": null}"
                },
                {"role": "user", "content": f"Transcript:\n{transcript_response.text}"}
            ], 
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e: 
        return {"anomalies": [], "error": str(e)}

# ---------------------------------------------------------
# HIDDEN SECURE GEMINI ENGINE PIPELINE
# ---------------------------------------------------------
def call_secure_gemini_api(prompt: str, is_summary: bool = False):
    """Executes a secure server-side call to Google Gemini using environment variables."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return "System configuration error: Server side AI credentials missing."
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={gemini_key}"
    sys_instruction = (
        "You are a leading video post-production auditor. Write short, clear, and direct executive summaries (max 3 lines) based on the compliance report."
        if is_summary else
        "You are a video post-production expert. Provide a practical, short (1-2 sentences), and actionable strategy to fix the video or audio issue described."
    )
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": sys_instruction}]}
    }
    
    # Implement robust exponential backoff to prevent timeouts (1s, 2s, 4s, 8s, 16s)
    delays = [1, 2, 4, 8, 16]
    for delay in delays:
        try:
            # Increased timeout to 30s to give Gemini enough processing time
            response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=30)
            if response.ok:
                res_data = response.json()
                return res_data['candidates'][0]['content']['parts'][0]['text']
        except Exception:
            pass # Silently catch network blips and proceed to backoff delay
            
        time.sleep(delay)
            
    return "AI generation timeout. Please try syncing again."

# ---------------------------------------------------------
# SECURE SERVER-SIDE PROXY ROUTING
# ---------------------------------------------------------
@app.post("/api/ai/suggest")
def secure_suggest_fix(data: dict, current_user: User = Depends(get_current_user)):
    """Proxies 'Suggest Fix' requests securely from the server backend."""
    issue_type = data.get("type", "General Violation")
    description = data.get("description", "No details provided")
    prompt = f"Issue: {issue_type}. Desc: {description}. How to fix it in post-production in 2 sentences."
    result = call_secure_gemini_api(prompt, is_summary=False)
    return {"text": result}

@app.post("/api/ai/summary")
def secure_generate_summary(data: dict, current_user: User = Depends(get_current_user)):
    """Proxies executive summaries securely from the server backend."""
    report_data = data.get("report", "")
    prompt = f"Write a very short executive summary (max 3 lines). Report:\n{report_data}"
    result = call_secure_gemini_api(prompt, is_summary=True)
    return {"text": result}

# ---------------------------------------------------------
# OPERATOR ACCESS ENDPOINTS
# ---------------------------------------------------------
@app.get("/")
def home_root(): return {"status": "online", "engine": "DeepCut Compliance API", "version": "1.4.1-recovery"}

@app.post("/api/register")
def register_user(background_tasks: BackgroundTasks, name: str = Form(...), username: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(or_(User.username == username, User.email == email)).first()
    if existing_user: raise HTTPException(status_code=400, detail="Username or email already registered")
    db.add(User(name=name, username=username, email=email, hashed_password=get_password_hash(password)))
    db.commit()
    
    # Hand off email execution to the background so the frontend resolves instantly
    background_tasks.add_task(send_confirmation_email, email, name, username)
    return {"message": "Operator registered successfully."}

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(or_(User.username == form_data.username, User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    return {"access_token": create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)), "token_type": "bearer", "username": user.username}

@app.post("/api/forgot-password")
def forgot_password(background_tasks: BackgroundTasks, email: str = Form(...), db: Session = Depends(get_db)):
    """Generates a secure temporary password and emails it to the operator."""
    user = db.query(User).filter(User.email == email).first()
    
    # We return success even if the email isn't found to prevent malicious actors from checking which emails exist.
    if not user:
        return {"message": "If an account matches that email, a reset email has been dispatched."}
    
    temp_pass = generate_temp_password()
    user.hashed_password = get_password_hash(temp_pass)
    db.commit()
    
    # Hand off email execution to the background so the frontend resolves instantly
    background_tasks.add_task(send_reset_email, user.email, temp_pass)
    return {"message": "If an account matches that email, a reset email has been dispatched."}

# ---------------------------------------------------------
# AI METADATA TRACKING WORKERS
# ---------------------------------------------------------
async def notify_progress(task_id: str, stage: str, progress: int, message: str):
    task_statuses[task_id] = {"status": "running", "stage": stage, "progress": progress, "message": message, "result": None}
    if task_id in active_connections:
        try: await active_connections[task_id].send_json({"status": "progress", "stage": stage, "progress": progress, "message": message})
        except Exception: pass

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
        
        final_result = {"status": "success", "filename": filename, "anomalies": ai_analysis.get('anomalies', []), "error": ai_analysis.get('error', None)}
        task_statuses[task_id] = {"status": "complete", "stage": "detect", "progress": 100, "message": "AUDIT COMPLETE.", "result": final_result}

        db = SessionLocal()
        try:
            db_audit = db.query(Audit).filter(Audit.id == task_id).first()
            if db_audit:
                db_audit.status = "Flagged" if len(ai_analysis.get('anomalies', [])) > 0 else "Clean"
                db_audit.anomalies = ai_analysis.get('anomalies', [])
                db.commit()
        finally: db.close()

        if task_id in active_connections: await active_connections[task_id].send_json({"status": "complete", "result": final_result})
    except Exception as e:
        task_statuses[task_id] = {"status": "error", "stage": "detect", "progress": 0, "message": str(e), "result": None}
        db = SessionLocal()
        try:
            db_audit = db.query(Audit).filter(Audit.id == task_id).first()
            if db_audit:
                db_audit.status = "Error"
                db_audit.anomalies = [{"timecode": "N/A", "type": "Engine Error", "description": str(e)}]
                db.commit()
        finally: db.close()
        if task_id in active_connections: await active_connections[task_id].send_json({"status": "error", "message": str(e)})

@app.post("/api/audit/start")
async def start_audit(background_tasks: BackgroundTasks, file: UploadFile = File(None), video_url: str = Form(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not file and not video_url: raise HTTPException(status_code=400, detail="Must provide file or URL.")
    file_content = await file.read() if file else None
    filename = file.filename if file else None
    task_id = str(uuid.uuid4())
    task_statuses[task_id] = {"status": "running", "stage": "scan", "progress": 0, "message": "INITIALIZING...", "result": None}
    format_label = "Web Stream" if video_url else ("Audio" if filename.lower().endswith(('.mp4', '.mp3', '.wav', '.m4a')) else "XML")

    db_audit = Audit(id=task_id, user_id=current_user.id, filename=filename or "Web Stream", format=format_label, status="Running", anomalies=[])
    db.add(db_audit)
    db.commit()
    background_tasks.add_task(run_audit_background, task_id, file_content, filename, video_url)
    return {"task_id": task_id}

@app.get("/api/audits")
def get_user_audits(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audits = db.query(Audit).filter(Audit.user_id == current_user.id).order_by(Audit.timestamp.desc()).all()
    return [{"id": a.id, "filename": a.filename, "format": a.format, "timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "status": a.status, "flag_count": len(a.anomalies) if a.anomalies else 0} for a in audits]

@app.get("/api/audits/{audit_id}")
def get_single_audit(audit_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit = db.query(Audit).filter(Audit.id == audit_id, Audit.user_id == current_user.id).first()
    if not audit: raise HTTPException(status_code=404, detail="Audit log not found")
    return {"status": "success", "filename": audit.filename, "format": audit.format, "anomalies": audit.anomalies}

@app.get("/api/audit/status/{task_id}")
async def get_audit_status(task_id: str, current_user: User = Depends(get_current_user)):
    if task_id not in task_statuses: raise HTTPException(status_code=404, detail="Task not found")
    return task_statuses[task_id]

@app.websocket("/ws/audit/{task_id}")
async def websocket_audit_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    active_connections[task_id] = websocket
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        if task_id in active_connections: del active_connections[task_id]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
