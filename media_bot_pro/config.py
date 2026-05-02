import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ApiThamaCAriyo123#")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
PUBLIC_BASE_URL = "http://127.0.0.1:8080"
DB_PATH = os.getenv("DB_PATH", "bot_admin.db")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
MAX_TELEGRAM_MB = int(os.getenv("MAX_TELEGRAM_MB", "1900"))
COOKIE_FILE = os.getenv("COOKIE_FILE","cookies.txt")
