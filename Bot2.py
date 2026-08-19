import os
import sqlite3
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
# تنظیمات اصلی
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

# آیدی عددی ادمین
ADMIN_ID = 440194278

DB_NAME = "bot.db"


# =========================
# دیتابیس
# =========================

def db():
    return sqlite3.connect(DB_NAME)


def init_db():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            level INTEGER DEFAULT 1,
            projects INTEGER DEFAULT 0,
            job TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS voices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job TEXT,
            title TEXT,
            file_id TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            photo_id TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)

    defaults = {
        "learning": "🎓 شروع آموزش",
        "level": "📊 سطح من",
        "jobs": "💼 انتخاب شغل",
        "audios": "🎧 آموزش‌های من",
        "register": "💳 ثبت‌نام",
        "about": "ℹ️ درباره دوره",
        "card": "شماره کارت هنوز تنظیم نشده",
        "price": "۲۹۸,۰۰۰ تومان",
    }

    for key, value in defaults.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings (key,value) VALUES (?,?)",
            (key, value)
        )

    conn.commit()
    conn.close()


def get_setting(key):

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,)
    )

    row = cur.fetchone()

    conn.close()

    return row[0] if row else ""


def set_setting(key, value):

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO settings (key,value)
        VALUES (?,?)
    """, (key, value))

    conn.commit()
    conn.close()


# =========================
# ثبت کاربر
# =========================

def save_user(user):

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO users
        (user_id, first_name, username)
        VALUES (?, ?, ?)
    """, (
        user.id,
        user.first_name or "",
        user.username or ""
    ))

    conn.commit()
    conn.close()


# =========================
# منوی اصلی
# =========================

def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                get_setting("learning"),
                callback_data="learning"
            ),
            InlineKeyboardButton(
                get_setting("level"),
                callback_data="level"
            ),
        ],
        [
            InlineKeyboardButton(
                get_setting("jobs"),
                callback_data="jobs"
            ),
            InlineKeyboardButton(
                get_setting("audios"),
                callback_data="audios"
            ),
        ],
        [
            InlineKeyboardButton(
                get_setting("register"),
                callback_data="register"
            ),
            InlineKeyboardButton(
                get_setting("about"),
                callback_data="about"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# شروع ربات
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user(update.effective_user)

    text = """
🌟 سلام و خوش اومدی!

به ربات آموزشی ما خوش اومدی 💎

اینجا قراره قدم‌به‌قدم مهارت یاد بگیری،
پروژه انجام بدی و مسیر شغلی خودت رو پیدا کنی 🚀

از منوی زیر شروع کن 👇
"""

    await update.message.reply_text(
        text,
        reply_markup=main_menu()
    )


# =========================
# پنل ادمین
# =========================

def admin_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "🎛️ تغییر منو",
                callback_data="admin_menu_edit"
            )
        ],
        [
            InlineKeyboardButton(
                "💳 تغییر شماره کارت",
                callback_data="admin_card"
            ),
            InlineKeyboardButton(
                "💰 تغییر قیمت",
                callback_data="admin_price"
            )
        ],
        [
            InlineKeyboardButton(
                "🎙️ افزودن ویس",
                callback_data="admin_voice"
            )
        ],
        [
            InlineKeyboardButton(
                "🧾 فیش‌های پرداخت",
                callback_data="admin_payments"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 کاربران",
                callback_data="admin_users"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریت ندارید."
        )

        return

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\n"
        "از اینجا می‌تونی تنظیمات ربات رو کنترل کنی:",
        reply_markup=admin_menu()
    )


# =========================
# تغییر نام منو
# =========================

def menu_edit():

    keyboard = [
        [
            InlineKeyboardButton(
                "🎓 شروع آموزش",
                callback_data="edit_learning"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 سطح من",
                callback_data="edit_level"
            )
        ],
        [
            InlineKeyboardButton(
                "💼 انتخاب شغل",
                callback_data="edit_jobs"
            )
        ],
        [
            InlineKeyboardButton(
                "🎧 آموزش‌های من",
                callback_data="edit_audios"
            )
        ],
        [
            InlineKeyboardButton(
                "💳 ثبت‌نام",
                callback_data="edit_register"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ درباره دوره",
                callback_data="edit_about"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="admin_home"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# مدیریت دکمه‌ها
# =========================

EDIT_BUTTONS = {
    "edit_learning": "learning",
    "edit_level": "level",
    "edit_jobs": "jobs",
    "edit_audios": "audios",
    "edit_register": "register",
    "edit_about": "about",
}


# =========================
# دکمه‌ها
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # =========================
    # امنیت ادمین
    # =========================

    if query.data.startswith("admin") or query.data.startswith("edit_"):

        if user_id != ADMIN_ID:

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True
            )

            return

    # =========================
    # پنل اصلی
    # =========================

    if query.data == "admin_home":

        await query.edit_message_text(
            "⚙️ پنل مدیریت",
            reply_markup=admin_menu()
        )

        return

    # =========================
    # ویرایش منو
    # =========================

    if query.data == "admin_menu_edit":

        await query.edit_message_text(
            "🎛️ کدام دکمه را می‌خواهی تغییر بدهی؟",
            reply_markup=menu_edit()
        )

        return

    # =========================
    # انتخاب دکمه برای تغییر
    # =========================

    if query.data in EDIT_BUTTONS:

        key = EDIT_BUTTONS[query.data]

        context.user_data["editing"] = key

        await query.edit_message_text(
            "✏️ اسم جدید این دکمه را همینجا برای من بفرست."
        )

        return

    # =========================
    # تغییر کارت
    # =========================

    if query.data == "admin_card":

        context.user_data["editing"] = "card"

        await query.edit_message_text(
            "💳 شماره کارت جدید را بفرست."
        )

        return

    # =========================
    # تغییر قیمت
    # =========================

    if query.data == "admin_price":

        context.user_data["editing"] = "price"

        await query.edit_message_text(
            "💰 مبلغ جدید را بفرست.\n\n"
            "مثال:\n"
            "۳۵۰,۰۰۰ تومان"
        )

        return

    # =========================
    # افزودن ویس
    # =========================

    if query.data == "admin_voice":

        context.user_data["adding_voice"] = True

        await query.edit_message_text(
            "🎙️ برای اضافه کردن ویس:\n\n"
            "اول نام شغل را بفرست.\n"
            "مثلاً:\n"
            "برنامه نویسی"
        )

        return

    # =========================
    # فیش‌ها
    # =========================

    if query.data == "admin_payments":

        conn = db()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, user_id
            FROM payments
            WHERE status='pending'
            ORDER BY id DESC
        """)

        payments = cur.fetchall()

        conn.close()

        if not payments:

            await query.edit_message_text(
                "🧾 فیش پرداختی در انتظار تأیید نداریم.",
                reply_markup=admin_menu()
            )

            return

        text = "🧾 فیش‌های در انتظار تأیید:\n\n"

        for payment_id, uid in payments:

            text += f"🧾 فیش #{payment_id}\n"
            text += f"👤 کاربر: {uid}\n\n"

        await query.edit_message_text(
            text,
            reply_markup=admin_menu()
        )

        return

    # =========================
    # کاربران
    # =========================

    if query.data == "admin_users":

        conn = db()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users")

        count = cur.fetchone()[0]

        conn.close()

        await query.edit_message_text(
            f"👥 تعداد کاربران: {count}",
            reply_markup=admin_menu()
        )

        return

    # =========================
    # بخش‌های کاربر
    # =========================

    if query.data == "learning":

        text = """
🎓 شروع آموزش

مسیر آموزشی شما از اینجا شروع می‌شود.

🚀 پروژه‌ها و آموزش‌ها به‌زودی فعال می‌شوند.
"""

    elif query.data == "level":

        conn = db()
        cur = conn.cursor()

        cur.execute("""
            SELECT level, projects
            FROM users
            WHERE user_id=?
        """, (user_id,))

        row = cur.fetchone()

        conn.close()

        level = row[0] if row else 1
        projects = row[1] if row else 0

        text = f"""
📊 سطح شما

⭐ سطح: {level}

📁 پروژه‌های انجام‌شده:
{projects} / 5

🎯 با انجام ۵ پروژه وارد سطح بعد می‌شوی.
"""

    elif query.data == "jobs":

        keyboard = [
            [
                InlineKeyboardButton(
                    "💻 برنامه‌نویسی",
                    callback_data="job_programming"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎨 طراحی",
                    callback_data="job_design"
                )
            ],
            [
                InlineKeyboardButton(
                    "📱 تولید محتوا",
                    callback_data="job_content"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )
            ]
        ]

        await query.edit_message_text(
            "💼 شغل مورد علاقه‌ات را انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    elif query.data.startswith("job_"):

        jobs = {
            "job_programming": "برنامه نویسی",
            "job_design": "طراحی",
            "job_content": "تولید محتوا",
        }

        job = jobs.get(query.data)

        conn = db()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users
            SET job=?
            WHERE user_id=?
        """, (job, user_id))

        cur.execute("""
            SELECT title, file_id
            FROM voices
            WHERE job=?
        """, (job,))

        voices = cur.fetchall()

        conn.commit()
        conn.close()

        await query.edit_message_text(
            f"✅ مسیر «{job}» انتخاب شد."
        )

        if voices:

            for title, file_id in voices:

                await context.bot.send_voice(
                    chat_id=user_id,
                    voice=file_id,
                    caption=f"🎙️ {title}"
                )

        else:

            await context.bot.send_message(
                chat_id=user_id,
                text="🎙️ هنوز ویسی برای این مسیر اضافه نشده."
            )

        return

    elif query.data == "audios":

        conn = db()
        cur = conn.cursor()

        cur.execute("""
            SELECT job
            FROM users
            WHERE user_id=?
        """, (user_id,))

        row = cur.fetchone()

        if not row or not row[0]:

            conn.close()

            text = "🎙️ اول باید یک شغل انتخاب کنی."

        else:

            job = row[0]

            cur.execute("""
                SELECT title, file_id
                FROM voices
                WHERE job=?
            """, (job,))

            voices = cur.fetchall()

            conn.close()

            if not voices:

                text = "🎙️ هنوز آموزشی برای این شغل قرار نگرفته."

            else:

                text = f"🎙️ آموزش‌های مسیر «{job}»:\n\n"

                for title, _ in voices:
                    text += f"🎧 {title}\n"

    elif query.data == "register":

        text = f"""
💳 ثبت‌نام اولیه

💰 مبلغ:
{get_setting("price")}

💳 شماره کارت:
{get_setting("card")}

بعد از پرداخت، عکس فیش را همینجا ارسال کن.

🧾 فیش برای مدیریت ارسال می‌شود و پس از تأیید، ثبت‌نامت فعال خواهد شد.
"""

    elif query.data == "about":

        text = """
ℹ️ درباره دوره

🚀 آموزش مرحله‌به‌مرحله
🎯 پروژه‌های عملی
📊 سیستم سطح‌بندی
💼 انتخاب مسیر شغلی
🎙️ آموزش‌های صوتی
🏆 پیشرفت مرحله‌ای
"""

    elif query.data == "home":

        await query.edit_message_text(
            "🌟 منوی اصلی",
            reply_markup=main_menu()
        )

        return

    else:
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "🔙 برگشت به منو",
                callback_data="home"
            )
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# دریافت پیام ادمین
# =========================

async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    editing = context.user_data.get("editing")

    if editing:

        value = update.message.text.strip()

        if editing in [
            "learning",
            "level",
            "jobs",
            "audios",
            "register",
            "about"
        ]:

            set_setting(editing, value)

        elif editing == "card":

            set_setting("card", value)

        elif editing == "price":

            set_setting("price", value)

        context.user_data["editing"] = None

        await update.message.reply_text(
            "✅ با موفقیت ذخیره شد.",
            reply_markup=admin_menu()
        )

        return

    # =========================
    # افزودن ویس
    # =========================

    if context.user_data.get("adding_voice"):

        context.user_data["voice_job"] = update.message.text.strip()
        context.user_data["adding_voice"] = False
        context.user_data["waiting_voice"] = True

        await update.message.reply_text(
            "🎙️ حالا خود ویس را همینجا ارسال کن."
        )

        return

    # =========================
    # عنوان ویس
    # =========================

    if context.user_data.get("waiting_voice_title"):

        title = update.message.text.strip()

        context.user_data["voice_title"] = title
        context.user_data["waiting_voice_title"] = False

        await update.message.reply_text(
            "✅ عنوان ذخیره شد."
        )

        return


# =========================
# دریافت ویس از ادمین
# =========================

async def receive_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get("waiting_voice"):
        return

    voice = update.message.voice

    job = context.user_data.get("voice_job")

    context.user_data["voice_file_id"] = voice.file_id
    context.user_data["waiting_voice"] = False
    context.user_data["waiting_voice_title"] = True

    await update.message.reply_text(
        f"🎙️ ویس برای شغل «{job}» دریافت شد.\n\n"
        "حالا عنوان ویس را بفرست.\n"
        "مثلاً:\n"
        "جلسه اول آشنایی با مسیر"
    )


# =========================
# ذخیره ویس
# =========================

async def save_voice_title(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get("waiting_voice_title"):
        return

    title = update.message.text.strip()

    job = context.user_data.get("voice_job")
    file_id = context.user_data.get("voice_file_id")

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO voices
        (job, title, file_id)
        VALUES (?, ?, ?)
    """, (job, title, file_id))

    conn.commit()
    conn.close()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ ویس با موفقیت اضافه شد.",
        reply_markup=admin_menu()
    )


# =========================
# دریافت فیش پرداخت
# =========================

async def receive_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id == ADMIN_ID:
        return

    if not update.message.photo:
        return

    photo = update.message.photo[-1]

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO payments
        (user_id, photo_id, status)
        VALUES (?, ?, 'pending')
    """, (
        update.effective_user.id,
        photo.file_id
    ))

    payment_id = cur.lastrowid

    conn.commit()
    conn.close()

    # ارسال فیش برای ادمین

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"approve_{payment_id}"
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_{payment_id}"
            )
        ]
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=(
            f"🧾 فیش پرداخت جدید\n\n"
            f"شماره فیش: #{payment_id}\n"
            f"👤 کاربر: {update.effective_user.id}\n"
            f"💰 مبلغ: {get_setting('price')}"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text(
        "✅ فیش شما دریافت شد.\n\n"
        "بعد از بررسی مدیریت، نتیجه به شما اعلام می‌شود."
    )


# =========================
# تأیید / رد فیش
# =========================

async def payment_action(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    action, payment_id = query.data.split("_")

    payment_id = int(payment_id)

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id
        FROM payments
        WHERE id=?
    """, (payment_id,))

    row = cur.fetchone()

    if not row:

        conn.close()
        return

    user_id = row[0]

    if action == "approve":

        cur.execute("""
            UPDATE payments
            SET status='approved'
            WHERE id=?
        """, (payment_id,))

        message = "✅ پرداخت شما تأیید شد."

    else:

        cur.execute("""
            UPDATE payments
            SET status='rejected'
            WHERE id=?
        """, (payment_id,))

        message = "❌ فیش پرداخت شما تأیید نشد."

    conn.commit()
    conn.close()

    await context.bot.send_message(
        chat_id=user_id,
        text=message
    )

    await query.edit_message_caption(
        caption=f"🧾 فیش #{payment_id}\n\nوضعیت: {message}"
    )


# =========================
# اجرای ربات
# =========================

def main():

    init_db()

    if not BOT_TOKEN:

        print("BOT_TOKEN تنظیم نشده.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("admin", admin)
    )

    app.add_handler(
        CallbackQueryHandler(
            payment_action,
            pattern=r"^(approve|reject)_\d+$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.VOICE,
            receive_voice
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_payment
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            save_voice_title
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_text
        )
    )

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
