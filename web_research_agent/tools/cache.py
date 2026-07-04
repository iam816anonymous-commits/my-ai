import json
import hashlib
import time
from pathlib import Path
from typing import Any, Optional
from web_research_agent.config import CACHE_DIR

class SmartCache:
    def __init__(self, expiration_seconds: int = 3600 * 24): # 24 hour default
        self.cache_dir = CACHE_DIR
        self.expiration = expiration_seconds

    def _get_hash(self, key: str) -> str:
        return hashlib.md5(key.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        h = self._get_hash(key)
        path = self.cache_dir / f"{h}.json"
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                data = json.load(f)

            if time.time() - data["timestamp"] > self.expiration:
                path.unlink() # Expired
                return None

            return data["value"]
        except:
            return None

    def set(self, key: str, value: Any):
        h = self._get_hash(key)
        path = self.cache_dir / f"{h}.json"
        try:
            with open(path, "w") as f:
                json.dump({
                    "timestamp": time.time(),
                    "value": value
                }, f)
        except:
            pass

# Global cache instance
cache = SmartCache()
