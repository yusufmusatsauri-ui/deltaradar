"""
DeltaRadar Anomaly Detection Engine.
Detects:
1. Volume Spike (volume > [3x] 20-period average)
2. Breakout (close beyond recent swing high/low, S/R zones)
3. News/Sentiment Shift (sentiment score change beyond threshold)
"""
from typing import List, Optional, Tuple, Dict, Any
from deltaradar.models import Candle, AnomalyType

class AnomalyDetector:
    def __init__(
        self,
        volume_multiplier: float = 3.0,
        volume_lookback: int = 20,
        swing_lookback: int = 20,
        min_breakout_penetration_pct: float = 0.2,
        sentiment_threshold: float = 0.35,
    ):
        self.volume_multiplier = volume_multiplier
        self.volume_lookback = volume_lookback
        self.swing_lookback = swing_lookback
        self.min_breakout_penetration_pct = min_breakout_penetration_pct
        self.sentiment_threshold = sentiment_threshold

    def check_volume_spike(self, candles: List[Candle]) -> Tuple[bool, float, float]:
        """
        Calculates whether the most recent candle's volume exceeds the threshold
        relative to the 20-period moving average volume.
        Returns: (is_spike, current_volume_ratio, avg_volume)
        """
        if len(candles) < self.volume_lookback + 1:
            return False, 1.0, 0.0

        current_candle = candles[-1]
        prior_candles = candles[-(self.volume_lookback + 1):-1]
        
        avg_volume = sum(c.volume for c in prior_candles) / len(prior_candles)
        if avg_volume <= 0:
            return False, 1.0, 0.0

        ratio = current_candle.volume / avg_volume
        is_spike = ratio >= self.volume_multiplier
        return is_spike, round(ratio, 2), round(avg_volume, 2)

    def check_breakout(self, candles: List[Candle]) -> Tuple[bool, Optional[str], float, float]:
        """
        Checks if the latest candle closed beyond the recent swing high or swing low.
        Returns: (is_breakout, breakout_direction ['high' | 'low' | None], level_broken, pct_penetration)
        """
        if len(candles) < self.swing_lookback + 1:
            return False, None, 0.0, 0.0

        current_candle = candles[-1]
        lookback_candles = candles[-(self.swing_lookback + 1):-1]

        swing_high = max(c.high for c in lookback_candles)
        swing_low = min(c.low for c in lookback_candles)

        # Bullish breakout above swing high
        if current_candle.close > swing_high:
            pct_pen = ((current_candle.close - swing_high) / swing_high) * 100.0
            if pct_pen >= self.min_breakout_penetration_pct:
                return True, "high", swing_high, round(pct_pen, 2)

        # Bearish breakdown below swing low
        if current_candle.close < swing_low:
            pct_pen = ((swing_low - current_candle.close) / swing_low) * 100.0
            if pct_pen >= self.min_breakout_penetration_pct:
                return True, "low", swing_low, round(pct_pen, 2)

        return False, None, 0.0, 0.0

    def check_sentiment_shift(self, current_sentiment: float, previous_sentiment: float) -> Tuple[bool, float]:
        """
        Checks if news sentiment shift exceeds the threshold.
        Scale: -1.0 (extremely bearish) to +1.0 (extremely bullish).
        Returns: (is_shift, delta)
        """
        delta = current_sentiment - previous_sentiment
        is_shift = abs(delta) >= self.sentiment_threshold
        return is_shift, round(delta, 2)

    def evaluate(
        self,
        candles: List[Candle],
        current_sentiment: Optional[float] = None,
        previous_sentiment: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates all anomaly conditions for a given symbol's candles and sentiment.
        """
        vol_spike, vol_ratio, avg_vol = self.check_volume_spike(candles)
        breakout, bo_dir, bo_level, bo_pen = self.check_breakout(candles)
        
        sent_shift = False
        sent_delta = 0.0
        if current_sentiment is not None and previous_sentiment is not None:
            sent_shift, sent_delta = self.check_sentiment_shift(current_sentiment, previous_sentiment)

        triggers = []
        if vol_spike:
            triggers.append(f"Volume Spike ({vol_ratio}x)")
        if breakout:
            triggers.append(f"Breakout {bo_dir.capitalize()} (Level: {bo_level})")
        if sent_shift:
            direction = "Bullish" if sent_delta > 0 else "Bearish"
            triggers.append(f"Sentiment Shift {direction} (Δ{sent_delta:+.2f})")

        return {
            "has_anomaly": len(triggers) > 0,
            "triggers": triggers,
            "volume_spike": vol_spike,
            "volume_ratio": vol_ratio,
            "avg_volume": avg_volume if 'avg_volume' in locals() else avg_vol,
            "breakout": breakout,
            "breakout_direction": bo_dir,
            "breakout_level": bo_level,
            "breakout_penetration_pct": bo_pen,
            "sentiment_shift": sent_shift,
            "sentiment_delta": sent_delta,
        }
