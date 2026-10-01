# 🛰️ DeltaRadar — Market Anomaly & Divergence Detection Agent

> **Bitget Hackathon S2 Submission**  
> *Autonomous Research & Anomaly Intelligence Desk for Altcoins, Tokenized Equities, and Gold/Forex.*  
> **CRITICAL ARCHITECTURAL MANDATE:** DeltaRadar is strictly a research and market intelligence desk. It **NEVER** places trades, manages customer capital, or executes automated transactions. Human judgment is always in the loop.

---

## 📋 Table of Contents
1. [Executive Summary & Core Thesis](#-executive-summary--core-thesis)
2. [Target User & Problem Statement](#-target-user--problem-statement)
3. [Key Features](#-key-features)
4. [Architecture & System Flow](#-architecture--system-flow)
5. [Verified Market Data Integrations](#-verified-market-data-integrations)
6. [Pre-Launch Validation Framework & Shadow Portfolio](#-pre-launch-validation-framework--shadow-portfolio)
7. [Tech Stack & APIs](#-tech-stack--apis)
8. [Project Structure](#-project-structure)
9. [Getting Started & Installation](#-getting-started--installation)
10. [Environment Configuration](#-environment-configuration)
11. [Running Tests & Verification](#-running-tests--verification)
12. [Security, Privacy & Non-Execution Policy](#-security-privacy--non-execution-policy)
13. [License](#-license)

---

## 🎯 Executive Summary & Core Thesis

A solo trader cannot monitor dozens of altcoins, tokenized equities, and gold/forex around the clock. When a sudden move occurs, discovering *why* it moved or whether it matters usually happens after the setup is already gone. 

Existing solutions fail this demographic:
* **Generic Charting Platforms:** Present raw lines and candlesticks with no explanation, requiring the trader to already know what to look for.
* **Telegram "Signal" Channels:** Sell opaque buy/sell calls with zero verifiable reasoning, no audit trail, and no accountability.
* **Black-Box Autonomous Trading Bots:** Force traders to hand over custody and execution control—a leap of faith most part-time retail traders are unwilling to make.

**DeltaRadar sits squarely in the middle:**
It continuously ingests public Bitget market feeds (WebSocket and REST), calculates statistical anomalies in real time (volume spikes, key-level breakouts, and cross-asset divergence), grounds catalysts using web-grounded LLM research, and presents context-rich alerts to the human trader. Every alert is logged into an empirical audit database and graded over `+1h`, `+4h`, and `+24h` horizons to continuously calibrate trigger weights.

---

## 👤 Target User & Problem Statement

* **Profile:** Retail traders with moderate risk appetite trading part-time alongside a primary career ($1,000 to $50,000 in trading capital).
* **Style:** Multi-day swing setups and short-term trend-following (trading multiple times a week; not high-frequency scalping).
* **Multi-Asset Scope:** Active in crypto altcoins, with expanding interest in tokenized US stocks (e.g. `rNVDA`, `rTSLA`, `rAAPL`, `rMSFT`, `rMETA`, `rMU`, `rSNDK`, `rSPCX`) and gold/forex via CFDs.
* **Core Pain Point:** Cannot afford a $24,000/year Bloomberg terminal or a team of research analysts. They miss moves while away from screens, and when they do see price spikes, they cannot quickly discern genuine market catalysts from algorithmic noise.

---

## ✨ Key Features

### 1. Live Bitget Market Data Board
* Real-time price, 24h change, high/low, and volume across crypto, tokenized stocks, and gold.
* **Strict Price Integrity:** Every displayed price renders its exact source label (`Bitget [PAIR]`) and UTC timestamp.
* **10s Freshness Guard:** Automatic `LIVE` (green) / `STALE` (red) indicators prevent trading on stale or delayed cached ticks.

### 2. Interactive Candlestick Chart & Technical Indicators
* Kline visualization powered by Bitget's public API across multiple timeframes (`1m`, `5m`, `15m`, `1h`, `4h`, `1D`).
* Real-time volume histogram.
* Configurable institutional overlay indicators: Simple Moving Averages (SMA 20/50), Exponential Moving Averages (EMA 12/26), Relative Strength Index (RSI 14), and Moving Average Convergence Divergence (MACD).

### 3. Real-Time Order Book Depth View
* Live public L2 bid/ask depth ladder directly from Bitget.
* Visual depth bars with real-time Bid/Ask liquidity ratios and spread computation.

### 4. Anomaly Detection Engine
* **Volume Spike Detector:** Flags volume surges $\ge 3.0\times$ against the rolling 20-period moving average.
* **Key-Level Breakout Detector:** Identifies clean breaches above recent swing highs or below swing lows with minimum move thresholds.
* **Spam Prevention:** Enforces strict 30-minute cooldowns per pair and trigger type to avoid noisy duplicate alerts.

### 5. AI Catalyst & Web-Grounded Research
* When an anomaly triggers, an integrated Gemini research check queries real-time web news to formulate a concise 2-sentence fundamental catalyst summary.
* Every AI catalyst includes clickable, verified external source links (zero hallucinated URLs).

### 6. Human Decision Flow & Shadow Portfolio
* **Human-in-the-Loop Controls:** Every alert card features interactive `Watch`, `Ignore`, and `Snooze` controls.
* **Shadow Portfolio:** Tapping `Watch` hypothetically tracks the setup without deploying real funds. Returns, Sharpe ratio, and drawdowns are evaluated purely as hypothetical accuracy benchmarks.
* **Pre-Launch Validation:** All fired alerts are recorded in SQLite and graded automatically at `+1h`, `+4h`, and `+24h` to evaluate alert accuracy transparently.

### 7. Institutional Dark-Mode Visual Design
* Dark-mode-first aesthetic inspired by professional financial terminals (`#06090e` base, `#0a0f1d` cards).
* **Electric Blue Brand Accent:** Distinguishes DeltaRadar branding from exchange markers.
* **Color Discipline:** Green and red are strictly reserved for market states (price up/down, order book bids/asks, and hit/miss outcomes).
* **Monospace Alignment:** All numbers, prices, percentages, timestamps, and order quantities use `font-mono` for clean tabular alignment.

---

## 🏗️ Architecture & System Flow

```text
 ┌──────────────────────────────────────────────────────────────┐
 │             Bitget Public Market Data Streams                │
 │    • WebSocket (wss://ws.bitget.com/v2/ws/public)            │
 │    • REST Public API (/api/v2/spot/market/tickers & candles) │
 └──────────────────────────────┬───────────────────────────────┘
                                │ Live Ticks & Depth
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                DeltaRadar Ingest & Proxy                     │
 │    • Low-latency WebSocket router with REST fallback         │
 │    • 10s Staleness Guard & Price Integrity Attribution       │
 └──────────────────────────────┬───────────────────────────────┘
                                │ Normalized Feed
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                 Statistical Anomaly Engine                   │
 │    • Volume Spike Detector (>3x 20-MA)                       │
 │    • Key-Level Breakout Detector (Swing High/Low breaches)   │
 │    • Divergence Engine (Tokenized vs. underlying spread)     │
 └──────────────────────────────┬───────────────────────────────┘
                                │ Candidate Anomaly (Cooldown: 30m)
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │            AI Catalyst Engine (Gemini 2.5/Flash)             │
 │    • Web Search Grounding (Live Financial News RSS)          │
 │    • 2-Sentence Fundamental Explanation + Clickable Sources  │
 └──────────────────────────────┬───────────────────────────────┘
                                │ Context-Rich Alert
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │            Trader Desk UI & Human Decision Loop              │
 │    • Live Price Board · Interactive Chart · Order Book Depth │
 │    • Human Action: [ Watch ] / [ Ignore ] / [ Snooze ]       │
 └──────────────────────────────┬───────────────────────────────┘
                                │ Watched Alerts
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │      Shadow Portfolio & Multi-Horizon Outcome Grading        │
 │    • Auto-graded at +1h, +4h, +24h against Bitget spot data  │
 │    • SQLite Persistence & Weekly Trigger Weight Recalibration│
 └──────────────────────────────────────────────────────────────┘
```

---

## 📈 Verified Market Data Integrations

DeltaRadar connects exclusively to official public market data feeds on Bitget. No mock or fabricated data is permitted.

### Supported Asset Classes:
1. **Crypto Altcoins:** `SOL/USDT`, `BTC/USDT`, `ETH/USDT`, `SUI/USDT`, `AVAX/USDT`, `DOGE/USDT`, `NEAR/USDT`, `LINK/USDT`, `ARB/USDT`.
2. **Tokenized US Equities:** Exact official Bitget spot format (`r` prefix + `USDT` quote):
   * `RNVDAUSDT` &rarr; NVIDIA Corp
   * `RMUUSDT` &rarr; Micron Technology
   * `RSNDKUSDT` &rarr; SanDisk Corp
   * `RMETAUSDT` &rarr; Meta Platforms
   * `RMSFTUSDT` &rarr; Microsoft Corp
   * `RAAPLUSDT` &rarr; Apple Inc
   * `RSPCXUSDT` &rarr; SpaceX Tokenized Stock
   * `RTSLAUSDT` &rarr; Tesla Inc
3. **Gold & Forex:** `PAXGUSDT` (PAX Gold Spot), `XAUUSDT` (Gold Contract), `EUR/USD`.

---

## 📊 Pre-Launch Validation Framework & Shadow Portfolio

DeltaRadar is currently in its pre-launch build stage. Performance figures reflect the validation framework rather than historical fund execution:
* **Zero Capital Deployed:** Total costs incurred = $0.00. No liquidation risk.
* **Core Benchmark:** Alert accuracy (% of alerts hitting target thresholds at +1h, +4h, and +24h), tracked through the **Shadow Portfolio** (hypothetical positions opened only when the human trader selects `Watch`).
* **Self-Calibration:** Weekly empirical evaluation recalibrates trigger weights to favor detectors with proven real-world hit rates.
* **Target Activation Signals:** Alerts sent per day, Watch/Ignore/Snooze ratio, catalyst lookup frequency, and weekly active Telegram retention.

---

## 🛠️ Tech Stack & APIs

* **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Lucide React icons.
* **Backend:** Node.js, Express, WebSocket (`ws`), SQLite3.
* **AI & Web Grounding:** Google Gemini API (`@google/genai`), Google News RSS for live market headline retrieval.
* **Market Feeds:** Bitget Public WebSocket (`wss://ws.bitget.com/v2/ws/public`) & Public REST API endpoints.
* **Python Engine (Optional CLI):** Python 3.10+, PyYAML, aiohttp, SQLite3.

---

## 📂 Project Structure

```text
├── src/
│   ├── components/
│   │   ├── AddAssetModal.tsx              # Asset catalog modal with Bitget verification
│   │   ├── AnomalyFeedPanel.tsx           # Live alert cards with human decision controls
│   │   ├── AssetBadge.tsx                 # Standardized ticker, logo, and asset-class tags
│   │   ├── LiveBitgetPriceBoard.tsx       # Live multi-pair ticker stream with staleness guard
│   │   ├── OrderBookView.tsx              # Public L2 order book depth visualization
│   │   ├── ProblemBanner.tsx              # Collapsible top mandate banner
│   │   ├── ProblemBannerAndSolvedCase.tsx # Pre-launch validation dashboard & audit table
│   │   ├── SystemAuditModal.tsx           # In-app build status and engineering audit modal
│   │   ├── TradingChart.tsx               # Candlestick chart with technical indicators
│   │   └── TradingChartToolsPanel.tsx     # Unified asset view (Chart, Price, Order Book)
│   ├── engine/
│   │   └── anomalyEngine.ts               # Core statistical detector evaluation loop
│   ├── detectors/
│   │   ├── volumeSpikeDetector.ts         # 3x 20-MA volume surge logic
│   │   ├── breakoutDetector.ts            # Swing high/low level breach logic
│   │   └── newsShiftDetector.ts           # News catalyst delta logic
│   ├── hooks/
│   │   ├── useAnomalyEngine.ts            # Alert dispatch & scanner state hook
│   │   ├── useBitgetMarketData.ts         # WebSocket ticker, candle & depth streaming hook
│   │   └── useWatchlist.ts                # Persistent multi-asset watchlist manager
│   ├── types.ts                           # Shared TypeScript models and interfaces
│   ├── App.tsx                            # Root application & terminal layout switcher
│   └── main.tsx                           # React entry point
├── server.ts                              # Express server, WebSocket ingest & Gemini AI routes
├── deltaradar/                            # Python backend engine for Telegram & CLI backtesting
│   ├── anomaly.py                         # Statistical volume & breakout detector
│   ├── divergence.py                      # Tokenized stock & BTC decoupling engine
│   ├── cause.py                           # Gemini web research cause check
│   ├── outcome_tracker.py                 # Multi-horizon (+1h/+4h/+24h) grading
│   └── telegram_bot.py                    # Telegram bot alert dispatcher
├── run.py                                 # Unified Python CLI entry point
├── config.yaml                            # System parameters, quiet hours, and thresholds
├── package.json                           # Node.js dependencies & scripts
├── tsconfig.json                          # TypeScript configuration
├── vite.config.ts                         # Vite bundler configuration
├── index.html                             # Web application HTML shell
├── .env.example                           # Template for required environment variables
├── .gitignore                             # Git ignore rules (node_modules, logs, dist)
├── LICENSE                                # MIT Open-Source License
└── README.md                              # Complete system documentation
```

---

## 🚀 Getting Started & Installation

### Prerequisites
* **Node.js** (v18.0.0 or higher)
* **npm** or **bun**
* *(Optional for Python CLI)* **Python** 3.10+ and pip

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/deltaradar.git
   cd deltaradar
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to include your `GEMINI_API_KEY` (required for AI web catalyst summaries).*

4. **Start the development server:**
   ```bash
   npm run dev
   ```
   *The application will launch on `http://localhost:3000` with the Vite dev server and Express proxy mounted.*

5. **Build for production:**
   ```bash
   npm run build
   npm run start
   ```

---

## ⚙️ Environment Configuration

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API Key for web news catalyst investigation | Required for AI summaries |
| `APP_URL` | Base hosting URL for self-referential links | `http://localhost:3000` |
| `PORT` | Local server port | `3000` |

*Note: Never commit your actual `.env` file or API keys to GitHub. `.gitignore` is configured to exclude all `.env*` files except `.env.example`.*

---

## 🧪 Running Tests & Verification

### TypeScript Lint & Typecheck
```bash
npm run lint
```

### Production Build Verification
```bash
npm run build
```

### Python Detector Unit Tests (Optional)
```bash
python3 -m unittest discover tests
```

---

## 🛡️ Security, Privacy & Non-Execution Policy

* **Strictly Non-Custodial & Non-Executing:** DeltaRadar possesses no trade execution capabilities, wallet connection logic, or exchange private API keys. It consumes only **public** market data.
* **No Secret Exposure:** Codebase is audited to ensure zero hardcoded API keys, private passwords, or environment credentials.
* **No Fabricated Prices:** If Bitget market endpoints are unreachable or delayed, components display a clear `STALE` or error indicator rather than interpolating mock prices.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
