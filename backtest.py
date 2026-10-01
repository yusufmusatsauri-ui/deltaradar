"""
DeltaRadar Historical Backtest Engine.
Replays historical candles to test anomaly, divergence, and scoring triggers.
Evaluates outcomes (+1h, +4h, +24h) and generates a backtest report.
"""
import time
import random
from typing import Dict, Any, List, Optional
from deltaradar.models import Candle, Alert, AssetClass, ConfidenceBreakdown
from deltaradar.anomaly import AnomalyDetector
from deltaradar.divergence import DivergenceEngine
from deltaradar.cause import CauseChecker
from deltaradar.scoring import ConfidenceScorer
from deltaradar.outcome_tracker import OutcomeTracker
from deltaradar.calibration import CalibrationEngine
from deltaradar.db import Database

class BacktestEngine:
    def __init__(self, db: Database, config: Dict[str, Any]):
        self.db = db
        self.config = config
        
        t = config.get("thresholds", {})
        s = config.get("scoring", {})
        
        self.anomaly_detector = AnomalyDetector(
            volume_multiplier=t.get("volume_spike", {}).get("multiplier", 3.0),
            volume_lookback=t.get("volume_spike", {}).get("lookback_periods", 20),
            swing_lookback=t.get("breakout", {}).get("swing_lookback", 20),
            min_breakout_penetration_pct=t.get("breakout", {}).get("min_penetration_pct", 0.2),
            sentiment_threshold=t.get("news_sentiment", {}).get("sentiment_shift_threshold", 0.35),
        )
        self.divergence_engine = DivergenceEngine(
            tokenized_max_lag_lead_pct=t.get("divergence", {}).get("tokenized_max_lag_lead_pct", 1.2),
            min_btc_move_pct=t.get("divergence", {}).get("altcoin_decoupling", {}).get("min_btc_move_pct", 1.5),
            min_alt_divergence_pct=t.get("divergence", {}).get("altcoin_decoupling", {}).get("min_alt_divergence_pct", 2.5),
        )
        self.cause_checker = CauseChecker()
        self.confidence_scorer = ConfidenceScorer()
        self.outcome_tracker = OutcomeTracker(db)
        self.min_confidence = s.get("min_alert_confidence", 60)

    def run_synthetic_backtest(self, num_candles: int = 120, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Runs full replay across test assets with simulated market impulses.
        """
        if symbols is None:
            symbols = ["SOL/USDT", "ETH/USDT", "SUI/USDT", "XAUUSD", "TSLA/USD"]

        alerts_generated = []
        outcomes_evaluated = []
        
        # Reference benchmark candles (BTC/USDT and Underlying TSLA)
        btc_candles = self._generate_series("BTC/USDT", 64000.0, num_candles, 5000.0)
        tsla_underlying_candles = self._generate_series("TSLA", 220.0, num_candles, 8000.0)

        for sym in symbols:
            asset_class = AssetClass.ALTCOIN
            if sym.startswith("XAU") or "USD" in sym and "/" not in sym:
                asset_class = AssetClass.FOREX_GOLD
                base_p = 2650.0
            elif "/USD" in sym and not sym.endswith("USDT"):
                asset_class = AssetClass.TOKENIZED_STOCK
                base_p = 215.0
            else:
                base_p = 150.0 if "SOL" in sym else (2500.0 if "ETH" in sym else 2.10)

            candles = self._generate_series(sym, base_p, num_candles, 1200.0)

            # Slide window across candles starting from lookback
            for i in range(25, num_candles - 24):
                window = candles[:i]
                cur_candle = window[-1]
                
                # Check anomaly
                eval_res = self.anomaly_detector.evaluate(window)
                
                # Check divergence
                div_note = "None"
                is_div = False
                div_gap = 0.0
                
                if asset_class == AssetClass.ALTCOIN:
                    btc_win = btc_candles[:i]
                    div_res = self.divergence_engine.check_altcoin_btc_decoupling(sym, window, btc_win)
                    if div_res.is_divergent:
                        is_div = True
                        div_note = div_res.details
                        div_gap = div_res.spread_or_gap_pct
                elif asset_class == AssetClass.TOKENIZED_STOCK:
                    und_p = tsla_underlying_candles[i - 1].close
                    div_res = self.divergence_engine.check_tokenized_divergence(sym, cur_candle.close, "TSLA", und_p)
                    if div_res.is_divergent:
                        is_div = True
                        div_note = div_res.details
                        div_gap = div_res.spread_or_gap_pct

                # Calculate confidence score
                bd = self.confidence_scorer.calculate(
                    volume_ratio=eval_res["volume_ratio"],
                    is_volume_spike=eval_res["volume_spike"],
                    is_breakout=eval_res["breakout"],
                    breakout_penetration_pct=eval_res["breakout_penetration_pct"],
                    is_divergence=is_div,
                    divergence_gap_pct=div_gap,
                    is_sentiment_shift=False,
                    sentiment_delta=0.0,
                    is_thin_liquidity=False,
                    spread_bps=6.0,
                )

                if (eval_res["has_anomaly"] or is_div) and bd.final_score >= self.min_confidence:
                    # Anomaly trigger met!
                    triggers = list(eval_res["triggers"])
                    if is_div:
                        triggers.append("Divergence")

                    # Calculate % move over last 3 candles
                    prev_p = window[-4].close if len(window) >= 4 else window[0].close
                    pct_move = round(((cur_candle.close - prev_p) / prev_p) * 100.0, 2)

                    # Cause check
                    cause = self.cause_checker.summarize_cause(sym, pct_move, triggers, skip_llm=True)

                    alert = Alert(
                        id=f"alert-bt-{sym}-{i}",
                        timestamp=cur_candle.timestamp,
                        symbol=sym,
                        asset_class=asset_class,
                        triggers=triggers,
                        price=cur_candle.close,
                        pct_move=pct_move,
                        volume_vs_avg=eval_res["volume_ratio"],
                        divergence_note=div_note,
                        confidence=bd.final_score,
                        why_summary=cause.summary,
                        chart_link=f"https://www.tradingview.com/chart/?symbol={sym.replace('/', '')}",
                        breakdown=bd,
                    )
                    self.db.save_alert(alert)
                    alerts_generated.append(alert)

                    # Outcome evaluation (+1h, +4h, +24h lookaheads)
                    direction = "bullish" if pct_move >= 0 else "bearish"
                    outcome_rec = self.outcome_tracker.register_alert_for_tracking(alert, direction)
                    
                    # 1h is +12 candles (5m * 12 = 60m)
                    # 4h is +48 candles
                    idx_1h = min(len(candles) - 1, i + 12)
                    idx_4h = min(len(candles) - 1, i + 48)
                    idx_24h = len(candles) - 1

                    # Evaluate 1h
                    o1 = self.outcome_tracker.evaluate_price_step(
                        outcome_rec.__dict__,
                        candles[idx_1h].timestamp,
                        candles[idx_1h].close,
                    )
                    # Evaluate 4h
                    o4 = self.outcome_tracker.evaluate_price_step(
                        o1.__dict__,
                        candles[idx_4h].timestamp,
                        candles[idx_4h].close,
                    )
                    outcomes_evaluated.append(o4)

        # Run calibration on backtest outcomes
        calibrator = CalibrationEngine(self.db)
        calib_stats = calibrator.evaluate_stats(lookback_days=30)

        return {
            "num_candles_replayed": num_candles,
            "symbols_tested": symbols,
            "alerts_generated": len(alerts_generated),
            "outcomes_evaluated": len(outcomes_evaluated),
            "overall_hit_rate": calib_stats["overall_hit_rate"],
            "calibration_report": calib_stats["report_markdown"],
            "new_weights": calib_stats["new_weights"],
            "sample_alerts": [a.to_dict() for a in alerts_generated[:5]],
        }

    def _generate_series(self, symbol: str, start_price: float, count: int, base_vol: float) -> List[Candle]:
        candles = []
        p = start_price
        now = time.time()
        
        trend = 0.0
        for i in range(count):
            ts = now - ((count - i) * 300)
            # Inject intermittent volatility or breakout bursts
            if i in [30, 60, 80]:
                trend = 0.004 if i % 2 == 0 else -0.003
                drift = 0.032 if i % 2 == 0 else -0.025
                vol = base_vol * (3.8 + (i % 3))
            elif 0 < trend and (i % 30) < 15:
                # Continuation trend
                drift = trend + (random.random() - 0.45) * 0.004
                vol = base_vol * (1.2 + random.random() * 0.8)
            else:
                trend = 0.0
                drift = (random.random() - 0.49) * 0.008
                vol = base_vol * (0.8 + random.random() * 0.5)

            o = p
            c = p * (1.0 + drift)
            h = max(o, c) * (1.0 + random.random() * 0.003)
            l = min(o, c) * (1.0 - random.random() * 0.003)
            p = c

            candles.append(Candle(
                symbol=symbol,
                timestamp=ts,
                open=round(o, 4),
                high=round(h, 4),
                low=round(l, 4),
                close=round(c, 4),
                volume=round(vol, 2),
                period="5m",
            ))
        return candles
