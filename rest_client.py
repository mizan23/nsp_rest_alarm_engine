import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests
from config import ALARMS_URL, VERIFY_SSL
from token_manager import TokenManager


class RestClient:
    def __init__(self):
        self.token_manager = TokenManager()

    def fetch_alarms(self):
        token = self.token_manager.get_token()

        response = requests.get(
            ALARMS_URL,
            headers={"Authorization": f"Bearer {token}"},
            verify=VERIFY_SSL,
            timeout=15,
        )

        if response.status_code == 401:
            # force refresh
            self.token_manager._get_new_token()
            return self.fetch_alarms()

        response.raise_for_status()
        return response.json()