/**
 * client/src/components/investigation/ProgressLoader.jsx
 * 
 * Multi-Stage Deterministic Progress Loader
 * Displays structured multi-system correlation progress steps instead of a blank spinner.
 */

import React from 'react';
import { Loader2, CheckCircle2, Circle } from 'lucide-react';

export default function ProgressLoader({ query, stepInfo }) {
  const steps = [
    'Querying Gateway records & trace graph...',
    'Traversing multi-hop Reference Chain (Bank & Ledger)...',
    'Executing Gross/Net reconciliation & variance audit...',
    'Evaluating 11-state settlement diagnosis taxonomy...',
    'Synthesizing & validating dual-channel AI explanation...',
  ];

  const currentStep = stepInfo?.step || 1;
  const currentPercent = stepInfo?.percent || 20;

  return (
    <div className="bg-surface border border-border rounded-xl p-8 shadow-sm max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-text-primary">
            Investigating {query || 'Transaction'}...
          </h3>
          <p className="text-xs text-text-secondary mt-0.5">
            Running multi-system reference trace and deterministic reconciliation
          </p>
        </div>
        <span className="font-mono text-sm font-bold text-primary">{currentPercent}%</span>
      </div>

      {/* Progress Bar Track */}
      <div className="w-full bg-surface-muted rounded-full h-2 overflow-hidden border border-border">
        <div
          className="bg-primary h-2 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${currentPercent}%` }}
        />
      </div>

      {/* Step Checklist */}
      <div className="space-y-2.5 pt-2">
        {steps.map((text, idx) => {
          const stepNum = idx + 1;
          const isDone = stepNum < currentStep;
          const isCurrent = stepNum === currentStep;

          return (
            <div
              key={idx}
              className={`flex items-center space-x-3 text-xs p-2 rounded-lg transition-colors ${
                isCurrent
                  ? 'bg-primary/5 text-primary font-semibold border border-primary/20'
                  : isDone
                  ? 'text-text-primary'
                  : 'text-text-muted opacity-60'
              }`}
            >
              {isDone ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
              ) : isCurrent ? (
                <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
              ) : (
                <Circle className="w-4 h-4 text-text-muted/40 shrink-0" />
              )}
              <span className="font-sans">{text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
