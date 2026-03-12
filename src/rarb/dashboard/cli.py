"""Rich dashboard for the trading bot."""

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from threading import Thread
from typing import Optional

from rich import box
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text
from rich.style import Style
from rich.color import Color

from rarb.config import get_settings
from rarb.data.repositories import TradeRepository, AlertRepository, StatsRepository, PositionRepository
from rarb.utils.logging import get_logger

log = get_logger(__name__)

console = Console()


@dataclass
class DashboardState:
    """Current state for the dashboard."""
    # Balance
    usdc_balance: float = 0.0
    positions_value: float = 0.0
    
    # P&L
    total_pnl: float = 0.0
    today's_pnl: float = 0.0
    win_rate: float = 0.0
    
    # Trading stats
    total_trades: int = 0
    buys_today: int = 0
    sells_today: int = 0
    total_volume: float = 0.0
    
    # Scanner stats
    markets_tracked: int = 0
    opportunities_found: int = 0
    arbitrage_alerts: int = 0
    
    # Active positions
    open_positions: list = field(default_factory=list)
    
    # Recent alerts
    recent_alerts: list = field(default_factory=list)
    
    # Status
    mode: str = "DRY RUN"
    status: str = "Running"
    last_update: str = ""
    
    # Arbitrage opportunities
    current_opportunities: list = field(default_factory=list)


class Dashboard:
    """Rich-based dashboard for the bot."""
    
    def __init__(self):
        self.settings = get_settings()
        self.state = DashboardState()
        self.state.mode = "DRY RUN" if self.settings.dry_run else "LIVE TRADING"
        self._running = False
        self._update_thread: Optional[Thread] = None
        self.console = Console()
        
    def _create_balance_panel(self) -> Panel:
        """Create the balance panel."""
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Label", style="cyan bold")
        table.add_column("Value", justify="right", style="green bold")
        
        table.add_row("USDC Balance", f"${self.state.usdc_balance:,.2f}")
        table.add_row("Positions Value", f"${self.state.positions_value:,.2f}")
        table.add_row("", "")
        table.add_row("[bold]Total[/bold]", f"[bold]${self.state.usdc_balance + self.state.positions_value:,.2f}[/bold]")
        
        return Panel(
            table,
            title="💰 Balance",
            border_style="green",
            box=box.ROUNDED,
        )
    
    def _create_pnl_panel(self) -> Panel:
        """Create the P&L panel."""
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Label", style="cyan bold")
        table.add_column("Value", justify="right")
        
        pnl_color = "green" if self.state.total_pnl >= 0 else "red"
        today_color = "green" if self.state.today's_pnl >= 0 else "red"
        
        table.add_row("Total P&L", f"[{pnl_color}]${self.state.total_pnl:+,.2f}[/{pnl_color}]")
        table.add_row("Today's P&L", f"[{today_color}]${self.state.today's_pnl:+,.2f}[/{today_color}]")
        table.add_row("Win Rate", f"{self.state.win_rate:.1f}%")
        
        return Panel(
            table,
            title="📈 Profit & Loss",
            border_style="blue",
            box=box.ROUNDED,
        )
    
    def _create_trading_panel(self) -> Panel:
        """Create the trading stats panel."""
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Label", style="cyan bold")
        table.add_column("Value", justify="right")
        
        table.add_row("Total Trades", str(self.state.total_trades))
        table.add_row("Buys Today", f"🔵 {self.state.buys_today}")
        table.add_row("Sells Today", f"🔴 {self.state.sells_today}")
        table.add_row("Volume", f"${self.state.total_volume:,.2f}")
        
        return Panel(
            table,
            title="📊 Trading Activity",
            border_style="yellow",
            box=box.ROUNDED,
        )
    
    def _create_scanner_panel(self) -> Panel:
        """Create the scanner stats panel."""
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Label", style="cyan bold")
        table.add_column("Value", justify="right")
        
        table.add_row("Markets Tracked", str(self.state.markets_tracked))
        table.add_row("Opportunities", str(self.state.opportunities_found))
        table.add_row("Arbitrage Alerts", str(self.state.arbitrage_alerts))
        
        return Panel(
            table,
            title="🔍 Scanner",
            border_style="magenta",
            box=box.ROUNDED,
        )
    
    def _create_positions_panel(self) -> Panel:
        """Create the positions panel."""
        if not self.state.open_positions:
            return Panel(
                Text("No open positions", style="dim italic"),
                title="💼 Positions",
                border_style="cyan",
                box=box.ROUNDED,
            )
        
        table = Table(box=None, show_header=True, padding=(0, 1))
        table.add_column("Market", style="cyan", max_width=30)
        table.add_column("Side", justify="center")
        table.add_column("Size", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("P&L", justify="right")
        
        for pos in self.state.open_positions[:8]:
            side_color = "green" if pos.get("side") == "YES" else "red"
            pnl = pos.get("pnl", 0)
            pnl_color = "green" if pnl >= 0 else "red"
            
            table.add_row(
                pos.get("market", "")[:30],
                f"[{side_color}]{pos.get('side', '')}[/{side_color}]",
                f"${pos.get('size', 0):.2f}",
                f"${pos.get('entry_price', 0):.3f}",
                f"[{pnl_color}]${pnl:+,.2f}[/{pnl_color}]",
            )
        
        return Panel(
            table,
            title="💼 Positions",
            border_style="cyan",
            box=box.ROUNDED,
        )
    
    def _create_opportunities_panel(self) -> Panel:
        """Create the arbitrage opportunities panel."""
        if not self.state.current_opportunities:
            return Panel(
                Text("Scanning for opportunities...", style="dim italic"),
                title="⚡ Arbitrage Opportunities",
                border_style="red",
                box=box.ROUNDED,
            )
        
        table = Table(box=None, show_header=True, padding=(0, 1))
        table.add_column("Market", style="cyan", max_width=35)
        table.add_column("YES", justify="right")
        table.add_column("NO", justify="right")
        table.add_column("Profit", justify="right", style="green")
        
        for opp in self.state.current_opportunities[:5]:
            table.add_row(
                opp.get("market", "")[:35],
                f"${opp.get('yes_price', 0):.3f}",
                f"${opp.get('no_price', 0):.3f}",
                f"[green]+{opp.get('profit_pct', 0)*100:.2f}%[/green]",
            )
        
        return Panel(
            table,
            title="⚡ Top Opportunities",
            border_style="red",
            box=box.ROUNDED,
        )
    
    def _create_status_bar(self) -> Table:
        """Create the status bar."""
        status_color = "yellow" if self.state.mode == "DRY RUN" else "red"
        
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Mode", style=status_color)
        table.add_column("Status", style="green")
        table.add_column("Last Update", style="dim")
        
        table.add_row(
            f"⚙ {self.state.mode}",
            f"✓ {self.state.status}",
            self.state.last_update,
        )
        
        return table
    
    def _create_header(self) -> Panel:
        """Create the header panel."""
        title = Text("🤖 Polymarket Trading Bot", style="bold cyan", justify="center")
        
        subtitle = Text()
        subtitle.append("Real-time Arbitrage & Signal Trading", style="dim")
        
        return Panel(
            Group(title, "", subtitle),
            style=Style(bgcolor="black"),
            box=box.ROUNDED,
            border_style="",
            padding=(0, 0),
        )
    
    def _build_layout(self) -> Layout:
        """Build the full dashboard layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(self._create_header(), size=4),
            Layout(name="main"),
        )
        
        layout["main"].split_row(
            Layout(self._create_balance_panel()),
            Layout(self._create_pnl_panel()),
            Layout(self._create_trading_panel()),
            Layout(self._create_scanner_panel()),
        )
        
        layout["main"].split_column(
            Layout(self._create_opportunities_panel()),
            Layout(self._create_positions_panel()),
        )
        
        return layout
    
    async def _fetch_data(self):
        """Fetch data from various sources."""
        try:
            # Get trade stats
            pnl_summary = await TradeRepository.get_pnl_summary()
            self.state.total_pnl = pnl_summary.get("total_pnl", 0)
            self.state.total_trades = pnl_summary.get("trade_count", 0)
            
            # Get open positions
            positions = await PositionRepository.get_open_positions()
            self.state.open_positions = positions
            
            # Calculate positions value
            self.state.positions_value = sum(
                float(p.get("size", 0)) * float(p.get("entry_price", 0))
                for p in positions
            )
            
            # Get scanner stats (from stats table)
            # This would need to be implemented
            
            self.state.last_update = datetime.now().strftime("%H:%M:%S")
            
        except Exception as e:
            log.debug(f"Dashboard data fetch error: {e}")
    
    def _update_loop(self):
        """Background loop to update data."""
        while self._running:
            try:
                asyncio.run(self._fetch_data())
            except Exception as e:
                log.debug(f"Update loop error: {e}")
            time.sleep(2)
    
    def start(self):
        """Start the dashboard."""
        self._running = True
        
        # Start background update thread
        self._update_thread = Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        
        # Initial data fetch
        asyncio.run(self._fetch_data())
        
        try:
            with Live(self._build_layout(), console=self.console, refresh_per_second=2, screen=True) as live:
                while self._running:
                    live.update(self._build_layout())
                    time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the dashboard."""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=1)


class SimpleDashboard:
    """Simple console dashboard that prints status updates."""
    
    def __init__(self):
        self.settings = get_settings()
        self.console = Console()
        self._running = False
        
    def print_header(self):
        """Print the header."""
        self.console.clear()
        self.console.print()
        self.console.print("╔════════════════════════════════════════════════════════════════════════════╗", style="bold cyan")
        self.console.print("║          🤖 POLYMARKET TRADING BOT - Real-time Dashboard                  ║", style="bold cyan")
        self.console.print("╚════════════════════════════════════════════════════════════════════════════╝", style="bold cyan")
        self.console.print()
        
    def print_status(self, stats: dict):
        """Print current status."""
        # Top row - key metrics
        self.console.print("┌──────────────────────────────────────────────────────────────────────────────────┐")
        
        mode = "🔴 LIVE" if not self.settings.dry_run else "🟡 DRY RUN"
        status = stats.get("status", "Running")
        
        # Balance section
        balance = stats.get("balance", 0)
        pnl = stats.get("pnl", 0)
        pnl_color = "green" if pnl >= 0 else "red"
        
        self.console.print(f"│  💰 Balance: ${balance:,.2f}  │  📈 P&L: [{pnl_color}]${pnl:+,.2f}[/{pnl_color}]  │  {mode}  │  Status: {status:<10} │")
        
        self.console.print("├──────────────────────────────────────────────────────────────────────────────────┤")
        
        # Trading stats
        trades = stats.get("trades", 0)
        buys = stats.get("buys", 0)
        sells = stats.get("sells", 0)
        volume = stats.get("volume", 0)
        
        self.console.print(f"│  📊 Trades: {trades:<5}  │  🔵 Buys: {buys:<3}  │  🔴 Sells: {sells:<3}  │  💵 Volume: ${volume:,.0f}          │")
        
        self.console.print("├──────────────────────────────────────────────────────────────────────────────────┤")
        
        # Scanner stats
        markets = stats.get("markets", 0)
        opportunities = stats.get("opportunities", 0)
        alerts = stats.get("alerts", 0)
        
        self.console.print(f"│  🔍 Markets: {markets:<4}  │  ⚡ Opportunities: {opportunities:<3}  │  🚨 Alerts: {alerts:<3}                    │")
        
        self.console.print("└──────────────────────────────────────────────────────────────────────────────────┘")
        self.console.print()
        
    def print_opportunities(self, opportunities: list):
        """Print current opportunities."""
        if not opportunities:
            self.console.print("  ⚡ Scanning for opportunities...", style="dim")
            return
            
        self.console.print("  ⚡ Top Opportunities:", style="bold yellow")
        
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Market", style="cyan", max_width=40)
        table.add_column("YES", justify="right")
        table.add_column("NO", justify="right")
        table.add_column("Profit", justify="right", style="green")
        
        for opp in opportunities[:5]:
            table.add_row(
                opp.get("market", "")[:40],
                f"${opp.get('yes_price', 0):.3f}",
                f"${opp.get('no_price', 0):.3f}",
                f"+{opp.get('profit_pct', 0)*100:.2f}%",
            )
        
        self.console.print(table)
        
    def print_positions(self, positions: list):
        """Print open positions."""
        if not positions:
            self.console.print("  💼 No open positions", style="dim")
            return
            
        self.console.print("  💼 Open Positions:", style="bold cyan")
        
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Market", style="cyan", max_width=30)
        table.add_column("Side", justify="center")
        table.add_column("Size", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("P&L", justify="right")
        
        for pos in positions[:5]:
            side = pos.get("side", "")
            side_color = "green" if side == "YES" else "red"
            pnl = pos.get("pnl", 0)
            pnl_color = "green" if pnl >= 0 else "red"
            
            table.add_row(
                pos.get("market", "")[:30],
                f"[{side_color}]{side}[/{side_color}]",
                f"${pos.get('size', 0):.2f}",
                f"${pos.get('entry_price', 0):.3f}",
                f"[{pnl_color}]${pnl:+,.2f}[/{pnl_color}]",
            )
        
        self.console.print(table)
        
    def run(self, stats_callback=None, opportunities_callback=None, positions_callback=None):
        """Run the dashboard."""
        self._running = True
        self.print_header()
        
        try:
            while self._running:
                stats = {}
                opportunities = []
                positions = []
                
                # Get data from callbacks
                if stats_callback:
                    stats = stats_callback()
                if opportunities_callback:
                    opportunities = opportunities_callback()
                if positions_callback:
                    positions = positions_callback()
                
                self.print_status(stats)
                self.print_opportunities(opportunities)
                self.console.print()
                self.print_positions(positions)
                self.console.print()
                
                # Footer
                self.console.print(f"  Last updated: {datetime.now().strftime('%H:%M:%S')}  │  Press Ctrl+C to stop", style="dim")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            self._running = False
            self.console.print("\n\n  👋 Dashboard stopped\n", style="bold yellow")
    
    def stop(self):
        """Stop the dashboard."""
        self._running = False


def create_dashboard() -> SimpleDashboard:
    """Create a dashboard instance."""
    return SimpleDashboard()
