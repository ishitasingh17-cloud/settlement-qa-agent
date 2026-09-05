/**
 * client/src/components/investigation/DiagnosisHeader.jsx
 * 
 * Status Banner & Confidence Meter rendering deterministic truth,
 * diagnosis code, severity, lifecycle state, and cryptographic integrity.
 */

import React, { useState } from 'react';
import { Copy, Check, Shield, Hash, Link as LinkIcon, Info } from 'lucide-react';
import {
  getDiagnosisMeta,
  getConfidenceMeta,
  getSeverityMeta,
  getStatusMeta,
} from '../../utils/formatters';

export default function DiagnosisHeader({ investigation }) {
  const [copied, setCopied] = useState(false);

  if (!investigation) return null;

  const {
    transaction_id,
    query,
    query_type,
    diagnosis,
    confidence,
    confidence_reason,
    severity,
    status,
    investigation_id,
    evidence_pack,
  } = investigation;

  const diagMeta = getDiagnosisMeta(diagnosis);
  const confMeta = getConfidenceMeta(confidence);
  const sevMeta = getSeverityMeta(severity);
  const statMeta = getStatusMeta(status);

  const IconComponent = diagMeta.icon;

  const copyId = async () => {
    try {
      await navigator.clipboard.writeText(transaction_id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const integrityHash = evidence_pack?.integrity_hash;

  // Factual evidence completeness calculation
  const gwPresent =
    evidence_pack?.gateway?.present !== false &&
    Boolean(
      evidence_pack?.gateway?.transaction_id ||
        evidence_pack?.gateway?.gateway_transaction_id
    );
  const bnkPresent = evidence_pack?.bank?.present === true;
  const ledPresent = evidence_pack?.ledger?.present === true;
  const systemsPresentCount =
    (gwPresent ? 1 : 0) + (bnkPresent ? 1 : 0) + (ledPresent ? 1 : 0);

  const missingList = [];
  if (!gwPresent) missingList.push('Gateway record');
  if (!bnkPresent) missingList.push('Bank record');
  if (!ledPresent) missingList.push('Ledger record');

  return (
    <div className="bg-surface border border-border rounded-xl p-5 shadow-xs space-y-4">
      {/* Top Banner: Anchor ID, Diagnosis Badge, and Operational Confidence */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-border-subtle">
        {/* Left Side: IDs and Status */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Canonical Transaction Identifier Pill */}
          <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-surface-muted border border-border text-sm font-mono font-semibold text-text-primary">
            <span>{transaction_id}</span>
            <button
              onClick={copyId}
              className="text-slate-700 dark:text-white hover:text-primary transition-colors p-0.5 rounded"
              title="Copy Transaction ID"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>

          {/* Resolved Query Pointer (if query differed from canonical ID) */}
          {query && query !== transaction_id && (
            <div className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md bg-surface-muted border border-border text-xs text-text-secondary font-mono">
              <LinkIcon className="w-3 h-3 text-slate-700 dark:text-white" />
              <span>Resolved from: {query}</span>
              {query_type && <span className="text-[10px] text-text-muted font-sans">({query_type})</span>}
            </div>
          )}

          {/* Primary Diagnosis Badge */}
          <div
            className={`inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full border ${diagMeta.bgColor} ${diagMeta.borderColor} ${diagMeta.textColor} text-xs font-bold tracking-wide shadow-2xs`}
          >
            <IconComponent className="w-4 h-4 shrink-0" />
            <span>{diagMeta.code}</span>
          </div>
        </div>

        {/* Right Side: Status, Severity & Confidence */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Lifecycle Status */}
          <span
            className={`px-2.5 py-1 rounded-md text-xs font-semibold border ${statMeta.bgColor} ${statMeta.borderColor} ${statMeta.textColor}`}
          >
            {statMeta.label}
          </span>

          {/* Operational Severity */}
          <span
            className={`px-2.5 py-1 rounded-md text-xs font-semibold border ${sevMeta.bgColor} ${sevMeta.borderColor} ${sevMeta.textColor}`}
          >
            Severity: {sevMeta.label}
          </span>

          {/* Confidence Meter Pill with Tooltip */}
          <div
            className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full border ${confMeta.bgColor} ${confMeta.borderColor} ${confMeta.textColor} text-xs font-semibold relative group cursor-help`}
          >
            <span className={`w-2 h-2 rounded-full ${confMeta.dotColor}`}></span>
            <span>{confMeta.label}</span>
            <Info className="w-3 h-3 text-slate-700 dark:text-white shrink-0" />

            {/* Hover Tooltip */}
            <div className="absolute right-0 top-full mt-1 hidden group-hover:block z-20 w-64 p-2.5 bg-slate-900 text-white text-[11px] font-sans font-normal rounded-lg shadow-lg">
              <p className="font-semibold mb-1 text-slate-200">Assigned Rationale:</p>
              <p className="leading-relaxed text-slate-300">{confidence_reason}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Visual Attention Block: WHAT HAPPENED? / WHY? / EVIDENCE COVERAGE */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 pt-1">
        {/* Left (8 cols): WHAT HAPPENED & WHY */}
        <div className="lg:col-span-8 space-y-3">
          <div className="bg-surface-muted/60 p-4 rounded-xl border border-border-subtle space-y-2">
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                WHAT HAPPENED?
              </span>
              <span className="text-xs font-bold text-text-primary">
                {diagMeta.label}
              </span>
            </div>
            <p className="text-xs sm:text-sm text-text-primary font-sans leading-relaxed">
              {diagMeta.description}
            </p>
            {diagnosis !== 'SUCCESSFULLY_SETTLED' && (
              <p className="text-[11px] text-text-muted font-sans pt-1 border-t border-border-subtle">
                <span className="font-semibold text-text-secondary">Root cause:</span> Not established from available dataset evidence (requires external clearing bank logs).
              </p>
            )}
          </div>

          {confidence_reason && (
            <div className="px-3.5 py-2.5 rounded-lg bg-surface border border-border-subtle text-xs flex items-start space-x-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted shrink-0 mt-0.5">
                WHY?
              </span>
              <span className="text-text-secondary font-sans leading-relaxed">
                {confidence_reason}
              </span>
            </div>
          )}
        </div>

        {/* Right (4 cols): EVIDENCE COVERAGE (3/3 systems) */}
        <div className="lg:col-span-4 bg-surface-muted/40 p-4 rounded-xl border border-border-subtle flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-border-subtle mb-2.5">
              <span className="text-xs font-bold text-text-primary uppercase tracking-wider">
                Evidence Coverage
              </span>
              <span className="font-mono text-xs font-bold text-primary">
                {systemsPresentCount} / 3 systems
              </span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              {/* Gateway System */}
              <div className="flex items-center justify-between">
                <span className="text-text-secondary font-sans">Gateway</span>
                {gwPresent ? (
                  <span className="inline-flex items-center space-x-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                    <Check className="w-3.5 h-3.5" />
                    <span>Captured</span>
                  </span>
                ) : (
                  <span className="text-rose-600 dark:text-rose-400 font-semibold">✕ Absent</span>
                )}
              </div>

              {/* Bank System */}
              <div className="flex items-center justify-between">
                <span className="text-text-secondary font-sans">Bank Rails</span>
                {bnkPresent ? (
                  <span
                    className={`inline-flex items-center space-x-1 font-semibold ${
                      evidence_pack?.bank?.settlement_status === 'settled'
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-amber-600 dark:text-amber-400'
                    }`}
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span className="capitalize">{evidence_pack?.bank?.settlement_status || 'Present'}</span>
                  </span>
                ) : (
                  <span className="text-amber-600 dark:text-amber-400 font-semibold">✕ Missing</span>
                )}
              </div>

              {/* Ledger System */}
              <div className="flex items-center justify-between">
                <span className="text-text-secondary font-sans">Ledger</span>
                {ledPresent ? (
                  <span className="inline-flex items-center space-x-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                    <Check className="w-3.5 h-3.5" />
                    <span>Posted</span>
                  </span>
                ) : (
                  <span className="text-amber-600 dark:text-amber-400 font-semibold">✕ Missing</span>
                )}
              </div>
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-border-subtle flex items-center justify-between text-[10px] font-mono text-text-muted">
            <span>VEO: {investigation_id}</span>
            {integrityHash && (
              <span title={`Full VEO Integrity Hash: ${integrityHash}`} className="flex items-center space-x-1">
                <Hash className="w-3 h-3 text-slate-700 dark:text-white" />
                <span>{integrityHash.slice(0, 8)}...</span>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
