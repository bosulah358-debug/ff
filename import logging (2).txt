import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from telegram.error import TelegramError
from datetime import datetime
import pytz
from database import Database

WAITING_FOR_KEYWORD, WAITING_FOR_REPLY = range(2)
WAITING_FOR_GLOBAL_KEYWORD, WAITING_FOR_GLOBAL_REPLY = range(2, 4)
OWNER_ID = None

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8458158034:AAGbNwJH5Sn2FQqnkxIkZTvLWjglGUfcBaU"
OWNER_USERNAME = "@h_7_m"

db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("أضفني لمجموعتك", url=f"https://t.me/{context.bot.username}?startgroup=true")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    total_users = db.get_total_users()
    
    welcome_message = (
        "• أهلاً بك عزيزي انا بوت اسمي انجل\n"
        "• اختصاص البوت حماية المجموعات\n"
        "• اضف البوت الى مجموعتك .\n"
        "• ارفعه ادمن مشرف\n"
        "• ارفعه مشرف وارسل تفعيل ليتم تفعيل المجموعة .\n"
        f"• عدد المستخدمين: {total_users}\n"
        f"• مطور البوت ↤︎ {OWNER_USERNAME}"
    )
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None) -> bool:
    if not update.effective_chat:
        return False
    
    chat_id = update.effective_chat.id
    user_id = user_id or update.effective_user.id
    
    if db.is_owner(chat_id, user_id) or db.is_admin(chat_id, user_id) or db.is_vip(chat_id, user_id):
        return True
    
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['creator', 'administrator']
    except:
        return False

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد حظره")
        return
    
    user_to_ban = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        await context.bot.ban_chat_member(chat_id, user_to_ban.id)
        db.add_banned(chat_id, user_to_ban.id)
        await update.message.reply_text(f"تم حظر [{user_to_ban.first_name}](tg://user?id={user_to_ban.id}) بنجاح", parse_mode='Markdown')
    except TelegramError as e:
        await update.message.reply_text(f"فشل الحظر: {str(e)}")

async def restrict_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد تقييده")
        return
    
    user_to_restrict = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        await context.bot.restrict_chat_member(chat_id, user_to_restrict.id, permissions)
        db.add_restricted(chat_id, user_to_restrict.id)
        await update.message.reply_text(f"تم تقييد [{user_to_restrict.first_name}](tg://user?id={user_to_restrict.id}) بنجاح", parse_mode='Markdown')
    except TelegramError as e:
        await update.message.reply_text(f"فشل التقييد: {str(e)}")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد طرده")
        return
    
    user_to_kick = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        await context.bot.ban_chat_member(chat_id, user_to_kick.id)
        await context.bot.unban_chat_member(chat_id, user_to_kick.id)
        await update.message.reply_text(f"تم طرد [{user_to_kick.first_name}](tg://user?id={user_to_kick.id}) بنجاح", parse_mode='Markdown')
    except TelegramError as e:
        await update.message.reply_text(f"فشل الطرد: {str(e)}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد كتمه")
        return
    
    user_to_mute = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        permissions = ChatPermissions(can_send_messages=False)
        await context.bot.restrict_chat_member(chat_id, user_to_mute.id, permissions)
        db.add_muted(chat_id, user_to_mute.id)
        await update.message.reply_text(f"تم كتم [{user_to_mute.first_name}](tg://user?id={user_to_mute.id}) بنجاح", parse_mode='Markdown')
    except TelegramError as e:
        await update.message.reply_text(f"فشل الكتم: {str(e)}")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد إنذاره")
        return
    
    user_to_warn = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    warnings = db.add_warning(chat_id, user_to_warn.id)
    
    if warnings >= 3:
        keyboard = [
            [
                InlineKeyboardButton("كتم", callback_data=f"warn_mute_{user_to_warn.id}"),
                InlineKeyboardButton("تقييد", callback_data=f"warn_restrict_{user_to_warn.id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"تم تجاوز عدد إنذارات [{user_to_warn.first_name}](tg://user?id={user_to_warn.id})\nاختر العقوبة:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"تم إنذار [{user_to_warn.first_name}](tg://user?id={user_to_warn.id})\nعدد الإنذارات: {warnings}/3",
            parse_mode='Markdown'
        )

async def warn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    action = data[1]
    user_id = int(data[2])
    chat_id = update.effective_chat.id
    
    try:
        if action == 'mute':
            permissions = ChatPermissions(can_send_messages=False)
            await context.bot.restrict_chat_member(chat_id, user_id, permissions)
            db.add_muted(chat_id, user_id)
            await query.edit_message_text(f"تم كتم المستخدم بسبب تجاوز عدد الإنذارات")
        elif action == 'restrict':
            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False
            )
            await context.bot.restrict_chat_member(chat_id, user_id, permissions)
            db.add_restricted(chat_id, user_id)
            await query.edit_message_text(f"تم تقييد المستخدم بسبب تجاوز عدد الإنذارات")
        
        db.reset_warnings(chat_id, user_id)
    except TelegramError as e:
        await query.edit_message_text(f"فشلت العملية: {str(e)}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد فك حظره")
        return
    
    user_to_unban = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        await context.bot.unban_chat_member(chat_id, user_to_unban.id)
        db.remove_banned(chat_id, user_to_unban.id)
        await update.message.reply_text(f"تم فك حظر [{user_to_unban.first_name}](tg://user?id={user_to_unban.id}) بنجاح", parse_mode='Markdown')
    except TelegramError as e:
        await update.message.reply_text(f"فشل فك الحظر: {str(e)}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد الغاء كتمه")
        return
    
    user_to_unmute = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True
        )
        await context.bot.restrict_chat_member(chat_id, user_to_unmute.id, permissions)
        db.remove_muted(chat_id, user_to_unmute.id)
        await update.message.reply_text(f"تم الغاء كتم [{user_to_unmute.first_name}](tg://user?id={user_to_unmute.id}) بنجاح", parse_mode='Markdown')
    except TelegramError as e:
        await update.message.reply_text(f"فشل الغاء الكتم: {str(e)}")

async def unrestrict_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد فك تقييده")
        return
    
    user_to_unrestrict = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        await context.bot.restrict_chat_member(chat_id, user_to_unrestrict.id, permissions)
        db.remove_restricted(chat_id, user_to_unrestrict.id)
        await update.message.reply_text(f"تم فك تقييد [{user_to_unrestrict.first_name}](tg://user?id={user_to_unrestrict.id}) بنجاح", parse_mode='Markdown')
    except TelegramError as e:
        await update.message.reply_text(f"فشل فك التقييد: {str(e)}")

async def promote_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد رفعه مميز")
        return
    
    user_to_promote = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    db.add_vip(chat_id, user_to_promote.id)
    await update.message.reply_text(f"تم رفع [{user_to_promote.first_name}](tg://user?id={user_to_promote.id}) مميز بنجاح", parse_mode='Markdown')

async def promote_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد رفعه مدير")
        return
    
    user_to_promote = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    db.add_admin(chat_id, user_to_promote.id)
    await update.message.reply_text(f"تم رفع [{user_to_promote.first_name}](tg://user?id={user_to_promote.id}) مدير بنجاح", parse_mode='Markdown')

async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد تنزيله")
        return
    
    user_to_demote = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    db.remove_all_ranks(chat_id, user_to_demote.id)
    await update.message.reply_text(f"تم تنزيل [{user_to_demote.first_name}](tg://user?id={user_to_demote.id}) من جميع الرتب", parse_mode='Markdown')

async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    chat_id = update.effective_chat.id
    
    rank = "عضو"
    if user.username and user.username.lower() == "h_7_m":
        rank = "مطور البوت"
    elif db.is_owner(chat_id, user.id):
        rank = "مالك"
    elif db.is_admin(chat_id, user.id):
        rank = "مدير"
    elif db.is_vip(chat_id, user.id):
        rank = "مميز"
    else:
        try:
            member = await context.bot.get_chat_member(chat_id, user.id)
            if member.status == 'creator':
                rank = "منشئ"
            elif member.status == 'administrator':
                rank = "ادمن"
        except:
            pass
    msg_count = db.get_message_count(chat_id, user.id)
    username = f"@{user.username}" if user.username else "لا يوجد"
    
    info = (
        f"• ID : `{user.id}`\n"
        f"• USE : {username}\n"
        f"• STE : {rank}\n"
        f"• MSG : {msg_count}"
    )
    
    await update.message.reply_text(info, parse_mode='Markdown')

async def top_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    chat_id = update.effective_chat.id
    top = db.get_top_users(chat_id, 20)
    
    if not top:
        await update.message.reply_text("لا توجد إحصائيات بعد")
        return
    
    message = "عرض التوب - أكثر 20 عضو تفاعلاً:\n\n"
    for i, (user_id, count) in enumerate(top, 1):
        try:
            user = await context.bot.get_chat(user_id)
            name = user.first_name
        except:
            name = "مستخدم محذوف"
        
        message += f"{i}. {name} - {count} رسالة\n"
    
    await update.message.reply_text(message)

async def commands_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("أوامر الإدارة", callback_data="cmd_admin")],
        [InlineKeyboardButton("أوامر الرفع والتنزيل", callback_data="cmd_ranks")],
        [InlineKeyboardButton("أوامر المسح", callback_data="cmd_clear")],
        [InlineKeyboardButton("أوامر المجموعة", callback_data="cmd_group")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("اختر نوع الأوامر:", reply_markup=reply_markup)

async def commands_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cmd_main":
        keyboard = [
            [InlineKeyboardButton("أوامر الإدارة", callback_data="cmd_admin")],
            [InlineKeyboardButton("أوامر الرفع والتنزيل", callback_data="cmd_ranks")],
            [InlineKeyboardButton("أوامر المسح", callback_data="cmd_clear")],
            [InlineKeyboardButton("أوامر المجموعة", callback_data="cmd_group")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("اختر نوع الأوامر:", reply_markup=reply_markup)
        return
    
    if query.data == "cmd_close":
        await query.delete_message()
        return
    
    if query.data == "cmd_admin":
        text = (
            "أوامر الإدارة:\n\n"
            "• حظر - حظر المستخدم\n"
            "• تقييد - تقييد المستخدم\n"
            "• طرد - طرد المستخدم\n"
            "• كتم - كتم المستخدم\n"
            "• انذار - إعطاء إنذار (حد 3)\n"
            "• فك الحظر - رفع الحظر\n"
            "• الغاء الكتم - إلغاء الكتم\n"
            "• فك التقييد - إلغاء التقييد\n"
            "• رفع الحظر - رفع الحظر\n"
            "• رفع الكتم - رفع الكتم\n"
            "• رفع القيود - رفع القيود"
        )
        keyboard = [
            [InlineKeyboardButton("التالي", callback_data="cmd_ranks")],
            [InlineKeyboardButton("الصفحة الرئيسية", callback_data="cmd_main"), 
             InlineKeyboardButton("إغلاق", callback_data="cmd_close")]
        ]
    elif query.data == "cmd_ranks":
        text = (
            "أوامر الرفع والتنزيل:\n\n"
            "• رفع مميز - رفع العضو مميز\n"
            "• رفع مدير - رفع العضو مدير\n"
            "• تنزيل الكل - إزالة جميع الرتب"
        )
        keyboard = [
            [InlineKeyboardButton("رجوع", callback_data="cmd_admin"),
             InlineKeyboardButton("التالي", callback_data="cmd_clear")],
            [InlineKeyboardButton("الصفحة الرئيسية", callback_data="cmd_main"),
             InlineKeyboardButton("إغلاق", callback_data="cmd_close")]
        ]
    elif query.data == "cmd_clear":
        text = (
            "أوامر المسح:\n\n"
            "• مسح الكل - مسح جميع البيانات\n"
            "• مسح المحظورين\n"
            "• مسح المكتومين\n"
            "• مسح + عدد - مسح عدد من الرسائل\n"
            "  مثال: مسح 100\n"
            "• مسح بالرد - مسح رسالة محددة"
        )
        keyboard = [
            [InlineKeyboardButton("رجوع", callback_data="cmd_ranks"),
             InlineKeyboardButton("التالي", callback_data="cmd_group")],
            [InlineKeyboardButton("الصفحة الرئيسية", callback_data="cmd_main"),
             InlineKeyboardButton("إغلاق", callback_data="cmd_close")]
        ]
    elif query.data == "cmd_group":
        text = (
            "أوامر المجموعة:\n\n"
            "• عرض التوب - أكثر 20 عضو نشاط\n"
            "• كشف - معلومات العضو\n"
            "• الاوامر - عرض هذه القائمة\n"
            "• تفعيل الترحيب\n"
            "• تعطيل الترحيب"
        )
        keyboard = [
            [InlineKeyboardButton("رجوع", callback_data="cmd_clear")],
            [InlineKeyboardButton("الصفحة الرئيسية", callback_data="cmd_main"),
             InlineKeyboardButton("إغلاق", callback_data="cmd_close")]
        ]
    else:
        text = "غير معروف"
        keyboard = []
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    chat_id = update.effective_chat.id
    db.clear_all_data(chat_id)
    await update.message.reply_text("تم مسح جميع البيانات المؤقتة")

async def clear_banned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    chat_id = update.effective_chat.id
    db.clear_banned(chat_id)
    await update.message.reply_text("تم مسح قائمة المحظورين")

async def clear_muted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    chat_id = update.effective_chat.id
    db.clear_muted(chat_id)
    await update.message.reply_text("تم مسح قائمة المكتومين")

async def clear_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    try:
        count = int(context.args[0]) if context.args else 1
        chat_id = update.effective_chat.id
        message_id = update.message.message_id
        
        try:
            await context.bot.delete_message(chat_id, message_id)
        except:
            pass
        
        for i in range(1, min(count + 1, 101)):
            try:
                await context.bot.delete_message(chat_id, message_id - i)
            except:
                pass
    except (ValueError, IndexError):
        pass

async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على الرسالة المراد مسحها")
        return
    
    try:
        await update.message.reply_to_message.delete()
        await update.message.reply_text("تم مسح الرسالة")
    except:
        await update.message.reply_text("فشل مسح الرسالة")

async def enable_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    chat_id = update.effective_chat.id
    db.set_welcome_status(chat_id, True)
    await update.message.reply_text("تم تفعيل الترحيب")

async def disable_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    chat_id = update.effective_chat.id
    db.set_welcome_status(chat_id, False)
    await update.message.reply_text("تم تعطيل الترحيب")

async def add_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return ConversationHandler.END
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return ConversationHandler.END
    
    await update.message.reply_text("حسناً الآن ارسل الكلمة")
    return WAITING_FOR_KEYWORD

async def receive_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()
    context.user_data['reply_keyword'] = keyword
    
    help_text = (
        "حسناً يمكنك اضافة:\n"
        "( نص,صوره,فيديو,متحركه,بصمه,اغنيه,ملف )\n\n"
        "ويمكنك اضافة الرد بتلك الطريقة:\n"
        "▹ #الاسم - اسم العضو\n"
        "▹ #يوزره - يوزر الرد\n"
        "▹ #اليوزر - يوزر مرسل الرسالة\n"
        "▹ #الرسائل - عدد رسائل المستخدم\n"
        "▹ #الايدي - ايدي المستخدم\n"
        "▹ #الرتبه - رتبة المستخدم\n"
        "▹ #التعديل - عدد تعديلات\n"
        "▹ #النقاط - نقاط المستخدم"
    )
    
    await update.message.reply_text(help_text)
    return WAITING_FOR_REPLY

async def receive_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = context.user_data.get('reply_keyword')
    if not keyword:
        await update.message.reply_text("حدث خطأ، يرجى المحاولة مرة أخرى")
        return ConversationHandler.END
    
    chat_id = update.effective_chat.id
    reply_data = {}
    
    if update.message.text:
        reply_data['type'] = 'text'
        reply_data['content'] = update.message.text
    elif update.message.photo:
        reply_data['type'] = 'photo'
        reply_data['file_id'] = update.message.photo[-1].file_id
        reply_data['caption'] = update.message.caption or ''
    elif update.message.video:
        reply_data['type'] = 'video'
        reply_data['file_id'] = update.message.video.file_id
        reply_data['caption'] = update.message.caption or ''
    elif update.message.animation:
        reply_data['type'] = 'animation'
        reply_data['file_id'] = update.message.animation.file_id
        reply_data['caption'] = update.message.caption or ''
    elif update.message.voice:
        reply_data['type'] = 'voice'
        reply_data['file_id'] = update.message.voice.file_id
    elif update.message.audio:
        reply_data['type'] = 'audio'
        reply_data['file_id'] = update.message.audio.file_id
        reply_data['caption'] = update.message.caption or ''
    elif update.message.document:
        reply_data['type'] = 'document'
        reply_data['file_id'] = update.message.document.file_id
        reply_data['caption'] = update.message.caption or ''
    else:
        await update.message.reply_text("نوع الرسالة غير مدعوم")
        return ConversationHandler.END
    
    db.add_custom_reply(chat_id, keyword, reply_data)
    await update.message.reply_text(f"تم اضافة الرد '{keyword}' بنجاح")
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_add_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("تم الغاء اضافة الرد")
    return ConversationHandler.END

def replace_variables(text, user, chat_id, edit_count=0, points=0):
    if not text:
        return text
    
    username = f"@{user.username}" if user.username else "لا يوجد"
    msg_count = db.get_message_count(chat_id, user.id)
    
    rank = "عضو"
    if db.is_owner(chat_id, user.id):
        rank = "مالك"
    elif db.is_admin(chat_id, user.id):
        rank = "مدير"
    elif db.is_vip(chat_id, user.id):
        rank = "مميز"
    
    text = text.replace('#الاسم', user.first_name or '')
    text = text.replace('#يوزره', username)
    text = text.replace('#اليوزر', username)
    text = text.replace('#الرسائل', str(msg_count))
    text = text.replace('#الايدي', str(user.id))
    text = text.replace('#الرتبه', rank)
    text = text.replace('#التعديل', str(edit_count))
    text = text.replace('#النقاط', str(points))
    
    return text

async def check_custom_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    if update.effective_chat.type == 'private':
        return
    
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    
    reply_data = db.get_custom_reply(chat_id, text)
    
    if reply_data:
        user = update.effective_user
        
        if reply_data['type'] == 'text':
            content = replace_variables(reply_data['content'], user, chat_id)
            await update.message.reply_text(content)
        elif reply_data['type'] == 'photo':
            caption = replace_variables(reply_data.get('caption', ''), user, chat_id)
            await update.message.reply_photo(
                photo=reply_data['file_id'],
                caption=caption if caption else None
            )
        elif reply_data['type'] == 'video':
            caption = replace_variables(reply_data.get('caption', ''), user, chat_id)
            await update.message.reply_video(
                video=reply_data['file_id'],
                caption=caption if caption else None
            )
        elif reply_data['type'] == 'animation':
            caption = replace_variables(reply_data.get('caption', ''), user, chat_id)
            await update.message.reply_animation(
                animation=reply_data['file_id'],
                caption=caption if caption else None
            )
        elif reply_data['type'] == 'voice':
            await update.message.reply_voice(voice=reply_data['file_id'])
        elif reply_data['type'] == 'audio':
            caption = replace_variables(reply_data.get('caption', ''), user, chat_id)
            await update.message.reply_audio(
                audio=reply_data['file_id'],
                caption=caption if caption else None
            )
        elif reply_data['type'] == 'document':
            caption = replace_variables(reply_data.get('caption', ''), user, chat_id)
            await update.message.reply_document(
                document=reply_data['file_id'],
                caption=caption if caption else None
            )

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    chat_id = update.effective_chat.id
    
    if not db.is_welcome_enabled(chat_id):
        return
    
    for member in update.message.new_chat_members:
        saudi_tz = pytz.timezone('Asia/Riyadh')
        now = datetime.now(saudi_tz)
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%Y/%m/%d")
        
        username = f"@{member.username}" if member.username else "لا يوجد"
        chat_title = update.effective_chat.title
        
        welcome_msg = (
            f"نـورت عـالـمـنا الجـمـيل )\n"
            f"• الايدي: `{member.id}`\n"
            f"• اليوزر: {username}\n"
            f"• الوقت: {time_str}\n"
            f"• التاريخ: {date_str}\n"
            f"• اسم المجموعة: {chat_title}"
        )
        
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def track_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    db.increment_message_count(chat_id, user_id)

import asyncio

async def handle_arabic_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    
    command_handlers = {
        'حظر': ban_user,
        'تقييد': restrict_user,
        'طرد': kick_user,
        'كتم': mute_user,
        'انذار': warn_user,
        'فك الحظر': unban_user,
        'الغاء الكتم': unmute_user,
        'فك التقييد': unrestrict_user,
        'رفع الحظر': unban_user,
        'رفع الكتم': unmute_user,
        'رفع القيود': unrestrict_user,
        'رفع مميز': promote_vip,
        'رفع مدير': promote_admin,
        'تنزيل الكل': demote_user,
        'كشف': check_user,
        'عرض التوب': top_users,
        'الاوامر': commands_list,
        'مسح الكل': clear_all,
        'مسح المحظورين': clear_banned,
        'مسح المكتومين': clear_muted,
        'مسح بالرد': delete_message,
        'تفعيل الترحيب': enable_welcome,
        'تعطيل الترحيب': disable_welcome,
        'تفعيل': enable_welcome,
        'الإدمنية': show_admins,
        'الادمنية': show_admins,
        'قفل القروب': lock_group,
        'فتح القروب': unlock_group,
        'احصائيات البوت': bot_stats,
        'الاحصائيات': bot_stats,
        'إيقاف البوت': disable_bot,
        'ايقاف البوت': disable_bot,
        'تشغيل البوت': enable_bot,
        'انجل': angel_command,
        'انذاراتي': get_warnings,
        'اخر رسايلي': get_my_messages
    }
    
    if text.startswith('كتم ') and (text.endswith('د') or text.endswith('س')):
        context.args = [text[4:]]
        await temp_mute_user(update, context)
        return
    
    if text.startswith('مسح ') and text[4:].isdigit():
        context.args = [text[4:]]
        await clear_messages(update, context)
        return
    
    if text in command_handlers:
        await command_handlers[text](update, context)


from datetime import timedelta

async def temp_mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة المستخدم المراد كتمه مؤقتاً")
        return
    
    if not context.args:
        await update.message.reply_text("يجب تحديد المدة (مثال: كتم 5د أو كتم 1س)")
        return
    
    time_arg = context.args[0]
    user_to_mute = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        if time_arg.endswith('د'):
            minutes = int(time_arg[:-1])
            until_date = datetime.now() + timedelta(minutes=minutes)
        elif time_arg.endswith('س'):
            hours = int(time_arg[:-1])
            until_date = datetime.now() + timedelta(hours=hours)
        else:
            await update.message.reply_text("صيغة خاطئة. استخدم: كتم 5د أو كتم 1س")
            return
        
        permissions = ChatPermissions(can_send_messages=False)
        await context.bot.restrict_chat_member(chat_id, user_to_mute.id, permissions, until_date=until_date)
        db.add_muted(chat_id, user_to_mute.id, until_date.isoformat())
        await update.message.reply_text(f"تم كتم [{user_to_mute.first_name}](tg://user?id={user_to_mute.id}) لمدة {time_arg}", parse_mode='Markdown')
    except (ValueError, TelegramError) as e:
        await update.message.reply_text(f"فشل الكتم المؤقت: {str(e)}")

async def show_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    chat_id = update.effective_chat.id
    
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_list = "قائمة الإدمنية:\n\n"
        for admin in admins:
            username = f"@{admin.user.username}" if admin.user.username else admin.user.first_name
            status = "منشئ" if admin.status == 'creator' else "ادمن"
            admin_list += f"• {username} - {status}\n"
        
        await update.message.reply_text(admin_list)
    except TelegramError as e:
        await update.message.reply_text(f"فشل عرض الإدمنية: {str(e)}")

async def lock_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    chat_id = update.effective_chat.id
    db.set_group_lock(chat_id, True)
    await update.message.reply_text("تم قفل القروب، فقط المشرفين يمكنهم إرسال الرسائل")

async def unlock_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    chat_id = update.effective_chat.id
    db.set_group_lock(chat_id, False)
    await update.message.reply_text("تم فتح القروب")

async def bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_groups = db.get_total_groups()
    total_users = db.get_total_users()
    total_commands = db.get_stat('commands_executed')
    
    stats_msg = (
        f"📊 احصائيات البوت:\n\n"
        f"• عدد القروبات: {total_groups}\n"
        f"• عدد الأعضاء النشطين: {total_users}\n"
        f"• عدد الأوامر المنفذة: {total_commands}"
    )
    
    await update.message.reply_text(stats_msg)

async def disable_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    chat_id = update.effective_chat.id
    db.set_bot_status(chat_id, False)
    await update.message.reply_text("تم إيقاف البوت مؤقتاً")

async def enable_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("هذا الأمر للمشرفين فقط")
        return
    
    chat_id = update.effective_chat.id
    db.set_bot_status(chat_id, True)
    await update.message.reply_text("تم تشغيل البوت")

async def angel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("• 𝗗𝗘𝗩 : @h_7_m")

async def get_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    user = update.effective_user
    chat_id = update.effective_chat.id
    warnings = db.get_warnings(chat_id, user.id)
    
    await update.message.reply_text(f"عدد إنذاراتك: {warnings}/3")

async def get_my_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    user = update.effective_user
    chat_id = update.effective_chat.id
    msg_count = db.get_message_count(chat_id, user.id)
    
    await update.message.reply_text(f"عدد رسائلك في القروب: {msg_count}")

async def add_global_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.effective_user.username != "h_7_m":
        await update.message.reply_text("هذا الأمر للمطور فقط")
        return ConversationHandler.END
    
    await update.message.reply_text("حسنًا، أرسل الكلمة التي تريد أن يرد عليها.")
    return WAITING_FOR_GLOBAL_KEYWORD

async def receive_global_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()
    context.user_data['global_reply_keyword'] = keyword
    await update.message.reply_text("الآن أرسل الرد (نص أو صورة أو فيديو أو غيره).")
    return WAITING_FOR_GLOBAL_REPLY

async def receive_global_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = context.user_data.get('global_reply_keyword')
    if not keyword:
        await update.message.reply_text("حدث خطأ، يرجى المحاولة مرة أخرى")
        return ConversationHandler.END
    
    reply_data = {}
    
    if update.message.text:
        reply_data['type'] = 'text'
        reply_data['content'] = update.message.text
    elif update.message.photo:
        reply_data['type'] = 'photo'
        reply_data['file_id'] = update.message.photo[-1].file_id
        reply_data['caption'] = update.message.caption or ''
    elif update.message.video:
        reply_data['type'] = 'video'
        reply_data['file_id'] = update.message.video.file_id
        reply_data['caption'] = update.message.caption or ''
    elif update.message.animation:
        reply_data['type'] = 'animation'
        reply_data['file_id'] = update.message.animation.file_id
        reply_data['caption'] = update.message.caption or ''
    elif update.message.voice:
        reply_data['type'] = 'voice'
        reply_data['file_id'] = update.message.voice.file_id
    elif update.message.audio:
        reply_data['type'] = 'audio'
        reply_data['file_id'] = update.message.audio.file_id
        reply_data['caption'] = update.message.caption or ''
    elif update.message.document:
        reply_data['type'] = 'document'
        reply_data['file_id'] = update.message.document.file_id
        reply_data['caption'] = update.message.caption or ''
    else:
        await update.message.reply_text("نوع الرسالة غير مدعوم")
        return ConversationHandler.END
    
    db.add_global_reply(keyword, reply_data)
    await update.message.reply_text(f"تم اضافة الرد العام '{keyword}' بنجاح")
    
    context.user_data.clear()
    return ConversationHandler.END

async def check_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not update.message or not update.message.text:
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    message_text = update.message.text
    
    if await is_admin(update, context):
        return
    
    db.add_message_to_history(chat_id, user_id, message_text)
    recent_messages = db.get_recent_messages(chat_id, user_id, minutes=1)
    
    if len(recent_messages) >= 7:
        same_message_count = sum(1 for msg in recent_messages if msg['message_text'] == message_text)
        
        if same_message_count >= 7:
            try:
                permissions = ChatPermissions(can_send_messages=False)
                await context.bot.restrict_chat_member(chat_id, user_id, permissions)
                db.add_muted(chat_id, user_id)
                await update.message.reply_text(f"تم كتم المستخدم بسبب التكرار المفرط")
            except TelegramError:
                pass

async def check_bot_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    if not update.message.new_chat_members:
        return
    
    for member in update.message.new_chat_members:
        if member.is_bot and member.id != context.bot.id:
            try:
                await context.bot.ban_chat_member(update.effective_chat.id, member.id)
                await update.message.reply_text(f"تم طرد البوت {member.first_name} تلقائياً")
            except TelegramError:
                pass

async def reply_to_salam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    if update.effective_chat.type == 'private':
        return
    
    text = update.message.text.strip()
    
    if text == "السلام عليكم" or text == "السلام عليكم ورحمة الله وبركاته":
        await update.message.reply_text("وعـليـكم الـسلام ورحـمه الله وبـركاتـه")

async def check_global_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    if update.effective_chat.type == 'private':
        return
    
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    
    reply_data = db.get_global_reply(text)
    
    if reply_data:
        user = update.effective_user
        
        if reply_data['type'] == 'text':
            content = replace_variables(reply_data['content'], user, chat_id)
            await update.message.reply_text(content)
        elif reply_data['type'] == 'photo':
            caption = replace_variables(reply_data.get('caption', ''), user, chat_id)
            await update.message.reply_photo(
                photo=reply_data['file_id'],
                caption=caption if caption else None
            )
        elif reply_data['type'] == 'video':
            caption = replace_variables(reply_data.get('caption', ''), user, chat_id)
            await update.message.reply_video(
                video=reply_data['file_id'],
                caption=caption if caption else None
            )
        elif reply_data['type'] == 'animation':
            caption = replace_variables(reply_data.get('caption', ''), user, chat_id)
            await update.message.reply_animation(
                animation=reply_data['file_id'],
                caption=caption if caption else None
            )
        elif reply_data['type'] == 'voice':
            await update.message.reply_voice(voice=reply_data['file_id'])
        elif reply_data['type'] == 'audio':
            caption = replace_variables(reply_data.get('caption', ''), user, chat_id)
            await update.message.reply_audio(
                audio=reply_data['file_id'],
                caption=caption if caption else None
            )
        elif reply_data['type'] == 'document':
            caption = replace_variables(reply_data.get('caption', ''), user, chat_id)
            await update.message.reply_document(
                document=reply_data['file_id'],
                caption=caption if caption else None
            )

async def check_group_locked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if db.is_group_locked(chat_id) and not await is_admin(update, context):
        try:
            await update.message.delete()
        except TelegramError:
            pass

async def check_bot_enabled(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    chat_id = update.effective_chat.id
    
    if not db.is_bot_enabled(chat_id) and not await is_admin(update, context):
        return False
    return True

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    
    application.add_handler(CallbackQueryHandler(warn_callback, pattern="^warn_"))
    application.add_handler(CallbackQueryHandler(commands_callback, pattern="^cmd_"))
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^اضف رد$'), add_reply_start)],
        states={
            WAITING_FOR_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_keyword)],
            WAITING_FOR_REPLY: [MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ANIMATION | 
                 filters.VOICE | filters.AUDIO | filters.Document.ALL) & ~filters.COMMAND,
                receive_reply
            )]
        },
        fallbacks=[MessageHandler(filters.Regex('^الغاء$'), cancel_add_reply)],
        allow_reentry=True
    )
    
    global_reply_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^اضف رد عام$'), add_global_reply_start)],
        states={
            WAITING_FOR_GLOBAL_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_global_keyword)],
            WAITING_FOR_GLOBAL_REPLY: [MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ANIMATION | 
                 filters.VOICE | filters.AUDIO | filters.Document.ALL) & ~filters.COMMAND,
                receive_global_reply
            )]
        },
        fallbacks=[MessageHandler(filters.Regex('^الغاء$'), cancel_add_reply)],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(global_reply_handler)
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, check_bot_member), group=0)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_spam), group=0)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_to_salam), group=0)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_global_replies), group=0)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_custom_replies), group=1)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_group_locked), group=1)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_arabic_commands), group=2)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_messages), group=3)
    
    application.add_error_handler(error_handler)
    
    logger.info("Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
