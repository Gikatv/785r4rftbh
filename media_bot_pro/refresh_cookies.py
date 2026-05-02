import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")

TEST_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

def refresh_cookies():
    print("🔄 Refreshing cookies.txt from Firefox...")

    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--cookies-from-browser",
        "firefox",
        "--cookies",
        COOKIES_FILE,
        "--skip-download",
        TEST_URL,
    ]

    result = subprocess.run(cmd, text=True)

    if result.returncode == 0 and os.path.exists(COOKIES_FILE):
        print("✅ cookies.txt refreshed successfully")
        return True

    print("❌ cookies refresh failed")
    return False


if __name__ == "__main__":
    refresh_cookies()