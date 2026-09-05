/**
 * client/src/components/investigation/TimelineView.jsx
 * 
 * Signature Component: Chronological Lifecycle Timeline
 * Answers: "Where did settlement processing stop?"
 */

import React from 'react';
import { Clock, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { formatTimestamp } from '../../utils/formatters';

export default function TimelineView({ timeline }) {
  if (!timeline || timeline.length === 0) return null;

  return (
    <div className="bg-surface border border-border rounded-xl p-5 shadow-xs space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
        <div className="flex items-center space-x-2">
          <Clock className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">
            Chronological Lifecycle Timeline
          </h3>
        </div>
        <span className="text-xs text-text-muted font-mono">{timeline.length} Recorded Events</span>
      </div>

      {/* Vertical Stepper Track */}
      <div className="relative pl-6 space-y-6 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-border">
        {timeline.map((event, idx) => {
          const isBank = (event.system || '').toLowerCase().includes('bank');
          const isLedger = (event.system || '').toLowerCase().includes('ledger');
          const isError =
            (event.event || '').toLowerCase().includes('fail') ||
            (event.event || '').toLowerCase().includes('reject');

          return (
            <div key={idx} className="relative group">
              {/* Stepper Dot */}
              <div
                className={`absolute -left-[29px] top-1 w-4 h-4 rounded-full border-2 bg-surface flex items-center justify-center ${
                  isError
                    ? 'border-rose-500 text-rose-500'
                    : isBank
                    ? 'border-blue-500 text-blue-500'
                    : isLedger
                    ? 'border-emerald-500 text-emerald-500'
                    : 'border-primary text-primary'
                }`}
              >
                <div
                  className={`w-1.5 h-1.5 rounded-full ${
                    isError
                      ? 'bg-rose-500'
                      : isBank
                      ? 'bg-blue-500'
                      : isLedger
                      ? 'bg-emerald-500'
                      : 'bg-primary'
                  }`}
                />
              </div>

              {/* Event Content */}
              <div className="bg-surface-muted/60 hover:bg-surface-muted p-3 rounded-lg border border-border-subtle transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-text-primary">{event.event}</span>
                    <span
                      className={`px-1.5 py-0.2 rounded text-[10px] font-semibold uppercase tracking-wider ${
                        isBank
                          ? 'bg-blue-50 text-blue-700'
                          : isLedger
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-indigo-50 text-indigo-700'
                      }`}
                    >
                      {event.system}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono text-text-muted">
                    <span>{formatTimestamp(event.timestamp)}</span>
                    <span className="text-[10px] text-text-secondary/80 font-sans">
                      {isBank || isLedger ? '(source timezone unspecified)' : '(UTC-referenced)'}
                    </span>
                    {event.source_row_index && (
                      <span className="text-[10px] px-1 rounded bg-surface border border-border">
                        Line #{event.source_row_index}
                      </span>
                    )}
                  </div>
                </div>

                {event.details && (
                  <p className="text-xs text-text-secondary leading-relaxed font-sans">{event.details}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Provenance Footnote */}
      <div className="pt-2.5 border-t border-border-subtle text-[11px] text-text-muted font-sans leading-relaxed">
        <span className="font-semibold text-text-secondary">Timestamp Provenance:</span> Gateway timestamps are Unix epoch (UTC-referenced). Bank clearing and internal ledger records provide no source timezone metadata and are displayed as recorded without cross-system SLA assumptions.
      </div>
    </div>
  );
}
