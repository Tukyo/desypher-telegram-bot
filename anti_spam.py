import time
from collections import defaultdict

class AntiSpam:
    def __init__(self, rate_limit=5, time_window=10):
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.user_messages = defaultdict(list)

    def is_spam(self, user_id):
        current_time = time.time()
        self.user_messages[user_id] = [msg_time for msg_time in self.user_messages[user_id] if current_time - msg_time < self.time_window]
        self.user_messages[user_id].append(current_time)
        return len(self.user_messages[user_id]) > self.rate_limit

    def time_to_wait(self, user_id):
        current_time = time.time()
        if len(self.user_messages[user_id]) < self.rate_limit:
            return 0
        return int(self.time_window - (current_time - self.user_messages[user_id][0]))
