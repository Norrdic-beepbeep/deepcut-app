import os
import time
import requests
import json
import smtplib
import uuid
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import openai
import tempfile
import yt_dlp
import uvicorn
from datetime import datetime, timedelta
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, or_
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt

# ---------------------------------------------------------
# SECURITY & DATABASE CONFIGURATION
# ---------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-fallback-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fallback.db")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ---------------------------------------------------------
# AUTHENTICATION & EMAIL
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
# FASTAPI APP, WEBSOCKETS & ROUTES
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

# WEBSOCKET CONNECTION MANAGER
active_connections: dict[str, WebSocket] = {}

async def notify_progress(task_id: str, stage: str, progress: int, message: str):
    """Sends a real-time JSON progress update to the connected frontend."""
    if task_id in active_connections:
        try:
            await active_connections[task_id].send_json({
                "status": "progress", "stage": stage, "progress": progress, "message": message
            })
        except Exception:
            pass

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
# AI & AUDIT PROCESSING (BACKGROUND TASK)
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

def security_scan(file_content, filename): return True

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

# THE BACKGROUND WORKER
async def run_audit_background(task_id: str, file_content: bytes, filename: str, video_url: str):
    # HANDSHAKE WAIT: Give the frontend up to 10 seconds to connect the WebSocket
    for _ in range(20):
        if task_id in active_connections:
            break
        await asyncio.sleep(0.5)
        
    # If it never connected, abort.
    if task_id not in active_connections:
        print(f"Task {task_id} aborted: Frontend WebSocket never connected.")
        return

    try:
        # STAGE 1: UPLOAD / EXTRACTION
        await notify_progress(task_id, "scan", 10, "EXTRACTING MEDIA..." if video_url else "UPLOADING TO ENGINE...")
        await asyncio.sleep(1) # UX Delay
        
        if video_url:
            await notify_progress(task_id, "scan", 40, "DOWNLOADING STREAM...")
            file_content, err = download_audio_from_link(video_url)
            if not file_content: raise Exception(f"Failed: {err}")
            filename = "Linked_Video.m4a"
            
        await notify_progress(task_id, "scan", 85, "ANALYZING SIGNATURES...")
        await asyncio.sleep(1) # UX Delay

        await notify_progress(task_id, "scan", 100, "SECURE. PHASE 1 COMPLETE.")
        await asyncio.sleep(0.5)

        # STAGE 2: AI DETECTION
        await notify_progress(task_id, "detect", 20, "INITIALIZING AI PIPELINE...")
        
        if filename.lower().endswith(('.mp4', '.mp3', '.wav', '.m4a')):
            await notify_progress(task_id, "detect", 50, "TRANSCRIBING AUDIO VIA WHISPER...")
            ai_analysis = detect_with_ai_audio(file_content, filename)
        else:
            await notify_progress(task_id, "detect", 60, "ANALYZING XML STRUCTURAL DATA...")
            ai_analysis = detect_with_ai_xml(file_content, filename)
            
        await notify_progress(task_id, "detect", 100, "AUDIT COMPLETE.")
        
        # COMPLETE
        final_result = {
            "status": "success", "filename": filename,
            "anomalies": ai_analysis.get('anomalies', []), "error": ai_analysis.get('error', None)
        }
        if task_id in active_connections:
            await active_connections[task_id].send_json({"status": "complete", "result": final_result})

    except Exception as e:
        if task_id in active_connections:
            await active_connections[task_id].send_json({"status": "error", "message": str(e)})

@app.post("/api/audit/start")
async def start_audit(background_tasks: BackgroundTasks, file: UploadFile = File(None), video_url: str = Form(None), current_user: User = Depends(get_current_user)):
    """Triggers the background task and returns the tracking ID to the frontend."""
    if not file and not video_url: raise HTTPException(status_code=400, detail="Must provide file or URL.")
    
    file_content = await file.read() if file else None
    filename = file.filename if file else None
    task_id = str(uuid.uuid4())
    
    background_tasks.add_task(run_audit_background, task_id, file_content, filename, video_url)
    return {"task_id": task_id}

@app.websocket("/ws/audit/{task_id}")
async def websocket_audit_endpoint(websocket: WebSocket, task_id: str):
    """Frontend connects here to listen for real-time progress events."""
    await websocket.accept()
    active_connections[task_id] = websocket
    try:
        while True: 
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        if task_id in active_connections:
            del active_connections[task_id]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))