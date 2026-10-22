"""
SQLite ma'lumotlar bazasi
"""

import sqlite3
from datetime import date, datetime
from typing import Optional, List, Dict
from config import Config


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DB_PATH
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Jadvallarni yaratish"""
        with self._conn() as conn:
            conn.executescript("""
                -- Foydalanuvchilar
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    name        TEXT NOT NULL,
                    role        TEXT NOT NULL CHECK(role IN ('agent','supervisor','rop')),
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active   INTEGER DEFAULT 1
                );

                -- Kunlik savdolar
                CREATE TABLE IF NOT EXISTS daily_sales (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    sale_date   DATE NOT NULL,
                    amount      INTEGER NOT NULL,
                    entered_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, sale_date),
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                );

                -- Oylik rejalar
                CREATE TABLE IF NOT EXISTS monthly_plans (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    year        INTEGER NOT NULL,
                    month       INTEGER NOT NULL,
                    total       INTEGER NOT NULL,
                    set_by      INTEGER,
                    set_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(year, month)
                );

                -- Spets zadachalar
                CREATE TABLE IF NOT EXISTS spets_zadacha (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER,
                    year        INTEGER NOT NULL,
                    month       INTEGER NOT NULL,
                    amount      INTEGER NOT NULL DEFAULT 0,
                    description TEXT,
                    set_by      INTEGER,
                    set_at      DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                -- Indekslar
                CREATE INDEX IF NOT EXISTS idx_sales_user_date
                    ON daily_sales(user_id, sale_date);
                CREATE INDEX IF NOT EXISTS idx_sales_date
                    ON daily_sales(sale_date);
            """)

    # ═══════════════════════════════════════════════════
    # Foydalanuvchilar
    # ═══════════════════════════════════════════════════

    def register_user(self, user_id: int, name: str, role: str):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO users(user_id, name, role)
                VALUES(?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name=excluded.name,
                    role=excluded.role,
                    is_active=1
            """, (user_id, name, role))

    def get_user(self, user_id: int) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id=? AND is_active=1",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_agents(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE role='agent' AND is_active=1 ORDER BY name"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_users_by_role(self, role: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE role=? AND is_active=1",
                (role,)
            ).fetchall()
            return [dict(r) for r in rows]

    def deactivate_user(self, user_id: int):
        with self._conn() as conn:
            conn.execute("UPDATE users SET is_active=0 WHERE user_id=?", (user_id,))

    # ═══════════════════════════════════════════════════
    # Kunlik savdolar
    # ═══════════════════════════════════════════════════

    def save_daily_sale(self, user_id: int, amount: int,
                        sale_date: date = None, update: bool = False):
        if sale_date is None:
            sale_date = date.today()

        with self._conn() as conn:
            if update:
                conn.execute("""
                    INSERT INTO daily_sales(user_id, sale_date, amount)
                    VALUES(?, ?, ?)
                    ON CONFLICT(user_id, sale_date) DO UPDATE SET
                        amount=excluded.amount,
                        updated_at=CURRENT_TIMESTAMP
                """, (user_id, sale_date.isoformat(), amount))
            else:
                conn.execute("""
                    INSERT INTO daily_sales(user_id, sale_date, amount)
                    VALUES(?, ?, ?)
                """, (user_id, sale_date.isoformat(), amount))

    def get_daily_sale(self, user_id: int, sale_date: date = None) -> Optional[Dict]:
        if sale_date is None:
            sale_date = date.today()

        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM daily_sales WHERE user_id=? AND sale_date=?",
                (user_id, sale_date.isoformat())
            ).fetchone()
            return dict(row) if row else None

    def get_monthly_sales(self, user_id: int, year: int, month: int) -> List[Dict]:
        """Oylik barcha savdolar (tartib bo'yicha)"""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM daily_sales
                WHERE user_id=?
                  AND strftime('%Y', sale_date) = ?
                  AND strftime('%m', sale_date) = ?
                ORDER BY sale_date
            """, (user_id, str(year), f"{month:02d}")).fetchall()
            return [dict(r) for r in rows]

    def get_today_all_sales(self, today: date = None) -> List[Dict]:
        """Bugun barcha agentlar savdolari"""
        if today is None:
            today = date.today()

        with self._conn() as conn:
            rows = conn.execute("""
                SELECT u.name, u.user_id, ds.amount
                FROM users u
                LEFT JOIN daily_sales ds
                    ON u.user_id = ds.user_id AND ds.sale_date = ?
                WHERE u.role = 'agent' AND u.is_active = 1
                ORDER BY COALESCE(ds.amount, 0) DESC
            """, (today.isoformat(),)).fetchall()
            return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════
    # Oylik rejalar
    # ═══════════════════════════════════════════════════

    def set_monthly_plan(self, year: int, month: int, total: int, set_by: int = None):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO monthly_plans(year, month, total, set_by)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(year, month) DO UPDATE SET
                    total=excluded.total,
                    set_by=excluded.set_by,
                    set_at=CURRENT_TIMESTAMP
            """, (year, month, total, set_by))

    def get_monthly_plan(self, year: int, month: int) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM monthly_plans WHERE year=? AND month=?",
                (year, month)
            ).fetchone()
            return dict(row) if row else None

    # ═══════════════════════════════════════════════════
    # Spets zadacha
    # ═══════════════════════════════════════════════════

    def get_spets_zadacha(self, user_id: int, year: int, month: int) -> int:
        with self._conn() as conn:
            row = conn.execute("""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM spets_zadacha
                WHERE (user_id=? OR user_id IS NULL)
                  AND year=? AND month=?
            """, (user_id, year, month)).fetchone()
            return row['total'] if row else 0

    def set_spets_zadacha(self, year: int, month: int, amount: int,
                          user_id: int = None, description: str = "",
                          set_by: int = None):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO spets_zadacha(user_id, year, month, amount, description, set_by)
                VALUES(?, ?, ?, ?, ?, ?)
            """, (user_id, year, month, amount, description, set_by))
