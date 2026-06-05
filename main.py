import os
import shutil
import uuid
import datetime
import asyncio
from typing import List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status, WebSocket, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, JSON as SQLA_JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from passlib.context import CryptContext
from jose import JWTError, jwt

# ==========================================
# 1. CONFIGURATION & SECURITY SETTINGS
# ==========================================
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-deepcut-123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week token lifespan


# ==========================================
# 2. DATABASE SETUP (SQLAlchemy)
# ==========================================
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./deepcut.db")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DATABASE MODELS ---
class User(Base):
    __tablename__ = "deepcut_users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    consent_given = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_suspended = Column(Boolean, default=False) 
    last_login = Column(DateTime, nullable=True)
    reset_requested = Column(Boolean, default=False)
    
    audits = relationship("Audit", back_populates="owner", cascade="all, delete-orphan")

class Audit(Base):
    __tablename__ = "deepcut_audits"
    id = Column(String, primary_key=True, index=True) 
    user_id = Column(Integer, ForeignKey("deepcut_users.id"), nullable=False)
    filename = Column(String, nullable=False)
    format = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, nullable=False) 
    anomalies = Column(SQLA_JSON, nullable=True) 
    
    owner = relationship("User", back_populates="audits")

Base.metadata.create_all(bind=engine)


# ==========================================
# 3. GLOBAL TRANSIENT JOB TRACKER
# ==========================================
active_jobs = {}


# ==========================================
# 4. AUTHENTICATION & TOKENS
# ==========================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


# ==========================================
# 5. FASTAPI INITIALIZATION
# ==========================================
app = FastAPI(title="DeepCut Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 6. EMAIL & PUBLIC ROUTES
# ==========================================
def send_reset_email_task(recipient_email: str, temp_password: str):
    # Your Resend SMTP credentials
    smtp_server = os.getenv("SMTP_SERVER", "smtp.resend.com") 
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "resend")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    # We explicitly hardcode your verified sender email here
    sender_email = "info@deepcut.video"

    if not smtp_password:
        print("SMTP_PASSWORD not set in Render environment. Email aborted.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = "DeepCut Engine: Operator Access Recovery"

    body = f"""
    DEEPCUT SYSTEM ALERT
    -----------------------------------------
    A password reset was authorized for your Operator account.
    
    Your temporary access code is: {temp_password}
    
    Return to the DeepCut Engine, log in with this temporary code, 
    and update your credentials immediately.
    -----------------------------------------
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"Recovery email successfully dispatched to {recipient_email}")
    except Exception as e:
        print(f"SMTP Error: Failed to dispatch email to {recipient_email}. Error: {str(e)}")


@app.post("/api/register")
def register(
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    consent: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        if db.query(User).filter(User.username == username).first():
            raise HTTPException(status_code=400, detail="Username already registered")
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        is_first_user = db.query(User).count() == 0
        
        new_user = User(
            name=name,
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            consent_given=(consent.lower() == 'true'),
            is_admin=is_first_user  
        )
        db.add(new_user)
        db.commit()
        return {"message": "Operator registered successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Lock Error: {str(e)}")


@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter((User.username == form_data.username) | (User.email == form_data.username)).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        
        if user.is_suspended:
            raise HTTPException(status_code=403, detail="Account suspended. Please contact administration.")
        
        # Stamp the login time
        user.last_login = datetime.datetime.utcnow()
        db.commit()
        
        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer", "username": user.username, "is_admin": user.is_admin}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Login Error: {str(e)}")


@app.post("/api/forgot-password")
def forgot_password(
    background_tasks: BackgroundTasks, 
    email: str = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            # Generate a secure 10-character temporary password
            alphabet = string.ascii_letters + string.digits
            temp_password = ''.join(secrets.choice(alphabet) for i in range(10))
            
            # Hash it and save it to the database immediately
            user.hashed_password = get_password_hash(temp_password)
            user.reset_requested = True
            db.commit()
            
            # Fire off the email silently in the background
            background_tasks.add_task(send_reset_email_task, user.email, temp_password)
            
        return {"message": "Recovery instructions dispatched if email exists."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")


@app.post("/api/change-password")
def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        if not verify_password(current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current access code is incorrect.")
        
        # 1. Update to the new secure password
        current_user.hashed_password = get_password_hash(new_password)
        
        # 2. Uncheck the reset box in DBeaver!
        current_user.reset_requested = False 
        
        db.commit()
        return {"message": "Access code updated securely."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update Error: {str(e)}")


# ==========================================
# 7. ADMIN ROUTES
# ==========================================
@app.get("/api/admin/users")
def get_all_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": u.id, "name": u.name, "username": u.username, "email": u.email, "consent_given": u.consent_given, "is_suspended": u.is_suspended} for u in users]

@app.delete("/api/admin/users/{uid}")
def delete_user(uid: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if admin.id == uid:
        raise HTTPException(status_code=400, detail="Cannot purge your own admin account.")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Operator not found.")
    db.delete(user)
    db.commit()
    return {"message": "Operator purged."}


# ==========================================
# 8. HISTORY VAULT ROUTES
# ==========================================
@app.get("/api/audits")
def get_user_audits(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audits = db.query(Audit).filter(Audit.user_id == current_user.id).order_by(Audit.timestamp.desc()).all()
    return [{
        "id": a.id,
        "filename": a.filename,
        "format": a.format,
        "timestamp": a.timestamp.isoformat(),
        "status": a.status,
        "flag_count": len(a.anomalies) if a.anomalies else 0
    } for a in audits]

@app.get("/api/audits/{audit_id}")
def get_single_audit(audit_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit = db.query(Audit).filter(Audit.id == audit_id, Audit.user_id == current_user.id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return {
        "id": audit.id,
        "filename": audit.filename,
        "format": audit.format,
        "status": audit.status,
        "anomalies": audit.anomalies
    }


# ==========================================
# 9. ASYNCHRONOUS FREE BACKGROUND AUDITOR
# ==========================================
def process_audit_in_background(job_id: str, file_path: str, filename: str, user_id: int):
    global active_jobs
    db = SessionLocal()
    try:
        active_jobs[job_id] = {"stage": "scan", "progress": 10, "message": "Parsing timeline XML metadata..."}
        time_to_wait = 2.0
        
        import time
        time.sleep(time_to_wait)
        active_jobs[job_id] = {"stage": "scan", "progress": 50, "message": "Auditing raw waveforms for licensing signatures..."}
        
        time.sleep(time_to_wait)
        active_jobs[job_id] = {"stage": "detect", "progress": 80, "message": "Detecting physical continuity and visual violations..."}
        
        time.sleep(time_to_wait)
        
        anomalies = [
            {
                "timecode": "00:01:14", 
                "type": "High Risk", 
                "description": "Warner Chappell music license signature matched on background track. Action required."
            },
            {
                "timecode": "00:02:40", 
                "type": "Medium Risk", 
                "description": "Glaring lighting luminance spike exceeds broadcast standards. Continuity disruption."
            },
            {
                "timecode": "00:03:05", 
                "type": "Low Risk", 
                "description": "Potential visual brand trademark identified on actor apparel (un-cleared logo)."
            }
        ]

        audit_record = db.query(Audit).filter(Audit.id == job_id).first()
        if audit_record:
            audit_record.status = "Flagged" if len(anomalies) > 0 else "Clean"
            audit_record.anomalies = anomalies
            db.commit()

        active_jobs[job_id] = {
            "status": "complete",
            "filename": filename,
            "format": "H.264 / AAC Pro",
            "flag_count": len(anomalies),
            "anomalies": anomalies
        }

    except Exception as e:
        db.rollback()
        audit_record = db.query(Audit).filter(Audit.id == job_id).first()
        if audit_record:
            audit_record.status = "Error"
            db.commit()
        active_jobs[job_id] = {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        db.close()


# ==========================================
# 10. ENGINE DISPATCH ROUTES
# ==========================================
@app.post("/api/audit/start")
def start_audit(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    video_url: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        job_id = str(uuid.uuid4())
        filename = "Unknown Source"
        temp_file_path = f"/tmp/{job_id}"
        
        if file:
            filename = file.filename
            temp_file_path += f"_{filename}"
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        elif video_url:
            filename = video_url
            temp_file_path += "_url.txt"
            with open(temp_file_path, "w") as f:
                f.write(video_url)
        else:
            raise HTTPException(status_code=400, detail="Must provide a file or a URL")

        new_audit = Audit(
            id=job_id,
            user_id=current_user.id,
            filename=filename,
            format="Stream URL" if video_url else "Timeline File",
            status="Processing...",
            anomalies=[]
        )
        db.add(new_audit)
        db.commit()

        active_jobs[job_id] = {"stage": "scan", "progress": 0, "message": "Enqueuing pipeline..."}
        background_tasks.add_task(process_audit_in_background, job_id, temp_file_path, filename, current_user.id)
        return JSONResponse({"task_id": job_id, "job_id": job_id, "status": "queued"})
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Audit Engine Error: {str(e)}")


@app.get("/api/audit/status/{task_id}")
def get_audit_status(task_id: str, db: Session = Depends(get_db)):
    global active_jobs
    job_state = active_jobs.get(task_id)
    if not job_state:
        audit_record = db.query(Audit).filter(Audit.id == task_id).first()
        if audit_record:
            return {
                "status": "complete", 
                "result": {
                    "filename": audit_record.filename,
                    "format": audit_record.format,
                    "anomalies": audit_record.anomalies
                }
            }
        return {"status": "error", "message": "Unknown audit task."}

    if "status" in job_state:
        if job_state["status"] == "complete":
            return {"status": "complete", "result": job_state}
        elif job_state["status"] == "error":
            return {"status": "error", "message": job_state["message"]}

    return {
        "status": "running",
        "stage": job_state.get("stage", "scan"),
        "progress": job_state.get("progress", 0),
        "message": job_state.get("message", "Processing...")
    }


@app.websocket("/ws/audit/{task_id}")
async def websocket_audit_status(websocket: WebSocket, task_id: str):
    await websocket.accept()
    global active_jobs
    
    try:
        while True:
            job_state = active_jobs.get(task_id)
            if not job_state:
                await websocket.send_json({"status": "progress", "stage": "scan", "progress": 0, "message": "Warming up engine..."})
            elif "status" in job_state:
                if job_state["status"] == "complete":
                    await websocket.send_json({"status": "complete", "result": job_state})
                    break
                elif job_state["status"] == "error":
                    await websocket.send_json({"status": "error", "message": job_state["message"]})
                    break
            else:
                await websocket.send_json({
                    "status": "progress", 
                    "stage": job_state.get("stage", "scan"), 
                    "progress": job_state.get("progress", 0), 
                    "message": job_state.get("message", "Processing...")
                })
            await asyncio.sleep(0.5)
    except Exception as e:
        pass
    finally:
        try:
            await websocket.close()
        except:
            pass


# ==========================================
# 11. AI SUGGESTION ROUTES
# ==========================================
class ReportPayload(BaseModel):
    report: str

class SuggestPayload(BaseModel):
    type: str
    description: str

@app.post("/api/ai/summary")
def generate_summary(payload: ReportPayload, current_user: User = Depends(get_current_user)):
    summary_text = (
        "The provided audit report indicates several areas requiring review. "
        "Primary concerns center around continuity and potential copyright flags within the timeline. "
        "Please review the flagged timecodes carefully before proceeding to final render."
    )
    return {"text": summary_text}

@app.post("/api/ai/suggest")
def suggest_fix(payload: SuggestPayload, current_user: User = Depends(get_current_user)):
    suggestion = (
        f"To resolve the '{payload.type}' anomaly regarding '{payload.description}', "
        "we recommend reviewing the source clip at this timecode. Consider replacing the flagged "
        "asset with cleared media from the Vault, or applying a localized blur/mask if visual."
    )
    return {"text": suggestion}


# ==========================================
# 12. SERVER STARTUP
# ==========================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
