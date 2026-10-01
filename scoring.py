"""
DeltaRadar Confidence Scoring Engine.
Calculates a 0-100 confidence score by weighting triggers, adding synergy bonuses
for aligned triggers, and applying penalties for thin liquidity or wide spreads.
Returns complete transparent breakdown.
"""
from typing import Dict, Any, List, Optional
from deltaradar.models import ConfidenceBreakdown, TriggerWeights

class ConfidenceScorer:
    def __init__(
        self,
        weights: Optional[TriggerWeights] = None,
        synergy_two_bonus: float = 15.0,
        synergy_three_bonus: float = 25.0,
        thin_liquidity_penalty: float = 15.0,
        wide_spread_penalty: float = 12.0,
        spread_threshold_bps: float = 18.0, # 0.18%
    ):
        self.weights = weights or TriggerWeights()
        self.synergy_two_bonus = synergy_two_bonus
        self.synergy_three_bonus = synergy_three_bonus
        self.thin_liquidity_penalty = thin_liquidity_penalty
        self.wide_spread_penalty = wide_spread_penalty
        self.spread_threshold_bps = spread_threshold_bps

    def update_weights(self, new_weights: TriggerWeights):
        self.weights = new_weights

    def calculate(
        self,
        volume_ratio: float,
        is_volume_spike: bool,
        is_breakout: bool,
        breakout_penetration_pct: float,
        is_divergence: bool,
        divergence_gap_pct: float,
        is_sentiment_shift: bool,
        sentiment_delta: float,
        is_thin_liquidity: bool = False,
        spread_bps: float = 5.0,
    ) -> ConfidenceBreakdown:
        """
        Calculates 0-100 score and returns itemized breakdown.
        """
        active_triggers_count = 0

        # 1. Volume spike component (0 - 100 scaled)
        if is_volume_spike:
            active_triggers_count += 1
            # 3x volume = 75 base, 5x = 90, 7x+ = 100
            vol_score = min(100.0, 70.0 + (min(volume_ratio, 7.0) - 3.0) * 7.5)
        else:
            vol_score = 0.0

        # 2. Breakout component
        if is_breakout:
            active_triggers_count += 1
            # 0.2% penetration = 70, up to 1.5% = 100
            bo_score = min(100.0, 70.0 + (min(breakout_penetration_pct, 1.5) - 0.2) * 23.0)
        else:
            bo_score = 0.0

        # 3. Divergence component
        if is_divergence:
            active_triggers_count += 1
            # 1.2% gap = 75, 3.0%+ = 100
            div_score = min(100.0, 70.0 + (min(abs(divergence_gap_pct), 3.0) - 1.2) * 16.6)
        else:
            div_score = 0.0

        # 4. Sentiment component
        if is_sentiment_shift:
            active_triggers_count += 1
            sent_score = min(100.0, 65.0 + (min(abs(sentiment_delta), 1.0) - 0.35) * 53.8)
        else:
            sent_score = 0.0

        # Weighted base calculation
        w_vol = vol_score * self.weights.volume_spike
        w_bo = bo_score * self.weights.breakout
        w_div = div_score * self.weights.divergence
        w_sent = sent_score * self.weights.sentiment

        base_score = w_vol + w_bo + w_div + w_sent

        # Synergy bonus when 2+ triggers fire together
        synergy_bonus = 0.0
        if active_triggers_count >= 3:
            synergy_bonus = self.synergy_three_bonus
        elif active_triggers_count == 2:
            synergy_bonus = self.synergy_two_bonus

        # Penalties
        liq_penalty = self.thin_liquidity_penalty if is_thin_liquidity else 0.0
        spr_penalty = self.wide_spread_penalty if spread_bps > self.spread_threshold_bps else 0.0

        raw_final = base_score + synergy_bonus - liq_penalty - spr_penalty
        final_score = int(max(0.0, min(100.0, round(raw_final))))

        return ConfidenceBreakdown(
            base_score=round(base_score, 1),
            volume_contribution=round(w_vol, 1),
            breakout_contribution=round(w_bo, 1),
            divergence_contribution=round(w_div, 1),
            sentiment_contribution=round(w_sent, 1),
            synergy_bonus=round(synergy_bonus, 1),
            liquidity_penalty=round(liq_penalty, 1),
            spread_penalty=round(spr_penalty, 1),
            final_score=final_score,
        )
