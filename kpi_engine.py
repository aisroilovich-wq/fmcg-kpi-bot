"""
KPI hisoblash mexanizmi — Excel faylidagi formula bilan bir xil
Yuklanma (carryover), kunlik bonus, oylik bonus hisoblaydi
"""

import calendar
from datetime import date
from typing import Dict, Optional
from config import Config


class KPIEngine:
    def __init__(self, db):
        self.db = db

    def _get_plans(self, user_id: int, year: int, month: int) -> tuple:
        """Agent oylik va kunlik reja"""
        plan = self.db.get_monthly_plan(year, month)
        agents = self.db.get_all_agents()
        agent_count = len(agents)

        if not plan or agent_count == 0:
            # Reja o'rnatilmagan bo'lsa default
            oylik_reja = Config.WORKING_DAYS * 800_000  # ~20.8M default
            oylik_reja = max(oylik_reja, 1)
        else:
            oylik_reja = plan['total'] // agent_count

        kunlik_reja = oylik_reja // Config.WORKING_DAYS
        return oylik_reja, kunlik_reja

    def calculate_day(self, user_id: int, target_date: date) -> Dict:
        """
        Bitta agent, bitta kun uchun hisoblash.
        Yuklanma logikasi: agar oldingi kun rejadan qolsa, bugunga qo'shiladi.
        """
        year, month = target_date.year, target_date.month
        oylik_reja, kunlik_reja = self._get_plans(user_id, year, month)

        # Oylik barcha savdolar (tartib bo'yicha)
        monthly_sales = self.db.get_monthly_sales(user_id, year, month)

        # Bugungi savdo
        bugungi_sale = self.db.get_daily_sale(user_id, target_date)
        bugungi_savdo = bugungi_sale['amount'] if bugungi_sale else 0

        # Yuklanma hisoblash
        # Excel formulasi: =IF(G_prev < 0, ABS(G_prev), 0)
        # G = savdo + yuklanma - kunlik_reja
        yuklanma = 0

        for sale in monthly_sales:
            sale_date = date.fromisoformat(str(sale['sale_date'])) if isinstance(sale['sale_date'], str) else sale['sale_date']
            if sale_date >= target_date:
                break

            # Oldingi kunning farqi
            prev_amount = sale['amount']
            # (Bu kunning yuklanmasi oldingi kunda hisoblangan)
            prev_balance = prev_amount + yuklanma - kunlik_reja

            if prev_balance < 0:
                yuklanma = abs(prev_balance)  # Keyingi kunga yuklanma
            else:
                yuklanma = 0

        # Agar target_date=bugun va hali savdo yo'q
        if bugungi_savdo == 0:
            return {
                'savdo': 0,
                'yuklanma': yuklanma,
                'kunlik_reja': kunlik_reja,
                'oylik_reja': oylik_reja,
                'bajarildi_pct': 0,
                'status_emoji': '⬜',
                'kunlik_bonus': 0,
                'shortfall': kunlik_reja,
                'recommendation': f"⏳ Savdo kiritilmagan. Reja: {kunlik_reja:,} so'm"
            }

        # Jami (savdo + yuklanma)
        jami = bugungi_savdo + yuklanma

        # Kunlik reja foizi
        bajarildi_pct = (jami / kunlik_reja * 100) if kunlik_reja > 0 else 0

        # Status
        if bajarildi_pct >= 100:
            status_emoji = '✅'
        elif bajarildi_pct >= 80:
            status_emoji = '🟡'
        else:
            status_emoji = '🔴'

        # Kunlik bonus
        kunlik_bonus = 0
        if jami >= Config.KUNLIK_BONUS_2_MIN:
            kunlik_bonus = Config.KUNLIK_BONUS_2_AMOUNT
        elif jami >= Config.KUNLIK_BONUS_1_MIN:
            kunlik_bonus = Config.KUNLIK_BONUS_1_AMOUNT

        # Shortfall
        shortfall = max(0, kunlik_reja - jami)

        # Tavsiya
        recommendation = _make_day_recommendation(jami, kunlik_reja, shortfall, status_emoji)

        return {
            'savdo': bugungi_savdo,
            'yuklanma': yuklanma,
            'jami': jami,
            'kunlik_reja': kunlik_reja,
            'oylik_reja': oylik_reja,
            'bajarildi_pct': bajarildi_pct,
            'status_emoji': status_emoji,
            'kunlik_bonus': kunlik_bonus,
            'shortfall': shortfall,
            'recommendation': recommendation,
        }

    def calculate_month(self, user_id: int, year: int, month: int) -> Dict:
        """
        Bitta agent, to'liq oy uchun hisoblash.
        """
        oylik_reja, kunlik_reja = self._get_plans(user_id, year, month)
        monthly_sales = self.db.get_monthly_sales(user_id, year, month)

        if not monthly_sales:
            return {
                'total_sales': 0,
                'days_worked': 0,
                'oylik_reja': oylik_reja,
                'reja_pct': 0,
                'fiksa': 0,
                'kunlik_bonuslar': 0,
                'oylik_bonus': 0,
                'spets_zadacha': 0,
                'jami_maosh': Config.FIKSA,
            }

        total_sales = 0
        kunlik_bonuslar = 0
        yuklanma = 0
        days_worked = len(monthly_sales)

        for sale in monthly_sales:
            amount = sale['amount']
            jami_kun = amount + yuklanma

            # Kunlik bonus
            if jami_kun >= Config.KUNLIK_BONUS_2_MIN:
                kunlik_bonuslar += Config.KUNLIK_BONUS_2_AMOUNT
            elif jami_kun >= Config.KUNLIK_BONUS_1_MIN:
                kunlik_bonuslar += Config.KUNLIK_BONUS_1_AMOUNT

            # Yuklanma yangilash
            balance = jami_kun - kunlik_reja
            yuklanma = abs(balance) if balance < 0 else 0

            total_sales += amount

        # Oylik reja foizi
        reja_pct = (total_sales / oylik_reja * 100) if oylik_reja > 0 else 0

        # Oylik reja bonusi
        oylik_bonus = Config.OYLIK_REJA_BONUS if reja_pct >= 100 else 0

        # Spets zadacha
        spets = self.db.get_spets_zadacha(user_id, year, month)

        # Fiksa (to'liq oy bo'lsa)
        fiksa = Config.FIKSA

        # Jami maosh
        jami_maosh = fiksa + kunlik_bonuslar + oylik_bonus + spets

        return {
            'total_sales': total_sales,
            'days_worked': days_worked,
            'oylik_reja': oylik_reja,
            'kunlik_reja': kunlik_reja,
            'reja_pct': reja_pct,
            'fiksa': fiksa,
            'kunlik_bonuslar': kunlik_bonuslar,
            'oylik_bonus': oylik_bonus,
            'spets_zadacha': spets,
            'jami_maosh': jami_maosh,
        }


def _make_day_recommendation(jami: int, kunlik_reja: int, shortfall: int, status: str) -> str:
    if status == '✅':
        return f"🎉 Ajoyib! Kunlik reja bajarildi!"
    elif status == '🟡':
        return f"📌 Ertaga {shortfall:,} so'm qo'shimcha kerak (yuklanma)"
    else:
        return (
            f"⚠️ Reja bajarilmadi. Yetmaydi: {shortfall:,} so'm\n"
            f"📌 Bu miqdor ertaga yuklanma sifatida qo'shiladi"
        )
