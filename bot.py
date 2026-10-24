"""
FMCG KPI Telegram Bot
Rollar: agent, supervisor, ekspeditor, rop
"""

import os
import logging
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

import sheets_sync

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DB_PATH = "users.db"

# Conversation states
ASK_NAME, ASK_ROLE = range(2)

ROLES = {
    "🤖 Agent": "agent",
    "👔 Supervisor": "supervisor",
    "🚚 Ekspeditor": "ekspeditor",
    "🏆 ROP": "rop"
}


# ─── Database ───────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            role TEXT,
            registered INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def get_user(tg_id: int):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    conn.close()
    if row:
        return {"tg_id": row[0], "username": row[1], "full_name": row[2], "role": row[3], "registered": row[4]}
    return None


def save_user(tg_id: int, username: str, full_name: str, role: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT OR REPLACE INTO users (tg_id, username, full_name, role, registered)
        VALUES (?, ?, ?, ?, 1)
    """, (tg_id, username, full_name, role))
    conn.commit()
    conn.close()


# ─── Keyboards ──────────────────────────────────────────────────────────────

def main_menu(role: str) -> ReplyKeyboardMarkup:
    if role == "agent":
        buttons = [
            [KeyboardButton("📊 Hisobotim")],
            [KeyboardButton("🔄 Yangilash")]
        ]
    elif role == "supervisor":
        buttons = [
            [KeyboardButton("📊 Jamoam"), KeyboardButton("👥 Agentlar")],
            [KeyboardButton("🔄 Yangilash")]
        ]
    elif role == "ekspeditor":
        buttons = [
            [KeyboardButton("📊 Hisobotim")],
            [KeyboardButton("🔄 Yangilash")]
        ]
    elif role == "rop":
        buttons = [
            [KeyboardButton("🏆 Umumiy hisobot")],
            [KeyboardButton("👔 S1 jamoasi"), KeyboardButton("👔 S2 jamoasi")],
            [KeyboardButton("👔 S3 jamoasi")],
            [KeyboardButton("🔄 Yangilash")]
        ]
    else:
        buttons = [[KeyboardButton("🔄 Yangilash")]]

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def role_keyboard() -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(r)] for r in ROLES.keys()]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)


# ─── Formatters ─────────────────────────────────────────────────────────────

def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def agent_text(d: dict) -> str:
    bar = progress_bar(d['bajarilish'])
    return (
        f"📊 *{d['ism']} — Agent hisoboti*\n\n"
        f"🎯 Oylik reja: *{fmt(d['oylik_reja'])}* so'm\n"
        f"📅 Kunlik reja: *{fmt(d['kunlik_reja'])}* so'm\n\n"
        f"💰 Jami savdo: *{fmt(d['jami_savdo'])}* so'm\n"
        f"📈 Bajarilish: *{d['bajarilish']}%*\n"
        f"{bar}\n"
        f"📆 Ishlagan kunlar: *{d['kun_soni']}*"
    )


def supervisor_text(d: dict) -> str:
    bar = progress_bar(d['bajarilish'])
    return (
        f"👔 *{d['ism']} — Supervisor hisoboti*\n\n"
        f"💼 Jamoa savdo: *{fmt(d['jamoa_savdo'])}* so'm\n"
        f"🎯 Jamoa reja: *{fmt(d['jamoa_reja'])}* so'm\n"
        f"📈 Bajarilish: *{d['bajarilish']}%*\n"
        f"{bar}\n\n"
        f"💵 Fiksa: *{fmt(d['fiksa'])}* so'm\n"
        f"🤝 Komanda bonus: *{fmt(d['komanda_bonus'])}* so'm\n"
        f"⭐ Plan bonus: *{fmt(d['plan_bonus'])}* so'm\n"
        f"━━━━━━━━━━━━━\n"
        f"💎 Jami maosh: *{fmt(d['jami'])}* so'm"
    )


def ekspeditor_text(d: dict) -> str:
    bar = progress_bar(d['bajarilish'])
    return (
        f"🚚 *{d['ism']} — Ekspeditor hisoboti*\n\n"
        f"📦 Yetkazilgan: *{fmt(d['yetkazilgan'])}* ta\n"
        f"🎯 Reja: *{fmt(d['reja'])}* ta\n"
        f"📈 Bajarilish: *{d['bajarilish']}%*\n"
        f"{bar}\n\n"
        f"💵 Fiksa: *{fmt(d['fiksa'])}* so'm\n"
        f"🚀 Yetkazish bonus: *{fmt(d['yetkazish_bonus'])}* so'm\n"
        f"⭐ Spets bonus: *{fmt(d['spets_bonus'])}* so'm\n"
        f"━━━━━━━━━━━━━\n"
        f"💎 Jami maosh: *{fmt(d['jami'])}* so'm"
    )


def rop_text(d: dict) -> str:
    bar = progress_bar(d['bajarilish'])
    return (
        f"🏆 *ROP — To'liq hisobot*\n\n"
        f"💼 Jamoa savdo: *{fmt(d['jamoa_savdo'])}* so'm\n"
        f"🎯 Jamoa reja: *{fmt(d['jamoa_reja'])}* so'm\n"
        f"📈 Bajarilish: *{d['bajarilish']}%*\n"
        f"{bar}\n\n"
        f"💵 Fiksa: *{fmt(d['fiksa'])}* so'm\n"
        f"🤝 Jamoa bonus: *{fmt(d['jamoa_bonus'])}* so'm\n"
        f"⭐ Plan bonus: *{fmt(d['plan_bonus'])}* so'm\n"
        f"🎁 Spets bonus: *{fmt(d['spets_bonus'])}* so'm\n"
        f"━━━━━━━━━━━━━\n"
        f"💎 Jami maosh: *{fmt(d['jami'])}* so'm"
    )


def progress_bar(pct: float) -> str:
    filled = int(pct / 10)
    filled = min(filled, 10)
    empty = 10 - filled
    return f"[{'█' * filled}{'░' * empty}] {pct}%"


# ─── Handlers ───────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = get_user(tg_id)

    if user and user["registered"]:
        role = user["role"]
        await update.message.reply_text(
            f"Xush kelibsiz, *{user['full_name']}*! 👋\nRolingiz: *{role}*",
            parse_mode="Markdown",
            reply_markup=main_menu(role)
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Salom! 👋\nBotga xush kelibsiz.\n\nIsmingizni kiriting:",
        parse_mode="Markdown"
    )
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["full_name"] = update.message.text.strip()
    await update.message.reply_text(
        "Rolingizni tanlang:",
        reply_markup=role_keyboard()
    )
    return ASK_ROLE


async def ask_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text not in ROLES:
        await update.message.reply_text("Iltimos, quyidagi ro'yxatdan tanlang:", reply_markup=role_keyboard())
        return ASK_ROLE

    role = ROLES[text]
    full_name = context.user_data.get("full_name", "")
    tg_id = update.effective_user.id
    username = update.effective_user.username or ""

    save_user(tg_id, username, full_name, role)

    await update.message.reply_text(
        f"✅ Ro'yxatdan o'tdingiz!\n\n👤 Ism: *{full_name}*\n🎭 Rol: *{text}*",
        parse_mode="Markdown",
        reply_markup=main_menu(role)
    )
    return ConversationHandler.END


async def hisobotim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = get_user(tg_id)
    if not user:
        await update.message.reply_text("Avval /start bilan ro'yxatdan o'ting.")
        return

    role = user["role"]
    name = user["full_name"]
    msg = await update.message.reply_text("⏳ Ma'lumotlar yuklanmoqda...")

    if role == "agent":
        data = sheets_sync.get_agent_data(name)
        if data:
            await msg.edit_text(agent_text(data), parse_mode="Markdown")
        else:
            await msg.edit_text(f"❌ *{name}* uchun ma'lumot topilmadi.\nVariaqda D2 katakda ism to'g'ri yozilganmi?", parse_mode="Markdown")

    elif role == "supervisor":
        data = sheets_sync.get_supervisor_data(name)
        if data:
            await msg.edit_text(supervisor_text(data), parse_mode="Markdown")
        else:
            await msg.edit_text("❌ Ma'lumot topilmadi.", parse_mode="Markdown")

    elif role == "ekspeditor":
        data = sheets_sync.get_ekspeditor_data(name)
        if data:
            await msg.edit_text(ekspeditor_text(data), parse_mode="Markdown")
        else:
            await msg.edit_text("❌ Ma'lumot topilmadi.", parse_mode="Markdown")

    elif role == "rop":
        data = sheets_sync.get_rop_data()
        if data:
            await msg.edit_text(rop_text(data), parse_mode="Markdown")
        else:
            await msg.edit_text("❌ Ma'lumot topilmadi.", parse_mode="Markdown")


async def jamoam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Supervisor — jamoam hisoboti"""
    tg_id = update.effective_user.id
    user = get_user(tg_id)
    if not user or user["role"] != "supervisor":
        return
    await hisobotim(update, context)


async def umumiy_hisobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ROP — umumiy hisobot"""
    tg_id = update.effective_user.id
    user = get_user(tg_id)
    if not user or user["role"] != "rop":
        return

    msg = await update.message.reply_text("⏳ Ma'lumotlar yuklanmoqda...")
    data = sheets_sync.get_rop_data()
    if data:
        await msg.edit_text(rop_text(data), parse_mode="Markdown")
    else:
        await msg.edit_text("❌ Ma'lumot topilmadi.", parse_mode="Markdown")


async def sup_jamoa(update: Update, context: ContextTypes.DEFAULT_TYPE, sheet_name: str):
    """ROP — bitta supervisor jamoasi"""
    msg = await update.message.reply_text("⏳ Ma'lumotlar yuklanmoqda...")
    try:
        sh = sheets_sync.get_spreadsheet()
        if not sh:
            await msg.edit_text("❌ Google Sheets ulanmadi.")
            return
        ws = sh.worksheet(sheet_name)
        vals = ws.get('B3:B11', value_render_option='UNFORMATTED_VALUE')

        def v(i):
            return sheets_sync.safe_int(vals[i][0]) if len(vals) > i and vals[i] else 0

        jamoa_savdo = v(1)
        jamoa_reja = v(2)
        fiksa = v(5)
        komanda_bonus = v(6)
        plan_bonus = v(7)
        bajarilish = round(jamoa_savdo / jamoa_reja * 100, 1) if jamoa_reja > 0 else 0
        bar = progress_bar(bajarilish)

        text = (
            f"👔 *{sheet_name} — Jamoa hisoboti*\n\n"
            f"💼 Jamoa savdo: *{fmt(jamoa_savdo)}* so'm\n"
            f"🎯 Jamoa reja: *{fmt(jamoa_reja)}* so'm\n"
            f"📈 Bajarilish: *{bajarilish}%*\n"
            f"{bar}\n\n"
            f"💵 Fiksa: *{fmt(fiksa)}* so'm\n"
            f"🤝 Komanda bonus: *{fmt(komanda_bonus)}* so'm\n"
            f"⭐ Plan bonus: *{fmt(plan_bonus)}* so'm\n"
            f"━━━━━━━━━━━━━\n"
            f"💎 Jami: *{fmt(fiksa + komanda_bonus + plan_bonus)}* so'm"
        )
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Xato: {e}")


async def yangilash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await hisobotim(update, context)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qayta ro'yxatdan o'tish"""
    tg_id = update.effective_user.id
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM users WHERE tg_id=?", (tg_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("♻️ Ma'lumotlaringiz o'chirildi. /start bosing.")


async def sinxron(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: /sinxron — Google Sheets test"""
    msg = await update.message.reply_text("⏳ Google Sheets tekshirilmoqda...")
    client = sheets_sync.get_sheets_client()
    if client:
        await msg.edit_text("✅ Google Sheets ulandi!")
    else:
        await msg.edit_text("❌ Google Sheets ulanmadi. GOOGLE_CREDENTIALS ni tekshiring.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text in ["📊 Hisobotim", "🔄 Yangilash"]:
        await hisobotim(update, context)
    elif text == "📊 Jamoam":
        await jamoam(update, context)
    elif text == "👥 Agentlar":
        await hisobotim(update, context)
    elif text == "🏆 Umumiy hisobot":
        await umumiy_hisobot(update, context)
    elif text == "👔 S1 jamoasi":
        await sup_jamoa(update, context, "👔 S1")
    elif text == "👔 S2 jamoasi":
        await sup_jamoa(update, context, "👔 S2")
    elif text == "👔 S3 jamoasi":
        await sup_jamoa(update, context, "👔 S3")


# ─── Health server ───────────────────────────────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    init_db()

    threading.Thread(target=run_health_server, daemon=True).start()
    logger.info("Health server ishga tushdi")

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_role)],
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("sinxron", sinxron))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot ishga tushdi")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
