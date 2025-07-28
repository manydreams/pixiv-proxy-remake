import datetime
import bisect

from typing import Any

class Cache:
    default_timeout = 60 * 60 * 24 * 3 # 1 week in seconds
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.cache_timeout: list[tuple[float, str]] = []
        
    def clear_timeout(self) -> int:
        now = datetime.datetime.now().timestamp()
        cnt = 0
        
        if len(self.cache_timeout) == 0:
            return cnt
        
        while self.cache_timeout[-1][0] < now and len(self.cache_timeout) > 0:
            key = self.cache_timeout.pop()[1]
            del self.cache[key]
            cnt += 1
            
        return cnt
    
    def clear(self) -> None:
        self.cache.clear()
    
    def get(self, key: str) -> Any | None:
        self.clear_timeout()
        if key in self.cache.keys():
            return self.cache[key][0]
        return None

    def update(self, key: str, value: Any,
               timeout: int = default_timeout) -> None:
        self.clear_timeout()
        now = datetime.datetime.now().timestamp()
        if key in self.cache.keys():
            self.cache_timeout.remove((self.cache[key][1], key))
            self.cache[key] = (value, now + timeout)
            bisect.insort(self.cache_timeout, (now + timeout, key),
                          key=lambda x: -x[0])
            if len(self.cache) > self.max_size:
                key = self.cache_timeout.pop()[1]
                del self.cache[key]
        else:
            self.cache[key] = (value, now + timeout)
            bisect.insort(self.cache_timeout, (now + timeout, key),
                          key=lambda x: -x[0])
            if len(self.cache) > self.max_size:
                key = self.cache_timeout.pop()[1]
                del self.cache[key]
            
    def remove(self, key: str):
        if key in self.cache:
            self.cache_timeout.remove((self.cache[key][1], key))
            del self.cache[key]