import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 440194278
DB_NAME = "bot.db"


def db():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = db()
    cur = conn.cursor()

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
        name TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_jobs (
        user_id INTEGER,
        job_id INTEGER,
        PRIMARY KEY(user_id, job_id)
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

    settings = {
        "welcome":
        "سلام کاربر گرامی 🌹\n\n"
        "به ربات درآمدزایی ما خوش آمدید 💰\n\n"
        "اینجا می‌توانید مسیر شغلی مورد علاقه‌تان را انتخاب کنید "
        "و آموزش‌های مربوط به آن را دریافت کنید.",

        "start_button": "🚀 شروع درآمدزایی",

        "start_text":
        "شما می‌توانید با روزی چند ساعت زمان گذاشتن، "
        "مسیر درآمدزایی خودتان را شروع کنید. 💰\n\n"
        "برای شروع روی دکمه زیر کلیک کنید 👇",

        "job_text":
        "💼 شغل مورد نظر خودتان را انتخاب کنید.\n\n"
        "توضیحات و ویس‌های مربوط به شغل انتخابی برای شما ارسال می‌شود.\n\n"
        "حداکثر ۴ شغل می‌توانید انتخاب کنید.",

        "price": "298000",

        "card": "شماره کارت را از پنل مدیریت وارد کنید.",

        "about":
        "ℹ️ توضیحات\n\n"
        "هدف ما آموزش مهارت‌های کاربردی و ایجاد مسیر "
        "برای شروع فعالیت پروژه‌ای است."
    }

    for key, value in settings.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
            (key, value)
        )

    jobs = [
        "💻 برنامه‌نویسی",
        "🎨 طراحی گرافیک",
        "📱 تولید محتوا",
        "🎬 تدوین ویدئو",
        "📈 دیجیتال مارکتینگ",
        "🎙️ گویندگی"
    ]

    for job in jobs:
        cur.execute(
            "INSERT OR IGNORE INTO jobs(name) VALUES(?)",
            (job,)
        )

    conn.commit()
    conn.close()


def setting(key):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else ""


def set_setting(key, value):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
        (key, value)
    )
    conn.commit()
    conn.close()


def save_user(user):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO users(user_id,first_name,username)
    VALUES(?,?,?)
    """, (
        user.id,
        user.first_name or "",
        user.username or ""
    ))

    conn.commit()
    conn.close()


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            setting("start_button"),
            callback_data="start_income"
        )],
        [
            InlineKeyboardButton("⭐ سطح من", callback_data="level"),
            InlineKeyboardButton("💰 موجودی", callback_data="balance")
        ],
        [
            InlineKeyboardButton("💼 شغل‌ها", callback_data="jobs"),
            InlineKeyboardButton("ℹ️ توضیحات", callback_data="about")
        ]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)

    await update.message.reply_text(
        setting("welcome"),
        reply_markup=main_menu()
    )


def jobs_keyboard(user_id):
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT id,name FROM jobs ORDER BY id")
    jobs = cur.fetchall()

    cur.execute(
        "SELECT job_id FROM user_jobs WHERE user_id=?",
        (user_id,)
    )
    selected = [x[0] for x in cur.fetchall()]

    conn.close()

    keyboard = []

    for job_id, name in jobs:
        mark = "✅ " if job_id in selected else ""
        keyboard.append([
            InlineKeyboardButton(
                mark + name,
                callback_data=f"job_{job_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🎧 گوش کردم",
            callback_data="heard"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 برگشت",
            callback_data="start_income"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


async def show_jobs(query):
    await query.edit_message_text(
        setting("job_text"),
        reply_markup=jobs_keyboard(query.from_user.id)
    )


async def select_job(query, context):
    user_id = query.from_user.id
    job_id = int(query.data.split("_")[1])

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT job_id FROM user_jobs WHERE user_id=?",
        (user_id,)
    )

    selected = [x[0] for x in cur.fetchall()]

    if job_id in selected:
        cur.execute(
            "DELETE FROM user_jobs WHERE user_id=? AND job_id=?",
            (user_id, job_id)
        )
    else:
        if len(selected) >= 4:
            conn.close()
            await query.answer(
                "⚠️ حداکثر ۴ شغل می‌توانید انتخاب کنید.",
                show_alert=True
            )
            return

        cur.execute(
            "INSERT INTO user_jobs(user_id,job_id) VALUES(?,?)",
            (user_id, job_id)
        )

        cur.execute(
            "SELECT name FROM jobs WHERE id=?",
            (job_id,)
        )
        job = cur.fetchone()

        conn.commit()

        if job:
            cur.execute(
                "SELECT title,file_id FROM voices WHERE job_id=?",
                (job_id,)
            )
            voices = cur.fetchall()

            for title, file_id in voices:
                await context.bot.send_voice(
                    user_id,
                    file_id,
                    caption=f"🎧 {title}"
                )

    conn.commit()
    conn.close()

    await query.edit_message_reply_markup(
        reply_markup=jobs_keyboard(user_id)
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "start_income":
        await query.edit_message_text(
            setting("start_text"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🚀 شروع",
                    callback_data="choose_jobs"
                )],
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )]
            ])
        )

    elif data == "choose_jobs":
        await show_jobs(query)

    elif data == "jobs":
        await show_jobs(query)

    elif data.startswith("job_"):
        await select_job(query, context)

    elif data == "heard":
        await query.edit_message_text(
            "🎧 گوش کردم.\n\n"
            "حالا شغل‌هایی که مدنظرتان است را انتخاب کنید.\n"
            "حداکثر ۴ شغل.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "💳 ادامه ثبت‌نام",
                    callback_data="register"
                )],
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="choose_jobs"
                )]
            ])
        )

    elif data == "register":
        price = int(setting("price"))

        await query.edit_message_text(
            f"💳 مراحل ثبت‌نام\n\n"
            f"برای ثبت‌نام کافی است مبلغ {price:,} تومان پرداخت کنید.\n\n"
            "این مبلغ در موجودی ربات شما ثبت می‌شود و "
            "طبق شرایط سیستم پس از انجام اولین پروژه "
            "امکان برداشت آن فراهم خواهد شد.\n\n"
            f"💳 شماره کارت:\n{setting('card')}\n\n"
            "بعد از پرداخت، تصویر فیش واریزی را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "📸 ارسال فیش",
                    callback_data="receipt"
                )],
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="choose_jobs"
                )]
            ])
        )

    elif data == "receipt":
        context.user_data["receipt"] = True

        await query.edit_message_text(
            "📸 لطفاً تصویر فیش واریزی را ارسال کنید."
        )

    elif data == "level":
        conn = db()
        cur = conn.cursor()
        cur.execute(
            "SELECT level,projects FROM users WHERE user_id=?",
            (query.from_user.id,)
        )
        row = cur.fetchone()
        conn.close()

        level = row[0] if row else 1
        projects = row[1] if row else 0

        await query.edit_message_text(
            f"⭐ سطح شما: {level}\n\n"
            f"📁 پروژه‌های انجام‌شده: {projects}\n\n"
            "🎯 با انجام هر ۵ پروژه وارد سطح بعدی می‌شوید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )]
            ])
        )

    elif data == "balance":
        conn = db()
        cur = conn.cursor()
        cur.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (query.from_user.id,)
        )
        row = cur.fetchone()
        conn.close()

        balance = row[0] if row else 0

        await query.edit_message_text(
            f"💰 موجودی شما:\n\n{balance:,} تومان",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )]
            ])
        )

    elif data == "about":
        await query.edit_message_text(
            setting("about"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )]
            ])
        )

    elif data == "home":
        await query.edit_message_text(
            "🏠 منوی اصلی",
            reply_markup=main_menu()
        )


async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        return

    if not context.user_data.get("receipt"):
        return

    if not update.message.photo:
        return

    photo = update.message.photo[-1]

    price = int(setting("price"))

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO payments(user_id,photo_id,amount,status)
    VALUES(?,?,?,'pending')
    """, (
        update.effective_user.id,
        photo.file_id,
        price
    ))

    payment_id = cur.lastrowid

    conn.commit()
    conn.close()

    context.user_data["receipt"] = False

    await context.bot.send_photo(
        ADMIN_ID,
        photo.file_id,
        caption=(
            "🧾 فیش جدید\n\n"
            f"👤 کاربر: {update.effective_user.id}\n"
            f"💰 مبلغ: {price:,} تومان\n"
            f"🆔 فیش: {payment_id}"
        ),
        reply_markup=InlineKeyboardMarkup([
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
        ])
    )

    await update.message.reply_text(
        "✅ فیش شما دریافت شد.\n\n"
        "پس از بررسی مدیریت، نتیجه برای شما ارسال می‌شود."
    )


async def payment_action(query, context):
    if query.from_user.id != ADMIN_ID:
        return

    action, payment_id = query.data.split("_")
    payment_id = int(payment_id)

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT user_id,amount FROM payments WHERE id=?",
        (payment_id,)
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        return

    user_id, amount = row

    if action == "approve":
        cur.execute(
            "UPDATE payments SET status='approved' WHERE id=?",
            (payment_id,)
        )

        cur.execute(
            """
            UPDATE users
            SET balance=balance+?, registered=1
            WHERE user_id=?
            """,
            (amount, user_id)
        )

        message = (
            "✅ پرداخت شما تأیید شد.\n\n"
            f"💰 مبلغ {amount:,} تومان به موجودی شما اضافه شد."
        )

    else:
        cur.execute(
            "UPDATE payments SET status='rejected' WHERE id=?",
            (payment_id,)
        )

        message = (
            "❌ فیش پرداخت شما تأیید نشد.\n\n"
            "لطفاً اطلاعات پرداخت را بررسی و دوباره ارسال کنید."
        )

    conn.commit()
    conn.close()

    await context.bot.send_message(user_id, message)


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ دسترسی ندارید.")
        return

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\n"
        "فعلاً مدیریت شغل‌ها و پرداخت‌ها از این بخش انجام می‌شود.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "💳 شماره کارت فعلی",
                callback_data="admin_card"
            )],
            [InlineKeyboardButton(
                "💰 مبلغ فعلی",
                callback_data="admin_price"
            )]
        ])
    )


async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("admin_card"):
        set_setting("card", update.message.text)
        context.user_data["admin_card"] = False
        await update.message.reply_text("✅ شماره کارت ذخیره شد.")

    elif context.user_data.get("admin_price"):
        try:
            price = update.message.text.replace(",", "").replace("٬", "")
            int(price)
            set_setting("price", price)
            context.user_data["admin_price"] = False
            await update.message.reply_text("✅ مبلغ ذخیره شد.")
        except:
            await update.message.reply_text("❌ مبلغ را به صورت عدد وارد کنید.")


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        return

    await query.answer()

    if query.data == "admin_card":
        context.user_data["admin_card"] = True
        await query.edit_message_text(
            "💳 شماره کارت جدید را ارسال کنید."
        )

    elif query.data == "admin_price":
        context.user_data["admin_price"] = True
        await query.edit_message_text(
            "💰 مبلغ جدید را ارسال کنید.\nمثلاً: 298000"
        )

    elif query.data.startswith("approve_") or query.data.startswith("reject_"):
        await payment_action(query, context)


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern="^(admin_card|admin_price|approve_|reject_)"
        )
    )

    app.add_handler(
        CallbackQueryHandler(button)
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_receipt
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_buttons
        )
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
