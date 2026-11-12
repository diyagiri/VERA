"""Single-process, expiring in-memory sessions. No transcript persistence."""
import secrets, time, asyncio
from dataclasses import dataclass, field

@dataclass
class Session:
    consent: bool
    locale: str
    touched: float = field(default_factory=time.monotonic)
    profile: dict = field(default_factory=lambda: {'facts': {}, 'goals': [], 'priority': None})
    profile_version: int = 0
    plan: dict | None = None
    goal: str = ''
    provider_requests: int = 0
    tokens: int = 0
    reserved_tokens: int = 0
    retries: dict = field(default_factory=dict)
    recent: list = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

class Sessions:
    def __init__(self, settings):
        self.settings, self.items = settings, {}

    def purge(self):
        now = time.monotonic()
        for key in list(self.items):
            if now - self.items[key].touched > self.settings.ttl_seconds:
                del self.items[key]

    def create(self, consent, locale):
        self.purge()
        if len(self.items) >= self.settings.max_sessions:
            raise ValueError('Session capacity reached')
        sid = secrets.token_urlsafe(32)
        self.items[sid] = Session(consent, locale)
        return sid, self.items[sid]

    def get(self, sid):
        self.purge()
        session = self.items.get(sid)
        if session:
            session.touched = time.monotonic()
        return session

    def delete(self, sid):
        self.items.pop(sid, None)
