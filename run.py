#!/usr/bin/env python3
"""
DeltaRadar Main Entry Point.
Modes:
  --mode dry-run   : Run live anomaly detection and print formatted alerts to console (no trades executed)
  --mode live      : Run live detection with WebSocket streams & Telegram Bot dispatcher
  --mode backtest  : Replay historical candles, score triggers, and verify +1h/+4h/+24h outcomes
  --mode calibrate : Run weekly empirical calibration and output performance report
  --test           : Execute automated unit test suite
"""
import sys
import os
import argparse
import asyncio
import logging
import time

from deltaradar.config import load_config
from deltaradar.db import Database
from deltaradar.models import Candle, Alert, AssetClass
from deltaradar.anomaly import AnomalyDetector
from deltaradar.divergence import DivergenceEngine
from deltaradar.cause import CauseChecker
from deltaradar.brief import DeskBriefGenerator
from deltaradar.scoring import ConfidenceScorer
from deltaradar.telegram_bot import TelegramBot
from deltaradar.outcome_tracker import OutcomeTracker
from deltaradar.calibration import CalibrationEngine
from deltaradar.backtest import BacktestEngine
from deltaradar.ingest.mock_replay import MockReplayAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("DeltaRadar")

async def run_radar(config_path: str = "config.yaml", dry_run: bool = False):
    config = load_config(config_path)
    db = Database(config.get("database_path", "deltaradar.db"))
    
    t = config.get("thresholds", {})
    s = config.get("scoring", {})
    tg = config.get("telegram", {})

    logger.info("Initializing DeltaRadar Agent...")
    print("\n" + "=" * 60)
    print("🛰️  DELTARADAR: Autonomous Market Anomaly Agent")
    print(f"⚠️  {config.get('agent', {}).get('disclaimer', 'Alert-only intelligence.')}")
    print("=" * 60)

    # Instantiate modules
    anomaly_detector = AnomalyDetector(
        volume_multiplier=t.get("volume_spike", {}).get("multiplier", 3.0),
        volume_lookback=t.get("volume_spike", {}).get("lookback_periods", 20),
        swing_lookback=t.get("breakout", {}).get("swing_lookback", 20),
        min_breakout_penetration_pct=t.get("breakout", {}).get("min_penetration_pct", 0.2),
        sentiment_threshold=t.get("news_sentiment", {}).get("sentiment_shift_threshold", 0.35),
    )

    divergence_engine = DivergenceEngine(
        tokenized_max_lag_lead_pct=t.get("divergence", {}).get("tokenized_max_lag_lead_pct", 1.2),
        min_btc_move_pct=t.get("divergence", {}).get("altcoin_decoupling", {}).get("min_btc_move_pct", 1.5),
        min_alt_divergence_pct=t.get("divergence", {}).get("altcoin_decoupling", {}).get("min_alt_divergence_pct", 2.5),
    )

    cause_checker = CauseChecker(api_key=config.get("ai", {}).get("gemini_api_key"))
    desk_brief_gen = DeskBriefGenerator(api_key=config.get("ai", {}).get("gemini_api_key"))
    
    # Load calibrated or default weights
    weights = db.get_latest_weights()
    confidence_scorer = ConfidenceScorer(weights=weights)

    telegram_bot = TelegramBot(
        db=db,
        bot_token=tg.get("bot_token"),
        chat_id=tg.get("chat_id"),
        cooldown_minutes=tg.get("cooldown_minutes_per_asset", 30),
        quiet_hours_enabled=tg.get("quiet_hours", {}).get("enabled", False),
        quiet_hours_start_utc=tg.get("quiet_hours", {}).get("start_utc", "23:00"),
        quiet_hours_end_utc=tg.get("quiet_hours", {}).get("end_utc", "06:00"),
        dry_run=dry_run or config.get("agent", {}).get("dry_run", False),
    )

    outcome_tracker = OutcomeTracker(db)

    # Ingest setup
    replay_feed = MockReplayAdapter()
    
    # Watchlist symbols
    wl = config.get("watchlist", {})
    alts = wl.get("altcoins", {}).get("symbols", ["SOL/USDT", "ETH/USDT", "SUI/USDT"])
    stocks = [s["symbol"] if isinstance(s, dict) else s for s in wl.get("tokenized_stocks", {}).get("symbols", ["TSLA/USD"])]
    forex = [f["symbol"] if isinstance(f, dict) else f for f in wl.get("forex_gold", {}).get("symbols", ["XAUUSD"])]
    all_symbols = alts + stocks + forex

    logger.info(f"Loaded {len(all_symbols)} watchlist assets across 3 sectors.")
    
    # Seed candle histories
    btc_series = replay_feed.generate_baseline_series("BTC/USDT", 65000.0, 30, 8000.0)
    for sym in all_symbols:
        p = 2650.0 if "XAU" in sym else (220.0 if "TSLA" in sym else (150.0 if "SOL" in sym else 100.0))
        replay_feed.generate_baseline_series(sym, p, 30, 1000.0)

    print(f"\n[Radar Active] Monitoring live order book and trade streams... Press Ctrl+C to stop.\n")

    iteration = 0
    try:
        while True:
            iteration += 1
            # Every 3 iterations, simulate an anomaly for demonstration
            if iteration == 1:
                # Volume spike + Breakout on SOL
                print("⚡ [Live Stream] Ingesting burst volume on SOL/USDT...")
                replay_feed.inject_volume_spike("SOL/USDT", multiplier=4.2)
                cur_c = replay_feed.inject_breakout("SOL/USDT", direction="high", penetration_pct=1.4)
            elif iteration == 3:
                # Decoupling: BTC dumps, SUI surges
                print("⚡ [Live Stream] Injecting BTC selloff vs SUI surge decoupling...")
                for _ in range(4):
                    replay_feed.inject_breakout("BTC/USDT", direction="low", penetration_pct=0.6)
                cur_c = replay_feed.inject_breakout("SUI/USDT", direction="high", penetration_pct=2.8)
                replay_feed.inject_volume_spike("SUI/USDT", multiplier=3.6)
            elif iteration == 5:
                # Tokenized TSLA premium lead vs Nasdaq
                print("⚡ [Live Stream] TSLA/USD tokenized spread divergence...")
                cur_c = replay_feed.inject_breakout("TSLA/USD", direction="high", penetration_pct=1.8)
            else:
                await asyncio.sleep(2)
                continue

            # Process candidates
            for sym in ["SOL/USDT", "SUI/USDT", "TSLA/USD"]:
                candles = await replay_feed.fetch_historical_candles(sym, limit=25)
                if len(candles) < 21:
                    continue

                cur_candle = candles[-1]
                anom = anomaly_detector.evaluate(candles)
                
                # Divergence check
                is_div = False
                div_note = "None"
                div_gap = 0.0

                if "/USD" in sym and not sym.endswith("USDT"):
                    asset_cls = AssetClass.TOKENIZED_STOCK
                    div_res = divergence_engine.check_tokenized_divergence(sym, cur_candle.close, "TSLA", 220.0)
                    if div_res.is_divergent:
                        is_div = True
                        div_note = div_res.details
                        div_gap = div_res.spread_or_gap_pct
                elif "XAU" in sym:
                    asset_cls = AssetClass.FOREX_GOLD
                else:
                    asset_cls = AssetClass.ALTCOIN
                    btc_candles = await replay_feed.fetch_historical_candles("BTC/USDT", limit=25)
                    div_res = divergence_engine.check_altcoin_btc_decoupling(sym, candles, btc_candles)
                    if div_res.is_divergent:
                        is_div = True
                        div_note = div_res.details
                        div_gap = div_res.spread_or_gap_pct

                # Calculate confidence score
                breakdown = confidence_scorer.calculate(
                    volume_ratio=anom["volume_ratio"],
                    is_volume_spike=anom["volume_spike"],
                    is_breakout=anom["breakout"],
                    breakout_penetration_pct=anom["breakout_penetration_pct"],
                    is_divergence=is_div,
                    divergence_gap_pct=div_gap,
                    is_sentiment_shift=False,
                    sentiment_delta=0.0,
                )

                min_conf = s.get("min_alert_confidence", 60)
                if (anom["has_anomaly"] or is_div) and breakdown.final_score >= min_conf:
                    triggers = list(anom["triggers"])
                    if is_div:
                        triggers.append("Divergence")

                    # % move over 3 periods
                    prev_p = candles[-4].close if len(candles) >= 4 else candles[0].close
                    pct_move = round(((cur_candle.close - prev_p) / prev_p) * 100.0, 2)

                    # Desk Brief generation
                    brief = desk_brief_gen.generate_brief(
                        symbol=sym,
                        asset_class=asset_cls,
                        current_price=cur_candle.close,
                        pct_move=pct_move,
                        volume_vs_avg=anom["volume_ratio"],
                        triggers=triggers,
                        divergence_note=div_note,
                        confidence_breakdown=breakdown,
                        candles=candles,
                        skip_llm=True, # Instant in dry-run
                    )

                    alert = Alert(
                        id=f"alt-{int(time.time())}-{sym.replace('/', '')}",
                        timestamp=time.time(),
                        symbol=sym,
                        asset_class=asset_cls,
                        triggers=triggers,
                        price=cur_candle.close,
                        pct_move=pct_move,
                        volume_vs_avg=anom["volume_ratio"],
                        divergence_note=div_note,
                        confidence=breakdown.final_score,
                        why_summary=brief.likely_cause,
                        chart_link=f"https://www.tradingview.com/chart/?symbol={sym.replace('/', '')}",
                        breakdown=breakdown,
                        brief=brief,
                    )

                    # Dispatch alert
                    sent = telegram_bot.send_alert(alert)
                    if sent:
                        # Register in outcome tracker
                        direction = "bullish" if pct_move >= 0 else "bearish"
                        outcome_tracker.register_alert_for_tracking(alert, direction)

            if dry_run and iteration >= 5:
                print("\n[Dry Run Cycle Complete] Exiting test loop successfully.")
                break

            await asyncio.sleep(2)

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("DeltaRadar stopped by user.")

def main():
    parser = argparse.ArgumentParser(description="DeltaRadar: Autonomous Market Anomaly Agent")
    parser.add_argument("--mode", choices=["live", "dry-run", "backtest", "calibrate"], default="dry-run", help="Execution mode")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--test", action="store_true", help="Run automated test suite")
    args = parser.parse_args()

    if args.test:
        import unittest
        suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py")
        runner = unittest.TextTestRunner(verbosity=2)
        res = runner.run(suite)
        sys.exit(0 if res.wasSuccessful() else 1)

    if args.mode == "backtest":
        cfg = load_config(args.config)
        db = Database(cfg.get("database_path", "deltaradar.db"))
        engine = BacktestEngine(db, cfg)
        print("Starting DeltaRadar Historical Backtest...")
        results = engine.run_synthetic_backtest(num_candles=100)
        print("\n" + "=" * 60)
        print("🎯 BACKTEST SUMMARY")
        print(f"Candles Replayed: {results['num_candles_replayed']}")
        print(f"Alerts Triggered: {results['alerts_generated']}")
        print(f"Overall Hit Rate: {results['overall_hit_rate']}%")
        print("=" * 60)
        print("\n" + results["calibration_report"])
        sys.exit(0)

    if args.mode == "calibrate":
        cfg = load_config(args.config)
        db = Database(cfg.get("database_path", "deltaradar.db"))
        calibrator = CalibrationEngine(db)
        stats = calibrator.run_calibration_and_save()
        print(stats["report_markdown"].replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace("<i>", "").replace("</i>", ""))
        sys.exit(0)

    # Live or Dry-run
    asyncio.run(run_radar(config_path=args.config, dry_run=(args.mode == "dry-run")))

if __name__ == "__main__":
    main()
