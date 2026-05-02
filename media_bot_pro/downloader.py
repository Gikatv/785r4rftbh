import os
import uuid
import glob
import subprocess
import yt_dlp
from config import DOWNLOAD_DIR

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def detect_platform(url: str) -> str:
    u = (url or "").lower()

    if "tiktok.com" in u:
        return "TikTok"

    if "youtube.com" in u or "youtu.be" in u:
        return "YouTube"

    if "facebook.com" in u or "fb.watch" in u or "fb.com" in u:
        return "Facebook"

    return "Unknown"


def is_supported(url: str) -> bool:
    return detect_platform(url) in ["TikTok", "YouTube", "Facebook"]


def _duration_string(seconds):
    if not seconds:
        return "N/A"

    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)

    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fix_video(input_path: str) -> str:
    base, _ = os.path.splitext(input_path)
    output_path = base + "_fixed.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,

        "-vf", "scale='min(720,iw)':-2,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",

        "-c:a", "aac",
        "-b:a", "128k",

        "-movflags", "+faststart",

        output_path
    ]

    subprocess.run(cmd, check=True)

    if os.path.exists(output_path):
        return output_path

    return input_path


def download_media(url: str, quality: str = "best", media_type: str = "video") -> dict:
    if not is_supported(url):
        raise ValueError("Unsupported URL. Use TikTok, YouTube, or Facebook link.")

    file_id = str(uuid.uuid4())
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")
    media_type = (media_type or "video").lower()

    opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 60,
        "ignoreerrors": False,

        "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,

        "js_runtimes": {"node": {}},
        "remote_components": "ejs:github",

        "extractor_args": {
            "youtube": {
                "player_client": ["web"]
            },
            "facebook": {
                "formats": ["dash", "progressive"]
            }
        },
    }

    if media_type == "audio":
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        if quality and quality != "best":
            try:
                height = int(str(quality).replace("p", "").strip())
                opts.update({
                    "format": (
                        f"bestvideo*[height<={height}]+bestaudio/"
                        f"best[height<={height}]/best"
                    ),
                    "merge_output_format": "mp4",
                })
            except ValueError:
                opts.update({
                    "format": "bestvideo*+bestaudio/best",
                    "merge_output_format": "mp4",
                })
        else:
            opts.update({
                "format": "bestvideo*+bestaudio/best",
                "merge_output_format": "mp4",
            })

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

        if not info:
            raise RuntimeError("Download info not found")

        path = ydl.prepare_filename(info)

    if media_type == "audio":
        mp3 = os.path.splitext(path)[0] + ".mp3"
        if os.path.exists(mp3):
            path = mp3
    else:
        mp4 = os.path.splitext(path)[0] + ".mp4"
        if os.path.exists(mp4):
            path = mp4

    matches = glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_id}.*"))

    if not os.path.exists(path) and matches:
        path = matches[0]

    if not os.path.exists(path):
        raise FileNotFoundError("Downloaded file not found")

    if media_type == "video":
        try:
            fixed_path = fix_video(path)
            path = fixed_path
        except Exception as e:
            print("FFmpeg video fix failed:", e)

    duration = info.get("duration")
    size = os.path.getsize(path)

    return {
        "path": path,
        "platform": detect_platform(url),
        "title": info.get("title") or "",
        "duration": duration,
        "duration_string": _duration_string(duration),
        "ext": os.path.splitext(path)[1].lstrip("."),
        "size_bytes": size,
        "size_mb": round(size / (1024 * 1024), 2),
    }


def download_video(url: str, quality: str = "best") -> str:
    return download_media(url, quality, "video")["path"]


def download_audio(url: str) -> str:
    return download_media(url, "best", "audio")["path"]