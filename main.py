import os
import shutil
import uuid
import datetime
import asyncio
import time
import json
import openai
from typing import List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import xml.etree.ElementTree as ET

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
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_for_local_dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
PASSWORD_RESET_EXPIRE_MINUTES = 30
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://deepcut.video")

# ==========================================
# 2. DATABASE SETUP
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
    company_type = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    number_of_employees = Column(Integer, nullable=True)
    address_line_1 = Column(String, nullable=True)
    address_line_2 = Column(String, nullable=True)
    city_town = Column(String, nullable=True)
    postcode = Column(String, nullable=True)
    country = Column(String, nullable=True)
    role = Column(String, default="Operator")
    failed_login_attempts = Column(Integer, default=0)
    lockout_time = Column(DateTime, nullable=True)
    
    audits = relationship("Audit", back_populates="owner", cascade="all, delete-orphan")

class AdminLog(Base):
    __tablename__ = "deepcut_admin_logs"
    id = Column(Integer, primary_key=True, index=True)
    admin_username = Column(String, nullable=False)
    action = Column(String, nullable=False)
    target_username = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

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

class AdminUserResponse(BaseModel):
    name: Optional[str] = None
    username: str
    email: str
    role: str
    company_name: Optional[str] = None
    is_suspended: bool
    last_login: Optional[datetime.datetime] = None
    id: int

    class Config:
        orm_mode = True
        from_attributes = True

Base.metadata.create_all(bind=engine)

# ==========================================
# 3. GLOBAL TRANSIENT JOB TRACKER
# ==========================================
active_jobs = {}
TEMP_UPLOAD_DIR = "tmp_uploads"
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

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

def create_password_reset_token(email: str):
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES)
    payload = {"sub": email, "purpose": "password_reset", "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

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
    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account is suspended.")
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(status_code=403, detail="Operation denied. Insufficient security clearance.")
        return current_user

require_master = RoleChecker(["Master_Control"])
require_admin = RoleChecker(["Master_Control", "Org_Admin"])

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

@app.get("/")
@app.head("/")
def health_check():
    return {"status": "DeepCut Engine is online and operational."}

# ==========================================
# 6. EMAILS
# ==========================================
def send_welcome_email_task(recipient_email: str, username: str, company_name: str):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.resend.com") 
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "resend")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    if not smtp_password: return
    sender_email = "info@deepcut.video"
    msg = MIMEMultipart("alternative")
    msg['From'] = f"DeepCut Engine <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = "DeepCut Engine: Operator Provisioning Complete"
    html_body = f"<html><body><p>Operator [{username}] provisioned.</p></body></html>"
    msg.attach(MIMEText(html_body, 'html'))
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        pass

def send_reset_email_task(recipient_email: str, reset_link: str):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.resend.com") 
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "resend")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    if not smtp_password: return
    sender_email = "info@deepcut.video"
    msg = MIMEMultipart("alternative")
    msg['From'] = f"DeepCut Engine <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = "DeepCut Engine: Operator Access Recovery"
    html_body = f"<html><body><a href='{reset_link}'>RESET ACCESS CODE</a></body></html>"
    msg.attach(MIMEText(html_body, 'html'))
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        pass

def send_audit_complete_email(recipient_email: str, filename: str, flag_count: int):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.resend.com") 
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "resend")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    if not smtp_password: return
    sender_email = "info@deepcut.video"
    msg = MIMEMultipart("alternative")
    msg['From'] = f"DeepCut Engine <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = f"DeepCut Audit Complete: {filename}"
    html_body = f"<html><body><p>Audit Complete. Flags: {flag_count}</p></body></html>"
    msg.attach(MIMEText(html_body, 'html'))
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        pass

# ==========================================
# 7. PUBLIC ROUTES (AUTH)
# ==========================================
@app.post("/api/register")
def register_user(
    background_tasks: BackgroundTasks,
    name: str = Form(...), username: str = Form(...), email: str = Form(...),
    password: str = Form(...), consent: bool = Form(...), company_type: str = Form(...),
    company_name: str = Form(...), number_of_employees: int = Form(...),
    address_line_1: str = Form(...), address_line_2: str = Form(None), 
    city_town: str = Form(...), postcode: str = Form(...), country: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        if db.query(User).filter((User.email == email) | (User.username == username)).first():
            raise HTTPException(status_code=400, detail="Email or Username already registered.")
        new_user = User(
            name=name, username=username, email=email, hashed_password=get_password_hash(password),
            consent_given=consent, company_type=company_type, company_name=company_name,
            number_of_employees=number_of_employees, address_line_1=address_line_1,
            address_line_2=address_line_2, city_town=city_town, postcode=postcode, country=country
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        background_tasks.add_task(send_welcome_email_task, new_user.email, new_user.username, new_user.company_name)
        return {"message": "Enterprise account successfully created."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter((User.username == form_data.username) | (User.email == form_data.username)).first()
    if not user or user.is_suspended:
        raise HTTPException(status_code=401, detail="Access denied")
    now = datetime.datetime.utcnow()
    if user.lockout_time and user.lockout_time > now:
        raise HTTPException(status_code=403, detail="Account locked.")
    if not verify_password(form_data.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5: user.lockout_time = now + datetime.timedelta(minutes=2)
        db.commit()
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    
    user.failed_login_attempts = 0
    user.lockout_time = None
    user.last_login = now
    db.commit()
    
    return {
        "access_token": create_access_token(data={"sub": user.username, "role": user.role}), 
        "token_type": "bearer", "username": user.username, "role": user.role,
        "is_admin": user.role in ["Master_Control", "Org_Admin"]
    }

@app.post("/api/forgot-password")
def forgot_password(background_tasks: BackgroundTasks, email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user:
        reset_token = create_password_reset_token(user.email)
        background_tasks.add_task(send_reset_email_task, user.email, f"{APP_BASE_URL.rstrip('/')}/#forgot?token={reset_token}")
        user.reset_requested = True
        db.commit()
    return {"message": "Recovery instructions dispatched."}

@app.post("/api/change-password")
def change_password(
    current_password: str = Form(...), new_password: str = Form(...),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current code incorrect.")
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    return {"message": "Access code updated."}

# ==========================================
# 8. ADMIN ROUTES
# ==========================================
@app.get("/api/admin/users", response_model=List[AdminUserResponse])
def get_all_users(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user.role == "Master_Control": return db.query(User).all()
    return db.query(User).filter(User.company_name == current_user.company_name).all()

@app.get("/api/admin/logs")
def get_admin_logs(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user.role == "Master_Control": return db.query(AdminLog).order_by(AdminLog.timestamp.desc()).limit(50).all()
    return db.query(AdminLog).filter(AdminLog.admin_username == current_user.username).order_by(AdminLog.timestamp.desc()).limit(50).all()

@app.delete("/api/admin/users/{user_id}")
def delete_user(user_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete: raise HTTPException(status_code=404, detail="Operator not found")
    db.delete(user_to_delete)
    db.add(AdminLog(admin_username=current_user.username, action="PURGED_OPERATOR", target_username=user_to_delete.username))
    db.commit()
    return {"message": "Operator purged."}

@app.post("/api/admin/users/{user_id}/reset-password")
def admin_reset_password(user_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    target_user = db.query(User).filter(User.id == user_id).first()
    temporary_code = secrets.token_urlsafe(6) 
    target_user.hashed_password = get_password_hash(temporary_code)
    db.add(AdminLog(admin_username=current_user.username, action="RESET_PASSWORD", target_username=target_user.username))
    db.commit()
    return {"message": "Access code overridden.", "temporary_code": temporary_code}

@app.post("/api/admin/users/create")
def admin_create_user(
    name: str = Form(...), username: str = Form(...), email: str = Form(...),
    current_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    temp_password = secrets.token_urlsafe(8)
    new_user = User(
        name=name, username=username, email=email, hashed_password=get_password_hash(temp_password),
        role="Operator", consent_given=True, company_type=current_user.company_type, company_name=current_user.company_name
    )
    db.add(new_user)
    db.add(AdminLog(admin_username=current_user.username, action="PROVISIONED_OPERATOR", target_username=username))
    db.commit()
    return {"message": "Operator provisioned.", "temporary_password": temp_password}

# ==========================================
# 9. VAULT LOGIC
# ==========================================
@app.get("/api/audits")
def get_user_audits(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audits = db.query(Audit).filter(Audit.user_id == current_user.id).order_by(Audit.timestamp.desc()).all()
    return [{"id": a.id, "filename": a.filename, "format": a.format, "timestamp": a.timestamp.isoformat(), "status": a.status, "flag_count": len(a.anomalies) if a.anomalies else 0} for a in audits]

@app.get("/api/audits/{audit_id}")
def get_single_audit(audit_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit = db.query(Audit).filter(Audit.id == audit_id, Audit.user_id == current_user.id).first()
    return {"id": audit.id, "filename": audit.filename, "format": audit.format, "status": audit.status, "anomalies": audit.anomalies}

# ==========================================
# 10. XML PARSER & CONFORM RULES
# ==========================================
def parse_fcpxml_timeline(file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_content = f.read().strip()
        if not raw_content: return {"success": False, "error": "Empty XML"}
        
        start_index = raw_content.find('<')
        if start_index != -1: raw_content = raw_content[start_index:]
        root = ET.fromstring(raw_content)
        
        asset_map = {asset.get('id'): asset.get('src', 'Unknown Path') for asset in root.findall('.//asset') if asset.get('id')}
        
        clips = []
        for item in root.iter():
            if item.tag in ['asset-clip', 'clip', 'mc-clip', 'sync-clip', 'ref-clip']:
                ref_id = item.get('ref')
                if not ref_id:
                    media_tag = item.find('*[@ref]')
                    if media_tag is not None: ref_id = media_tag.get('ref')
                
                clips.append({
                    "type": item.tag,
                    "name": item.get('name', 'Unknown'),
                    "timecode": item.get('offset', '00:00:00:00'),
                    "duration": item.get('duration', '00:00:00:00'),
                    "hidden_path": asset_map.get(ref_id, "No path found")
                })
        return {"success": True, "clips": clips}
    except Exception as e:
        return {"success": False, "error": str(e)}

def run_conform_audit(xml_string: str):
    anomalies = []
    try:
        start_index = xml_string.find('<')
        if start_index != -1: xml_string = xml_string[start_index:]
        root = ET.fromstring(xml_string)
    except ET.ParseError:
        return [{"timecode": "00:00:00", "type": "High Risk - Parsing", "description": "XML is corrupted."}]

    for asset in root.iter('asset'):
        asset_name = asset.get('name', 'Unknown ID')
        src = asset.get('src', '')
        if not src or src.strip() == '':
            anomalies.append({"timecode": "N/A", "type": "High Risk - Offline Media", "description": f"Media Offline: The clip '{asset_name}' has a blank source pathway."})
        elif any(path in src for path in ["C:/Users/", "/Users/", "Desktop"]):
            anomalies.append({"timecode": "N/A", "type": "Medium Risk - Local Path", "description": f"Path Warning: '{asset_name}' points to a local user drive."})

    master_framerate = next((f.get('frameDuration') for f in root.iter('format') if f.get('frameDuration')), None)
    if master_framerate:
        for clip in root.iter('asset-clip'):
            clip_fd = clip.get('tcFormat', '')
            if clip_fd and clip_fd != master_framerate:
                anomalies.append({"timecode": clip.get('start', 'N/A'), "type": "High Risk - Framerate Mismatch", "description": f"Clip '{clip.get('name', '')}' timebase mismatch."})
    return anomalies

async def call_openai_for_compliance(extracted_metadata):
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"You are a compliance officer. Detect copyright, continuity, and broadcast standard issues. Return JSON with 'anomalies'. Data: {json.dumps(extracted_metadata)}"
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content).get("anomalies", [])
    except Exception as e:
        print(f"AI API Error: {e}")
        return []

# ==========================================
# 11. AUDIT ENGINE PROCESS
# ==========================================
async def process_audit_in_background(job_id: str, file_path: str, filename: str, user_id: int):
    global active_jobs
    db = SessionLocal()
    try:
        active_jobs[job_id] = {"stage": "scan", "progress": 10, "message": "Parsing XML metadata..."}
        
        xml_content = ""
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                xml_content = f.read().strip()

        parsed_data = parse_fcpxml_timeline(file_path)
        extracted_metadata = parsed_data.get("clips", []) if parsed_data["success"] else []
        
        active_jobs[job_id] = {"stage": "detect", "progress": 50, "message": "AI is auditing metadata..."}
        ai_anomalies = await call_openai_for_compliance(extracted_metadata)
        conform_anomalies = run_conform_audit(xml_content) if xml_content else []
        final_anomalies = ai_anomalies + conform_anomalies

        audit_record = db.query(Audit).filter(Audit.id == job_id).first()
        if audit_record:
            audit_record.status = "Flagged" if len(final_anomalies) > 0 else "Clean"
            audit_record.anomalies = final_anomalies
            db.commit()

        active_jobs[job_id] = {
            "status": "complete", "filename": filename, "format": "FCPXML Sequence",
            "flag_count": len(final_anomalies), "anomalies": final_anomalies
        }
    except Exception as e:
        db.rollback()
        active_jobs[job_id] = {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        db.close()

@app.post("/api/audit/start")
async def start_audit(background_tasks: BackgroundTasks, file: UploadFile = File(None), video_url: str = Form(None), current_user: User = Depends(get_current_user)):
    job_id = str(uuid.uuid4())
    filename = file.filename if file else "URL_Stream"
    file_path = f"temp_{job_id}.xml"
    if file:
        with open(file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    else:
        with open(file_path, "w") as f: f.write("<fcpxml></fcpxml>")

    db = SessionLocal()
    db.add(Audit(id=job_id, user_id=current_user.id, filename=filename, format="FCPXML", status="Running"))
    db.commit()
    db.close()

    active_jobs[job_id] = {"stage": "scan", "progress": 0, "message": "INITIALIZING..."}
    background_tasks.add_task(process_audit_in_background, job_id, file_path, filename, current_user.id)
    return {"task_id": job_id}

@app.get("/api/audit/status/{task_id}")
def get_audit_status(task_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job_state = active_jobs.get(task_id)
    if job_state and job_state.get("status") == "complete": return {"status": "complete", "result": job_state}
    if job_state and job_state.get("status") == "error": return {"status": "error", "message": job_state.get("message")}
    return {"status": "running", "stage": job_state.get("stage", "scan"), "progress
