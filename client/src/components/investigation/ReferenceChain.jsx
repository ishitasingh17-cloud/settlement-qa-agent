/**
 * client/src/components/investigation/ReferenceChain.jsx
 * 
 * Signature Visual Component: Direct Cross-System Reference Topology.
 * Accurately visualizes the hub-and-spoke relationship where gateway_transaction_id
 * directly links Bank Settlement and Ledger Entry to the Gateway Transaction,
 * rather than an artificial sequential multi-hop financial chain.
 */

import React from 'react';
import {
  GitFork,
  CheckCircle2,
  Clock,
  CreditCard,
  Building2,
  BookOpen,
  Link as LinkIcon,
} from 'lucide-react';

export default function ReferenceChain({ resolutionPath, evidencePack }) {
  if (!resolutionPath && !evidencePack) return null;

  const steps = resolutionPath?.steps || resolutionPath?.hops || [];
  const anchorId =
    resolutionPath?.resolved_gateway_transaction_id ||
    evidencePack?.gateway?.transaction_id ||
    evidencePack?.gateway?.gateway_transaction_id ||
    evidencePack?.bank?.gateway_transaction_id ||
    evidencePack?.ledger?.gateway_transaction_id ||
    '—';

  const gateway = evidencePack?.gateway || {};
  const bank = evidencePack?.bank || {};
  const ledger = evidencePack?.ledger || {};

  // Check if query was resolved from a secondary attribute
  const queryStep = steps.find(
    (s) => s.from_entity === 'QUERY' && s.lookup_key !== 'gateway_transaction_id'
  );

  return (
    <div className="bg-surface border border-border rounded-xl p-5 shadow-xs space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border-subtle">
        <div className="flex items-center space-x-2">
          <GitFork className="w-4 h-4 text-primary" />
          <div>
            <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">
              Cross-System Reference Resolution Topology
            </h3>
            <p className="text-[11px] text-text-muted">
              Direct hub-and-spoke linkage via <code className="font-mono text-primary font-semibold">gateway_transaction_id</code>
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
              gateway.present && bank.present && ledger.present
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-amber-50 text-amber-700 border border-amber-200'
            }`}
          >
            {gateway.present && bank.present && ledger.present
              ? 'Complete 3-System Linkage'
              : 'Partial / Disconnected Spoke'}
          </span>
        </div>
      </div>

      {/* Query Resolution Banner if query was by Order ID, UTR, or Settlement ID */}
      {queryStep && (
        <div className="bg-surface-muted border border-border rounded-lg px-3.5 py-2 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            <LinkIcon className="w-3.5 h-3.5 text-text-muted" />
            <span className="text-text-secondary">
              Input Query Resolved:
            </span>
            <span className="font-mono font-bold text-text-primary">
              {queryStep.lookup_key} = {queryStep.lookup_value}
            </span>
          </div>
          <div className="flex items-center space-x-1.5 text-[11px] text-primary font-mono font-semibold">
            <span>→ Anchor Transaction ID:</span>
            <span>{anchorId}</span>
          </div>
        </div>
      )}

      {/* Top Node: Gateway Transaction (Anchor Hub) */}
      <div className="flex flex-col items-center">
        <div
          className={`w-full max-w-md p-4 rounded-xl border shadow-xs transition-colors ${
            gateway.present !== false
              ? 'bg-surface border-border hover:border-primary/40'
              : 'bg-rose-50/40 border-dashed border-rose-300'
          }`}
        >
          <div className="flex items-center justify-between pb-2 border-b border-border-subtle mb-2.5">
            <div className="flex items-center space-x-2">
              <CreditCard className="w-4 h-4 text-primary" />
              <span className="text-xs font-bold text-text-primary uppercase tracking-wider">
                Gateway Transaction (Anchor Hub)
              </span>
            </div>
            {gateway.present !== false ? (
              <span className="flex items-center space-x-1 text-[10px] font-bold text-emerald-700 uppercase bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                <CheckCircle2 className="w-3 h-3" />
                <span>{gateway.status || 'captured'}</span>
              </span>
            ) : (
              <span className="text-[10px] font-bold text-rose-700 uppercase bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                Absent / Orphan
              </span>
            )}
          </div>

          <div className="space-y-1.5">
            <div className="text-xs font-mono bg-surface-muted px-2.5 py-1.5 rounded border border-border flex items-center justify-between">
              <span className="text-text-muted text-[11px]">Primary Key:</span>
              <span className="font-bold text-primary truncate">{anchorId}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
              <div>
                <span className="text-text-muted block text-[10px]">Associated Order ID</span>
                <span className="font-mono text-text-secondary truncate block font-medium">
                  {gateway.order_id || '—'}
                </span>
              </div>
              <div>
                <span className="text-text-muted block text-[10px]">Payment Instrument</span>
                <span className="font-medium text-text-secondary capitalize truncate block">
                  {gateway.method || '—'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Forking Connector Branches */}
        <div className="w-full max-w-2xl flex flex-col items-center my-2">
          <div className="w-[2px] h-4 bg-border"></div>
          <div className="relative w-full flex items-center justify-center">
            {/* Horizontal bridge connecting left and right spokes */}
            <div className="w-1/2 h-[2px] bg-border absolute top-0"></div>
          </div>
          <div className="w-full flex justify-between px-16 sm:px-28">
            <div className="w-[2px] h-4 bg-border"></div>
            <div className="w-[2px] h-4 bg-border"></div>
          </div>
          <div className="text-[10px] font-mono text-text-muted -mt-2 bg-surface px-2 border border-border rounded-full">
            Direct Linkage: gateway_transaction_id
          </div>
        </div>

        {/* Downstream Child Spokes: Bank Settlement (Left) & Ledger Entry (Right) */}
        <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Spoke 1: Bank Clearing Record */}
          <div
            className={`p-4 rounded-xl border shadow-xs flex flex-col justify-between ${
              bank.present
                ? bank.settlement_status === 'settled'
                  ? 'bg-surface border-border hover:border-emerald-300'
                  : 'bg-amber-50/30 border-amber-300'
                : 'bg-rose-50/30 border-dashed border-rose-300'
            }`}
          >
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-border-subtle mb-2.5">
                <div className="flex items-center space-x-2">
                  <Building2 className="w-4 h-4 text-primary" />
                  <span className="text-xs font-bold text-text-primary uppercase tracking-wider">
                    Bank Settlement Spoke
                  </span>
                </div>
                {bank.present ? (
                  <span
                    className={`flex items-center space-x-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                      bank.settlement_status === 'settled'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-amber-50 text-amber-700 border-amber-200'
                    }`}
                  >
                    {bank.settlement_status === 'settled' ? (
                      <CheckCircle2 className="w-3 h-3" />
                    ) : (
                      <Clock className="w-3 h-3" />
                    )}
                    <span>{bank.settlement_status}</span>
                  </span>
                ) : (
                  <span className="text-[10px] font-bold text-rose-700 uppercase bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                    Unlinked / Missing
                  </span>
                )}
              </div>

              <div className="space-y-1.5">
                <div className="text-xs font-mono bg-surface-muted px-2.5 py-1.5 rounded border border-border flex items-center justify-between">
                  <span className="text-text-muted text-[11px]">Linked via Tx ID:</span>
                  <span className="font-semibold text-text-primary truncate">{bank.gateway_transaction_id || anchorId}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                  <div>
                    <span className="text-text-muted block text-[10px]">Settlement Batch</span>
                    <span className="font-mono text-text-secondary truncate block font-medium">
                      {bank.settlement_id || '—'}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-muted block text-[10px]">Bank UTR Ref</span>
                    <span className="font-mono text-text-secondary truncate block font-semibold">
                      {bank.bank_reference_number || <span className="italic text-text-muted">Not Issued</span>}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <p className="text-[10px] text-text-muted mt-3 pt-2 border-t border-border-subtle font-sans">
              {bank.present
                ? 'Directly referenced by gateway_transaction_id in bank clearing files.'
                : 'No corresponding bank settlement record found for this transaction ID.'}
            </p>
          </div>

          {/* Spoke 2: Internal Accounting Ledger Entry */}
          <div
            className={`p-4 rounded-xl border shadow-xs flex flex-col justify-between ${
              ledger.present
                ? 'bg-surface border-border hover:border-blue-300'
                : 'bg-rose-50/30 border-dashed border-rose-300'
            }`}
          >
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-border-subtle mb-2.5">
                <div className="flex items-center space-x-2">
                  <BookOpen className="w-4 h-4 text-primary" />
                  <span className="text-xs font-bold text-text-primary uppercase tracking-wider">
                    Ledger Accounting Spoke
                  </span>
                </div>
                {ledger.present ? (
                  <span className="flex items-center space-x-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border bg-emerald-50 text-emerald-700 border-emerald-200">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>Posted</span>
                  </span>
                ) : (
                  <span className="text-[10px] font-bold text-rose-700 uppercase bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                    Unlinked / Missing
                  </span>
                )}
              </div>

              <div className="space-y-1.5">
                <div className="text-xs font-mono bg-surface-muted px-2.5 py-1.5 rounded border border-border flex items-center justify-between">
                  <span className="text-text-muted text-[11px]">Linked via Tx ID:</span>
                  <span className="font-semibold text-text-primary truncate">{ledger.gateway_transaction_id || anchorId}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                  <div>
                    <span className="text-text-muted block text-[10px]">Ledger Entry ID</span>
                    <span className="font-mono text-text-secondary truncate block font-medium">
                      {ledger.ledger_entry_id || '—'}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-muted block text-[10px]">Account Type</span>
                    <span className="font-mono text-text-secondary truncate block font-medium">
                      {ledger.account_type || '—'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <p className="text-[10px] text-text-muted mt-3 pt-2 border-t border-border-subtle font-sans">
              {ledger.present
                ? 'Directly referenced by gateway_transaction_id in accounting journal entries.'
                : 'No corresponding ledger entry found for this transaction ID.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
