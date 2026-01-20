from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import subprocess, uuid, os, threading, time

app = FastAPI()

VIDEO_DIR = "/tmp/videos"
os.makedirs(VIDEO_DIR, exist_ok=True)

VIDEO_MAP = {}

class VideoRequest(BaseModel):
    caption: str
    duration: int  # seconds

@app.post("/post")
def create_video(data: VideoRequest):
    if data.duration <= 0 or data.duration > 15:
        raise HTTPException(status_code=400, detail="Duration must be 1–15 seconds")

    video_id = str(uuid.uuid4())
    output = os.path.join(VIDEO_DIR, f"{video_id}.mp4")
    safe_caption = data.caption.replace("'", "\\'")

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s=1080x1920:d={data.duration}",
        "-vf",
        (
            f"drawtext=fontfile=/usr/share/fonts/TTF/DejaVuSans.ttf:"
            f"text='{safe_caption}':"
            "fontcolor=white:"
            "fontsize=64:"
            "line_spacing=10:"
            "x=(w-text_w)/2:"
            "y=(h-text_h)/2"
        ),
        output
    ]

    try:
        subprocess.run(cmd, check=True, timeout=30)  # safe timeout
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Video generation timed out")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {e}")

    VIDEO_MAP[video_id] = output
    return JSONResponse({"video_id": video_id, "message": "Video generated successfully"})

@app.get("/get/{video_id}")
def get_video(video_id: str):
    if video_id not in VIDEO_MAP or not os.path.isfile(VIDEO_MAP[video_id]):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(VIDEO_MAP[video_id], media_type="video/mp4", filename=f"{video_id}.mp4")

# Cleanup old videos every hour
def cleanup_old_videos():
    while True:
        for vid, path in list(VIDEO_MAP.items()):
            if os.path.isfile(path) and (time.time() - os.path.getmtime(path)) > 3600:
                os.remove(path)
                VIDEO_MAP.pop(vid)
        time.sleep(3600)

threading.Thread(target=cleanup_old_videos, daemon=True).start()

# Start server with Render/Koyeb port
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
