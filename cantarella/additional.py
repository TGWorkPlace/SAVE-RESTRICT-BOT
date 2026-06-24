# Features extracted from Code 2 (VJ_Botz)
# Exact copy of functions - no modifications to core logic
# Integrated into Code 1 (LastPerson07 x cantarella) as additional features

import os
import re
import random
import subprocess
import asyncio
import aiohttp


# ========== CONFIGURATION SECTION ==========
# Add words to remove from filename (case-insensitive)
WORDS_TO_REMOVE = [
    "@ADL_DRAMA",
    "#ADL",
    "[MABLG]",
    "@DA_RIPS",
    "@Da_Rips",
    "DA_Rips",
    "ADL_DRAMA",
    "ADL",
    "MABLG",
    "[MABLG]."
    "[DnO]",
]

# Permanent thumbnail URL (leave empty string "" to disable)
PERMANENT_THUMBNAIL_URL = "https://imghost-bay.vercel.app/i/BQACAgUAAyEGAATP5GC2AAOVahXLZY7dZFBd2ZwVD0BwL2u9M3wAAsIeAAJXerFUehNK1jbpcKc7BA"

# Prefix and Suffix settings
FILE_PREFIX = os.environ.get("FILE_PREFIX", "").strip() or None
FILE_SUFFIX = os.environ.get("FILE_SUFFIX", "@BLRealm").strip() or None

# Metadata settings
METADATA_TITLE = os.environ.get("METADATA_TITLE", "{file_name}").strip() or None
METADATA_AUTHOR = os.environ.get("METADATA_AUTHOR", "@DramaShip").strip() or None
METADATA_ARTIST = os.environ.get("METADATA_ARTIST", "@DramaShip").strip() or None
METADATA_DESCRIPTION = os.environ.get("METADATA_DESCRIPTION", "uploaded by @Dramaship").strip() or None
METADATA_COMMENT = os.environ.get("METADATA_COMMENT", "@DramaShip").strip() or None

# Video/Audio/Subtitle Stream Title settings
METADATA_VIDEO_TITLE = os.environ.get("METADATA_VIDEO_TITLE", "@DramaShip").strip() or None
METADATA_AUDIO_TITLE = os.environ.get("METADATA_AUDIO_TITLE", "@DramaShip").strip() or None
METADATA_SUBTITLE_TITLE = os.environ.get("METADATA_SUBTITLE_TITLE", "@DramaShip").strip() or None
# =========================================


# Sleep settings storage - per user_id
CUSTOM_SLEEP = {}


def clean_filename(filename):
    """Remove unwanted words from filename"""
    if not filename:
        return filename

    name_parts = filename.rsplit('.', 1)
    name = name_parts[0]
    ext = name_parts[1] if len(name_parts) > 1 else ""

    for word in WORDS_TO_REMOVE:
        name = re.sub(re.escape(word), '', name, flags=re.IGNORECASE)

    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'[_\-\s]+', ' ', name).strip()

    return f"{name}.{ext}" if ext else name


def apply_prefix_suffix(filename):
    """Apply prefix and suffix to filename"""
    if not filename:
        return filename

    name_parts = filename.rsplit('.', 1)
    if len(name_parts) == 2:
        name, ext = name_parts
    else:
        name = filename
        ext = ""

    if FILE_PREFIX:
        name = f"{FILE_PREFIX}.{name}"

    if FILE_SUFFIX:
        name = f"{name}.{FILE_SUFFIX}"

    if ext:
        return f"{name}.{ext}"
    return name


async def smart_sleep(user_id: int):
    """Intelligent sleep with randomization between batch downloads.
    
    Picks a random value from the user's custom sleep list,
    adds ±20% jitter for natural behaviour.
    """
    base_sleep = CUSTOM_SLEEP.get(user_id, [3, 5, 7, 10])
    sleep_time = random.choice(base_sleep)
    jitter = random.uniform(-0.2, 0.2) * sleep_time
    final_sleep = sleep_time + jitter
    await asyncio.sleep(final_sleep)


async def download_thumbnail(url):
    """Download thumbnail from URL"""
    if not url:
        return None

    try:
        os.makedirs("temp_thumbs", exist_ok=True)
        thumb_path = f"temp_thumbs/thumb_{random.randint(1000, 9999)}.jpg"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    with open(thumb_path, 'wb') as f:
                        f.write(await response.read())
                    return thumb_path
    except Exception as e:
        print(f"Error downloading thumbnail: {e}")

    return None


async def add_metadata_with_ffmpeg(input_file, final_filename):
    """Add metadata to video/audio files using ffmpeg while preserving all streams and adding stream titles.

    If metadata variables are blank/None, original metadata is preserved.
    If metadata variables are set, they override original metadata.
    """

    if not any([METADATA_TITLE, METADATA_AUTHOR, METADATA_ARTIST, METADATA_DESCRIPTION,
                METADATA_COMMENT, METADATA_VIDEO_TITLE, METADATA_AUDIO_TITLE, METADATA_SUBTITLE_TITLE]):
        return input_file, False

    ext = input_file.rsplit('.', 1)[-1].lower()
    if ext not in ['mp4', 'mkv', 'avi', 'mov', 'flv', 'wmv', 'webm', 'mp3', 'flac', 'wav', 'm4a', 'aac', 'ogg']:
        return input_file, False

    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("FFmpeg/FFprobe not found. Skipping metadata addition.")
        return input_file, False

    try:
        dir_name = os.path.dirname(input_file)
        output_file = os.path.join(dir_name, f"temp_meta_{random.randint(1000, 9999)}.{ext}")

        # First, probe the file to get stream information
        probe_cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', input_file
        ]

        try:
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            import json
            probe_data = json.loads(probe_result.stdout)
            streams = probe_data.get('streams', [])
        except:
            streams = []

        cmd = [
            'ffmpeg', '-i', input_file,
            '-map', '0',
            '-c', 'copy',
            '-map_metadata', '0'  # Preserve all original metadata by default
        ]

        # Add/override global metadata only if set
        if METADATA_TITLE:
            title = METADATA_TITLE.format(file_name=final_filename)
            cmd.extend(['-metadata', f'title={title}'])
        if METADATA_AUTHOR:
            author = METADATA_AUTHOR.format(file_name=final_filename)
            cmd.extend(['-metadata', f'author={author}'])
        if METADATA_ARTIST:
            artist = METADATA_ARTIST.format(file_name=final_filename)
            cmd.extend(['-metadata', f'artist={artist}'])
        if METADATA_DESCRIPTION:
            description = METADATA_DESCRIPTION.format(file_name=final_filename)
            cmd.extend(['-metadata', f'description={description}'])
        if METADATA_COMMENT:
            comment = METADATA_COMMENT.format(file_name=final_filename)
            cmd.extend(['-metadata', f'comment={comment}'])

        # Add stream-specific metadata only if set (preserves original if not set)
        for idx, stream in enumerate(streams):
            codec_type = stream.get('codec_type', '').lower()

            if codec_type == 'video' and METADATA_VIDEO_TITLE:
                video_title = METADATA_VIDEO_TITLE.format(file_name=final_filename)
                video_idx = sum(1 for s in streams[:idx] if s.get('codec_type') == 'video')
                cmd.extend([f'-metadata:s:v:{video_idx}', f'title={video_title}'])

            elif codec_type == 'audio' and METADATA_AUDIO_TITLE:
                audio_title = METADATA_AUDIO_TITLE.format(file_name=final_filename)
                audio_idx = sum(1 for s in streams[:idx] if s.get('codec_type') == 'audio')
                cmd.extend([f'-metadata:s:a:{audio_idx}', f'title={audio_title}'])

            elif codec_type == 'subtitle' and METADATA_SUBTITLE_TITLE:
                subtitle_title = METADATA_SUBTITLE_TITLE.format(file_name=final_filename)
                subtitle_idx = sum(1 for s in streams[:idx] if s.get('codec_type') == 'subtitle')
                cmd.extend([f'-metadata:s:s:{subtitle_idx}', f'title={subtitle_title}'])

        cmd.extend(['-y', output_file])

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        process.wait()

        if process.returncode == 0 and os.path.exists(output_file):
            os.remove(input_file)
            os.rename(output_file, input_file)
            return input_file, True
        else:
            if os.path.exists(output_file):
                os.remove(output_file)
            raise Exception("FFmpeg failed")

    except Exception as e:
        print(f"Metadata error: {e}")
        if 'output_file' in locals() and os.path.exists(output_file):
            try:
                os.remove(output_file)
            except:
                pass
        return input_file, False
