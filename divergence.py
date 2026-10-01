"""
DeltaRadar Divergence Engine (Signature Feature).
Detects:
1. Tokenized Asset Lag/Lead vs Underlying Stock or Gold (e.g., TSLA/USD vs NASDAQ:TSLA, XAUT/USD vs Spot Gold).
2. Altcoin Decoupling: when an altcoin moves against or radically decouples from BTC in the middle of a BTC trend/impulse.
"""
from typing import List, Optional
from deltaradar.models import Candle, DivergenceResult, DivergenceType

class DivergenceEngine:
    def __init__(
        self,
        tokenized_max_lag_lead_pct: float = 1.2,
        min_btc_move_pct: float = 1.5,
        min_alt_divergence_pct: float = 2.5,
    ):
        self.tokenized_max_lag_lead_pct = tokenized_max_lag_lead_pct
        self.min_btc_move_pct = min_btc_move_pct
        self.min_alt_divergence_pct = min_alt_divergence_pct

    def check_tokenized_divergence(
        self,
        token_symbol: str,
        token_price: float,
        underlying_symbol: str,
        underlying_price: float,
    ) -> DivergenceResult:
        """
        Calculates spread between tokenized asset and underlying market price.
        If spread exceeds threshold, flags lag (discount) or lead (premium).
        """
        if underlying_price <= 0:
            return DivergenceResult(
                is_divergent=False,
                divergence_type=DivergenceType.NONE,
                reference_symbol=underlying_symbol,
                asset_price=token_price,
                reference_price=underlying_price,
                asset_move_pct=0.0,
                reference_move_pct=0.0,
                spread_or_gap_pct=0.0,
                details="Invalid reference price",
            )

        spread_pct = ((token_price - underlying_price) / underlying_price) * 100.0

        if abs(spread_pct) >= self.tokenized_max_lag_lead_pct:
            div_type = DivergenceType.TOKENIZED_LEAD if spread_pct > 0 else DivergenceType.TOKENIZED_LAG
            condition = "trading at premium (+lead)" if spread_pct > 0 else "lagging underlying (-discount)"
            details = (
                f"{token_symbol} {condition} by {abs(spread_pct):.2f}% "
                f"(Token: ${token_price:.2f} vs {underlying_symbol}: ${underlying_price:.2f})"
            )
            return DivergenceResult(
                is_divergent=True,
                divergence_type=div_type,
                reference_symbol=underlying_symbol,
                asset_price=token_price,
                reference_price=underlying_price,
                asset_move_pct=0.0,
                reference_move_pct=0.0,
                spread_or_gap_pct=round(spread_pct, 2),
                details=details,
            )

        return DivergenceResult(
            is_divergent=False,
            divergence_type=DivergenceType.NONE,
            reference_symbol=underlying_symbol,
            asset_price=token_price,
            reference_price=underlying_price,
            asset_move_pct=0.0,
            reference_move_pct=0.0,
            spread_or_gap_pct=round(spread_pct, 2),
            details=f"In sync with {underlying_symbol} (Spread: {spread_pct:.2f}%)",
        )

    def check_altcoin_btc_decoupling(
        self,
        alt_symbol: str,
        alt_candles: List[Candle],
        btc_candles: List[Candle],
        lookback_periods: int = 4, # e.g. 20 minutes on 5m candles
    ) -> DivergenceResult:
        """
        Detects if an altcoin is decoupling from BTC during a significant BTC move.
        Scenarios:
        - BTC is dumping >= min_btc_move_pct, but Altcoin is surging or holding strong (+ decoupled).
        - BTC is pumping >= min_btc_move_pct, but Altcoin is selling off heavily (- decoupled).
        """
        if len(alt_candles) < lookback_periods + 1 or len(btc_candles) < lookback_periods + 1:
            return DivergenceResult(
                is_divergent=False,
                divergence_type=DivergenceType.NONE,
                reference_symbol="BTC/USDT",
                asset_price=alt_candles[-1].close if alt_candles else 0.0,
                reference_price=btc_candles[-1].close if btc_candles else 0.0,
                asset_move_pct=0.0,
                reference_move_pct=0.0,
                spread_or_gap_pct=0.0,
                details="Insufficient candle history",
            )

        alt_start = alt_candles[-lookback_periods - 1].close
        alt_current = alt_candles[-1].close
        btc_start = btc_candles[-lookback_periods - 1].close
        btc_current = btc_candles[-1].close

        if alt_start <= 0 or btc_start <= 0:
            return DivergenceResult(
                is_divergent=False,
                divergence_type=DivergenceType.NONE,
                reference_symbol="BTC/USDT",
                asset_price=alt_current,
                reference_price=btc_current,
                asset_move_pct=0.0,
                reference_move_pct=0.0,
                spread_or_gap_pct=0.0,
                details="Zero baseline price",
            )

        alt_move_pct = ((alt_current - alt_start) / alt_start) * 100.0
        btc_move_pct = ((btc_current - btc_start) / btc_start) * 100.0
        divergence_delta = alt_move_pct - btc_move_pct

        # Check if BTC had a meaningful directional impulse
        btc_significant = abs(btc_move_pct) >= self.min_btc_move_pct

        # Check decoupling condition:
        # 1. Opposite direction with magnitude (e.g. BTC -2% and Alt +3%)
        # 2. Extreme outperformance/underperformance delta
        is_decoupled = False
        details = ""

        if btc_significant and (alt_move_pct * btc_move_pct < 0):
            # Strict opposite direction
            if abs(divergence_delta) >= self.min_alt_divergence_pct:
                is_decoupled = True
                details = (
                    f"Inverse Decoupling: {alt_symbol} moved {alt_move_pct:+.2f}% "
                    f"while BTC moved {btc_move_pct:+.2f}% (Spread: {divergence_delta:+.2f}%)"
                )
        elif btc_significant and abs(divergence_delta) >= (self.min_alt_divergence_pct * 1.5):
            # Extreme velocity decoupling in same direction
            is_decoupled = True
            details = (
                f"Velocity Decoupling: {alt_symbol} moved {alt_move_pct:+.2f}% "
                f"outpacing BTC {btc_move_pct:+.2f}% by {abs(divergence_delta):.2f}%"
            )

        return DivergenceResult(
            is_divergent=is_decoupled,
            divergence_type=DivergenceType.ALTCOIN_DECOUPLING if is_decoupled else DivergenceType.NONE,
            reference_symbol="BTC/USDT",
            asset_price=alt_current,
            reference_price=btc_current,
            asset_move_pct=round(alt_move_pct, 2),
            reference_move_pct=round(btc_move_pct, 2),
            spread_or_gap_pct=round(divergence_delta, 2),
            details=details if is_decoupled else f"Correlated with BTC (Alt: {alt_move_pct:+.2f}%, BTC: {btc_move_pct:+.2f}%)",
        )
