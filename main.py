import os
import shutil
import uuid
import datetime
import asyncio
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, JSON as SQLA_JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from passlib.context import CryptContext
from jose import JWTError, jwt

# --- CELERY BACKGROUND WORKER IMPORT ---
# This attempts to load the worker file. If you haven't created it yet, 
# it gracefully fails without crashing the main web server.
try:
    from worker import celery_app, process_video_audit
    CELERY_ENABLED = True
except ImportError:
    CELERY_ENABLED = False


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
# Render uses 'postgres://' but SQLAlchemy requires 'postgresql://'
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    # check_same_thread is only needed for local SQLite, not production Postgres
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Database Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    consent_given = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    
    # Relationship to the Audit History Vault
    audits = relationship("Audit", back_populates="owner", cascade="all, delete-orphan")

class Audit(Base):
    __tablename__ = "audits"
    id = Column(String, primary_key=True, index=True) # Unique Job ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    format = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, nullable=False) # "Processing", "Clean", "Flagged", "Error"
    anomalies = Column(SQLA_JSON, nullable=True) # Stores the AI JSON results
    
    owner = relationship("User", back_populates="audits")

# Build the tables if they don't exist
Base.metadata.create_all(bind=engine)


# ==========================================
# 3. AUTHENTICATION & TOKENS
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

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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

async def get_current_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


# ==========================================
# 4. FASTAPI INITIALIZATION
# ==========================================
app = FastAPI(title="DeepCut Engine API")

# Setup CORS so your Vercel frontend can talk to your Render backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, change this to ["https://deepcut.video", "https://www.deepcut.video"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 5. PUBLIC ROUTES (Login & Registration)
# ==========================================
@app.post("/api/register")
async def register(
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    consent: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # The very first user to register automatically gets Admin rights
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

@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter((User.username == form_data.username) | (User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer", "username": user.username, "is_admin": user.is_admin}

@app.post("/api/forgot-password")
async def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    # To prevent enumeration attacks, always return success even if email isn't found
    return {"message": "Recovery instructions dispatched if email exists."}

@app.post("/api/change-password")
async def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current access code is incorrect.")
    
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    return {"message": "Access code updated securely."}


# ==========================================
# 6. ADMIN ROUTES
# ==========================================
@app.get("/api/admin/users")
def get_all_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": u.id, "name": u.name, "username": u.username, "email": u.email, "consent_given": u.consent_given} for u in users]

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

@app.post("/api/admin/users/{uid}/reset-password")
def reset_user_password(uid: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Operator not found.")
    temp_pass = f"DeepCut-{uuid.uuid4().hex[:6]}"
    user.hashed_password = get_password_hash(temp_pass)
    db.commit()
    return {"temporary_code": temp_pass}


# ==========================================
# 7. HISTORY VAULT ROUTES
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
# 8. ENGINE DISPATCH ROUTES
# ==========================================
@app.post("/api/audit/start")
async def start_audit(
    file: Optional[UploadFile] = File(None),
    video_url: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not CELERY_ENABLED:
        raise HTTPException(status_code=500, detail="Background worker offline.")
        
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

    # 1. Create a pending Audit record in the database immediately
    new_audit = Audit(
        id=job_id,
        user_id=current_user.id,
        filename=filename,
        format="Media Stream" if video_url else "File Upload",
        status="Processing...",
        anomalies=[]
    )
    db.add(new_audit)
    db.commit()

    # 2. Dispatch the heavy processing to Celery so the server stays fast
    task = process_video_audit.delay(job_id, temp_file_path, filename, current_user.id)
    
    return JSONResponse({"task_id": task.id, "job_id": job_id, "status": "queued"})


@app.get("/api/audit/status/{task_id}")
async def get_audit_status(task_id: str):
    """Fallback HTTP Polling for clients who drop WebSocket connections."""
    if not CELERY_ENABLED:
        return {"status": "error", "message": "Background processing offline."}

    task_result = celery_app.AsyncResult(task_id)
    
    if task_result.state == 'PENDING':
        return {"status": "running", "stage": "scan", "progress": 0, "message": "Waiting for available engine..."}
    elif task_result.state == 'PROGRESS':
        return {
            "status": "running",
            "stage": task_result.info.get('stage', 'scan'),
            "progress": task_result.info.get('progress', 0),
            "message": task_result.info.get('message', 'Processing...')
        }
    elif task_result.state == 'SUCCESS':
        return {"status": "complete", "result": task_result.result}
    else:
        return {"status": "error", "message": str(task_result.info or "Unknown Error")}


@app.websocket("/ws/audit/{task_id}")
async def websocket_audit_status(websocket: WebSocket, task_id: str):
    """Real-time progress streaming via WebSockets."""
    await websocket.accept()
    if not CELERY_ENABLED:
        await websocket.send_json({"status": "error", "message": "Background processing offline."})
        await websocket.close()
        return
        
    try:
        while True:
            task_result = celery_app.AsyncResult(task_id)
            if task_result.state == 'PENDING':
                await websocket.send_json({"status": "progress", "stage": "scan", "progress": 0, "message": "Waiting for engine..."})
            elif task_result.state == 'PROGRESS':
                await websocket.send_json({
                    "status": "progress", 
                    "stage": task_result.info.get("stage", "scan"), 
                    "progress": task_result.info.get("progress", 0), 
                    "message": task_result.info.get("message", "Processing...")
                })
            elif task_result.state == 'SUCCESS':
                await websocket.send_json({"status": "complete", "result": task_result.result})
                break
            elif task_result.state == 'FAILURE':
                await websocket.send_json({"status": "error", "message": str(task_result.info or "Task Failed")})
                break
            await asyncio.sleep(1.0)
    except Exception as e:
        # Client likely disconnected
        pass
    finally:
        try:
            await websocket.close()
        except:
            pass


# ==========================================
# 9. AI SUGGESTION ROUTES
# ==========================================
class ReportPayload(BaseModel):
    report: str

class SuggestPayload(BaseModel):
    type: str
    description: str

@app.post("/api/ai/summary")
async def generate_summary(payload: ReportPayload, current_user: User = Depends(get_current_user)):
    # Placeholder for actual Gemini API call logic
    summary_text = (
        "The provided audit report indicates several areas requiring review. "
        "Primary concerns center around continuity and potential copyright flags within the timeline. "
        "Please review the flagged timecodes carefully before proceeding to final render."
    )
    return {"text": summary_text}

@app.post("/api/ai/suggest")
async def suggest_fix(payload: SuggestPayload, current_user: User = Depends(get_current_user)):
    # Placeholder for actual Gemini API call logic
    suggestion = (
        f"To resolve the '{payload.type}' anomaly regarding '{payload.description}', "
        "we recommend reviewing the source clip at this timecode. Consider replacing the flagged "
        "asset with cleared media from the Vault, or applying a localized blur/mask if visual."
    )
    return {"text": suggestion}


# ==========================================
# 10. SERVER STARTUP
# ==========================================
if __name__ == "__main__":
    import uvicorn
    # Render binds to the $PORT environment variable
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
