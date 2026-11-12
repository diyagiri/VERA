"""Runtime configuration. No credential is included in any build artifact."""
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    api_key: str = ''
    model: str = ''
    origin: str = 'http://127.0.0.1:8000'
    secure_cookie: bool = False
    ttl_seconds: int = 3600
    max_sessions: int = 100
    max_requests_per_session: int = 30
    max_provider_requests: int = 200
    max_output_tokens: int = 1600
    max_total_tokens: int = 200000
    max_session_tokens: int = 100000
    wall_seconds: int = 150

    @property
    def online(self):
        return bool(self.api_key and self.model)

    @classmethod
    def from_env(cls):
        _load_dotenv()
        origin = os.getenv('VERA_ORIGIN', 'http://127.0.0.1:8000').rstrip('/')
        limits = {k: int(os.environ[e]) for k, e in {
            'max_requests_per_session': 'VERA_SESSION_REQUEST_LIMIT',
            'max_provider_requests': 'VERA_GLOBAL_REQUEST_LIMIT',
            'max_total_tokens': 'VERA_GLOBAL_TOKEN_LIMIT',
            'max_session_tokens': 'VERA_SESSION_TOKEN_LIMIT',
        }.items() if e in os.environ}
        if any(v < 1 for v in limits.values()):
            raise ValueError('Limits must be positive')
        return cls(api_key=os.getenv('ANTHROPIC_API_KEY', ''), model=os.getenv('VERA_MODEL', ''),
                   origin=origin, secure_cookie=origin.startswith('https://'), **limits)


def _load_dotenv(path=None):
    """Read KEY=VALUE lines from a local .env (git-ignored) without overriding real environment variables."""
    from pathlib import Path
    p = Path(path) if path else Path(__file__).resolve().parent / '.env'
    if not p.is_file():
        return
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
