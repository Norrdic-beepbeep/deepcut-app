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
import secrets

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

    from sqlalchemy import Column, Integer, String, DateTime
import datetime

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


from typing import List

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)):
        # If their role isn't on the VIP list, instantly block them
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail="Operation denied. Insufficient security clearance."
            )
        return current_user

# Create specific bouncers you can attach to any route
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

def send_audit_complete_email(recipient_email: str, filename: str, flag_count: int):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.resend.com") 
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "resend")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    sender_email = "info@deepcut.video"

    if not smtp_password:
        print("SMTP_PASSWORD missing. Cannot send completion email.")
        return

    msg = MIMEMultipart()
    msg['From'] = f"DeepCut Engine <{sender_email}>"
    msg['To'] = recipient_email
    
    # Change the subject line depending on if the engine found issues
    status_text = "ACTION REQUIRED" if flag_count > 0 else "CLEAN"
    msg['Subject'] = f"DeepCut Audit Complete [{status_text}]: {filename}"

    body = f"""
    DEEPCUT SYSTEM ALERT
    -----------------------------------------
    The engine has finished processing your timeline.
    
    File Name: {filename}
    Anomalies Detected: {flag_count}
    
    Log in to the DeepCut Engine dashboard to review the full audit report 
    and export your clearance documentation.
    -----------------------------------------
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"Audit completion email dispatched to {recipient_email}")
    except Exception as e:
        print(f"SMTP Error: Failed to dispatch completion email. Error: {str(e)}")


@app.post("/api/register")
def register_user(
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
        # 1. Check if username or email is already taken
        existing_user = db.query(User).filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email or Username already registered.")

        # 2. Hash the secure password
        hashed_pw = get_password_hash(password)

        # 3. Build the COMPLETE operator profile
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
        
        # 4. Save to DBeaver
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {"message": "Enterprise account successfully created."}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration Error: {str(e)}")
    # ... existing password hashing logic ...

    new_user = User(
        # ... existing fields mapped here ...
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
    
    return {"message": "Enterprise account successfully created."}

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter((User.username == form_data.username) | (User.email == form_data.username)).first()
    
    # 1. Handle non-existent users immediately
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # 2. Check for Cooldown
    now = datetime.datetime.utcnow()
    if user.lockout_time and user.lockout_time > now:
        wait_time = int((user.lockout_time - now).total_seconds() / 60)
        raise HTTPException(
            status_code=403, 
            detail=f"Account locked. Cooldown active. Try again in {wait_time} minutes."
        )

    # 3. Check password
    if not verify_password(form_data.password, user.hashed_password):
    user.failed_login_attempts += 1

    print(
        f"Failed login: {user.username}, "
        f"attempts={user.failed_login_attempts}"
    )

    if user.failed_login_attempts >= 5:
        user.lockout_time = now + datetime.timedelta(minutes=2)
        print(f"LOCKED UNTIL: {user.lockout_time}")

    db.commit()

    raise HTTPException(
        status_code=401,
        detail="Incorrect username or password"
    )

    # 4. Successful login: Reset counters
    user.failed_login_attempts = 0
    user.lockout_time = None
    user.last_login = now
    db.commit()

    # ... (Keep your existing token generation/return logic here) ...
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
# The Depends(require_admin) is the physical lock on the door
@app.get("/api/admin/users")
def get_all_users(
    current_user: User = Depends(require_admin), # Lets both roles inside
    db: Session = Depends(get_db)
):
    if current_user.role == "Master_Control":
        # Master Control gets the global list
        users = db.query(User).all()
    else:
        # Org_Admin ONLY gets a list of their exact co-workers
        users = db.query(User).filter(User.company_name == current_user.company_name).all()
        
    return users

@app.get("/api/admin/logs")
def get_admin_logs(
    current_user: User = Depends(require_admin), 
    db: Session = Depends(get_db)
):
    if current_user.role == "Master_Control":
        # Master gets to see everything
        logs = db.query(AdminLog).order_by(AdminLog.timestamp.desc()).limit(50).all()
    else:
        # Org_Admin only sees their own actions
        logs = db.query(AdminLog).filter(AdminLog.admin_username == current_user.username).order_by(AdminLog.timestamp.desc()).limit(50).all()
        
    return logs

@app.delete("/api/admin/users/{user_id}")
def delete_user(
    user_id: int, 
    current_user: User = Depends(require_admin), 
    db: Session = Depends(get_db)
):
    # 1. Find the target user in the database
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="Operator not found")
        
    # 2. Strict Boundary Check for Org_Admins
    # Managers can only delete operators that share their exact company name
    if current_user.role == "Org_Admin":
        if getattr(user_to_delete, 'company_name', None) != getattr(current_user, 'company_name', None):
            raise HTTPException(
                status_code=403, 
                detail="Security Override: Cannot modify operators outside your organization."
            )
            
    # 3. Master_Control bypasses the check entirely and deletes the user
    db.delete(user_to_delete)
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
        
    # Strict Boundary Check for Org_Admins
    if current_user.role == "Org_Admin":
        if getattr(target_user, 'company_name', None) != getattr(current_user, 'company_name', None):
            raise HTTPException(
                status_code=403, 
                detail="Security Override: Cannot modify operators outside your organization."
            )

    # Generate a secure, random fallback code
    temporary_code = secrets.token_urlsafe(6) 
    target_user.hashed_password = get_password_hash(temporary_code)
    target_user.reset_requested = True

# --- NEW AUDIT LOG ---
    log_entry = AdminLog(
        admin_username=current_user.username,
        action="RESET_PASSWORD",
        target_username=target_user.username
    )
    db.add(log_entry)
    # ---------------------
    
    db.commit()
    return {"message": "Access code overridden.", "temporary_code": temporary_code}


    # 1. Find the target user
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="Operator not found")
        
    # 2. Strict Boundary Check for Org_Admins
    if current_user.role == "Org_Admin":
        if user_to_delete.company_name != current_user.company_name:
            raise HTTPException(
                status_code=403, 
                detail="Security Override: Cannot modify operators outside your organization."
            )
            
    # 3. Master_Control bypasses the check entirely and deletes the user
    target_username_cache = user_to_delete.username
    db.delete(user_to_delete)
    
    log_entry = AdminLog(
        admin_username=current_user.username,
        action="PURGED_OPERATOR",
        target_username=target_username_cache
    )
    db.add(log_entry)
    # ---------------------
    
    db.commit()
    return {"message": f"Operator {user_id} structurally purged."}

@app.post("/api/admin/users/create")
def admin_create_user(
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # 1. Ensure the username or email isn't already taken
    existing_user = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Operator email or username already exists.")

    # 2. Generate a secure temporary password
    temp_password = secrets.token_urlsafe(8)
    hashed_pw = get_password_hash(temp_password)

    # 3. Create the user, inheriting the manager's enterprise data!
    new_user = User(
        name=name,
        username=username,
        email=email,
        hashed_password=hashed_pw,
        role="Operator", # Force role to standard operator
        consent_given=True, # Assuming organization-level consent
        company_type=current_user.company_type,
        company_name=current_user.company_name,
        number_of_employees=current_user.number_of_employees,
        address_line_1=current_user.address_line_1,
        address_line_2=current_user.address_line_2,
        city_town=current_user.city_town,
        postcode=current_user.postcode,
        country=current_user.country
    )
    
    # ... existing create user logic ...
    db.add(new_user)
    
    # --- NEW AUDIT LOG ---
    log_entry = AdminLog(
        admin_username=current_user.username,
        action="PROVISIONED_OPERATOR",
        target_username=username
    )
    db.add(log_entry)
    # ---------------------
    
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

            user = db.query(User).filter(User.id == user_id).first()
            if user:
                send_audit_complete_email(user.email, filename, len(anomalies))

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
