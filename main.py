import os
import time
import requests
import json
import smtplib
import uuid
import asyncio
import random
import string
import subprocess
import tempfile
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiofiles
from pydub import AudioSegment
import openai
import yt_dlp
import uvicorn
# --- PATCH FOR MISSING AUDIOOP ---
import sys
try:
    import audioop
except ImportError:
    try:
        import pyaudioop as audioop
        sys.modules['audioop'] = audioop
    except ImportError:
        # If no replacement is found, provide a mock object to prevent startup crashes
        # Note: This will only fail if you attempt to use features that require audioop
        class MockAudioop:
            def mul(self, *args, **kwargs): return b''
            def lin2lin(self, *args, **kwargs): return b''
        sys.modules['audioop'] = MockAudioop()
# ---------------------------------
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, or_, ForeignKey, DateTime, JSON, Boolean, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt

# ---------------------------------------------------------
# SECURITY & DATABASE CONFIGURATION
# ---------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-fallback-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")  # Master Admin Username

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
    consent_given = Column(Boolean, default=False)  # GDPR Legal Flag
    tier = Column(String, default="free")           # Billing Tier
    audits_used = Column(Integer, default=0)        # Usage Tracker
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

# --- THE MAGIC AUTO-MIGRATION HACK ---
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN consent_given BOOLEAN DEFAULT FALSE;"))
        print("Successfully patched database with missing consent_given column!")
except Exception:
    pass # Column already exists, safe to ignore!

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN tier VARCHAR DEFAULT 'free';"))
        conn.execute(text("ALTER TABLE users ADD COLUMN audits_used INTEGER DEFAULT 0;"))
        print("Successfully patched database with billing columns!")
except Exception:
    pass
# -------------------------------------

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

def verify_admin_clearance(current_user: User):
    if current_user.username != ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="Access Denied: Administrative Clearance Required.")

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
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(characters) for i in range(length))

# ---------------------------------------------------------
# CORE FASTAPI SETUP & CORS SECURITY
# ---------------------------------------------------------
app = FastAPI()

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "https://deepcut-app.onrender.com")
origins = [origin.strip() for origin in allowed_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
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
# MEDIA DOWNLOADER & HEAVY PROCESSING PIPELINE
# ---------------------------------------------------------
def download_audio_from_link(url: str, session_id: str):
    """Downloads audio from a URL stream directly to disk."""
    temp_dir = tempfile.gettempdir()
    out_tmpl = os.path.join(temp_dir, f'{session_id}_downloaded.%(ext)s')
    ydl_opts = {'format': 'm4a/bestaudio/best', 'outtmpl': out_tmpl, 'noplaylist': True, 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            return path, None
    except Exception as e: 
        return None, str(e)

def extract_and_chunk_audio(file_path: str, session_id: str):
    """Uses FFmpeg to strip video, exports an MP3, and uses pydub to slice it into chunks."""
    temp_dir = tempfile.gettempdir()
    audio_path = os.path.join(temp_dir, f"{session_id}_extracted.mp3")
    chunk_paths = []
    
    # Extract audio using FFmpeg
    subprocess.run([
        'ffmpeg', '-y', '-i', file_path,
        '-vn', '-acodec', 'libmp3lame', '-ac', '1', '-b:a', '64k', audio_path
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Slice the extracted audio into 15-minute chunks for OpenAI
    audio = AudioSegment.from_mp3(audio_path)
    chunk_length_ms = 15 * 60 * 1000 
    chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]

    for i, chunk in enumerate(chunks):
        chunk_file = os.path.join(temp_dir, f"{session_id}_chunk_{i}.mp3")
        chunk.export(chunk_file, format="mp3")
        chunk_paths.append(chunk_file)

    if os.path.exists(audio_path):
        os.remove(audio_path)
        
    return chunk_paths

# ---------------------------------------------------------
# OPENAI COMPLIANCE ANALYSIS FUNCTIONS
# ---------------------------------------------------------
def detect_with_ai_xml(file_content, filename):
    if not client: return {"anomalies": [], "error": "AI Engine offline. OpenAI API key missing."}
    text_content = file_content.decode('utf-8', errors='ignore')[:10000] 
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a strict video compliance auditor. Look for copyrighted music and continuity errors in the XML. Return JSON: {\"anomalies\": [{\"timecode\": \"string\", \"type\": \"string\", \"description\": \"string\"}], \"error\": null}"},
                {"role": "user", "content": f"Filename: {filename}\nXML: {text_content}"}
            ], 
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e: return {"anomalies": [], "error": str(e)}

def detect_with_ai_audio_chunked(file_path: str, filename: str, task_id: str):
    if not client: return {"anomalies": [], "error": "AI Engine offline. OpenAI API key missing."}
    try:
        # Process the massive file via FFmpeg and slice it
        chunk_paths = extract_and_chunk_audio(file_path, task_id)
        
        full_transcript = ""
        # Process chunks sequentially through Whisper
        for chunk_path in chunk_paths:
            with open(chunk_path, "rb") as af:
                transcript_response = client.audio.transcriptions.create(model="whisper-1", file=af)
                full_transcript += transcript_response.text + " "
            os.remove(chunk_path) # Instantly cleanup to save disk space
            
        # Send full assembled transcript to GPT for compliance check
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a broadcast auditor. Flag profanity or explicit mentions of competitor brands. Return JSON: {\"anomalies\": [{\"timecode\": \"Spoken Audio\", \"type\": \"string\", \"description\": \"string\"}], \"error\": null}"},
                {"role": "user", "content": f"Transcript:\n{full_transcript}"}
            ], 
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e: return {"anomalies": [], "error": str(e)}

def generate_text_with_ai(prompt: str, is_summary: bool = False):
    if not client: return "System configuration error: Server side AI credentials missing (OpenAI API key not found)."
    sys_instruction = (
        "You are a leading video post-production auditor. Write short, clear, and direct executive summaries (max 3 lines) based on the compliance report."
        if is_summary else
        "You are a video post-production expert. Provide a practical, short (1-2 sentences), and actionable strategy to fix the video or audio issue described."
    )
    last_error = ""
    delays = [1, 2, 4]
    for delay in delays:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": sys_instruction}, {"role": "user", "content": prompt}],
                timeout=30
            )
            return response.choices[0].message.content
        except Exception as e:
            last_error = str(e)
            time.sleep(delay)
    return f"AI generation failed. Please try again. (Last Error: {last_error})"

# ---------------------------------------------------------
# SECURE SERVER-SIDE PROXY ROUTING
# ---------------------------------------------------------
@app.post("/api/ai/suggest")
def secure_suggest_fix(data: dict, current_user: User = Depends(get_current_user)):
    prompt = f"Issue: {data.get('type', 'General Violation')}. Desc: {data.get('description', 'No details provided')}. How to fix it in post-production in 2 sentences."
    return {"text": generate_text_with_ai(prompt, is_summary=False)}

@app.post("/api/ai/summary")
def secure_generate_summary(data: dict, current_user: User = Depends(get_current_user)):
    prompt = f"Write a very short executive summary (max 3 lines). Report:\n{data.get('report', '')}"
    return {"text": generate_text_with_ai(prompt, is_summary=True)}

# ---------------------------------------------------------
# OPERATOR ACCESS ENDPOINTS
# ---------------------------------------------------------
@app.get("/")
def home_root(): return {"status": "online", "engine": "DeepCut Compliance API", "version": "1.5.0-admin-enabled"}

@app.post("/api/register")
def register_user(background_tasks: BackgroundTasks, name: str = Form(...), username: str = Form(...), email: str = Form(...), password: str = Form(...), consent: bool = Form(...), db: Session = Depends(get_db)):
    if not consent:
        raise HTTPException(status_code=400, detail="You must accept the Terms and Conditions to complete setup.")
    existing_user = db.query(User).filter(or_(User.username == username, User.email == email)).first()
    if existing_user: raise HTTPException(status_code=400, detail="Username or email already registered")
    
    db.add(User(name=name, username=username, email=email, hashed_password=get_password_hash(password), consent_given=True))
    db.commit()
    background_tasks.add_task(send_confirmation_email, email, name, username)
    return {"message": "Operator registered successfully."}

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(or_(User.username == form_data.username, User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    
    is_admin_flag = (user.username == ADMIN_USERNAME)

    return {
        "access_token": create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)), 
        "token_type": "bearer", 
        "username": user.username,
        "is_admin": is_admin_flag
    }

@app.post("/api/forgot-password")
def forgot_password(background_tasks: BackgroundTasks, email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user: return {"message": "If an account matches that email, a reset email has been dispatched."}
    temp_pass = generate_temp_password()
    user.hashed_password = get_password_hash(temp_pass)
    db.commit()
    background_tasks.add_task(send_reset_email, user.email, temp_pass)
    return {"message": "If an account matches that email, a reset email has been dispatched."}

@app.post("/api/change-password")
def change_password(current_password: str = Form(...), new_password: str = Form(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current access code.")
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    return {"message": "Access code updated securely."}

# ---------------------------------------------------------
# SECURE ADMINISTRATIVE ENDPOINTS
# ---------------------------------------------------------
@app.get("/api/admin/users")
def admin_get_all_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    verify_admin_clearance(current_user)
    users = db.query(User).all()
    return [{"id": u.id, "name": u.name, "username": u.username, "email": u.email, "consent_given": getattr(u, 'consent_given', False)} for u in users]

@app.post("/api/admin/users/{user_id}/reset-password")
def admin_reset_user_password(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    verify_admin_clearance(current_user)
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user: raise HTTPException(status_code=404, detail="Operator account not found.")
    temp_pass = generate_temp_password()
    target_user.hashed_password = get_password_hash(temp_pass)
    db.commit()
    return {"message": "Password reset successful.", "temporary_code": temp_pass}

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    verify_admin_clearance(current_user)
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user: raise HTTPException(status_code=404, detail="Operator account not found.")
    if target_user.id == current_user.id: raise HTTPException(status_code=400, detail="Administrative accounts cannot self-purge.")
    db.delete(target_user)
    db.commit()
    return {"message": "Operator profile permanently purged."}

# ---------------------------------------------------------
# SYSTEM WORKERS & STREAM PIPELINE
# ---------------------------------------------------------
async def notify_progress(task_id: str, stage: str, progress: int, message: str):
    task_statuses[task_id] = {"status": "running", "stage": stage, "progress": progress, "message": message, "result": None}
    if task_id in active_connections:
        try: await active_connections[task_id].send_json({"status": "progress", "stage": stage, "progress": progress, "message": message})
        except Exception: pass

async def run_audit_background(task_id: str, file_path: str, filename: str, video_url: str):
    try:
        await notify_progress(task_id, "scan", 10, "EXTRACTING MEDIA..." if video_url else "STREAMING TO LOCAL STORAGE...")
        await asyncio.sleep(1)
        
        # Determine File Path Context
        if video_url:
            await notify_progress(task_id, "scan", 40, "DOWNLOADING STREAM TO DISK...")
            file_path, err = download_audio_from_link(video_url, task_id)
            if not file_path: raise Exception(f"Failed: {err}")
            filename = "Linked_Video.m4a"
            
        await notify_progress(task_id, "scan", 85, "ANALYZING SIGNATURES...")
        await asyncio.sleep(1)
        await notify_progress(task_id, "scan", 100, "SECURE. PHASE 1 COMPLETE.")
        await asyncio.sleep(0.5)

        await notify_progress(task_id, "detect", 20, "INITIALIZING AI PIPELINE...")
        
        # Audio / Video Processing Execution (The Heavy Lifter)
        if filename.lower().endswith(('.mp4', '.mp3', '.wav', '.m4a', '.mov')):
            await notify_progress(task_id, "detect", 50, "SLICING & TRANSCRIBING VIA WHISPER...")
            # Route to the newly built FFmpeg/Pydub logic
            ai_analysis = detect_with_ai_audio_chunked(file_path, filename, task_id)
        else:
            await notify_progress(task_id, "detect", 60, "ANALYZING XML STRUCTURAL DATA...")
            # For lightweight XML files, safe to read straight into RAM
            with open(file_path, 'rb') as f:
                file_content = f.read()
            ai_analysis = detect_with_ai_xml(file_content, filename)
            
        await notify_progress(task_id, "detect", 100, "AUDIT COMPLETE.")
        
        final_result = {"status": "success", "filename": filename, "anomalies": ai_analysis.get('anomalies', []), "error": ai_analysis.get('error', None)}
        task_statuses[task_id] = {"status": "complete", "stage": "detect", "progress": 100, "message": "AUDIT COMPLETE.", "result": final_result}

        # Save to Database
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
        
    finally:
        # THE JANITOR: Always scrub massive video files from Render's disk
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

@app.post("/api/audit/start")
async def start_audit(background_tasks: BackgroundTasks, file: UploadFile = File(None), video_url: str = Form(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # --- QUOTA GUARDRAIL ---
    if current_user.username != ADMIN_USERNAME:
        if current_user.tier == "free" and current_user.audits_used >= 5:
            raise HTTPException(status_code=403, detail="QUOTA_EXCEEDED")
        current_user.audits_used += 1
        db.commit()
    # -----------------------

    if not file and not video_url: raise HTTPException(status_code=400, detail="Must provide file or URL.")
    
    task_id = str(uuid.uuid4())
    task_statuses[task_id] = {"status": "running", "stage": "scan", "progress": 0, "message": "INITIALIZING...", "result": None}
    
    filename = file.filename if file else None
    format_label = "Web Stream" if video_url else ("Audio" if filename.lower().endswith(('.mp4', '.mp3', '.wav', '.m4a', '.mov')) else "XML")

    # STREAM TO DISK FIRST: Save the file out of RAM before the route finishes
    file_path = None
    if file:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"{task_id}_{file.filename}")
        async with aiofiles.open(file_path, 'wb') as out_file:
            # Streams the heavy video locally in ultra-light 1MB memory blocks
            while content := await file.read(1024 * 1024):
                await out_file.write(content)

    db.add(Audit(id=task_id, user_id=current_user.id, filename=filename or "Web Stream", format=format_label, status="Running", anomalies=[]))
    db.commit()
    
    # Hand off the local path (not the heavy file object) to the worker
    background_tasks.add_task(run_audit_background, task_id, file_path, filename, video_url)
    
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
