import os
import time
import requests
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Crucial to allow your frontend to talk to your Render backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, change to your specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "DeepCut Engine is online"}

def security_scan(file_content, filename):
    api_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not api_key:
        print("WARNING: No VirusTotal API key found. Skipping scan.")
        time.sleep(2) # Fake delay so the frontend animation looks natural during local testing
        return True

    url = "https://www.virustotal.com/api/v3/files"
    files = {"file": (filename, file_content)}
    headers = {"x-apikey": api_key}
    
    try:
        # Step 1: Send the file to VirusTotal
        response = requests.post(url, headers=headers, files=files)
        if response.status_code != 200:
            print("VirusTotal upload failed. Proceeding to avoid blocking pipeline.")
            return True # Fail open during development
            
        data = response.json()
        analysis_id = data["data"]["id"]
        
        # Step 2: The Polling Loop (This makes the backend actually wait for results)
        while True:
            print(f"Checking scan status for {filename}...")
            result_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
            result = requests.get(result_url, headers=headers).json()
            status = result["data"]["attributes"]["status"]
            
            if status == "completed":
                stats = result["data"]["attributes"]["stats"]
                print(f"Scan complete. Malicious engines flagged: {stats['malicious']}")
                # Returns True if safe (0 malicious flags), False if dangerous
                return stats["malicious"] == 0
                
            time.sleep(3) # Wait 3 seconds before pinging the API again
            
    except Exception as e:
        print(f"VirusTotal integration error: {e}")
        return True # Fail open

@app.post("/api/audit")
@app.post("/api/audit/")
async def run_audit(file: UploadFile = File(...)):
    # 1. Read the uploaded file into memory
    file_content = await file.read()
    print(f"Received file: {file.filename} ({len(file_content)} bytes)")
    
    # 2. Run the Real Security Scan
    is_safe = security_scan(file_content, file.filename)
    if not is_safe:
        raise HTTPException(status_code=400, detail="Security scan failed. Malicious file detected.")
        
    # 3. Simulate the AI processing time (we will build the real AI parser next)
    time.sleep(1.5)
    
    # 4. Return the exact JSON structure the Dashboard expects
    return {
        "status": "success",
        "filename": file.filename,
        "duration": "00:04:12:00",
        "total_clips": "142",
        "anomalies_found": 1,
        "message": "Continuity mismatch detected: Subject crosses the 180-degree line."
    }
