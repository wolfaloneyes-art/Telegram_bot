import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import psycopg2
from psycopg2 import pool

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
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PORT = int(os.getenv("PORT", "10000"))


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        return


def run_health_server():

    try:
        server = HTTPServer(
            ("0.0.0.0", PORT),
            HealthHandler
        )

        logger.info(
            "Health server listening on port %s",
            PORT
        )

        server.serve_forever()

    except Exception as e:
        logger.exception(
            "Health server error: %s",
            e
        )


threading.Thread(
    target=run_health_server,
    daemon=True
).start()


# =========================================================
# DATABASE
# =========================================================

db_pool = None


def create_pool():

    global db_pool

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    db_pool = pool.ThreadedConnectionPool(
        1,
        10,
        DATABASE_URL
    )


def execute(
    query,
    params=None,
    fetch=False,
    fetchone=False,
):

    global db_pool

    connection = None
    cursor = None

    try:

        connection = db_pool.getconn()

        cursor = connection.cursor()

        cursor.execute(
            query,
            params or ()
        )

        result = None

        if fetchone:
            result = cursor.fetchone()

        elif fetch:
            result = cursor.fetchall()

        connection.commit()

        return result

    except Exception:

        if connection:
            connection.rollback()

        raise

    finally:

        if cursor:
            cursor.close()

        if connection:
            db_pool.putconn(connection)


# =========================================================
# DEFAULT JOBS
# =========================================================

DEFAULT_JOBS = [
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


# =========================================================
# DATABASE INIT
# =========================================================

def init_database():

    execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            first_name TEXT DEFAULT '',
            username TEXT DEFAULT '',
            balance BIGINT DEFAULT 0,
            level INTEGER DEFAULT 1,
            projects INTEGER DEFAULT 0,
            registered BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS voices (
            id SERIAL PRIMARY KEY,
            job_id INTEGER NOT NULL
                REFERENCES jobs(id)
                ON DELETE CASCADE,
            title TEXT DEFAULT '',
            file_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS user_jobs (
            user_id BIGINT NOT NULL
                REFERENCES users(user_id)
                ON DELETE CASCADE,
            job_id INTEGER NOT NULL
                REFERENCES jobs(id)
                ON DELETE CASCADE,
            PRIMARY KEY(user_id, job_id)
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            amount BIGINT NOT NULL,
            photo_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    job_count = execute(
        "SELECT COUNT(*) FROM jobs",
        fetchone=True
    )[0]

    if job_count == 0:

        for job in DEFAULT_JOBS:

            execute(
                "INSERT INTO jobs(name) VALUES(%s)",
                (job,)
            )


# =========================================================
# SETTINGS
# =========================================================

DEFAULT_SETTINGS = {

    "welcome":
        "📣📣 روش‌های درآمدزایی مجموعه ما ⬇️⬇️\n\n"
        "💫 به مجموعه ما خوش آمدی.\n\n"
        "از منوی زیر گزینه مورد نظرت را انتخاب کن.",

    "about":
        "ℹ️ درباره مجموعه\n\n"
        "به مجموعه ما خوش آمدید.",

    "card":
        "شماره کارت را از پنل مدیریت وارد کنید.",

    "price":
        "298000",

}


def init_settings():

    for key, value in DEFAULT_SETTINGS.items():

        execute("""
            INSERT INTO settings(key, value)
            VALUES(%s, %s)
            ON CONFLICT(key) DO NOTHING
        """, (
            key,
            value
        ))


def get_setting(key):

    row = execute(
        "SELECT value FROM settings WHERE key=%s",
        (key,),
        fetchone=True
    )

    if row:
        return row[0]

    return ""


def set_setting(key, value):

    execute("""
        INSERT INTO settings(key, value)
        VALUES(%s, %s)
        ON CONFLICT(key)
        DO UPDATE SET value=EXCLUDED.value
    """, (
        key,
        value
    ))


# =========================================================
# USER
# =========================================================

def save_user(user):

    execute("""
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


# =========================================================
# MAIN MENU
# =========================================================

def main_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🚀 شروع درآمدزایی",
                callback_data="start_income"
            )
        ],

        [
            InlineKeyboardButton(
                "💼 روش‌های درآمدزایی",
                callback_data="jobs"
            )
        ],

        [
            InlineKeyboardButton(
                "⭐ سطح من",
                callback_data="level"
            ),

            InlineKeyboardButton(
                "💰 موجودی من",
                callback_data="balance"
            )
        ],

        [
            InlineKeyboardButton(
                "ℹ️ درباره مجموعه",
                callback_data="about"
            )
        ]

    ])


# =========================================================
# START
# =========================================================

async def start(update, context):

    save_user(update.effective_user)

    await update.message.reply_text(
        get_setting("welcome"),
        reply_markup=main_menu()
    )


# =========================================================
# JOB LIST
# =========================================================

def get_jobs():

    return execute("""
        SELECT id, name
        FROM jobs
        WHERE active=TRUE
        ORDER BY id
    """, fetch=True)


def get_selected_jobs(user_id):

    rows = execute("""
        SELECT job_id
        FROM user_jobs
        WHERE user_id=%s
    """, (
        user_id,
    ), fetch=True)

    return {
        row[0]
        for row in rows
    }


def jobs_keyboard(user_id):

    jobs = get_jobs()

    selected = get_selected_jobs(
        user_id
    )

    buttons = []

    for job_id, name in jobs:

        mark = "✅ " if job_id in selected else ""

        buttons.append([
            InlineKeyboardButton(
                mark + name,
                callback_data=f"job:{job_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✅ ادامه",
            callback_data="continue_jobs"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 برگشت",
            callback_data="home"
        )
    ])

    return InlineKeyboardMarkup(buttons)


# =========================================================
# SHOW JOBS
# =========================================================

async def show_jobs(query):

    await query.edit_message_text(
        "📣📣 روش‌های درآمدزایی مجموعه ما ⬇️⬇️\n\n"
        "💫 شغل مورد نظر خودت را انتخاب کن.\n\n"
        "می‌توانی چند مورد را انتخاب کنی.",
        reply_markup=jobs_keyboard(
            query.from_user.id
        )
    )


# =========================================================
# JOB SELECTION
# =========================================================

async def select_job(
    query,
    job_id
):

    user_id = query.from_user.id

    job = execute("""
        SELECT name
        FROM jobs
        WHERE id=%s
        AND active=TRUE
    """, (
        job_id,
    ), fetchone=True)

    if not job:

        await query.answer(
            "این شغل پیدا نشد.",
            show_alert=True
        )

        return

    existing = execute("""
        SELECT 1
        FROM user_jobs
        WHERE user_id=%s
        AND job_id=%s
    """, (
        user_id,
        job_id
    ), fetchone=True)

    if existing:

        execute("""
            DELETE FROM user_jobs
            WHERE user_id=%s
            AND job_id=%s
        """, (
            user_id,
            job_id
        ))

        await query.answer(
            "از انتخاب‌ها حذف شد."
        )

        await query.edit_message_reply_markup(
            reply_markup=jobs_keyboard(user_id)
        )

        return

    execute("""
        INSERT INTO user_jobs(
            user_id,
            job_id
        )
        VALUES(%s, %s)
        ON CONFLICT DO NOTHING
    """, (
        user_id,
        job_id
    ))

    await query.answer(
        "شغل انتخاب شد."
    )

    await query.message.reply_text(
        f"💼 {job[0]}\n\n"
        "🎧 آموزش‌های این شغل:"
    )

    voices = execute("""
        SELECT title, file_id
        FROM voices
        WHERE job_id=%s
        ORDER BY id
    """, (
        job_id,
    ), fetch=True)

    if not voices:

        await query.message.reply_text(
            "🎙️ هنوز آموزشی برای این شغل قرار داده نشده."
        )

    else:

        for title, file_id in voices:

            try:

                await query.message.reply_voice(
                    voice=file_id,
                    caption=title or "🎧 آموزش صوتی"
                )

            except Exception as e:

                logger.exception(
                    "Could not send voice: %s",
                    e
                )

    await query.edit_message_reply_markup(
        reply_markup=jobs_keyboard(user_id)
    )


# =========================================================
# CONTINUE
# =========================================================

async def continue_jobs(query):

    selected = get_selected_jobs(
        query.from_user.id
    )

    if not selected:

        await query.answer(
            "⚠️ حداقل یک شغل انتخاب کن.",
            show_alert=True
        )

        return

    await query.edit_message_text(

        "🎉 انتخاب شغل‌ها ثبت شد.\n\n"
        "حالا می‌توانی مراحل ثبت‌نام را ادامه بدهی.",

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "💳 ادامه ثبت‌نام",
                    callback_data="register"
                )
            ],

            [
                InlineKeyboardButton(
                    "💼 تغییر انتخاب‌ها",
                    callback_data="jobs"
                )
            ],

            [
                InlineKeyboardButton(
                    "🔙 منوی اصلی",
                    callback_data="home"
                )
            ]

        ])

    )


# =========================================================
# REGISTER
# =========================================================

async def register(query):

    price = int(
        get_setting("price") or "298000"
    )

    card = get_setting("card")

    await query.edit_message_text(

        "💳 ثبت‌نام\n\n"
        f"💰 مبلغ: {price:,} تومان\n\n"
        "💳 شماره کارت:\n"
        f"{card}\n\n"
        "بعد از پرداخت، تصویر فیش را ارسال کن.",

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "📸 ارسال فیش",
                    callback_data="send_receipt"
                )
            ],

            [
                InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="jobs"
                )
            ]

        ])

    )


# =========================================================
# LEVEL
# =========================================================

async def show_level(query):

    row = execute("""
        SELECT level, projects
        FROM users
        WHERE user_id=%s
    """, (
        query.from_user.id,
    ), fetchone=True)

    level = row[0] if row else 1
    projects = row[1] if row else 0

    await query.edit_message_text(

        "⭐ اطلاعات حساب\n\n"
        f"⭐ سطح: {level}\n"
        f"📁 پروژه‌های انجام‌شده: {projects}",

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )
            ]

        ])

    )


# =========================================================
# BALANCE
# =========================================================

async def show_balance(query):

    row = execute("""
        SELECT balance
        FROM users
        WHERE user_id=%s
    """, (
        query.from_user.id,
    ), fetchone=True)

    balance = row[0] if row else 0

    await query.edit_message_text(

        "💰 موجودی حساب\n\n"
        f"💰 موجودی شما: {balance:,} تومان",

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )
            ]

        ])

    )


# =========================================================
# ABOUT
# =========================================================

async def show_about(query):

    await query.edit_message_text(

        get_setting("about"),

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )
            ]

        ])

    )


# =========================================================
# ADMIN MENU
# =========================================================

def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🎙️ مدیریت ویس‌ها",
                callback_data="admin_voices"
            )
        ],

        [
            InlineKeyboardButton(
                "💼 مدیریت شغل‌ها",
                callback_data="admin_jobs"
            )
        ],

        [
            InlineKeyboardButton(
                "💳 تنظیمات پرداخت",
                callback_data="admin_payment"
            )
        ],

        [
            InlineKeyboardButton(
                "🎛️ تنظیمات متن",
                callback_data="admin_text"
            )
        ],

        [
            InlineKeyboardButton(
                "🧾 فیش‌های در انتظار",
                callback_data="admin_receipts"
            )
        ]

    ])


async def admin(update, context):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ دسترسی ندارید."
        )

        return

    await update.message.reply_text(
        "⚙️ پنل مدیریت",
        reply_markup=admin_keyboard()
    )


# =========================================================
# ADMIN VOICES
# =========================================================

def admin_voice_jobs_keyboard():

    jobs = get_jobs()

    buttons = []

    for job_id, name in jobs:

        buttons.append([
            InlineKeyboardButton(
                name,
                callback_data=f"admin_voice_job:{job_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 پنل مدیریت",
            callback_data="admin_home"
        )
    ])

    return InlineKeyboardMarkup(buttons)


async def admin_voices(query):

    await query.edit_message_text(

        "🎙️ یک شغل را انتخاب کن تا ویس‌هایش را مدیریت کنی:",

        reply_markup=admin_voice_jobs_keyboard()

    )


# =========================================================
# ADMIN VOICE LIST
# =========================================================

def admin_voice_list_keyboard(job_id):

    voices = execute("""
        SELECT id, title
        FROM voices
        WHERE job_id=%s
        ORDER BY id
    """, (
        job_id,
    ), fetch=True)

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
                f"🗑 حذف #{voice_id} - "
                f"{title or 'ویس'}",
                callback_data=f"delete_voice:{voice_id}"
            )

        ])

    buttons.append([

        InlineKeyboardButton(
            "🔙 لیست شغل‌ها",
            callback_data="admin_voices"
        )

    ])

    return InlineKeyboardMarkup(buttons)


async def admin_voice_job(
    query,
    job_id
):

    job = execute("""
        SELECT name
        FROM jobs
        WHERE id=%s
    """, (
        job_id,
    ), fetchone=True)

    name = job[0] if job else "شغل"

    await query.edit_message_text(

        f"🎙️ مدیریت ویس‌های:\n{name}",

        reply_markup=admin_voice_list_keyboard(
            job_id
        )

    )


# =========================================================
# ADD VOICE
# =========================================================

async def ask_voice(
    query,
    context,
    job_id
):

    context.user_data["voice_job_id"] = job_id
    context.user_data["waiting_voice"] = True

    await query.edit_message_text(

        "🎙️ حالا ویس را همینجا بفرست.\n\n"
        "ویس بعد از ارسال مستقیم ذخیره می‌شود."

    )


# =========================================================
# RECEIVE VOICE
# =========================================================

async def receive_voice(
    update,
    context
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get(
        "waiting_voice"
    ):

        await update.message.reply_text(

            "⚠️ اول از `/admin` وارد "
            "مدیریت ویس‌ها شو، شغل را انتخاب کن "
            "و «گذاشتن ویس جدید» را بزن."

        )

        return

    job_id = context.user_data.get(
        "voice_job_id"
    )

    if not job_id:

        await update.message.reply_text(
            "❌ شغل انتخاب نشده."
        )

        return

    file_id = update.message.voice.file_id

    execute("""
        INSERT INTO voices(
            job_id,
            title,
            file_id
        )
        VALUES(%s, %s, %s)
    """, (
        job_id,
        "🎧 آموزش صوتی",
        file_id
    ))

    context.user_data.pop(
        "voice_job_id",
        None
    )

    context.user_data.pop(
        "waiting_voice",
        None
    )

    await update.message.reply_text(

        "✅ ویس با موفقیت ذخیره شد.\n\n"
        "برای گذاشتن ویس بعدی، دوباره شغل را انتخاب کن."

    )


# =========================================================
# DELETE VOICE
# =========================================================

async def delete_voice(
    query,
    voice_id
):

    execute(
        "DELETE FROM voices WHERE id=%s",
        (voice_id,)
    )

    await query.edit_message_text(
        "✅ ویس حذف شد.",
        reply_markup=admin_keyboard()
    )


# =========================================================
# ADMIN JOBS
# =========================================================

def admin_jobs_keyboard():

    jobs = get_jobs()

    buttons = []

    for job_id, name in jobs:

        buttons.append([

            InlineKeyboardButton(
                f"✏️ {job_id} - {name}",
                callback_data=f"edit_job:{job_id}"
            )

        ])

    buttons.append([

        InlineKeyboardButton(
            "➕ افزودن شغل",
            callback_data="add_job"
        )

    ])

    buttons.append([

        InlineKeyboardButton(
            "🔙 پنل مدیریت",
            callback_data="admin_home"
        )

    ])

    return InlineKeyboardMarkup(buttons)


async def admin_jobs(query):

    await query.edit_message_text(

        "💼 مدیریت شغل‌ها\n\n"
        "برای تغییر نام روی شغل بزن:",

        reply_markup=admin_jobs_keyboard()

    )


# =========================================================
# EDIT JOB
# =========================================================

async def edit_job(
    query,
    context,
    job_id
):

    context.user_data[
        "editing_job"
    ] = job_id

    await query.edit_message_text(
        "✏️ نام جدید این شغل را بفرست."
    )


# =========================================================
# ADD JOB
# =========================================================

async def add_job(
    query,
    context
):

    context.user_data[
        "adding_job"
    ] = True

    await query.edit_message_text(
        "➕ نام شغل جدید را بفرست."
    )


# =========================================================
# ADMIN PAYMENT
# =========================================================

async def admin_payment(query):

    price = int(
        get_setting("price") or "298000"
    )

    card = get_setting("card")

    await query.edit_message_text(

        "💳 تنظیمات پرداخت\n\n"
        f"💰 مبلغ فعلی: {price:,} تومان\n"
        f"💳 کارت فعلی:\n{card}",

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "💳 تغییر شماره کارت",
                    callback_data="change_card"
                )
            ],

            [
                InlineKeyboardButton(
                    "💰 تغییر مبلغ",
                    callback_data="change_price"
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


# =========================================================
# PAYMENT SETTINGS
# =========================================================

async def change_card(
    query,
    context
):

    context.user_data[
        "change_card"
    ] = True

    await query.edit_message_text(
        "💳 شماره کارت جدید را بفرست."
    )


async def change_price(
    query,
    context
):

    context.user_data[
        "change_price"
    ] = True

    await query.edit_message_text(
        "💰 مبلغ جدید را فقط به عدد بفرست."
    )


# =========================================================
# ADMIN TEXT
# =========================================================

async def admin_text(query):

    await query.edit_message_text(

        "🎛️ تنظیمات متن\n\n"
        "در این نسخه متن‌های اصلی از کد تنظیم می‌شوند.",

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "🔙 پنل مدیریت",
                    callback_data="admin_home"
                )
            ]

        ])

    )


# =========================================================
# RECEIPT
# =========================================================

async def request_receipt(
    query,
    context
):

    context.user_data[
        "waiting_receipt"
    ] = True

    await query.edit_message_text(
        "📸 تصویر فیش پرداخت را همینجا ارسال کن."
    )


async def receive_receipt(
    update,
    context
):

    if not context.user_data.get(
        "waiting_receipt"
    ):
        return

    if not update.message.photo:
        return

    user_id = update.effective_user.id

    amount = int(
        get_setting("price") or "298000"
    )

    photo_id = (
        update.message.photo[-1].file_id
    )

    row = execute("""
        INSERT INTO payments(
            user_id,
            amount,
            photo_id
        )
        VALUES(%s, %s, %s)
        RETURNING id
    """, (
        user_id,
        amount,
        photo_id
    ), fetchone=True)

    payment_id = row[0]

    context.user_data.pop(
        "waiting_receipt",
        None
    )

    await context.bot.send_photo(

        chat_id=ADMIN_ID,

        photo=photo_id,

        caption=(
            "🧾 فیش جدید\n\n"
            f"👤 User ID: {user_id}\n"
            f"💰 مبلغ: {amount:,} تومان\n"
            f"🆔 شماره فیش: {payment_id}"
        ),

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=f"approve:{payment_id}"
                ),

                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"reject:{payment_id}"
                )
            ]

        ])

    )

    await update.message.reply_text(
        "✅ فیش دریافت شد.\n\n"
        "بعد از بررسی مدیریت نتیجه برایت ارسال می‌شود."
    )


# =========================================================
# PAYMENT REVIEW
# =========================================================

async def review_payment(
    query,
    context,
    payment_id,
    approve
):

    payment = execute("""
        SELECT user_id, amount, status
        FROM payments
        WHERE id=%s
    """, (
        payment_id,
    ), fetchone=True)

    if not payment:

        await query.answer(
            "فیش پیدا نشد.",
            show_alert=True
        )

        return

    user_id, amount, status = payment

    if status != "pending":

        await query.answer(
            "این فیش قبلاً بررسی شده.",
            show_alert=True
        )

        return

    if approve:

        execute("""
            UPDATE payments
            SET status='approved'
            WHERE id=%s
        """, (
            payment_id,
        ))

        execute("""
            UPDATE users
            SET balance=balance+%s,
                registered=TRUE
            WHERE user_id=%s
        """, (
            amount,
            user_id
        ))

        await context.bot.send_message(

            chat_id=user_id,

            text=(
                "✅ پرداخت شما تأیید شد.\n\n"
                f"💰 مبلغ {amount:,} تومان "
                "به حساب شما اضافه شد."
            )

        )

        text = "✅ تأیید شد"

    else:

        execute("""
            UPDATE payments
            SET status='rejected'
            WHERE id=%s
        """, (
            payment_id,
        ))

        await context.bot.send_message(

            chat_id=user_id,

            text=(
                "❌ فیش پرداخت شما تأیید نشد.\n\n"
                "لطفاً دوباره بررسی و ارسال کنید."
            )

        )

        text = "❌ رد شد"

    try:

        await query.edit_message_caption(
            caption=f"🧾 فیش #{payment_id}\n\n{text}"
        )

    except Exception:

        await query.edit_message_text(
            f"🧾 فیش #{payment_id}\n\n{text}"
        )


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def callback_handler(
    update,
    context
):

    query = update.callback_query

    try:

        await query.answer()

    except Exception:
        pass

    data = query.data

    # -----------------------------------------------------
    # USER
    # -----------------------------------------------------

    if data == "home":

        await query.edit_message_text(
            get_setting("welcome"),
            reply_markup=main_menu()
        )

        return

    if data == "start_income":

        await query.edit_message_text(

            "🚀 شروع درآمدزایی\n\n"
            "از لیست زیر شغل مورد نظر خودت را انتخاب کن:",

            reply_markup=jobs_keyboard(
                query.from_user.id
            )

        )

        return

    if data == "jobs":

        await show_jobs(query)

        return

    if data.startswith("job:"):

        job_id = int(
            data.split(":")[1]
        )

        await select_job(
            query,
            job_id
        )

        return

    if data == "continue_jobs":

        await continue_jobs(query)

        return

    if data == "register":

        await register(query)

        return

    if data == "send_receipt":

        await request_receipt(
            query,
            context
        )

        return

    if data == "level":

        await show_level(query)

        return

    if data == "balance":

        await show_balance(query)

        return

    if data == "about":

        await show_about(query)

        return

    # -----------------------------------------------------
    # ADMIN SECURITY
    # -----------------------------------------------------

    admin_actions = (
        "admin_",
        "add_voice:",
        "delete_voice:",
        "edit_job:",
        "add_job",
        "change_card",
        "change_price",
        "approve:",
        "reject:",
    )

    if data.startswith(admin_actions):

        if query.from_user.id != ADMIN_ID:

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True
            )

            return

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    if data == "admin_home":

        await query.edit_message_text(
            "⚙️ پنل مدیریت",
            reply_markup=admin_keyboard()
        )

        return

    if data == "admin_voices":

        await admin_voices(query)

        return

    if data.startswith("admin_voice_job:"):

        job_id = int(
            data.split(":")[1]
        )

        await admin_voice_job(
            query,
            job_id
        )

        return

    if data.startswith("add_voice:"):

        job_id = int(
            data.split(":")[1]
        )

        await ask_voice(
            query,
            context,
            job_id
        )

        return

    if data.startswith("delete_voice:"):

        voice_id = int(
            data.split(":")[1]
        )

        await delete_voice(
            query,
            voice_id
        )

        return

    if data == "admin_jobs":

        await admin_jobs(query)

        return

    if data.startswith("edit_job:"):

        job_id = int(
            data.split(":")[1]
        )

        await edit_job(
            query,
            context,
            job_id
        )

        return

    if data == "add_job":

        await add_job(
            query,
            context
        )

        return

    if data == "admin_payment":

        await admin_payment(query)

        return

    if data == "change_card":

        await change_card(
            query,
            context
        )

        return

    if data == "change_price":

        await change_price(
            query,
            context
        )

        return

    if data == "admin_text":

        await admin_text(query)

        return

    if data == "admin_receipts":

        await query.edit_message_text(
            "🧾 فیش‌های جدید از طریق پیام مستقیم برایت ارسال می‌شوند.",
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

    if data.startswith("approve:"):

        payment_id = int(
            data.split(":")[1]
        )

        await review_payment(
            query,
            context,
            payment_id,
            True
        )

        return

    if data.startswith("reject:"):

        payment_id = int(
            data.split(":")[1]
        )

        await review_payment(
            query,
            context,
            payment_id,
            False
        )

        return


# =========================================================
# ADMIN TEXT INPUT
# =========================================================

async def admin_text_handler(
    update,
    context
):

    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text.strip()

    # -----------------------------------------------------
    # EDIT JOB
    # -----------------------------------------------------

    job_id = context.user_data.get(
        "editing_job"
    )

    if job_id:

        execute("""
            UPDATE jobs
            SET name=%s
            WHERE id=%s
        """, (
            text,
            job_id
        ))

        context.user_data.pop(
            "editing_job",
            None
        )

        await update.message.reply_text(
            "✅ نام شغل تغییر کرد.",
            reply_markup=admin_keyboard()
        )

        return

    # -----------------------------------------------------
    # ADD JOB
    # -----------------------------------------------------

    if context.user_data.get(
        "adding_job"
    ):

        execute(
            "INSERT INTO jobs(name) VALUES(%s)",
            (text,)
        )

        context.user_data.pop(
            "adding_job",
            None
        )

        await update.message.reply_text(
            "✅ شغل جدید اضافه شد.",
            reply_markup=admin_keyboard()
        )

        return

    # -----------------------------------------------------
    # CARD
    # -----------------------------------------------------

    if context.user_data.get(
        "change_card"
    ):

        set_setting(
            "card",
            text
        )

        context.user_data.pop(
            "change_card",
            None
        )

        await update.message.reply_text(
            "✅ شماره کارت ذخیره شد.",
            reply_markup=admin_keyboard()
        )

        return

    # -----------------------------------------------------
    # PRICE
    # -----------------------------------------------------

    if context.user_data.get(
        "change_price"
    ):

        try:

            price = int(
                text.replace(",", "")
                    .replace("٬", "")
                    .replace("تومان", "")
                    .strip()
            )

        except ValueError:

            await update.message.reply_text(
                "❌ مبلغ را فقط به صورت عددی بفرست."
            )

            return

        set_setting(
            "price",
            str(price)
        )

        context.user_data.pop(
            "change_price",
            None
        )

        await update.message.reply_text(
            "✅ مبلغ ذخیره شد.",
            reply_markup=admin_keyboard()
        )

        return


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    logger.exception(
        "Unhandled bot error",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN در Environment Variables نیست."
        )

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL در Environment Variables نیست."
        )

    if not ADMIN_ID:

        raise RuntimeError(
            "ADMIN_ID در Environment Variables نیست."
        )

    logger.info(
        "Starting database..."
    )

    create_pool()

    init_database()

    init_settings()

    logger.info(
        "Database ready."
    )

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands

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

    # Callback buttons

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    # Voice

    application.add_handler(
        MessageHandler(
            filters.VOICE,
            receive_voice
        ),
        group=0
    )

    # Receipt photo

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_receipt
        ),
        group=1
    )

    # Admin text

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_text_handler
        ),
        group=2
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Bot is running..."
    )

    application.run_polling(
        drop_pending_updates=False
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
