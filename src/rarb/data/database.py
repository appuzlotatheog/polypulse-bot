"""Database management with SQLite for positions and trades."""

import aiosqlite
import asyncio
from pathlib import Path
from typing import Optional

from rarb.utils.logging import get_logger

log = get_logger(__name__)

DB_PATH = "rarb.db"


async def init_async_db() -> aiosqlite.Connection:
    """Initialize SQLite database with tables."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            market_id TEXT NOT NULL,
            market_question TEXT NOT NULL,
            side TEXT NOT NULL,
            token_id TEXT NOT NULL,
            entry_price REAL NOT NULL,
            size REAL NOT NULL,
            size_remaining REAL NOT NULL,
            entry_time TEXT NOT NULL,
            status TEXT NOT NULL,
            stop_loss_price REAL,
            take_profit_price REAL,
            realized_pnl REAL DEFAULT 0,
            hedge_position_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id TEXT,
            market_question TEXT NOT NULL,
            side TEXT NOT NULL,
            size REAL NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL,
            pnl REAL,
            status TEXT NOT NULL,
            order_id TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (position_id) REFERENCES positions (id)
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market TEXT NOT NULL,
            yes_ask REAL NOT NULL,
            no_ask REAL NOT NULL,
            combined REAL NOT NULL,
            profit REAL NOT NULL,
            timestamp TEXT NOT NULL,
            platform TEXT DEFAULT 'polymarket',
            days_until_resolution INTEGER,
            resolution_date TEXT,
            first_seen TEXT,
            duration_secs REAL,
            executed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            markets INTEGER DEFAULT 0,
            price_updates INTEGER DEFAULT 0,
            arbitrage_alerts INTEGER DEFAULT 0,
            ws_connected INTEGER DEFAULT 0,
            ws_connections TEXT DEFAULT '',
            subscribed_tokens INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_positions_market ON positions(market_id)
    """)
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)
    """)
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_position ON trades(position_id)
    """)
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_market ON alerts(market)
    """)
    
    await db.commit()
    log.info("Database initialized", path=DB_PATH)
    return db


async def get_db() -> Optional[aiosqlite.Connection]:
    """Get database connection."""
    try:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        return db
    except Exception as e:
        log.error(f"Failed to connect to database: {e}")
        return None
