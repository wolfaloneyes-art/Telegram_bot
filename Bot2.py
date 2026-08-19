import os
import psycopg2
from psycopg2.extras import RealDictCursor

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

ADMIN_ID = 440194278


# =========================================================
# DATABASE
# =========================================================

def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db():

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            level INTEGER DEFAULT 1,
            projects INTEGER DEFAULT 0,
            balance BIGINT DEFAULT 0,
            registered INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS voices (
            id SERIAL PRIMARY KEY,
            job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
            title TEXT,
            file_id TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_jobs (
            user_id BIGINT,
            job_id INTEGER,
            PRIMARY KEY(user_id, job_id)
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
            "اینجا می‌توانید شغل مورد علاقه خودتان را انتخاب کنید "
            "و آموزش‌های مربوط به آن را دریافت کنید.",

        "start_button":
            "🚀 شروع درآمدزایی",

        "start_text":
            "شما با روزی چند ساعت زمان گذاشتن می‌توانید "
            "مسیر درآمدزایی خودتان را شروع کنید. 💰\n\n"
            "برای شروع روی دکمه زیر کلیک کنید 👇",

        "jobs_text":
            "💼 شغل‌های مورد نظر خودتان را انتخاب کنید.\n\n"
            "با انتخاب هر شغل، توضیحات و ویس‌های مربوط به آن "
            "برای شما ارسال می‌شود.\n\n"
            "حداکثر ۴ شغل انتخاب کنید.",

        "heard_text":
            "🎧 گوش کردم.\n\n"
            "حالا شغل‌هایی که مدنظر دارید را انتخاب کنید.\n\n"
            "حداکثر ۴ شغل.",

        "register_text":
            "💳 مراحل ثبت‌نام\n\n"
            "برای ثبت‌نام مبلغ {price:,} تومان پرداخت کنید.\n\n"
            "💳 شماره کارت:\n"
            "{card}\n\n"
            "بعد از پرداخت تصویر فیش را ارسال کنید.",

        "about":
            "ℹ️ توضیحات\n\n"
            "توضیحات کسب‌وکار را از پنل مدیریت تغییر دهید.",

        "card":
            "شماره کارت را از پنل مدیریت وارد کنید.",

        "price":
            "298000",

        "level_text":
            "⭐ سطح شما: {level}\n\n"
            "📁 پروژه‌های انجام‌شده: {projects}",

        "balance_text":
            "💰 موجودی شما:\n\n"
            "{balance:,} تومان"
    }

    for key, value in defaults.items():

        cur.execute("""
            INSERT INTO settings(key,value)
            VALUES(%s,%s)
            ON CONFLICT(key)
            DO NOTHING
        """, (key, value))


    # اگر هیچ شغلی وجود نداشت
    cur.execute(
        "SELECT COUNT(*) FROM jobs"
    )

    count = cur.fetchone()[0]

    if count == 0:

        jobs = [

            "💥 تایپ معمولی و ساده",

            "💥 ترجمه متون انگلیسی به فارسی یا بالعکس",

            "💥 دایرکتر",

            "💥 ادمین کانال تلگرامی",

            "💥 جذب و همکاری",

            "💥 گویندگی صوتی",

            "💥 تایپ صوتی",

            "✍️ نویسندگی",

            "📝 خلاصه نویسی",

            "🎬 تهیه ویدیو"

        ]

        for job in jobs:

            cur.execute(
                "INSERT INTO jobs(name) VALUES(%s)",
                (job,)
            )


    con.commit()
    cur.close()
    con.close()


def get_setting(key):

    con = get_db()
    cur = con.cursor()

    cur.execute(
        "SELECT value FROM settings WHERE key=%s",
        (key,)
    )

    row = cur.fetchone()

    cur.close()
    con.close()

    return row[0] if row else ""


def set_setting(key, value):

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO settings(key,value)
        VALUES(%s,%s)
        ON CONFLICT(key)
        DO UPDATE SET value=EXCLUDED.value
    """, (key, value))

    con.commit()

    cur.close()
    con.close()


def save_user(user):

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO users(user_id,first_name,username)
        VALUES(%s,%s,%s)
        ON CONFLICT(user_id)
        DO UPDATE SET
            first_name=EXCLUDED.first_name,
            username=EXCLUDED.username
    """, (
        user.id,
        user.first_name or "",
        user.username or ""
    ))

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


async def start(update: Update, context):

    save_user(update.effective_user)

    await update.message.reply_text(
        get_setting("welcome"),
        reply_markup=main_menu()
    )


# =========================================================
# JOB MENU
# =========================================================

def jobs_menu(user_id):

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT id,name
        FROM jobs
        WHERE active=1
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

        reply_markup=jobs_menu(
            query.from_user.id
        )

    )


# =========================================================
# SELECT JOB
# =========================================================

async def select_job(query, context):

    user_id = query.from_user.id

    job_id = int(
        query.data.split(":")[1]
    )

    con = get_db()
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
            "⚠️ حداکثر ۴ شغل می‌توانید انتخاب کنید.",
            show_alert=True
        )

        return


    cur.execute("""
        INSERT INTO user_jobs(user_id,job_id)
        VALUES(%s,%s)
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
        SELECT title,file_id
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


# =========================================================
# ADMIN MENU
# =========================================================

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
            "⛔ دسترسی ندارید."
        )

        return


    await update.message.reply_text(

        "⚙️ پنل مدیریت\n\n"
        "از این قسمت می‌توانید ربات را مدیریت کنید.",

        reply_markup=admin_menu()

    )


# =========================================================
# ADMIN TEXT MENU
# =========================================================

def admin_text_menu():

    items = [

        ("👋 خوش‌آمدگویی", "edit:welcome"),

        ("🚀 متن شروع", "edit:start_text"),

        ("💼 متن شغل‌ها", "edit:jobs_text"),

        ("🎧 متن گوش کردم", "edit:heard_text"),

        ("💳 متن ثبت‌نام", "edit:register_text"),

        ("ℹ️ توضیحات", "edit:about"),

        ("🔘 اسم دکمه شروع", "edit:start_button"),

        ("⭐ متن سطح", "edit:level_text"),

        ("💰 متن موجودی", "edit:balance_text")

    ]

    buttons = []

    for title, callback in items:

        buttons.append([

            InlineKeyboardButton(
                title,
                callback_data=callback
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
# ADMIN JOBS
# =========================================================

def admin_jobs_menu():

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT id,name,active
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
                callback_data="job_add"
            )
        ],

        [
            InlineKeyboardButton(
                "♻️ جایگزینی با ۱۰ شغل پیش‌فرض",
                callback_data="jobs_reset"
            )
        ],

        [
            InlineKeyboardButton(
                "🗑️ حذف شغل",
                callback_data="job_delete"
            )
        ]

    ]


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
            "🔙 پنل مدیریت",
            callback_data="admin_home"
        )

    ])


    return InlineKeyboardMarkup(buttons)


# =========================================================
# ADMIN VOICES
# =========================================================

def admin_voice_jobs():

    con = get_db()
    cur = con.cursor()

    cur.execute(
        "SELECT id,name FROM jobs ORDER BY id"
    )

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
# CALLBACK
# =========================================================

async def callback(update, context):

    query = update.callback_query

    await query.answer()

    data = query.data


    # -----------------------------------------------------
    # USER
    # -----------------------------------------------------

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


    if data in ["choose_jobs", "jobs"]:

        await show_jobs(query)

        return


    if data.startswith("job:"):

        await select_job(
            query,
            context
        )

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
            get_setting("price") or 298000
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

            "📸 تصویر فیش واریزی را همینجا ارسال کنید."

        )

        return


    if data == "level":

        con = get_db()
        cur = con.cursor()

        cur.execute("""
            SELECT level,projects
            FROM users
            WHERE user_id=%s
        """, (
            query.from_user.id,
        ))

        row = cur.fetchone()

        cur.close()
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

        con = get_db()
        cur = con.cursor()

        cur.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id=%s
            """,
            (
                query.from_user.id,
            )
        )

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


    # -----------------------------------------------------
    # ADMIN SECURITY
    # -----------------------------------------------------

    admin_commands = [

        "admin_home",
        "admin_texts",
        "admin_jobs",
        "admin_voices",
        "admin_money",
        "admin_payments",
        "admin_users",
        "jobs_reset",
        "job_add",
        "job_delete",
        "voice_job:",
        "job_edit:",
        "edit:",
        "money_",
        "payment:"

    ]


    if any(
        data.startswith(x)
        for x in admin_commands
    ):

        if query.from_user.id != ADMIN_ID:

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True
            )

            return


    # -----------------------------------------------------
    # ADMIN HOME
    # -----------------------------------------------------

    if data == "admin_home":

        await query.edit_message_text(

            "⚙️ پنل مدیریت",

            reply_markup=admin_menu()

        )

        return


    # -----------------------------------------------------
    # ADMIN TEXT
    # -----------------------------------------------------

    if data == "admin_texts":

        await query.edit_message_text(

            "🎛️ چه چیزی را می‌خواهید تغییر دهید؟",

            reply_markup=admin_text_menu()

        )

        return


    if data.startswith("edit:"):

        key = data.split(
            ":",
            1
        )[1]

        context.user_data[
            "editing_setting"
        ] = key


        messages = {

            "welcome":
                "👋 متن خوش‌آمدگویی جدید را بفرست.",

            "start_text":
                "🚀 متن مرحله شروع را بفرست.",

            "jobs_text":
                "💼 متن صفحه شغل‌ها را بفرست.",

            "heard_text":
                "🎧 متن گوش کردم را بفرست.",

            "register_text":
                "💳 متن ثبت‌نام را بفرست.\n\n"
                "برای مبلغ از {price} و "
                "برای کارت از {card} استفاده کن.",

            "about":
                "ℹ️ متن توضیحات را بفرست.",

            "start_button":
                "🔘 اسم جدید دکمه شروع را بفرست.",

            "level_text":
                "⭐ متن سطح را بفرست.\n\n"
                "متغیرها: {level} و {projects}",

            "balance_text":
                "💰 متن موجودی را بفرست.\n\n"
                "متغیر: {balance}"

        }


        await query.edit_message_text(

            messages.get(
                key,
                "متن جدید را بفرست."
            )

        )

        return


    # -----------------------------------------------------
    # ADMIN JOBS
    # -----------------------------------------------------

    if data == "admin_jobs":

        await query.edit_message_text(

            "💼 مدیریت شغل‌ها",

            reply_markup=admin_jobs_menu()

        )

        return


    if data == "jobs_reset":

        con = get_db()
        cur = con.cursor()

        cur.execute(
            "DELETE FROM voices"
        )

        cur.execute(
            "DELETE FROM user_jobs"
        )

        cur.execute(
            "DELETE FROM jobs"
        )


        jobs = [

            "💥 تایپ معمولی و ساده",

            "💥 ترجمه متون انگلیسی به فارسی یا بالعکس",

            "💥 دایرکتر",

            "💥 ادمین کانال تلگرامی",

            "💥 جذب و همکاری",

            "💥 گویندگی صوتی",

            "💥 تایپ صوتی",

            "✍️ نویسندگی",

            "📝 خلاصه نویسی",

            "🎬 تهیه ویدیو"

        ]


        for job in jobs:

            cur.execute(
                "INSERT INTO jobs(name) VALUES(%s)",
                (job,)
            )


        con.commit()

        cur.close()
        con.close()


        await query.edit_message_text(

            "✅ شغل‌های قبلی حذف شدند.\n\n"
            "۱۰ شغل جدید اضافه شدند.",

            reply_markup=admin_menu()

        )

        return


    if data == "job_add":

        context.user_data[
            "job_action"
        ] = "add"

        await query.edit_message_text(

            "➕ اسم شغل جدید را بفرست."

        )

        return


    if data == "job_delete":

        context.user_data[
            "job_action"
        ] = "delete"

        await query.edit_message_text(

            "🗑️ ID شغلی که می‌خواهی حذف کنی را بفرست."

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

            "✏️ اسم جدید شغل را بفرست."

        )

        return


    # -----------------------------------------------------
    # VOICES
    # -----------------------------------------------------

    if data == "admin_voices":

        await query.edit_message_text(

            "🎙️ شغلی را انتخاب کن:",

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
            "بعد از آن عنوان ویس را می‌پرسم."

        )

        return


    # -----------------------------------------------------
    # MONEY
    # -----------------------------------------------------

    if data == "admin_money":

        price = int(
            get_setting("price") or 0
        )


        await query.edit_message_text(

            "💳 تنظیمات پرداخت\n\n"

            f"شماره کارت:\n"
            f"{get_setting('card')}\n\n"

            f"مبلغ:\n"
            f"{price:,} تومان",

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

            "💰 مبلغ جدید را فقط به عدد بفرست."

        )

        return


    # -----------------------------------------------------
    # PAYMENTS
    # -----------------------------------------------------

    if data == "admin_payments":

        await query.edit_message_text(

            "🧾 فیش‌های واریزی\n\n"
            "هر فیش جدید مستقیماً برای شما ارسال می‌شود.",

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


    # -----------------------------------------------------
    # PAYMENT ACTION
    # -----------------------------------------------------

    if data.startswith("payment:"):

        _, action, payment_id = data.split(":")

        payment_id = int(payment_id)


        con = get_db()
        cur = con.cursor()

        cur.execute("""
            SELECT user_id,amount,status
            FROM payments
            WHERE id=%s
        """, (
            payment_id,
        ))

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
            """, (
                payment_id,
            ))


            cur.execute("""
                UPDATE users
                SET balance=balance+%s,
                    registered=1
                WHERE user_id=%s
            """, (
                amount,
                user_id
            ))


            message = (

                "✅ پرداخت شما تأیید شد.\n\n"

                f"💰 مبلغ {amount:,} تومان "
                "به موجودی شما اضافه شد."

            )


            caption = (
                f"✅ فیش #{payment_id} تأیید شد."
            )


        else:

            cur.execute("""
                UPDATE payments
                SET status='rejected'
                WHERE id=%s
            """, (
                payment_id,
            ))


            message = (
                "❌ فیش شما تأیید نشد.\n\n"
                "لطفاً پرداخت را بررسی و دوباره ارسال کنید."
            )


            caption = (
                f"❌ فیش #{payment_id} رد شد."
            )


        con.commit()

        cur.close()
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


# =========================================================
# RECEIPT
# =========================================================

async def receipt_handler(update, context):

    if update.effective_user.id == ADMIN_ID:
        return


    if not context.user_data.get(
        "waiting_receipt"
    ):

        return


    photo_id = (
        update.message
        .photo[-1]
        .file_id
    )


    amount = int(
        get_setting("price") or 298000
    )


    con = get_db()
    cur = con.cursor()


    cur.execute("""
        INSERT INTO payments
        (user_id,photo_id,amount,status)
        VALUES(%s,%s,%s,'pending')
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

            f"👤 کاربر: "
            f"{update.effective_user.id}\n"

            f"💰 مبلغ: "
            f"{amount:,} تومان\n"

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
        "بعد از بررسی مدیریت، نتیجه برای شما ارسال می‌شود."

    )


# =========================================================
# VOICE
# =========================================================

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
        "حالا عنوان ویس را بفرست."

    )


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(update, context):

    if update.effective_user.id != ADMIN_ID:
        return


    text = update.message.text.strip()


    # ---------------------------
    # SETTINGS
    # ---------------------------

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

            "✅ ذخیره شد.",

            reply_markup=admin_menu()

        )

        return


    # ---------------------------
    # JOBS
    # ---------------------------

    if context.user_data.get(
        "job_action"
    ):

        action = context.user_data.pop(
            "job_action"
        )


        con = get_db()
        cur = con.cursor()


        try:

            if action == "add":

                cur.execute(
                    "INSERT INTO jobs(name) VALUES(%s)",
                    (text,)
                )

                message = "✅ شغل اضافه شد."


            elif action == "delete":

                job_id = int(text)

                cur.execute(
                    "DELETE FROM jobs WHERE id=%s",
                    (job_id,)
                )

                message = "✅ شغل حذف شد."


            elif action.startswith(
                "edit:"
            ):

                job_id = int(
                    action.split(":")[1]
                )


                cur.execute("""
                    UPDATE jobs
                    SET name=%s
                    WHERE id=%s
                """, (
                    text,
                    job_id
                ))


                message = "✅ نام شغل تغییر کرد."


            con.commit()


        except Exception:

            con.rollback()

            message = (
                "❌ عملیات انجام نشد."
            )


        cur.close()
        con.close()


        await update.message.reply_text(

            message,

            reply_markup=admin_menu()

        )

        return


    # ---------------------------
    # VOICE TITLE
    # ---------------------------

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


        con = get_db()
        cur = con.cursor()


        cur.execute("""
            INSERT INTO voices
            (job_id,title,file_id)
            VALUES(%s,%s,%s)
        """, (
            job_id,
            title,
            file_id
        ))


        con.commit()

        cur.close()
        con.close()


        await update.message.reply_text(

            "✅ ویس ذخیره شد.\n\n"
            "این ویس حالا برای کاربران "
            "همان شغل ارسال می‌شود.",

            reply_markup=admin_menu()

        )

        return


    # ---------------------------
    # MONEY
    # ---------------------------

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

                    "❌ مبلغ را فقط به صورت عدد وارد کن."

                )

            return


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )


    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL تنظیم نشده است."
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
            text_handler
        )
    )


    print(
        "Bot is running with PostgreSQL..."
    )


    app.run_polling()


if __name__ == "__main__":

    main()
