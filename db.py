"""
SQLite Storage Layer for DeltaRadar.
Persists alerts, outcome evaluations, calibration history, and muted symbols.
"""
import sqlite3
import json
import time
import os
from typing import List, Optional, Dict, Any, Tuple
from deltaradar.models import Alert, Outcome, TriggerWeights, ConfidenceBreakdown, AssetClass

class Database:
    def __init__(self, db_path: str = "deltaradar.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # Alerts table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                symbol TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                triggers TEXT NOT NULL,
                price REAL NOT NULL,
                pct_move REAL NOT NULL,
                volume_vs_avg REAL NOT NULL,
                divergence_note TEXT,
                confidence INTEGER NOT NULL,
                why_summary TEXT NOT NULL,
                chart_link TEXT,
                breakdown TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            )
            """)

            # Outcomes table (+1h, +4h, +24h tracking)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                alert_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                direction TEXT NOT NULL,
                alert_timestamp REAL NOT NULL,
                alert_price REAL NOT NULL,
                price_1h REAL,
                move_pct_1h REAL,
                hit_1h INTEGER,
                price_4h REAL,
                move_pct_4h REAL,
                hit_4h INTEGER,
                price_24h REAL,
                move_pct_24h REAL,
                hit_24h INTEGER,
                triggers TEXT NOT NULL,
                confidence INTEGER NOT NULL,
                resolved INTEGER DEFAULT 0,
                human_decision TEXT DEFAULT 'pending',
                FOREIGN KEY(alert_id) REFERENCES alerts(id)
            )
            """)

            # Trigger calibration history
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS calibration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                volume_spike REAL NOT NULL,
                breakout REAL NOT NULL,
                divergence REAL NOT NULL,
                sentiment REAL NOT NULL,
                report_markdown TEXT NOT NULL
            )
            """)

            # Decision Journal (Human Decisions: Watch, Ignore, Snooze)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS decision_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                decision TEXT NOT NULL,
                decided_at REAL NOT NULL,
                alert_price REAL NOT NULL,
                notes TEXT,
                FOREIGN KEY(alert_id) REFERENCES alerts(id)
            )
            """)

            # Muted assets (via /mute command)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS muted_assets (
                symbol TEXT PRIMARY KEY,
                muted_until REAL NOT NULL,
                reason TEXT
            )
            """)
            conn.commit()

    # --- Alerts ---
    def save_alert(self, alert: Alert):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO alerts (
                id, timestamp, symbol, asset_class, triggers, price, pct_move,
                volume_vs_avg, divergence_note, confidence, why_summary, chart_link, breakdown, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.id,
                alert.timestamp,
                alert.symbol,
                alert.asset_class.value if isinstance(alert.asset_class, AssetClass) else str(alert.asset_class),
                json.dumps(alert.triggers),
                alert.price,
                alert.pct_move,
                alert.volume_vs_avg,
                alert.divergence_note,
                alert.confidence,
                alert.why_summary,
                alert.chart_link,
                json.dumps(alert.breakdown.__dict__ if hasattr(alert.breakdown, "__dict__") else alert.breakdown),
                alert.status
            ))
            conn.commit()

    def get_recent_alert_for_symbol(self, symbol: str, lookback_seconds: float) -> Optional[Dict[str, Any]]:
        """Used for cooldown check: returns most recent alert within lookback."""
        cutoff = time.time() - lookback_seconds
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM alerts 
            WHERE symbol = ? AND timestamp >= ? 
            ORDER BY timestamp DESC LIMIT 1
            """, (symbol, cutoff))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["triggers"] = json.loads(d["triggers"])
                d["breakdown"] = json.loads(d["breakdown"])
                results.append(d)
            return results

    def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["triggers"] = json.loads(d["triggers"])
            d["breakdown"] = json.loads(d["breakdown"])
            return d

    # --- Outcomes ---
    def save_outcome(self, outcome: Outcome):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO outcomes (
                alert_id, symbol, asset_class, direction, alert_timestamp, alert_price,
                price_1h, move_pct_1h, hit_1h,
                price_4h, move_pct_4h, hit_4h,
                price_24h, move_pct_24h, hit_24h,
                triggers, confidence, resolved, human_decision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                outcome.alert_id,
                outcome.symbol,
                outcome.asset_class,
                outcome.direction,
                outcome.alert_timestamp,
                outcome.alert_price,
                outcome.price_1h,
                outcome.move_pct_1h,
                1 if outcome.hit_1h else (0 if outcome.hit_1h is False else None),
                outcome.price_4h,
                outcome.move_pct_4h,
                1 if outcome.hit_4h else (0 if outcome.hit_4h is False else None),
                outcome.price_24h,
                outcome.move_pct_24h,
                1 if outcome.hit_24h else (0 if outcome.hit_24h is False else None),
                json.dumps(outcome.triggers),
                outcome.confidence,
                1 if outcome.resolved else 0,
                getattr(outcome, "human_decision", "pending")
            ))
            conn.commit()

    def get_pending_outcomes(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM outcomes WHERE resolved = 0")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["triggers"] = json.loads(d["triggers"])
                results.append(d)
            return results

    def get_all_outcomes(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM outcomes ORDER BY alert_timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["triggers"] = json.loads(d["triggers"])
                results.append(d)
            return results

    # --- Calibration History & Weights ---
    def save_calibration(self, weights: TriggerWeights, report: str):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO calibration_history (
                timestamp, volume_spike, breakout, divergence, sentiment, report_markdown
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                time.time(),
                weights.volume_spike,
                weights.breakout,
                weights.divergence,
                weights.sentiment,
                report
            ))
            conn.commit()

    def get_latest_weights(self) -> Optional[TriggerWeights]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT volume_spike, breakout, divergence, sentiment 
            FROM calibration_history 
            ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return TriggerWeights(
                    volume_spike=row["volume_spike"],
                    breakout=row["breakout"],
                    divergence=row["divergence"],
                    sentiment=row["sentiment"]
                )
            return None

    # --- Muted Assets ---
    def mute_asset(self, symbol: str, duration_hours: float = 24.0, reason: str = "user_command"):
        muted_until = time.time() + (duration_hours * 3600.0)
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO muted_assets (symbol, muted_until, reason)
            VALUES (?, ?, ?)
            """, (symbol.upper(), muted_until, reason))
            conn.commit()

    def unmute_asset(self, symbol: str):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM muted_assets WHERE symbol = ?", (symbol.upper(),))
            conn.commit()

    def is_asset_muted(self, symbol: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT muted_until FROM muted_assets 
            WHERE symbol = ? AND muted_until > ?
            """, (symbol.upper(), time.time()))
            return cursor.fetchone() is not None

    def get_muted_assets(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM muted_assets WHERE muted_until > ?", (time.time(),))
            return [dict(r) for r in cursor.fetchall()]

    # --- Decision Journal (Human Desk Actions: Watch, Ignore, Snooze) ---
    def record_human_decision(
        self,
        alert_id: str,
        symbol: str,
        decision: str,
        alert_price: float = 0.0,
        notes: str = "",
    ) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            decided_at = time.time()
            cursor.execute("""
            INSERT INTO decision_journal (alert_id, symbol, decision, decided_at, alert_price, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (alert_id, symbol, decision.lower(), decided_at, alert_price, notes))
            
            # Also update outcome record with human_decision if exists
            cursor.execute("""
            UPDATE outcomes SET human_decision = ? WHERE alert_id = ?
            """, (decision.lower(), alert_id))
            conn.commit()

            return {
                "alert_id": alert_id,
                "symbol": symbol,
                "decision": decision.lower(),
                "decided_at": decided_at,
                "alert_price": alert_price,
            }

    def get_decision_journal(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM decision_journal 
            ORDER BY decided_at DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_decision_stats(self) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT decision, COUNT(*) as count FROM decision_journal GROUP BY decision")
            rows = cursor.fetchall()
            stats = {"watch": 0, "ignore": 0, "snooze_1h": 0, "total": 0}
            for r in rows:
                dec = r["decision"]
                if dec in stats:
                    stats[dec] = r["count"]
                stats["total"] += r["count"]
            return stats
