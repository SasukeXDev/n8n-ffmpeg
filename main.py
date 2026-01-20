from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import subprocess, uuid, os, threading, time

app = FastAPI()

VIDEO_DIR = "/tmp/videos"
os.makedirs(VIDEO_DIR, exist_ok=True)

VIDEO_MAP = {}  # video_id -> {"status": "processing"/"ready"/"error", "path": file_path}

class VideoRequest(BaseModel):
    caption: str
    duration: int  # 1-15 seconds

# Background FFmpeg worker
def generate_video(video_id: str, caption: str, duration: int):
    output = os.path.join(VIDEO_DIR, f"{video_id}.mp4")
    safe_caption = caption.replace("'", "\\'")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s=1080x1920:d={duration}",
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
        subprocess.run(cmd, check=True, timeout=30)
        VIDEO_MAP[video_id]["status"] = "ready"
        VIDEO_MAP[video_id]["path"] = output
    except Exception:
        VIDEO_MAP[video_id]["status"] = "error"

@app.post("/post")
def create_video(data: VideoRequest):
    if data.duration <= 0 or data.duration > 15:
        raise HTTPException(status_code=400, detail="Duration must be 1–15 seconds")

    video_id = str(uuid.uuid4())
    VIDEO_MAP[video_id] = {"status": "processing", "path": None}

    # Start FFmpeg in background
    threading.Thread(target=generate_video, args=(video_id, data.caption, data.duration), daemon=True).start()

    return JSONResponse({"video_id": video_id, "message": "Video is being generated"})

@app.get("/get/{video_id}")
def get_video(video_id: str):
    if video_id not in VIDEO_MAP:
        raise HTTPException(status_code=404, detail="Video ID not found")

    info = VIDEO_MAP[video_id]

    if info["status"] == "processing":
        return JSONResponse({"status": "processing", "message": "Video is not ready yet"})
    elif info["status"] == "error":
        raise HTTPException(status_code=500, detail="Video generation failed")
    elif info["status"] == "ready":
        path = info["path"]
        if path and os.path.isfile(path):
            return FileResponse(path, media_type="video/mp4", filename=f"{video_id}.mp4")
        else:
            raise HTTPException(status_code=404, detail="Video file not found")

# Optional: cleanup old videos
def cleanup_old_videos():
    while True:
        for vid, info in list(VIDEO_MAP.items()):
            path = info["path"]
            if path and os.path.isfile(path) and (time.time() - os.path.getmtime(path)) > 3600:
                os.remove(path)
                VIDEO_MAP.pop(vid)
        time.sleep(3600)

threading.Thread(target=cleanup_old_videos, daemon=True).start()

# Start server with dynamic port
if __name__ == "__main__":
    import uvicorn, os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
