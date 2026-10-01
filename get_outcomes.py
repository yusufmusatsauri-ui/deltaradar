import sqlite3
import json
import os
import sys
from datetime import datetime, timezone

def format_utc_timestamp(ts):
    if not ts:
        return "--:--:-- UTC"
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

def format_utc_time_only(ts):
    if not ts:
        return "--:--:-- UTC"
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%H:%M:%S UTC")

def get_outcomes():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'deltaradar.db')
    if not os.path.exists(db_path):
        db_path = 'deltaradar.db'
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
    SELECT 
        o.alert_id,
        o.symbol,
        o.asset_class,
        o.direction,
        o.alert_timestamp,
        o.alert_price,
        o.price_1h,
        o.move_pct_1h,
        o.hit_1h,
        o.price_4h,
        o.move_pct_4h,
        o.hit_4h,
        o.price_24h,
        o.move_pct_24h,
        o.hit_24h,
        o.triggers,
        o.confidence,
        o.resolved,
        a.why_summary
    FROM outcomes o
    LEFT JOIN alerts a ON o.alert_id = a.id
    ORDER BY o.alert_timestamp DESC
    """
    try:
        cursor.execute(query)
        cols = [c[0] for c in cursor.description]
        outcomes = []
        for row in cursor.fetchall():
            item = dict(zip(cols, row))
            if isinstance(item['triggers'], str):
                try:
                    item['triggers'] = json.loads(item['triggers'])
                except:
                    item['triggers'] = [item['triggers']]

            # Compute fields required for Solved Case card & Honesty rules
            is_replay = item['alert_id'].startswith('alert-bt-') or 'replay' in item['alert_id'].lower()
            is_graded = (item['price_1h'] is not None) or (item['price_4h'] is not None) or (item['price_24h'] is not None)

            clean_pair = item['symbol'].replace('/', '')
            time_fired_utc = format_utc_timestamp(item['alert_timestamp'])
            time_only_utc = format_utc_time_only(item['alert_timestamp'])
            source_label = f"Bitget {item['symbol']} {time_only_utc}"

            # Plain verdict: "Alert preceded a X% move" or "Alert did not play out"
            has_hit = bool(item['hit_1h'] or item['hit_4h'] or item['hit_24h'])
            best_move = None
            for m in [item['move_pct_1h'], item['move_pct_4h'], item['move_pct_24h']]:
                if m is not None:
                    if best_move is None or abs(m) > abs(best_move):
                        best_move = m

            if not is_graded:
                verdict = "In progress (evaluating +1h / +4h horizons)"
                hit_status = "in_progress"
            elif has_hit:
                move_display = f"{abs(best_move):.2f}%" if best_move is not None else "significant"
                verdict = f"Alert preceded a {move_display} move"
                hit_status = "hit"
            else:
                verdict = "Alert did not play out"
                hit_status = "miss"

            # Formatted trigger type string
            trigger_list = item['triggers'] if isinstance(item['triggers'], list) else [str(item['triggers'])]
            trigger_type_str = " · ".join(trigger_list) if trigger_list else "Anomaly"

            # Cause summary
            cause_summary = item['why_summary']
            if not cause_summary or cause_summary == 'None':
                cause_summary = f"{trigger_type_str} detected at price ${item['alert_price']:.4f}."

            enriched = {
                **item,
                'pair': item['symbol'],
                'clean_pair': clean_pair,
                'is_replay': is_replay,
                'is_graded': is_graded,
                'time_fired_utc': time_fired_utc,
                'time_only_utc': time_only_utc,
                'source_label': source_label,
                'verdict': verdict,
                'hit_status': hit_status,
                'trigger_type_str': trigger_type_str,
                'cause_summary': cause_summary,
            }
            outcomes.append(enriched)

        conn.close()
        return outcomes
    except Exception as e:
        sys.stderr.write(f"Error querying outcomes: {e}\n")
        conn.close()
        return []

if __name__ == '__main__':
    data = get_outcomes()
    print(json.dumps(data))
