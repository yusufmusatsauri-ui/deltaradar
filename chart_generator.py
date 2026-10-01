"""
DeltaRadar Candlestick Chart Generator for Bitget Feeds.
Renders high-resolution candlestick chart images from Bitget 1m/5m candles.
Marks:
- Trigger Candle (highlighted ring, arrow beacon, anomaly label)
- Key Levels (Breakout pivot, Support, Resistance)
- Volume Bars (with 20-MA volume benchmark line and spike ratio)
- Direct link to Bitget Spot market page
"""
import base64
import html
from typing import List, Dict, Any, Optional
from deltaradar.models import Candle

def render_candlestick_chart_svg(
    candles: List[Candle],
    symbol: str = "SOL/USDT",
    period: str = "5m",
    trigger_index: Optional[int] = None,
    breakout_level: Optional[float] = None,
    support_level: Optional[float] = None,
    resistance_level: Optional[float] = None,
    width: int = 760,
    height: int = 420,
    source_label: str = "Bitget (Direct WS/REST)",
    live_ticker_price: Optional[float] = None,
    timestamp_utc: Optional[str] = None,
    is_replay: bool = False,
) -> str:
    """
    Renders standalone, crisp SVG candlestick chart with volume bars,
    trigger candle annotation, and key level lines.
    """
    if not candles:
        # Fallback dummy candle
        candles = [
            Candle(symbol=symbol, timestamp=1000 + i * 300, open=100.0, high=102.0, low=99.0, close=101.0, volume=50.0)
            for i in range(20)
        ]

    n = len(candles)
    if trigger_index is None or trigger_index < 0 or trigger_index >= n:
        trigger_index = n - 1  # Default to most recent candle

    # Price bounds
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    if breakout_level:
        highs.append(breakout_level)
        lows.append(breakout_level)
    if support_level:
        highs.append(support_level)
        lows.append(support_level)
    if resistance_level:
        highs.append(resistance_level)
        lows.append(resistance_level)

    min_price = min(lows)
    max_price = max(highs)
    price_range = max(max_price - min_price, 0.0001)

    # Add 5% padding to price bounds
    min_price -= price_range * 0.05
    max_price += price_range * 0.05
    price_range = max_price - min_price

    # Volume bounds
    max_vol = max(max([c.volume for c in candles], default=1.0), 0.001)
    vol_20_avg = sum([c.volume for c in candles[-20:]]) / min(len(candles), 20)

    # Layout geometry
    padding_left = 60
    padding_right = 75
    padding_top = 45
    padding_bottom = 35

    chart_w = width - padding_left - padding_right
    chart_h = height - padding_top - padding_bottom

    # Split: 72% price chart, 28% volume chart
    price_h = chart_h * 0.70
    vol_h = chart_h * 0.24
    vol_top = padding_top + chart_h * 0.76

    def price_to_y(p: float) -> float:
        return padding_top + (max_price - p) / price_range * price_h

    def vol_to_h(v: float) -> float:
        return (v / max_vol) * vol_h

    candle_slot_w = chart_w / n
    candle_w = max(candle_slot_w * 0.65, 3.0)

    svg_elements = []

    # 1. Background and grid
    svg_elements.append(f'<rect width="{width}" height="{height}" fill="#0b0f19" rx="8" />')
    svg_elements.append(f'<rect x="{padding_left}" y="{padding_top}" width="{chart_w}" height="{price_h}" fill="#0d1322" stroke="#1e293b" stroke-width="1" />')
    svg_elements.append(f'<rect x="{padding_left}" y="{vol_top}" width="{chart_w}" height="{vol_h}" fill="#0a0e18" stroke="#1e293b" stroke-width="1" />')

    # Horizontal Price Gridlines (4 lines)
    for i in range(5):
        ratio = i / 4.0
        p_val = min_price + (max_price - min_price) * ratio
        y_val = padding_top + price_h - (ratio * price_h)
        p_str = f"{p_val:.2f}" if p_val < 1000 else f"{p_val:,.1f}"
        svg_elements.append(f'<line x1="{padding_left}" y1="{y_val:.1f}" x2="{width - padding_right}" y2="{y_val:.1f}" stroke="#172033" stroke-dasharray="3 3" />')
        svg_elements.append(f'<text x="{width - padding_right + 6}" y="{y_val + 4:.1f}" fill="#64748b" font-family="monospace" font-size="10">${p_str}</text>')

    # 2. Key Level Lines (Breakout, Support, Resistance)
    levels = [
        ("Breakout Pivot", breakout_level, "#06b6d4", "5 3"),
        ("Support", support_level, "#10b981", "3 3"),
        ("Resistance", resistance_level, "#f59e0b", "3 3"),
    ]

    for label, lvl, color, dash in levels:
        if lvl and min_price <= lvl <= max_price:
            y = price_to_y(lvl)
            lvl_str = f"{lvl:.2f}" if lvl < 1000 else f"{lvl:,.1f}"
            svg_elements.append(f'<g class="level-{label.lower().replace(" ", "-")}">')
            svg_elements.append(f'<title>{label}: ${lvl_str}</title>')
            svg_elements.append(f'<line x1="{padding_left}" y1="{y:.1f}" x2="{width - padding_right}" y2="{y:.1f}" stroke="{color}" stroke-dasharray="{dash}" stroke-width="1.5" />')
            # Level badge
            badge_text = f"{label} ${lvl_str}"
            badge_w = max(len(badge_text) * 5.8, 55.0)
            svg_elements.append(f'<rect x="{padding_left + 8}" y="{y - 14:.1f}" width="{badge_w:.1f}" height="14" fill="{color}" rx="2" fill-opacity="0.2" stroke="{color}" stroke-width="0.8" />')
            svg_elements.append(f'<text x="{padding_left + 12}" y="{y - 4:.1f}" fill="{color}" font-family="monospace" font-weight="bold" font-size="8.5">{badge_text}</text>')
            svg_elements.append(f'<text x="{width - padding_right + 8}" y="{y + 4:.1f}" fill="{color}" font-family="monospace" font-weight="bold" font-size="9">${lvl_str}</text>')
            svg_elements.append('</g>')

    # 3. Draw Volume Bars & Candlesticks
    ma_points = []
    vol_acc = 0.0

    for i, c in enumerate(candles):
        x_center = padding_left + i * candle_slot_w + candle_slot_w / 2.0
        is_bullish = c.close >= c.open
        candle_color = "#10b981" if is_bullish else "#ef4444"
        is_trigger = (i == trigger_index)

        # Candlestick Coordinates
        y_high = price_to_y(c.high)
        y_low = price_to_y(c.low)
        y_open = price_to_y(c.open)
        y_close = price_to_y(c.close)
        body_top = min(y_open, y_close)
        body_h = max(abs(y_close - y_open), 1.5)

        # Wick
        svg_elements.append(f'<line x1="{x_center:.1f}" y1="{y_high:.1f}" x2="{x_center:.1f}" y2="{y_low:.1f}" stroke="{candle_color}" stroke-width="1.2" />')

        # Body
        body_x = x_center - candle_w / 2.0
        svg_elements.append(f'<rect x="{body_x:.1f}" y="{body_top:.1f}" width="{candle_w:.1f}" height="{body_h:.1f}" fill="{candle_color}" stroke="{candle_color}" stroke-width="1" />')

        # Volume Bar
        v_bar_h = max(vol_to_h(c.volume), 2.0)
        v_bar_y = vol_top + vol_h - v_bar_h
        svg_elements.append(f'<rect x="{body_x:.1f}" y="{v_bar_y:.1f}" width="{candle_w:.1f}" height="{v_bar_h:.1f}" fill="{candle_color}" fill-opacity="0.7" />')

        # Moving Average point
        vol_acc += c.volume
        if i >= 4:
            subset_len = min(i + 1, 20)
            subset_avg = sum([x.volume for x in candles[i - subset_len + 1 : i + 1]]) / subset_len
            ma_y = vol_top + vol_h - vol_to_h(subset_avg)
            ma_points.append(f"{x_center:.1f},{ma_y:.1f}")

        # Highlight Trigger Candle
        if is_trigger:
            # Glow box
            glow_x = body_x - 4
            glow_y = y_high - 6
            glow_w = candle_w + 8
            glow_h = (y_low - y_high) + 12
            svg_elements.append(f'<rect x="{glow_x:.1f}" y="{glow_y:.1f}" width="{glow_w:.1f}" height="{glow_h:.1f}" fill="none" stroke="#38bdf8" stroke-width="2" stroke-dasharray="2 2" rx="4" />')
            
            # Beacon Arrow above trigger
            arrow_y = y_high - 14
            svg_elements.append(f'<polygon points="{x_center:.1f},{arrow_y + 8:.1f} {x_center - 5:.1f},{arrow_y:.1f} {x_center + 5:.1f},{arrow_y:.1f}" fill="#38bdf8" />')
            
            # Trigger Candle Badge
            badge_x = max(min(x_center - 55, width - padding_right - 110), padding_left + 5)
            svg_elements.append(f'<rect x="{badge_x:.1f}" y="{arrow_y - 18:.1f}" width="112" height="17" fill="#0284c7" rx="3" stroke="#38bdf8" stroke-width="1" />')
            svg_elements.append(f'<text x="{badge_x + 6:.1f}" y="{arrow_y - 6:.1f}" fill="#ffffff" font-family="sans-serif" font-weight="bold" font-size="9">⚡ TRIGGER CANDLE</text>')

    # 4. Volume 20-MA line
    if ma_points:
        svg_elements.append(f'<polyline points="{" ".join(ma_points)}" fill="none" stroke="#818cf8" stroke-width="1.5" stroke-opacity="0.8" />')

    # 5. Header & Branding (Price Integrity: Live Ticker Stream & Exact Timestamp)
    last_c = candles[-1]
    active_price = live_ticker_price if live_ticker_price is not None else last_c.close
    pct_change = ((active_price - candles[0].open) / candles[0].open) * 100.0
    sign = "+" if pct_change >= 0 else ""
    price_fmt = f"${active_price:.2f}" if active_price < 1000 else f"${active_price:,.2f}"

    time_tag = f" {timestamp_utc}" if timestamp_utc else ""
    is_fallback = "fallback" in source_label.lower()
    
    # Clean pair for Bitget vs Fallback
    pair_fmt = symbol.replace("/", "").replace("-", "") if not is_fallback else symbol

    if is_replay:
        badge_text = f"⚠️ [REPLAY] {source_label}{time_tag}"
        badge_bg = "#451a03"
        badge_border = "#f59e0b"
        badge_color = "#fef08a"
    elif is_fallback:
        # Fallback source: must start with Fallback: and NEVER show Bitget
        clean_src = source_label.replace("Bitget (Direct WS/REST)", "Secondary Reference Feed")
        badge_text = f"🔄 {clean_src}{time_tag}"
        badge_bg = "#3b1e04"
        badge_border = "#d97706"
        badge_color = "#fde68a"
    else:
        label_lead = source_label if source_label else f"Bitget {pair_fmt}"
        badge_text = f"🟢 {label_lead}{time_tag} (Live Ticker)"
        badge_bg = "#0369a1"
        badge_border = "#0ea5e9"
        badge_color = "#38bdf8"

    badge_w = max(len(badge_text) * 6.2, 160.0)

    svg_elements.append(f'<text x="{padding_left}" y="24" fill="#f8fafc" font-family="sans-serif" font-weight="bold" font-size="14">{html.escape(symbol)} <tspan fill="#94a3b8" font-size="12">({period} Candles)</tspan></text>')
    svg_elements.append(f'<text x="{padding_left + 175}" y="24" fill="#38bdf8" font-family="monospace" font-weight="bold" font-size="13">{price_fmt} <tspan fill="{"#10b981" if pct_change >= 0 else "#ef4444"}" font-size="11">({sign}{pct_change:.2f}%)</tspan></text>')
    
    # Source Tag Badge
    badge_x = width - padding_right - badge_w
    svg_elements.append(f'<rect x="{badge_x:.1f}" y="10" width="{badge_w:.1f}" height="18" fill="{badge_bg}" fill-opacity="0.5" stroke="{badge_border}" stroke-width="1" rx="4" />')
    svg_elements.append(f'<text x="{badge_x + 6:.1f}" y="22" fill="{badge_color}" font-family="monospace" font-size="9" font-weight="bold">{html.escape(badge_text)}</text>')

    # Volume legend
    svg_elements.append(f'<text x="{padding_left}" y="{vol_top - 4:.1f}" fill="#64748b" font-family="monospace" font-size="9">VOL BARS (vs 20-MA: {candles[trigger_index].volume / max(vol_20_avg, 0.1):.1f}x)</text>')

    # Bitget Spot Trading URL or Fallback footnote
    if not is_fallback:
        bitget_sym = symbol.replace("/", "").replace("-", "")
        svg_elements.append(f'<text x="{width - padding_right}" y="{height - 10}" text-anchor="end" fill="#64748b" font-family="monospace" font-size="9">Bitget Market: https://www.bitget.com/spot/{bitget_sym}</text>')
    else:
        svg_elements.append(f'<text x="{width - padding_right}" y="{height - 10}" text-anchor="end" fill="#f59e0b" font-family="monospace" font-size="9">Reference Market: {html.escape(source_label)}</text>')

    svg_body = "\n".join(svg_elements)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="auto">\n{svg_body}\n</svg>'

def get_chart_data_uri(svg_content: str) -> str:
    """Converts SVG string to Base64 Data URI suitable for <img src="..." />."""
    b64 = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"
