/**
 * client/src/components/dashboard/ExceptionSummaryCards.jsx
 * 
 * High-density macro exception metric cards derived strictly from API payload.
 */

import React from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  HelpCircle,
  AlertOctagon,
  CheckCircle2,
} from 'lucide-react';

export default function ExceptionSummaryCards({ data }) {
  if (!data) return null;

  const totalExceptions = data.total_exceptions ?? data.actionable_exceptions_count ?? 0;
  const criticalCount = data.critical_count ?? 0;
  const missingBankCount = data.missing_bank_count ?? 0;
  const discrepanciesCount = (data.bank_rejected_count || 0) + (data.conflicting_evidence_count || 0) + (data.missing_ledger_count || 0);
  const settledCount = data.settled_count ?? 0;
  const totalTransactions = data.total_transactions ?? 0;

  const cards = [
    {
      title: 'Total Exceptions',
      value: totalExceptions,
      subtitle: `Out of ${totalTransactions} total investigated`,
      icon: AlertTriangle,
      color: 'text-rose-600 dark:text-rose-400',
      bg: 'bg-rose-50',
      border: 'border-rose-200',
      badge: 'Actionable',
      badgeColor: 'bg-rose-100 text-rose-700',
    },
    {
      title: 'Critical Severity',
      value: criticalCount,
      subtitle: 'Conflicting & Insufficient Evidence',
      icon: ShieldAlert,
      color: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-50',
      border: 'border-purple-200',
      badge: 'Immediate Triage',
      badgeColor: 'bg-purple-100 text-purple-700',
    },
    {
      title: 'Missing Bank Records',
      value: missingBankCount,
      subtitle: 'Pending nodal settlement confirmation',
      icon: HelpCircle,
      color: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      badge: 'High Latency',
      badgeColor: 'bg-amber-100 text-amber-700',
    },
    {
      title: 'Rejections & Conflicts',
      value: discrepanciesCount,
      subtitle: 'Explicit bank rejects & status conflicts',
      icon: AlertOctagon,
      color: 'text-rose-600 dark:text-rose-400',
      bg: 'bg-rose-50',
      border: 'border-rose-200',
      badge: 'Escalated',
      badgeColor: 'bg-rose-100 text-rose-700',
    },
    {
      title: 'Successfully Settled',
      value: settledCount,
      subtitle: 'Fully reconciled across all rails',
      icon: CheckCircle2,
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      badge: 'Reconciled',
      badgeColor: 'bg-emerald-100 text-emerald-700',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`bg-surface border ${card.border} rounded-xl p-4 shadow-xs flex flex-col justify-between transition-all hover:shadow-sm`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-text-secondary">
                {card.title}
              </span>
              <div className={`p-1.5 rounded-lg ${card.bg} ${card.color}`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-baseline space-x-2">
                <span className="text-2xl font-bold font-mono text-text-primary tracking-tight">
                  {card.value}
                </span>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full font-sans ${card.badgeColor}`}>
                  {card.badge}
                </span>
              </div>
              <p className="text-[11px] text-text-muted leading-tight">
                {card.subtitle}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
