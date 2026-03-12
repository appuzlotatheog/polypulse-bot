"""Data access repositories with SQLite."""

from datetime import datetime
from typing import Optional

from rarb.data.database import get_db
from rarb.utils.logging import get_logger

log = get_logger(__name__)


class PositionRepository:
    """Repository for position data."""
    
    @staticmethod
    async def insert(
        position_id: str,
        market_id: str,
        market_question: str,
        side: str,
        token_id: str,
        entry_price: float,
        size: float,
        size_remaining: float,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> bool:
        db = await get_db()
        if not db:
            return False
        try:
            await db.execute(
                """INSERT INTO positions 
                   (id, market_id, market_question, side, token_id, entry_price, size, 
                    size_remaining, status, stop_loss_price, take_profit_price)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)""",
                (position_id, market_id, market_question, side, token_id, entry_price,
                 size, size_remaining, stop_loss_price, take_profit_price)
            )
            await db.commit()
            return True
        except Exception as e:
            log.error(f"Failed to insert position: {e}")
            return False
        finally:
            await db.close()
    
    @staticmethod
    async def update_status(
        position_id: str,
        status: str,
        size_remaining: Optional[float] = None,
        realized_pnl: Optional[float] = None,
    ) -> bool:
        db = await get_db()
        if not db:
            return False
        try:
            updates = ["status = ?", "updated_at = ?"]
            values = [status, datetime.now(timezone.utc).isoformat()]
            
            if size_remaining is not None:
                updates.append("size_remaining = ?")
                values.append(size_remaining)
            if realized_pnl is not None:
                updates.append("realized_pnl = ?")
                values.append(realized_pnl)
            
            values.append(position_id)
            
            await db.execute(
                f"UPDATE positions SET {', '.join(updates)} WHERE id = ?",
                values
            )
            await db.commit()
            return True
        except Exception as e:
            log.error(f"Failed to update position: {e}")
            return False
        finally:
            await db.close()
    
    @staticmethod
    async def get_open_positions() -> list:
        db = await get_db()
        if not db:
            return []
        try:
            cursor = await db.execute(
                "SELECT * FROM positions WHERE status = 'OPEN'"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            log.error(f"Failed to get positions: {e}")
            return []
        finally:
            await db.close()
    
    @staticmethod
    async def get_by_market(market_id: str) -> list:
        db = await get_db()
        if not db:
            return []
        try:
            cursor = await db.execute(
                "SELECT * FROM positions WHERE market_id = ?",
                (market_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            log.error(f"Failed to get positions by market: {e}")
            return []
        finally:
            await db.close()


class TradeRepository:
    """Repository for trade data."""
    
    @staticmethod
    async def insert(
        position_id: Optional[str],
        market_question: str,
        side: str,
        size: float,
        entry_price: float,
        exit_price: Optional[float],
        pnl: Optional[float],
        status: str,
        order_id: Optional[str] = None,
    ) -> bool:
        db = await get_db()
        if not db:
            return False
        try:
            await db.execute(
                """INSERT INTO trades 
                   (position_id, market_question, side, size, entry_price, exit_price, pnl, status, order_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (position_id, market_question, side, size, entry_price, exit_price, pnl, status, order_id)
            )
            await db.commit()
            return True
        except Exception as e:
            log.error(f"Failed to insert trade: {e}")
            return False
        finally:
            await db.close()
    
    @staticmethod
    async def get_recent(limit: int = 50) -> list:
        db = await get_db()
        if not db:
            return []
        try:
            cursor = await db.execute(
                "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            log.error(f"Failed to get trades: {e}")
            return []
        finally:
            await db.close()
    
    @staticmethod
    async def get_pnl_summary() -> dict:
        db = await get_db()
        if not db:
            return {"total_pnl": 0, "trade_count": 0}
        try:
            cursor = await db.execute(
                "SELECT SUM(pnl) as total_pnl, COUNT(*) as count FROM trades WHERE pnl IS NOT NULL"
            )
            row = await cursor.fetchone()
            return {"total_pnl": row["total_pnl"] or 0, "trade_count": row["count"] or 0}
        except Exception as e:
            log.error(f"Failed to get PnL summary: {e}")
            return {"total_pnl": 0, "trade_count": 0}
        finally:
            await db.close()


class AlertRepository:
    """Repository for arbitrage alerts."""
    
    @staticmethod
    async def insert(
        market: str,
        yes_ask: float,
        no_ask: float,
        combined: float,
        profit: float,
        timestamp: str,
        platform: str = "polymarket",
        days_until_resolution: Optional[int] = None,
        resolution_date: Optional[str] = None,
        first_seen: Optional[str] = None,
        duration_secs: Optional[float] = None,
    ) -> bool:
        db = await get_db()
        if not db:
            return False
        try:
            await db.execute(
                """INSERT INTO alerts 
                   (market, yes_ask, no_ask, combined, profit, timestamp, platform,
                    days_until_resolution, resolution_date, first_seen, duration_secs)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (market, yes_ask, no_ask, combined, profit, timestamp, platform,
                 days_until_resolution, resolution_date, first_seen, duration_secs)
            )
            await db.commit()
            return True
        except Exception as e:
            log.error(f"Failed to insert alert: {e}")
            return False
        finally:
            await db.close()
    
    @staticmethod
    async def update_duration(market: str, duration_secs: float) -> bool:
        db = await get_db()
        if not db:
            return False
        try:
            await db.execute(
                "UPDATE alerts SET duration_secs = ? WHERE market = ? AND duration_secs IS NULL",
                (round(duration_secs, 1), market)
            )
            await db.commit()
            return True
        except Exception as e:
            log.error(f"Failed to update alert duration: {e}")
            return False
        finally:
            await db.close()
    
    @staticmethod
    async def mark_executed(market: str) -> bool:
        db = await get_db()
        if not db:
            return False
        try:
            await db.execute(
                "UPDATE alerts SET executed = 1 WHERE market = ? ORDER BY id DESC LIMIT 1",
                (market,)
            )
            await db.commit()
            return True
        except Exception as e:
            log.error(f"Failed to mark alert executed: {e}")
            return False
        finally:
            await db.close()


class StatsRepository:
    """Repository for scanner stats."""
    
    @staticmethod
    async def update(
        markets: int = 0,
        price_updates: int = 0,
        arbitrage_alerts: int = 0,
        ws_connected: bool = False,
        ws_connections: str = "",
        subscribed_tokens: int = 0,
    ) -> bool:
        db = await get_db()
        if not db:
            return False
        try:
            await db.execute(
                """INSERT OR REPLACE INTO stats 
                   (id, markets, price_updates, arbitrage_alerts, ws_connected, 
                    ws_connections, subscribed_tokens, updated_at)
                   VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
                (markets, price_updates, arbitrage_alerts, int(ws_connected),
                 ws_connections, subscribed_tokens, datetime.now(timezone.utc).isoformat())
            )
            await db.commit()
            return True
        except Exception as e:
            log.error(f"Failed to update stats: {e}")
            return False
        finally:
            await db.close()


from datetime import timezone
