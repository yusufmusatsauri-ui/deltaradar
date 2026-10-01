import sqlite3
import json
import os
import sys
import time

def save_alert(alert_data):
    db_path = os.path.join(os.path.dirname(__file__), '..', 'deltaradar.db')
    if not os.path.exists(db_path):
        db_path = 'deltaradar.db'
    if not os.path.exists(db_path):
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    alert_id = alert_data.get('id')
    ts = alert_data.get('timestamp', time.time() * 1000)
    timestamp_sec = ts / 1000.0 if ts > 1e11 else float(ts)
    symbol = alert_data.get('pair', '')
    price = float(alert_data.get('price', 0))
    pct_move = float(alert_data.get('pctMove', 0))
    triggers = json.dumps([alert_data.get('triggerLabel', 'Anomaly')])
    why = alert_data.get('headline') or alert_data.get('causeLabel') or f"{alert_data.get('triggerLabel', 'Anomaly')} at ${price:.4f}"
    direction = 'bearish' if ('down' in alert_data.get('triggerLabel', '').lower() or 'low' in alert_data.get('triggerLabel', '').lower()) else 'bullish'

    try:
        cursor.execute("""
        INSERT OR IGNORE INTO alerts (
            id, timestamp, symbol, asset_class, triggers, price, pct_move,
            volume_vs_avg, divergence_note, confidence, why_summary, breakdown, status
        ) VALUES (?, ?, ?, 'altcoin', ?, ?, ?, 1.0, '', 75, ?, '{}', 'active')
        """, (alert_id, timestamp_sec, symbol, triggers, price, pct_move, why))

        cursor.execute("""
        INSERT OR IGNORE INTO outcomes (
            alert_id, symbol, asset_class, direction, alert_timestamp, alert_price, triggers, confidence, resolved
        ) VALUES (?, ?, 'altcoin', ?, ?, ?, ?, 75, 0)
        """, (alert_id, symbol, direction, timestamp_sec, price, triggers))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        sys.stderr.write(f"Save alert err: {e}\n")
        conn.close()
        return False

if __name__ == '__main__':
    try:
        raw = sys.stdin.read()
        if raw.strip():
            data = json.loads(raw)
            ok = save_alert(data)
            print(json.dumps({"success": ok}))
        else:
            print(json.dumps({"success": False, "error": "No input"}))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
