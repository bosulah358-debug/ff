
import json
import os
from datetime import datetime, timedelta

class Database:
    def __init__(self, path="data.json"):
        self.path = path
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
        self.load()

    def load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                self.data = json.load(f)
            except json.JSONDecodeError:
                self.data = {}

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    # --- Basic Group Structure ---
    def ensure_group(self, chat_id):
        if str(chat_id) not in self.data:
            self.data[str(chat_id)] = {
                "owners": [],
                "admins": [],
                "vips": [],
                "banned": [],
                "muted": {},
                "restricted": [],
                "warnings": {},
                "messages": {},
                "custom_replies": {},
                "welcome_enabled": True,
                "locked": False,
                "bot_enabled": True,
                "message_history": [],
            }
            self.save()

    # --- Ownership & Permissions ---
    def is_owner(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        return user_id in self.data[chat_id]["owners"]

    def is_admin(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        return user_id in self.data[chat_id]["admins"]

    def is_vip(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        return user_id in self.data[chat_id]["vips"]

    def add_owner(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        if user_id not in self.data[chat_id]["owners"]:
            self.data[chat_id]["owners"].append(user_id)
            self.save()

    def add_admin(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        if user_id not in self.data[chat_id]["admins"]:
            self.data[chat_id]["admins"].append(user_id)
            self.save()

    def add_vip(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        if user_id not in self.data[chat_id]["vips"]:
            self.data[chat_id]["vips"].append(user_id)
            self.save()

    def remove_all_ranks(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        for rank in ["owners", "admins", "vips"]:
            if user_id in self.data[chat_id][rank]:
                self.data[chat_id][rank].remove(user_id)
        self.save()

    # --- Bans / Mutes / Restrictions ---
    def add_banned(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        if user_id not in self.data[chat_id]["banned"]:
            self.data[chat_id]["banned"].append(user_id)
            self.save()

    def remove_banned(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        if user_id in self.data[chat_id]["banned"]:
            self.data[chat_id]["banned"].remove(user_id)
            self.save()

    def add_muted(self, chat_id, user_id, until=None):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        self.data[chat_id]["muted"][str(user_id)] = {"until": until}
        self.save()

    def remove_muted(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        self.data[chat_id]["muted"].pop(str(user_id), None)
        self.save()

    def add_restricted(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        if user_id not in self.data[chat_id]["restricted"]:
            self.data[chat_id]["restricted"].append(user_id)
            self.save()

    def remove_restricted(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        if user_id in self.data[chat_id]["restricted"]:
            self.data[chat_id]["restricted"].remove(user_id)
            self.save()

    # --- Warnings ---
    def add_warning(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        warnings = self.data[chat_id]["warnings"].get(str(user_id), 0) + 1
        self.data[chat_id]["warnings"][str(user_id)] = warnings
        self.save()
        return warnings

    def get_warnings(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        return self.data[chat_id]["warnings"].get(str(user_id), 0)

    def reset_warnings(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        self.data[chat_id]["warnings"][str(user_id)] = 0
        self.save()

    # --- Messages Count ---
    def increment_message_count(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        self.data[chat_id]["messages"][str(user_id)] = (
            self.data[chat_id]["messages"].get(str(user_id), 0) + 1
        )
        self.save()

    def get_message_count(self, chat_id, user_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        return self.data[chat_id]["messages"].get(str(user_id), 0)

    def get_top_users(self, chat_id, limit=20):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        sorted_users = sorted(
            self.data[chat_id]["messages"].items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_users[:limit]

    # --- Custom Replies ---
    def add_custom_reply(self, chat_id, keyword, reply_data):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        self.data[chat_id]["custom_replies"][keyword] = reply_data
        self.save()

    def get_custom_reply(self, chat_id, keyword):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        return self.data[chat_id]["custom_replies"].get(keyword)

    # --- Global Replies ---
    def add_global_reply(self, keyword, reply_data):
        if "_global_replies" not in self.data:
            self.data["_global_replies"] = {}
        self.data["_global_replies"][keyword] = reply_data
        self.save()

    def get_global_reply(self, keyword):
        return self.data.get("_global_replies", {}).get(keyword)

    # --- Spam Detection ---
    def add_message_to_history(self, chat_id, user_id, message_text):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        now = datetime.now().isoformat()
        self.data[chat_id]["message_history"].append({
            "user_id": user_id,
            "message_text": message_text,
            "time": now,
        })
        # Keep only last 1000
        self.data[chat_id]["message_history"] = self.data[chat_id]["message_history"][-1000:]
        self.save()

    def get_recent_messages(self, chat_id, user_id, minutes=1):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        now = datetime.now()
        cutoff = now - timedelta(minutes=minutes)
        return [
            msg for msg in self.data[chat_id]["message_history"]
            if msg["user_id"] == user_id and datetime.fromisoformat(msg["time"]) > cutoff
        ]

    # --- Welcome / Group Settings ---
    def is_welcome_enabled(self, chat_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        return self.data[chat_id]["welcome_enabled"]

    def set_welcome_status(self, chat_id, status):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        self.data[chat_id]["welcome_enabled"] = status
        self.save()

    def is_group_locked(self, chat_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        return self.data[chat_id]["locked"]

    def set_group_lock(self, chat_id, status):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        self.data[chat_id]["locked"] = status
        self.save()

    def is_bot_enabled(self, chat_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        return self.data[chat_id]["bot_enabled"]

    def set_bot_status(self, chat_id, status):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        self.data[chat_id]["bot_enabled"] = status
        self.save()

    # --- Stats ---
    def get_total_users(self):
        users = set()
        for chat_id, chat_data in self.data.items():
            if not chat_id.startswith("_"):
                users.update(chat_data["messages"].keys())
        return len(users)

    def get_total_groups(self):
        return len([c for c in self.data.keys() if not c.startswith("_")])

    def get_stat(self, key):
        return self.data.get("_stats", {}).get(key, 0)

    def increment_stat(self, key):
        if "_stats" not in self.data:
            self.data["_stats"] = {}
        self.data["_stats"][key] = self.data["_stats"].get(key, 0) + 1
        self.save()

    # --- Clear Data ---
    def clear_all_data(self, chat_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        self.data[chat_id] = {
            "owners": [],
            "admins": [],
            "vips": [],
            "banned": [],
            "muted": {},
            "restricted": [],
            "warnings": {},
            "messages": {},
            "custom_replies": {},
            "welcome_enabled": True,
            "locked": False,
            "bot_enabled": True,
            "message_history": [],
        }
        self.save()

    def clear_banned(self, chat_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        self.data[chat_id]["banned"] = []
        self.save()

    def clear_muted(self, chat_id):
        chat_id = str(chat_id)
        self.ensure_group(chat_id)
        self.data[chat_id]["muted"] = {}
        self.save()
