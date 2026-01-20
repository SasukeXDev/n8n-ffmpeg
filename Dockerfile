FROM n8nio/n8n:latest

USER root

# Install ffmpeg (works on Koyeb)
RUN apk add --no-cache ffmpeg fontconfig ttf-dejavu

# Video working directory
RUN mkdir -p /data/videos && chmod -R 777 /data

USER node
