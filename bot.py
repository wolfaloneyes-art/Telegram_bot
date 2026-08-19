import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# تنظیمات ربات
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

# آیدی عددی ادمین را بعداً اینجا قرار می‌دهیم
ADMIN_ID = 0


# =========================
# متن خوش‌آمدگویی
# =========================

WELCOME_TEXT = """
🌟 سلام و خوش اومدی!

به ربات آموزشی ما خوش اومدی 💎

اینجا قراره قدم‌به‌قدم مهارت یاد بگیری،
پروژه انجام بدی و سطح خودت رو بالاتر ببری 🚀

از منوی زیر شروع کن 👇
"""


# =========================
# منوی اصلی
# =========================

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("🎓 شروع آموزش", callback_data="learning"),
            InlineKeyboardButton("📊 سطح من", callback_data="level"),
        ],
        [
            InlineKeyboardButton("💼 انتخاب شغل", callback_data="jobs"),
            InlineKeyboardButton("🎧 آموزش‌های من", callback_data="audios"),
        ],
        [
            InlineKeyboardButton("💳 ثبت‌نام", callback_data="register"),
            InlineKeyboardButton("ℹ️ درباره دوره", callback_data="about"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# دستور /start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=main_menu()
    )


# =========================
# مدیریت دکمه‌های منو
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "learning":

        text = """
🎓 شروع آموزش

برای شروع مسیر آموزشی آماده‌ای؟ 🚀

در مراحل بعدی این بخش شامل:
• پروژه‌ها
• آموزش‌ها
• آزمون‌ها
• ارتقای سطح

خواهد شد.
"""

        keyboard = [
            [InlineKeyboardButton("🔙 برگشت به منو", callback_data="home")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    elif query.data == "level":

        text = """
📊 سطح شما

⭐ سطح فعلی: مبتدی

پیشرفت:
0 / 5 پروژه

🎯 با انجام ۵ پروژه، وارد سطح بعدی می‌شوید.

به زودی سیستم کامل سطح‌بندی فعال می‌شود.
"""

        keyboard = [
            [InlineKeyboardButton("🔙 برگشت به منو", callback_data="home")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    elif query.data == "jobs":

        text = """
💼 انتخاب شغل

در این قسمت می‌توانی شغلی را که به آن علاقه داری انتخاب کنی.

در مرحله بعد، برای هر شغل
آموزش‌ها و ویس‌های مخصوص همان شغل قرار می‌گیرد.
"""

        keyboard = [
            [InlineKeyboardButton("💻 برنامه‌نویسی", callback_data="job_programming")],
            [InlineKeyboardButton("🎨 طراحی", callback_data="job_design")],
            [InlineKeyboardButton("📱 تولید محتوا", callback_data="job_content")],
            [InlineKeyboardButton("🔙 برگشت", callback_data="home")],
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    elif query.data == "audios":

        text = """
🎧 آموزش‌های من

بعد از انتخاب شغل، آموزش‌ها و ویس‌های مخصوص همان مسیر اینجا نمایش داده می‌شوند.

🔒 هنوز آموزشی برای شما فعال نشده است.
"""

        keyboard = [
            [InlineKeyboardButton("🔙 برگشت به منو", callback_data="home")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    elif query.data == "register":

        text = """
💳 ثبت‌نام اولیه

هزینه ثبت‌نام:
💰 ۲۹۸,۰۰۰ تومان

در مرحله بعد:
1️⃣ اطلاعات ثبت‌نام را وارد می‌کنی
2️⃣ شماره کارت نمایش داده می‌شود
3️⃣ مبلغ را پرداخت می‌کنی
4️⃣ فیش پرداخت را ارسال می‌کنی
5️⃣ فیش توسط مدیریت بررسی می‌شود

🔒 سیستم پرداخت در مرحله بعد اضافه می‌شود.
"""

        keyboard = [
            [InlineKeyboardButton("🔙 برگشت به منو", callback_data="home")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    elif query.data == "about":

        text = """
ℹ️ درباره دوره

🚀 آموزش مرحله‌به‌مرحله
🎯 انجام پروژه
📊 سیستم سطح‌بندی
💼 انتخاب مسیر شغلی
🎧 آموزش‌های اختصاصی
🏆 پیشرفت مرحله‌ای

به زودی امکانات کامل فعال می‌شوند.
"""

        keyboard = [
            [InlineKeyboardButton("🔙 برگشت به منو", callback_data="home")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    elif query.data.startswith("job_"):

        jobs = {
            "job_programming": "💻 برنامه‌نویسی",
            "job_design": "🎨 طراحی",
            "job_content": "📱 تولید محتوا",
        }

        job_name = jobs.get(query.data, "شغل انتخابی")

        text = f"""
✅ انتخاب شما ثبت شد!

💼 مسیر انتخابی:
{job_name}

در مرحله بعد، آموزش‌ها و ویس‌های مخصوص این مسیر برای شما ارسال خواهد شد.
"""

        keyboard = [
            [InlineKeyboardButton("🔙 برگشت به منو", callback_data="home")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    elif query.data == "home":

        await query.edit_message_text(
            WELCOME_TEXT,
            reply_markup=main_menu()
        )


# =========================
# اجرای ربات
# =========================

def main():

    if not BOT_TOKEN:
        print("خطا: BOT_TOKEN تنظیم نشده است.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    application.add_handler(
        CallbackQueryHandler(button_handler)
    )

    print("ربات با موفقیت اجرا شد...")

    application.run_polling()


if __name__ == "__main__":
    main()
