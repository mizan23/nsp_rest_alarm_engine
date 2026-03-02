import requests
import time
import jwt
from config import AUTH_URL, CLIENT_ID, CLIENT_SECRET, VERIFY_SSL

class TokenManager:
    def __init__(self):
        self.access_token = None
        self.expiry = 0

    def _get_new_token(self):
        response = requests.post(
            AUTH_URL,
            auth=(CLIENT_ID, CLIENT_SECRET),
            json={"grant_type": "client_credentials"},
            verify=VERIFY_SSL,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]

        decoded = jwt.decode(
            self.access_token,
            options={"verify_signature": False}
        )
        self.expiry = decoded["exp"]

    def get_token(self):
        if not self.access_token or time.time() > self.expiry - 600:
            self._get_new_token()
        return self.access_token