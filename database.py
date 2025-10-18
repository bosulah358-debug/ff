
import json
import os
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.data_file = "data.json"
        if not os.path.exists(self.data_file):
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False)

        # ضع هنا ID مالك البوت (من تيليجرام)
        self.owner_id = 1812457550

    def _read(self):
        with open(self.data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_total_users(self):
        data = self._read()
        users = set()
        for chat_id in data:
            users.update(data[chat_id].get("users", []))
        return len(users)

    def get_total_groups(self):
        data = self._read()
        return len(data)

    def get_stat(self, key):
        data = self._read()
        return sum(chat.get(key, 0) for chat in data.values())

    def increment_message_count(self, chat_id, user_id):
        data = self._read()
        chat = data.setdefault(str(chat_id), {})
        counts = chat.setdefault("message_counts", {})
        counts[str(user_id)] = counts.get(str(user_id), 0) + 1
        chat["users"] = list(counts.keys())
        self._write(data)

    def get_message_count(self, chat_id, user_id):
        data = self._read()
        return data.get(str(chat_id), {}).get("message_counts", {}).get(str(user_id), 0)

    # ✅ الدوال المفقودة
    def is_owner(self, user_id: int) -> bool:
        """يتأكد إذا المستخدم هو صاحب البوت"""
        return user_id == self.owner_id

    def get_custom_reply(self, chat_id, keyword):
        """يرجع رد مخصص حسب الكلمة"""
        data = self._read()
        chat = data.get(str(chat_id), {})
        replies = chat.get("custom_replies", {})
        return replies.get(keyword)

    def set_custom_reply(self, chat_id, keyword, reply_text):
        """يحفظ رد مخصص"""
        data = self._read()
        chat = data.setdefault(str(chat_id), {})
        replies = chat.setdefault("custom_replies", {})
        replies[keyword] = reply_text
        self._write(data)
