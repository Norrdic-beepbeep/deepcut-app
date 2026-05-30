import os
import time
import requests
import json
import openai
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI Client
try:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"Warning: OpenAI client failed to initialize. {e}")
    client = None

@app.get("/")
def read_root():
    return {"message": "DeepCut Engine is online"}

# ---------------------------------------------------------
# ENGINE STAGE 1: VIRUSTOTAL
# ---------------------------------------------------------
def security_scan(file_content, filename):
    api_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not api_key:
        return True

    url = "https://www.virustotal.com/api/v3/files"
    files = {"file": (filename, file_content)}
    headers = {"x-apikey": api_key}
    
    try:
        response = requests.post(url, headers=headers, files=files)
        if response.status_code != 200:
            return True 
            
        data = response.json()
        analysis_id = data["data"]["id"]
        
        while True:
            result_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
            result = requests.get(result_url, headers=headers).json()
            status = result["data"]["attributes"]["status"]
            
            if status == "completed":
                stats = result["data"]["attributes"]["stats"]
                return stats["malicious"] == 0
                
            time.sleep(3) 
            
    except Exception as e:
        return True 

# ---------------------------------------------------------
# ENGINE STAGE 2A: XML TIMELINE AUDITOR
# ---------------------------------------------------------
def detect_with_ai_xml(file_content, filename):
    if not client:
        return {"anomalies": [], "error": "AI Engine offline. Check API Key."}

    text_content = file_content.decode('utf-8', errors='ignore')[:10000] 

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a strict video compliance auditor. Analyze the XML timeline data. Look for copyrighted music (e.g., Drake, Hans Zimmer) and continuity notes/errors (e.g., jump cuts). Return the result STRICTLY as JSON with this exact structure: {\"anomalies\": [{\"timecode\": \"<string>\", \"type\": \"<string>\", \"description\": \"<string>\"}], \"error\": null}. If perfectly clean, return an empty array for anomalies."
                },
                {
                    "role": "user", 
                    "content": f"Filename: {filename}\nTimeline Data: {text_content}"
                }
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return {"anomalies": [], "error": str(e)}

# ---------------------------------------------------------
# ENGINE STAGE 2B: AUDIO/VIDEO DIALOGUE AUDITOR
# ---------------------------------------------------------
def detect_with_ai_audio(file_content, filename):
    if not client:
        return {"anomalies": [], "error": "AI Engine offline.
