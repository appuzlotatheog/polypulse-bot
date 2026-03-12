"""Order execution with real trading, position management, and risk controls."""

import asyncio
import csv
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from rarb.api.models import ArbitrageOpportunity, Market
from rarb.config import get_settings
from rarb.executor.async_clob import AsyncClobClient, create_async_clob_client
from rarb.executor.position_manager import PositionManager, PositionSide, get_position_manager
from rarb.risk.manager import RiskManager
from rarb.utils.logging import get_logger

log = get_logger(__name__)


class ExecutionStatus:
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ExecutionResult:
    def __init__(
        self,
        status: str,
        expected_profit: Decimal,
        actual_profit: Decimal = Decimal("0"),
        order_id: Optional[str] = None,
        error: Optional[str] = None,
        position_id: Optional[str] = None,
    ):
        self.status = status
        self.expected_profit = expected_profit
        self.actual_profit = actual_profit
        self.order_id = order_id
        self.error = error
        self.position_id = position_id


class OrderExecutor:
    """
    Executes trades with real order placement, position tracking, and TP/SL.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[AsyncClobClient] = None
        self.position_manager = get_position_manager()
        self.risk_manager = RiskManager()
        self.log_file = "trades_performance.csv"
        self._init_log()
        self._filled_positions = {}

    def _init_log(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Timestamp",
                        "Market",
                        "Side",
                        "Size",
                        "Entry Price",
                        "Exit Price",
                        "Profit %",
                        "P&L ($)",
                        "Status",
                    ]
                )

    def _log_trade(
        self,
        market: str,
        side: str,
        size: float,
        entry: float,
        exit_price: float,
        profit_pct: float,
        pnl: float,
        status: str,
    ):
        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    datetime.now(timezone.utc).isoformat(),
                    market[:50],
                    side,
                    f"{size:.2f}",
                    f"${entry:.4f}",
                    f"${exit_price:.4f}",
                    f"{profit_pct * 100:.2f}%",
                    f"${pnl:.2f}",
                    status,
                ]
            )

    async def _ensure_client(self) -> Optional[AsyncClobClient]:
        """Ensure we have a client."""
        if self.client is None:
            self.client = await create_async_clob_client()
        return self.client

    async def execute(self, opportunity: ArbitrageOpportunity) -> ExecutionResult:
        """Execute an arbitrage opportunity with real orders."""
        if self.settings.dry_run:
            return await self._execute_dry_run(opportunity)
        
        return await self._execute_live(opportunity)

    async def _execute_dry_run(self, opportunity: ArbitrageOpportunity) -> ExecutionResult:
        """Simulate execution without real trading."""
        log.info(
            "DRY RUN: Executing arbitrage",
            market=opportunity.market.question[:40],
            profit_pct=f"{opportunity.profit_pct * 100:.2f}%",
            expected_profit=f"${float(opportunity.expected_profit):.2f}",
        )
        self._log_trade(
            opportunity.market.question,
            "ARB",
            float(opportunity.max_size or 0),
            float(opportunity.combined_cost or 0),
            1.0,
            opportunity.profit_pct,
            float(opportunity.expected_profit or 0),
            "DRY_RUN",
        )
        return ExecutionResult(
            status=ExecutionStatus.FILLED,
            expected_profit=opportunity.expected_profit or Decimal("0"),
        )

    async def _execute_live(self, opportunity: ArbitrageOpportunity) -> ExecutionResult:
        """Execute real arbitrage trade."""
        client = await self._ensure_client()
        if not client:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                expected_profit=opportunity.expected_profit or Decimal("0"),
                error="No client - check credentials",
            )
        
        try:
            token_id_yes = opportunity.market.yes_token.token_id
            token_id_no = opportunity.market.no_token.token_id
            
            size = min(
                float(opportunity.max_size or 0),
                float(opportunity.max_trade_size or 0),
                self.settings.max_position_size,
            )
            
            log.info(
                "Executing live arbitrage",
                market=opportunity.market.question[:40],
                yes_token=token_id_yes[:20],
                no_token=token_id_no[:20],
                yes_price=float(opportunity.yes_ask or 0),
                no_price=float(opportunity.no_ask or 0),
                size=size,
            )
            
            neg_risk_yes = await client.get_neg_risk(token_id_yes)
            neg_risk_no = await client.get_neg_risk(token_id_no)
            
            yes_response = await client.submit_order(
                token_id=token_id_yes,
                side="BUY",
                price=float(opportunity.yes_ask or 0),
                size=size,
                neg_risk=neg_risk_yes,
            )
            
            no_response = await client.submit_order(
                token_id=token_id_no,
                side="BUY",
                price=float(opportunity.no_ask or 0),
                size=size,
                neg_risk=neg_risk_no,
            )
            
            yes_order_id = yes_response.get("orderID")
            no_order_id = no_response.get("orderID")
            
            if not yes_order_id or not no_order_id:
                error = f"Yes: {yes_response.get('errorMsg', 'no order ID')}, No: {no_response.get('errorMsg', 'no order ID')}"
                log.error("Order submission failed", error=error)
                return ExecutionResult(
                    status=ExecutionStatus.REJECTED,
                    expected_profit=opportunity.expected_profit or Decimal("0"),
                    error=error,
                )
            
            log.info("Orders submitted", yes_order_id=yes_order_id, no_order_id=no_order_id)
            
            filled_yes = await self._wait_for_fill(client, yes_order_id, timeout=10)
            filled_no = await self._wait_for_fill(client, no_order_id, timeout=10)
            
            if not filled_yes or not filled_no:
                if filled_yes:
                    await client.cancel_order(yes_order_id)
                if filled_no:
                    await client.cancel_order(no_order_id)
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    expected_profit=opportunity.expected_profit or Decimal("0"),
                    error="Timeout waiting for fill",
                )
            
            self._log_trade(
                opportunity.market.question,
                "YES",
                size,
                float(opportunity.yes_ask or 0),
                float(filled_yes),
                0,
                0,
                "FILLED",
            )
            self._log_trade(
                opportunity.market.question,
                "NO",
                size,
                float(opportunity.no_ask or 0),
                float(filled_no),
                0,
                0,
                "FILLED",
            )
            
            return ExecutionResult(
                status=ExecutionStatus.FILLED,
                expected_profit=opportunity.expected_profit or Decimal("0"),
                actual_profit=opportunity.expected_profit or Decimal("0"),
                order_id=f"{yes_order_id}|{no_order_id}",
            )
            
        except Exception as e:
            log.error(f"Execution error: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                expected_profit=opportunity.expected_profit or Decimal("0"),
                error=str(e),
            )

    async def _wait_for_fill(
        self,
        client: AsyncClobClient,
        order_id: str,
        timeout: float = 10.0,
    ) -> Optional[Decimal]:
        """Wait for an order to be filled."""
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            try:
                order = await client.get_order(order_id)
                status = order.get("status", "").upper()
                
                if status == "FILLED":
                    avg_price = order.get("avgPrice", "0")
                    return Decimal(str(avg_price))
                elif status in ["CANCELLED", "EXPIRED", "REJECTED"]:
                    return None
                
                await asyncio.sleep(0.5)
            except Exception as e:
                log.debug(f"Fill check error: {e}")
                await asyncio.sleep(0.5)
        
        return None

    async def execute_with_signal(
        self,
        market: Market,
        side: str,
        price: Decimal,
        size: Decimal,
    ) -> ExecutionResult:
        """Execute a directional trade (for 5m signal strategies)."""
        if self.settings.dry_run:
            log.info(
                "DRY RUN: Signal trade",
                market=market.question[:40],
                side=side,
                size=float(size),
                price=float(price),
            )
            return ExecutionResult(
                status=ExecutionStatus.FILLED,
                expected_profit=Decimal("0"),
            )
        
        client = await self._ensure_client()
        if not client:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                expected_profit=Decimal("0"),
                error="No client",
            )
        
        try:
            token_id = market.yes_token.token_id if side.upper() == "YES" else market.no_token.token_id
            neg_risk = await client.get_neg_risk(token_id)
            
            response = await client.submit_order(
                token_id=token_id,
                side="BUY",
                price=float(price or 0),
                size=float(size or 0),
                neg_risk=neg_risk,
            )
            
            order_id = response.get("orderID")
            if not order_id:
                return ExecutionResult(
                    status=ExecutionStatus.REJECTED,
                    expected_profit=Decimal("0"),
                    error=response.get("errorMsg", "no order ID"),
                )
            
            filled_price = await self._wait_for_fill(client, order_id)
            if not filled_price:
                await client.cancel_order(order_id)
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    expected_profit=Decimal("0"),
                    error="Timeout",
                )
            
            position = await self.position_manager.open_position(
                market=market,
                side=PositionSide.YES if side.upper() == "YES" else PositionSide.NO,
                token_id=token_id,
                price=filled_price,
                size=Decimal(str(size)),
                order_id=order_id,
            )
            
            return ExecutionResult(
                status=ExecutionStatus.FILLED,
                expected_profit=Decimal("0"),
                order_id=order_id,
                position_id=position.id,
            )
            
        except Exception as e:
            log.error(f"Signal trade error: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                expected_profit=Decimal("0"),
                error=str(e),
            )

    async def close(self) -> None:
        """Close the executor."""
        if self.client:
            await self.client.close()
