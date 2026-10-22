"""
Google Sheets sinxronizatsiya moduli
Excel varaq nomlari: ⚙️ Sozlamalar, 📅 Oylik Reja, 👤 Agent Tracker,
                    📊 Agent KPI, 👔 Supervisor, 🏆 ROP, 📈 Jamoa Hisobot
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

        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            secret_path = "/etc/secrets/google_credentials.json"
            local_path = "google_credentials.json"
            filepath = secret_path if os.path.exists(secret_path) else local_path
            creds = Credentials.from_service_account_file(filepath, scopes=scopes)

        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logger.error(f"Google Sheets ulanishda xato: {e}")
        return None


def get_spreadsheet():
    """Spreadsheet ochish"""
    client = get_sheets_client()
    if not client:
        return None
    try:
        return client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        logger.error(f"Spreadsheet ochishda xato: {e}")
        return None


def get_monthly_plan():
    """📅 Oylik Reja varag'idan jamoa reja va agent soni"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None
        ws = sh.worksheet("📅 Oylik Reja")
        # B3 = agentlar soni, B4 = jamoa oylik reja
        agent_soni = ws.acell('B3').value
        jamoa_reja = ws.acell('B4').value

        if jamoa_reja and agent_soni:
            reja = int(float(str(jamoa_reja).replace(',', '').replace(' ', '')))
            soni = int(float(str(agent_soni)))
            logger.info(f"Oylik reja: {reja:,}, agentlar: {soni}")
            return {"jamoa_reja": reja, "agent_soni": soni}
        return None
    except Exception as e:
        logger.error(f"Oylik reja olishda xato: {e}")
        return None


def get_sozlamalar():
    """⚙️ Sozlamalar varag'idan KPI parametrlari"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None
        ws = sh.worksheet("⚙️ Sozlamalar")
        # B3=fiksa1, B4=fiksa2, B5=fiksa3
        # B7=yuqori bonus, B8=orta daraja min, B9=orta bonus, B10=past bonus
        vals = ws.batch_get(['B3', 'B4', 'B5', 'B7', 'B9', 'B10'])
        def v(cell):
            try:
                return int(float(str(cell[0][0]).replace(',', '')))
            except:
                return None

        return {
            'fiksa_1': v(vals[0]),  # 8,000,000
            'fiksa_2': v(vals[1]),  # 6,000,000
            'fiksa_3': v(vals[2]),  # 4,000,000
            'bonus_yuqori': v(vals[3]),  # 154,000
            'bonus_orta': v(vals[4]),    # 96,000
            'bonus_past': v(vals[5]),    # 75,000
        }
    except Exception as e:
        logger.error(f"Sozlamalar olishda xato: {e}")
        return None


def get_agent_report(agent_name: str):
    """👤 Agent Tracker — agent o'z ma'lumotlari"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None
        ws = sh.worksheet("👤 Agent Tracker")
        all_vals = ws.get_all_values()

        # D2 = agent ismi
        # F5:F30 = kunlik savdolar (haqiqiy)
        # C5 = kunlik reja
        # D5:D30 = yuklanma
        # E5:E30 = bugungi reja (kunlik + yuklanma)
        # G5:G30 = farq
        # H5:H30 = status

        result = {
            'agent_nomi': all_vals[1][3] if len(all_vals) > 1 else '',
            'oylik_reja': None,
            'kunlik_reja': None,
            'kunlar': []
        }

        # Oylik reja (D3)
        try:
            result['oylik_reja'] = int(float(str(all_vals[2][3]).replace(',', ''))) if all_vals[2][3] else None
        except:
            pass

        # Kunlik reja (G3)
        try:
            result['kunlik_reja'] = int(float(str(all_vals[2][6]).replace(',', ''))) if len(all_vals[2]) > 6 else None
        except:
            pass

        # Kunlar (5-qatordan boshlab = index 4)
        for i, row in enumerate(all_vals[4:30], 1):
            if len(row) < 8:
                continue
            try:
                savdo = row[5]  # F ustun
                if not savdo or savdo == '':
                    continue
                savdo_val = int(float(str(savdo).replace(',', '')))
                status = row[7] if len(row) > 7 else ''
                result['kunlar'].append({
                    'kun': i,
                    'savdo': savdo_val,
                    'status': status
                })
            except:
                continue

        return result
    except Exception as e:
        logger.error(f"Agent tracker olishda xato: {e}")
        return None


def get_supervisor_report():
    """👔 Supervisor varag'idan ma'lumotlar"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None
        ws = sh.worksheet("👔 Supervisor")
        all_vals = ws.get_all_values()

        result = {}
        for row in all_vals:
            if len(row) < 2:
                continue
            key = str(row[0]).strip()
            val = str(row[1]).strip() if row[1] else ''
            try:
                num = int(float(val.replace(',', '').replace(' ', '')))
                if 'savdo' in key.lower() and 'jamoa' in key.lower():
                    result['jamoa_savdo'] = num
                elif 'fiksa' in key.lower():
                    result['fiksa'] = num
                elif 'komanda bonus' in key.lower():
                    result['komanda_bonus'] = num
                elif 'plan bonus' in key.lower():
                    result['plan_bonus'] = num
            except:
                pass

        # Hisoblangan qatorlar (formulalar qiymatlari)
        # B4=jamoa savdo, B8=fiksa, B9=komanda bonus, B10=plan bonus
        try:
            jamoa_savdo = ws.acell('B4').value
            fiksa = ws.acell('B8').value
            komanda_b = ws.acell('B9').value
            plan_b = ws.acell('B10').value

            if jamoa_savdo:
                result['jamoa_savdo'] = int(float(str(jamoa_savdo).replace(',', '')))
            if fiksa:
                result['fiksa'] = int(float(str(fiksa).replace(',', '')))
            if komanda_b:
                result['komanda_bonus'] = int(float(str(komanda_b).replace(',', '')))
            if plan_b:
                result['plan_bonus'] = int(float(str(plan_b).replace(',', '')))

            result['jami'] = result.get('fiksa', 0) + result.get('komanda_bonus', 0) + result.get('plan_bonus', 0)
        except Exception as e:
            logger.error(f"Supervisor hisob xato: {e}")

        return result
    except Exception as e:
        logger.error(f"Supervisor report xato: {e}")
        return None


def get_rop_report():
    """🏆 ROP varag'idan ma'lumotlar"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None
        ws = sh.worksheet("🏆 ROP")

        fiksa = ws.acell('B3').value
        jamoa_savdo = ws.acell('B4').value
        jamoa_reja = ws.acell('B5').value
        plan_b = ws.acell('B11').value
        spets_b = ws.acell('B12').value

        result = {}
        for k, v in [('fiksa', fiksa), ('jamoa_savdo', jamoa_savdo),
                     ('jamoa_reja', jamoa_reja), ('plan_bonus', plan_b),
                     ('spets_bonus', spets_b)]:
            try:
                result[k] = int(float(str(v).replace(',', ''))) if v else 0
            except:
                result[k] = 0

        # Jamoa bonus (2%)
        result['jamoa_bonus'] = int(result.get('jamoa_savdo', 0) * 0.02)
        result['jami'] = (result.get('fiksa', 0) + result.get('jamoa_bonus', 0) +
                          result.get('plan_bonus', 0) + result.get('spets_bonus', 0))

        # Bajarilish %
        if result.get('jamoa_reja', 0) > 0:
            result['bajarilish_pct'] = round(result['jamoa_savdo'] / result['jamoa_reja'] * 100, 1)
        else:
            result['bajarilish_pct'] = 0

        return result
    except Exception as e:
        logger.error(f"ROP report xato: {e}")
        return None


def get_jamoa_hisobot():
    """📈 Jamoa Hisobot varag'idan umumiy ko'rsatkichlar"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None
        ws = sh.worksheet("📈 Jamoa Hisobot")

        jamoa_reja = ws.acell('B3').value
        agent_soni = ws.acell('B4').value
        haqiqiy_savdo = ws.acell('C3').value
        bajarilish = ws.acell('D3').value

        result = {}
        for k, v in [('jamoa_reja', jamoa_reja), ('agent_soni', agent_soni),
                     ('haqiqiy_savdo', haqiqiy_savdo)]:
            try:
                result[k] = int(float(str(v).replace(',', ''))) if v else 0
            except:
                result[k] = 0

        try:
            result['bajarilish_pct'] = round(float(str(bajarilish)) * 100, 1) if bajarilish else 0
        except:
            result['bajarilish_pct'] = 0

        return result
    except Exception as e:
        logger.error(f"Jamoa hisobot xato: {e}")
        return None
