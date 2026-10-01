"""
DeltaRadar Self-Calibration Engine.
Analyzes historical alert outcomes and empirically tunes trigger weights weekly.
Generates comprehensive report:
- Hit rate by trigger
- Hit rate by asset class
- Hit rate by confidence band
- Trigger weight delta rationale (which weights changed and why)
"""
import time
from typing import Dict, Any, List, Tuple
from deltaradar.models import TriggerWeights
from deltaradar.db import Database

class CalibrationEngine:
    def __init__(
        self,
        db: Database,
        target_hit_rate: float = 0.65,
        adjust_step: float = 0.05,
        min_weight: float = 0.05,
        max_weight: float = 0.55,
    ):
        self.db = db
        self.target_hit_rate = target_hit_rate
        self.adjust_step = adjust_step
        self.min_weight = min_weight
        self.max_weight = max_weight

    def evaluate_stats(self, lookback_days: int = 7) -> Dict[str, Any]:
        """
        Analyzes outcomes over the lookback window.
        """
        outcomes = self.db.get_all_outcomes()
        cutoff = time.time() - (lookback_days * 86400)
        
        # Filter for outcomes within window that have at least +1h or +4h resolved
        evaluated = [
            o for o in outcomes 
            if o["alert_timestamp"] >= cutoff and (o["hit_1h"] is not None or o["hit_4h"] is not None)
        ]

        if not evaluated:
            # Fallback to all evaluated outcomes if recent sample is small
            evaluated = [o for o in outcomes if (o["hit_1h"] is not None or o["hit_4h"] is not None)]

        # 1. By trigger
        trigger_stats = {
            "volume_spike": {"hits": 0, "total": 0},
            "breakout": {"hits": 0, "total": 0},
            "divergence": {"hits": 0, "total": 0},
            "sentiment": {"hits": 0, "total": 0},
        }

        # 2. By asset class
        class_stats = {
            "altcoin": {"hits": 0, "total": 0},
            "forex_gold": {"hits": 0, "total": 0},
            "tokenized_stock": {"hits": 0, "total": 0},
        }

        # 3. By confidence band
        bands = {
            "60-69 (Moderate)": {"hits": 0, "total": 0},
            "70-79 (High)": {"hits": 0, "total": 0},
            "80-89 (Strong)": {"hits": 0, "total": 0},
            "90-100 (Exceptional)": {"hits": 0, "total": 0},
        }

        # 4. Human Decision Performance (Watched vs Ignored)
        decisions_stats = {
            "watch": {"hits": 0, "total": 0},
            "ignore": {"hits": 0, "total": 0},
            "snooze_1h": {"hits": 0, "total": 0},
            "pending": {"hits": 0, "total": 0},
        }

        # 5. Alerts ignored that played out (missed moves)
        ignored_that_played_out = []

        total_hits = 0
        total_count = len(evaluated)

        for o in evaluated:
            # Overall success if hit at 1h or 4h
            is_hit = bool(o.get("hit_1h") or o.get("hit_4h") or o.get("hit_24h"))
            if is_hit:
                total_hits += 1

            # Decision tracking
            dec = o.get("human_decision", "pending")
            if dec not in decisions_stats:
                dec = "pending"
            decisions_stats[dec]["total"] += 1
            if is_hit:
                decisions_stats[dec]["hits"] += 1

            # Check if ignored that played out
            if dec == "ignore" and is_hit:
                max_move = max(filter(None, [o.get("move_pct_1h"), o.get("move_pct_4h"), o.get("move_pct_24h")]), default=0.0)
                ignored_that_played_out.append({
                    "symbol": o["symbol"],
                    "triggers": o.get("triggers", []),
                    "confidence": o.get("confidence", 0),
                    "move_pct": round(max_move, 2),
                })

            # Asset class
            ac = o.get("asset_class", "altcoin")
            if ac in class_stats:
                class_stats[ac]["total"] += 1
                if is_hit:
                    class_stats[ac]["hits"] += 1

            # Confidence band
            conf = o.get("confidence", 0)
            if 60 <= conf <= 69:
                band_key = "60-69 (Moderate)"
            elif 70 <= conf <= 79:
                band_key = "70-79 (High)"
            elif 80 <= conf <= 89:
                band_key = "80-89 (Strong)"
            else:
                band_key = "90-100 (Exceptional)"
            bands[band_key]["total"] += 1
            if is_hit:
                bands[band_key]["hits"] += 1

            # Triggers
            triggers = o.get("triggers", [])
            trig_str = " ".join(triggers).lower()
            if "volume" in trig_str:
                trigger_stats["volume_spike"]["total"] += 1
                if is_hit:
                    trigger_stats["volume_spike"]["hits"] += 1
            if "breakout" in trig_str:
                trigger_stats["breakout"]["total"] += 1
                if is_hit:
                    trigger_stats["breakout"]["hits"] += 1
            if "divergence" in trig_str or "decoupling" in trig_str or "lag" in trig_str:
                trigger_stats["divergence"]["total"] += 1
                if is_hit:
                    trigger_stats["divergence"]["hits"] += 1
            if "sentiment" in trig_str:
                trigger_stats["sentiment"]["total"] += 1
                if is_hit:
                    trigger_stats["sentiment"]["hits"] += 1

        overall_hit_rate = (total_hits / total_count) if total_count > 0 else 0.0

        # Compute calibrated weights
        current_weights = self.db.get_latest_weights() or TriggerWeights()
        new_weights, changes = self._calibrate_weights(current_weights, trigger_stats)

        # Build Markdown report
        report_md = self._generate_report(
            total_count=total_count,
            overall_hit_rate=overall_hit_rate,
            trigger_stats=trigger_stats,
            class_stats=class_stats,
            bands=bands,
            decisions_stats=decisions_stats,
            ignored_that_played_out=ignored_that_played_out,
            old_weights=current_weights,
            new_weights=new_weights,
            changes=changes,
        )

        return {
            "total_evaluated": total_count,
            "overall_hit_rate": round(overall_hit_rate * 100, 1),
            "trigger_stats": trigger_stats,
            "class_stats": class_stats,
            "confidence_bands": bands,
            "decisions_stats": decisions_stats,
            "ignored_that_played_out": ignored_that_played_out,
            "old_weights": current_weights.to_dict(),
            "new_weights": new_weights.to_dict(),
            "changes": changes,
            "report_markdown": report_md,
        }

    def _calibrate_weights(
        self,
        current: TriggerWeights,
        trigger_stats: Dict[str, Dict[str, int]],
    ) -> Tuple[TriggerWeights, List[str]]:
        changes = []
        w_vol = current.volume_spike
        w_bo = current.breakout
        w_div = current.divergence
        w_sent = current.sentiment

        mapping = [
            ("volume_spike", "Volume Spike", w_vol),
            ("breakout", "Breakout", w_bo),
            ("divergence", "Divergence", w_div),
            ("sentiment", "Sentiment", w_sent),
        ]

        new_vals = {}
        for key, name, cur_val in mapping:
            st = trigger_stats[key]
            total = st["total"]
            if total >= 3: # Min sample size to adjust
                rate = st["hits"] / total
                if rate >= (self.target_hit_rate + 0.05):
                    new_val = min(self.max_weight, cur_val + self.adjust_step)
                    new_vals[key] = new_val
                    changes.append(f"{name}: +0.05 ({cur_val:.2f} ➔ {new_val:.2f}) [High hit rate {rate*100:.1f}%]")
                elif rate < (self.target_hit_rate - 0.10):
                    new_val = max(self.min_weight, cur_val - self.adjust_step)
                    new_vals[key] = new_val
                    changes.append(f"{name}: -0.05 ({cur_val:.2f} ➔ {new_val:.2f}) [Underperforming hit rate {rate*100:.1f}%]")
                else:
                    new_vals[key] = cur_val
            else:
                new_vals[key] = cur_val

        # Normalize so sum == 1.0
        tot = sum(new_vals.values())
        if tot > 0:
            for k in new_vals:
                new_vals[k] = round(new_vals[k] / tot, 4)

        if not changes:
            changes.append("All trigger weights maintained within target calibration equilibrium.")

        calibrated = TriggerWeights(
            volume_spike=new_vals["volume_spike"],
            breakout=new_vals["breakout"],
            divergence=new_vals["divergence"],
            sentiment=new_vals["sentiment"],
        )
        return calibrated, changes

    def _generate_report(
        self,
        total_count: int,
        overall_hit_rate: float,
        trigger_stats: Dict[str, Dict[str, int]],
        class_stats: Dict[str, Dict[str, int]],
        bands: Dict[str, Dict[str, int]],
        decisions_stats: Dict[str, Dict[str, int]],
        ignored_that_played_out: List[Dict[str, Any]],
        old_weights: TriggerWeights,
        new_weights: TriggerWeights,
        changes: List[str],
    ) -> str:
        def rate_str(h: int, t: int) -> str:
            return f"{(h / t * 100):.1f}% ({h}/{t})" if t > 0 else "N/A (0)"

        ignored_lines = []
        if ignored_that_played_out:
            for item in ignored_that_played_out[:4]:
                ignored_lines.append(f"• <b>{item['symbol']}</b> (+{item['move_pct']}%) — Triggers: {', '.join(item['triggers'])} [Conf: {item['confidence']}]")
        else:
            ignored_lines.append("• None. Excellent discipline on dismissed alerts.")

        ignored_section = "\n".join(ignored_lines)

        md = (
            f"📊 <b>DELTARADAR WEEKLY RESEARCH & CALIBRATION REPORT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>Total Alerts Evaluated:</b> {total_count}\n"
            f"📈 <b>Overall Hit Rate:</b> {overall_hit_rate * 100:.1f}%\n\n"
            f"⚡ <b>HIT RATE BY TRIGGER:</b>\n"
            f"• Volume Spike: {rate_str(trigger_stats['volume_spike']['hits'], trigger_stats['volume_spike']['total'])}\n"
            f"• Breakout: {rate_str(trigger_stats['breakout']['hits'], trigger_stats['breakout']['total'])}\n"
            f"• Divergence: {rate_str(trigger_stats['divergence']['hits'], trigger_stats['divergence']['total'])}\n"
            f"• Sentiment: {rate_str(trigger_stats['sentiment']['hits'], trigger_stats['sentiment']['total'])}\n\n"
            f"🏛️ <b>HIT RATE BY ASSET CLASS:</b>\n"
            f"• Altcoins: {rate_str(class_stats['altcoin']['hits'], class_stats['altcoin']['total'])}\n"
            f"• Forex & Gold: {rate_str(class_stats['forex_gold']['hits'], class_stats['forex_gold']['total'])}\n"
            f"• Tokenized Stocks: {rate_str(class_stats['tokenized_stock']['hits'], class_stats['tokenized_stock']['total'])}\n\n"
            f"🎯 <b>HIT RATE BY CONFIDENCE BAND:</b>\n"
            f"• 60-69 (Moderate): {rate_str(bands['60-69 (Moderate)']['hits'], bands['60-69 (Moderate)']['total'])}\n"
            f"• 70-79 (High): {rate_str(bands['70-79 (High)']['hits'], bands['70-79 (High)']['total'])}\n"
            f"• 80-89 (Strong): {rate_str(bands['80-89 (Strong)']['hits'], bands['80-89 (Strong)']['total'])}\n"
            f"• 90-100 (Exceptional): {rate_str(bands['90-100 (Exceptional)']['hits'], bands['90-100 (Exceptional)']['total'])}\n\n"
            f"🧠 <b>HUMAN TRADER DISCIPLINE AUDIT:</b>\n"
            f"• Watched Alerts Hit Rate: {rate_str(decisions_stats['watch']['hits'], decisions_stats['watch']['total'])}\n"
            f"• Ignored Alerts Hit Rate: {rate_str(decisions_stats['ignore']['hits'], decisions_stats['ignore']['total'])}\n\n"
            f"👀 <b>ALERTS YOU IGNORED THAT PLAYED OUT:</b>\n"
            f"{ignored_section}\n\n"
            f"⚖️ <b>WEIGHT ADJUSTMENTS & RATIONALE:</b>\n"
            + "\n".join(f"• {c}" for c in changes) +
            f"\n\n<b>New Calibrated Weights:</b>\n"
            f"• Vol: {new_weights.volume_spike:.2f} | Breakout: {new_weights.breakout:.2f} | Div: {new_weights.divergence:.2f} | Sent: {new_weights.sentiment:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>⚠️ Informational research report. DeltaRadar never executes trades.</i>"
        )
        return md

    def run_calibration_and_save(self) -> Dict[str, Any]:
        stats = self.evaluate_stats()
        new_w = TriggerWeights(**stats["new_weights"])
        self.db.save_calibration(new_w, stats["report_markdown"])
        return stats
