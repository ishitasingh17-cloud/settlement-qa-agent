/**
 * client/src/components/dashboard/ExceptionDistribution.jsx
 * 
 * Compact horizontal distribution breakdown of exception categories.
 */

import React from 'react';
import { Layers } from 'lucide-react';
import { getDiagnosisMeta } from '../../utils/formatters';

export default function ExceptionDistribution({ byType = {}, onSelectCategory, activeCategory }) {
  const entries = Object.entries(byType).filter(([_, count]) => count > 0);
  const total = entries.reduce((acc, [_, count]) => acc + count, 0);

  if (entries.length === 0) return null;

  return (
    <div className="bg-surface border border-border rounded-xl p-4 shadow-xs space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="p-1 rounded-md bg-primary/10 text-primary">
            <Layers className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold text-text-primary uppercase tracking-wider">
            Exception Category Distribution ({total})
          </span>
        </div>
        <span className="text-[11px] text-text-muted">
          Click category to filter queue
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
        {entries.map(([typeKey, count]) => {
          const meta = getDiagnosisMeta(typeKey);
          const Icon = meta.icon;
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          const isSelected = activeCategory === typeKey;

          return (
            <button
              key={typeKey}
              type="button"
              onClick={() => onSelectCategory(isSelected ? 'ALL' : typeKey)}
              className={`p-2.5 rounded-lg border text-left transition-all cursor-pointer ${
                isSelected
                  ? 'bg-primary/5 border-primary shadow-xs ring-1 ring-primary/30'
                  : 'bg-surface hover:bg-surface-muted border-border hover:border-primary/40'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center space-x-1.5 truncate">
                  <Icon className={`w-3.5 h-3.5 ${meta.textColor} shrink-0`} />
                  <span className="text-xs font-semibold text-text-primary truncate">
                    {meta.label}
                  </span>
                </div>
                <span className="font-mono text-xs font-bold text-text-primary shrink-0 ml-2">
                  {count}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-surface-muted border border-border/40 rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-full rounded-full ${meta.dotColor || 'bg-primary'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-[10px] text-text-muted mt-1 block">
                {pct}% of total exceptions
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
