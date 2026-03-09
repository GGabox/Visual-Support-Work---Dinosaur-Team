import time
import heapq


class MessageQueue:
    def __init__(self):
        self.queue = []

    def enqueue(self, text, priority, ttl):
        expires = time.time() + ttl
        # heap = menor número sale primero → usamos -priority
        heapq.heappush(self.queue, (-priority, expires, text))

    def get_next(self):
        now = time.time()

        while self.queue:
            priority, expires, text = heapq.heappop(self.queue)
            if now <= expires:
                return text
        return None

    def clear(self):
        self.queue.clear()