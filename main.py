import os
import uuid
import asyncio
import subprocess
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import aiofiles
from pydub import AudioSegment
from openai import AsyncOpenAI
from sqlalchemy import create_engine, Column, String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt

# ==========================================
# 1. SYSTEM CONFIGURATION & SECURITY
# ==========================================

app = FastAPI(title="DeepCut API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment Variables (Set these in Render Dashboard)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./deepcut.db") # Fallback to local SQLite if Postgres isn't set
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-fallback-key-replace-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 24 hours

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

TEMP_DIR = "temp_workspace"
os.makedirs(TEMP_DIR, exist_ok=True)

# ==========================================
# 2. DATABASE ARCHITECTURE (SQLAlchemy)
# ==========================================

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    consent_given = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

class AuditRecord(Base):
    __tablename__ = "audits"
    id = Column(String, primary_key=True, index=True)
    operator_id = Column(String, ForeignKey("users.id"))
    filename = Column(String)
    status = Column(String)
    flag_count = Column(Integer)
    format = Column(String)
    timestamp = Column(String)
    raw_anomalies = Column(Text) # Store JSON string of anomalies

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 3. AUTHENTICATION UTILITIES
# ==========================================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ==========================================
# 4. WEBSOCKET MANAGER & TRACKING
# ==========================================

ACTIVE_TASKS = {} # Tracks progress status

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]

    async def send_update(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            try:
                await self.active_connections[task_id].send_json(message)
            except Exception:
                self.disconnect(task_id)

manager = ConnectionManager()

# ==========================================
# 5. HEAVY MEDIA PROCESSING PIPELINE
# ==========================================

async def process_massive_video(file: UploadFile, task_id: str):
    """Streams video to disk, extracts audio via FFmpeg, and slices it for OpenAI."""
    session_id = str(uuid.uuid4())
    video_path = os.path.join(TEMP_DIR, f"{session_id}_{file.filename}")
    audio_path = os.path.join(TEMP_DIR, f"{session_id}_extracted.mp3")
    chunk_paths = []
    
    try:
        await manager.send_update(task_id, {"status": "progress", "stage": "scan", "progress": 10, "message": "Streaming file to secure node..."})
        
        # 1. Stream to Disk Asynchronously
        async with aiofiles.open(video_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024): 
                await out_file.write(content)
        
        await manager.send_update(task_id, {"status": "progress", "stage": "scan", "progress": 40, "message": "Extracting audio footprint..."})
        
        # 2. FFmpeg Extraction (Mono, 64kbps MP3)
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path,
            '-vn', '-acodec', 'libmp3lame', '-ac', '1', '-b:a', '64k', audio_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        await manager.send_update(task_id, {"status": "progress", "stage": "scan", "progress": 70, "message": "Slicing for AI ingestion..."})
        
        # 3. Chunking for OpenAI limit (15 mins)
        audio = AudioSegment.from_mp3(audio_path)
        chunk_length_ms = 15 * 60 * 1000 
        chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
        
        for i, chunk in enumerate(chunks):
            chunk_file = os.path.join(TEMP_DIR, f"{session_id}_chunk_{i}.mp3")
            chunk.export(chunk_file, format="mp3")
            chunk_paths.append(chunk_file)
            
        return chunk_paths
        
    except subprocess.CalledProcessError:
        raise Exception("FFmpeg extraction failed. Corrupt timeline.")
    except Exception as e:
        raise Exception(f"Media failure: {str(e)}")
    finally:
        if os.path.exists(video_path): os.remove(video_path)
        if os.path.exists(audio_path): os.remove(audio_path)

async def background_audit_worker(task_id: str, file: UploadFile, user: User, db: Session):
    """Manages the pipeline, calls OpenAI, and saves to PostgreSQL."""
    try:
        audio_chunks = await process_massive_video(file, task_id)
        
        await manager.send_update(task_id, {"status": "progress", "stage": "detect", "progress": 85, "message": "Transcribing audio chunks..."})
        
        full_transcript = ""
        # 4. Process Chunks via OpenAI Whisper
        for chunk in audio_chunks:
            with open(chunk, "rb") as af:
                res = await openai_client.audio.transcriptions.create(model="whisper-1", file=af)
                full_transcript += res.text + " "
            os.remove(chunk) # Cleanup chunk immediately
            
        await manager.send_update(task_id, {"status": "progress", "stage": "detect", "progress": 95, "message": "Analyzing transcript for anomalies..."})
        
        # 5. Analyze Transcript (Replace this with your specific GPT-4 compliance prompt)
        # For demonstration, we trigger a mock result so the frontend responds correctly
        import json
        mock_anomalies = [
            {"timecode": "00:04:12:00", "type": "High - Copyright", "description": "Unlicensed commercial track detected in background."},
            {"timecode": "00:15:30:12", "type": "Medium - Continuity", "description": "Visual jump cut detected without audio bridge."}
        ]
        
        result_data = {
            "id": str(uuid.uuid4()),
            "filename": file.filename,
            "status": "Flagged" if len(mock_anomalies) > 0 else "Clean",
            "flag_count": len(mock_anomalies),
            "format": "MP4/Audio",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "anomalies": mock_anomalies
        }
        
        # 6. Save Record to Database Vault
        db_audit = AuditRecord(
            id=result_data["id"],
            operator_id=user.id,
            filename=result_data["filename"],
            status=result_data["status"],
            flag_count=result_data["flag_count"],
            format=result_data["format"],
            timestamp=result_data["timestamp"],
            raw_anomalies=json.dumps(mock_anomalies)
        )
        db.add(db_audit)
        db.commit()
        
        ACTIVE_TASKS[task_id] = {"status": "complete", "result": result_data}
        await manager.send_update(task_id, {"status": "complete", "result": result_data})
        
    except Exception as e:
        ACTIVE_TASKS[task_id] = {"status": "error", "message": str(e)}
        await manager.send_update(task_id, {"status": "error", "message": str(e)})

# ==========================================
# 6. API ENDPOINTS
# ==========================================

@app.post("/api/register")
async def register(
    name: str = Form(...), username: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken.")
    
    new_user = User(
        id=str(uuid.uuid4()),
        name=name,
        username=username,
        email=email,
        hashed_password=get_password_hash(password)
    )
    db.add(new_user)
    db.commit()
    return {"message": "Operator registered successfully"}

@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid Credentials")
    
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "username": user.username, "is_admin": user.is_admin}

@app.post("/api/audit/start")
async def start_audit(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check Quotas here in production
    task_id = str(uuid.uuid4())
    ACTIVE_TASKS[task_id] = {"status": "running"}
    
    # Pass db session and user to background worker
    asyncio.create_task(background_audit_worker(task_id, file, current_user, db))
    return {"task_id": task_id}

@app.websocket("/ws/audit/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(websocket, task_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id)

@app.get("/api/audit/status/{task_id}")
async def get_audit_status(task_id: str, current_user: User = Depends(get_current_user)):
    task = ACTIVE_TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/api/audits")
async def get_audits(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    import json
    audits = db.query(AuditRecord).filter(AuditRecord.operator_id == current_user.id).order_by(AuditRecord.timestamp.desc()).all()
    results = []
    for a in audits:
        results.append({
            "id": a.id, "filename": a.filename, "status": a.status, "flag_count": a.flag_count, 
            "format": a.format, "timestamp": a.timestamp, "anomalies": json.loads(a.raw_anomalies) if a.raw_anomalies else []
        })
    return results

class AIRequest(BaseModel):
    report: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None

@app.post("/api/ai/summary")
async def generate_summary(req: AIRequest, current_user: User = Depends(get_current_user)):
    # Replace with real openai_client.chat.completions call
    await asyncio.sleep(1)
    return {"text": "Executive Summary: The analyzed timeline presents 2 critical structural anomalies that mandate operator review prior to deployment."}

@app.post("/api/ai/suggest")
async def generate_suggestion(req: AIRequest, current_user: User = Depends(get_current_user)):
    # Replace with real openai_client.chat.completions call
    await asyncio.sleep(1)
    return {"text": f"Remediation Strategy: Address the {req.type} by executing a timeline substitution or applying a limiter effect to the specified sub-channel."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
