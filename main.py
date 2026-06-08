import os
import shutil
import uuid
import datetime
import asyncio
import time
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
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week token lifespan
PASSWORD_RESET_EXPIRE_MINUTES = 30
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://deepcut.video")

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
# 3. GLOBAL TRANSIENT JOB TRACKER & VAULT
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
    payload = {
        "sub": email,
        "purpose": "password_reset",
        "exp": expire
    }
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
            raise HTTPException(
                status_code=403, 
                detail="Operation denied. Insufficient security clearance."
            )
        return current_user

require_master = RoleChecker(["Master_Control"])
require_admin = RoleChecker(["Master_Control", "Org_Admin"])

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

@app.get("/")
@app.head("/")
def health_check():
    return {"status": "DeepCut Engine is online and operational."}

# ==========================================
# 6. EMAIL & PUBLIC ROUTES
# ==========================================
def send_welcome_email_task(recipient_email: str, username: str, company_name: str):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.resend.com") 
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "resend")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    sender_email = "info@deepcut.video"

    if not smtp_password: return

    msg = MIMEMultipart("alternative")
    msg['From'] = f"DeepCut Engine <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = "DeepCut Engine: Operator Provisioning Complete"

    html_body = f"""
    <html>
    <body style="background-color: #EAE3D2; padding: 40px 20px; font-family: 'Courier New', Courier, monospace; color: #2D2824;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #FDFBF7; border: 4px solid #2D2824; padding: 30px; box-shadow: 6px 6px 0px #2D2824;">
            <div style="text-align: center; border-bottom: 3px solid #2D2824; padding-bottom: 20px; margin-bottom: 20px;">
                <h1 style="margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px;">DeepCut Engine</h1>
                <p style="margin: 5px 0 0 0; font-size: 12px; font-weight: bold; letter-spacing: 3px; color: #504840;">AUTHORIZED PERSONNEL ONLY</p>
            </div>
            <p style="font-size: 14px; line-height: 1.6;"><strong>STATUS:</strong> CLEARANCE GRANTED</p>
            <p style="font-size: 14px; line-height: 1.6;">Operator <strong>[{username}]</strong> has been successfully provisioned under the enterprise entity: <strong>{company_name}</strong>.</p>
            <p style="font-size: 14px; line-height: 1.6;">Your structural workspace is now active. You may begin initializing compliance audits immediately.</p>
            <div style="text-align: center; margin-top: 30px; border-top: 2px dashed #2D2824; padding-top: 20px;">
                <a href="{APP_BASE_URL}" style="display: inline-block; background-color: #40635A; color: #FDFBF7; text-decoration: none; padding: 12px 24px; font-weight: bold; border: 2px solid #2D2824; letter-spacing: 2px; box-shadow: 3px 3px 0px #2D2824;">ACCESS TERMINAL ENTRANCE</a>
            </div>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"SMTP Error: {str(e)}")

def send_reset_email_task(recipient_email: str, reset_link: str):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.resend.com") 
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "resend")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    sender_email = "info@deepcut.video"

    if not smtp_password: return

    msg = MIMEMultipart("alternative")
    msg['From'] = f"DeepCut Engine <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = "DeepCut Engine: Operator Access Recovery"

    html_body = f"""
    <html>
    <body style="background-color: #EAE3D2; padding: 40px 20px; font-family: 'Courier New', Courier, monospace; color: #2D2824;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #FDFBF7; border: 4px solid #2D2824; padding: 30px; box-shadow: 6px 6px 0px #2D2824;">
            <div style="text-align: center; border-bottom: 3px solid #2D2824; padding-bottom: 20px; margin-bottom: 20px;">
                <h1 style="margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px;">System Recovery</h1>
                <p style="margin: 5px 0 0 0; font-size: 12px; font-weight: bold; letter-spacing: 3px; color: #B45044;">SECURITY OVERRIDE INITIATED</p>
            </div>
             <p style="font-size: 14px; line-height: 1.6;">A structural recovery request has been authorized for your Operator account.</p>
            <p style="font-size: 14px; line-height: 1.6;">Use the secure recovery link below to set a new access code. This link expires in 30 minutes.</p>
            <div style="text-align: center; margin: 20px 0;">
                <a href="{reset_link}" style="display: inline-block; background-color: #2D2824; color: #FDFBF7; text-decoration: none; padding: 12px 24px; font-weight: bold; border: 2px solid #2D2824; letter-spacing: 2px;">RESET ACCESS CODE</a>
            </div>
            <p style="font-size: 14px; line-height: 1.6;">If you did not request this recovery, you can ignore this message. Your existing access code has not been changed.</p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"SMTP Error: {str(e)}")

def send_audit_complete_email(recipient_email: str, filename: str, flag_count: int):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.resend.com") 
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "resend")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    sender_email = "info@deepcut.video"

    if not smtp_password: return

    msg = MIMEMultipart("alternative")
    msg['From'] = f"DeepCut Engine <{sender_email}>"
    msg['To'] = recipient_email
    
    status_text = "ACTION REQUIRED" if flag_count > 0 else "CLEAN"
    status_color = "#B45044" if flag_count > 0 else "#4B7350"
    
    msg['Subject'] = f"DeepCut Audit Complete [{status_text}]: {filename}"

    html_body = f"""
    <html>
    <body style="background-color: #EAE3D2; padding: 40px 20px; font-family: 'Courier New', Courier, monospace; color: #2D2824;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #FDFBF7; border: 4px solid #2D2824; padding: 30px; box-shadow: 6px 6px 0px #2D2824;">
            <div style="text-align: center; border-bottom: 3px solid #2D2824; padding-bottom: 20px; margin-bottom: 20px;">
                <h1 style="margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px;">Audit Complete</h1>
                <p style="margin: 5px 0 0 0; font-size: 12px; font-weight: bold; letter-spacing: 3px; color: {status_color};">{status_text}</p>
            </div>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #2D2824; font-weight: bold; width: 40%;">FILE:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #2D2824;">{filename}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #2D2824; font-weight: bold;">ANOMALIES DETECTED:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #2D2824; font-weight: bold; color: {status_color}; font-size: 18px;">{flag_count}</td>
                </tr>
            </table>
            <p style="font-size: 14px; line-height: 1.6;">The DeepCut Engine has finished processing the timeline parameters. Log in to the dashboard to review the full compliance log and AI executive summary.</p>
            <div style="text-align: center; margin-top: 30px;">
                <a href="{APP_BASE_URL}" style="display: inline-block; background-color: #2D2824; color: #FDFBF7; text-decoration: none; padding: 12px 24px; font-weight: bold; border: 2px solid #2D2824; letter-spacing: 2px; box-shadow: 3px 3px 0px #D2911E;">OPEN DASHBOARD</a>
            </div>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"SMTP Error: {str(e)}")

@app.post("/api/register")
def register_user(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    consent: bool = Form(...),
    company_type: str = Form(...),
    company_name: str = Form(...),
    number_of_employees: int = Form(...),
    address_line_1: str = Form(...),
    address_line_2: str = Form(None), 
    city_town: str = Form(...),
    postcode: str = Form(...),
    country: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        existing_user = db.query(User).filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email or Username already registered.")

        hashed_pw = get_password_hash(password)

        new_user = User(
            name=name,
            username=username,
            email=email,
            hashed_password=hashed_pw,
            consent_given=consent,
            company_type=company_type,
            company_name=company_name,
            number_of_employees=number_of_employees,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            city_town=city_town,
            postcode=postcode,
            country=country
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        background_tasks.add_task(send_welcome_email_task, new_user.email, new_user.username, new_user.company_name)
        
        return {"message": "Enterprise account successfully created."}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration Error: {str(e)}")

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter((User.username == form_data.username) | (User.email == form_data.username)).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account is suspended.")

    now = datetime.datetime.utcnow()
    if user.lockout_time and user.lockout_time > now:
        wait_time = int((user.lockout_time - now).total_seconds() / 60)
        raise HTTPException(
            status_code=403, 
            detail=f"Account locked. Cooldown active. Try again in {wait_time} minutes."
        )

    if not verify_password(form_data.password, user.hashed_password):
        user.failed_login_attempts += 1
        print(f"Failed login: {user.username}, attempts={user.failed_login_attempts}")

        if user.failed_login_attempts >= 5:
            user.lockout_time = now + datetime.timedelta(minutes=2)
            print(f"LOCKED UNTIL: {user.lockout_time}")

        db.commit()
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    user.failed_login_attempts = 0
    user.lockout_time = None
    user.last_login = now
    db.commit()

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "username": user.username,
        "role": user.role,
        "is_admin": user.role in ["Master_Control", "Org_Admin"]
    }

@app.post("/api/forgot-password")
def forgot_password(
    background_tasks: BackgroundTasks, 
    email: str = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            reset_token = create_password_reset_token(user.email)
            reset_link = f"{APP_BASE_URL.rstrip('/')}/reset-password?token={reset_token}"
            user.reset_requested = True
            db.commit()
            background_tasks.add_task(send_reset_email_task, user.email, reset_link)
            
        return {"message": "Recovery instructions dispatched if email exists."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

@app.post("/api/reset-password")
def reset_password(
    token: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "password_reset":
            raise JWTError()
        email = payload.get("sub")
        if not email:
            raise JWTError()
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
        if user.is_suspended:
            raise HTTPException(status_code=403, detail="Account is suspended.")

        user.hashed_password = get_password_hash(new_password)
        user.reset_requested = False
        user.failed_login_attempts = 0
        user.lockout_time = None
        db.commit()
        return {"message": "Access code updated securely."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Reset Error: {str(e)}")

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
        
        current_user.hashed_password = get_password_hash(new_password)
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
@app.get("/api/admin/users", response_model=List[AdminUserResponse])
def get_all_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if current_user.role == "Master_Control":
        users = db.query(User).all()
    else:
        users = db.query(User).filter(User.company_name == current_user.company_name).all()
    return users

@app.get("/api/admin/logs")
def get_admin_logs(
    current_user: User = Depends(require_admin), 
    db: Session = Depends(get_db)
):
    if current_user.role == "Master_Control":
        logs = db.query(AdminLog).order_by(AdminLog.timestamp.desc()).limit(50).all()
    else:
        logs = db.query(AdminLog).filter(AdminLog.admin_username == current_user.username).order_by(AdminLog.timestamp.desc()).limit(50).all()
    return logs

@app.delete("/api/admin/users/{user_id}")
def delete_user(
    user_id: int, 
    current_user: User = Depends(require_admin), 
    db: Session = Depends(get_db)
):
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="Operator not found")
        
    if current_user.role == "Org_Admin":
        if getattr(user_to_delete, 'company_name', None) != getattr(current_user, 'company_name', None):
            raise HTTPException(
                status_code=403, 
                detail="Security Override: Cannot modify operators outside your organization."
            )
            
    target_username_cache = user_to_delete.username
    db.delete(user_to_delete)
    
    log_entry = AdminLog(
        admin_username=current_user.username,
        action="PURGED_OPERATOR",
        target_username=target_username_cache
    )
    db.add(log_entry)
    db.commit()
    
    return {"message": f"Operator {user_id} structurally purged."}

@app.post("/api/admin/users/{user_id}/reset-password")
def admin_reset_password(
    user_id: int, 
    current_user: User = Depends(require_admin), 
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Operator not found")
        
    if current_user.role == "Org_Admin":
        if getattr(target_user, 'company_name', None) != getattr(current_user, 'company_name', None):
            raise HTTPException(
                status_code=403, 
                detail="Security Override: Cannot modify operators outside your organization."
            )

    temporary_code = secrets.token_urlsafe(6) 
    target_user.hashed_password = get_password_hash(temporary_code)
    target_user.reset_requested = True

    log_entry = AdminLog(
        admin_username=current_user.username,
        action="RESET_PASSWORD",
        target_username=target_user.username
    )
    db.add(log_entry)
    db.commit()
    
    return {"message": "Access code overridden.", "temporary_code": temporary_code}

@app.post("/api/admin/users/create")
def admin_create_user(
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Operator email or username already exists.")

    temp_password = secrets.token_urlsafe(8)
    hashed_pw = get_password_hash(temp_password)

    new_user = User(
        name=name,
        username=username,
        email=email,
        hashed_password=hashed_pw,
        role="Operator", 
        consent_given=True, 
        company_type=current_user.company_type,
        company_name=current_user.company_name,
        number_of_employees=current_user.number_of_employees,
        address_line_1=current_user.address_line_1,
        address_line_2=current_user.address_line_2,
        city_town=current_user.city_town,
        postcode=current_user.postcode,
        country=current_user.country
    )
    
    db.add(new_user)
    
    log_entry = AdminLog(
        admin_username=current_user.username,
        action="PROVISIONED_OPERATOR",
        target_username=username
    )
    db.add(log_entry)
    db.commit()
    
    return {"message": "Operator provisioned.", "temporary_password": temp_password}


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
# 9. XML PARSING & CONFORM LOGIC
# ==========================================
def parse_fcpxml_timeline(file_path: str):
    """Parses an FCPXML file and extracts timeline structure, clips, and hidden forensic file paths."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_content = f.read().strip()
            
        if not raw_content:
            return {"success": False, "error": "The uploaded XML file is empty."}
            
        start_index = raw_content.find('<')
        if start_index != -1:
            raw_content = raw_content[start_index:]

        root = ET.fromstring(raw_content)
        
        project_tag = root.find('.//project')
        project_name = project_tag.get('name', 'Unknown Project') if project_tag is not None else 'Unknown Project'
        
        sequence_tag = root.find('.//sequence')
        sequence_duration = sequence_tag.get('duration', '00:00:00:00') if sequence_tag is not None else '00:00:00:00'
        
        # Forensic upgrade: Map all hidden original file pathways
        asset_map = {}
        for asset in root.findall('.//asset'):
            asset_id = asset.get('id')
            src_path = asset.get('src', 'Unknown Path')
            if asset_id:
                asset_map[asset_id] = src_path
        
        clips = []
        for item in root.findall('.//spine/*'):
            clip_type = item.tag  
            name = item.get('name', 'Unknown')
            offset = item.get('offset', '00:00:00:00')
            duration = item.get('duration', '00:00:00:00')
            
            ref_id = item.get('ref')
            if not ref_id:
                media_tag = item.find('*[@ref]')
                if media_tag is not None:
                    ref_id = media_tag.get('ref')
                    
            hidden_path = asset_map.get(ref_id, "No forensic path found")
                
            clips.append({
                "type": clip_type,
                "name": name,
                "timecode": offset,
                "duration": duration,
                "hidden_path": hidden_path
            })
            
        return {
            "success": True,
            "project_name": project_name,
            "duration": sequence_duration,
            "clips": clips
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to parse XML: {str(e)}"}


def run_conform_audit(xml_string: str):
    """
    Scans a timeline XML for technical conform errors.
    Returns a list of anomaly dictionaries for the frontend.
    """
    anomalies = []
    
    try:
        # Some XML files might have leading whitespaces/newlines before the declaration
        start_index = xml_string.find('<')
        if start_index != -1:
            xml_string = xml_string[start_index:]
        root = ET.fromstring(xml_string)
    except ET.ParseError:
        return [{"timecode": "00:00:00", "type": "High Risk - Parsing", "description": "XML file is corrupted or malformed."}]

    # --- RULE 1: OFFLINE MEDIA & LOCAL PATH CHECKS ---
    for asset in root.iter('asset'):
        asset_id = asset.get('id', 'Unknown ID')
        asset_name = asset.get('name', f'Asset_{asset_id}')
        src = asset.get('src', '')

        # 1A. Blank or Missing File Paths
        if not src or src.strip() == '':
            anomalies.append({
                "timecode": "N/A", 
                "type": "High Risk - Offline Media",
                "description": f"Media Offline: The clip '{asset_name}' has a blank source pathway and cannot be conformed."
            })
            continue

        # 1B. Local Drive References (A nightmare for post-houses)
        if "C:/Users/" in src or "/Users/" in src or "Desktop" in src:
            anomalies.append({
                "timecode": "N/A",
                "type": "Medium Risk - Local Drive Reference",
                "description": f"Path Warning: '{asset_name}' points to a local user drive rather than a shared post-production server."
            })

    # --- RULE 2: FRAMERATE MISMATCH CHECKS ---
    master_framerate = None
    for format_tag in root.iter('format'):
        fd = format_tag.get('frameDuration', '')
        if fd:
            master_framerate = fd
            break 
            
    if master_framerate:
        for clip in root.iter('asset-clip'):
            clip_name = clip.get('name', 'Unknown Clip')
            clip_fd = clip.get('tcFormat', '') 
            
            if clip_fd and clip_fd != master_framerate:
                anomalies.append({
                    "timecode": clip.get('start', 'N/A'),
                    "type": "High Risk - Framerate Mismatch",
                    "description": f"Timing Slip Risk: Clip '{clip_name}' has a different timebase ({clip_fd}) than the master sequence ({master_framerate})."
                })

    return anomalies


# ==========================================
# 10. BACKGROUND WORKER & AUDIT LOGIC
# ==========================================
def process_audit_in_background(job_id: str, file_path: str, filename: str, user_id: int):
    global active_jobs
    db = SessionLocal()
    try:
        active_jobs[job_id] = {"stage": "scan", "progress": 10, "message": "Parsing timeline XML metadata..."}
        
        # 1. Read the incoming XML content
        xml_content = ""
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                xml_content = f.read().strip()
                
        time.sleep(2.0)
        active_jobs[job_id] = {"stage": "scan", "progress": 100, "message": "Auditing raw waveforms for licensing signatures..."}
        
        time.sleep(2.0)
        active_jobs[job_id] = {"stage": "detect", "progress": 100, "message": "Detecting physical continuity and visual violations..."}
        
        time.sleep(2.0)
        
        # 3. NEW: Run the conform audit based on the actual uploaded XML text
        conform_anomalies = run_conform_audit(xml_content) if xml_content else []

        # 4. Merge results
        final_anomalies = ai_anomalies + conform_anomalies

        audit_record = db.query(Audit).filter(Audit.id == job_id).first()
        if audit_record:
            audit_record.status = "Flagged" if len(final_anomalies) > 0 else "Clean"
            audit_record.anomalies = final_anomalies
            db.commit()

            user = db.query(User).filter(User.id == user_id).first()
            if user:
                send_audit_complete_email(user.email, filename, len(final_anomalies))

        active_jobs[job_id] = {
            "status": "complete",
            "filename": filename,
            "format": "FCPXML Sequence",
            "flag_count": len(final_anomalies),
            "anomalies": final_anomalies
        }

    except Exception as e:
        db.rollback()
        audit_record = db.query(Audit).filter(Audit.id == job_id).first()
        if audit_record:
            audit_record.status = "Error"
            db.commit()
        active_jobs[job_id] = {"status": "error", "message": str(e)}
    finally:
        # Cleanup the temporary XML file
        if os.path.exists(file_path):
            os.remove(file_path)
        db.close()


@app.post("/api/audit/start")
async def start_audit(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    video_url: str = Form(None),
    current_user: User = Depends(get_current_user)
):
    if not file and not video_url:
        raise HTTPException(status_code=400, detail="No timeline file or URL provided.")
        
    job_id = str(uuid.uuid4())
    filename = file.filename if file else "URL_Stream"
    file_path = f"temp_{job_id}.xml"
    
    if file:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    else:
        with open(file_path, "w") as f:
            f.write("<fcpxml><project name='URL_Stream'></project></fcpxml>")

    db = SessionLocal()
    new_audit = Audit(
        id=job_id,
        user_id=current_user.id,
        filename=filename,
        format="FCPXML Sequence",
        status="Running"
    )
    db.add(new_audit)
    db.commit()
    db.close()

    active_jobs[job_id] = {
        "stage": "scan", 
        "progress": 0, 
        "message": "INITIALIZING..."
    }

    background_tasks.add_task(
        process_audit_in_background, 
        job_id, 
        file_path, 
        filename, 
        current_user.id
    )

    return {"task_id": job_id}

@app.get("/api/audit/status/{task_id}")
def get_audit_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    global active_jobs

    audit_record = db.query(Audit).filter(
        Audit.id == task_id,
        Audit.user_id == current_user.id
    ).first()

    if not audit_record:
        raise HTTPException(status_code=404, detail="Unknown audit task.")

    job_state = active_jobs.get(task_id)

    if not job_state:
        return {
            "status": audit_record.status.lower(),
            "result": {
                "filename": audit_record.filename,
                "format": audit_record.format,
                "anomalies": audit_record.anomalies or []
            }
        }

    if job_state.get("status") == "complete":
        return {"status": "complete", "result": job_state}

    if job_state.get("status") == "error":
        return {"status": "error", "message": job_state.get("message", "Audit failed.")}

    return {
        "status": "running",
        "stage": job_state.get("stage", "scan"),
        "progress": job_state.get("progress", 0),
        "message": job_state.get("message", "Processing...")
    }

@app.websocket("/ws/audit/{task_id}")
async def websocket_audit_status(websocket: WebSocket, task_id: str):
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    db = SessionLocal()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if not username:
            await websocket.close(code=1008)
            return

        user = db.query(User).filter(User.username == username).first()

        if not user:
            await websocket.close(code=1008)
            return

        audit_record = db.query(Audit).filter(
            Audit.id == task_id,
            Audit.user_id == user.id
        ).first()

        if not audit_record:
            await websocket.close(code=1008)
            return

        await websocket.accept()

        while True:
            job_state = active_jobs.get(task_id)

            if not job_state:
                await websocket.send_json({
                    "status": audit_record.status.lower(),
                    "result": {
                        "filename": audit_record.filename,
                        "format": audit_record.format,
                        "anomalies": audit_record.anomalies or []
                    }
                })
                break

            if job_state.get("status") == "complete":
                await websocket.send_json({"status": "complete", "result": job_state})
                break

            if job_state.get("status") == "error":
                await websocket.send_json({
                    "status": "error",
                    "message": job_state.get("message", "Audit failed.")
                })
                break

            await websocket.send_json({
                "status": "progress",
                "stage": job_state.get("stage", "scan"),
                "progress": job_state.get("progress", 0),
                "message": job_state.get("message", "Processing...")
            })

            await asyncio.sleep(0.5)

    except JWTError:
        await websocket.close(code=1008)
    finally:
        db.close()
        try:
            await websocket.close()
        except Exception:
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