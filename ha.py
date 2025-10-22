# ============================================
# bot.py  —  DIL / ديل Telegram Group Manager
# Python 3.11 — python-telegram-bot v20+
# ============================================

import sqlite3
import json
import time
import requests
import logging
from datetime import datetime, timedelta
from contextlib import closing

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from telegram.error import TelegramError

# ========= إعدادات أساسية =========
BOT_TOKEN = "8458158034:AAGbNwJH5Sn2FQqnkxIkZTvLWjglGUfcBaU"
OWNER_USERNAME = "@h_7_m"
OWNER_ID = 1812457550

DEFAULT_LANG = "ar"  # اللغة الافتراضية
BOT_NAME = {"ar": "ديل", "en": "DIL"}

# ========= تسجيل =========
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger("DIL")

# ========= قاعدة بيانات (SQLite داخل نفس الملف) =========
class DB:
    def __init__(self, path="database.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init()

    def _init(self):
        with self.conn:
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users(
              chat_id INTEGER, user_id INTEGER,
              messages INTEGER DEFAULT 0,
              warnings INTEGER DEFAULT 0,
              rank TEXT DEFAULT 'member',
              PRIMARY KEY(chat_id,user_id)
            )""")
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS settings(
              chat_id INTEGER PRIMARY KEY,
              lang TEXT DEFAULT 'ar',
              welcome_enabled INTEGER DEFAULT 1,
              bot_enabled INTEGER DEFAULT 1,
              lock_links INTEGER DEFAULT 0,
              lock_photos INTEGER DEFAULT 0,
              lock_videos INTEGER DEFAULT 0,
              lock_stickers INTEGER DEFAULT 0,
              group_locked INTEGER DEFAULT 0
            )""")
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS replies(
              chat_id INTEGER, keyword TEXT, data TEXT,
              is_global INTEGER DEFAULT 0,
              PRIMARY KEY(chat_id, keyword)
            )""")
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bans(
              chat_id INTEGER, user_id INTEGER,
              PRIMARY KEY(chat_id,user_id)
            )""")
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS mutes(
              chat_id INTEGER, user_id INTEGER, until_ts INTEGER,
              PRIMARY KEY(chat_id,user_id)
            )""")

    # ---- مستخدمين / إحصائيات
    def ensure_user(self, chat_id, user_id):
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO users(chat_id,user_id) VALUES(?,?)",
                (chat_id, user_id)
            )

    def add_msg(self, chat_id, user_id):
        with self.conn:
            self.conn.execute(
                "UPDATE users SET messages=messages+1 WHERE chat_id=? AND user_id=?",
                (chat_id, user_id)
            )

    def get_msg_count(self, chat_id, user_id):
        r = self.conn.execute(
            "SELECT messages FROM users WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        ).fetchone()
        return r[0] if r else 0

    def top_users(self, chat_id, limit=20):
        return self.conn.execute(
            "SELECT user_id, messages FROM users WHERE chat_id=? ORDER BY messages DESC LIMIT ?",
            (chat_id, limit)
        ).fetchall()

    def total_users(self):
        r = self.conn.execute("SELECT COUNT(DISTINCT user_id) FROM users").fetchone()
        return r[0] if r else 0

    # ---- لغة
    def get_lang(self, chat_id):
        r = self.conn.execute(
            "SELECT lang FROM settings WHERE chat_id=?", (chat_id,)
        ).fetchone()
        return r[0] if r else DEFAULT_LANG

    def set_lang(self, chat_id, lang):
        with self.conn:
            self.conn.execute(
                "INSERT INTO settings(chat_id,lang) VALUES(?,?) ON CONFLICT(chat_id) DO UPDATE SET lang=excluded.lang",
                (chat_id, lang)
            )

    # ---- إعدادات
    def set_flag(self, chat_id, key, value):
        with self.conn:
            self.conn.execute(
                f"INSERT INTO settings(chat_id,{key}) VALUES(?,?) "
                f"ON CONFLICT(chat_id) DO UPDATE SET {key}=excluded.{key}",
                (chat_id, int(bool(value)))
            )

    def get_flag(self, chat_id, key, default=0):
        r = self.conn.execute(
            f"SELECT {key} FROM settings WHERE chat_id=?", (chat_id,)
        ).fetchone()
        return (r[0] if r is not None and r[0] is not None else default) == 1

    # ---- رتب
    def set_rank(self, chat_id, user_id, rank):
        with self.conn:
            self.conn.execute(
                "UPDATE users SET rank=? WHERE chat_id=? AND user_id=?",
                (rank, chat_id, user_id)
            )

    def get_rank(self, chat_id, user_id):
        r = self.conn.execute(
            "SELECT rank FROM users WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        ).fetchone()
        return r[0] if r else "member"

    def clear_rank_group(self, chat_id, rank):
        with self.conn:
            self.conn.execute(
                "UPDATE users SET rank='member' WHERE chat_id=? AND rank=?",
                (chat_id, rank)
            )

    # ---- إنذارات
    def warn(self, chat_id, user_id):
        with self.conn:
            self.conn.execute(
                "UPDATE users SET warnings=warnings+1 WHERE chat_id=? AND user_id=?",
                (chat_id, user_id)
            )
        r = self.conn.execute(
            "SELECT warnings FROM users WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        ).fetchone()
        return r[0] if r else 0

    def clear_warnings(self, chat_id, user_id):
        with self.conn:
            self.conn.execute(
                "UPDATE users SET warnings=0 WHERE chat_id=? AND user_id=?",
                (chat_id, user_id)
            )

    def get_warnings(self, chat_id, user_id):
        r = self.conn.execute(
            "SELECT warnings FROM users WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        ).fetchone()
        return r[0] if r else 0

    # ---- حظر/كتم/تقييد
    def ban(self, chat_id, user_id):
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO bans(chat_id,user_id) VALUES(?,?)",
                (chat_id, user_id)
            )

    def unban(self, chat_id, user_id):
        with self.conn:
            self.conn.execute(
                "DELETE FROM bans WHERE chat_id=? AND user_id=?",
                (chat_id, user_id)
            )

    def mute(self, chat_id, user_id, minutes=None, hours=None):
        until_ts = 0
        if minutes:
            until_ts = int(time.time() + minutes * 60)
        if hours:
            until_ts = int(time.time() + hours * 3600)
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO mutes(chat_id,user_id,until_ts) VALUES(?,?,?)",
                (chat_id, user_id, until_ts)
            )

    def unmute(self, chat_id, user_id):
        with self.conn:
            self.conn.execute(
                "DELETE FROM mutes WHERE chat_id=? AND user_id=?",
                (chat_id, user_id)
            )

    # ---- ردود
    def set_reply(self, chat_id, keyword, data, is_global=False):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO replies(chat_id,keyword,data,is_global) VALUES(?,?,?,?)",
                (chat_id, keyword, json.dumps(data, ensure_ascii=False), int(is_global))
            )

    def del_reply(self, chat_id, keyword):
        with self.conn:
            self.conn.execute(
                "DELETE FROM replies WHERE chat_id=? AND keyword=?", (chat_id, keyword)
            )

    def get_reply(self, chat_id, keyword):
        r = self.conn.execute(
            "SELECT data FROM replies WHERE (chat_id=? OR is_global=1) AND keyword=?",
            (chat_id, keyword)
        ).fetchone()
        return json.loads(r[0]) if r else None

db = DB()

# ========= نصوص =========
T = {
    "ar": {
        "start": f"• أهلاً بك عزيزي انا بوت اسمي {BOT_NAME['ar']}\n• اختصاص البوت حماية المجموعات\n• اضف البوت الى مجموعتك .\n• ارفعه ادمن مشرف\n• ارفعه مشرف وارسل تفعيل ليتم تفعيل المجموعة .\n• مطور البوت ↤︎ {OWNER_USERNAME}",
        "add_me": "أضفني لمجموعتك",
        "change_lang": "تغيير اللغة",
        "lang_changed": "تم تغيير اللغة",
        "only_admin": "هذا الأمر للمشرفين فقط",
        "enabled_welcome": "تم تفعيل الترحيب",
        "disabled_welcome": "تم تعطيل الترحيب",
        "enabled_bot": "تم تفعيل الحماية",
        "disabled_bot": "تم تعطيل الحماية",
        "locked_links": "تم قفل الروابط",
        "unlocked_links": "تم فتح الروابط",
        "locked_photos": "تم قفل الصور",
        "unlocked_photos": "تم فتح الصور",
        "locked_videos": "تم قفل الفيديوهات",
        "unlocked_videos": "تم فتح الفيديوهات",
        "locked_stickers": "تم قفل الملصقات",
        "unlocked_stickers": "تم فتح الملصقات",
        "group_locked": "تم قفل القروب",
        "group_unlocked": "تم فتح القروب",
        "crypto_title": "اسعار العملات الرقمية مقابل USDT :",
        "crypto_fail": "تعذر جلب الأسعار حالياً",
        "no_stats": "لا توجد إحصائيات بعد",
        "info_format": "• ID : {id}\n• USE : {user}\n• STE : {rank}\n• MSG : {msg}",
        "ranks_title": "عرض الرتب:",
    },
    "en": {
        "start": f"Hello, I am {BOT_NAME['en']}\nI protect and manage groups.\nAdd me to your group.\nPromote me to admin.\nThen send 'enable' to activate.\nDeveloper ↤︎ {OWNER_USERNAME}",
        "add_me": "Add me to your group",
        "change_lang": "Change Language",
        "lang_changed": "Language changed",
        "only_admin": "This command is for admins only",
        "enabled_welcome": "Welcome enabled",
        "disabled_welcome": "Welcome disabled",
        "enabled_bot": "Protection enabled",
        "disabled_bot": "Protection disabled",
        "locked_links": "Links locked",
        "unlocked_links": "Links unlocked",
        "locked_photos": "Photos locked",
        "unlocked_photos": "Photos unlocked",
        "locked_videos": "Videos locked",
        "unlocked_videos": "Videos unlocked",
        "locked_stickers": "Stickers locked",
        "unlocked_stickers": "Stickers unlocked",
        "group_locked": "Group locked",
        "group_unlocked": "Group unlocked",
        "crypto_title": "Crypto prices vs USDT:",
        "crypto_fail": "Failed to fetch prices",
        "no_stats": "No stats yet",
        "info_format": "• ID : {id}\n• USER : {user}\n• RANK : {rank}\n• MSG : {msg}",
        "ranks_title": "Ranks:",
    }
}

def tr(chat_id, key):
    lang = db.get_lang(chat_id)
    return T[lang][key]

# ========= صلاحيات محلية =========
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    chat = update.effective_chat
    if not chat: return False
    uid = user_id or update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat.id, uid)
        return member.status in ("creator", "administrator")
    except:
        return False

# ========= تغيير اسم ووصف البوت حسب اللغة وعدد المستخدمين =========
async def update_bot_profile(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    lang = db.get_lang(chat_id)
    try:
        await context.bot.set_my_name(BOT_NAME[lang])
    except Exception:
        pass
    try:
        total = db.total_users()
        desc = f"{total} monthly users" if lang == "en" else f"{total} مستخدم شهري"
        await context.bot.set_my_description(desc)
    except Exception:
        pass

# ========= /start في الخاص =========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    chat_id = update.effective_chat.id
    # اللغة الافتراضية عربية
    db.set_lang(chat_id, "ar")
    # رسالة ترحيب + زر أضفني + زر تغيير اللغة
    keyboard = [
        [InlineKeyboardButton(T["ar"]["add_me"], url=f"https://t.me/{context.bot.username}?startgroup=true")],
        [InlineKeyboardButton(T["ar"]["change_lang"], callback_data="lang_toggle")]
    ]
    await update.message.reply_text(T["ar"]["start"], reply_markup=InlineKeyboardMarkup(keyboard))

# ========= واجهة الأوامر المختصرة (بالرسالة) =========
async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    db.ensure_user(chat.id, user.id)
    total = db.total_users()
    name = BOT_NAME[db.get_lang(chat.id)]
    head = f"{name} — عدد المستخدمين: {total}" if db.get_lang(chat.id)=="ar" else f"{name} — Users: {total}"
    # أزرار عامة
    keyboard = [
        [InlineKeyboardButton(tr(chat.id, "add_me"), url=f"https://t.me/{context.bot.username}?startgroup=true")],
        [InlineKeyboardButton(tr(chat.id, "change_lang"), callback_data="lang_toggle")],
        [InlineKeyboardButton("الصرف", callback_data="currencies")]
    ]
    await update.message.reply_text(head, reply_markup=InlineKeyboardMarkup(keyboard))

# ========= تبديل اللغة =========
async def cb_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    cur = db.get_lang(chat_id)
    new_lang = "en" if cur == "ar" else "ar"
    db.set_lang(chat_id, new_lang)
    await update_bot_profile(context, chat_id)
    await q.edit_message_text(T[new_lang]["lang_changed"])

# ========= أسعار العملات =========
COINGECKO = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,litecoin,toncoin&vs_currencies=usd&include_24hr_change=true"

async def cb_currencies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    try:
        data = requests.get(COINGECKO, timeout=10).json()
        btc = data["bitcoin"]; ltc = data["litecoin"]; ton = data["toncoin"]
        title = tr(chat_id, "crypto_title")
        msg = (
            f"{title}\n\n"
            f"BTC : {btc['usd']:.2f}$ [{btc['usd_24h_change']:+.2f}%]\n"
            f"LTC : {ltc['usd']:.2f}$ [{ltc['usd_24h_change']:+.2f}%]\n"
            f"TON : {ton['usd']:.2f}$ [{ton['usd_24h_change']:+.2f}%]"
        )
        await q.edit_message_text(msg)
    except Exception:
        await q.edit_message_text(tr(chat_id, "crypto_fail"))

# ========= حماية الرسائل (قفل الروابط/الصور/الفيديو/الملصقات) =========
def contains_link(text: str) -> bool:
    if not text: return False
    t = text.lower()
    return ("http://" in t) or ("https://" in t) or ("t.me/" in t)

async def protection_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    chat_id = update.effective_chat.id
    msg = update.message
    if not msg: return
    # إذا البوت معطّل
    if not db.get_flag(chat_id, "bot_enabled", default=1): return
    # إن كان القروب مقفول بالكامل
    if db.get_flag(chat_id, "group_locked", default=0):
        if not await is_admin(update, context, msg.from_user.id):
            try: await msg.delete()
            except: pass
            return
    # روابط
    if db.get_flag(chat_id, "lock_links") and msg.text and not await is_admin(update, context, msg.from_user.id):
        if contains_link(msg.text):
            try: await msg.delete()
            except: pass
            return
    # صور
    if db.get_flag(chat_id, "lock_photos") and (msg.photo or (msg.document and getattr(msg.document, "mime_type", "").startswith("image/"))):
        if not await is_admin(update, context, msg.from_user.id):
            try: await msg.delete()
            except: pass
            return
    # فيديو
    if db.get_flag(chat_id, "lock_videos") and (msg.video or (msg.document and getattr(msg.document, "mime_type", "").startswith("video/"))):
        if not await is_admin(update, context, msg.from_user.id):
            try: await msg.delete()
            except: pass
            return
    # ملصقات
    if db.get_flag(chat_id, "lock_stickers") and msg.sticker:
        if not await is_admin(update, context, msg.from_user.id):
            try: await msg.delete()
            except: pass
            return
    # إحصاء الرسائل
    db.ensure_user(chat_id, msg.from_user.id)
    db.add_msg(chat_id, msg.from_user.id)

# ========= أوامر عربية/إنجليزية (Mapping) =========
# ملاحظة: كثير من الأوامر لها صيغة "بالرد" — نطبّق بالرد على رسالة
def user_from_reply(update: Update):
    if update.message and update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    return None

# ---- إدارة الرتب
async def set_rank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, rank: str):
    if update.effective_chat.type == "private": return
    chat_id = update.effective_chat.id
    if not await is_admin(update, context):
        await update.message.reply_text(tr(chat_id, "only_admin")); return
    u = user_from_reply(update)
    if not u:
        await update.message.reply_text("الرد على العضو") if db.get_lang(chat_id)=="ar" else await update.message.reply_text("Reply to a user")
        return
    db.ensure_user(chat_id, u.id)
    db.set_rank(chat_id, u.id, rank)
    await update.message.reply_text(f"تم رفعه {rank}") if db.get_lang(chat_id)=="ar" else await update.message.reply_text(f"Promoted to {rank}")

async def clear_rank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, rank: str):
    if update.effective_chat.type == "private": return
    chat_id = update.effective_chat.id
    if not await is_admin(update, context):
        await update.message.reply_text(tr(chat_id, "only_admin")); return
    db.clear_rank_group(chat_id, rank)
    await update.message.reply_text("تم المسح") if db.get_lang(chat_id)=="ar" else await update.message.reply_text("Cleared")

# ---- حظر/طرد/تقييد/كتم
async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    chat_id = update.effective_chat.id
    if not await is_admin(update, context):
        await update.message.reply_text(tr(chat_id, "only_admin")); return
    u = user_from_reply(update)
    if not u: await update.message.reply_text("الرد على العضو"); return
    try:
        await context.bot.ban_chat_member(chat_id, u.id)
        db.ban(chat_id, u.id)
        await update.message.reply_text("تم الحظر")
    except TelegramError as e:
        await update.message.reply_text(str(e))

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    chat_id = update.effective_chat.id
    if not await is_admin(update, context):
        await update.message.reply_text(tr(chat_id, "only_admin")); return
    u = user_from_reply(update)
    if not u: await update.message.reply_text("الرد على العضو"); return
    try:
        await context.bot.unban_chat_member(chat_id, u.id)
        db.unban(chat_id, u.id)
        await update.message.reply_text("تم فك الحظر")
    except TelegramError as e:
        await update.message.reply_text(str(e))

async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    chat_id = update.effective_chat.id
    if not await is_admin(update, context):
        await update.message.reply_text(tr(chat_id, "only_admin")); return
    u = user_from_reply(update)
    if not u: await update.message.reply_text("الرد على العضو"); return
    try:
        await context.bot.ban_chat_member(chat_id, u.id)
        await context.bot.unban_chat_member(chat_id, u.id)
        await update.message.reply_text("تم الطرد")
    except TelegramError as e:
        await update.message.reply_text(str(e))

async def restrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, mute_only=False):
    if update.effective_chat.type == "private": return
    chat_id = update.effective_chat.id
    if not await is_admin(update, context):
        await update.message.reply_text(tr(chat_id, "only_admin")); return
    u = user_from_reply(update)
    if not u: await update.message.reply_text("الرد على العضو"); return
    perms = ChatPermissions(can_send_messages=False) if mute_only else ChatPermissions(
        can_send_messages=False, can_send_media_messages=False, can_send_polls=False,
        can_send_other_messages=False, can_add_web_page_previews=False
    )
    try:
        await context.bot.restrict_chat_member(chat_id, u.id, perms)
        if mute_only: db.mute(chat_id, u.id)
        await update.message.reply_text("تم التقييد" if not mute_only else "تم الكتم")
    except TelegramError as e:
        await update.message.reply_text(str(e))

async def unrestrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, unmute=False):
    if update.effective_chat.type == "private": return
    chat_id = update.effective_chat.id
    if not await is_admin(update, context):
        await update.message.reply_text(tr(chat_id, "only_admin")); return
    u = user_from_reply(update)
    if not u: await update.message.reply_text("الرد على العضو"); return
    perms = ChatPermissions(
        can_send_messages=True, can_send_media_messages=True, can_send_polls=True,
        can_send_other_messages=True, can_add_web_page_previews=True,
        can_change_info=True, can_invite_users=True, can_pin_messages=True
    )
    try:
        await context.bot.restrict_chat_member(chat_id, u.id, perms)
        if unmute: db.unmute(chat_id, u.id)
        await update.message.reply_text("تم فك التقييد" if not unmute else "تم فك الكتم")
    except TelegramError as e:
        await update.message.reply_text(str(e))

# ---- إنذارات
async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    chat_id = update.effective_chat.id
    if not await is_admin(update, context):
        await update.message.reply_text(tr(chat_id, "only_admin")); return
    u = user_from_reply(update)
    if not u: await update.message.reply_text("الرد على العضو"); return
    db.ensure_user(chat_id, u.id)
    w = db.warn(chat_id, u.id)
    await update.message.reply_text(f"إنذار رقم {w}")

async def warn_clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    chat_id = update.effective_chat.id
    if not await is_admin(update, context):
        await update.message.reply_text(tr(chat_id, "only_admin")); return
    u = user_from_reply(update)
    if not u: await update.message.reply_text("الرد على العضو"); return
    db.clear_warnings(chat_id, u.id)
    await update.message.reply_text("تم حذف الإنذارات")

async def warn_show_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    u = user_from_reply(update) or update.effective_user
    w = db.get_warnings(chat_id, u.id)
    await update.message.reply_text(f"عدد إنذاراته: {w}")

# ---- مسح
async def clear_last_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text(tr(update.effective_chat.id, "only_admin")); return
    try:
        count = int(context.args[0]) if context.args else 1
        chat_id = update.effective_chat.id
        mid = update.message.message_id
        try: await context.bot.delete_message(chat_id, mid)
        except: pass
        for i in range(1, min(count+1, 101)):
            try: await context.bot.delete_message(chat_id, mid - i)
            except: pass
    except:
        pass

async def delete_reply_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text(tr(update.effective_chat.id, "only_admin")); return
    if not update.message.reply_to_message:
        await update.message.reply_text("الرد على الرسالة"); return
    try:
        await update.message.reply_to_message.delete()
        await update.message.reply_text("تم المسح")
    except:
        await update.message.reply_text("فشل المسح")

# ---- ترحيب
async def enable_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_flag(update.effective_chat.id, "welcome_enabled", True)
    await update.message.reply_text(tr(update.effective_chat.id, "enabled_welcome"))

async def disable_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_flag(update.effective_chat.id, "welcome_enabled", False)
    await update.message.reply_text(tr(update.effective_chat.id, "disabled_welcome"))

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not db.get_flag(chat_id, "welcome_enabled", default=1): return
    for m in update.message.new_chat_members:
        username = f"@{m.username}" if m.username else "لا يوجد" if db.get_lang(chat_id)=="ar" else "N/A"
        txt = f"مرحباً {m.first_name} ({username})" if db.get_lang(chat_id)=="ar" else f"Welcome {m.first_name} ({username})"
        await update.message.reply_text(txt)

# ---- حماية عامة
async def enable_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_flag(update.effective_chat.id, "bot_enabled", True)
    await update.message.reply_text(tr(update.effective_chat.id, "enabled_bot"))

async def disable_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_flag(update.effective_chat.id, "bot_enabled", False)
    await update.message.reply_text(tr(update.effective_chat.id, "disabled_bot"))

async def lock_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_flag(update.effective_chat.id, "group_locked", True)
    await update.message.reply_text(tr(update.effective_chat.id, "group_locked"))

async def unlock_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_flag(update.effective_chat.id, "group_locked", False)
    await update.message.reply_text(tr(update.effective_chat.id, "group_unlocked"))

async def lock_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, on: bool):
    if not await is_admin(update, context):
        await update.message.reply_text(tr(update.effective_chat.id, "only_admin")); return
    db.set_flag(update.effective_chat.id, key, on)
    key_msg = {
        ("lock_links", True): "locked_links", ("lock_links", False): "unlocked_links",
        ("lock_photos", True): "locked_photos", ("lock_photos", False): "unlocked_photos",
        ("lock_videos", True): "locked_videos", ("lock_videos", False): "unlocked_videos",
        ("lock_stickers", True): "locked_stickers", ("lock_stickers", False): "unlocked_stickers",
    }[(key, on)]
    await update.message.reply_text(tr(update.effective_chat.id, key_msg))

# ---- كشف / info
def rank_label(lang, r):
    ar = {"owner":"مالك","creator":"منشئ","manager":"مدير","admin":"ادمن","vip":"مميز","member":"عضو"}
    en = {"owner":"Owner","creator":"Creator","manager":"Manager","admin":"Admin","vip":"VIP","member":"Member"}
    return (ar if lang=="ar" else en).get(r, r)

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    u = user_from_reply(update) or update.effective_user
    db.ensure_user(chat_id, u.id)
    rank = rank_label(db.get_lang(chat_id), db.get_rank(chat_id, u.id))
    username = f"@{u.username}" if u.username else ("لا يوجد" if db.get_lang(chat_id)=="ar" else "N/A")
    msgc = db.get_msg_count(chat_id, u.id)
    fmt = tr(chat_id, "info_format")
    await update.message.reply_text(fmt.format(id=u.id, user=username, rank=rank, msg=msgc), parse_mode="Markdown")

# ---- توب
async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rows = db.top_users(chat_id, 20)
    if not rows:
        await update.message.reply_text(tr(chat_id, "no_stats")); return
    title = "عرض التوب - أكثر 20 عضو تفاعلاً:\n" if db.get_lang(chat_id)=="ar" else "Top 20 most active members:\n"
    out = [title, ""]
    for i,(uid,cnt) in enumerate(rows, 1):
        out.append(f"{i}. {uid} - {cnt}")
    await update.message.reply_text("\n".join(out))

# ========= الراوتر: تطابق الأوامر العربية/الإنجليزية =========
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # أوامر عامة
    if text in ("الأوامر","commands"):
        await show_commands(update, context); return
    if text in ("كشف","info"):
        await info_cmd(update, context); return
    if text == "الصرف" or text.lower()=="exchange":
        # نحول للزر حتى لا نحذف رسالة الأزرار السابقة
        try:
            data = requests.get(COINGECKO, timeout=10).json()
            btc = data["bitcoin"]; ltc = data["litecoin"]; ton = data["toncoin"]
            title = tr(chat_id, "crypto_title")
            msg = (
                f"{title}\n\n"
                f"BTC : {btc['usd']:.2f}$ [{btc['usd_24h_change']:+.2f}%]\n"
                f"LTC : {ltc['usd']:.2f}$ [{ltc['usd_24h_change']:+.2f}%]\n"
                f"TON : {ton['usd']:.2f}$ [{ton['usd_24h_change']:+.2f}%]"
            )
            await update.message.reply_text(msg)
        except:
            await update.message.reply_text(tr(chat_id, "crypto_fail"))
        return

    # ترحيب
    if text in ("تفعيل الترحيب","enable welcome"):
        await enable_welcome(update, context); return
    if text in ("تعطيل الترحيب","disable welcome"):
        await disable_welcome(update, context); return

    # حماية عامة
    if text in ("تفعيل الحماية","تشغيل البوت","enable","enable protection","run bot"):
        await enable_bot(update, context); return
    if text in ("تعطيل الحماية","تعطيل البوت","disable","disable protection","stop bot"):
        await disable_bot(update, context); return

    # قفل/فتح القروب
    if text in ("قفل القروب","lock group"):
        await lock_group(update, context); return
    if text in ("فتح القروب","unlock group"):
        await unlock_group(update, context); return

    # قفل/فتح العناصر
    if text in ("قفل الروابط","lock links"):
        await lock_toggle(update, context, "lock_links", True); return
    if text in ("فتح الروابط","unlock links"):
        await lock_toggle(update, context, "lock_links", False); return

    if text in ("قفل الصور","lock photos"):
        await lock_toggle(update, context, "lock_photos", True); return
    if text in ("فتح الصور","unlock photos"):
        await lock_toggle(update, context, "lock_photos", False); return

    if text in ("قفل الفيديوهات","lock videos"):
        await lock_toggle(update, context, "lock_videos", True); return
    if text in ("فتح الفيديوهات","unlock videos"):
        await lock_toggle(update, context, "lock_videos", False); return

    if text in ("قفل الملصقات","lock stickers"):
        await lock_toggle(update, context, "lock_stickers", True); return
    if text in ("فتح الملصقات","unlock stickers"):
        await lock_toggle(update, context, "lock_stickers", False); return

    # إدارة الرتب (بالرد)
    if text in ("رفع مالك","promote owner"):
        await set_rank_cmd(update, context, "owner"); return
    if text in ("تنزيل مالك","demote owner"):
        await clear_rank_cmd(update, context, "owner"); return

    if text in ("رفع منشئ","promote creator"):
        await set_rank_cmd(update, context, "creator"); return
    if text in ("تنزيل منشئ","demote creator"):
        await clear_rank_cmd(update, context, "creator"); return

    if text in ("رفع مدير","promote manager"):
        await set_rank_cmd(update, context, "manager"); return
    if text in ("تنزيل مدير","demote manager"):
        await clear_rank_cmd(update, context, "manager"); return

    if text in ("رفع ادمن","promote admin"):
        await set_rank_cmd(update, context, "admin"); return
    if text in ("تنزيل ادمن","demote admin"):
        await clear_rank_cmd(update, context, "admin"); return

    if text in ("رفع مميز","promote vip"):
        await set_rank_cmd(update, context, "vip"); return
    if text in ("تنزيل مميز","demote vip"):
        await clear_rank_cmd(update, context, "vip"); return

    # قوائم الرتب
    if text in ("الادمنيه","admins","المدراء","managers","المنشئين","creators","المالكين","owners","عرض الرتب","ranks"):
        label_map = {
            "owners":"owner","creators":"creator","managers":"manager","admins":"admin","vips":"vip"
        }
        rows = db.conn.execute(
            "SELECT user_id, rank FROM users WHERE chat_id=?", (chat_id,)
        ).fetchall()
        lang = db.get_lang(chat_id)
        title = tr(chat_id, "ranks_title")
        if not rows:
            await update.message.reply_text(title + "\nلا يوجد")
            return
        lines = [title]
        for uid, r in rows:
            if text in ("المالكين","owners") and r!="owner": continue
            if text in ("المنشئين","creators") and r!="creator": continue
            if text in ("المدراء","managers") and r!="manager": continue
            if text in ("الادمنيه","admins") and r!="admin": continue
            if text in ("عرض الرتب","ranks"): pass
            lines.append(f"{uid} - {rank_label(lang, r)}")
        if len(lines)==1: lines.append("لا يوجد" if lang=="ar" else "None")
        await update.message.reply_text("\n".join(lines))
        return

    # حظر/طرد/تقييد/كتم
    if text.startswith("حظر") or text.lower()=="ban":
        await ban_cmd(update, context); return
    if text in ("فك حظر","unban"):
        await unban_cmd(update, context); return
    if text in ("طرد","kick"):
        await kick_cmd(update, context); return
    if text in ("تقييد","restrict"):
        await restrict_cmd(update, context, mute_only=False); return
    if text in ("الغاء تقييد","unrestrict"):
        await unrestrict_cmd(update, context, unmute=False); return
    if text in ("كتم","mute"):
        await restrict_cmd(update, context, mute_only=True); return
    if text in ("فك كتم","unmute"):
        await unrestrict_cmd(update, context, unmute=True); return

    # إنذارات
    if text in ("انذار","warn"):
        await warn_cmd(update, context); return
    if text in ("حذف الانذارات","clear warns"):
        await warn_clear_cmd(update, context); return
    if text in ("عرض الانذارات","show warns"):
        await warn_show_cmd(update, context); return

    # تنظيف
    if text.startswith("مسح "):
        arg = text.split(" ",1)[1]
        if arg.isdigit():
            context.args = [arg]
            await clear_last_cmd(update, context); return
    if text in ("مسح بالرد","delete"):
        await delete_reply_msg(update, context); return
    if text in ("مسح الكل","clear all"):
        context.args = ["100"]
        await clear_last_cmd(update, context); return

# ========= أزرار الكولباك =========
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.data: return
    if q.data == "lang_toggle":
        await cb_lang(update, context)
    elif q.data == "currencies":
        await cb_currencies(update, context)

# ========= الإقلاع =========
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # /start في الخاص فقط
    app.add_handler(CommandHandler("start", cmd_start))

    # أوامر/نصوص
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    # حماية على كل الرسائل (روابط/صور/فيديو/ملصقات)
    app.add_handler(MessageHandler(filters.ALL, protection_filter), group=1)

    # أزرار
    app.add_handler(CallbackQueryHandler(callbacks))

    log.info("DIL bot is running")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
