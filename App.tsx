import React, { useState } from 'react';
import { ProblemBanner } from './components/ProblemBanner';
import { TradingChartToolsPanel } from './components/TradingChartToolsPanel';
import { LiveBitgetPriceBoard } from './components/LiveBitgetPriceBoard';
import { AnomalyFeedPanel } from './components/AnomalyFeedPanel';
import { ProblemBannerAndSolvedCase } from './components/ProblemBannerAndSolvedCase';
import { SystemAuditModal } from './components/SystemAuditModal';
import { BarChart2, Code2, Download, LayoutGrid, Radio, ShieldCheck, Zap } from 'lucide-react';

export default function App() {
  // Layout: Primary screen is the Unified Asset View
  const [activeView, setActiveView] = useState<'unified' | 'price_board' | 'anomaly_feed' | 'performance'>('unified');
  const [focusedPair, setFocusedPair] = useState<string>('SOLUSDT');
  const [isAuditModalOpen, setIsAuditModalOpen] = useState<boolean>(false);

  const handleSelectPairForChart = (pair: string) => {
    setFocusedPair(pair);
    setActiveView('unified');
  };

  return (
    <div className="min-h-screen bg-[#06090e] text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* 1. Top Problem Banner (Collapsible, muted style so it doesn't compete with live data) */}
      <ProblemBanner />

      {/* 2. Professional Trading Desk Top Navigation Header */}
      <header className="border-b border-slate-800/80 bg-[#080d19]/90 backdrop-blur sticky top-0 z-40 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex flex-wrap items-center justify-between gap-3">
          {/* Brand Identity with Electric Blue Accent */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600/15 border border-blue-500/40 flex items-center justify-center text-blue-400 font-bold font-mono text-sm tracking-tight shadow-sm shadow-blue-950/50">
              ΔR
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-semibold text-slate-100 tracking-tight text-sm sm:text-base font-sans">
                  DeltaRadar
                </h1>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                  Bitget Desk
                </span>
              </div>
              <p className="text-[11px] text-slate-500 hidden sm:block font-sans">
                Professional Market Intelligence &amp; Anomaly Detection
              </p>
            </div>
          </div>

          {/* Navigation Tabs (Electric Blue Active Accent, No Rainbow Colors) */}
          <nav 
            aria-label="Trading Desk Views" 
            className="flex items-center gap-1 bg-[#050811] p-1 rounded-lg border border-slate-800/90"
          >
            {/* Primary Screen: Unified Asset View */}
            <button
              onClick={() => setActiveView('unified')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono transition-colors ${
                activeView === 'unified'
                  ? 'bg-blue-600 text-white font-semibold shadow-sm border border-blue-500'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Unified Asset</span>
            </button>

            {/* Live Price Board */}
            <button
              onClick={() => setActiveView('price_board')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono transition-colors ${
                activeView === 'price_board'
                  ? 'bg-blue-600 text-white font-semibold shadow-sm border border-blue-500'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Price Board</span>
            </button>

            {/* Anomaly Feed */}
            <button
              onClick={() => setActiveView('anomaly_feed')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono transition-colors ${
                activeView === 'anomaly_feed'
                  ? 'bg-blue-600 text-white font-semibold shadow-sm border border-blue-500'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Anomaly Feed</span>
            </button>

            {/* Performance Tracking */}
            <button
              onClick={() => setActiveView('performance')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono transition-colors ${
                activeView === 'performance'
                  ? 'bg-blue-600 text-white font-semibold shadow-sm border border-blue-500'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Performance</span>
            </button>
          </nav>

          {/* Download Repository Zip for Hackathon Submission */}
          <a
            href="/deltarader.zip"
            download="deltarader.zip"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-mono bg-blue-600/15 hover:bg-blue-600/25 text-blue-300 border border-blue-500/30 transition-colors shadow-sm"
            title="Download complete clean project zip for GitHub submission"
          >
            <Download className="w-3.5 h-3.5 text-blue-400" />
            <span className="hidden sm:inline font-semibold">deltarader.zip</span>
            <span className="sm:hidden font-semibold">ZIP</span>
          </a>
        </div>
      </header>

      {/* 3. Main Workspace Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5">
        {/* Tab 1: Primary Screen - Unified Asset View (Chart, live price, indicators, order book together) */}
        {activeView === 'unified' && (
          <TradingChartToolsPanel
            currentPair={focusedPair}
            onSelectPair={setFocusedPair}
          />
        )}

        {/* Tab 2: Live Price Board (Multi-pair Watchlist) */}
        {activeView === 'price_board' && <LiveBitgetPriceBoard />}

        {/* Tab 3: Anomaly Feed with AI Catalyst Web Grounding */}
        {activeView === 'anomaly_feed' && (
          <AnomalyFeedPanel onSelectPairForChart={handleSelectPairForChart} />
        )}

        {/* Tab 4: Performance Tracking & Graded Alert Outcomes */}
        {activeView === 'performance' && (
          <ProblemBannerAndSolvedCase 
            onSelectPairForChart={handleSelectPairForChart}
            hideProblemBanner={true}
          />
        )}
      </main>

      {/* Footer System Status Bar */}
      <footer className="border-t border-slate-800/70 bg-[#070b14] py-2 px-4 sm:px-8 text-xs font-mono text-slate-500 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-[11px]">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
          <span>DeltaRadar Institutional Terminal</span>
          <span className="text-slate-700">·</span>
          <span>Bitget Public Market Stream</span>
        </div>
        <div className="flex items-center gap-3 text-[11px]">
          <a
            href="/deltarader.zip"
            download="deltarader.zip"
            className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-blue-600/15 hover:bg-blue-600/25 text-blue-300 hover:text-white border border-blue-500/30 transition-colors"
            title="Download GitHub Submission Archive"
          >
            <Download className="w-3 h-3 text-blue-400" />
            <span>deltarader.zip</span>
          </a>
          <button
            onClick={() => setIsAuditModalOpen(true)}
            className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 text-blue-400 hover:text-blue-300 border border-slate-800 transition-colors"
          >
            <Code2 className="w-3 h-3" />
            <span>Build Status &amp; Roadmap</span>
          </button>
          <span className="text-slate-500 hidden sm:inline">
            Dark-Mode Native · Low Latency Depth &amp; Candle Engine
          </span>
        </div>
      </footer>

      {/* System Audit & Engineering Roadmap Modal */}
      <SystemAuditModal
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
      />
    </div>
  );
}
