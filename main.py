from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI(title="DeepCut AI Engine", version="1.0")

# Allow your frontend (local or Vercel) to talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "DeepCut Engine is online"}

@app.post("/api/audit")
async def run_audit(file: UploadFile = File(...)):
    # 1. Log the receipt
    print(f"📥 Receiving file: {file.filename}")
    
    # 2. Add your "Audit" logic here
    # (Currently simulates processing time)
    is_video = file.filename.lower().endswith('.mp4')
    time.sleep(2) 
    
    # 3. Return the response to the frontend
    return {
        "status": "success",
        "filename": file.filename,
        "type": "video" if is_video else "metadata",
        "message": "Audit completed successfully.",
        "anomalies_found": 3
    }

if __name__ == "__main__":
    import uvicorn
    # Starts the server on port 8000
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

import os
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException

# Load the .env file
load_dotenv()

app = FastAPI(title="DeepCut AI Engine")

# Get the key from the environment
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")

@app.post("/api/audit")
async def run_audit(file: UploadFile = File(...)):
    if not VIRUSTOTAL_API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured.")
        
    # Use VIRUSTOTAL_API_KEY here...
    print(f"Using API Key: {VIRUSTOTAL_API_KEY[:4]}****") # Only print first 4 chars to be safe
    # ... rest of your code