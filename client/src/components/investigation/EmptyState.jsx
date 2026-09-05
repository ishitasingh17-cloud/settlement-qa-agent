/**
 * client/src/components/investigation/EmptyState.jsx
 * 
 * Empty state displayed before user initiates a query,
 * featuring system overview, quick-start demo cards, and operational guidance.
 */

import React from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  Clock,
  AlertOctagon,
  Scale,
  FileQuestion,
  AlertTriangle,
  ArrowRight,
  Layers,
} from 'lucide-react';

const DEMO_CARDS = [
  {
    id: 'pay_Gz8x1001',
    title: 'Clean Settlement',
    scenario: 'SC-01',
    description: 'Fully matched transaction across Gateway, Bank, and Ledger with verified UTR.',
    icon: CheckCircle2,
    color: 'text-white',
    bg: 'bg-emerald-500',
    border: 'hover:border-emerald-400',
  },
  {
    id: 'pay_Gz8x1000',
    title: 'In-Flight Settlement Delay',
    scenario: 'SC-02',
    description: 'Gateway captured payment; bank clearing record is currently pending or missing.',
    icon: Clock,
    color: 'text-white',
    bg: 'bg-amber-500',
    border: 'hover:border-amber-400',
  },
  {
    id: 'pay_Gz8x1038',
    title: 'Missing Ledger Record',
    scenario: 'SC-03',
    description: 'Nodal bank cleared funds, but internal accounting ledger record was never booked.',
    icon: FileQuestion,
    color: 'text-white',
    bg: 'bg-blue-500',
    border: 'hover:border-blue-400',
  },
  {
    id: 'pay_Gz8x1042',
    title: 'Bank Rejection',
    scenario: 'SC-04',
    description: 'Clearing bank returned explicit rejection; support script requests updated bank details.',
    icon: AlertOctagon,
    color: 'text-white',
    bg: 'bg-rose-500',
    border: 'hover:border-rose-400',
  },
  {
    id: 'pay_Gz8x1052',
    title: 'Conflicting Cross-System Evidence',
    scenario: 'SC-05',
    description: 'Status contradiction between records; system flags conflict for manual review.',
    icon: AlertTriangle,
    color: 'text-white',
    bg: 'bg-purple-500',
    border: 'hover:border-purple-400',
  },
  {
    id: 'pay_Gz8x1100',
    title: 'Insufficient Evidence',
    scenario: 'SC-06',
    description: 'Orphan bank clearing file entry without anchor gateway authorization record.',
    icon: Layers,
    color: 'text-white',
    bg: 'bg-sky-500',
    border: 'hover:border-sky-400',
  },
];

export default function EmptyState({ onSelectId }) {
  return (
    <div className="space-y-8 py-6">
      {/* Hero Welcome Card */}
      <div className="bg-surface border border-border rounded-2xl p-8 shadow-xs text-center max-w-3xl mx-auto space-y-4">
        <div className="w-12 h-12 bg-primary/10 border border-primary/20 rounded-2xl flex items-center justify-center text-primary mx-auto shadow-xs">
          <ShieldCheck className="w-6 h-6 text-primary" />
        </div>

        <h2 className="text-xl font-bold text-text-primary tracking-tight">
          Settlement Investigation Cockpit
        </h2>

        <p className="text-sm text-text-secondary max-w-xl mx-auto leading-relaxed">
          Investigate payment discrepancies across Payment Gateway, Bank Clearing, and Internal Accounting Ledger.
          Enter a Transaction ID, Order ID, Settlement Batch, Bank UTR, or ask a natural question above.
        </p>
      </div>

      {/* Interactive Canonical Demo Test Cases */}
      <div className="space-y-3 max-w-4xl mx-auto">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-text-secondary">
            Canonical Demonstration Scenarios (Click to Investigate)
          </h3>
          <span className="text-[11px] text-text-muted font-mono">101 Ingested Transactions</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {DEMO_CARDS.map((card) => {
            const Icon = card.icon;
            return (
              <button
                key={card.id}
                onClick={() => onSelectId(card.id)}
                className={`text-left p-4 rounded-xl bg-surface border border-border ${card.border} hover:shadow-xs transition-all flex flex-col justify-between group`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className={`p-1.5 rounded-lg ${card.bg} shadow-2xs`}>
                      <Icon className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-[10px] font-mono text-text-muted px-1.5 py-0.5 rounded bg-surface-muted border border-border">
                      {card.scenario}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-xs font-bold text-text-primary group-hover:text-primary transition-colors">
                      {card.title}
                    </h4>
                    <span className="text-[11px] font-mono text-text-muted block mt-0.5">
                      {card.id}
                    </span>
                  </div>

                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    {card.description}
                  </p>
                </div>

                <div className="mt-3 pt-2 border-t border-border-subtle flex items-center justify-between text-[11px] text-primary font-semibold">
                  <span>Run Investigation</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
