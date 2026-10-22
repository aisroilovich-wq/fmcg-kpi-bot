"""
Google Sheets sinxronizatsiya moduli
Varaqlar: ⚙️ Sozlamalar, 📅 Oylik Reja,
          🤖A1..🤖A16 (agentlar), 👔 S1..S3 (supervisorlar), 🏆 ROP
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1bIVzp2VbodtcaulMimxaHmOBvCVT85o7kn0Zi7Huf3c"

# Agent varaqlari ro'yxati (tartib bo'yicha)
AGENT_SHEETS = [f"🤖A{i}" for i in range(1, 17)]
# A2 nomi boshqacha — tekshirib ko'ramiz
SUPERVISOR_SHEETS = ["👔 S1", "👔 S2", "👔 S3"]


def get_sheets_client():
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

        return gspread.authorize(creds)
    except Exception as e:
        logger.error(f"Google Sheets ulanishda xato: {e}")
        return None


def get_spreadsheet():
    client = get_sheets_client()
    if not client:
        return None
    try:
        return client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        logger.error(f"Spreadsheet ochishda xato: {e}")
        return None


def get_monthly_plan():
    """📅 Oylik Reja: B3=agentlar soni, B4=jamoa reja"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None
        ws = sh.worksheet("📅 Oylik Reja")
        data = ws.get('B3:B4', value_render_option='UNFORMATTED_VALUE')
        logger.info(f"Oylik Reja B3:B4 = {data}")

        agent_soni = int(float(str(data[0][0]))) if data and data[0] else None
        jamoa_reja = int(float(str(data[1][0]))) if data and len(data) > 1 and data[1] else None

        if agent_soni and jamoa_reja:
            return {"jamoa_reja": jamoa_reja, "agent_soni": agent_soni}
        return None
    except Exception as e:
        logger.error(f"Oylik reja xato: {e}")
        return None


def get_all_sheet_names():
    """Barcha varaq nomlarini olish"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return []
        return [ws.title for ws in sh.worksheets()]
    except Exception as e:
        logger.error(f"Varaq nomlari xato: {e}")
        return []


def find_agent_sheet(agent_name: str):
    """Agent ismiga mos varaqni topish — D2 katakda ismi yozilgan"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None, None

        all_names = get_all_sheet_names()
        # Agent varaqlari: 🤖 bilan boshlanadi
        agent_sheets = [n for n in all_names if '🤖' in n or n.startswith('A')]

        for sheet_name in agent_sheets:
            try:
                ws = sh.worksheet(sheet_name)
                # D2 = agent ismi
                name_cell = ws.acell('D2', value_render_option='UNFORMATTED_VALUE').value
                if name_cell and agent_name.lower() in str(name_cell).lower():
                    logger.info(f"Agent '{agent_name}' → varaq '{sheet_name}'")
                    return ws, sheet_name
            except:
                continue
        return None, None
    except Exception as e:
        logger.error(f"Agent varaq topishda xato: {e}")
        return None, None


def get_agent_data(agent_name: str):
    """Agent o'z varag'idagi kunlik ma'lumotlarni olish"""
    try:
        ws, sheet_name = find_agent_sheet(agent_name)
        if not ws:
            return None

        # F5:F30 = haqiqiy savdo, E5:E30 = bugungi reja, H5:H30 = status
        data = ws.get('A5:K30', value_render_option='UNFORMATTED_VALUE')

        # Oylik reja (D3) va kunlik reja (G3)
        meta = ws.get('D3:G3', value_render_option='UNFORMATTED_VALUE')
        oylik_reja = None
        kunlik_reja = None
        try:
            if meta and meta[0]:
                oylik_reja = int(float(str(meta[0][0]))) if meta[0][0] else None
                kunlik_reja = int(float(str(meta[0][3]))) if len(meta[0]) > 3 and meta[0][3] else None
        except:
            pass

        kunlar = []
        jami_savdo = 0
        for row in data:
            if not row or len(row) < 6:
                continue
            try:
                kun = row[0]  # A ustun
                savdo = row[5]  # F ustun
                if not savdo or savdo == '':
                    continue
                savdo_val = int(float(str(savdo)))
                status = row[7] if len(row) > 7 else ''
                kunlar.append({'kun': kun, 'savdo': savdo_val, 'status': str(status)})
                jami_savdo += savdo_val
            except:
                continue

        return {
            'sheet_name': sheet_name,
            'oylik_reja': oylik_reja,
            'kunlik_reja': kunlik_reja,
            'jami_savdo': jami_savdo,
            'kunlar': kunlar,
            'kun_soni': len(kunlar)
        }
    except Exception as e:
        logger.error(f"Agent ma'lumot xato: {e}")
        return None


def get_supervisor_data(supervisor_name: str):
    """Supervisor varag'idan ma'lumot — S1, S2, S3"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None

        all_names = get_all_sheet_names()
        sup_sheets = [n for n in all_names if '👔' in n or 'S1' in n or 'S2' in n or 'S3' in n]

        # Har bir supervisor varag'ini tekshiramiz
        for sheet_name in sup_sheets:
            try:
                ws = sh.worksheet(sheet_name)
                data = ws.get('A1:D15', value_render_option='UNFORMATTED_VALUE')

                # B4=jamoa savdo, B5=jamoa reja, B8=fiksa, B9=komanda bonus, B10=plan bonus
                vals = ws.get('B3:B11', value_render_option='UNFORMATTED_VALUE')

                def safe_int(v):
                    try:
                        return int(float(str(v)))
                    except:
                        return 0

                fiksa_daraja = safe_int(vals[0][0]) if vals and vals[0] else 1
                jamoa_savdo = safe_int(vals[1][0]) if len(vals) > 1 and vals[1] else 0
                jamoa_reja = safe_int(vals[2][0]) if len(vals) > 2 and vals[2] else 0
                fiksa = safe_int(vals[5][0]) if len(vals) > 5 and vals[5] else 0
                komanda_b = safe_int(vals[6][0]) if len(vals) > 6 and vals[6] else 0
                plan_b = safe_int(vals[7][0]) if len(vals) > 7 and vals[7] else 0

                bajarilish = round(jamoa_savdo / jamoa_reja * 100, 1) if jamoa_reja > 0 else 0

                return {
                    'sheet_name': sheet_name,
                    'jamoa_savdo': jamoa_savdo,
                    'jamoa_reja': jamoa_reja,
                    'bajarilish_pct': bajarilish,
                    'fiksa': fiksa,
                    'komanda_bonus': komanda_b,
                    'plan_bonus': plan_b,
                    'jami': fiksa + komanda_b + plan_b
                }
            except Exception as e:
                logger.error(f"{sheet_name} xato: {e}")
                continue

        return None
    except Exception as e:
        logger.error(f"Supervisor data xato: {e}")
        return None


def get_rop_data():
    """🏆 ROP varag'idan ma'lumot"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None
        ws = sh.worksheet("🏆 ROP")

        vals = ws.get('B3:B14', value_render_option='UNFORMATTED_VALUE')

        def safe_int(i):
            try:
                return int(float(str(vals[i][0]))) if len(vals) > i and vals[i] else 0
            except:
                return 0

        fiksa = safe_int(0)        # B3
        jamoa_savdo = safe_int(1)  # B4
        jamoa_reja = safe_int(2)   # B5
        jamoa_bonus = safe_int(6)  # B9 = 2% bonus
        plan_bonus = safe_int(7)   # B10
        spets_bonus = safe_int(8)  # B11
        jami = safe_int(9)         # B12
        yakuniy = safe_int(11)     # B14 = MIN(jami, limit)

        bajarilish = round(jamoa_savdo / jamoa_reja * 100, 1) if jamoa_reja > 0 else 0

        return {
            'fiksa': fiksa,
            'jamoa_savdo': jamoa_savdo,
            'jamoa_reja': jamoa_reja,
            'jamoa_bonus': jamoa_bonus,
            'plan_bonus': plan_bonus,
            'spets_bonus': spets_bonus,
            'jami': yakuniy if yakuniy > 0 else jami,
            'bajarilish_pct': bajarilish
        }
    except Exception as e:
        logger.error(f"ROP data xato: {e}")
        return None


def get_ekspeditor_data(ekspeditor_name: str = None):
    """🚚 Ekspeditor varag'idan ma'lumot — E1, E2, E3"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None

        all_names = get_all_sheet_names()
        exp_sheets = [n for n in all_names if '🚚' in n]

        for sheet_name in exp_sheets:
            try:
                ws = sh.worksheet(sheet_name)
                vals = ws.get('B3:B13', value_render_option='UNFORMATTED_VALUE')

                def safe_int(i):
                    try:
                        return int(float(str(vals[i][0]))) if len(vals) > i and vals[i] else 0
                    except:
                        return 0

                def safe_float(i):
                    try:
                        return float(str(vals[i][0])) if len(vals) > i and vals[i] else 0
                    except:
                        return 0

                yetkazilgan = safe_int(1)   # B4
                reja_buy = safe_int(2)       # B5
                fiksa = safe_int(5)          # B8
                yetkazish_b = safe_int(6)    # B9
                spets_b = safe_int(7)        # B10
                yakuniy = safe_int(10)       # B13

                bajarilish = round(yetkazilgan / reja_buy * 100, 1) if reja_buy > 0 else 0

                return {
                    'sheet_name': sheet_name,
                    'yetkazilgan': yetkazilgan,
                    'reja': reja_buy,
                    'bajarilish_pct': bajarilish,
                    'fiksa': fiksa,
                    'yetkazish_bonus': yetkazish_b,
                    'spets_bonus': spets_b,
                    'jami': yakuniy
                }
            except Exception as e:
                logger.error(f"{sheet_name} xato: {e}")
                continue

        return None
    except Exception as e:
        logger.error(f"Ekspeditor data xato: {e}")
        return None


def get_jamoa_hisobot():
    """📈 Jamoa Hisobot varag'idan umumiy ko'rsatkichlar"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None
        ws = sh.worksheet("📈 Jamoa Hisobot")
        vals = ws.get('B3:D4', value_render_option='UNFORMATTED_VALUE')

        def safe_int(row, col):
            try:
                return int(float(str(vals[row][col])))
            except:
                return 0

        jamoa_reja = safe_int(0, 0)
        haqiqiy = safe_int(0, 1)
        agent_reja = safe_int(1, 0)
        agent_haqiqiy = safe_int(1, 1)

        bajarilish = round(haqiqiy / jamoa_reja * 100, 1) if jamoa_reja > 0 else 0

        return {
            'jamoa_reja': jamoa_reja,
            'haqiqiy_savdo': haqiqiy,
            'bajarilish_pct': bajarilish,
            'agent_soni': agent_haqiqiy
        }
    except Exception as e:
        logger.error(f"Jamoa hisobot xato: {e}")
        return None
