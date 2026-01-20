from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import subprocess
import uuid
import os

app = FastAPI()

# Video storage directory
VIDEO_DIR = "/tmp/videos"
os.makedirs(VIDEO_DIR, exist_ok=True)

# In-memory mapping of video IDs to file paths
VIDEO_MAP = {}

# Request schema
class VideoRequest(BaseModel):
    caption: str
    duration: int  # seconds (1-15)

@app.post("/post")
def create_video(data: VideoRequest):
    # Validate duration
    if data.duration <= 0 or data.duration > 15:
        raise HTTPException(status_code=400, detail="Duration must be 1–15 seconds")

    # Generate unique ID for the video
    video_id = str(uuid.uuid4())
    output = os.path.join(VIDEO_DIR, f"{video_id}.mp4")

    # Escape single quotes in caption for ffmpeg
    safe_caption = data.caption.replace("'", "\\'")

    # FFmpeg command
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
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")

    # Store mapping
    VIDEO_MAP[video_id] = output

    # Return the video ID
    return JSONResponse({"video_id": video_id, "message": "Video generated successfully"})

@app.get("/get/{video_id}")
def get_video(video_id: str):
    # Check if video exists
    if video_id not in VIDEO_MAP or not os.path.isfile(VIDEO_MAP[video_id]):
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(
        VIDEO_MAP[video_id],
        media_type="video/mp4",
        filename=f"{video_id}.mp4"
    )

# Optional: cleanup old files
import threading, time

def cleanup_old_videos(interval=3600):
    while True:
        for vid, path in list(VIDEO_MAP.items()):
            if os.path.isfile(path):
                # Remove videos older than 1 hour
                if time.time() - os.path.getmtime(path) > 3600:
                    os.remove(path)
                    VIDEO_MAP.pop(vid)
        time.sleep(interval)

# Start cleanup in background
threading.Thread(target=cleanup_old_videos, daemon=True).start()
