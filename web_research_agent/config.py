import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# LLM Configuration
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")

# Output and Logs Directories
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Search Configuration
MAX_RESULTS = 5
