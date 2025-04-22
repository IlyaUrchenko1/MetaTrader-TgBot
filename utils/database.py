import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class Database:
    def __init__(self, db_name: str = "data/trading_bot.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    join_date TIMESTAMP,
                    referrer_id INTEGER,
                    successful_trades INTEGER DEFAULT 0,
                    failed_trades INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0.0,
                    referral_count INTEGER DEFAULT 0,
                    referral_earnings REAL DEFAULT 0.0,
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    symbol TEXT DEFAULT 'EURUSD',
                    lot REAL DEFAULT 0.1,
                    distance_pips INTEGER DEFAULT 15,
                    trailing_distance INTEGER DEFAULT 15,
                    max_drawdown_pct INTEGER DEFAULT 5,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_pairs (
                    pair_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    symbol TEXT,
                    buy_stop_ticket INTEGER,
                    sell_stop_ticket INTEGER,
                    buy_stop_price REAL,
                    sell_stop_price REAL,
                    lot REAL,
                    created_at TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    join_date TIMESTAMP,
                    PRIMARY KEY (referrer_id, referred_id),
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY (referred_id) REFERENCES users(user_id)
                )
            """)
            
            conn.commit()

    def add_user(self, user_id: int, username: str, full_name: str, referrer_id: Optional[int] = None) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                if cursor.fetchone():
                    return True
                
                cursor.execute(
                    "INSERT INTO users (user_id, username, full_name, join_date, referrer_id) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, full_name, datetime.now(), referrer_id)
                )
                
                default_settings = {
                    "symbol": "EURUSD",
                    "lot": 0.1,
                    "distance_pips": 15,
                    "trailing_distance": 15,
                    "max_drawdown_pct": 5
                }
                
                cursor.execute("""
                    INSERT INTO user_settings (
                        user_id, symbol, lot, distance_pips, trailing_distance, max_drawdown_pct
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    default_settings["symbol"],
                    default_settings["lot"],
                    default_settings["distance_pips"],
                    default_settings["trailing_distance"],
                    default_settings["max_drawdown_pct"]
                ))
                
                if referrer_id:
                    cursor.execute(
                        "INSERT INTO referrals (referrer_id, referred_id, join_date) VALUES (?, ?, ?)",
                        (referrer_id, user_id, datetime.now())
                    )
                    cursor.execute(
                        "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
                        (referrer_id,)
                    )
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при добавлении пользователя: {e}")
            return False

    def get_user_profile(self, user_id: int) -> Optional[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT u.*, us.*
                    FROM users u
                    LEFT JOIN user_settings us ON u.user_id = us.user_id
                    WHERE u.user_id = ?
                """, (user_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    "user_id": row[0],
                    "username": row[1],
                    "full_name": row[2],
                    "join_date": row[3],
                    "referrer_id": row[4],
                    "successful_trades": row[5],
                    "failed_trades": row[6],
                    "total_profit": row[7],
                    "referral_count": row[8],
                    "referral_earnings": row[9],
                    "settings": {
                        "symbol": row[11],
                        "lot": row[12],
                        "distance_pips": row[13],
                        "trailing_distance": row[14],
                        "max_drawdown_pct": row[15]
                    }
                }
        except Exception as e:
            print(f"Ошибка при получении профиля пользователя: {e}")
            return None

    def update_user_settings(self, user_id: int, settings: Dict) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                current_settings = self.get_user_profile(user_id)["settings"]
                if not current_settings:
                    return False
                
                updated_settings = {**current_settings, **settings}
                
                cursor.execute("""
                    UPDATE user_settings
                    SET symbol = ?,
                        lot = ?,
                        distance_pips = ?,
                        trailing_distance = ?,
                        max_drawdown_pct = ?
                    WHERE user_id = ?
                """, (
                    updated_settings["symbol"],
                    updated_settings["lot"],
                    updated_settings["distance_pips"],
                    updated_settings["trailing_distance"],
                    updated_settings["max_drawdown_pct"],
                    user_id
                ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при обновлении настроек пользователя: {e}")
            return False

    def get_referral_stats(self, user_id: int) -> Dict:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(*) FROM referrals WHERE referrer_id = ?
                """, (user_id,))
                total_referrals = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(DISTINCT r.referred_id)
                    FROM referrals r
                    JOIN user_settings us ON r.referred_id = us.user_id
                    WHERE r.referrer_id = ?
                """, (user_id,))
                active_referrals = cursor.fetchone()[0]
                
                return {
                    "total_referrals": total_referrals,
                    "active_referrals": active_referrals
                }
        except Exception as e:
            print(f"Ошибка при получении статистики рефералов: {e}")
            return {"total_referrals": 0, "active_referrals": 0}

    def update_user_stats(self, user_id: int, successful: bool) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if successful:
                    cursor.execute("""
                        UPDATE users 
                        SET successful_trades = successful_trades + 1
                        WHERE user_id = ?
                    """, (user_id,))
                else:
                    cursor.execute("""
                        UPDATE users 
                        SET failed_trades = failed_trades + 1
                        WHERE user_id = ?
                    """, (user_id,))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при обновлении статистики пользователя: {e}")
            return False

    def add_order_pair(self, user_id: int, symbol: str, buy_stop_ticket: int, sell_stop_ticket: int, 
                      buy_stop_price: float, sell_stop_price: float, lot: float) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO order_pairs (
                        user_id, symbol, buy_stop_ticket, sell_stop_ticket,
                        buy_stop_price, sell_stop_price, lot, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, symbol, buy_stop_ticket, sell_stop_ticket,
                    buy_stop_price, sell_stop_price, lot, datetime.now()
                ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при добавлении пары ордеров: {e}")
            return False

    def get_active_order_pairs(self, user_id: int, symbol: str) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM order_pairs 
                    WHERE user_id = ? AND symbol = ? AND status = 'active'
                    ORDER BY created_at DESC
                """, (user_id, symbol))
                
                pairs = []
                for row in cursor.fetchall():
                    pairs.append({
                        "pair_id": row[0],
                        "user_id": row[1],
                        "symbol": row[2],
                        "buy_stop_ticket": row[3],
                        "sell_stop_ticket": row[4],
                        "buy_stop_price": row[5],
                        "sell_stop_price": row[6],
                        "lot": row[7],
                        "created_at": row[8],
                        "status": row[9]
                    })
                
                return pairs
        except Exception as e:
            print(f"Ошибка при получении пар ордеров: {e}")
            return []

    def update_order_pair_status(self, pair_id: int, status: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE order_pairs 
                    SET status = ?
                    WHERE pair_id = ?
                """, (status, pair_id))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при обновлении статуса пары ордеров: {e}")
            return False

    def get_order_pair(self, pair_id: int) -> Optional[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM order_pairs WHERE pair_id = ?",
                    (pair_id,)
                )
                result = cursor.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            print(f"Error getting order pair: {e}")
            return None 