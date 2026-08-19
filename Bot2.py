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

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 440194278
DB_NAME = "bot.db"


# =========================
# DATABASE
# =========================

def db():
    return sqlite3.connect(DB_NAME)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            level INTEGER DEFAULT 1,
            projects INTEGER DEFAULT 0,
            balance INTEGER DEFAULT 0,
            registered INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS voices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            title TEXT,
            file_id TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_jobs (
            user_id INTEGER,
            job_id INTEGER,
            PRIMARY KEY (user_id, job_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            photo_id TEXT,
            amount INTEGER,
            status TEXT DEFAULT 'pending'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    defaults = {
        "welcome":
            "سلام کاربر گرامی 🌹\n\n"
            "به ربات درآمدزایی ما خوش آمدید 💰\n\n"
            "اینجا می‌توانید مسیر شغلی مناسب خودتان را انتخاب کنید "
            "و آموزش‌های مربوط به آن را دریافت کنید.",

        "start_button": "🚀 شروع درآمدزایی",

        "start_text":
            "شما با روزی چند ساعت زمان گذاشتن می‌توانید "
            "مسیر درآمدزایی خودتان را شروع کنید. 💰\n\n"
            "برای شروع روی دکمه زیر کلیک کنید 👇",

        "jobs_text":
            "💼 شغل‌های مورد نظر خودتان را انتخاب کنید.\n\n"
            "با انتخاب هر شغل، توضیحات و ویس‌های مربوط به آن "
            "برای شما ارسال می‌شود.\n\n"
            "حداکثر ۴ شغل می‌توانید انتخاب کنید.",

        "heard_text":
            "🎧 گوش کردم.\n\n"
            "حالا شغل‌هایی که مدنظر دارید را انتخاب کنید.\n\n"
            "حداکثر ۴ شغل.",

        "register_text":
            "💳 مراحل ثبت‌نام\n\n"
            "برای ثبت‌نام مبلغ {price:,} تومان پرداخت کنید.\n\n"
            "این مبلغ در موجودی ربات شما ثبت می‌شود و طبق "
            "شرایط سرویس، امکان برداشت آن فراهم خواهد شد.\n\n"
            "💳 شماره کارت:\n"
            "{card}\n\n"
            "بعد از پرداخت تصویر فیش را ارسال کنید.",

        "about":
            "ℹ️ توضیحات\n\n"
            "توضیحات کسب‌وکار خودتان را از پنل مدیریت تغییر دهید.",

        "card":
            "شماره کارت را از پنل مدیریت تنظیم کنید.",

        "price": "298000",

        "level_text":
            "⭐ سطح شما: {level}\n\n"
            "📁 پروژه‌های انجام‌شده: {projects}\n\n"
            "🎯 با انجام هر ۵ پروژه وارد سطح بعدی می‌شوید.",

        "balance_text":
            "💰 موجودی شما:\n\n"
            "{balance:,} تومان",
    }

    for key, value in defaults.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
            (key, value)
        )

    sample_jobs = [
        "💻 برنامه‌نویسی",
        "🎨 طراحی گرافیک",
        "📱 تولید محتوا",
        "🎬 تدوین ویدئو",
        "📈 دیجیتال مارکتینگ",
        "🎙️ گویندگی",
    ]

    for job in sample_jobs:
        cur.execute(
            "INSERT OR IGNORE INTO jobs(name) VALUES(?)",
            (job,)
        )

    con.commit()
    con.close()


def get_setting(key):
    con = db()
    row = con.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,)
    ).fetchone()
    con.close()

    return row[0] if row else ""


def set_setting(key, value):
    con = db()

    con.execute(
        "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
        (key, value)
    )

    con.commit()
    con.close()


def save_user(user):
    con = db()

    con.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, first_name, username)
        VALUES (?, ?, ?)
        """,
        (
            user.id,
            user.first_name or "",
            user.username or "",
        )
    )

    con.commit()
    con.close()


# =========================
# MAIN MENU
# =========================

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                get_setting("start_button"),
                callback_data="start_income"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ سطح من",
                callback_data="level"
            ),
            InlineKeyboardButton(
                "💰 موجودی",
                callback_data="balance"
            )
        ],
        [
            InlineKeyboardButton(
                "💼 شغل‌ها",
                callback_data="jobs"
            ),
            InlineKeyboardButton(
                "ℹ️ توضیحات",
                callback_data="about"
            )
        ]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)

    await update.message.reply_text(
        get_setting("welcome"),
        reply_markup=main_menu()
    )


# =========================
# JOB MENU
# =========================

def jobs_menu(user_id):
    con = db()

    jobs = con.execute(
        "SELECT id,name FROM jobs WHERE active=1 ORDER BY id"
    ).fetchall()

    selected = {
        row[0]
        for row in con.execute(
            "SELECT job_id FROM user_jobs WHERE user_id=?",
            (user_id,)
        ).fetchall()
    }

    con.close()

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
            "🎧 گوش کردم",
            callback_data="heard"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 برگشت",
            callback_data="start_income"
        )
    ])

    return InlineKeyboardMarkup(buttons)


async def show_jobs(query):
    await query.edit_message_text(
        get_setting("jobs_text"),
        reply_markup=jobs_menu(query.from_user.id)
    )


# =========================
# SELECT JOB
# =========================

async def select_job(query, context):

    user_id = query.from_user.id
    job_id = int(query.data.split(":")[1])

    con = db()

    selected = {
        row[0]
        for row in con.execute(
            "SELECT job_id FROM user_jobs WHERE user_id=?",
            (user_id,)
        ).fetchall()
    }

    if job_id in selected:

        con.execute(
            """
            DELETE FROM user_jobs
            WHERE user_id=? AND job_id=?
            """,
            (user_id, job_id)
        )

        con.commit()
        con.close()

        await query.edit_message_reply_markup(
            reply_markup=jobs_menu(user_id)
        )

        return

    if len(selected) >= 4:

        con.close()

        await query.answer(
            "⚠️ حداکثر ۴ شغل می‌توانید انتخاب کنید.",
            show_alert=True
        )

        return

    con.execute(
        """
        INSERT INTO user_jobs(user_id,job_id)
        VALUES(?,?)
        """,
        (user_id, job_id)
    )

    job = con.execute(
        "SELECT name FROM jobs WHERE id=?",
        (job_id,)
    ).fetchone()

    voices = con.execute(
        """
        SELECT title,file_id
        FROM voices
        WHERE job_id=?
        ORDER BY id
        """,
        (job_id,)
    ).fetchall()

    con.commit()
    con.close()

    if job:
        await context.bot.send_message(
            user_id,
            f"💼 شغل انتخاب‌شده:\n{job[0]}"
        )

    if voices:

        for title, file_id in voices:

            await context.bot.send_voice(
                user_id,
                file_id,
                caption=f"🎧 {title}"
            )

    else:

        await context.bot.send_message(
            user_id,
            "🎙️ هنوز ویسی برای این شغل قرار داده نشده است."
        )

    await query.edit_message_reply_markup(
        reply_markup=jobs_menu(user_id)
    )


# =========================
# ADMIN MENU
# =========================

def admin_menu():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎛️ تغییر متن‌ها و دکمه‌ها",
                callback_data="admin_texts"
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
                "🎙️ مدیریت ویس‌ها",
                callback_data="admin_voices"
            )
        ],
        [
            InlineKeyboardButton(
                "💳 شماره کارت و مبلغ",
                callback_data="admin_money"
            )
        ],
        [
            InlineKeyboardButton(
                "🧾 فیش‌های واریزی",
                callback_data="admin_payments"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 کاربران",
                callback_data="admin_users"
            )
        ]
    ])


async def admin_command(update, context):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریت ندارید."
        )

        return

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\n"
        "از اینجا می‌توانید تنظیمات ربات را تغییر دهید.",
        reply_markup=admin_menu()
    )


# =========================
# ADMIN TEXT MENU
# =========================

def admin_text_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "👋 خوش‌آمدگویی",
                callback_data="edit:welcome"
            )
        ],

        [
            InlineKeyboardButton(
                "🚀 متن شروع",
                callback_data="edit:start_text"
            )
        ],

        [
            InlineKeyboardButton(
                "💼 متن شغل‌ها",
                callback_data="edit:jobs_text"
            )
        ],

        [
            InlineKeyboardButton(
                "🎧 متن گوش کردم",
                callback_data="edit:heard_text"
            )
        ],

        [
            InlineKeyboardButton(
                "💳 متن ثبت‌نام",
                callback_data="edit:register_text"
            )
        ],

        [
            InlineKeyboardButton(
                "ℹ️ توضیحات",
                callback_data="edit:about"
            )
        ],

        [
            InlineKeyboardButton(
                "🔘 اسم دکمه شروع",
                callback_data="edit:start_button"
            )
        ],

        [
            InlineKeyboardButton(
                "⭐ متن سطح",
                callback_data="edit:level_text"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 متن موجودی",
                callback_data="edit:balance_text"
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 پنل مدیریت",
                callback_data="admin_home"
            )
        ]

    ])


# =========================
# ADMIN JOBS
# =========================

def admin_jobs_menu():

    con = db()

    jobs = con.execute(
        "SELECT id,name,active FROM jobs ORDER BY id"
    ).fetchall()

    con.close()

    buttons = []

    buttons.append([
        InlineKeyboardButton(
            "➕ افزودن شغل",
            callback_data="job_add"
        )
    ])

    for job_id, name, active in jobs:

        status = "🟢" if active else "🔴"

        buttons.append([
            InlineKeyboardButton(
                f"{status} {job_id} - {name}",
                callback_data=f"job_edit:{job_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🗑️ حذف شغل",
            callback_data="job_delete"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 پنل مدیریت",
            callback_data="admin_home"
        )
    ])

    return InlineKeyboardMarkup(buttons)


# =========================
# ADMIN VOICES
# =========================

def admin_voice_jobs():

    con = db()

    jobs = con.execute(
        "SELECT id,name FROM jobs ORDER BY id"
    ).fetchall()

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


# =========================
# ADMIN CALLBACK
# =========================

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data

    # =====================
    # USER
    # =====================

    if data == "home":

        await query.edit_message_text(
            "🏠 منوی اصلی",
            reply_markup=main_menu()
        )

        return

    if data == "start_income":

        await query.edit_message_text(
            get_setting("start_text"),

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🚀 شروع",
                        callback_data="choose_jobs"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 برگشت",
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    if data == "choose_jobs":

        await show_jobs(query)

        return

    if data == "jobs":

        await show_jobs(query)

        return

    if data.startswith("job:"):

        await select_job(query, context)

        return

    if data == "heard":

        await query.edit_message_text(

            get_setting("heard_text"),

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "💳 ادامه ثبت‌نام",
                        callback_data="register"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 برگشت",
                        callback_data="choose_jobs"
                    )
                ]

            ])
        )

        return

    if data == "register":

        price = int(
            get_setting("price") or "298000"
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
                        "📸 ارسال فیش",
                        callback_data="receipt"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 برگشت",
                        callback_data="choose_jobs"
                    )
                ]

            ])
        )

        return

    if data == "receipt":

        context.user_data[
            "waiting_receipt"
        ] = True

        await query.edit_message_text(
            "📸 تصویر فیش واریزی را ارسال کنید."
        )

        return

    if data == "level":

        con = db()

        row = con.execute(
            """
            SELECT level,projects
            FROM users
            WHERE user_id=?
            """,
            (query.from_user.id,)
        ).fetchone()

        con.close()

        if row:
            level, projects = row
        else:
            level, projects = 1, 0

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
                        "🔙 برگشت",
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    if data == "balance":

        con = db()

        row = con.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id=?
            """,
            (query.from_user.id,)
        ).fetchone()

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
                        "🔙 برگشت",
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
                        "🔙 برگشت",
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    # =====================
    # ADMIN SECURITY
    # =====================

    if query.from_user.id != ADMIN_ID:

        if data.startswith("admin") or \
           data.startswith("edit:") or \
           data.startswith("job_") or \
           data.startswith("voice_") or \
           data.startswith("money_") or \
           data.startswith("payment_"):

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True
            )

            return

    # =====================
    # ADMIN HOME
    # =====================

    if data == "admin_home":

        await query.edit_message_text(
            "⚙️ پنل مدیریت",
            reply_markup=admin_menu()
        )

        return

    # =====================
    # ADMIN TEXTS
    # =====================

    if data == "admin_texts":

        await query.edit_message_text(
            "🎛️ چه چیزی را می‌خواهید تغییر دهید؟",
            reply_markup=admin_text_menu()
        )

        return

    if data.startswith("edit:"):

        key = data.split(":", 1)[1]

        context.user_data[
            "editing_setting"
        ] = key

        instructions = {

            "welcome":
                "👋 متن خوش‌آمدگویی جدید را بفرست.",

            "start_text":
                "🚀 متن مرحله شروع را بفرست.",

            "jobs_text":
                "💼 متن صفحه شغل‌ها را بفرست.",

            "heard_text":
                "🎧 متن مرحله گوش کردم را بفرست.",

            "register_text":
                "💳 متن ثبت‌نام را بفرست.\n\n"
                "برای نمایش مبلغ از {price} و "
                "برای شماره کارت از {card} استفاده کن.",

            "about":
                "ℹ️ متن توضیحات جدید را بفرست.",

            "start_button":
                "🔘 اسم جدید دکمه شروع را بفرست.",

            "level_text":
                "⭐ متن سطح را بفرست.\n\n"
                "می‌توانی از {level} و {projects} استفاده کنی.",

            "balance_text":
                "💰 متن موجودی را بفرست.\n\n"
                "می‌توانی از {balance} استفاده کنی."
        }

        await query.edit_message_text(
            instructions.get(
                key,
                "متن جدید را بفرست."
            )
        )

        return

    # =====================
    # ADMIN JOBS
    # =====================

    if data == "admin_jobs":

        await query.edit_message_text(
            "💼 مدیریت شغل‌ها",
            reply_markup=admin_jobs_menu()
        )

        return

    if data == "job_add":

        context.user_data[
            "job_action"
        ] = "add"

        await query.edit_message_text(
            "➕ اسم شغل جدید را ارسال کن."
        )

        return

    if data == "job_delete":

        context.user_data[
            "job_action"
        ] = "delete"

        await query.edit_message_text(
            "🗑️ شماره ID شغلی که می‌خواهی حذف شود را بفرست."
        )

        return

    if data.startswith("job_edit:"):

        job_id = int(
            data.split(":")[1]
        )

        context.user_data[
            "job_action"
        ] = f"edit:{job_id}"

        await query.edit_message_text(
            "✏️ اسم جدید این شغل را بفرست."
        )

        return

    # =====================
    # ADMIN VOICES
    # =====================

    if data == "admin_voices":

        await query.edit_message_text(
            "🎙️ اول شغلی را انتخاب کن:",
            reply_markup=admin_voice_jobs()
        )

        return

    if data.startswith("voice_job:"):

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
            "🎙️ ویس را همینجا ارسال کن.\n\n"
            "بعد از ارسال ویس، عنوان آن را از تو می‌پرسم."
        )

        return

    # =====================
    # ADMIN MONEY
    # =====================

    if data == "admin_money":

        price = int(
            get_setting("price") or 0
        )

        await query.edit_message_text(

            "💳 تنظیمات پرداخت\n\n"
            f"شماره کارت:\n{get_setting('card')}\n\n"
            f"مبلغ ثبت‌نام:\n{price:,} تومان",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "💳 تغییر شماره کارت",
                        callback_data="money_card"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "💰 تغییر مبلغ",
                        callback_data="money_price"
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

    if data == "money_card":

        context.user_data[
            "money_action"
        ] = "card"

        await query.edit_message_text(
            "💳 شماره کارت جدید را بفرست."
        )

        return

    if data == "money_price":

        context.user_data[
            "money_action"
        ] = "price"

        await query.edit_message_text(
            "💰 مبلغ جدید را فقط به عدد بفرست.\nمثال:\n298000"
        )

        return

    # =====================
    # ADMIN PAYMENTS
    # =====================

    if data == "admin_payments":

        await query.edit_message_text(
            "🧾 فیش‌های واریزی از اینجا برای شما ارسال می‌شوند.\n\n"
            "هر فیش جدید همراه دکمه تأیید و رد برای ادمین ارسال خواهد شد.",
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

    # =====================
    # PAYMENT ACTION
    # =====================

    if data.startswith("payment:"):

        parts = data.split(":")

        action = parts[1]
        payment_id = int(parts[2])

        con = db()

        payment = con.execute(
            """
            SELECT user_id,amount,status
            FROM payments
            WHERE id=?
            """,
            (payment_id,)
        ).fetchone()

        if not payment:

            con.close()
            return

        user_id, amount, status = payment

        if status != "pending":

            con.close()

            await query.answer(
                "این فیش قبلاً بررسی شده.",
                show_alert=True
            )

            return

        if action == "approve":

            con.execute(
                """
                UPDATE payments
                SET status='approved'
                WHERE id=?
                """,
                (payment_id,)
            )

            con.execute(
                """
                UPDATE users
                SET balance=balance+?,
                    registered=1
                WHERE user_id=?
                """,
                (amount, user_id)
            )

            message = (
                "✅ پرداخت شما تأیید شد.\n\n"
                f"💰 مبلغ {amount:,} تومان "
                "به موجودی شما اضافه شد."
            )

            caption = (
                f"✅ فیش #{payment_id} تأیید شد."
            )

        else:

            con.execute(
                """
                UPDATE payments
                SET status='rejected'
                WHERE id=?
                """,
                (payment_id,)
            )

            message = (
                "❌ فیش پرداخت شما تأیید نشد.\n\n"
                "لطفاً پرداخت را بررسی و دوباره ارسال کنید."
            )

            caption = (
                f"❌ فیش #{payment_id} رد شد."
            )

        con.commit()
        con.close()

        await context.bot.send_message(
            user_id,
            message
        )

        try:
            await query.edit_message_caption(
                caption=caption
            )
        except Exception:
            pass

        return


# =========================
# USER RECEIPT
# =========================

async def receipt_handler(update, context):

    if update.effective_user.id == ADMIN_ID:
        return

    if not context.user_data.get(
        "waiting_receipt"
    ):
        return

    photo = update.message.photo[-1]

    amount = int(
        get_setting("price") or 298000
    )

    con = db()

    cur = con.cursor()

    cur.execute(
        """
        INSERT INTO payments
        (user_id,photo_id,amount,status)
        VALUES(?,?,?,'pending')
        """,
        (
            update.effective_user.id,
            photo.file_id,
            amount
        )
    )

    payment_id = cur.lastrowid

    con.commit()
    con.close()

    context.user_data[
        "waiting_receipt"
    ] = False

    await context.bot.send_photo(

        ADMIN_ID,

        photo.file_id,

        caption=(
            "🧾 فیش جدید\n\n"
            f"👤 کاربر: {update.effective_user.id}\n"
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
        "✅ فیش شما دریافت شد.\n\n"
        "بعد از بررسی مدیریت، نتیجه برای شما ارسال می‌شود."
    )


# =========================
# ADMIN VOICE
# =========================

async def voice_handler(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get(
        "waiting_voice"
    ):
        return

    context.user_data[
        "voice_file_id"
    ] = update.message.voice.file_id

    context.user_data[
        "waiting_voice"
    ] = False

    context.user_data[
        "waiting_voice_title"
    ] = True

    await update.message.reply_text(
        "🎙️ ویس دریافت شد.\n\n"
        "حالا عنوان ویس را بفرست.\n"
        "مثلاً:\n"
        "قسمت اول آموزش"
    )


# =========================
# ADMIN TEXT INPUT
# =========================

async def admin_text_handler(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text.strip()

    # ---------------------
    # EDIT SETTINGS
    # ---------------------

    if context.user_data.get(
        "editing_setting"
    ):

        key = context.user_data.pop(
            "editing_setting"
        )

        set_setting(
            key,
            text
        )

        await update.message.reply_text(
            "✅ تغییر ذخیره شد.",
            reply_markup=admin_menu()
        )

        return

    # ---------------------
    # JOB ACTION
    # ---------------------

    if context.user_data.get(
        "job_action"
    ):

        action = context.user_data.pop(
            "job_action"
        )

        con = db()

        try:

            if action == "add":

                con.execute(
                    "INSERT INTO jobs(name) VALUES(?)",
                    (text,)
                )

                message = "✅ شغل جدید اضافه شد."

            elif action == "delete":

                job_id = int(text)

                con.execute(
                    "DELETE FROM jobs WHERE id=?",
                    (job_id,)
                )

                con.execute(
                    "DELETE FROM voices WHERE job_id=?",
                    (job_id,)
                )

                con.execute(
                    "DELETE FROM user_jobs WHERE job_id=?",
                    (job_id,)
                )

                message = "✅ شغل حذف شد."

            elif action.startswith(
                "edit:"
            ):

                job_id = int(
                    action.split(":")[1]
                )

                con.execute(
                    """
                    UPDATE jobs
                    SET name=?
                    WHERE id=?
                    """,
                    (text, job_id)
                )

                message = "✅ نام شغل تغییر کرد."

            else:

                message = "❌ عملیات نامعتبر است."

            con.commit()

        except Exception:

            message = (
                "❌ عملیات انجام نشد.\n"
                "ورودی را بررسی کنید."
            )

        con.close()

        await update.message.reply_text(
            message,
            reply_markup=admin_menu()
        )

        return

    # ---------------------
    # VOICE TITLE
    # ---------------------

    if context.user_data.get(
        "waiting_voice_title"
    ):

        title = text

        job_id = context.user_data.pop(
            "voice_job_id"
        )

        file_id = context.user_data.pop(
            "voice_file_id"
        )

        context.user_data.pop(
            "waiting_voice_title"
        )

        con = db()

        con.execute(
            """
            INSERT INTO voices
            (job_id,title,file_id)
            VALUES(?,?,?)
            """,
            (
                job_id,
                title,
                file_id
            )
        )

        con.commit()
        con.close()

        await update.message.reply_text(
            "✅ ویس ذخیره شد.\n\n"
            "برای اضافه‌کردن ویس بعدی دوباره /admin را بزن.",
            reply_markup=admin_menu()
        )

        return

    # ---------------------
    # MONEY
    # ---------------------

    if context.user_data.get(
        "money_action"
    ):

        action = context.user_data.pop(
            "money_action"
        )

        if action == "card":

            set_setting(
                "card",
                text
            )

            await update.message.reply_text(
                "✅ شماره کارت تغییر کرد.",
                reply_markup=admin_menu()
            )

            return

        if action == "price":

            try:

                price = int(
                    text
                    .replace(",", "")
                    .replace("٬", "")
                    .replace("تومان", "")
                    .strip()
                )

                set_setting(
                    "price",
                    str(price)
                )

                await update.message.reply_text(
                    "✅ مبلغ تغییر کرد.",
                    reply_markup=admin_menu()
                )

            except ValueError:

                await update.message.reply_text(
                    "❌ مبلغ را فقط به صورت عدد بفرست."
                )

            return


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN در Environment Variables وجود ندارد."
        )

    init_db()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            callback
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receipt_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.VOICE,
            voice_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_text_handler
        )
    )

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
