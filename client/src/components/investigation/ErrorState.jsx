/**
 * client/src/components/investigation/ErrorState.jsx
 * 
 * Informative Error State for 404 (Not Found), 400 (Bad Request), and 500 (API Error)
 * with constructive remediation guidance and quick links to valid transactions.
 */

import React from 'react';
import { SearchX, AlertTriangle, WifiOff, RefreshCw } from 'lucide-react';

const RECOVERY_SUGGESTIONS = [
  { id: 'pay_Gz8x1001', label: 'Clean Settlement' },
  { id: 'pay_Gz8x1000', label: 'Delayed Settlement' },
  { id: 'pay_Gz8x1042', label: 'Bank Rejection' },
  { id: 'pay_Gz8x1052', label: 'Conflicting Evidence' },
];

export default function ErrorState({ error, onRetryQuery }) {
  if (!error) return null;

  const isNetworkError = error.code === 'NETWORK_ERROR' || error.status === 0;
  const isNotFound = error.status === 404 || error.code === 'NOT_FOUND';

  return (
    <div className="bg-surface border border-border rounded-2xl p-8 shadow-xs max-w-xl mx-auto text-center space-y-5 animate-in fade-in duration-200">
      <div
        className={`w-12 h-12 rounded-2xl flex items-center justify-center mx-auto ${
          isNetworkError
            ? 'bg-amber-950/40 text-amber-400 border border-amber-800/40'
            : isNotFound
            ? 'bg-blue-950/40 text-blue-400 border border-blue-800/40'
            : 'bg-rose-950/40 text-rose-400 border border-rose-800/40'
        }`}
      >
        {isNetworkError ? (
          <WifiOff className="w-6 h-6" />
        ) : isNotFound ? (
          <SearchX className="w-6 h-6" />
        ) : (
          <AlertTriangle className="w-6 h-6" />
        )}
      </div>

      <div className="space-y-2">
        <h3 className="text-lg font-bold text-text-primary tracking-tight">
          {isNetworkError
            ? 'Backend Server Unreachable'
            : isNotFound
            ? 'Transaction Identifier Not Found'
            : 'Investigation Request Failed'}
        </h3>
        <p className="text-xs text-text-secondary leading-relaxed max-w-md mx-auto font-sans">
          {isNetworkError
            ? 'Unable to connect to the Settlement Investigation API on http://127.0.0.1:8000. Please start the backend service using python -m server.main.'
            : isNotFound
            ? `We searched Gateway, Bank, and Ledger datasets but found no record matching "${error.query}". Please verify the identifier.`
            : error.message}
        </p>
      </div>

      {isNetworkError && (
        <div className="pt-2">
          <button
            onClick={() => onRetryQuery(error.query || 'pay_Gz8x1001')}
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-primary text-white text-xs font-semibold hover:bg-primary/90 transition-colors shadow-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Connection</span>
          </button>
        </div>
      )}

      {/* Recovery Links */}
      <div className="pt-4 border-t border-border space-y-2">
        <span className="text-[11px] font-semibold text-text-muted block">
          Try investigating a verified synthetic transaction:
        </span>
        <div className="flex flex-wrap justify-center gap-2">
          {RECOVERY_SUGGESTIONS.map((rec) => (
            <button
              key={rec.id}
              onClick={() => onRetryQuery(rec.id)}
              className="px-3 py-1 rounded-lg bg-surface-muted hover:bg-ai-tint border border-border hover:border-primary/40 text-xs font-mono text-text-primary hover:text-primary transition-colors flex items-center space-x-1"
            >
              <span>{rec.id}</span>
              <span className="text-[10px] text-text-muted font-sans">({rec.label})</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
