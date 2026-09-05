/**
 * client/src/components/investigation/SystemInspector.jsx
 * 
 * 3-Column Evidence Inspector (Gateway | Bank | Ledger)
 * with Gross/Net reconciliation variance breakdown and physical provenance citations.
 */

import React from 'react';
import {
  CreditCard,
  Building2,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  Clock,
  Check,
  AlertTriangle,
  FileCode,
  ArrowRightLeft,
} from 'lucide-react';
import { formatCurrency, formatTimestamp } from '../../utils/formatters';

export default function SystemInspector({ evidencePack }) {
  if (!evidencePack) return null;

  const { gateway, bank, ledger, reconciliation } = evidencePack;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider flex items-center space-x-2">
          <span>Three-System Evidence Breakdown</span>
        </h3>
        <span className="text-xs text-text-secondary font-mono">
          Gateway · Bank · Ledger
        </span>
      </div>

      {/* 3-Column Evidence Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 1. Payment Gateway Card */}
        <div className="bg-surface border border-border rounded-xl p-4 shadow-xs flex flex-col justify-between">
          <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between pb-2.5 border-b border-border-subtle">
              <div className="flex items-center space-x-2">
                <CreditCard className="w-4 h-4 text-primary" />
                <span className="text-xs font-bold text-text-primary">Payment Gateway</span>
              </div>
              {gateway.present ? (
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                    gateway.status === 'captured'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-rose-50 text-rose-700 border border-rose-200'
                  }`}
                >
                  ● {gateway.status}
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                  Not Present
                </span>
              )}
            </div>

            {/* Financial Amount */}
            <div>
              <span className="text-[11px] font-semibold text-text-muted block">Gross Collected Amount</span>
              <div className="text-xl font-bold font-sans text-text-primary tracking-tight">
                {gateway.present ? formatCurrency(gateway.gross_amount, gateway.currency) : '—'}
              </div>
            </div>

            {/* Field Details */}
            {gateway.present ? (
              <dl className="grid grid-cols-2 gap-y-2 text-xs pt-1">
                <div className="col-span-2">
                  <dt className="text-text-muted text-[11px]">Transaction ID</dt>
                  <dd className="font-mono text-[11px] text-text-primary font-semibold truncate">
                    {gateway.transaction_id || gateway.gateway_transaction_id || '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-muted text-[11px]">Order ID</dt>
                  <dd className="font-mono text-[11px] text-text-primary truncate">{gateway.order_id || '—'}</dd>
                </div>
                <div>
                  <dt className="text-text-muted text-[11px]">Method · Currency</dt>
                  <dd className="font-medium text-text-primary capitalize">{gateway.method || '—'} · {gateway.currency || 'INR'}</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-text-muted text-[11px]">Created At (UTC-referenced)</dt>
                  <dd className="font-mono text-[11px] text-text-primary">{formatTimestamp(gateway.created_at || gateway.captured_at)}</dd>
                </div>
                {gateway.error_code && (
                  <div className="col-span-2 p-2 rounded bg-rose-50 border border-rose-200 text-rose-800 text-xs">
                    <span className="font-bold block">{gateway.error_code}</span>
                    <span className="text-[11px]">{gateway.error_description}</span>
                  </div>
                )}
              </dl>
            ) : (
              <div className="py-6 text-center text-xs text-text-muted italic">
                No matching record found in Gateway logs.
              </div>
            )}
          </div>

          {/* Provenance Footer */}
          {gateway.present && gateway.provenance && (
            <div className="mt-4 pt-2 border-t border-border-subtle flex items-center justify-between text-[10px] font-mono text-text-muted">
              <span>{gateway.provenance.source_file}</span>
              <span>Line #{gateway.provenance.source_row_index}</span>
            </div>
          )}
        </div>

        {/* 2. Bank Clearing Settlement Card */}
        <div className="bg-surface border border-border rounded-xl p-4 shadow-xs flex flex-col justify-between">
          <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between pb-2.5 border-b border-border-subtle">
              <div className="flex items-center space-x-2">
                <Building2 className="w-4 h-4 text-primary" />
                <span className="text-xs font-bold text-text-primary">Bank Clearing</span>
              </div>
              {bank.present ? (
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                    bank.settlement_status === 'settled'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : bank.settlement_status === 'pending'
                      ? 'bg-amber-50 text-amber-700 border border-amber-200'
                      : 'bg-rose-50 text-rose-700 border border-rose-200'
                  }`}
                >
                  ● {bank.settlement_status}
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                  Missing Record
                </span>
              )}
            </div>

            {/* Financial Amount */}
            <div>
              <span className="text-[11px] font-semibold text-text-muted block">Disbursed Net Payout</span>
              <div className="text-xl font-bold font-sans text-text-primary tracking-tight">
                {bank.present ? formatCurrency(bank.net_settlement_amount) : '—'}
              </div>
            </div>

            {/* Field Details */}
            {bank.present ? (
              <dl className="grid grid-cols-2 gap-y-2 text-xs pt-1">
                <div>
                  <dt className="text-text-muted text-[11px]">Settlement ID</dt>
                  <dd className="font-mono text-[11px] text-text-primary truncate font-semibold">{bank.settlement_id || '—'}</dd>
                </div>
                <div>
                  <dt className="text-text-muted text-[11px]">Gateway Tx ID</dt>
                  <dd className="font-mono text-[11px] text-text-primary truncate">{bank.gateway_transaction_id || '—'}</dd>
                </div>
                <div>
                  <dt className="text-text-muted text-[11px]">Bank UTR Ref</dt>
                  <dd className="font-mono text-[11px] text-text-primary truncate font-semibold">
                    {bank.bank_reference_number || <span className="italic text-text-muted">Not Issued</span>}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-muted text-[11px]">Settlement Status</dt>
                  <dd className="font-mono text-[11px] text-text-primary capitalize">{bank.settlement_status || '—'}</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-text-muted text-[11px]">Settled At (source timezone unspecified)</dt>
                  <dd className="font-mono text-[11px] text-text-primary">
                    {bank.settled_at ? formatTimestamp(bank.settled_at) : <span className="text-amber-600 dark:text-amber-400">Pending / Unrecorded</span>}
                  </dd>
                </div>
              </dl>
            ) : (
              <div className="py-6 text-center text-xs text-rose-600/80 dark:text-rose-400/80 italic">
                No matching clearing entry found in Bank settlement files.
              </div>
            )}
          </div>

          {/* Provenance Footer */}
          {bank.present && bank.provenance && (
            <div className="mt-4 pt-2 border-t border-border-subtle flex items-center justify-between text-[10px] font-mono text-text-muted">
              <span>{bank.provenance.source_file}</span>
              <span>Line #{bank.provenance.source_row_index}</span>
            </div>
          )}
        </div>

        {/* 3. Internal Accounting Ledger Card */}
        <div className="bg-surface border border-border rounded-xl p-4 shadow-xs flex flex-col justify-between">
          <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between pb-2.5 border-b border-border-subtle">
              <div className="flex items-center space-x-2">
                <BookOpen className="w-4 h-4 text-primary" />
                <span className="text-xs font-bold text-text-primary">Internal Ledger</span>
              </div>
              {ledger.present ? (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
                  ● Posted
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                  Missing Entry
                </span>
              )}
            </div>

            {/* Financial Amount */}
            <div>
              <span className="text-[11px] font-semibold text-text-muted block">Booked Journal Amount</span>
              <div className="text-xl font-bold font-sans text-text-primary tracking-tight">
                {ledger.present ? formatCurrency(ledger.ledger_amount) : '—'}
              </div>
            </div>

            {/* Field Details */}
            {ledger.present ? (
              <dl className="grid grid-cols-2 gap-y-2 text-xs pt-1">
                <div>
                  <dt className="text-text-muted text-[11px]">Ledger Entry ID</dt>
                  <dd className="font-mono text-[11px] text-text-primary truncate font-semibold">{ledger.ledger_entry_id || '—'}</dd>
                </div>
                <div>
                  <dt className="text-text-muted text-[11px]">Gateway Tx ID</dt>
                  <dd className="font-mono text-[11px] text-text-primary truncate">{ledger.gateway_transaction_id || '—'}</dd>
                </div>
                <div>
                  <dt className="text-text-muted text-[11px]">Account Type</dt>
                  <dd className="font-mono text-[11px] text-text-primary truncate">{ledger.account_type || '—'}</dd>
                </div>
                <div>
                  <dt className="text-text-muted text-[11px]">Entry Type</dt>
                  <dd className="font-semibold text-text-primary uppercase">{ledger.entry_type || '—'}</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-text-muted text-[11px]">Booked At (source timezone unspecified)</dt>
                  <dd className="font-mono text-[11px] text-text-primary">{formatTimestamp(ledger.booked_at)}</dd>
                </div>
              </dl>
            ) : (
              <div className="py-6 text-center text-xs text-rose-600/80 dark:text-rose-400/80 italic">
                No journal posting found in Internal Ledger records.
              </div>
            )}
          </div>

          {/* Provenance Footer */}
          {ledger.present && ledger.provenance && (
            <div className="mt-4 pt-2 border-t border-border-subtle flex items-center justify-between text-[10px] font-mono text-text-muted">
              <span>{ledger.provenance.source_file}</span>
              <span>Line #{ledger.provenance.source_row_index}</span>
            </div>
          )}
        </div>
      </div>

      {/* Reconciliation Summary Bar */}
      {reconciliation && (
        <div className="bg-surface-muted border border-border rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2">
            <ArrowRightLeft className="w-4 h-4 text-primary shrink-0" />
            <span className="font-semibold text-text-primary">Reconciliation Audit:</span>
          </div>

          <div className="flex flex-wrap items-center gap-4 font-mono text-[11px]">
            {/* Gross vs Net Variance */}
            <div>
              <span className="text-text-secondary mr-1.5 font-sans">Gross − Net Variance:</span>
              <span className="font-bold text-text-primary">
                {reconciliation.gross_minus_net_variance != null
                  ? formatCurrency(reconciliation.gross_minus_net_variance)
                  : '—'}
              </span>
            </div>

            {/* Bank vs Ledger Match */}
            <div>
              <span className="text-text-secondary mr-1.5 font-sans">Bank ↔ Ledger Diff:</span>
              <span
                className={`font-bold ${
                  reconciliation.bank_ledger_numeric_diff === '0.00' || reconciliation.bank_ledger_match
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-rose-600 dark:text-rose-400'
                }`}
              >
                {formatCurrency(reconciliation.bank_ledger_numeric_diff || '0.00')}
              </span>
            </div>

            {/* Status Consistency */}
            <div className="flex items-center space-x-1 font-sans">
              <span className="text-text-secondary">Status Consistency:</span>
              {reconciliation.has_status_conflict ? (
                <span className="inline-flex items-center space-x-1 text-rose-700 dark:text-rose-400 font-semibold">
                  <AlertTriangle className="w-3 h-3 text-rose-600 dark:text-rose-400" />
                  <span>MISMATCH</span>
                </span>
              ) : (
                <span className="inline-flex items-center space-x-1 text-emerald-700 dark:text-emerald-400 font-semibold">
                  <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                  <span>MATCH</span>
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
