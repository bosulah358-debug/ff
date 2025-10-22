import logging, asyncio, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from database import Database
from config import *

logging.basicConfig(level=logging.INFO)
db = Database()

# === الترجمة ===
translations = {
    "ar": {
        "welcome": f"أهلاً بك، أنا البوت {BOT_NAME_AR}\nاختصاصي حماية المجموعات\nأضفني لمجموعتك وامنحني صلاحيات.",
        "add_me": "أضفني لمجموعتك",
        "language_changed": "✅ تم تغيير اللغة إلى العربية.",
        "currencies": "• أسعار العملات الرقمية مقابل USDT :",
    },
    "en": {
        "welcome": f"Hello, I’m {BOT_NAME_EN}.\nI specialize in group protection.\nAdd me to your group and give me admin rights.",
        "add_me": "Add me to your group",
        "language_changed": "✅ Language changed to English.",
        "currencies": "• Cryptocurrency Prices vs USDT :",
    }
}

# === أوامر ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    db.add_user(chat_id, user.id)

    lang = db.get_lang(chat_id, user.id)
    total_users = db.get_total_users()
    text = translations[lang]["welcome"]
    keyboard = [[InlineKeyboardButton(translations[lang]["add_me"], url=f"https://t.me/{context.bot.username}?startgroup=true")],
                [InlineKeyboardButton("🌐 تغيير اللغة", callback_data="toggle_lang")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"{text}\n\n👥 المستخدمين: {total_users}", reply_markup=reply_markup)

async def toggle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    current = db.get_lang(chat_id, user_id)
    new_lang = "en" if current == "ar" else "ar"
    db.set_lang(chat_id, user_id, new_lang)
    await query.edit_message_text(translations[new_lang]["language_changed"])

async def show_currencies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = db.get_lang(update.effective_chat.id, update.effective_user.id)
    try:
        data = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
        symbols = {"BTCUSDT": "BTC", "LTCUSDT": "LTC", "TONUSDT": "TON"}
        text = translations[lang]["currencies"] + "\n\n"
        for s in symbols:
            d = next((i for i in data if i["symbol"] == s), None)
            if d:
                text += f"{symbols[s]} : {float(d['lastPrice']):,.2f}$ [{float(d['priceChangePercent']):.2f}%]\n"
        await update.message.reply_text(text)
    except:
        await update.message.reply_text("⚠️ فشل جلب أسعار العملات.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(toggle_lang, pattern="^toggle_lang$"))
    app.add_handler(MessageHandler(filters.Regex("^الصرف$") | filters.Regex("^currencies$"), show_currencies))
    app.run_polling()

if __name__ == "__main__":
    main()
