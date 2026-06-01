import os
import time
import requests
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import openai
import tempfile
import yt_dlp
import uvicorn
from datetime import datetime, timedelta
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status
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
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 24 hours token expiry

# Fix the Render Postgres URL format if necessary
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fallback.db")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

# UPDATED: Database Model now includes Name and Email
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
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# EMAIL LOGIC
# ---------------------------------------------------------
def send_confirmation_email(user_email: str, user_name: str, username: str):
    # Configure these in your Render Environment Variables
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME") 
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") 
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@deepcut.app")

    subject = "DeepCut Engine // Access Confirmed"
    body = f"""
    OPERATOR ACCESS CONFIRMED
    -------------------------
    Name: {user_name}
    Operator ID: {username}
    
    Welcome to the DeepCut Compliance Engine. Your credentials have been successfully encrypted and stored. 
    You may now access the system using either your Operator ID ({username}) or this email address.
    
    Proceed to terminal to initialize audits.
    """

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        # Fallback to console print if email isn't configured yet (great for testing)
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
        print(f"Confirmation email successfully sent to {user_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

# ---------------------------------------------------------
# AUTHENTICATION LOGIC
# ---------------------------------------------------------
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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

# ---------------------------------------------------------
# FASTAPI APP & ROUTES
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
except Exception as e:
    print(f"Warning: OpenAI client failed to initialize. {e}")
    client = None

# UPDATED: Registration endpoint now takes name and email, and triggers email sending
@app.post("/api/register")
def register_user(
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check if username or email already exists
    existing_user = db.query(User).filter(or_(User.username == username, User.email == email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    hashed_pwd = get_password_hash(password)
    new_user = User(name=name, username=username, email=email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    
    # Trigger the confirmation email
    send_confirmation_email(email, name, username)
    
    return {"message": "Operator registered successfully. Confirmation email sent."}

# UPDATED: Login now accepts either Username or Email
@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Look up user by EITHER username OR email
    user = db.query(User).filter(or_(User.username == form_data.username, User.email == form_data.username)).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username, email, or password")
    
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer", "username": user.username}

@app.get("/")
@app.head("/")
def read_root():
    return {"message": "DeepCut Secure Engine is online"}

# ---------------------------------------------------------
# AI & AUDIT FUNCTIONS (Unchanged)
# ---------------------------------------------------------
def download_audio_from_link(url: str):
    temp_dir = tempfile.gettempdir()
    out_tmpl = os.path.join(temp_dir, 'downloaded_audio.%(ext)s')
    ydl_opts = {'format': 'm4a/bestaudio/best', 'outtmpl': out_tmpl, 'noplaylist': True, 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file_path = ydl.prepare_filename(info)
            with open(downloaded_file_path, 'rb') as f:
                file_content = f.read()
            os.remove(downloaded_file_path)
            return file_content, "downloaded_link.m4a"
    except Exception as e:
        return None, str(e)

def security_scan(file_content, filename):
    api_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not api_key: return True
    url = "https://www.virustotal.com/api/v3/files"
    files = {"file": (filename, file_content)}
    headers = {"x-apikey": api_key}
    try:
        response = requests.post(url, headers=headers, files=files)
        if response.status_code != 200: return True 
        data = response.json()
        analysis_id = data["data"]["id"]
        while True:
            result_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
            result = requests.get(result_url, headers=headers).json()
            status = result["data"]["attributes"]["status"]
            if status == "completed":
                return result["data"]["attributes"]["stats"]["malicious"] == 0
            time.sleep(3) 
    except Exception:
        return True 

def detect_with_ai_xml(file_content, filename):
    if not client: return {"anomalies": [], "error": "AI Engine offline."}
    text_content = file_content.decode('utf-8', errors='ignore')[:10000] 
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a strict video compliance auditor. Analyze the XML timeline data. Look for copyrighted music and continuity notes/errors. Return the result STRICTLY as JSON: {\"anomalies\": [{\"timecode\": \"<string>\", \"type\": \"<string>\", \"description\": \"<string>\"}], \"error\": null}."},
                {"role": "user", "content": f"Filename: {filename}\nTimeline Data: {text_content}"}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"anomalies": [], "error": str(e)}

def detect_with_ai_audio(file_content, filename):
    if not client: return {"anomalies": [], "error": "AI Engine offline."}
    if len(file_content) > 25 * 1024 * 1024: return {"anomalies": [], "error": "File exceeds 25MB limit."}
    try:
        transcript_response = client.audio.transcriptions.create(model="whisper-1", file=(filename, file_content))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a broadcast standards auditor. Flag any profanity, offensive language, or explicit mentions of competitor brands. Return the result STRICTLY as JSON: {\"anomalies\": [{\"timecode\": \"Spoken Audio\", \"type\": \"<string>\", \"description\": \"<string>\"}], \"error\": null}."},
                {"role": "user", "content": f"Transcript:\n{transcript_response.text}"}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"anomalies": [], "error": f"Audio processing failed: {str(e)}"}

@app.post("/api/audit")
@app.post("/api/audit/")
async def run_audit(file: UploadFile = File(None), video_url: str = Form(None), current_user: User = Depends(get_current_user)):
    if video_url:
        file_content, filename_or_error = download_audio_from_link(video_url)
        if not file_content: return {"status": "error", "anomalies": [], "error": f"Failed: {filename_or_error}"}
        filename = "Linked_Video.m4a"
    elif file:
        file_content = await file.read()
        filename = file.filename
    else:
        raise HTTPException(status_code=400, detail="Must provide file or URL.")

    if not security_scan(file_content, filename):
        raise HTTPException(status_code=400, detail="Security scan failed.")
        
    if filename.lower().endswith(('.mp4', '.mp3', '.wav', '.m4a')):
        ai_analysis = detect_with_ai_audio(file_content, filename)
    else:
        ai_analysis = detect_with_ai_xml(file_content, filename)
    
    return {"status": "success", "filename": filename, "anomalies": ai_analysis.get('anomalies', []), "error": ai_analysis.get('error', None)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
