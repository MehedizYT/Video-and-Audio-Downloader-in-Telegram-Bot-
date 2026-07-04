import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Optional Settings
# Leave empty if not required
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "") # e.g. "@MyChannel"
X_ACCOUNT = os.getenv("X_ACCOUNT", "") # e.g. "https://x.com/username"

# Star System Pricing (e.g., 50 Stars for Premium)
PREMIUM_PRICE = 50
