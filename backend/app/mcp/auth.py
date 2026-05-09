import base64
import hashlib
import json
import secrets
from typing import Dict, Optional
import httpx
from redis import Redis
from app.config import settings

redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

class MCPAuth:
    def __init__(self, session_id: str):
        self.session_id = session_id

    def generate_auth_url(self) -> str:
        if settings.MOCK_MCP:
            return f"http://localhost:3000?mock_auth=success&session_id={self.session_id}"
            
        code_verifier = secrets.token_urlsafe(64)
        redis_client.setex(f"pkce:{self.session_id}", 3600, code_verifier)
        
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        url = (
            "https://www.swiggy.com/oauth/authorize"
            "?response_type=code"
            f"&client_id={settings.SWIGGY_CLIENT_ID}"
            f"&redirect_uri={settings.SWIGGY_OAUTH_REDIRECT_URI}"
            f"&code_challenge={code_challenge}"
            "&code_challenge_method=S256"
            "&scope=instamart"
            f"&state={self.session_id}"
        )
        return url

    async def exchange_code(self, code: str, state: str) -> bool:
        if settings.MOCK_MCP:
            self._save_tokens("mock_access", "mock_refresh", 86400)
            return True

        code_verifier = redis_client.get(f"pkce:{state}")
        if not code_verifier:
            return False

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                settings.SWIGGY_OAUTH_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.SWIGGY_OAUTH_REDIRECT_URI,
                    "client_id": settings.SWIGGY_CLIENT_ID,
                    "code_verifier": code_verifier
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                self._save_tokens(data["access_token"], data["refresh_token"], data.get("expires_in", 86400))
                return True
            return False

    def get_valid_token(self) -> Optional[str]:
        if settings.MOCK_MCP:
            return "mock_token"
            
        tokens = self._get_tokens()
        if not tokens:
            return None
        return tokens.get("access_token")

    def _save_tokens(self, access: str, refresh: str, expires_in: int):
        data = {
            "access_token": access,
            "refresh_token": refresh
        }
        redis_client.setex(f"tokens:{self.session_id}", 86400, json.dumps(data))

    def _get_tokens(self) -> Optional[Dict[str, str]]:
        data = redis_client.get(f"tokens:{self.session_id}")
        return json.loads(data) if data else None
        
    def has_valid_session(self) -> bool:
        return self.get_valid_token() is not None
