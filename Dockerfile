FROM python:3.11-alpine

# Install ffmpeg + fonts
RUN apk add --no-cache ffmpeg fontconfig ttf-dejavu

WORKDIR /app
COPY main.py .

RUN pip install fastapi uvicorn pydantic

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
