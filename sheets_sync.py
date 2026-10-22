"""
Google Sheets sinxronizatsiya moduli
Excel ma'lumotlarini Google Sheets dan o'qiydi
"""

import os
import json
import logging
from datetime import date

logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1bIVzp2VbodtcaulMimxaHmOBvCVT85o7kn0Zi7Huf3c"

def get_sheets_client():
    """Google Sheets client yaratish"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # Render da environment variable dan olish
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            # Render Secret Files yoki lokal fayl
            import os.path
            secret_path = "/etc/secrets/google_credentials.json"
            local_path = "google_credentials.json"
            filepath = secret_path if os.path.exists(secret_path) else local_path
            creds = Credentials.from_service_account_file(filepath, scopes=scopes)

        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logger.error(f"Google Sheets ulanishda xato: {e}")
        return None


def get_monthly_plan_from_sheets():
    """Sheets dan oylik reja va agent sonini olish"""
    try:
        client = get_sheets_client()
        if not client:
            return None

        sh = client.open_by_key(SPREADSHEET_ID)

        # "📅 Oylik Reja" varag'ini topish
        try:
            ws = sh.worksheet("📅 Oylik Reja")
        except:
            # Varaq nomini topish
            worksheets = sh.worksheets()
            ws = None
            for w in worksheets:
                if "Reja" in w.title or "reja" in w.title.lower():
                    ws = w
                    break
            if not ws:
                ws = worksheets[1] if len(worksheets) > 1 else worksheets[0]

        # B4 = Jamoa oylik reja, B3 = Agentlar soni
        all_values = ws.get_all_values()

        jamoa_reja = None
        agent_soni = None

        for row in all_values:
            for i, cell in enumerate(row):
                if "JAMOA OYLIK REJA" in str(cell).upper() or "JAMOA OYLIK" in str(cell).upper():
                    # Keyingi katakdan qiymat olish
                    if i + 1 < len(row) and row[i+1]:
                        try:
                            val = str(row[i+1]).replace(' ', '').replace(',', '').replace("'", '')
                            jamoa_reja = int(float(val))
                        except:
                            pass
                if "AGENTLAR SONI" in str(cell).upper() or "SAVDO VAKILLARI" in str(cell).upper():
                    if i + 1 < len(row) and row[i+1]:
                        try:
                            agent_soni = int(float(str(row[i+1])))
                        except:
                            pass

        if jamoa_reja and agent_soni:
            logger.info(f"Sheets dan olindi: reja={jamoa_reja}, agentlar={agent_soni}")
            return {"jamoa_reja": jamoa_reja, "agent_soni": agent_soni}

        # Fallback: B4 va B3 ni to'g'ridan olish
        try:
            reja_cell = ws.acell('B4').value
            agent_cell = ws.acell('B3').value
            if reja_cell and agent_cell:
                jamoa_reja = int(float(str(reja_cell).replace(',', '')))
                agent_soni = int(float(str(agent_cell)))
                return {"jamoa_reja": jamoa_reja, "agent_soni": agent_soni}
        except:
            pass

        return None

    except Exception as e:
        logger.error(f"Sheets dan ma'lumot olishda xato: {e}")
        return None


def get_settings_from_sheets():
    """Sheets dan KPI sozlamalarini olish"""
    try:
        client = get_sheets_client()
        if not client:
            return None

        sh = client.open_by_key(SPREADSHEET_ID)

        # "⚙️ Sozlamalar" varag'ini topish
        worksheets = sh.worksheets()
        ws = None
        for w in worksheets:
            if "Sozlama" in w.title or "sozlama" in w.title.lower() or "Settings" in w.title:
                ws = w
                break
        if not ws:
            ws = worksheets[0]

        all_values = ws.get_all_values()

        settings = {}
        for row in all_values:
            if len(row) < 2:
                continue
            key = str(row[0]).strip()
            val = str(row[1]).strip() if row[1] else ""

            try:
                num = float(val.replace(',', '').replace(' ', ''))
                if "Fiksa 1" in key or "yuqori" in key.lower():
                    settings['fiksa_1'] = int(num)
                elif "Fiksa 2" in key or "o'rta" in key.lower():
                    settings['fiksa_2'] = int(num)
                elif "Fiksa 3" in key or "past" in key.lower():
                    settings['fiksa_3'] = int(num)
                elif "1 500 000" in key or "Yuqori daraja" in key:
                    settings['kunlik_bonus_yuqori'] = int(num)
                elif "800K" in key or "O'rta daraja" in key:
                    settings['kunlik_bonus_orta'] = int(num)
                elif "Past daraja" in key:
                    settings['kunlik_bonus_past'] = int(num)
                elif "100% bajarish" in key:
                    settings['oylik_bonus_100'] = int(num)
                elif "120% bajarish" in key:
                    settings['oylik_bonus_120'] = int(num)
                elif "Spets zadacha bonusi" in key:
                    settings['spets_bonus'] = int(num)
                elif "ishchi kunlar" in key.lower():
                    settings['ish_kunlar'] = int(num)
            except:
                pass

        logger.info(f"Sozlamalar olindi: {settings}")
        return settings if settings else None

    except Exception as e:
        logger.error(f"Sozlamalar olishda xato: {e}")
        return None


def sync_to_database(db):
    """Sheets ma'lumotlarini bazaga sinxronlashtirish"""
    today = date.today()

    # Oylik reja
    plan_data = get_monthly_plan_from_sheets()
    if plan_data:
        db.set_monthly_plan(
            today.year,
            today.month,
            plan_data['jamoa_reja'],
            user_id=0  # System
        )
        logger.info(f"Oylik reja yangilandi: {plan_data['jamoa_reja']:,} so'm")
        return True

    return False
