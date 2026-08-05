import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Voice
WAKE_WORD = os.getenv("HARMONIX_WAKE_WORD", "harmonix")
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
SILENCE_DB = int(os.getenv("HARMONIX_SILENCE_DB", "-35"))
SILENCE_DURATION = float(os.getenv("HARMONIX_SILENCE_DURATION", "1.5"))
MAX_RECORD_SECONDS = int(os.getenv("HARMONIX_MAX_RECORD_SECONDS", "20"))
STT_MODEL = os.getenv("HARMONIX_STT_MODEL", "small")
STT_DEVICE = os.getenv("HARMONIX_STT_DEVICE", "auto")
STT_COMPUTE_TYPE = os.getenv("HARMONIX_STT_COMPUTE_TYPE", "auto")
TTS_VOICE = os.getenv("HARMONIX_TTS_VOICE", "af_heart")

# LLM
OMNIROUTE_URL = os.getenv("OMNIROUTE_URL", "http://localhost:20128/v1/chat/completions")
OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY", "")
OMNIROUTE_FAST_MODEL = os.getenv("OMNIROUTE_FAST_MODEL", "auto/best-fast")
OMNIROUTE_REASON_MODEL = os.getenv("OMNIROUTE_REASON_MODEL", "auto/best-reasoning")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "3"))

# Data
TIMEZONE = os.getenv("HARMONIX_TIMEZONE", "Asia/Manila")
TZ_OFFSET_HOURS = int(os.getenv("HARMONIX_TZ_OFFSET_HOURS", "8"))

# Notion
NOTION_TASKS_DB_ID = os.getenv("NOTION_TASKS_DB_ID", "1d798e489e2b80f4aa4ccf3a01993734")
NOTION_PROJECTS_DB_ID = os.getenv("NOTION_PROJECTS_DB_ID", "12f98e489e2b81adb67ccdc6f51f0989")

# Tools
ALLOWED_DIRS = [
    d.strip() for d in os.getenv("HARMONIX_ALLOWED_DIRS", "").split(";")
    if d.strip()
]
