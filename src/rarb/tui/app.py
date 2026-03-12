"""The Ultimate Institutional-Grade TUI for 7Flow AI Bot."""

import asyncio
import random
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any, Union

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import (
    Container, Grid, Horizontal, Vertical, ScrollableContainer, Center
)
from textual.widgets import (
    DataTable, Footer, Header, Label, Log, Static, TabbedContent, 
    TabPane, Sparkline, Digits, Pretty, ProgressBar, Button
)
from textual.reactive import reactive
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.console import RenderableType
from rich.align import Align

from rarb.bot import ArbitrageBot
from rarb.config import get_settings
from rarb.api.blockchain import BlockchainManager
from rarb.api.models import MarketSnapshot


class InstitutionalTile(Static):
    """Institutional-style bento tile with high-fidelity styling."""
    DEFAULT_CSS = """
    InstitutionalTile {
        background: #0f172a;
        border: solid #1e293b;
        padding: 1 2;
        margin: 0;
        height: auto;
    }
    InstitutionalTile:hover {
        border: solid #38bdf8;
        background: #1e293b;
    }
    """

class GlowingMetric(InstitutionalTile):
    """A metric tile that glows based on value shifts."""
    value = reactive("0.00")
    delta = reactive("+0.00%")
    trend = reactive(0) # 1: up, -1: down, 0: stable
    
    def __init__(self, title: str, unit: str = "", color: str = "cyan", id: str | None = None):
        super().__init__(id=id)
        self.title = title
        self.unit = unit
        self.color = color

    def render(self) -> RenderableType:
        t_color = "#10b981" if self.trend > 0 else "#f43f5e" if self.trend < 0 else "#94a3b8"
        sign = "▲" if self.trend > 0 else "▼" if self.trend < 0 else "●"
        
        return Text.assemble(
            (f"{self.title.upper()}\n", "bold #94a3b8"),
            (f"{self.value}", f"bold {self.color}"),
            (f" {self.unit}\n", "dim"),
            (f"{sign} {self.delta}", t_color)
        )


class GeopoliticalPulse(InstitutionalTile):
    """Visualizes the Global Geopolitical Risk Score."""
    risk_level = reactive(3) # 1-10
    verdict = reactive("STABLE")
    
    def render(self) -> RenderableType:
        colors = ["#10b981", "#10b981", "#10b981", "#f59e0b", "#f59e0b", "#ef4444", "#ef4444", "#7f1d1d", "#7f1d1d", "#450a0a"]
        meter = ""
        for i in range(10):
            char = "█" if i < self.risk_level else "░"
            meter += f"[{colors[i]}]{char}[/]"
            
        v_color = "#10b981" if self.risk_level < 4 else "#f59e0b" if self.risk_level < 7 else "#f43f5e"
        
        return Text.from_markup(
            f"[bold #94a3b8]GEOPOLITICAL PULSE[/]\n"
            f"{meter} [bold white]{self.risk_level}/10[/]\n"
            f"[bold {v_color}]VERDICT: {self.verdict}[/]"
        )


class IntelligenceFeed(InstitutionalTile):
    """A scrolling marquee-style feed for research findings."""
    news = reactive("Awaiting intelligence pulse from X and BrowserScout...")
    
    def render(self) -> RenderableType:
        return Panel(
            Text(self.news, style="italic white"),
            title="[bold magenta]📡 REAL-TIME INTELLIGENCE[/]",
            border_style="magenta",
            padding=(0, 1)
        )


class ActiveScoutTerminal(InstitutionalTile):
    """Shows what the AI scouts are currently investigating."""
    current_action = reactive("STANDBY")
    target = reactive("None")
    
    def render(self) -> RenderableType:
        icon = "🔍" if "RESEARCH" in self.current_action else "🐦" if "X" in self.current_action else "🌐" if "BROWSER" in self.current_action else "💤"
        
        return Text.assemble(
            ("AI SCOUT MISSION\n", "bold #94a3b8"),
            (f"{icon} {self.current_action}: ", "bold #38bdf8"),
            (f"{self.target[:35]}", "white italic")
        )


class InstitutionalTable(DataTable):
    """Styled DataTable for professional aesthetics."""
    DEFAULT_CSS = """
    InstitutionalTable {
        background: transparent;
        border: none;
        height: 1fr;
    }
    InstitutionalTable > .datatable--header {
        background: #1e293b;
        color: #94a3b8;
        text-style: bold;
    }
    InstitutionalTable > .datatable--cursor {
        background: #334155;
    }
    """

class PolypulseInstitutionalTUI(App):
    """The gold standard in trading bot interfaces."""

    TITLE = "7FLOW INSTITUTIONAL v2.0"
    SUB_TITLE = "7Flow Advanced Arbitrage Engine"

    CSS = """
    Screen { background: #020617; }

    #header {
        background: #0f172a;
        color: #38bdf8;
        text-style: bold;
        border-bottom: double #1e293b;
    }

    #main-grid {
        layout: grid;
        grid-size: 4 5;
        grid-gutter: 1;
        padding: 1;
        height: 100%;
    }

    GlowingMetric { height: 6; }
    GeopoliticalPulse { height: 6; }
    ActiveScoutTerminal { height: 6; }
    
    IntelligenceFeed {
        column-span: 4;
        height: 4;
    }

    #tabs-container {
        height: 1fr;
        margin: 0 1;
        background: #0f172a;
        border: solid #1e293b;
    }

    TabPane { padding: 0; }

    .status-running { color: #10b981; }
    .status-stopped { color: #f43f5e; }
    
    #engine-panel {
        column-span: 2;
        background: #0f172a;
        border: solid #1e293b;
        padding: 1 2;
        height: 6;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Exit"),
        Binding("s", "toggle_engine", "Engage/Disengage"),
        Binding("t", "switch_tab", "Cycle Tabs"),
        Binding("r", "research_now", "Manual Scout"),
        Binding("c", "clear", "Purge Logs"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(id="main-grid"):
            # Row 1: Key Performance Metrics
            yield GlowingMetric("Institutional Balance", "USDC", "#38bdf8", id="m-balance")
            yield GlowingMetric("Session Yield", "USD", "#10b981", id="m-pnl")
            yield GlowingMetric("Alpha Success", "%", "#f59e0b", id="m-winrate")
            yield GlowingMetric("Execution Velocity", "MS", "#818cf8", id="m-speed")
            
            # Row 2: Intelligence Layer
            yield GeopoliticalPulse(id="geo-pulse")
            yield ActiveScoutTerminal(id="scout-term")
            
            with Vertical(id="engine-panel"):
                yield Label("[bold]SYSTEM PROTOCOL:[/] [bold rose]DISENGAGED[/]", id="engine-label")
                yield ProgressBar(total=100, show_percentage=True, id="heartbeat")
            
            # Row 3: Research Marquee
            yield IntelligenceFeed(id="news-feed")

        with TabbedContent(id="tabs-container"):
            with TabPane("⚡ ALPHA STREAM", id="tab-flow"):
                yield InstitutionalTable(id="flow-table")
            with TabPane("📜 AUDIT LOG", id="tab-history"):
                yield InstitutionalTable(id="audit-table")
            with TabPane("🧠 INTEL CORE", id="tab-research"):
                yield Log(id="research-log")
            with TabPane("📡 SYSTEM", id="tab-sys"):
                yield Log(id="sys-log")

        yield Footer()

    def on_mount(self) -> None:
        # Table Schema
        flow = self.query_one("#flow-table", InstitutionalTable)
        flow.add_columns("MARKET OPPORTUNITY", "PROBABILITY", "YIELD %", "LIQUIDITY", "AI VERDICT")
        
        audit = self.query_one("#audit-table", InstitutionalTable)
        audit.add_columns("TIMESTAMP", "OP", "MARKET", "ENTRY", "P&L", "STATUS")
        
        # State Initialization
        self.bot_running = False
        self.bot_task = None
        self.total_pnl = Decimal("0")
        self.trades = 0
        self.wins = 0
        
        self.blockchain = BlockchainManager()
        self.log_sys("[bold cyan]CORE SYSTEMS ONLINE. READY FOR ENGAGEMENT.[/]")
        
        # Refresh loops
        self.set_interval(1.0, self.pulse_ui)
        self.set_interval(15.0, self.update_blockchain)

    def log_sys(self, msg: str):
        try:
            self.query_one("#sys-log", Log).write(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}")
        except: pass

    def update_scout_action(self, action: str, target: str):
        try:
            scout = self.query_one("#scout-term", ActiveScoutTerminal)
            scout.current_action = action
            scout.target = target
            if "X" in action or "BROWSER" in action or "RESEARCH" in action:
                self.log_research(f"{action}: {target}")
        except: pass

    def log_research(self, msg: str):
        try:
            self.query_one("#research-log", Log).write(f"[bold magenta][RESEARCH][/] {msg}")
        except: pass

    async def update_blockchain(self):
        try:
            bal = await asyncio.to_thread(self.blockchain.get_usdc_balance)
            self.query_one("#m-balance", GlowingMetric).value = f"{float(bal):,.2f}"
        except: pass

    def pulse_ui(self):
        if self.bot_running:
            hb = self.query_one("#heartbeat", ProgressBar)
            hb.advance(10)
            if hb.progress >= 100: hb.progress = 0
            
            # Random speed jitter for institutional feel
            self.query_one("#m-speed", GlowingMetric).value = str(random.randint(45, 120))

    async def action_toggle_engine(self):
        label = self.query_one("#engine-label", Label)
        scout = self.query_one("#scout-term", ActiveScoutTerminal)
        
        if self.bot_running:
            self.bot_running = False
            if self.bot_task: self.bot_task.cancel()
            label.update("[bold]SYSTEM PROTOCOL:[/] [bold #f43f5e]DISENGAGED[/]")
            scout.current_action = "STANDBY"
            self.log_sys("Disengagement sequence complete.")
        else:
            self.bot_running = True
            label.update("[bold]SYSTEM PROTOCOL:[/] [bold #10b981]ENGAGED[/]")
            scout.current_action = "INITIALIZING SCANNERS"
            self.bot_task = asyncio.create_task(self.run_engine())
            self.log_sys("All systems engaged. Hunting for alpha.")

    async def run_engine(self):
        settings = get_settings()
        try:
            def report_cb(action: str, target: str):
                self.call_from_thread(self.update_scout_action, action, target)

            async with ArbitrageBot(reporting_callback=report_cb) as bot:
                def cb(snap: MarketSnapshot):
                    self.call_from_thread(self.on_market_update, snap)
                bot.scanner.on_snapshot(cb)
                
                while self.bot_running:
                    self.query_one("#scout-term", ActiveScoutTerminal).current_action = "SCANNING POLYMARKET"
                    await bot.scanner.run_once()
                    
                    # AI Alpha Check
                    snaps = list(bot.scanner.state.snapshots.values())
                    if snaps:
                        self.query_one("#scout-term", ActiveScoutTerminal).current_action = "AI ANALYZING ALPHA"
                        alpha = await bot.analyzer.get_alpha_suggestion(snaps)
                        if alpha:
                            self.query_one("#news-feed", IntelligenceFeed).news = alpha
                            self.log_research(alpha)
                    
                    # Execution
                    self.query_one("#scout-term", ActiveScoutTerminal).current_action = "EVALUATING TRADES"
                    results = await bot.execute_opportunities()
                    for r in results:
                        self.call_from_thread(self.on_trade_complete, r)
                        
                    await asyncio.sleep(settings.poll_interval_seconds)
        except Exception as e:
            self.log_sys(f"[bold red]CRITICAL KERNEL PANIC:[/] {e}")

    def on_market_update(self, snap: MarketSnapshot):
        table = self.query_one("#flow-table", InstitutionalTable)
        yes = float(snap.yes_best_ask or 0)
        no = float(snap.no_best_ask or 0)
        combined = yes + no if yes and no else 0
        profit = (1 - combined) * 100 if combined else 0
        
        verdict = "💎 STRONGBUY" if profit > 1.0 else "✅ BUY" if profit > 0.5 else "⏳ HOLD"
        v_color = "#10b981" if profit > 0.5 else "#94a3b8"
        
        try:
            if table.row_count > 40: table.clear()
            table.add_row(
                snap.market.question[:45],
                f"${combined:.3f}",
                f"[bold emerald]{profit:+.2f}%[/]",
                f"${snap.market.liquidity:,.0f}",
                f"[bold {v_color}]{verdict}[/]",
                key=snap.market.id
            )
        except: pass

    def on_trade_complete(self, res: Any):
        self.trades += 1
        pnl = float(res.expected_profit)
        if pnl > 0: self.wins += 1
        self.total_pnl += Decimal(str(pnl))
        
        self.query_one("#m-pnl", GlowingMetric).value = f"${float(self.total_pnl):+.2f}"
        self.query_one("#m-winrate", GlowingMetric).value = f"{(self.wins/self.trades)*100:.1f}"
        self.query_one("#m-winrate", GlowingMetric).trend = 1 if pnl > 0 else -1
        
        audit = self.query_one("#audit-table", InstitutionalTable)
        try:
            audit.add_row(
                datetime.now(timezone.utc).strftime("%H:%M:%S"),
                "ARB", "Polymarket", "-", f"{pnl:+.2f}", str(res.status)
            )
        except: pass

    async def action_research_now(self):
        """Force manual AI deep research."""
        self.log_sys("Manual Intelligence Pulse Triggered.")
        self.query_one("#scout-term", ActiveScoutTerminal).current_action = "MANUAL BROWSER RESEARCH"
        await asyncio.sleep(2)
        self.query_one("#scout-term", ActiveScoutTerminal).current_action = "SCANNING X PULSE"

    async def action_switch_tab(self):
        tabs = self.query_one("#tabs-container", TabbedContent)
        all_tabs = ["tab-flow", "tab-history", "tab-research", "tab-sys"]
        cur = str(tabs.active)
        idx = (all_tabs.index(cur) + 1) % len(all_tabs)
        tabs.active = all_tabs[idx]

    async def action_clear(self):
        self.query_one("#sys-log", Log).clear()
        self.query_one("#research-log", Log).clear()


def run_tui():
    PolypulseInstitutionalTUI().run()


if __name__ == "__main__":
    run_tui()
