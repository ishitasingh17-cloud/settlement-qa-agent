/**
 * client/src/components/dashboard/ExceptionEmptyState.jsx
 * 
 * Empty state rendered when exception filters return 0 matching items.
 */

import React from 'react';
import { CheckCircle2, RotateCcw } from 'lucide-react';

export default function ExceptionEmptyState({ onResetFilters }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-10 text-center space-y-4">
      <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto">
        <CheckCircle2 className="w-6 h-6" />
      </div>
      <div className="space-y-1 max-w-md mx-auto">
        <h3 className="text-sm font-bold text-text-primary">
          No Exceptions Found
        </h3>
        <p className="text-xs text-text-secondary">
          No settlement discrepancy records match the selected date, severity, or category filters.
        </p>
      </div>

      <button
        type="button"
        onClick={onResetFilters}
        className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-surface hover:bg-surface-muted text-xs font-semibold text-text-primary border border-border shadow-xs transition-colors cursor-pointer"
      >
        <RotateCcw className="w-3.5 h-3.5 text-slate-700 dark:text-white" />
        <span>Reset Filters</span>
      </button>
    </div>
  );
}
