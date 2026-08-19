import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import psycopg2

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

PORT = int(os.getenv("PORT", "10000"))


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")

    def log_message(self, format, *args):
        pass


def run_health_server():
    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(f"Health server running on port {PORT}")

    server.serve_forever()


threading.Thread(
    target=run_health_server,
    daemon=True
).start()


# =========================================================
# DATABASE
# =========================================================

def db():
    return psycopg2.connect(DATABASE_URL)


def init_db():

    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            first_name TEXT DEFAULT '',
            username TEXT DEFAULT '',
            balance BIGINT DEFAULT 0,
            level INTEGER DEFAULT 1,
            projects INTEGER DEFAULT 0,
            registered BOOLEAN DEFAULT FALSE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            active BOOLEAN DEFAULT TRUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS voices (
            id SERIAL PRIMARY KEY,
            job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
            title TEXT DEFAULT '',
            file_id TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_jobs (
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
            PRIMARY KEY(user_id, job_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            photo_id TEXT,
            amount BIGINT,
            status TEXT DEFAULT 'pending'
        )
    """)

    con.commit()

    cur.execute("SELECT COUNT(*) FROM jobs")
    count = cur.fetchone()[0]

    if count == 0:
        insert_default_jobs(cur)

    con.commit()

    cur.close()
    con.close()


def insert_default_jobs(cur):

    jobs = [
        "💫 1 تایپ",
        "💫 2 ترجمه",
        "💫 3 ادمین",
        "💫 4 پشتیبانی",
        "💫 5 دست نویسی",
        "💫 6 نویسندگی",
        "💫 7 تایپ صوتی",
        "💫 8 گویندگی",
        "💫 9 دایرکتر",
        "💫 10 ادمین اینستاگرام",
        "💫 11 ویراستاری",
        "💫 12 خلاصه نویسی",
    ]

    for name in jobs:
        cur.execute(
            "INSERT INTO jobs(name) VALUES(%s)",
            (name,)
        )


def get_setting(key, default=""):

    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT value FROM settings WHERE key=%s",
        (key,)
    )

    row = cur.fetchone()

    cur.close()
    con.close()

    if row:
        return row[0]

    return default


def set_setting(key, value):

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO settings(key, value)
        VALUES(%s, %s)
        ON CONFLICT(key)
        DO UPDATE SET value=EXCLUDED.value
    """, (key, value))

    con.commit()

    cur.close()
    con.close()


def save_user(user):

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO users(
            user_id,
            first_name,
            username
        )
        VALUES(%s, %s, %s)

        ON CONFLICT(user_id)
        DO UPDATE SET
            first_name=EXCLUDED.first_name,
            username=EXCLUDED.username
    """, (
        user.id,
        user.first_name or "",
        user.username or "",
    ))

    con.commit()

    cur.close()
    con.close()


# =========================================================
# DEFAULT SETTINGS
# =========================================================

DEFAULT_SETTINGS = {

    "welcome":
        "📣📣 روش‌های درآمدزایی مجموعه ما ⬇️⬇️\n\n"
        "💫 از منوی زیر شغل مورد نظر خودت رو انتخاب کن.",

    "jobs_intro":
        "📣📣 روش‌های درآمدزایی مجموعه ما ⬇️⬇️\n\n"
        "💫 شغل مورد نظر خودت رو انتخاب کن.\n\n"
        "می‌تونی چند شغل رو انتخاب کنی.",

    "start_text":
        "🚀 برای شروع درآمدزایی، شغل مورد نظر خودت رو انتخاب کن.",

    "about":
        "ℹ️ توضیحات مجموعه\n\n"
        "این متن از پنل مدیریت قابل تغییر است.",

    "start_button":
        "🚀 شروع درآمدزایی",

    "jobs_button":
        "💼 روش‌های درآمدزایی",

    "about_button":
        "ℹ️ درباره مجموعه",

    "back_button":
        "🔙 برگشت",

    "heard_button":
        "🎧 گوش کردم",

    "register_button":
        "💳 ادامه ثبت‌نام",

    "receipt_button":
        "📸 ارسال فیش",

    "level_button":
        "⭐ سطح من",

    "balance_button":
        "💰 موجودی",

    "card":
        "شماره کارت را از پنل مدیریت وارد کنید.",

    "price":
        "298000",

    "register_text":
        "💳 مراحل ثبت‌نام\n\n"
        "💰 مبلغ: {price:,} تومان\n\n"
        "💳 شماره کارت:\n"
        "{card}\n\n"
        "بعد از پرداخت، تصویر فیش را ارسال کنید.",

    "level_text":
        "⭐ سطح شما: {level}\n\n"
        "📁 پروژه‌های انجام شده: {projects}",

    "balance_text":
        "💰 موجودی شما:\n\n"
        "{balance:,} تومان",
}


def ensure_settings():

    con = db()
    cur = con.cursor()

    for key, value in DEFAULT_SETTINGS.items():

        cur.execute("""
            INSERT INTO settings(key, value)
            VALUES(%s, %s)
            ON CONFLICT(key)
            DO NOTHING
        """, (key, value))

    con.commit()

    cur.close()
    con.close()


# =========================================================
# MAIN MENU
# =========================================================

def main_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                get_setting("start_button"),
                callback_data="start"
            )
        ],

        [
            InlineKeyboardButton(
                get_setting("jobs_button"),
                callback_data="jobs"
            )
        ],

        [
            InlineKeyboardButton(
                get_setting("level_button"),
                callback_data="level"
            ),

            InlineKeyboardButton(
                get_setting("balance_button"),
                callback_data="balance"
            )
        ],

        [
            InlineKeyboardButton(
                get_setting("about_button"),
                callback_data="about"
            )
        ],

    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user(update.effective_user)

    await update.message.reply_text(
        get_setting("welcome"),
        reply_markup=main_menu()
    )


# =========================================================
# JOB MENU
# =========================================================

def jobs_menu(user_id):

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, name
        FROM jobs
        WHERE active=TRUE
        ORDER BY id
    """)

    jobs = cur.fetchall()

    cur.execute("""
        SELECT job_id
        FROM user_jobs
        WHERE user_id=%s
    """, (user_id,))

    selected = {
        row[0]
        for row in cur.fetchall()
    }

    cur.close()
    con.close()

    buttons = []

    for job_id, name in jobs:

        mark = "✅ " if job_id in selected else ""

        buttons.append([
            InlineKeyboardButton(
                mark + name,
                callback_data=f"select_job:{job_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            get_setting("heard_button"),
            callback_data="heard"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            get_setting("back_button"),
            callback_data="home"
        )
    ])

    return InlineKeyboardMarkup(buttons)


# =========================================================
# SEND JOBS
# =========================================================

async def show_jobs(query):

    await query.edit_message_text(
        get_setting("jobs_intro"),
        reply_markup=jobs_menu(
            query.from_user.id
        )
    )


# =========================================================
# SELECT JOB
# =========================================================

async def select_job(
    query,
    context,
    job_id
):

    user_id = query.from_user.id

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT job_id
        FROM user_jobs
        WHERE user_id=%s
    """, (user_id,))

    selected = {
        row[0]
        for row in cur.fetchall()
    }

    if job_id in selected:

        cur.execute("""
            DELETE FROM user_jobs
            WHERE user_id=%s
            AND job_id=%s
        """, (
            user_id,
            job_id
        ))

        con.commit()

        cur.close()
        con.close()

        await query.edit_message_reply_markup(
            reply_markup=jobs_menu(user_id)
        )

        return

    if len(selected) >= 4:

        cur.close()
        con.close()

        await query.answer(
            "⚠️ حداکثر ۴ شغل می‌توانی انتخاب کنی.",
            show_alert=True
        )

        return

    cur.execute("""
        INSERT INTO user_jobs(user_id, job_id)
        VALUES(%s, %s)
        ON CONFLICT DO NOTHING
    """, (
        user_id,
        job_id
    ))

    cur.execute(
        "SELECT name FROM jobs WHERE id=%s",
        (job_id,)
    )

    job = cur.fetchone()

    cur.execute("""
        SELECT id, title, file_id
        FROM voices
        WHERE job_id=%s
        ORDER BY id
    """, (job_id,))

    voices = cur.fetchall()

    con.commit()

    cur.close()
    con.close()

    if job:

        await context.bot.send_message(
            user_id,
            f"💼 {job[0]}"
        )

    if voices:

        for voice_id, title, file_id in voices:

            await context.bot.send_voice(
                user_id,
                file_id,
                caption=(
                    f"🎧 {title}"
                    if title
                    else "🎧 آموزش صوتی"
                )
            )

    else:

        await context.bot.send_message(
            user_id,
            "🎙️ هنوز ویسی برای این شغل قرار داده نشده است."
        )

    await query.edit_message_reply_markup(
        reply_markup=jobs_menu(user_id)
    )


# =========================================================
# ADMIN MENU
# =========================================================

def admin_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "💼 مدیریت شغل‌ها",
                callback_data="admin_jobs"
            )
        ],

        [
            InlineKeyboardButton(
                "🎙️ مدیریت ویس‌ها",
                callback_data="admin_voices"
            )
        ],

        [
            InlineKeyboardButton(
                "🎛️ تغییر متن‌ها و دکمه‌ها",
                callback_data="admin_texts"
            )
        ],

        [
            InlineKeyboardButton(
                "💳 پرداخت و ثبت‌نام",
                callback_data="admin_money"
            )
        ],

        [
            InlineKeyboardButton(
                "🧾 فیش‌های واریزی",
                callback_data="admin_payments"
            )
        ],

    ])


async def admin(update, context):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریت ندارید."
        )

        return

    await update.message.reply_text(
        "⚙️ پنل مدیریت",
        reply_markup=admin_menu()
    )


# =========================================================
# ADMIN JOBS
# =========================================================

def admin_jobs_menu():

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, name, active
        FROM jobs
        ORDER BY id
    """)

    jobs = cur.fetchall()

    cur.close()
    con.close()

    buttons = [

        [
            InlineKeyboardButton(
                "➕ افزودن شغل",
                callback_data="add_job"
            )
        ],

        [
            InlineKeyboardButton(
                "🗑️ حذف شغل",
                callback_data="delete_job"
            )
        ],

        [
            InlineKeyboardButton(
                "♻️ جایگزینی با ۱۲ شغل اصلی",
                callback_data="reset_jobs"
            )
        ],

    ]

    for job_id, name, active in jobs:

        status = "🟢" if active else "🔴"

        buttons.append([

            InlineKeyboardButton(
                f"{status} {job_id} - {name}",
                callback_data=f"edit_job:{job_id}"
            )

        ])

    buttons.append([

        InlineKeyboardButton(
            "🔙 پنل مدیریت",
            callback_data="admin_home"
        )

    ])

    return InlineKeyboardMarkup(buttons)


# =========================================================
# ADMIN VOICES JOBS
# =========================================================

def admin_voice_jobs():

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, name
        FROM jobs
        ORDER BY id
    """)

    jobs = cur.fetchall()

    cur.close()
    con.close()

    buttons = []

    for job_id, name in jobs:

        buttons.append([

            InlineKeyboardButton(
                name,
                callback_data=f"voice_job:{job_id}"
            )

        ])

    buttons.append([

        InlineKeyboardButton(
            "🔙 پنل مدیریت",
            callback_data="admin_home"
        )

    ])

    return InlineKeyboardMarkup(buttons)


# =========================================================
# ADMIN VOICES
# =========================================================

def voice_manage_menu(job_id):

    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT name FROM jobs WHERE id=%s",
        (job_id,)
    )

    job = cur.fetchone()

    cur.execute("""
        SELECT id, title
        FROM voices
        WHERE job_id=%s
        ORDER BY id
    """, (job_id,))

    voices = cur.fetchall()

    cur.close()
    con.close()

    buttons = [

        [
            InlineKeyboardButton(
                "➕ گذاشتن ویس جدید",
                callback_data=f"add_voice:{job_id}"
            )
        ]

    ]

    for voice_id, title in voices:

        buttons.append([

            InlineKeyboardButton(
                f"🗑️ حذف ویس {voice_id} - {title}",
                callback_data=f"delete_voice:{voice_id}"
            )

        ])

    buttons.append([

        InlineKeyboardButton(
            "🔙 انتخاب شغل",
            callback_data="admin_voices"
        )

    ])

    return (
        job[0] if job else "شغل",
        InlineKeyboardMarkup(buttons)
    )


# =========================================================
# ADMIN TEXTS
# =========================================================

TEXT_FIELDS = {

    "welcome": "👋 متن خوش‌آمدگویی",

    "jobs_intro": "💼 متن صفحه شغل‌ها",

    "start_text": "🚀 متن شروع",

    "about": "ℹ️ متن درباره مجموعه",

    "start_button": "🔘 دکمه شروع",

    "jobs_button": "🔘 دکمه شغل‌ها",

    "about_button": "🔘 دکمه درباره مجموعه",

    "back_button": "🔘 دکمه برگشت",

    "heard_button": "🔘 دکمه گوش کردم",

    "register_button": "🔘 دکمه ثبت‌نام",

    "receipt_button": "🔘 دکمه ارسال فیش",

    "level_button": "🔘 دکمه سطح",

    "balance_button": "🔘 دکمه موجودی",

    "register_text": "💳 متن ثبت‌نام",

    "level_text": "⭐ متن سطح",

    "balance_text": "💰 متن موجودی",

}


def admin_text_menu():

    buttons = []

    for key, title in TEXT_FIELDS.items():

        buttons.append([

            InlineKeyboardButton(
                title,
                callback_data=f"edit_text:{key}"
            )

        ])

    buttons.append([

        InlineKeyboardButton(
            "🔙 پنل مدیریت",
            callback_data="admin_home"
        )

    ])

    return InlineKeyboardMarkup(buttons)


# =========================================================
# CALLBACKS
# =========================================================

async def callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    data = query.data

    # -------------------------------
    # USER
    # -------------------------------

    if data == "home":

        await query.edit_message_text(
            get_setting("welcome"),
            reply_markup=main_menu()
        )

        return

    if data == "start":

        await query.edit_message_text(
            get_setting("start_text"),
            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        get_setting("jobs_button"),
                        callback_data="jobs"
                    )
                ],

                [
                    InlineKeyboardButton(
                        get_setting("back_button"),
                        callback_data="home"
                    )
                ]

            ])
        )

        return

    if data == "jobs":

        await show_jobs(query)

        return

    if data.startswith("select_job:"):

        job_id = int(
            data.split(":")[1]
        )

        await select_job(
            query,
            context,
            job_id
        )

        return

    if data == "heard":

        await query.edit_message_text(

            "🎧 عالی!\n\n"
            "حالا می‌توانی مراحل ثبت‌نام را ادامه بدهی.",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        get_setting("register_button"),
                        callback_data="register"
                    )
                ],

                [
                    InlineKeyboardButton(
                        get_setting("back_button"),
                        callback_data="jobs"
                    )
                ]

            ])

        )

        return

    if data == "register":

        price = int(
            get_setting("price", "298000")
        )

        text = get_setting(
            "register_text"
        ).format(
            price=price,
            card=get_setting("card")
        )

        await query.edit_message_text(

            text,

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        get_setting("receipt_button"),
                        callback_data="send_receipt"
                    )
                ],

                [
                    InlineKeyboardButton(
                        get_setting("back_button"),
                        callback_data="jobs"
                    )
                ]

            ])

        )

        return

    if data == "send_receipt":

        context.user_data[
            "waiting_receipt"
        ] = True

        await query.edit_message_text(
            "📸 تصویر فیش واریزی را همینجا ارسال کن."
        )

        return

    if data == "level":

        con = db()
        cur = con.cursor()

        cur.execute("""
            SELECT level, projects
            FROM users
            WHERE user_id=%s
        """, (
            query.from_user.id,
        ))

        row = cur.fetchone()

        cur.close()
        con.close()

        level = row[0] if row else 1
        projects = row[1] if row else 0

        await query.edit_message_text(

            get_setting(
                "level_text"
            ).format(
                level=level,
                projects=projects
            ),

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        get_setting("back_button"),
                        callback_data="home"
                    )
                ]

            ])

        )

        return

    if data == "balance":

        con = db()
        cur = con.cursor()

        cur.execute("""
            SELECT balance
            FROM users
            WHERE user_id=%s
        """, (
            query.from_user.id,
        ))

        row = cur.fetchone()

        cur.close()
        con.close()

        balance = row[0] if row else 0

        await query.edit_message_text(

            get_setting(
                "balance_text"
            ).format(
                balance=balance
            ),

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        get_setting("back_button"),
                        callback_data="home"
                    )
                ]

            ])

        )

        return

    if data == "about":

        await query.edit_message_text(

            get_setting("about"),

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        get_setting("back_button"),
                        callback_data="home"
                    )
                ]

            ])

        )

        return

    # -------------------------------
    # ADMIN SECURITY
    # -------------------------------

    if data.startswith("admin") or \
       data.startswith("edit_") or \
       data.startswith("add_") or \
       data.startswith("delete_") or \
       data.startswith("reset_") or \
       data.startswith("voice_") or \
       data.startswith("job_") or \
       data.startswith("payment"):

        if query.from_user.id != ADMIN_ID:

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True
            )

            return

    # -------------------------------
    # ADMIN HOME
    # -------------------------------

    if data == "admin_home":

        await query.edit_message_text(
            "⚙️ پنل مدیریت",
            reply_markup=admin_menu()
        )

        return

    # -------------------------------
    # ADMIN JOBS
    # -------------------------------

    if data == "admin_jobs":

        await query.edit_message_text(
            "💼 مدیریت شغل‌ها",
            reply_markup=admin_jobs_menu()
        )

        return

    if data == "reset_jobs":

        con = db()
        cur = con.cursor()

        cur.execute(
            "DELETE FROM user_jobs"
        )

        cur.execute(
            "DELETE FROM voices"
        )

        cur.execute(
            "DELETE FROM jobs"
        )

        insert_default_jobs(cur)

        con.commit()

        cur.close()
        con.close()

        await query.edit_message_text(

            "✅ انجام شد.\n\n"
            "شغل‌های قبلی حذف شدند و "
            "۱۲ شغل اصلی اضافه شدند.",

            reply_markup=admin_menu()
        )

        return

    if data == "add_job":

        context.user_data[
            "admin_action"
        ] = "add_job"

        await query.edit_message_text(
            "➕ اسم شغل جدید را بفرست."
        )

        return

    if data == "delete_job":

        context.user_data[
            "admin_action"
        ] = "delete_job"

        await query.edit_message_text(
            "🗑️ ID شغلی که می‌خواهی حذف کنی را بفرست.\n\n"
            "مثال: 3"
        )

        return

    if data.startswith("edit_job:"):

        job_id = int(
            data.split(":")[1]
        )

        context.user_data[
            "admin_action"
        ] = f"edit_job:{job_id}"

        await query.edit_message_text(
            "✏️ اسم جدید شغل را بفرست."
        )

        return

    # -------------------------------
    # ADMIN VOICES
    # -------------------------------

    if data == "admin_voices":

        await query.edit_message_text(
            "🎙️ اول شغل مورد نظر را انتخاب کن:",
            reply_markup=admin_voice_jobs()
        )

        return

    if data.startswith("voice_job:"):

        job_id = int(
            data.split(":")[1]
        )

        title, markup = voice_manage_menu(
            job_id
        )

        await query.edit_message_text(
            f"🎙️ مدیریت ویس‌های:\n{title}",
            reply_markup=markup
        )

        return

    if data.startswith("add_voice:"):

        job_id = int(
            data.split(":")[1]
        )

        context.user_data[
            "voice_job_id"
        ] = job_id

        context.user_data[
            "waiting_voice"
        ] = True

        await query.edit_message_text(
            "🎙️ حالا ویس را همینجا بفرست."
        )

        return

    if data.startswith("delete_voice:"):

        voice_id = int(
            data.split(":")[1]
        )

        con = db()
        cur = con.cursor()

        cur.execute(
            "DELETE FROM voices WHERE id=%s",
            (voice_id,)
        )

        con.commit()

        cur.close()
        con.close()

        await query.edit_message_text(
            "✅ ویس حذف شد.",
            reply_markup=admin_voice_jobs()
        )

        return

    # -------------------------------
    # ADMIN TEXTS
    # -------------------------------

    if data == "admin_texts":

        await query.edit_message_text(
            "🎛️ متن یا دکمه‌ای که می‌خواهی تغییر بدهی انتخاب کن:",
            reply_markup=admin_text_menu()
        )

        return

    if data.startswith("edit_text:"):

        key = data.split(
            ":",
            1
        )[1]

        context.user_data[
            "admin_action"
        ] = f"edit_text:{key}"

        current = get_setting(key)

        await query.edit_message_text(

            "✏️ مقدار جدید را بفرست.\n\n"
            "مقدار فعلی:\n"
            f"{current}"

        )

        return

    # -------------------------------
    # ADMIN MONEY
    # -------------------------------

    if data == "admin_money":

        await query.edit_message_text(

            "💳 تنظیمات پرداخت\n\n"

            f"شماره کارت:\n"
            f"{get_setting('card')}\n\n"

            f"مبلغ:\n"
            f"{int(get_setting('price', '298000')):,} تومان",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "💳 تغییر شماره کارت",
                        callback_data="edit_money:card"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "💰 تغییر مبلغ",
                        callback_data="edit_money:price"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin_home"
                    )
                ]

            ])

        )

        return

    if data == "edit_money:card":

        context.user_data[
            "admin_action"
        ] = "money_card"

        await query.edit_message_text(
            "💳 شماره کارت جدید را بفرست."
        )

        return

    if data == "edit_money:price":

        context.user_data[
            "admin_action"
        ] = "money_price"

        await query.edit_message_text(
            "💰 مبلغ جدید را فقط به عدد بفرست."
        )

        return

    # -------------------------------
    # ADMIN PAYMENTS
    # -------------------------------

    if data == "admin_payments":

        await query.edit_message_text(

            "🧾 فیش‌های واریزی\n\n"
            "هر فیش جدید برای ادمین ارسال می‌شود.",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin_home"
                    )
                ]

            ])

        )

        return

    # -------------------------------
    # PAYMENT
    # -------------------------------

    if data.startswith("payment:"):

        parts = data.split(":")

        action = parts[1]
        payment_id = int(parts[2])

        con = db()
        cur = con.cursor()

        cur.execute("""
            SELECT user_id, amount, status
            FROM payments
            WHERE id=%s
        """, (payment_id,))

        row = cur.fetchone()

        if not row:

            cur.close()
            con.close()

            return

        user_id, amount, status = row

        if status != "pending":

            cur.close()
            con.close()

            await query.answer(
                "این فیش قبلاً بررسی شده.",
                show_alert=True
            )

            return

        if action == "approve":

            cur.execute("""
                UPDATE payments
                SET status='approved'
                WHERE id=%s
            """, (payment_id,))

            cur.execute("""
                UPDATE users
                SET balance=balance+%s,
                    registered=TRUE
                WHERE user_id=%s
            """, (
                amount,
                user_id
            ))

            con.commit()

            message = (
                "✅ فیش شما تأیید شد.\n\n"
                f"💰 مبلغ {amount:,} تومان "
                "به موجودی شما اضافه شد."
            )

        else:

            cur.execute("""
                UPDATE payments
                SET status='rejected'
                WHERE id=%s
            """, (payment_id,))

            con.commit()

            message = (
                "❌ فیش شما تأیید نشد.\n\n"
                "لطفاً پرداخت را بررسی و دوباره ارسال کنید."
            )

        cur.close()
        con.close()

        await context.bot.send_message(
            user_id,
            message
        )

        await query.edit_message_caption(
            caption=(
                f"🧾 فیش #{payment_id}\n\n"
                f"{'✅ تأیید شد' if action == 'approve' else '❌ رد شد'}"
            )
        )

        return


# =========================================================
# ADMIN TEXT / JOB / VOICE INPUT
# =========================================================

async def admin_text_handler(
    update,
    context
):

    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text.strip()

    action = context.user_data.get(
        "admin_action"
    )

    # -------------------------------
    # ADD JOB
    # -------------------------------

    if action == "add_job":

        con = db()
        cur = con.cursor()

        cur.execute(
            "INSERT INTO jobs(name) VALUES(%s)",
            (text,)
        )

        con.commit()

        cur.close()
        con.close()

        context.user_data.pop(
            "admin_action",
            None
        )

        await update.message.reply_text(
            "✅ شغل اضافه شد.",
            reply_markup=admin_menu()
        )

        return

    # -------------------------------
    # DELETE JOB
    # -------------------------------

    if action == "delete_job":

        try:
            job_id = int(text)

        except ValueError:

            await update.message.reply_text(
                "❌ فقط ID عددی بفرست. مثال: 3"
            )

            return

        con = db()
        cur = con.cursor()

        cur.execute(
            "DELETE FROM jobs WHERE id=%s",
            (job_id,)
        )

        con.commit()

        cur.close()
        con.close()

        context.user_data.pop(
            "admin_action",
            None
        )

        await update.message.reply_text(
            "✅ شغل حذف شد.",
            reply_markup=admin_menu()
        )

        return

    # -------------------------------
    # EDIT JOB
    # -------------------------------

    if action and action.startswith(
        "edit_job:"
    ):

        job_id = int(
            action.split(":")[1]
        )

        con = db()
        cur = con.cursor()

        cur.execute("""
            UPDATE jobs
            SET name=%s
            WHERE id=%s
        """, (
            text,
            job_id
        ))

        con.commit()

        cur.close()
        con.close()

        context.user_data.pop(
            "admin_action",
            None
        )

        await update.message.reply_text(
            "✅ اسم شغل تغییر کرد.",
            reply_markup=admin_menu()
        )

        return

    # -------------------------------
    # EDIT TEXT
    # -------------------------------

    if action and action.startswith(
        "edit_text:"
    ):

        key = action.split(
            ":",
            1
        )[1]

        set_setting(
            key,
            text
        )

        context.user_data.pop(
            "admin_action",
            None
        )

        await update.message.reply_text(
            "✅ تغییر ذخیره شد.",
            reply_markup=admin_menu()
        )

        return

    # -------------------------------
    # MONEY CARD
    # -------------------------------

    if action == "money_card":

        set_setting(
            "card",
            text
        )

        context.user_data.pop(
            "admin_action",
            None
        )

        await update.message.reply_text(
            "✅ شماره کارت تغییر کرد.",
            reply_markup=admin_menu()
        )

        return

    # -------------------------------
    # MONEY PRICE
    # -------------------------------

    if action == "money_price":

        try:

            price = int(
                text.replace(",", "")
                    .replace("٬", "")
                    .replace("تومان", "")
                    .strip()
            )

        except ValueError:

            await update.message.reply_text(
                "❌ فقط مبلغ را به عدد بفرست."
            )

            return

        set_setting(
            "price",
            str(price)
        )

        context.user_data.pop(
            "admin_action",
            None
        )

        await update.message.reply_text(
            "✅ مبلغ تغییر کرد.",
            reply_markup=admin_menu()
        )

        return


# =========================================================
# VOICE HANDLER
# =========================================================

async def voice_handler(
    update,
    context
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get(
        "waiting_voice"
    ):
        return

    job_id = context.user_data.get(
        "voice_job_id"
    )

    if not job_id:
        return

    file_id = update.message.voice.file_id

    context.user_data[
        "voice_file_id"
    ] = file_id

    context.user_data[
        "waiting_voice"
    ] = False

    context.user_data[
        "waiting_voice_title"
    ] = True

    await update.message.reply_text(
        "🎙️ ویس دریافت شد.\n\n"
        "حالا اسم یا عنوان ویس را به صورت متن بفرست."
    )


# =========================================================
# VOICE TITLE
# =========================================================

async def voice_title_handler(
    update,
    context
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get(
        "waiting_voice_title"
    ):
        return

    title = update.message.text.strip()

    job_id = context.user_data.get(
        "voice_job_id"
    )

    file_id = context.user_data.get(
        "voice_file_id"
    )

    if not job_id or not file_id:
        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO voices(
            job_id,
            title,
            file_id
        )
        VALUES(%s, %s, %s)
    """, (
        job_id,
        title,
        file_id
    ))

    con.commit()

    cur.close()
    con.close()

    context.user_data.pop(
        "waiting_voice_title",
        None
    )

    context.user_data.pop(
        "voice_job_id",
        None
    )

    context.user_data.pop(
        "voice_file_id",
        None
    )

    await update.message.reply_text(
        "✅ ویس با موفقیت ذخیره شد.\n\n"
        "حالا کاربران آن شغل می‌توانند ویس را دریافت کنند.",
        reply_markup=admin_menu()
    )


# =========================================================
# RECEIPT HANDLER
# =========================================================

async def receipt_handler(
    update,
    context
):

    if not context.user_data.get(
        "waiting_receipt"
    ):
        return

    if update.effective_user.id == ADMIN_ID:
        return

    amount = int(
        get_setting(
            "price",
            "298000"
        )
    )

    photo_id = update.message.photo[-1].file_id

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO payments(
            user_id,
            photo_id,
            amount
        )
        VALUES(%s, %s, %s)
        RETURNING id
    """, (
        update.effective_user.id,
        photo_id,
        amount
    ))

    payment_id = cur.fetchone()[0]

    con.commit()

    cur.close()
    con.close()

    context.user_data[
        "waiting_receipt"
    ] = False

    await context.bot.send_photo(

        ADMIN_ID,

        photo_id,

        caption=(
            "🧾 فیش جدید\n\n"
            f"👤 User ID: {update.effective_user.id}\n"
            f"💰 مبلغ: {amount:,} تومان\n"
            f"🆔 فیش: #{payment_id}"
        ),

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=f"payment:approve:{payment_id}"
                ),

                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"payment:reject:{payment_id}"
                )
            ]

        ])

    )

    await update.message.reply_text(
        "✅ فیش دریافت شد.\n\n"
        "بعد از بررسی مدیریت، نتیجه برایت ارسال می‌شود."
    )


# =========================================================
# UNKNOWN ADMIN TEXT
# =========================================================

async def general_text(
    update,
    context
):

    if update.effective_user.id == ADMIN_ID:

        await admin_text_handler(
            update,
            context
        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    print(
        "BOT ERROR:",
        context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN در Environment Variables تنظیم نشده."
        )

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL در Environment Variables تنظیم نشده."
        )

    if not ADMIN_ID:
        raise RuntimeError(
            "ADMIN_ID در Environment Variables تنظیم نشده."
        )

    init_db()
    ensure_settings()

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            admin
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callback
        )
    )

    application.add_handler(
        MessageHandler(
            filters.VOICE,
            voice_handler
        ),
        group=0
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            receipt_handler
        ),
        group=1
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            voice_title_handler
        ),
        group=2
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            general_text
        ),
        group=3
    )

    application.add_error_handler(
        error_handler
    )

    print("Bot is running...")

    application.run_polling(
        drop_pending_updates=False
    )


if __name__ == "__main__":
    main()
