import os
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# تنظیمات
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 440194278

SETTINGS_FILE = "settings.json"


DEFAULT_SETTINGS = {
    "buttons": {
        "learning": "🎓 شروع آموزش",
        "level": "📊 سطح من",
        "jobs": "💼 انتخاب شغل",
        "audios": "🎧 آموزش‌های من",
        "register": "💳 ثبت‌نام",
        "about": "ℹ️ درباره دوره",
    },
    "card_number": "شماره کارت هنوز تنظیم نشده",
    "price": "۲۹۸,۰۰۰ تومان",
}


# =========================
# ذخیره و خواندن تنظیمات
# =========================

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(settings, file, ensure_ascii=False, indent=2)


settings = load_settings()


# =========================
# منوی اصلی
# =========================

def main_menu():
    b = settings["buttons"]

    keyboard = [
        [
            InlineKeyboardButton(b["learning"], callback_data="learning"),
            InlineKeyboardButton(b["level"], callback_data="level"),
        ],
        [
            InlineKeyboardButton(b["jobs"], callback_data="jobs"),
            InlineKeyboardButton(b["audios"], callback_data="audios"),
        ],
        [
            InlineKeyboardButton(b["register"], callback_data="register"),
            InlineKeyboardButton(b["about"], callback_data="about"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# /start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
🌟 سلام و خوش اومدی!

به ربات آموزشی ما خوش اومدی 💎

اینجا قراره قدم‌به‌قدم مهارت یاد بگیری،
پروژه انجام بدی و سطح خودت رو بالاتر ببری 🚀

از منوی زیر شروع کن 👇
"""

    await update.message.reply_text(
        text,
        reply_markup=main_menu()
    )


# =========================
# پنل مدیریت
# =========================

def admin_menu():

    keyboard = [
        [
            InlineKeyboardButton("✏️ تغییر شروع آموزش", callback_data="edit_learning"),
        ],
        [
            InlineKeyboardButton("✏️ تغییر سطح من", callback_data="edit_level"),
        ],
        [
            InlineKeyboardButton("✏️ تغییر انتخاب شغل", callback_data="edit_jobs"),
        ],
        [
            InlineKeyboardButton("✏️ تغییر آموزش‌های من", callback_data="edit_audios"),
        ],
        [
            InlineKeyboardButton("✏️ تغییر ثبت‌نام", callback_data="edit_register"),
        ],
        [
            InlineKeyboardButton("✏️ تغییر درباره دوره", callback_data="edit_about"),
        ],
        [
            InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="edit_card"),
        ],
        [
            InlineKeyboardButton("💰 تغییر قیمت", callback_data="edit_price"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ شما دسترسی مدیریت ندارید.")
        return

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\nاز این قسمت می‌تونی تنظیمات ربات رو تغییر بدی:",
        reply_markup=admin_menu()
    )


# =========================
# مدیریت تغییرات
# =========================

EDIT_MAP = {
    "edit_learning": ("learning", "اسم جدید دکمه «شروع آموزش» را بفرست:"),
    "edit_level": ("level", "اسم جدید دکمه «سطح من» را بفرست:"),
    "edit_jobs": ("jobs", "اسم جدید دکمه «انتخاب شغل» را بفرست:"),
    "edit_audios": ("audios", "اسم جدید دکمه «آموزش‌های من» را بفرست:"),
    "edit_register": ("register", "اسم جدید دکمه «ثبت‌نام» را بفرست:"),
    "edit_about": ("about", "اسم جدید دکمه «درباره دوره» را بفرست:"),
}


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # =========================
    # پنل ادمین
    # =========================

    if query.data == "admin":

        if user_id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        await query.edit_message_text(
            "⚙️ پنل مدیریت",
            reply_markup=admin_menu()
        )
        return

    # =========================
    # تغییر اسم دکمه‌ها
    # =========================

    if query.data in EDIT_MAP:

        if user_id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        key, message = EDIT_MAP[query.data]

        context.user_data["editing"] = key

        await query.edit_message_text(
            "✏️ " + message
        )

        return

    # =========================
    # تغییر شماره کارت
    # =========================

    if query.data == "edit_card":

        if user_id != ADMIN_ID:
            return

        context.user_data["editing"] = "card_number"

        await query.edit_message_text(
            "💳 شماره کارت جدید را ارسال کن:"
        )

        return

    # =========================
    # تغییر قیمت
    # =========================

    if query.data == "edit_price":

        if user_id != ADMIN_ID:
            return

        context.user_data["editing"] = "price"

        await query.edit_message_text(
            "💰 قیمت جدید را ارسال کن:\nمثلاً ۳۵۰,۰۰۰ تومان"
        )

        return

    # =========================
    # منوی اصلی
    # =========================

    if query.data == "home":

        await query.edit_message_text(
            "🌟 منوی اصلی",
            reply_markup=main_menu()
        )

        return

    # =========================
    # بخش‌های کاربر
    # =========================

    if query.data == "learning":

        text = """
🎓 شروع آموزش

اینجا مسیر آموزشی شما قرار می‌گیرد.

🚀 به‌زودی پروژه‌های آموزشی فعال می‌شوند.
"""

    elif query.data == "level":

        text = """
📊 سطح شما

⭐ سطح فعلی: مبتدی

پیشرفت:
0 / 5 پروژه

🎯 با انجام ۵ پروژه وارد سطح بعد می‌شوید.
"""

    elif query.data == "jobs":

        text = """
💼 انتخاب شغل

در مرحله بعد می‌توانیم مسیرهای شغلی مختلف را اینجا قرار دهیم.
"""

    elif query.data == "audios":

        text = """
🎧 آموزش‌های من

آموزش‌ها و ویس‌های اختصاصی شما در این قسمت قرار می‌گیرند.
"""

    elif query.data == "register":

        text = f"""
💳 ثبت‌نام اولیه

هزینه ثبت‌نام:
💰 {settings["price"]}

شماره کارت:
💳 {settings["card_number"]}

در مرحله بعد سیستم ارسال فیش و تأیید پرداخت را اضافه می‌کنیم.
"""

    elif query.data == "about":

        text = """
ℹ️ درباره دوره

🚀 آموزش مرحله‌به‌مرحله
🎯 انجام پروژه
📊 سیستم سطح‌بندی
💼 انتخاب مسیر شغلی
🎧 آموزش اختصاصی
🏆 پیشرفت مرحله‌ای
"""

    else:
        return

    keyboard = [
        [InlineKeyboardButton("🔙 برگشت به منو", callback_data="home")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# دریافت تغییرات ادمین
# =========================

async def receive_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    editing = context.user_data.get("editing")

    if not editing:
        return

    new_value = update.message.text.strip()

    if editing in settings["buttons"]:

        settings["buttons"][editing] = new_value

    elif editing == "card_number":

        settings["card_number"] = new_value

    elif editing == "price":

        settings["price"] = new_value

    save_settings(settings)

    context.user_data["editing"] = None

    await update.message.reply_text(
        "✅ تغییر با موفقیت ذخیره شد!\n\n"
        "برای دیدن پنل مدیریت دوباره /admin را بزن."
    )


# =========================
# اجرای ربات
# =========================

def main():

    if not BOT_TOKEN:
        print("BOT_TOKEN تنظیم نشده است.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("admin", admin_command)
    )

    application.add_handler(
        CallbackQueryHandler(button_handler)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_admin_message
        )
    )

    print("ربات با موفقیت اجرا شد...")

    application.run_polling()


if __name__ == "__main__":
    main()
