import os
import time
import requests
import json
import openai
import uvicorn
import tempfile
import yt_dlp
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
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
# HELPER: DOWNLOAD AUDIO FROM LINK
# ---------------------------------------------------------
def download_audio_from_link(url: str):
    print(f"Attempting to extract audio from: {url}")
    temp_dir = tempfile.gettempdir()
    out_tmpl = os.path.join(temp_dir, 'downloaded_audio.%(ext)s')
    
    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'outtmpl': out_tmpl,
        'noplaylist': True,
        'quiet': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file_path = ydl.prepare_filename(info)
            
            with open(downloaded_file_path, 'rb') as f:
                file_content = f.read()
                
            os.remove(downloaded_file_path)
            return file_content, "downloaded_link.m4a"
            
    except Exception as e:
        print(f"yt-dlp error: {e}")
        return None, str(e)

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
        return {"anomalies": [], "error": str(e)}

# ---------------------------------------------------------
# ENGINE STAGE 2B: AUDIO/VIDEO DIALOGUE AUDITOR
# ---------------------------------------------------------
def detect_with_ai_audio(file_content, filename):
    if not client:
        return {"anomalies": [], "error": "AI Engine offline. Check API Key."}
    
    if len(file_content) > 25 * 1024 * 1024:
        return {"anomalies": [], "error": "File exceeds the 25MB limit for direct audio transcription."}

    try:
        print(f"Sending {filename} to Whisper for transcription...")
        transcript_response = client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, file_content)
        )
        transcript_text = transcript_response.text
        
        # X-RAY 1: Watch Whisper in your Render logs
        print(f"WHISPER HEARD: {transcript_text}")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a broadcast standards auditor. Analyze the following video transcript. Flag any profanity, offensive language, or explicit mentions of competitor brands (e.g., 'Pepsi', 'Burger King'). Return the result STRICTLY as JSON with this exact structure: {\"anomalies\": [{\"timecode\": \"Spoken Audio\", \"type\": \"<string>\", \"description\": \"<string>\"}], \"error\": null}. If perfectly clean, return an empty array for anomalies."
                },
                {
                    "role": "user", 
                    "content": f"Transcript:\n{transcript_text}"
                }
            ],
            response_format={ "type": "json_object" }
        )
        
        # X-RAY 2: Watch GPT's final decision
        ai_output = json.loads(response.choices[0].message.content)
        print(f"GPT OUTPUT: {json.dumps(ai_output)}")
        
        return ai_output

    except Exception as e:
        return {"anomalies": [], "error": f"Audio processing failed: {str(e)}"}

# ---------------------------------------------------------
# MASTER ROUTE: TRIGGER AUDIT PIPELINE
# ---------------------------------------------------------
# Notice how file and video_url are now explicitly optional (None)
@app.post("/api/audit")
@app.post("/api/audit/")
async def run_audit(file: UploadFile = File(None), video_url: str = Form(None)):
    
    # Pathway A: Process URL Link
    if video_url:
        print(f"Processing URL: {video_url}")
        file_content, filename_or_error = download_audio_from_link(video_url)
        if not file_content:
            return {"status": "error", "anomalies": [], "error": f"Failed to extract video: {filename_or_error}"}
        filename = "Linked_Video.m4a"
        
    # Pathway B: Process Uploaded File
    elif file:
        file_content = await file.read()
        filename = file.filename
        
    else:
        raise HTTPException(status_code=400, detail="Must provide either a file or a video URL.")

    filename_lower = filename.lower()
    
    # 1. Global Security Scan
    is_safe = security_scan(file_content, filename)
    if not is_safe:
        raise HTTPException(status_code=400, detail="Security scan failed.")
        
    # 2. Intelligent Routing based on File Extension
    if filename_lower.endswith(('.mp4', '.mp3', '.wav', '.m4a')):
        ai_analysis = detect_with_ai_audio(file_content, filename)
    else:
        ai_analysis = detect_with_ai_xml(file_content, filename)
    
    # 3. Standardized Output
    return {
        "status": "success",
        "filename": filename if file else video_url,
        "anomalies": ai_analysis.get('anomalies', []),
        "error": ai_analysis.get('error', None)
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
