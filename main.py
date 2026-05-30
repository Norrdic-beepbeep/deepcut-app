import os
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="DeepCut AI Engine", version="1.0")

# Allow your frontend to talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # When ready for production, change to: ["https://deepcut-app.vercel.app"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SECURITY GATE ---
def security_scan(file_content, filename):
    return True 

# --- YOUR DEEP_CUT LOGIC ---
def process_file_logic(file_data, filename):
    # This is where your actual XML/Video parsing goes.
    # We return the number of anomalies so the UI updates correctly.
    
    # Mocking results for now so your UI has data to display
    return {
        "anomalies_found": 3,
        "details": "XML/Video processed successfully"
    }

@app.get("/", include_in_schema=False)
def health_check():
    return {"status": "DeepCut Engine is online"}

@app.post("/api/audit")
async def run_audit(file: UploadFile = File(...)):
    # 1. Security Check
    file_content = await file.read()
    if not security_scan(file_content, file.filename):
        raise HTTPException(status_code=400, detail="Security threat detected.")
    
    # 2. Reset file pointer
    await file.seek(0)
    
    # 3. Process the File
    result = process_file_logic(file_content, file.filename)
    
    # --- IMPORTANT: These keys match what index.html expects ---
    return {
        "status": "success",
        "filename": file.filename,
        "anomalies_found": result["anomalies_found"],
        "data": result["details"]
    }

if __name__ == "__main__":
    # Render-ready deployment settings
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
