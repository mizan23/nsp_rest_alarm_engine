import os
from dotenv import load_dotenv

load_dotenv()

NSP_HOST = os.getenv("NSP_HOST", "192.168.42.7")
NSP_PORT = os.getenv("NSP_PORT", "8443")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

VERIFY_SSL = os.getenv("VERIFY_SSL", "false").lower() == "true"
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 10))

DATABASE_URL = os.getenv("DATABASE_URL")
WHATSAPP_URL = os.getenv("WHATSAPP_URL")

BASE_URL = f"https://{NSP_HOST}:{NSP_PORT}"
AUTH_URL = f"{BASE_URL}/rest-gateway/rest/api/v1/auth/token"
ALARMS_URL = f"{BASE_URL}/oms1350/data/npr/alarms"