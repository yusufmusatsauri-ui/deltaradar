"""
DeltaRadar Data Models
Structured data definitions for candles, trades, anomalies, divergences, alerts, and outcomes.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any
import time

class AssetClass(str, Enum):
    ALTCOIN = "altcoin"
    FOREX_GOLD = "forex_gold"
    TOKENIZED_STOCK = "tokenized_stock"

class AnomalyType(str, Enum):
    VOLUME_SPIKE = "volume_spike"
    BREAKOUT_HIGH = "breakout_high"
    BREAKOUT_LOW = "breakout_low"
    SENTIMENT_SHIFT = "sentiment_shift"
    DIVERGENCE = "divergence"

class DivergenceType(str, Enum):
    TOKENIZED_LAG = "tokenized_lag"
    TOKENIZED_LEAD = "tokenized_lead"
    ALTCOIN_DECOUPLING = "altcoin_decoupling"
    NONE = "none"

class HumanDecision(str, Enum):
    WATCH = "watch"
    IGNORE = "ignore"
    SNOOZE_1H = "snooze_1h"
    PENDING = "pending"

@dataclass
class Candle:
    symbol: str
    timestamp: float  # Unix timestamp in seconds
    open: float
    high: float
    low: float
    close: float
    volume: float
    period: str = "5m"  # 1m or 5m

@dataclass
class Trade:
    symbol: str
    timestamp: float
    price: float
    size: float
    side: str  # buy or sell

@dataclass
class DivergenceResult:
    is_divergent: bool
    divergence_type: DivergenceType
    reference_symbol: str
    asset_price: float
    reference_price: float
    asset_move_pct: float
    reference_move_pct: float
    spread_or_gap_pct: float
    details: str

@dataclass
class CauseInfo:
    headline: str
    summary: str
    catalyst_found: bool
    source: str = "news_llm"

@dataclass
class ConfidenceBreakdown:
    base_score: float
    volume_contribution: float
    breakout_contribution: float
    divergence_contribution: float
    sentiment_contribution: float
    synergy_bonus: float
    liquidity_penalty: float
    spread_penalty: float
    final_score: int

@dataclass
class TradeIdea:
    direction: str  # "long", "short", "neutral"
    entry_zone: str  # e.g. "$114.00 - $115.00"
    entry_price: float
    invalidation_level: float  # e.g. $111.50
    target_1: float  # e.g. $119.50
    target_2: Optional[float] = None  # e.g. $123.00
    reward_risk_ratio: float = 2.0  # e.g. 2.4 : 1
    change_mind_condition: str = ""  # "What would change my mind" (1 line)
    disclaimer: str = "Idea for human review. Not an order, not advice."

@dataclass
class DeskBrief:
    what_happened: str  # Numbers, price, volume vs avg, timeframe
    likely_cause: str   # Headline-linked or "no clear catalyst"
    divergence_status: str # Lag/lead or Decoupling stats
    key_levels: Dict[str, float] # e.g. {"breakout": 151.2, "support": 147.8, "resistance": 158.0}
    invalidation: str   # What would invalidate this read (e.g. "Close back below $148.50 on 15m")
    compact_summary: str # 1-line desk overview
    trade_idea: Optional[TradeIdea] = None

@dataclass
class ShadowPosition:
    id: str
    alert_id: str
    symbol: str
    direction: str  # "long", "short"
    entry_price: float
    current_price: float
    invalidation_level: float
    target_1: float
    target_2: Optional[float]
    reward_risk_ratio: float
    status: str = "open"  # "open", "hit_target_1", "hit_target_2", "stopped_out", "expired_24h"
    pnl_pct: float = 0.0
    r_multiple: float = 0.0
    opened_at: float = 0.0
    closed_at: Optional[float] = None
    duration_seconds: float = 0.0
    duration_str: str = "0m"
    triggers: List[str] = field(default_factory=list)
    asset_class: str = "altcoin"
    is_counterfactual: bool = False  # True if from an Ignored alert
    label: str = "Hypothetical. No real trades were placed."
    entry_source_label: str = ""   # e.g. "Bitget SOLUSDT 12:00:15 UTC"
    current_source_label: str = "" # e.g. "Bitget SOLUSDT 12:04:31 UTC"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class DecisionLog:
    alert_id: str
    symbol: str
    decision: HumanDecision
    decided_at: float
    alert_price: float
    notes: str = ""

@dataclass
class Alert:
    id: str
    timestamp: float
    symbol: str
    asset_class: AssetClass
    triggers: List[str]
    price: float
    pct_move: float
    volume_vs_avg: float
    divergence_note: str
    confidence: int
    why_summary: str
    chart_link: str
    breakdown: ConfidenceBreakdown
    status: str = "active"
    brief: Optional[DeskBrief] = None
    human_decision: HumanDecision = HumanDecision.PENDING
    source: str = "Bitget (Direct WS/REST)"
    bitget_url: str = ""
    chart_image: Optional[str] = None
    session_status: str = "US Market Closed"
    off_hours_drift: Optional[Dict[str, Any]] = None
    delivery_status: str = "delivered"
    is_replay: bool = False
    price_source_label: str = ""  # e.g. "Bitget SOLUSDT 12:04:31 UTC"
    is_stale: bool = False
    stale_warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["asset_class"] = self.asset_class.value
        d["human_decision"] = self.human_decision.value
        return d

@dataclass
class Outcome:
    alert_id: str
    symbol: str
    asset_class: str
    direction: str  # "bullish" or "bearish"
    alert_timestamp: float
    alert_price: float
    human_decision: str = "pending" # "watch", "ignore", "snooze_1h", "pending"
    
    # +1h metrics
    price_1h: Optional[float] = None
    move_pct_1h: Optional[float] = None
    hit_1h: Optional[bool] = None
    
    # +4h metrics
    price_4h: Optional[float] = None
    move_pct_4h: Optional[float] = None
    hit_4h: Optional[bool] = None
    
    # +24h metrics
    price_24h: Optional[float] = None
    move_pct_24h: Optional[float] = None
    hit_24h: Optional[bool] = None
    
    triggers: List[str] = field(default_factory=list)
    confidence: int = 0
    resolved: bool = False

@dataclass
class TriggerWeights:
    volume_spike: float = 0.35
    breakout: float = 0.30
    divergence: float = 0.25
    sentiment: float = 0.10

    def to_dict(self) -> Dict[str, float]:
        return {
            "volume_spike": round(self.volume_spike, 4),
            "breakout": round(self.breakout, 4),
            "divergence": round(self.divergence, 4),
            "sentiment": round(self.sentiment, 4),
        }
