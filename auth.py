import json
from pathlib import Path
from httpx_oauth.oauth2 import OAuth2Token, BaseOAuth2

from web_server import WebServer


class OAuth:
    SCOPES = ['https://mail.google.com/']

    def __init__(self):
        self.token_path: Path | None = None
        self.client: BaseOAuth2 | None = None
        self.http_port: int = 12345
        self.token: OAuth2Token | None = None

    async def _login_from_file(self, token_path: Path):
        # read token from file
        with token_path.open() as f_in:
            token_dict = json.load(f_in)
        self.token = OAuth2Token(token_dict)

    async def _login_through_web(self, client: BaseOAuth2, http_port: int = 12345):
        callback_url = f"http://localhost:{http_port}/"

        url = await client.get_authorization_url(callback_url, scope=self.SCOPES)

        token_response = await WebServer.start_server_and_open_browser(url)
        self.token = await client.get_access_token(token_response["code"][0], callback_url)

    async def login(self, token_path: Path, client: BaseOAuth2, http_port: int = 12345):
        self.token_path = token_path
        self.client = client
        self.http_port = http_port

        if not token_path.is_file():
            await self._login_through_web(client, http_port)
        else:
            await self._login_from_file(token_path)

        # write token to file
        with token_path.open("w") as f_out:
            json.dump(self.token, f_out, indent=4)

        if self.token.is_expired():
            await self.refresh_token()

    async def refresh_token(self):
        self.token = await self.client.refresh_token(self.token["refresh_token"])


oauth = OAuth()
