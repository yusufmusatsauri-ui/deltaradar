"""
DeltaRadar Outcome Tracker.
Records and grades the price move after each alert at +1h, +4h, and +24h intervals.
Marks each window as HIT or MISS against direction and size thresholds.
"""
import time
from typing import Dict, Any, List, Optional
from deltaradar.models import Outcome, Alert
from deltaradar.db import Database

class OutcomeTracker:
    def __init__(
        self,
        db: Database,
        min_move_1h_pct: float = 1.2,
        min_move_4h_pct: float = 2.5,
        min_move_24h_pct: float = 4.5,
        max_adverse_1h_pct: float = 1.0,
        max_adverse_4h_pct: float = 1.8,
        max_adverse_24h_pct: float = 3.0,
    ):
        self.db = db
        self.min_move_1h_pct = min_move_1h_pct
        self.min_move_4h_pct = min_move_4h_pct
        self.min_move_24h_pct = min_move_24h_pct
        self.max_adverse_1h_pct = max_adverse_1h_pct
        self.max_adverse_4h_pct = max_adverse_4h_pct
        self.max_adverse_24h_pct = max_adverse_24h_pct

    def register_alert_for_tracking(self, alert: Alert, direction: str = "bullish") -> Outcome:
        """Called when an alert is published: creates the initial outcome record in SQLite."""
        outcome = Outcome(
            alert_id=alert.id,
            symbol=alert.symbol,
            asset_class=alert.asset_class.value if hasattr(alert.asset_class, "value") else str(alert.asset_class),
            direction=direction,
            alert_timestamp=alert.timestamp,
            alert_price=alert.price,
            triggers=alert.triggers,
            confidence=alert.confidence,
            resolved=False,
        )
        self.db.save_outcome(outcome)
        return outcome

    def evaluate_price_step(
        self,
        outcome_dict: Dict[str, Any],
        current_time: float,
        current_price: float,
    ) -> Outcome:
        """
        Updates an outcome record with current price if +1h, +4h, or +24h horizons have matured.
        """
        alert_time = outcome_dict["alert_timestamp"]
        alert_price = outcome_dict["alert_price"]
        direction = outcome_dict["direction"]
        elapsed_sec = current_time - alert_time

        # Calculate directional return %
        if direction == "bullish":
            move_pct = ((current_price - alert_price) / alert_price) * 100.0
        else:
            move_pct = ((alert_price - current_price) / alert_price) * 100.0

        p1 = outcome_dict.get("price_1h")
        m1 = outcome_dict.get("move_pct_1h")
        h1 = outcome_dict.get("hit_1h")
        
        p4 = outcome_dict.get("price_4h")
        m4 = outcome_dict.get("move_pct_4h")
        h4 = outcome_dict.get("hit_4h")
        
        p24 = outcome_dict.get("price_24h")
        m24 = outcome_dict.get("move_pct_24h")
        h24 = outcome_dict.get("hit_24h")
        
        resolved = bool(outcome_dict.get("resolved", 0))

        # Check +1h (>= 3600 seconds)
        if elapsed_sec >= 3600 and p1 is None:
            p1 = current_price
            m1 = round(move_pct, 2)
            h1 = m1 >= self.min_move_1h_pct

        # Check +4h (>= 14400 seconds)
        if elapsed_sec >= 14400 and p4 is None:
            p4 = current_price
            m4 = round(move_pct, 2)
            h4 = m4 >= self.min_move_4h_pct

        # Check +24h (>= 86400 seconds)
        if elapsed_sec >= 86400 and p24 is None:
            p24 = current_price
            m24 = round(move_pct, 2)
            h24 = m24 >= self.min_move_24h_pct
            resolved = True

        updated = Outcome(
            alert_id=outcome_dict["alert_id"],
            symbol=outcome_dict["symbol"],
            asset_class=outcome_dict["asset_class"],
            direction=outcome_dict["direction"],
            alert_timestamp=alert_time,
            alert_price=alert_price,
            price_1h=p1,
            move_pct_1h=m1,
            hit_1h=bool(h1) if h1 is not None else None,
            price_4h=p4,
            move_pct_4h=m4,
            hit_4h=bool(h4) if h4 is not None else None,
            price_24h=p24,
            move_pct_24h=m24,
            hit_24h=bool(h24) if h24 is not None else None,
            triggers=outcome_dict["triggers"],
            confidence=outcome_dict["confidence"],
            resolved=resolved,
        )

        self.db.save_outcome(updated)
        return updated
