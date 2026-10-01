import os
import re
import json
import time
import asyncio
import requests
import urllib.parse
import subprocess

import google.generativeai as genai
import edge_tts

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6JkRrkpAf_Y6itKwlvJIo1ZADtJSUD1QXen-1mDkZSehA)
genai.configure(api_key=GEMINI_API_KEY.strip().strip('"').strip("'"))

os.makedirs("output/visuals", exist_ok=True)
os.makedirs("output/audio", exist_ok=True)
os.makedirs("output/final", exist_ok=True)

def mine_usa_trend():
    prompt = "Provide 1 viral, high-RPM topic for USA/UK audience in 'True Crime & Mysteries'. Return ONLY raw JSON: {\"topic\": \"...\"}"
    try:
        res = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
        clean = re.sub(r'```json\s*|\s*```', '', res.text).strip()
        return json.loads(clean)["topic"]
    except:
        return "Unexplained Mystery of Bermuda Triangle 2026"

def generate_script(topic):
    prompt = f"""Write YouTube script for target audience USA/UK. Topic: {topic}. 
    Return RAW JSON ONLY:
    {{
      "script": "In the cold winter of 1945...",
      "scenes": [
        "Dark mystery cinematic scene 16:9",
        "Eerie foggy night atmosphere 16:9",
        "Classified files on desk 16:9"
      ]
    }}"""
    res = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
    clean = re.sub(r'```json\s*|\s*```', '', res.text).strip()
    return json.loads(clean)

async def make_audio(text):
    out = "output/audio/voiceover.mp3"
    comm = edge_tts.Communicate(text, voice="en-US-AndrewMultilingualNeural", rate="-2%")
    await comm.save(out)
    return out

def make_visuals(scenes):
    paths = []
    for idx, sc in enumerate(scenes):
        encoded = urllib.parse.quote(f"{sc}, 3d render, cinematic, 16:9")
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1920&height=1080&nologo=true&seed={idx+77}"
        out = f"output/visuals/frame_{idx:03d}.jpg"
        try:
            res = requests.get(url, timeout=30)
            if res.status_code == 200:
                with open(out, "wb") as f:
                    f.write(res.content)
                paths.append(out)
        except Exception as e:
            print(f"Image error: {e}")
    return paths

def assemble_mp4(images, audio):
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprintwrappers=1:nokey=1", audio]).decode().strip())
    per_frame = dur / len(images)
    
    with open("output/visuals/input.txt", "w") as f:
        for img in images:
            f.write(f"file '{os.path.abspath(img)}'\n")
            f.write(f"duration {per_frame:.2f}\n")
        f.write(f"file '{os.path.abspath(images[-1])}'\n")
        
    out_video = "output/final/master_usa_video.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "output/visuals/input.txt",
        "-i", audio, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-s", "1920x1080", "-c:a", "aac", "-b:a", "192k", "-shortest", out_video
    ]
    subprocess.run(cmd, check=True)
    return out_video

async def run_pipeline():
    print("🚀 Running Cloud AURA-5 Engine...")
    topic = mine_usa_trend()
    data = generate_script(topic)
    audio = await make_audio(data["script"])
    imgs = make_visuals(data["scenes"])
    final = assemble_mp4(imgs, audio)
    print(f"✅ Master Video Generated at: {final}")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
