export type AssetClass = 'altcoin' | 'forex_gold' | 'tokenized_stock';

export type HumanDecision = 'pending' | 'watch' | 'ignore' | 'snooze_1h';

export interface TradeIdea {
  direction: 'long' | 'short' | 'neutral';
  entry_zone: string;
  entry_price: number;
  invalidation_level: number;
  target_1: number;
  target_2?: number;
  reward_risk_ratio: number;
  change_mind_condition: string;
  disclaimer: string;
}

export interface DeskBrief {
  what_happened: string;
  likely_cause: string;
  divergence_status: string;
  key_levels: {
    breakout: number;
    support: number;
    resistance: number;
  };
  invalidation: string;
  compact_summary: string;
  trade_idea?: TradeIdea;
}

export interface ShadowPosition {
  id: string;
  alert_id: string;
  symbol: string;
  direction: 'long' | 'short';
  entry_price: number;
  current_price: number;
  invalidation_level: number;
  target_1: number;
  target_2?: number;
  reward_risk_ratio: number;
  status: 'open' | 'hit_target_1' | 'hit_target_2' | 'stopped_out' | 'expired_24h' | 'closed_manually';
  pnl_pct: number;
  r_multiple: number;
  opened_at: number;
  closed_at?: number;
  duration_seconds: number;
  duration_str: string;
  triggers: string[];
  asset_class: string;
  is_counterfactual: boolean;
  label: string;
  entry_source_label?: string;
  current_source_label?: string;
  is_replay?: boolean;
}

export interface ShadowPortfolioMetrics {
  total: number;
  win_rate: number;
  avg_r: number;
  total_r: number;
  max_drawdown_r: number;
  profit_factor: number;
}

export interface ShadowReportData {
  watched_metrics: ShadowPortfolioMetrics;
  ignored_metrics: ShadowPortfolioMetrics;
  open_count: number;
  open_positions: ShadowPosition[];
  by_trigger: Record<string, { count: number; wins: number; total_r: number; win_rate: number; avg_r: number }>;
  by_asset_class: Record<string, { count: number; wins: number; total_r: number; win_rate: number; avg_r: number }>;
  label: string;
}

export interface DecisionLogItem {
  id?: number;
  alert_id: string;
  symbol: string;
  decision: HumanDecision;
  decided_at: number;
  alert_price: number;
  notes?: string;
}

export interface ConfidenceBreakdown {
  base_score: number;
  volume_contribution: number;
  breakout_contribution: number;
  divergence_contribution: number;
  sentiment_contribution: number;
  synergy_bonus: number;
  liquidity_penalty: number;
  spread_penalty: number;
  final_score: number;
}

export interface BitgetCandle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  period?: string;
}

export interface BitgetFeedStatus {
  ws_connected: boolean;
  last_heartbeat: number;
  mode: 'websocket' | 'polling_fallback';
  active_pairs_count: number;
  latency_ms: number;
  source_label: string;
}

export interface OffHoursDriftInfo {
  is_drift: boolean;
  drift_pct: number;
  last_close: number;
  current_price: number;
  threshold_pct: number;
  note: string;
}

export interface AlertItem {
  id: string;
  timestamp: number;
  symbol: string;
  asset_class: AssetClass;
  triggers: string[];
  price: number;
  pct_move: number;
  volume_vs_avg: number;
  divergence_note?: string;
  confidence: number;
  why_summary: string;
  chart_link: string;
  breakdown: ConfidenceBreakdown;
  status?: string;
  brief?: DeskBrief;
  human_decision?: HumanDecision;
  source?: string;
  bitget_url?: string;
  chart_svg?: string;
  candles?: BitgetCandle[];
  session_status?: string; // e.g. "US Market Closed" or "US Market Open" or "24/7 Crypto Open"
  market_session_open?: boolean;
  off_hours_drift?: OffHoursDriftInfo;
  delivery_status?: 'delivered' | 'queued_quiet_hours';
  queued_at?: number;
  queue_reason?: string;
  price_source_label?: string; // e.g. "Bitget SOLUSDT 12:04:31 UTC" or "Fallback: NASDAQ Reference TSLA/USD 12:04:31 UTC"
  price_source?: string;
  price_timestamp_utc?: string;
  is_stale?: boolean;
  is_replay?: boolean;
  stale_warning?: string;
}

export interface MarketSessionItem {
  label: string;
  is_open: boolean;
  session_name: string;
  badge_color: string;
  off_hours: boolean;
}

export interface PairTickStatus {
  symbol: string;
  pair: string;
  price: number;
  last_tick_time: string;
  last_tick_seconds_ago: number;
  elapsed_seconds?: number;
  source_label?: string;
  is_stale: boolean;
  source: string;
}

export interface SystemHealthStatus {
  uptime_seconds: number;
  uptime_str: string;
  uptime_pct: number;
  service_status: string;
  auto_reconnect_count: number;
  silence_alarms: Array<{
    feed: string;
    silence_seconds: number;
    threshold_seconds: number;
    message: string;
  }>;
  feeds: Record<string, {
    last_tick_seconds_ago: number;
    ticks_total: number;
    healthy: boolean;
  }>;
  pair_ticks?: Record<string, PairTickStatus>;
  stale_pairs?: string[];
  staleness_guard_threshold_sec?: number;
  staleness_guard?: any;
  startup_self_test?: any;
  self_test_passed?: boolean;
  alerts_last_24h: {
    total: number;
    high_confidence: number;
    standard: number;
  };
  quiet_hours: {
    enabled: boolean;
    is_active: boolean;
    window: string;
    min_confidence: number;
    queued_count: number;
  };
  market_sessions: Record<string, MarketSessionItem>;
}

export interface MorningDigestData {
  timestamp: number;
  date_str: string;
  queued_alerts: AlertItem[];
  top_movers: Array<{ symbol: string; price: number; change_24h: number }>;
  shadow_positions: ShadowPosition[];
  markdown_content: string;
}

export interface OutcomeItem {
  alert_id: string;
  symbol: string;
  asset_class: string;
  direction: 'bullish' | 'bearish';
  alert_timestamp: number;
  alert_price: number;
  price_1h?: number;
  move_pct_1h?: number;
  hit_1h?: boolean;
  price_4h?: number;
  move_pct_4h?: number;
  hit_4h?: boolean;
  price_24h?: number;
  move_pct_24h?: number;
  hit_24h?: boolean;
  triggers: string[];
  confidence: number;
  resolved: boolean;
  human_decision?: string;
}

export interface WatchlistAsset {
  symbol: string;
  name: string;
  asset_class: AssetClass;
  price: number;
  change_24h: number;
  volume_ratio: number;
  benchmark_symbol: string;
  benchmark_price?: number;
  divergence_pct?: number;
  is_anomaly?: boolean;
  active_trigger?: string;
  source?: string;
  bitget_url?: string;
  high_24h?: number;
  low_24h?: number;
  price_source_label?: string;
  last_tick_time?: string;
  last_tick_seconds_ago?: number;
  is_stale?: boolean;
}

export interface CalibrationData {
  total_evaluated: number;
  overall_hit_rate: number;
  trigger_stats: Record<string, { hits: number; total: number }>;
  class_stats: Record<string, { hits: number; total: number }>;
  confidence_bands: Record<string, { hits: number; total: number }>;
  decisions_stats?: Record<string, { hits: number; total: number }>;
  ignored_that_played_out?: Array<{
    symbol: string;
    triggers: string[];
    confidence: number;
    move_pct: number;
  }>;
  old_weights: Record<string, number>;
  new_weights: Record<string, number>;
  changes: string[];
  report_markdown: string;
}
