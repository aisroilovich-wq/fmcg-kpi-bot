"""
Google Sheets sinxronizatsiya moduli
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1bIVzp2VbodtcaulMimxaHmOBvCVT85o7kn0Zi7Huf3c"


def get_sheets_client():
    try:
        import gspread
        from google.oauth2 import service_account

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # Env variable dan o'qish
        creds_json = os.environ.get("GOOGLE_CREDENTIALS", "").strip()
        if creds_json and creds_json.startswith("{"):
            info = json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
            client = gspread.authorize(creds)
            logger.info("Google Sheets ulandi (env)")
            return client

        # Secret file dan o'qish
        for path in ["/etc/secrets/google_credentials.json", "google_credentials.json"]:
            if os.path.exists(path):
                from google.oauth2.service_account import Credentials
                creds = Credentials.from_service_account_file(path, scopes=scopes)
                client = gspread.authorize(creds)
                logger.info(f"Google Sheets ulandi (fayl: {path})")
                return client

        logger.error("GOOGLE_CREDENTIALS topilmadi")
        return None
    except Exception as e:
        logger.error(f"Sheets ulanish xato: {e}")
        return None


def get_spreadsheet():
    client = get_sheets_client()
    if not client:
        return None
    try:
        return client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        logger.error(f"Spreadsheet xato: {e}")
        return None


def safe_int(val):
    try:
        return int(float(str(val)))
    except:
        return 0


def get_agent_data(agent_name: str):
    """Agent o'z varag'idagi ma'lumotlar"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None

        all_sheets = [ws.title for ws in sh.worksheets()]
        agent_sheets = [n for n in all_sheets if '🤖' in n]

        for sheet_name in agent_sheets:
            try:
                ws = sh.worksheet(sheet_name)
                name_cell = ws.acell('D2', value_render_option='UNFORMATTED_VALUE').value
                if name_cell and agent_name.lower() in str(name_cell).lower():
                    # Ma'lumotlarni olish
                    meta = ws.get('D3:G3', value_render_option='UNFORMATTED_VALUE')
                    rows = ws.get('A5:K30', value_render_option='UNFORMATTED_VALUE')

                    oylik_reja = safe_int(meta[0][0]) if meta and meta[0] else 0
                    kunlik_reja = safe_int(meta[0][3]) if meta and meta[0] and len(meta[0]) > 3 else 0

                    jami_savdo = 0
                    kunlar = []
                    for row in rows:
                        if len(row) < 6 or not row[5]:
                            continue
                        savdo = safe_int(row[5])
                        if savdo > 0:
                            jami_savdo += savdo
                            kunlar.append({
                                'kun': row[0],
                                'savdo': savdo,
                                'status': str(row[7]) if len(row) > 7 else ''
                            })

                    bajarilish = round(jami_savdo / oylik_reja * 100, 1) if oylik_reja > 0 else 0

                    return {
                        'ism': str(name_cell),
                        'sheet': sheet_name,
                        'oylik_reja': oylik_reja,
                        'kunlik_reja': kunlik_reja,
                        'jami_savdo': jami_savdo,
                        'bajarilish': bajarilish,
                        'kun_soni': len(kunlar)
                    }
            except:
                continue
        return None
    except Exception as e:
        logger.error(f"Agent data xato: {e}")
        return None


def get_supervisor_data(supervisor_name: str):
    """Supervisor varag'idan ma'lumot"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None

        all_sheets = [ws.title for ws in sh.worksheets()]
        sup_sheets = [n for n in all_sheets if '👔' in n]

        for sheet_name in sup_sheets:
            try:
                ws = sh.worksheet(sheet_name)
                # D2 da supervisor ismi
                name_cell = ws.acell('D2', value_render_option='UNFORMATTED_VALUE').value
                if name_cell and supervisor_name.lower() in str(name_cell).lower():
                    vals = ws.get('B3:B11', value_render_option='UNFORMATTED_VALUE')

                    def v(i):
                        return safe_int(vals[i][0]) if len(vals) > i and vals[i] else 0

                    jamoa_savdo = v(1)
                    jamoa_reja = v(2)
                    fiksa = v(5)
                    komanda_bonus = v(6)
                    plan_bonus = v(7)
                    bajarilish = round(jamoa_savdo / jamoa_reja * 100, 1) if jamoa_reja > 0 else 0

                    return {
                        'ism': str(name_cell),
                        'sheet': sheet_name,
                        'jamoa_savdo': jamoa_savdo,
                        'jamoa_reja': jamoa_reja,
                        'bajarilish': bajarilish,
                        'fiksa': fiksa,
                        'komanda_bonus': komanda_bonus,
                        'plan_bonus': plan_bonus,
                        'jami': fiksa + komanda_bonus + plan_bonus
                    }
            except:
                continue
        return None
    except Exception as e:
        logger.error(f"Supervisor data xato: {e}")
        return None


def get_ekspeditor_data(ekspeditor_name: str):
    """Ekspeditor varag'idan ma'lumot"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None

        all_sheets = [ws.title for ws in sh.worksheets()]
        exp_sheets = [n for n in all_sheets if '🚚' in n]

        for sheet_name in exp_sheets:
            try:
                ws = sh.worksheet(sheet_name)
                name_cell = ws.acell('D2', value_render_option='UNFORMATTED_VALUE').value
                if name_cell and ekspeditor_name.lower() in str(name_cell).lower():
                    vals = ws.get('B3:B13', value_render_option='UNFORMATTED_VALUE')

                    def v(i):
                        return safe_int(vals[i][0]) if len(vals) > i and vals[i] else 0

                    yetkazilgan = v(1)
                    reja = v(2)
                    fiksa = v(5)
                    yetkazish_bonus = v(6)
                    spets_bonus = v(7)
                    yakuniy = v(10)
                    bajarilish = round(yetkazilgan / reja * 100, 1) if reja > 0 else 0

                    return {
                        'ism': str(name_cell),
                        'sheet': sheet_name,
                        'yetkazilgan': yetkazilgan,
                        'reja': reja,
                        'bajarilish': bajarilish,
                        'fiksa': fiksa,
                        'yetkazish_bonus': yetkazish_bonus,
                        'spets_bonus': spets_bonus,
                        'jami': yakuniy
                    }
            except:
                continue
        return None
    except Exception as e:
        logger.error(f"Ekspeditor data xato: {e}")
        return None


def get_rop_data():
    """ROP varag'idan ma'lumot"""
    try:
        sh = get_spreadsheet()
        if not sh:
            return None

        ws = sh.worksheet("🏆 ROP")
        vals = ws.get('B3:B14', value_render_option='UNFORMATTED_VALUE')

        def v(i):
            return safe_int(vals[i][0]) if len(vals) > i and vals[i] else 0

        jamoa_savdo = v(1)
        jamoa_reja = v(2)
        fiksa = v(0)
        jamoa_bonus = v(6)
        plan_bonus = v(7)
        spets_bonus = v(8)
        jami = v(9)
        yakuniy = v(11)
        bajarilish = round(jamoa_savdo / jamoa_reja * 100, 1) if jamoa_reja > 0 else 0

        return {
            'jamoa_savdo': jamoa_savdo,
            'jamoa_reja': jamoa_reja,
            'bajarilish': bajarilish,
            'fiksa': fiksa,
            'jamoa_bonus': jamoa_bonus,
            'plan_bonus': plan_bonus,
            'spets_bonus': spets_bonus,
            'jami': yakuniy if yakuniy > 0 else jami
        }
    except Exception as e:
        logger.error(f"ROP data xato: {e}")
        return None
