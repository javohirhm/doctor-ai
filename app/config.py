import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Google Cloud / Vertex AI Configuration
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
ENDPOINT_ID = os.getenv("ENDPOINT_ID")
DEDICATED_ENDPOINT_DNS = os.getenv("DEDICATED_ENDPOINT_DNS")

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Database Configuration
DATABASE_FILE = os.getenv("DATABASE_FILE", "bot_data.db")

# Gemini Configuration (for follow-up suggestions)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Memory Configuration
MAX_MEMORY_MESSAGES = 14  # Number of messages to keep in short-term memory
