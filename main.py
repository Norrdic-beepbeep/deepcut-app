import os
import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="DeepCut Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SECURITY GATE ---
def security_scan(file_content, filename):
    # PLACEHOLDER: Insert your VirusTotal or ClamAV logic here
    # Return True if clean, False if virus found
    return True 

# Adding both routes prevents the redirect from ever needing to happen
@app.post("/api/audit")
@app.post("/api/audit/")
async def run_audit(file: UploadFile = File(...)):
    # ... your existing code ...
async def run_audit(file: UploadFile = File(...)):
    file_content = await file.read()
    
    # 1. Perform Scan
    if not security_scan(file_content, file.filename):
        # File is "deleted" because it is discarded from memory immediately
        return {
            "status": "danger", 
            "message": "Virus detected! File blocked and discarded.",
            "anomalies_found": 1
        }
    
    # 2. Process File
    # (Your parsing logic goes here)
    
    return {
        "status": "success", 
        "filename": file.filename,
        "anomalies_found": 0,
        "message": "Scan complete. Audit successful."
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
