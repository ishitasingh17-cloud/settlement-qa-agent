/**
 * client/src/components/layout/Sidebar.jsx
 * 
 * Persistent navigation sidebar with view switcher, canonical test cases, and query history.
 */

import React from 'react';
import {
  Search,
  AlertTriangle,
  History,
  CheckCircle2,
  Clock,
  AlertOctagon,
  FileQuestion,
  Layers,
  ChevronRight,
} from 'lucide-react';

const CANONICAL_DEMOS = [
  {
    id: 'pay_Gz8x1001',
    label: 'Clean Settlement',
    scenario: 'SC-01',
    diagnosis: 'SUCCESSFULLY_SETTLED',
    icon: CheckCircle2,
    color: 'text-white',
    bg: 'bg-emerald-500',
    desc: 'Gateway captured, bank settled with UTR, ledger posted.',
  },
  {
    id: 'pay_Gz8x1000',
    label: 'In-Flight Delay',
    scenario: 'SC-02',
    diagnosis: 'MISSING_BANK_RECORD',
    icon: Clock,
    color: 'text-white',
    bg: 'bg-amber-500',
    desc: 'Payment captured; bank clearing record pending/absent.',
  },
  {
    id: 'pay_Gz8x1038',
    label: 'Missing Ledger',
    scenario: 'SC-03',
    diagnosis: 'MISSING_LEDGER_RECORD',
    icon: FileQuestion,
    color: 'text-white',
    bg: 'bg-blue-500',
    desc: 'Settled on bank rails but missing internal ledger entry.',
  },
  {
    id: 'pay_Gz8x1042',
    label: 'Bank Rejection',
    scenario: 'SC-04',
    diagnosis: 'BANK_REJECTED',
    icon: AlertOctagon,
    color: 'text-white',
    bg: 'bg-rose-500',
    desc: 'Nodal clearing bank returned an explicit rejection.',
  },
  {
    id: 'pay_Gz8x1052',
    label: 'Conflicting Evidence',
    scenario: 'SC-05',
    diagnosis: 'CONFLICTING_EVIDENCE',
    icon: AlertTriangle,
    color: 'text-white',
    bg: 'bg-purple-500',
    desc: 'Direct cross-system status contradiction detected.',
  },
  {
    id: 'pay_Gz8x1100',
    label: 'Insufficient Evidence',
    scenario: 'SC-06',
    diagnosis: 'INSUFFICIENT_EVIDENCE',
    icon: Layers,
    color: 'text-white',
    bg: 'bg-sky-500',
    desc: 'Orphan bank & ledger record without gateway anchor.',
  },
];

export default function Sidebar({
  onSelectTransaction,
  activeId,
  history = [],
  currentView = 'investigate',
  onViewChange,
  exceptionCount = 17,
}) {
  const handleSelectCanonical = (id) => {
    if (onViewChange && currentView !== 'investigate') {
      onViewChange('investigate');
    }
    onSelectTransaction(id);
  };

  return (
    <aside className="w-64 bg-surface border-r border-border flex flex-col justify-between h-[calc(100vh-61px)] sticky top-[61px] overflow-y-auto">
      <div className="p-4 space-y-6">
        {/* Navigation Sections */}
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted px-2 block mb-2">
            Navigation
          </span>
          <nav className="space-y-1">
            <button
              onClick={() => onViewChange && onViewChange('investigate')}
              className={`w-full flex items-center justify-between px-3 py-2 text-xs font-semibold rounded-lg transition-all ${
                currentView === 'investigate'
                  ? 'bg-primary/10 text-primary border border-primary/20'
                  : 'text-text-secondary hover:bg-surface-muted hover:text-text-primary'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <Search className={`w-4 h-4 ${currentView === 'investigate' ? 'text-primary' : 'text-slate-700 dark:text-white'}`} />
                <span>Investigate</span>
              </div>
              {currentView === 'investigate' && (
                <span className="w-2 h-2 rounded-full bg-primary"></span>
              )}
            </button>

            <button
              onClick={() => onViewChange && onViewChange('exceptions')}
              className={`w-full flex items-center justify-between px-3 py-2 text-xs font-semibold rounded-lg transition-all ${
                currentView === 'exceptions'
                  ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20'
                  : 'text-text-secondary hover:bg-surface-muted hover:text-text-primary'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <AlertTriangle className={`w-4 h-4 ${currentView === 'exceptions' ? 'text-amber-500' : 'text-amber-500'}`} />
                <span>Exception Dashboard</span>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-muted text-amber-600 dark:text-amber-400 border border-border">
                {exceptionCount}
              </span>
            </button>
          </nav>
        </div>

        {/* Canonical Test Scenarios */}
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted px-2 block mb-2">
            Canonical Scenarios
          </span>
          <div className="space-y-1.5">
            {CANONICAL_DEMOS.map((demo) => {
              const Icon = demo.icon;
              const isActive = activeId === demo.id && currentView === 'investigate';
              return (
                <button
                  key={demo.id}
                  onClick={() => handleSelectCanonical(demo.id)}
                  className={`w-full text-left p-2.5 rounded-lg border transition-all flex items-start space-x-2.5 ${
                    isActive
                      ? 'bg-primary/10 border-primary/40 shadow-xs'
                      : 'bg-surface hover:bg-surface-muted border-border hover:border-primary/30'
                  }`}
                >
                  <div className={`p-1.5 rounded-md ${demo.bg} mt-0.5 shadow-2xs`}>
                    <Icon className="w-3.5 h-3.5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-text-primary truncate">
                        {demo.label}
                      </span>
                      <span className="text-[10px] font-mono text-text-muted">{demo.scenario}</span>
                    </div>
                    <span className="text-[11px] font-mono text-text-secondary block truncate">
                      {demo.id}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Recent Investigations History */}
        {history.length > 0 && (
          <div>
            <div className="flex items-center justify-between px-2 mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted">
                Recent Queries
              </span>
              <History className="w-3 h-3 text-slate-700 dark:text-white" />
            </div>
            <div className="space-y-1">
              {history.map((item, idx) => (
                <button
                  key={`${item.id}-${idx}`}
                  onClick={() => handleSelectCanonical(item.id)}
                  className="w-full text-left px-2.5 py-1.5 rounded-md hover:bg-surface-muted flex items-center justify-between text-xs text-text-secondary group transition-colors"
                >
                  <span className="font-mono text-[11px] truncate">{item.id}</span>
                  <ChevronRight className="w-3 h-3 text-slate-700 dark:text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Sidebar Footer Metadata */}
      <div className="p-4 border-t border-border bg-surface-muted/30">
        <div className="text-[11px] text-text-muted space-y-1">
          <div className="flex items-center justify-between">
            <span>Deterministic Truth:</span>
            <span className="font-mono text-emerald-400 font-medium">100%</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Float Parsing:</span>
            <span className="font-mono text-emerald-400 font-medium">0.00%</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Total Dataset:</span>
            <span className="font-mono text-text-secondary">101 txns</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
