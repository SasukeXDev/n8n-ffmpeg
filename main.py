from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import uuid
import os

app = FastAPI()

VIDEO_DIR = "/tmp/videos"
os.makedirs(VIDEO_DIR, exist_ok=True)

class VideoRequest(BaseModel):
    caption: str
    duration: int  # seconds


@app.post("/post")
def create_video(data: VideoRequest):
    if data.duration <= 0 or data.duration > 15:
        raise HTTPException(status_code=400, detail="Duration must be 1–15 seconds")

    video_id = str(uuid.uuid4())
    output = f"{VIDEO_DIR}/{video_id}.mp4"

    safe_caption = data.caption.replace("'", "\\'")

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s=1080x1920:d={data.duration}",
        "-vf",
        (
            "drawtext=fontfile=/usr/share/fonts/TTF/DejaVuSans.ttf:"
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
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Video generation failed")

    return FileResponse(
        output,
        media_type="video/mp4",
        filename="short.mp4"
    )
