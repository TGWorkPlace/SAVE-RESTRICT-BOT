# ========================================================
# cantarella
# Don't Remove Credit 🥺
# Telegram Channel @cantarellabots
#
# Maintained & Updated by:
# Dhanpal Sharma
# GitHub: https://github.com/LastPerson07
# ========================================================

FROM mwader/static-ffmpeg:7.0 AS ffmpeg

FROM python:3.10.13-slim-bullseye

# Prevent Python from creating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Ensure logs are shown instantly
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy static ffmpeg binaries from the FFmpeg image
COPY --from=ffmpeg /ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg /ffprobe /usr/local/bin/ffprobe

# Verify ffmpeg and ffprobe installation
RUN ffmpeg -version && ffprobe -version

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p downloads temp_thumbs

# Start ONLY the bot
# Flask keep_alive server handles port binding
CMD ["python3", "bot.py"]

# ========================================================
# cantarella
# Don't Remove Credit
# Telegram Channel @cantarellabots
#
# Updated & Managed by:
# Dhanpal Sharma | https://github.com/LastPerson07
# ========================================================
