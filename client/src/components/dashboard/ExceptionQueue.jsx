/**
 * client/src/components/dashboard/ExceptionQueue.jsx
 * 
 * Operational triage queue table for flagged settlement exceptions.
 * Implements sorting, responsive card view on mobile, and zero float parsing.
 */

import React, { useState } from 'react';
import {
  ArrowUpDown,
  ChevronUp,
  ChevronDown,
  ArrowRight,
  Copy,
  Check,
  Calendar,
  AlertCircle,
} from 'lucide-react';
import {
  formatCurrency,
  formatTimestamp,
  getDiagnosisMeta,
  getSeverityMeta,
  getStatusMeta,
  getExceptionTypeMeta,
} from '../../utils/formatters';

export default function ExceptionQueue({
  exceptions = [],
  sortConfig,
  onSort,
  onSelectTransaction,
}) {
  const [copiedId, setCopiedId] = useState(null);

  const handleCopy = async (e, text) => {
    e.stopPropagation();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(text);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy ID:', err);
    }
  };

  const renderSortIcon = (field) => {
    if (sortConfig.field !== field) {
      return <ArrowUpDown className="w-3 h-3 text-slate-700 dark:text-white ml-1 inline" />;
    }
    return sortConfig.direction === 'asc' ? (
      <ChevronUp className="w-3 h-3 text-primary ml-1 inline" />
    ) : (
      <ChevronDown className="w-3 h-3 text-primary ml-1 inline" />
    );
  };

  return (
    <div className="bg-surface border border-border rounded-xl shadow-xs overflow-hidden">
      {/* Desktop Table View */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-surface-muted/60 border-b border-border text-[11px] font-bold text-text-secondary uppercase tracking-wider">
              <th
                onClick={() => onSort('transaction_id')}
                className="py-3 px-4 cursor-pointer hover:text-primary transition-colors"
              >
                <span>Transaction & Order</span>
                {renderSortIcon('transaction_id')}
              </th>
              <th
                onClick={() => onSort('diagnosis')}
                className="py-3 px-4 cursor-pointer hover:text-primary transition-colors"
              >
                <span>Discrepancy / Diagnosis</span>
                {renderSortIcon('diagnosis')}
              </th>
              <th
                onClick={() => onSort('severity')}
                className="py-3 px-3 cursor-pointer hover:text-primary transition-colors"
              >
                <span>Severity</span>
                {renderSortIcon('severity')}
              </th>
              <th className="py-3 px-3">Status</th>
              <th className="py-3 px-4">Gross Collected</th>
              <th className="py-3 px-4">Net Disbursed</th>
              <th
                onClick={() => onSort('captured_at')}
                className="py-3 px-4 cursor-pointer hover:text-primary transition-colors"
              >
                <span>Captured Timestamp</span>
                {renderSortIcon('captured_at')}
              </th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {exceptions.map((item) => {
              const diagMeta = getDiagnosisMeta(item.diagnosis);
              const DiagIcon = diagMeta.icon;
              const sevMeta = getSeverityMeta(item.severity);
              const statusMeta = getStatusMeta(item.status);
              const excMeta = getExceptionTypeMeta(item.exception_type);

              return (
                <tr
                  key={item.transaction_id}
                  onClick={() => onSelectTransaction(item.transaction_id)}
                  className="hover:bg-primary/5 transition-colors cursor-pointer group"
                >
                  {/* Transaction & Order IDs */}
                  <td className="py-3 px-4">
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-1.5 font-mono text-xs font-bold text-text-primary group-hover:text-primary">
                        <span>{item.transaction_id}</span>
                        <button
                          type="button"
                          onClick={(e) => handleCopy(e, item.transaction_id)}
                          className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-primary transition-opacity"
                          title="Copy Transaction ID"
                        >
                          {copiedId === item.transaction_id ? (
                            <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                      {item.order_id && (
                        <span className="font-mono text-[10px] text-text-muted block">
                          Order: {item.order_id}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Diagnosis & Exception Code */}
                  <td className="py-3 px-4">
                    <div className="space-y-1">
                      <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${diagMeta.bgColor} ${diagMeta.borderColor} ${diagMeta.textColor}`}>
                        <DiagIcon className="w-3 h-3" />
                        <span>{diagMeta.label}</span>
                      </span>
                      {item.exception_type && item.exception_type !== 'NONE' && (
                        <span className="font-mono text-[10px] text-text-muted block">
                          {item.exception_type}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Severity Badge */}
                  <td className="py-3 px-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${sevMeta.bgColor} ${sevMeta.borderColor} ${sevMeta.textColor}`}>
                      {sevMeta.label}
                    </span>
                  </td>

                  {/* Lifecycle Status */}
                  <td className="py-3 px-3">
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wider border ${statusMeta.bgColor} ${statusMeta.borderColor} ${statusMeta.textColor}`}>
                      {statusMeta.label}
                    </span>
                  </td>

                  {/* Gross Amount (Zero Float Rule) */}
                  <td className="py-3 px-4 font-mono font-medium text-text-primary text-xs">
                    {formatCurrency(item.gross_amount)}
                  </td>

                  {/* Net Disbursed (Zero Float Rule) */}
                  <td className="py-3 px-4 font-mono font-medium text-xs">
                    {item.net_amount !== null && item.net_amount !== undefined ? (
                      <span className="text-text-primary">{formatCurrency(item.net_amount)}</span>
                    ) : (
                      <span className="text-text-muted italic">—</span>
                    )}
                  </td>

                  {/* Captured Timestamp */}
                  <td className="py-3 px-4 text-text-secondary text-[11px] font-mono whitespace-nowrap">
                    {formatTimestamp(item.captured_at)}
                  </td>

                  {/* Action Button */}
                  <td className="py-3 px-4 text-right">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectTransaction(item.transaction_id);
                      }}
                      className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md bg-primary hover:bg-primary-dark text-white font-semibold text-[11px] shadow-2xs transition-colors cursor-pointer"
                    >
                      <span>Investigate</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Stacked Cards View */}
      <div className="md:hidden divide-y divide-border p-2 space-y-2">
        {exceptions.map((item) => {
          const diagMeta = getDiagnosisMeta(item.diagnosis);
          const DiagIcon = diagMeta.icon;
          const sevMeta = getSeverityMeta(item.severity);

          return (
            <div
              key={item.transaction_id}
              onClick={() => onSelectTransaction(item.transaction_id)}
              className="p-3 bg-surface hover:bg-surface-muted rounded-lg border border-border space-y-2.5 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-text-primary">
                  {item.transaction_id}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${sevMeta.bgColor} ${sevMeta.borderColor} ${sevMeta.textColor}`}>
                  {sevMeta.label}
                </span>
              </div>

              <div className="flex items-center space-x-1.5">
                <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${diagMeta.bgColor} ${diagMeta.borderColor} ${diagMeta.textColor}`}>
                  <DiagIcon className="w-3 h-3" />
                  <span>{diagMeta.label}</span>
                </span>
                {item.order_id && (
                  <span className="font-mono text-[10px] text-text-muted">
                    Order: {item.order_id}
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between text-xs pt-1 border-t border-border">
                <div className="space-y-0.5">
                  <span className="text-[10px] text-text-muted block">Gross / Net:</span>
                  <span className="font-mono font-bold text-text-primary">
                    {formatCurrency(item.gross_amount)} / {formatCurrency(item.net_amount)}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectTransaction(item.transaction_id);
                  }}
                  className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-md bg-primary text-white font-semibold text-xs shadow-2xs"
                >
                  <span>Investigate</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
