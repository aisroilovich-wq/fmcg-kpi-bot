"""
FMCG KPI Telegram Bot
Multi-role: Agent | Supervisor | ROP/Admin
Webhook mode for 24/7 hosting
"""

import os
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

from database import Database
from kpi_engine import KPIEngine
from reports import ReportGenerator
from config import Config
from sheets_sync import (get_monthly_plan, get_sozlamalar,
                         get_supervisor_report, get_rop_report, get_jamoa_hisobot)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()
kpi = KPIEngine(db)
reporter = ReportGenerator(db, kpi)


# ═══════════════════════════════════════════════════════════
# /start — Ro'yxatdan o'tish
# ═══════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if user:
        role_emoji = {"agent": "🧑", "supervisor": "👔", "rop": "🏆"}.get(user['role'], "👤")
        await update.message.reply_text(
            f"{role_emoji} Xush kelibsiz, *{user['name']}*!\n\n"
            f"Rol: `{user['role'].upper()}`\n\n"
            f"Buyruqlar uchun /help yuboring.",
            parse_mode='Markdown'
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🧑 Agent", callback_data="reg_agent")],
            [InlineKeyboardButton("👔 Supervisor", callback_data="reg_supervisor")],
            [InlineKeyboardButton("🏆 ROP / Direktor", callback_data="reg_rop")],
        ]
        await update.message.reply_text(
            "👋 *FMCG KPI Botga xush kelibsiz!*\n\n"
            "Rolingizni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )


async def register_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    role = query.data.replace("reg_", "")
    context.user_data['pending_role'] = role

    role_names = {"agent": "Agent", "supervisor": "Supervisor", "rop": "ROP/Direktor"}
    await query.edit_message_text(
        f"✅ Rol tanlandi: *{role_names[role]}*\n\n"
        f"Endi to'liq ismingizni yuboring:\n_(masalan: Alisher Nazarov)_",
        parse_mode='Markdown'
    )


async def handle_registration_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'pending_role' not in context.user_data:
        return False

    user_id = update.effective_user.id
    name = update.message.text.strip()
    role = context.user_data.pop('pending_role')

    # ROP uchun parol tekshiruvi
    if role == 'rop':
        context.user_data['pending_rop_name'] = name
        await update.message.reply_text(
            "🔐 ROP paroli kiriting:",
        )
        return True

    db.register_user(user_id, name, role)
    role_emoji = {"agent": "🧑", "supervisor": "👔", "rop": "🏆"}.get(role, "👤")

    await update.message.reply_text(
        f"{role_emoji} *{name}* sifatida ro'yxatdan o'tdingiz!\n\n"
        f"Rol: `{role.upper()}`\n\n"
        f"/help — barcha buyruqlar",
        parse_mode='Markdown'
    )
    return True


async def handle_rop_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'pending_rop_name' not in context.user_data:
        return False

    password = update.message.text.strip()
    if password != Config.ROP_PASSWORD:
        await update.message.reply_text("❌ Noto'g'ri parol! Qayta urinib ko'ring.")
        return True

    user_id = update.effective_user.id
    name = context.user_data.pop('pending_rop_name')
    db.register_user(user_id, name, 'rop')

    await update.message.reply_text(
        f"🏆 *{name}* ROP sifatida tasdiqlandi!\n\n"
        f"/help — barcha buyruqlar",
        parse_mode='Markdown'
    )
    return True


# ═══════════════════════════════════════════════════════════
# /help
# ═══════════════════════════════════════════════════════════

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        await update.message.reply_text("Avval /start bilan ro'yxatdan o'ting.")
        return

    role = user['role']

    if role == 'agent':
        text = (
            "🧑 *AGENT BUYRUQLARI*\n\n"
            "📊 *Savdo kiritish:*\n"
            "`/savdo 3500000` — bugungi savdo\n"
            "`/savdo 3500000 kecha` — kechagi savdo\n\n"
            "📈 *Ko'rish:*\n"
            "`/bugun` — bugungi natija\n"
            "`/oy` — oylik jami\n"
            "`/status` — reja bajarish holati\n\n"
            "ℹ️ *Boshqa:*\n"
            "`/reja` — oylik rejam nechchi?\n"
        )
    elif role == 'supervisor':
        text = (
            "👔 *SUPERVISOR BUYRUQLARI*\n\n"
            "👥 *Jamoa:*\n"
            "`/jamoa` — barcha agentlar holati\n\n"
            "📊 *Hisobotlar:*\n"
            "`/hisobot` — bugungi hisobot\n"
            "`/oy` — oylik hisobot\n\n"
            "⚙️ *Boshqaruv:*\n"
            "`/agentlar` — agent ro'yxati\n"
        )
    else:  # rop
        text = (
            "🏆 *ROP/DIREKTOR BUYRUQLARI*\n\n"
            "📊 *Hisobotlar:*\n"
            "`/jamoa` — barcha agentlar holati\n"
            "`/hisobot` — bugungi to'liq hisobot\n"
            "`/oy` — oylik hisobot\n\n"
            "⚙️ *Boshqaruv:*\n"
            "`/reja [miqdor]` — oylik reja o'rnatish\n"
            "`/agentlar` — agent ro'yxati\n"
            "`/bonus` — bonus hisob-kitobi\n"
        )

    await update.message.reply_text(text, parse_mode='Markdown')


# ═══════════════════════════════════════════════════════════
# /savdo — Savdo kiritish (Agent)
# ═══════════════════════════════════════════════════════════

async def savdo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        await update.message.reply_text("Avval /start bilan ro'yxatdan o'ting.")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ Savdo miqdorini kiriting:\n`/savdo 3500000`",
            parse_mode='Markdown'
        )
        return

    try:
        amount_str = args[0].replace('_', '').replace(' ', '').replace(',', '')
        amount = int(amount_str)
    except ValueError:
        await update.message.reply_text(
            "❌ Noto'g'ri format. Faqat raqam kiriting:\n`/savdo 3500000`",
            parse_mode='Markdown'
        )
        return

    # Sana aniqlash
    target_date = date.today()
    if len(args) > 1 and args[1].lower() in ('kecha', 'yesterday'):
        target_date = date.today() - timedelta(days=1)

    # Allaqachon kiritilganmi?
    existing = db.get_daily_sale(user_id, target_date)

    if existing:
        keyboard = [
            [
                InlineKeyboardButton("✅ Ha, yangilash", callback_data=f"update_sale_{amount}_{target_date}"),
                InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel"),
            ]
        ]
        await update.message.reply_text(
            f"⚠️ {target_date.strftime('%d.%m.%Y')} kuni allaqachon kiritilgan:\n"
            f"*{existing['amount']:,} so'm*\n\n"
            f"Yangi miqdor: *{amount:,} so'm*\n"
            f"Yangilashni xohlaysizmi?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    db.save_daily_sale(user_id, amount, target_date)

    # KPI hisoblash
    result = kpi.calculate_day(user_id, target_date)

    date_str = "Bugun" if target_date == date.today() else target_date.strftime('%d.%m.%Y')

    await update.message.reply_text(
        _format_day_result(user['name'], date_str, amount, result),
        parse_mode='Markdown'
    )


async def update_sale_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ Bekor qilindi.")
        return

    parts = query.data.split('_')
    amount = int(parts[2])
    target_date = date.fromisoformat(parts[3])
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    db.save_daily_sale(user_id, amount, target_date, update=True)
    result = kpi.calculate_day(user_id, target_date)

    await query.edit_message_text(
        _format_day_result(user['name'], target_date.strftime('%d.%m.%Y'), amount, result),
        parse_mode='Markdown'
    )


def _format_day_result(name: str, date_str: str, amount: int, result: dict) -> str:
    status_emoji = result.get('status_emoji', '🟡')
    kunlik_reja = result.get('kunlik_reja', 0)
    yuklanma = result.get('yuklanma', 0)
    bajarildi_pct = result.get('bajarildi_pct', 0)
    kunlik_bonus = result.get('kunlik_bonus', 0)

    text = (
        f"✅ *{date_str} savdosi saqlandi!*\n\n"
        f"👤 {name}\n"
        f"💰 Savdo: *{amount:,} so'm*\n"
    )

    if yuklanma > 0:
        text += f"📦 Yuklanma: +{yuklanma:,} so'm\n"
        text += f"📊 Jami (yuklanma bilan): *{amount + yuklanma:,} so'm*\n"

    text += (
        f"\n📋 Kunlik reja: {kunlik_reja:,} so'm\n"
        f"{status_emoji} Bajarildi: *{bajarildi_pct:.0f}%*\n"
    )

    if kunlik_bonus > 0:
        text += f"🎁 Kunlik bonus: +{kunlik_bonus:,} so'm\n"
    elif result.get('shortfall', 0) > 0:
        text += f"📉 Yetmaydi: {result['shortfall']:,} so'm\n"

    text += f"\n{result.get('recommendation', '')}"

    return text


# ═══════════════════════════════════════════════════════════
# /bugun — Bugungi natija
# ═══════════════════════════════════════════════════════════

async def bugun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        await update.message.reply_text("Avval /start bilan ro'yxatdan o'ting.")
        return

    today = date.today()
    sale = db.get_daily_sale(user_id, today)
    result = kpi.calculate_day(user_id, today)

    if not sale:
        kunlik_reja = result.get('kunlik_reja', 0)
        yuklanma = result.get('yuklanma', 0)
        text = (
            f"📊 *Bugun ({today.strftime('%d.%m.%Y')}) — {user['name']}*\n\n"
            f"⏳ Hali savdo kiritilmagan\n\n"
            f"📋 Kunlik reja: *{kunlik_reja:,} so'm*\n"
        )
        if yuklanma > 0:
            text += f"📦 Yuklanma (o'tgan kundan): +{yuklanma:,} so'm\n"
        text += "\nSavdo kiritish: `/savdo 3500000`"
        await update.message.reply_text(text, parse_mode='Markdown')
        return

    amount = sale['amount']
    status_emoji = result.get('status_emoji', '🟡')
    kunlik_reja = result.get('kunlik_reja', 0)
    yuklanma = result.get('yuklanma', 0)
    bajarildi_pct = result.get('bajarildi_pct', 0)

    text = (
        f"📊 *Bugun ({today.strftime('%d.%m.%Y')}) — {user['name']}*\n\n"
        f"💰 Savdo: *{amount:,} so'm*\n"
    )
    if yuklanma > 0:
        text += f"📦 Yuklanma: +{yuklanma:,} so'm\n"
        text += f"📊 Jami: *{amount + yuklanma:,} so'm*\n"

    text += (
        f"\n📋 Kunlik reja: {kunlik_reja:,} so'm\n"
        f"{status_emoji} Bajarildi: *{bajarildi_pct:.0f}%*\n"
    )

    if result.get('kunlik_bonus', 0) > 0:
        text += f"🎁 Kunlik bonus: +{result['kunlik_bonus']:,} so'm\n"

    text += f"\n{result.get('recommendation', '')}"

    await update.message.reply_text(text, parse_mode='Markdown')


# ═══════════════════════════════════════════════════════════
# /oy — Oylik hisobot
# ═══════════════════════════════════════════════════════════

async def oy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        await update.message.reply_text("Avval /start bilan ro'yxatdan o'ting.")
        return

    role = user['role']

    if role == 'agent':
        await _show_agent_monthly(update, user_id, user)
    else:
        await _show_team_monthly(update, user)


async def _show_agent_monthly(update, user_id, user):
    today = date.today()
    year, month = today.year, today.month

    result = kpi.calculate_month(user_id, year, month)

    days_worked = result.get('days_worked', 0)
    total_sales = result.get('total_sales', 0)
    oylik_reja = result.get('oylik_reja', 0)
    reja_pct = result.get('reja_pct', 0)
    fiksa = result.get('fiksa', 0)
    kunlik_bonuslar = result.get('kunlik_bonuslar', 0)
    oylik_bonus = result.get('oylik_bonus', 0)
    spets = result.get('spets_zadacha', 0)
    jami_maosh = result.get('jami_maosh', 0)

    status = "✅" if reja_pct >= 100 else ("🟡" if reja_pct >= 80 else "🔴")

    text = (
        f"📅 *{today.strftime('%B %Y')} — {user['name']}*\n\n"
        f"📊 *Savdo natijasi:*\n"
        f"💰 Jami savdo: *{total_sales:,} so'm*\n"
        f"📋 Oylik reja: {oylik_reja:,} so'm\n"
        f"{status} Bajarildi: *{reja_pct:.1f}%*\n"
        f"📆 Ish kunlari: {days_worked} kun\n\n"
        f"💵 *Maosh hisob-kitobi:*\n"
        f"├ Fiksa: {fiksa:,} so'm\n"
        f"├ Kunlik bonuslar: {kunlik_bonuslar:,} so'm\n"
        f"├ Oylik reja bonusi: {oylik_bonus:,} so'm\n"
        f"├ Spets zadacha: {spets:,} so'm\n"
        f"└ *JAMI: {jami_maosh:,} so'm*\n"
    )

    remaining = oylik_reja - total_sales
    if remaining > 0:
        import calendar
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        days_left = days_in_month - today.day
        if days_left > 0:
            per_day_need = remaining // days_left
            text += f"\n📉 Rejaga yetmaydi: {remaining:,} so'm\n"
            text += f"📌 Qolgan {days_left} kun uchun: *{per_day_need:,}/kun*"

    await update.message.reply_text(text, parse_mode='Markdown')


async def _show_team_monthly(update, user):
    today = date.today()
    year, month = today.year, today.month

    agents = db.get_all_agents()
    if not agents:
        await update.message.reply_text("Hali agentlar ro'yxatdan o'tmagan.")
        return

    text = f"📅 *{today.strftime('%B %Y')} — Jamoa oylik*\n\n"

    total_team = 0
    for agent in agents:
        result = kpi.calculate_month(agent['user_id'], year, month)
        total_sales = result.get('total_sales', 0)
        reja_pct = result.get('reja_pct', 0)
        status = "✅" if reja_pct >= 100 else ("🟡" if reja_pct >= 80 else "🔴")
        text += f"{status} {agent['name']}: *{total_sales:,}* ({reja_pct:.0f}%)\n"
        total_team += total_sales

    text += f"\n💰 *Jamoa jami: {total_team:,} so'm*"

    await update.message.reply_text(text, parse_mode='Markdown')


# ═══════════════════════════════════════════════════════════
# /jamoa — Jamoa holati (Supervisor/ROP)
# ═══════════════════════════════════════════════════════════

async def jamoa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user or user['role'] == 'agent':
        await update.message.reply_text("Bu buyruq supervisor/ROP uchun.")
        return

    today = date.today()
    agents = db.get_all_agents()

    if not agents:
        await update.message.reply_text("Hali agentlar ro'yxatdan o'tmagan.")
        return

    text = f"👥 *Jamoa holati — {today.strftime('%d.%m.%Y')}*\n\n"

    entered = 0
    not_entered = 0

    for agent in agents:
        sale = db.get_daily_sale(agent['user_id'], today)
        result = kpi.calculate_day(agent['user_id'], today)
        kunlik_reja = result.get('kunlik_reja', 0)
        yuklanma = result.get('yuklanma', 0)

        if sale:
            amount = sale['amount']
            bajarildi_pct = result.get('bajarildi_pct', 0)
            status = result.get('status_emoji', '🟡')
            text += f"{status} *{agent['name']}*: {amount:,} so'm ({bajarildi_pct:.0f}%)\n"
            if yuklanma > 0:
                text += f"   📦 yuklanma: +{yuklanma:,}\n"
            entered += 1
        else:
            text += f"⬜ *{agent['name']}*: _kiritilmagan_ (reja: {kunlik_reja:,})\n"
            not_entered += 1

    text += f"\n📊 Kiritgan: {entered}/{len(agents)}"
    if not_entered > 0:
        text += f" | Kiritmagani: {not_entered}"

    await update.message.reply_text(text, parse_mode='Markdown')


# ═══════════════════════════════════════════════════════════
# /hisobot — Bugungi to'liq hisobot
# ═══════════════════════════════════════════════════════════

async def hisobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        await update.message.reply_text("Avval /start bilan ro'yxatdan o'ting.")
        return

    today = date.today()

    if user['role'] == 'agent':
        result = kpi.calculate_day(user_id, today)
        sale = db.get_daily_sale(user_id, today)

        if not sale:
            await update.message.reply_text("Bugun savdo kiritilmagan. `/savdo [miqdor]`", parse_mode='Markdown')
            return

        text = _format_day_result(user['name'], "Bugun", sale['amount'], result)
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        report = reporter.daily_team_report(today)
        await update.message.reply_text(report, parse_mode='Markdown')


# ═══════════════════════════════════════════════════════════
# /reja — Reja ko'rish/o'rnatish
# ═══════════════════════════════════════════════════════════

async def reja(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        await update.message.reply_text("Avval /start bilan ro'yxatdan o'ting.")
        return

    args = context.args
    today = date.today()

    if not args:
        plan = db.get_monthly_plan(today.year, today.month)
        agent_count = len(db.get_all_agents())

        if not plan:
            await update.message.reply_text(
                "⚠️ Oylik reja o'rnatilmagan.\n\n"
                "ROP: `/reja 1000000000` — reja o'rnatish",
                parse_mode='Markdown'
            )
            return

        agent_plan = plan['total'] // agent_count if agent_count > 0 else 0
        daily_plan = agent_plan // Config.WORKING_DAYS

        await update.message.reply_text(
            f"📋 *{today.strftime('%B %Y')} Reja*\n\n"
            f"🏢 Jamoa reja: *{plan['total']:,} so'm*\n"
            f"👤 1 agent reja: *{agent_plan:,} so'm*\n"
            f"📅 Kunlik reja: *{daily_plan:,} so'm*\n"
            f"👥 Agentlar: {agent_count} ta",
            parse_mode='Markdown'
        )
        return

    if user['role'] != 'rop':
        await update.message.reply_text("❌ Reja faqat ROP tomonidan o'rnatiladi.")
        return

    try:
        amount_str = args[0].replace('_', '').replace(',', '')
        amount = int(amount_str)
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format: `/reja 1000000000`", parse_mode='Markdown')
        return

    db.set_monthly_plan(today.year, today.month, amount, user_id)
    agent_count = len(db.get_all_agents())
    agent_plan = amount // agent_count if agent_count > 0 else 0
    daily_plan = agent_plan // Config.WORKING_DAYS

    await update.message.reply_text(
        f"✅ *{today.strftime('%B %Y')} Reja o'rnatildi!*\n\n"
        f"🏢 Jamoa reja: *{amount:,} so'm*\n"
        f"👤 1 agent reja: *{agent_plan:,} so'm*\n"
        f"📅 Kunlik reja: *{daily_plan:,} so'm*\n"
        f"👥 Agentlar: {agent_count} ta",
        parse_mode='Markdown'
    )


# ═══════════════════════════════════════════════════════════
# /agentlar — Agent ro'yxati (ROP)
# ═══════════════════════════════════════════════════════════

async def agentlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user or user['role'] not in ('supervisor', 'rop'):
        await update.message.reply_text("Bu buyruq faqat supervisor/ROP uchun.")
        return

    agents = db.get_all_agents()
    if not agents:
        await update.message.reply_text("Hali agentlar ro'yxatdan o'tmagan.")
        return

    text = f"👥 *Agentlar ro'yxati ({len(agents)} ta)*\n\n"
    for i, agent in enumerate(agents, 1):
        text += f"{i}. {agent['name']} — ID: `{agent['user_id']}`\n"

    await update.message.reply_text(text, parse_mode='Markdown')


# ═══════════════════════════════════════════════════════════
# /bonus — Bonus hisob-kitobi (ROP)
# ═══════════════════════════════════════════════════════════

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user or user['role'] not in ('supervisor', 'rop'):
        await update.message.reply_text("Bu buyruq faqat supervisor/ROP uchun.")
        return

    today = date.today()
    agents = db.get_all_agents()

    if not agents:
        await update.message.reply_text("Hali agentlar ro'yxatdan o'tmagan.")
        return

    text = f"💵 *{today.strftime('%B %Y')} Bonus hisob-kitobi*\n\n"

    total_maosh = 0
    for agent in agents:
        result = kpi.calculate_month(agent['user_id'], today.year, today.month)
        jami = result.get('jami_maosh', 0)
        fiksa = result.get('fiksa', 0)
        kunlik_b = result.get('kunlik_bonuslar', 0)
        oylik_b = result.get('oylik_bonus', 0)
        reja_pct = result.get('reja_pct', 0)
        status = "✅" if reja_pct >= 100 else ("🟡" if reja_pct >= 80 else "🔴")

        text += (
            f"{status} *{agent['name']}*\n"
            f"   Fiksa: {fiksa:,} | Kunlik: {kunlik_b:,} | Oylik: {oylik_b:,}\n"
            f"   💰 Jami: *{jami:,} so'm*\n\n"
        )
        total_maosh += jami

    text += f"━━━━━━━━━━━━━━\n💰 *Jamoa jami: {total_maosh:,} so'm*"

    await update.message.reply_text(text, parse_mode='Markdown')


# ═══════════════════════════════════════════════════════════
# /sinxron — Google Sheets dan ma'lumot yangilash (ROP)
# ═══════════════════════════════════════════════════════════

async def sinxron(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        await update.message.reply_text("Avval /start bilan ro'yxatdan o'ting.")
        return

    role = user['role']
    await update.message.reply_text("🔄 Google Sheets dan ma'lumot olinmoqda...")

    today = date.today()

    if role == 'agent':
        # Agent: o'z oylik rejasi
        plan_data = get_monthly_plan()
        if plan_data:
            jamoa_reja = plan_data['jamoa_reja']
            agent_soni = plan_data['agent_soni']
            agent_plan = jamoa_reja // agent_soni if agent_soni > 0 else 0
            daily_plan = agent_plan // Config.WORKING_DAYS
            db.set_monthly_plan(today.year, today.month, jamoa_reja, user_id)
            text = (
                f"📊 *{user['name']} — Reja ma'lumotlari*\n\n"
                f"📋 Sizning oylik reja: *{agent_plan:,} so'm*\n"
                f"📅 Kunlik reja: *{daily_plan:,} so'm*\n"
                f"👥 Jamoada: {agent_soni} ta agent\n\n"
                f"_Google Sheets dan yangilandi ✅_"
            )
        else:
            text = "⚠️ Google Sheets dan ma'lumot olinmadi."
        await update.message.reply_text(text, parse_mode='Markdown')

    elif role == 'supervisor':
        # Supervisor: jamoa holati + o'z maoshi
        sup_data = get_supervisor_report()
        jamoa_data = get_jamoa_hisobot()
        plan_data = get_monthly_plan()

        if plan_data:
            db.set_monthly_plan(today.year, today.month, plan_data['jamoa_reja'], user_id)

        text = f"👔 *{user['name']} — Supervisor hisobot*\n\n"

        if jamoa_data:
            status = "✅" if jamoa_data.get('bajarilish_pct', 0) >= 100 else (
                "🟡" if jamoa_data.get('bajarilish_pct', 0) >= 80 else "🔴")
            text += (
                f"📈 *Jamoa natija:*\n"
                f"🎯 Reja: {jamoa_data.get('jamoa_reja', 0):,} so'm\n"
                f"💰 Haqiqiy: {jamoa_data.get('haqiqiy_savdo', 0):,} so'm\n"
                f"{status} Bajarildi: {jamoa_data.get('bajarilish_pct', 0)}%\n\n"
            )

        if sup_data:
            text += (
                f"💵 *Sizning maoshingiz:*\n"
                f"├ Fiksa: {sup_data.get('fiksa', 0):,} so'm\n"
                f"├ Komanda bonus: {sup_data.get('komanda_bonus', 0):,} so'm\n"
                f"├ Plan bonus: {sup_data.get('plan_bonus', 0):,} so'm\n"
                f"└ *JAMI: {sup_data.get('jami', 0):,} so'm*\n"
            )

        text += "\n_Google Sheets dan yangilandi ✅_"
        await update.message.reply_text(text, parse_mode='Markdown')

    else:  # rop
        # ROP: hammasi
        rop_data = get_rop_report()
        jamoa_data = get_jamoa_hisobot()
        plan_data = get_monthly_plan()

        if plan_data:
            db.set_monthly_plan(today.year, today.month, plan_data['jamoa_reja'], user_id)

        text = f"🏆 *{user['name']} — ROP to'liq hisobot*\n\n"

        if jamoa_data:
            status = "✅" if jamoa_data.get('bajarilish_pct', 0) >= 100 else (
                "🟡" if jamoa_data.get('bajarilish_pct', 0) >= 80 else "🔴")
            text += (
                f"📈 *Jamoa natija:*\n"
                f"🎯 Reja: {jamoa_data.get('jamoa_reja', 0):,} so'm\n"
                f"💰 Haqiqiy: {jamoa_data.get('haqiqiy_savdo', 0):,} so'm\n"
                f"{status} Bajarildi: {jamoa_data.get('bajarilish_pct', 0)}%\n"
                f"👥 Agentlar: {jamoa_data.get('agent_soni', 0)} ta\n\n"
            )

        if rop_data:
            text += (
                f"💵 *ROP maoshi:*\n"
                f"├ Fiksa: {rop_data.get('fiksa', 0):,} so'm\n"
                f"├ Jamoa bonusi (2%): {rop_data.get('jamoa_bonus', 0):,} so'm\n"
                f"├ Plan bonusi: {rop_data.get('plan_bonus', 0):,} so'm\n"
                f"├ Spets zadacha: {rop_data.get('spets_bonus', 0):,} so'm\n"
                f"└ *JAMI: {rop_data.get('jami', 0):,} so'm*\n\n"
                f"📊 Bajarilish: {rop_data.get('bajarilish_pct', 0)}%\n"
            )

        if plan_data:
            agent_plan = plan_data['jamoa_reja'] // plan_data['agent_soni'] if plan_data['agent_soni'] > 0 else 0
            text += (
                f"\n📋 *Reja taqsimoti:*\n"
                f"🏢 Jamoa: {plan_data['jamoa_reja']:,} so'm\n"
                f"👤 1 agent: {agent_plan:,} so'm\n"
                f"📅 Kunlik: {agent_plan // Config.WORKING_DAYS:,} so'm\n"
            )

        text += "\n_Google Sheets dan yangilandi ✅_"
        await update.message.reply_text(text, parse_mode='Markdown')


# ═══════════════════════════════════════════════════════════
# /status — O'z holati (Agent)
# ═══════════════════════════════════════════════════════════

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        await update.message.reply_text("Avval /start bilan ro'yxatdan o'ting.")
        return

    today = date.today()
    year, month = today.year, today.month

    monthly = kpi.calculate_month(user_id, year, month)
    daily_result = kpi.calculate_day(user_id, today)

    total_sales = monthly.get('total_sales', 0)
    oylik_reja = monthly.get('oylik_reja', 0)
    reja_pct = monthly.get('reja_pct', 0)
    remaining = oylik_reja - total_sales

    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    days_left = days_in_month - today.day
    per_day_need = (remaining // days_left) if days_left > 0 and remaining > 0 else 0

    status = "✅" if reja_pct >= 100 else ("🟡" if reja_pct >= 80 else "🔴")

    text = (
        f"📊 *{user['name']} — Holat*\n\n"
        f"📅 *Oylik:*\n"
        f"💰 Jami savdo: *{total_sales:,} so'm*\n"
        f"📋 Oylik reja: {oylik_reja:,} so'm\n"
        f"{status} Bajarildi: *{reja_pct:.1f}%*\n"
    )

    if remaining > 0 and days_left > 0:
        text += (
            f"📉 Yetmaydi: {remaining:,} so'm\n"
            f"📌 Qolgan {days_left} kun: *{per_day_need:,}/kun* kerak\n"
        )

    sale_today = db.get_daily_sale(user_id, today)
    text += f"\n📆 *Bugun:*\n"
    if sale_today:
        text += f"💰 Kiritilgan: *{sale_today['amount']:,} so'm*\n"
        text += f"{daily_result.get('status_emoji', '🟡')} {daily_result.get('bajarildi_pct', 0):.0f}% bajarildi"
    else:
        text += "⏳ Hali kiritilmagan\n`/savdo [miqdor]`"

    await update.message.reply_text(text, parse_mode='Markdown')


# ═══════════════════════════════════════════════════════════
# Umumiy xabar handler
# ═══════════════════════════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if await handle_registration_name(update, context):
        return
    if await handle_rop_password(update, context):
        return

    try:
        amount_str = text.replace('_', '').replace(' ', '').replace(',', '').strip()
        amount = int(amount_str)
        if amount > 10000:
            context.args = [amount_str]
            await savdo(update, context)
            return
    except ValueError:
        pass

    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("👋 Ro'yxatdan o'tish uchun /start yuboring.")
    else:
        await update.message.reply_text("❓ Buyruqlar uchun /help yuboring.")


# ═══════════════════════════════════════════════════════════
# Avtomatik kunlik hisobot (kechqurun 18:00 Toshkent vaqti)
# ═══════════════════════════════════════════════════════════

async def send_evening_report(context: ContextTypes.DEFAULT_TYPE):
    rop_users = db.get_users_by_role('rop')
    supervisor_users = db.get_users_by_role('supervisor')

    today = date.today()
    report = reporter.daily_team_report(today)

    recipients = rop_users + supervisor_users
    for user in recipients:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"🌆 *Kechki hisobot*\n\n{report}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Hisobot yuborishda xato {user['user_id']}: {e}")

    agents = db.get_all_agents()
    for agent in agents:
        try:
            sale = db.get_daily_sale(agent['user_id'], today)
            result = kpi.calculate_day(agent['user_id'], today)

            if not sale:
                await context.bot.send_message(
                    chat_id=agent['user_id'],
                    text=(
                        f"🌆 Bugungi savdo kiritilmagan!\n\n"
                        f"📋 Kunlik reja: {result.get('kunlik_reja', 0):,} so'm\n"
                        f"Kiritish: `/savdo [miqdor]`"
                    ),
                    parse_mode='Markdown'
                )
            else:
                text = _format_day_result(agent['name'], "Bugun", sale['amount'], result)
                await context.bot.send_message(
                    chat_id=agent['user_id'],
                    text=f"🌆 *Kunlik natija*\n\n{text}",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Agent hisobotida xato {agent['user_id']}: {e}")


# ═══════════════════════════════════════════════════════════
# Main — Webhook yoki Polling
# ═══════════════════════════════════════════════════════════

def main():
    token = Config.BOT_TOKEN
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("❌ BOT_TOKEN o'rnatilmagan!")
        return

    app = Application.builder().token(token).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("savdo", savdo))
    app.add_handler(CommandHandler("bugun", bugun))
    app.add_handler(CommandHandler("oy", oy))
    app.add_handler(CommandHandler("jamoa", jamoa))
    app.add_handler(CommandHandler("hisobot", hisobot))
    app.add_handler(CommandHandler("reja", reja))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("agentlar", agentlar))
    app.add_handler(CommandHandler("bonus", bonus))
    app.add_handler(CommandHandler("sinxron", sinxron))

    app.add_handler(CallbackQueryHandler(register_callback, pattern="^reg_"))
    app.add_handler(CallbackQueryHandler(update_sale_callback, pattern="^update_sale_|^cancel$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Kunlik hisobot: 18:00 Toshkent = 13:00 UTC
    job_queue = app.job_queue
    job_queue.run_daily(
        send_evening_report,
        time=datetime.strptime("13:00", "%H:%M").time(),
        days=(0, 1, 2, 3, 4, 5, 6)
    )

    print("🤖 Bot ishga tushdi! (Polling)")
    app.run_polling(drop_pending_updates=True)


def start_health_server():
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK - Bot ishlayapti!")
        def log_message(self, format, *args):
            pass

    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"✅ Health server port {port} da ishlamoqda")


if __name__ == '__main__':
    start_health_server()
    main()
