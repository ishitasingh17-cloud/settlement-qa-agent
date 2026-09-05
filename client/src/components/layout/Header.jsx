/**
 * client/src/components/layout/Header.jsx
 * 
 * Top bar displaying brand, view switcher, environment tag, real-time backend health probe,
 * and an interactive Environment Diagnostics popover modal.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck,
  Search,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  X,
  Server,
  Database,
  Cpu,
  Lock,
  Layers,
} from 'lucide-react';
import { checkHealth } from '../../services/api';

export default function Header({
  onReset,
  currentView = 'investigate',
  onViewChange,
  exceptionCount = 17,
}) {
  const [health, setHealth] = useState(null);
  const [probing, setProbing] = useState(true);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const modalRef = useRef(null);

  const probe = async () => {
    setProbing(true);
    try {
      const data = await checkHealth();
      setHealth({ status: 'ok', data });
    } catch (err) {
      setHealth({ status: 'error', error: err.message });
    } finally {
      setProbing(false);
    }
  };

  useEffect(() => {
    probe();
    const interval = setInterval(probe, 30000);
    return () => clearInterval(interval);
  }, []);

  // Close diagnostics on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (modalRef.current && !modalRef.current.contains(event.target)) {
        setShowDiagnostics(false);
      }
    };
    if (showDiagnostics) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showDiagnostics]);

  const diag = health?.data?.diagnostics || {};
  const records = health?.data?.records_loaded || {};

  return (
    <header className="bg-surface border-b border-border px-4 sm:px-6 py-3 flex items-center justify-between shadow-xs sticky top-0 z-30">
      {/* Brand & Title */}
      <div className="flex items-center space-x-3 cursor-pointer" onClick={onReset}>
        <div className="w-9 h-9 bg-primary/10 border border-primary/25 rounded-xl flex items-center justify-center text-primary shadow-xs transition-transform hover:scale-105">
          <ShieldCheck className="w-5 h-5 text-primary" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-sm sm:text-base font-bold text-text-primary tracking-tight">
              Settlement Q&A Agent
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-surface-muted text-text-secondary border border-border rounded-full hidden sm:inline-block">
              Cockpit v1.0
            </span>
          </div>
          <p className="text-[11px] sm:text-xs text-text-secondary font-sans hidden sm:block">
            Fintech Support & Multi-System Reconciliation Console
          </p>
        </div>
      </div>

      {/* Center View Switcher Tabs */}
      <div className="flex items-center bg-surface-muted p-1 rounded-xl border border-border">
        <button
          onClick={() => onViewChange && onViewChange('investigate')}
          className={`flex items-center space-x-2 px-3 sm:px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            currentView === 'investigate'
              ? 'bg-surface text-primary shadow-xs border border-border/80 font-bold'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <Search className="w-3.5 h-3.5 text-primary" />
          <span>Investigate</span>
        </button>

        <button
          onClick={() => onViewChange && onViewChange('exceptions')}
          className={`flex items-center space-x-2 px-3 sm:px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            currentView === 'exceptions'
              ? 'bg-surface text-amber-500 shadow-xs border border-border/80 font-bold'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
          <span>Exceptions</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
            {exceptionCount}
          </span>
        </button>
      </div>

      {/* Right Controls & Health Status */}
      <div className="flex items-center space-x-2 sm:space-x-3 relative">
        {/* Sandbox Tag */}
        <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-surface-muted border border-border text-xs text-text-secondary font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
          <span>Mock Sandbox</span>
        </div>

        {/* Backend Health Badge (Clickable to open Environment Diagnostics) */}
        <button
          onClick={() => setShowDiagnostics((prev) => !prev)}
          title="Click to view Environment & Readiness Diagnostics"
          className="flex items-center space-x-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary/40 rounded-full transition-transform active:scale-95"
        >
          {probing ? (
            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-surface-muted border border-border text-text-muted font-mono text-[11px]">
              <RefreshCw className="w-3 h-3 animate-spin text-text-muted" />
              <span className="hidden sm:inline">Probing</span>
            </span>
          ) : health?.status === 'ok' ? (
            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-medium text-[11px] hover:bg-emerald-100 cursor-pointer">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span className="hidden sm:inline">Online (200 OK)</span>
            </span>
          ) : (
            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-rose-50 border border-rose-200 text-rose-700 font-medium text-[11px] hover:bg-rose-100 cursor-pointer">
              <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
              <span className="hidden sm:inline">Backend Offline</span>
            </span>
          )}
        </button>

        {/* Environment Diagnostics Popover Modal */}
        {showDiagnostics && (
          <div
            ref={modalRef}
            className="absolute right-0 top-11 w-80 sm:w-96 bg-surface border border-border rounded-2xl shadow-xl p-4 z-50 space-y-4 animate-in fade-in zoom-in-95 duration-150"
          >
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center space-x-2">
                <Server className="w-4 h-4 text-primary" />
                <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Environment Diagnostics
                </h3>
              </div>
              <button
                onClick={() => setShowDiagnostics(false)}
                className="text-text-muted hover:text-text-primary p-1 rounded-lg hover:bg-surface-muted transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between p-2 rounded-lg bg-surface-muted border border-border/50">
                <span className="text-text-secondary flex items-center space-x-1.5">
                  <Cpu className="w-3.5 h-3.5 text-primary" />
                  <span>Application Status</span>
                </span>
                <span className="font-mono text-emerald-400 font-bold bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
                  {diag.application || 'READY'}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-surface-muted border border-border/50">
                <span className="text-text-secondary flex items-center space-x-1.5">
                  <Server className="w-3.5 h-3.5 text-primary" />
                  <span>Backend API</span>
                </span>
                <span className="font-mono text-emerald-400 font-semibold bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
                  {health?.status === 'ok' ? '200 OK' : 'OFFLINE'}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-surface-muted border border-border/50">
                <span className="text-text-secondary flex items-center space-x-1.5">
                  <Database className="w-3.5 h-3.5 text-primary" />
                  <span>Dataset Records</span>
                </span>
                <span className="font-mono text-text-primary font-medium">
                  GW: {records.gateway ?? '—'} | BNK: {records.bank ?? '—'} | LED: {records.ledger ?? '—'}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-surface-muted border border-border/50">
                <span className="text-text-secondary flex items-center space-x-1.5">
                  <Layers className="w-3.5 h-3.5 text-primary" />
                  <span>Deterministic Fallback</span>
                </span>
                <span className="font-mono text-emerald-400 font-semibold bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
                  {diag.deterministic_fallback || 'READY'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1">
                <div className="p-2 rounded-lg bg-surface-muted border border-border/50">
                  <span className="text-[10px] text-text-muted block">Gemini Provider</span>
                  <span className={`text-[11px] font-mono font-medium ${diag.gemini_provider === 'CONFIGURED' ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {diag.gemini_provider === 'CONFIGURED' ? 'Active' : 'Offline / Fallback'}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-surface-muted border border-border/50">
                  <span className="text-[10px] text-text-muted block">Groq Provider</span>
                  <span className={`text-[11px] font-mono font-medium ${diag.groq_provider === 'CONFIGURED' ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {diag.groq_provider === 'CONFIGURED' ? 'Active' : 'Offline / Fallback'}
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-border flex items-center space-x-1.5 text-[11px] text-text-muted">
              <Lock className="w-3 h-3 text-emerald-400 shrink-0" />
              <span>Zero secret leakage &bull; Strict VEO Trust Boundary</span>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
