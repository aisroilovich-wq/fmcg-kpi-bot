# 🤖 FMCG KPI Telegram Bot

Multi-rol Telegram bot — agent, supervisor va ROP uchun kunlik savdo va KPI tizimi.

## 📋 Xususiyatlar

- **Agent**: kunlik savdo kiritish, o'z natijasini ko'rish
- **Supervisor/ROP**: jamoa hisoboti, bonus hisob-kitobi
- **Yuklanma (carryover)**: agar agent kunlik rejadan qolsa, keyingi kunga o'tadi
- **Avtomatik kechki hisobot**: har kuni 18:00 da (Toshkent vaqti)
- **SQLite**: barcha ma'lumotlar mahalliy bazada saqlanadi

## 🚀 O'rnatish

### 1. @BotFather dan token olish
1. Telegramda `@BotFather` ga yozing
2. `/newbot` → bot nomini bering → token oling

### 2. Fayl sozlash
`config.py` faylini oching va o'zgartiring:
```python
BOT_TOKEN = "7123456789:AAFxxxxxxxx"   # Siz olingan token
ROP_PASSWORD = "sizning_parolingiz"    # ROP uchun parol
```

### 3. Lokal ishga tushirish
```bash
cd fmcg_bot
pip install -r requirements.txt
python bot.py
```

### 4. Render.com (bepul, 24/7) ga joylash
1. [render.com](https://render.com) da ro'yxatdan o'ting
2. "New → Web Service" → GitHub repo ulang yoki fayllarni yuklang
3. **Environment Variables** qo'shing:
   - `BOT_TOKEN` = tokeningiz
   - `ROP_PASSWORD` = parolingiz
4. Deploy tugmachasini bosing

## 💬 Buyruqlar

### Agent
| Buyruq | Tavsif |
|--------|--------|
| `/savdo 3500000` | Bugungi savdo kiritish |
| `/bugun` | Bugungi natija |
| `/oy` | Oylik statistika |
| `/status` | To'liq holat |

### Supervisor / ROP
| Buyruq | Tavsif |
|--------|--------|
| `/jamoa` | Barcha agentlar holati |
| `/hisobot` | Bugungi to'liq hisobot |
| `/oy` | Oylik jamoa hisoboti |
| `/bonus` | Bonus hisob-kitobi |
| `/reja 1000000000` | Oylik reja o'rnatish (ROP) |
| `/agentlar` | Agent ro'yxati |

## 🔧 KPI Tizimi

Excel `FMCG_KPI_v2.xlsx` fayli bilan bir xil hisoblash:

```
Kunlik bonus 1: ≥ 800,000 so'm → 15,000 so'm
Kunlik bonus 2: ≥ 1,500,000 so'm → 30,000 so'm  
Oylik reja bonusi: 100%+ bajarilsa → 500,000 so'm
Fiksa maosh: 3,000,000 so'm

Yuklanma: agar kunlik reja bajarilmasa → qoldiq keyingi kunga qo'shiladi
```

`config.py` da barcha miqdorlarni o'zgartirishingiz mumkin.

## 📁 Fayl tuzilmasi

```
fmcg_bot/
├── bot.py          — Asosiy bot fayli
├── config.py       — Sozlamalar (TOKEN shu yerda!)
├── database.py     — SQLite baza
├── kpi_engine.py   — KPI hisoblash
├── reports.py      — Hisobot generatori
├── requirements.txt
└── render.yaml     — Render.com uchun
```
