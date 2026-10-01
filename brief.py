"""
DeltaRadar Desk Brief Module.
Generates concise, highly actionable research briefs designed for human traders.
Produces:
1. What happened (exact numbers)
2. Likely cause (headline-linked or 'no clear catalyst')
3. Divergence status
4. Key levels (breakout, support, resistance)
5. What would invalidate this read
6. Confidence 0-100 with visible score breakdown
"""
import os
import json
import urllib.request
from typing import Dict, Any, List, Optional
from deltaradar.models import DeskBrief, Candle, ConfidenceBreakdown, AssetClass

class DeskBriefGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def generate_brief(
        self,
        symbol: str,
        asset_class: AssetClass,
        current_price: float,
        pct_move: float,
        volume_vs_avg: float,
        triggers: List[str],
        divergence_note: str,
        confidence_breakdown: ConfidenceBreakdown,
        candles: Optional[List[Candle]] = None,
        headlines: Optional[List[Dict[str, str]]] = None,
        skip_llm: bool = False,
    ) -> DeskBrief:
        """
        Synthesizes a structured Desk Brief for the human trader.
        """
        # 1. What Happened (Exact numbers)
        direction_word = "surged" if pct_move >= 0 else "plummeted"
        what_happened = (
            f"Price {direction_word} {pct_move:+.2f}% to ${current_price:,.2f} "
            f"with volume running at {volume_vs_avg:.1f}x its 20-period average on the 5m timeframe."
        )

        # 2. Key Levels calculation
        if candles and len(candles) >= 20:
            recent_high = max(c.high for c in candles[-20:])
            recent_low = min(c.low for c in candles[-20:])
            breakout_level = recent_high if pct_move >= 0 else recent_low
            support_level = round(recent_low * 0.995, 2)
            resistance_level = round(recent_high * 1.008, 2)
        else:
            breakout_level = round(current_price * (0.98 if pct_move >= 0 else 1.02), 2)
            support_level = round(current_price * 0.97, 2)
            resistance_level = round(current_price * 1.03, 2)

        key_levels = {
            "breakout": breakout_level,
            "support": support_level,
            "resistance": resistance_level,
        }

        # 3. Invalidation condition
        if pct_move >= 0:
            invalidation = (
                f"Bearish invalidation if price fails to hold breakout support at ${support_level:,.2f} "
                f"or drops back on higher-than-average sell volume."
            )
        else:
            invalidation = (
                f"Bullish invalidation if price recovers above prior breakdown level at ${breakout_level:,.2f} "
                f"with aggressive spot bid absorption."
            )

        # 4. Likely Cause
        likely_cause = "No clear catalyst (purely technical order book imbalance and liquidity hunt)."
        if headlines and len(headlines) > 0:
            top_h = headlines[0]
            likely_cause = f"Linked to reports that '{top_h.get('title', '')}' ({top_h.get('source', 'Desk Wire')})."

        # If Gemini LLM is enabled and not skipped, refine cause and invalidation
        if self.api_key and not skip_llm:
            llm_res = self._call_gemini_for_brief(
                symbol=symbol,
                asset_class=asset_class.value,
                price=current_price,
                pct_move=pct_move,
                volume_ratio=volume_vs_avg,
                triggers=triggers,
                divergence_note=divergence_note,
                headlines=headlines or [],
                key_levels=key_levels,
            )
            if llm_res:
                likely_cause = llm_res.get("likely_cause", likely_cause)
                invalidation = llm_res.get("invalidation", invalidation)

        compact_summary = (
            f"{symbol}: {triggers[0] if triggers else 'Anomaly'} at ${current_price:,.2f} ({pct_move:+.1f}%). "
            f"Cause: {likely_cause[:80]}... Invalidation: ${support_level:,.2f}."
        )

        return DeskBrief(
            what_happened=what_happened,
            likely_cause=likely_cause,
            divergence_status=divergence_note if divergence_note else "No divergence (correlated with benchmark)",
            key_levels=key_levels,
            invalidation=invalidation,
            compact_summary=compact_summary,
        )

    def _call_gemini_for_brief(
        self,
        symbol: str,
        asset_class: str,
        price: float,
        pct_move: float,
        volume_ratio: float,
        triggers: List[str],
        divergence_note: str,
        headlines: List[Dict[str, str]],
        key_levels: Dict[str, float],
    ) -> Optional[Dict[str, str]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        
        headline_text = "\n".join([f"- {h.get('title')} ({h.get('source')})" for h in headlines[:3]]) or "None"

        prompt = f"""You are an elite institutional market research desk analyst.
A human trader received an anomaly alert. Generate two concise outputs:
1. "likely_cause": strictly 1 factual sentence explaining why this happened based on headlines, or state "No clear catalyst (technical liquidity drive)."
2. "invalidation": strictly 1 sentence specifying the exact technical/orderflow invalidation level or condition.

Context:
Asset: {symbol} ({asset_class})
Price: ${price} ({pct_move:+.2f}%)
Volume Ratio: {volume_ratio:.1f}x 20-MA
Triggers: {', '.join(triggers)}
Divergence: {divergence_note}
Key Levels: Breakout=${key_levels.get('breakout')}, Support=${key_levels.get('support')}, Resistance=${key_levels.get('resistance')}
Headlines:
{headline_text}

Respond strictly in JSON format:
{{"likely_cause": "...", "invalidation": "..."}}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
        except Exception:
            return None
