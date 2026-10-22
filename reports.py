"""
Hisobot generatori — kunlik va oylik
"""

import calendar
from datetime import date
from typing import List, Dict
from config import Config


class ReportGenerator:
    def __init__(self, db, kpi):
        self.db = db
        self.kpi = kpi

    def daily_team_report(self, today: date = None) -> str:
        """Bugungi jamoa hisoboti (supervisor/ROP uchun)"""
        if today is None:
            today = date.today()

        agents = self.db.get_all_agents()
        if not agents:
            return "Hali agentlar ro'yxatdan o'tmagan."

        plan = self.db.get_monthly_plan(today.year, today.month)
        agent_count = len(agents)

        if plan and agent_count > 0:
            oylik_agent_reja = plan['total'] // agent_count
            kunlik_reja = oylik_agent_reja // Config.WORKING_DAYS
        else:
            kunlik_reja = 800_000

        results = []
        total_savdo = 0
        total_reja = 0
        entered_count = 0

        for agent in agents:
            sale = self.db.get_daily_sale(agent['user_id'], today)
            result = self.kpi.calculate_day(agent['user_id'], today)
            k_reja = result.get('kunlik_reja', kunlik_reja)
            yuklanma = result.get('yuklanma', 0)

            if sale:
                amount = sale['amount']
                bajarildi = result.get('bajarildi_pct', 0)
                status = result.get('status_emoji', '🟡')
                entered_count += 1
                total_savdo += amount
            else:
                amount = None
                bajarildi = 0
                status = '⬜'

            total_reja += k_reja
            results.append({
                'name': agent['name'],
                'amount': amount,
                'bajarildi': bajarildi,
                'status': status,
                'kunlik_reja': k_reja,
                'yuklanma': yuklanma,
            })

        # Natijalarni yaxshidan yomonga tartiblash
        results.sort(key=lambda x: x['bajarildi'], reverse=True)

        # Header
        text = (
            f"📊 *Kunlik hisobot — {today.strftime('%d.%m.%Y')}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        # Har bir agent
        for r in results:
            if r['amount'] is not None:
                text += f"{r['status']} *{r['name']}*\n"
                text += f"   💰 {r['amount']:,} so'm ({r['bajarildi']:.0f}%)\n"
                if r['yuklanma'] > 0:
                    text += f"   📦 yuklanma: +{r['yuklanma']:,}\n"
            else:
                text += f"⬜ *{r['name']}*\n"
                text += f"   ⏳ Kiritilmagan (reja: {r['kunlik_reja']:,})\n"

        # Jamoa jami
        team_pct = (total_savdo / total_reja * 100) if total_reja > 0 else 0

        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 *Jami: {total_savdo:,} so'm ({team_pct:.0f}%)*\n"
            f"📊 Kiritgan: {entered_count}/{agent_count}\n"
        )

        if entered_count < agent_count:
            not_entered = agent_count - entered_count
            text += f"⚠️ {not_entered} ta agent kiritmagan\n"

        return text

    def monthly_team_report(self, year: int, month: int) -> str:
        """Oylik jamoa hisoboti"""
        agents = self.db.get_all_agents()
        if not agents:
            return "Hali agentlar ro'yxatdan o'tmagan."

        month_name = f"{year}-{month:02d}"

        text = (
            f"📅 *Oylik hisobot — {month_name}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        results = []
        total_savdo = 0
        total_maosh = 0

        for agent in agents:
            result = self.kpi.calculate_month(agent['user_id'], year, month)
            results.append({
                'name': agent['name'],
                'total_sales': result.get('total_sales', 0),
                'reja_pct': result.get('reja_pct', 0),
                'jami_maosh': result.get('jami_maosh', 0),
                'days_worked': result.get('days_worked', 0),
            })
            total_savdo += result.get('total_sales', 0)
            total_maosh += result.get('jami_maosh', 0)

        # Eng yaxshidan tartiblash
        results.sort(key=lambda x: x['reja_pct'], reverse=True)

        for r in results:
            status = "✅" if r['reja_pct'] >= 100 else ("🟡" if r['reja_pct'] >= 80 else "🔴")
            text += (
                f"{status} *{r['name']}*\n"
                f"   💰 {r['total_sales']:,} so'm ({r['reja_pct']:.0f}%)\n"
                f"   💵 Maosh: {r['jami_maosh']:,} | Kun: {r['days_worked']}\n\n"
            )

        text += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Jamoa savdo: {total_savdo:,} so'm*\n"
            f"💵 *Jamoa maosh: {total_maosh:,} so'm*"
        )

        return text
