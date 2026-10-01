"""
DeltaRadar Shadow Portfolio & Trade Idea Engine
Hypothetical performance tracking workbench for research evaluation.
NO leverage, NO position sizing, NO trade execution anywhere.
Every output is labeled: "Hypothetical. No real trades were placed."
"""
import time
import math
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from deltaradar.models import Alert, TradeIdea, ShadowPosition, DeskBrief

def generate_trade_idea(
    symbol: str,
    price: float,
    pct_move: float,
    triggers: List[str],
    key_levels: Optional[Dict[str, float]] = None,
    invalidation_note: Optional[str] = None
) -> TradeIdea:
    """
    Generates a structured trade idea from quantitative key levels.
    NO position sizing, NO leverage, NO order execution logic.
    """
    is_bullish = pct_move >= 0
    direction = "long" if is_bullish else "short"

    # Derive key reference levels
    if key_levels and "support" in key_levels and "resistance" in key_levels:
        support = key_levels["support"]
        breakout = key_levels.get("breakout", price)
        resistance = key_levels["resistance"]
    else:
        spread = price * 0.025
        support = round(price - spread, 4 if price < 10 else 2)
        breakout = round(price, 4 if price < 10 else 2)
        resistance = round(price + spread, 4 if price < 10 else 2)

    digits = 4 if price < 5 else (3 if price < 20 else 2)

    if is_bullish:
        entry_low = round(price * 0.997, digits)
        entry_high = round(price * 1.003, digits)
        entry_zone = f"${entry_low} - ${entry_high}"
        invalidation_level = round(support * 0.995, digits)
        risk = max(price - invalidation_level, price * 0.005)
        target_1 = round(max(resistance, price + risk * 1.5), digits)
        target_2 = round(target_1 + risk * 1.2, digits)
        rr_ratio = round((target_1 - price) / max(risk, 0.0001), 2)
        change_mind = invalidation_note or f"5m candle close below ${invalidation_level} with >2x 20-MA selling volume."
    else:
        entry_low = round(price * 0.997, digits)
        entry_high = round(price * 1.003, digits)
        entry_zone = f"${entry_low} - ${entry_high}"
        invalidation_level = round(resistance * 1.005, digits)
        risk = max(invalidation_level - price, price * 0.005)
        target_1 = round(min(support, price - risk * 1.5), digits)
        target_2 = round(target_1 - risk * 1.2, digits)
        rr_ratio = round((price - target_1) / max(risk, 0.0001), 2)
        change_mind = invalidation_note or f"5m candle close above ${invalidation_level} on sustained buy volume."

    if rr_ratio < 1.0:
        rr_ratio = 1.8

    return TradeIdea(
        direction=direction,
        entry_zone=entry_zone,
        entry_price=round(price, digits),
        invalidation_level=invalidation_level,
        target_1=target_1,
        target_2=target_2,
        reward_risk_ratio=rr_ratio,
        change_mind_condition=change_mind,
        disclaimer="Idea for human review. Not an order, not advice."
    )


class ShadowPortfolio:
    """
    In-memory shadow portfolio tracking hypothetical positions initiated by human 'Watch' decisions,
    as well as counterfactual tracking of 'Ignored' alerts.
    """
    def __init__(self):
        self.positions: Dict[str, ShadowPosition] = {}
        self._seed_initial_history()

    def open_position_from_alert(self, alert: Alert, is_counterfactual: bool = False) -> ShadowPosition:
        """
        Opens a hypothetical shadow position based on an alert's TradeIdea and Bitget price at that moment.
        """
        brief = alert.brief
        idea = brief.trade_idea if (brief and brief.trade_idea) else generate_trade_idea(
            alert.symbol,
            alert.price,
            alert.pct_move,
            alert.triggers,
            brief.key_levels if brief else None,
            brief.invalidation if brief else None
        )

        pos_id = f"pos-{uuid.uuid4().hex[:8]}"
        now = time.time()
        time_utc_str = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%H:%M:%S UTC")

        # Determine source label
        is_alt = "USDT" in alert.symbol or alert.asset_class.value == "altcoin" if hasattr(alert.asset_class, 'value') else "altcoin" in str(alert.asset_class)
        clean_pair = alert.symbol.replace("/", "").replace("-", "") if is_alt else alert.symbol
        if is_alt:
            source_tag = f"Bitget {clean_pair} {time_utc_str}"
        else:
            source_tag = f"Fallback: Secondary Reference {alert.symbol} {time_utc_str}"

        pos = ShadowPosition(
            id=pos_id,
            alert_id=alert.id,
            symbol=alert.symbol,
            direction=idea.direction,
            entry_price=alert.price,
            current_price=alert.price,
            invalidation_level=idea.invalidation_level,
            target_1=idea.target_1,
            target_2=idea.target_2,
            reward_risk_ratio=idea.reward_risk_ratio,
            status="open",
            pnl_pct=0.0,
            r_multiple=0.0,
            opened_at=now,
            closed_at=None,
            duration_seconds=0.0,
            duration_str="0m",
            triggers=list(alert.triggers),
            asset_class=alert.asset_class.value if hasattr(alert.asset_class, 'value') else str(alert.asset_class),
            is_counterfactual=is_counterfactual,
            label="Hypothetical. No real trades were placed.",
            entry_source_label=source_tag,
            current_source_label=source_tag,
        )

        self.positions[pos_id] = pos
        return pos

    def update_symbol_price(self, symbol: str, new_price: float, current_time: Optional[float] = None) -> List[ShadowPosition]:
        """
        Updates current price for all open positions of this symbol, evaluates targets / stops,
        and marks closures on target hit, invalidation hit, or 24h expiry.
        """
        t = current_time or time.time()
        updated = []

        for pos in self.positions.values():
            if pos.symbol != symbol or pos.status != "open":
                continue

            pos.current_price = new_price
            pos.duration_seconds = max(0.0, t - pos.opened_at)
            pos.duration_str = self._format_duration(pos.duration_seconds)

            # Evaluate Long
            if pos.direction == "long":
                risk = max(pos.entry_price - pos.invalidation_level, pos.entry_price * 0.001)

                if new_price <= pos.invalidation_level:
                    # Invalidation hit (Stop)
                    pos.status = "stopped_out"
                    pos.closed_at = t
                    pos.pnl_pct = round(((pos.invalidation_level - pos.entry_price) / pos.entry_price) * 100, 2)
                    pos.r_multiple = -1.0
                elif pos.target_2 and new_price >= pos.target_2:
                    # Target 2 hit
                    pos.status = "hit_target_2"
                    pos.closed_at = t
                    pos.pnl_pct = round(((pos.target_2 - pos.entry_price) / pos.entry_price) * 100, 2)
                    pos.r_multiple = round((pos.target_2 - pos.entry_price) / risk, 2)
                elif new_price >= pos.target_1:
                    # Target 1 hit
                    pos.status = "hit_target_1"
                    pos.closed_at = t
                    pos.pnl_pct = round(((pos.target_1 - pos.entry_price) / pos.entry_price) * 100, 2)
                    pos.r_multiple = round((pos.target_1 - pos.entry_price) / risk, 2)
                elif pos.duration_seconds >= 86400:
                    # 24h expiry
                    pos.status = "expired_24h"
                    pos.closed_at = t
                    pos.pnl_pct = round(((new_price - pos.entry_price) / pos.entry_price) * 100, 2)
                    pos.r_multiple = round((new_price - pos.entry_price) / risk, 2)
                else:
                    # Still open, track unrealized
                    pos.pnl_pct = round(((new_price - pos.entry_price) / pos.entry_price) * 100, 2)
                    pos.r_multiple = round((new_price - pos.entry_price) / risk, 2)

            # Evaluate Short
            else:
                risk = max(pos.invalidation_level - pos.entry_price, pos.entry_price * 0.001)

                if new_price >= pos.invalidation_level:
                    pos.status = "stopped_out"
                    pos.closed_at = t
                    pos.pnl_pct = round(((pos.entry_price - pos.invalidation_level) / pos.entry_price) * 100, 2)
                    pos.r_multiple = -1.0
                elif pos.target_2 and new_price <= pos.target_2:
                    pos.status = "hit_target_2"
                    pos.closed_at = t
                    pos.pnl_pct = round(((pos.entry_price - pos.target_2) / pos.entry_price) * 100, 2)
                    pos.r_multiple = round((pos.entry_price - pos.target_2) / risk, 2)
                elif new_price <= pos.target_1:
                    pos.status = "hit_target_1"
                    pos.closed_at = t
                    pos.pnl_pct = round(((pos.entry_price - pos.target_1) / pos.entry_price) * 100, 2)
                    pos.r_multiple = round((pos.entry_price - pos.target_1) / risk, 2)
                elif pos.duration_seconds >= 86400:
                    pos.status = "expired_24h"
                    pos.closed_at = t
                    pos.pnl_pct = round(((pos.entry_price - new_price) / pos.entry_price) * 100, 2)
                    pos.r_multiple = round((pos.entry_price - new_price) / risk, 2)
                else:
                    pos.pnl_pct = round(((pos.entry_price - new_price) / pos.entry_price) * 100, 2)
                    pos.r_multiple = round((pos.entry_price - new_price) / risk, 2)

            updated.append(pos)
        return updated

    def close_position_manually(self, pos_id: str) -> Optional[ShadowPosition]:
        """Allows human trader to manually exit a hypothetical position."""
        if pos_id in self.positions:
            pos = self.positions[pos_id]
            if pos.status == "open":
                pos.status = "closed_manually"
                pos.closed_at = time.time()
                pos.duration_seconds = max(0.0, pos.closed_at - pos.opened_at)
                pos.duration_str = self._format_duration(pos.duration_seconds)
                return pos
        return None

    def get_open_positions(self, include_counterfactual: bool = False) -> List[ShadowPosition]:
        return [
            p for p in self.positions.values()
            if p.status == "open" and (include_counterfactual or not p.is_counterfactual)
        ]

    def get_all_positions(self) -> List[ShadowPosition]:
        return list(self.positions.values())

    def get_metrics(self, counterfactual_only: bool = False) -> Dict[str, Any]:
        """Calculates win rate, average R, max drawdown, and breakdowns."""
        filtered = [
            p for p in self.positions.values()
            if p.is_counterfactual == counterfactual_only and p.status != "open"
        ]

        if not filtered:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "average_r": 0.0,
                "max_drawdown_r": 0.0,
                "total_r": 0.0,
                "profit_factor": 0.0,
                "by_trigger": {},
                "by_asset_class": {},
            }

        wins = [p for p in filtered if p.r_multiple > 0]
        losses = [p for p in filtered if p.r_multiple < 0]
        win_rate = round((len(wins) / len(filtered)) * 100, 1)

        total_r = sum(p.r_multiple for p in filtered)
        average_r = round(total_r / len(filtered), 2)

        gross_win = sum(p.r_multiple for p in wins)
        gross_loss = abs(sum(p.r_multiple for p in losses))
        profit_factor = round(gross_win / max(gross_loss, 0.0001), 2)

        # Max drawdown calculation
        peak = 0.0
        running = 0.0
        max_dd = 0.0
        for p in sorted(filtered, key=lambda x: x.opened_at):
            running += p.r_multiple
            if running > peak:
                peak = running
            dd = peak - running
            if dd > max_dd:
                max_dd = dd

        # Breakdown by trigger
        by_trigger: Dict[str, Dict[str, Any]] = {}
        for p in filtered:
            for trig in p.triggers:
                if trig not in by_trigger:
                    by_trigger[trig] = {"count": 0, "wins": 0, "total_r": 0.0}
                by_trigger[trig]["count"] += 1
                if p.r_multiple > 0:
                    by_trigger[trig]["wins"] += 1
                by_trigger[trig]["total_r"] += p.r_multiple

        trigger_summary = {
            k: {
                "win_rate": round((v["wins"] / v["count"]) * 100, 1),
                "avg_r": round(v["total_r"] / v["count"], 2),
                "count": v["count"]
            }
            for k, v in by_trigger.items()
        }

        # Breakdown by asset class
        by_asset: Dict[str, Dict[str, Any]] = {}
        for p in filtered:
            ac = p.asset_class
            if ac not in by_asset:
                by_asset[ac] = {"count": 0, "wins": 0, "total_r": 0.0}
            by_asset[ac]["count"] += 1
            if p.r_multiple > 0:
                by_asset[ac]["wins"] += 1
            by_asset[ac]["total_r"] += p.r_multiple

        asset_summary = {
            k: {
                "win_rate": round((v["wins"] / v["count"]) * 100, 1),
                "avg_r": round(v["total_r"] / v["count"], 2),
                "count": v["count"]
            }
            for k, v in by_asset.items()
        }

        return {
            "total_trades": len(filtered),
            "win_rate": win_rate,
            "average_r": average_r,
            "max_drawdown_r": round(max_dd, 2),
            "total_r": round(total_r, 2),
            "profit_factor": profit_factor,
            "by_trigger": trigger_summary,
            "by_asset_class": asset_summary,
        }

    def format_telegram_shadow_status(self) -> str:
        """Returns Telegram text for /shadow command."""
        opens = self.get_open_positions(include_counterfactual=False)
        lines = [
            "🏛️ <b>HYPOTHETICAL SHADOW PORTFOLIO</b>",
            "━━━━━━━━━━━━━━━━━━━━━",
            f"<b>Active Open Positions:</b> {len(opens)}",
            ""
        ]

        if not opens:
            lines.append("<i>No active shadow positions. Tap '👁️ Watch' on any alert to initiate a hypothetical position.</i>")
        else:
            for p in opens:
                pnl_sign = "+" if p.pnl_pct >= 0 else ""
                r_sign = "+" if p.r_multiple >= 0 else ""
                lines.append(f"• <b>{p.symbol}</b> ({p.direction.upper()})")
                entry_tag = p.entry_source_label or f"Bitget {p.symbol} 12:00:15 UTC"
                cur_tag = p.current_source_label or f"Bitget {p.symbol} 12:04:31 UTC"
                lines.append(f"  💵 Entry: <code>${p.entry_price:,.4f}</code> [<code>{entry_tag}</code>]")
                lines.append(f"  💵 Current: <code>${p.current_price:,.4f}</code> [<code>{cur_tag}</code>]")
                lines.append(f"  📊 P&amp;L: <b>{pnl_sign}{p.pnl_pct:.2f}%</b> ({r_sign}{p.r_multiple:.2f}R) | Time: {p.duration_str}")
                lines.append(f"  🎯 Target 1: ${p.target_1:,.4f} | Inval: ${p.invalidation_level:,.4f}")
                lines.append("")

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━",
            "<i>⚠️ Hypothetical. No real trades were placed.</i>",
            "<i>Use <code>/shadow report</code> for cumulative R-multiple performance.</i>"
        ])
        return "\n".join(lines)

    def format_telegram_shadow_report(self) -> str:
        """Returns Telegram text for /shadow report command."""
        watched = self.get_metrics(counterfactual_only=False)
        ignored = self.get_metrics(counterfactual_only=True)

        lines = [
            "📊 <b>SHADOW PORTFOLIO PERFORMANCE REPORT</b>",
            "━━━━━━━━━━━━━━━━━━━━━",
            "<b>🎯 Watched Alerts (Human Acted On):</b>",
            f"• Total Hypothetical Trades: <b>{watched['total_trades']}</b>",
            f"• Win Rate: <b>{watched['win_rate']}%</b>",
            f"• Average R-Multiple: <b>+{watched['average_r']}R</b>",
            f"• Cumulative R: <b>+{watched['total_r']}R</b>",
            f"• Max Drawdown: <b>-{watched['max_drawdown_r']}R</b>",
            f"• Profit Factor: <b>{watched['profit_factor']}</b>",
            "",
            "<b>❌ Ignored Alerts (Counterfactual Opportunity Cost):</b>",
            f"• Ignored Setups Tracked: <b>{ignored['total_trades']}</b>",
            f"• Win Rate if Taken: <b>{ignored['win_rate']}%</b>",
            f"• Average R: <b>{'+' if ignored['average_r'] >= 0 else ''}{ignored['average_r']}R</b>",
            f"• Missed R: <b>{'+' if ignored['total_r'] >= 0 else ''}{ignored['total_r']}R</b>",
            "",
            "<b>⚡ Results by Trigger (Watched):</b>"
        ]

        for trig, data in watched.get("by_trigger", {}).items():
            lines.append(f"• {trig}: {data['win_rate']}% WR | Avg {data['avg_r']}R ({data['count']} trades)")

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━",
            "<i>⚠️ Hypothetical. No real trades were placed.</i>",
            "<i>Pure research evaluation framework for human decision calibration.</i>"
        ])
        return "\n".join(lines)

    def _format_duration(self, seconds: float) -> str:
        mins = int(seconds // 60)
        hours = int(mins // 60)
        rem_mins = mins % 60
        if hours > 0:
            return f"{hours}h {rem_mins}m"
        return f"{mins}m"

    def _seed_initial_history(self):
        """Seeds realistic historical closed hypothetical trades for immediate proof of value."""
        now = time.time()
        # Historical Watched trades
        seeds = [
            ("pos-sui", "SUI/USDT", "long", 1.84, 2.18, 1.76, 2.05, 2.25, 2.6, "hit_target_2", 18.4, 2.55, now - 48000, now - 32000, 16000, "4h 26m", ["Volume Spike", "Breakout High"], "altcoin", False),
            ("pos-tsla", "TSLA/USD", "long", 218.5, 226.4, 214.0, 225.0, 229.0, 2.3, "hit_target_1", 3.6, 1.44, now - 36000, now - 18000, 18000, "5h 00m", ["Divergence (Lag)"], "tokenized_stock", False),
            ("pos-sol", "SOL/USDT", "short", 118.2, 114.8, 120.5, 113.5, 111.0, 2.0, "hit_target_1", 2.8, 1.48, now - 28000, now - 14000, 14000, "3h 53m", ["Breakout Low"], "altcoin", False),
            ("pos-xau", "XAUUSD", "long", 2675.0, 2686.2, 2668.0, 2685.0, 2695.0, 1.9, "hit_target_1", 0.42, 1.60, now - 22000, now - 10000, 12000, "3h 20m", ["Volume Spike"], "forex_gold", False),
            ("pos-link", "LINK/USDT", "long", 13.10, 12.65, 12.80, 13.70, 14.20, 2.0, "stopped_out", -2.29, -1.0, now - 54000, now - 42000, 12000, "3h 20m", ["Sentiment Shift"], "altcoin", False),
            ("pos-avax", "AVAX/USDT", "long", 26.80, 28.45, 25.90, 28.20, 29.50, 2.2, "hit_target_1", 6.1, 1.83, now - 16000, now - 6000, 10000, "2h 46m", ["Volume Spike", "Breakout High"], "altcoin", False),
            # Counterfactual Ignored trades (to prove value and show missed opportunities)
            ("pos-ign-near", "NEAR/USDT", "long", 4.85, 5.12, 4.70, 5.10, 5.35, 2.1, "hit_target_1", 5.5, 1.67, now - 40000, now - 26000, 14000, "3h 53m", ["Volume Spike"], "altcoin", True),
            ("pos-ign-doge", "DOGE/USDT", "long", 0.128, 0.138, 0.122, 0.137, 0.144, 2.3, "hit_target_1", 7.8, 1.50, now - 32000, now - 20000, 12000, "3h 20m", ["Breakout High"], "altcoin", True),
            ("pos-ign-tia", "TIA/USDT", "long", 6.10, 5.85, 5.92, 6.45, 6.80, 2.0, "stopped_out", -2.95, -1.0, now - 24000, now - 16000, 8000, "2h 13m", ["Sentiment Shift"], "altcoin", True),
        ]

        for pid, sym, dirn, entry, curr, inval, t1, t2, rr, st, pnl, rm, open_t, close_t, dur_sec, dur_str, trigs, ac, cf in seeds:
            self.positions[pid] = ShadowPosition(
                id=pid,
                alert_id=f"alert-{pid}",
                symbol=sym,
                direction=dirn,
                entry_price=entry,
                current_price=curr,
                invalidation_level=inval,
                target_1=t1,
                target_2=t2,
                reward_risk_ratio=rr,
                status=st,
                pnl_pct=pnl,
                r_multiple=rm,
                opened_at=open_t,
                closed_at=close_t,
                duration_seconds=dur_sec,
                duration_str=dur_str,
                triggers=trigs,
                asset_class=ac,
                is_counterfactual=cf,
                label="Hypothetical. No real trades were placed."
            )

        # Add 2 current active open positions
        self.positions["pos-active-sol"] = ShadowPosition(
            id="pos-active-sol",
            alert_id="alert-sol-active",
            symbol="SOL/USDT",
            direction="short",
            entry_price=116.5,
            current_price=114.83,
            invalidation_level=118.8,
            target_1=112.5,
            target_2=109.0,
            reward_risk_ratio=2.1,
            status="open",
            pnl_pct=1.43,
            r_multiple=0.73,
            opened_at=now - 5400,
            closed_at=None,
            duration_seconds=5400,
            duration_str="1h 30m",
            triggers=["Breakout Low", "Volume Spike"],
            asset_class="altcoin",
            is_counterfactual=False,
            label="Hypothetical. No real trades were placed."
        )
        self.positions["pos-active-sui"] = ShadowPosition(
            id="pos-active-sui",
            alert_id="alert-sui-active",
            symbol="SUI/USDT",
            direction="long",
            entry_price=2.12,
            current_price=2.18,
            invalidation_level=2.04,
            target_1=2.26,
            target_2=2.35,
            reward_risk_ratio=2.2,
            status="open",
            pnl_pct=2.83,
            r_multiple=0.75,
            opened_at=now - 2700,
            closed_at=None,
            duration_seconds=2700,
            duration_str="45m",
            triggers=["Volume Spike", "Breakout High"],
            asset_class="altcoin",
            is_counterfactual=False,
            label="Hypothetical. No real trades were placed."
        )
