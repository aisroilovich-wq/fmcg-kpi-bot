"""
FMCG KPI Bot — Konfiguratsiya
Bu faylni o'zingizga moslashtiring!
"""

class Config:
    # ═══════════════════════════════════════════════════
    # 🔑 MUHIM: Shu yerga o'z tokeningizni kiriting!
    # @BotFather dan olingan token
    # ═══════════════════════════════════════════════════
    BOT_TOKEN = "8914647800:AAGIMAy_gN9bc0PmaMjwsobKA7lAItsuK_Q"

    # ROP/Direktor uchun parol (ro'yxatdan o'tishda so'raladi)
    ROP_PASSWORD = "admin2024"

    # ═══════════════════════════════════════════════════
    # KPI Sozlamalari (Excel faylidagi kabi)
    # ═══════════════════════════════════════════════════

    # Oylik ish kunlari
    WORKING_DAYS = 26

    # Fiksa (boshlang'ich maosh) — so'mda
    FIKSA = 3_000_000

    # Kunlik bonus tizimlari:
    # Agar agent >= KUNLIK_BONUS_1_MIN va < KUNLIK_BONUS_1_MAX → KUNLIK_BONUS_1 so'm
    # Agar agent >= KUNLIK_BONUS_2_MIN → KUNLIK_BONUS_2 so'm

    KUNLIK_BONUS_1_MIN = 800_000      # 800K+ → 1-daraja bonus
    KUNLIK_BONUS_1_AMOUNT = 15_000    # 15,000 so'm

    KUNLIK_BONUS_2_MIN = 1_500_000    # 1.5M+ → 2-daraja bonus
    KUNLIK_BONUS_2_AMOUNT = 30_000    # 30,000 so'm

    # Oylik reja bonusi (reja 100%+ bajarilsa)
    OYLIK_REJA_BONUS = 500_000        # 500,000 so'm

    # Spets zadacha (qo'shimcha)
    SPETS_ZADACHA = 200_000           # 200,000 so'm (default, o'zgartirilishi mumkin)

    # Yuklanma: agar agent kunlik rejadan qolsa, keyingi kunga o'tadi
    YUKLANMA_ENABLED = True

    # ═══════════════════════════════════════════════════
    # Ma'lumotlar bazasi
    # ═══════════════════════════════════════════════════
    DB_PATH = "fmcg_kpi.db"

    # ═══════════════════════════════════════════════════
    # Hisobot vaqti (UTC vaqt!)
    # Toshkent UTC+5, shuning uchun:
    # Toshkent 18:00 = UTC 13:00
    # ═══════════════════════════════════════════════════
    EVENING_REPORT_HOUR_UTC = 13    # = 18:00 Toshkent
    EVENING_REPORT_MINUTE = 0
