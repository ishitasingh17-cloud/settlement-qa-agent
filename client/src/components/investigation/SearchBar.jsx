/**
 * client/src/components/investigation/SearchBar.jsx
 * 
 * Omnibar search input supporting transaction IDs, order IDs, settlement batches,
 * bank UTR references, and natural-language inquiry questions.
 */

import React, { useState } from 'react';
import { Search, X, ArrowRight, Loader2, Sparkles } from 'lucide-react';

const SUGGESTIONS = [
  { label: 'Clean Settlement', query: 'pay_Gz8x1001' },
  { label: 'Delayed Clearing', query: 'pay_Gz8x1000' },
  { label: 'Missing Ledger', query: 'pay_Gz8x1038' },
  { label: 'Bank Rejection', query: 'pay_Gz8x1042' },
  { label: 'Conflicting Records', query: 'pay_Gz8x1052' },
  { label: 'Insufficient Evidence', query: 'pay_Gz8x1100' },
];

export default function SearchBar({ onSearch, loading, initialValue = '' }) {
  const [inputVal, setInputVal] = useState(initialValue);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputVal.trim() && !loading) {
      onSearch(inputVal.trim());
    }
  };

  const handleClear = () => {
    setInputVal('');
  };

  const handleSuggestionClick = (query) => {
    setInputVal(query);
    onSearch(query);
  };

  return (
    <div className="w-full space-y-2">
      <form onSubmit={handleSubmit} className="relative flex items-center shadow-xs">
        <div className="absolute left-3.5 flex items-center pointer-events-none text-slate-700 dark:text-white">
          <Search className="w-4 h-4" />
        </div>

        <input
          type="text"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          placeholder="Search by Transaction ID (pay_...), Order ID, Settlement Batch, UTR, or Ledger ID..."
          className="w-full pl-10 pr-28 py-3 bg-surface border border-border rounded-xl text-sm text-text-primary placeholder:text-text-muted focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-sans"
          disabled={loading}
        />

        <div className="absolute right-2.5 flex items-center space-x-1.5">
          {inputVal && !loading && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1.5 text-slate-700 dark:text-white hover:text-primary rounded-md transition-colors"
              title="Clear input"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            type="submit"
            disabled={loading || !inputVal.trim()}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-primary hover:bg-primary-dark disabled:bg-surface-muted disabled:border disabled:border-border text-white disabled:text-text-muted text-xs font-semibold shadow-xs transition-all disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Tracing...</span>
              </>
            ) : (
              <>
                <span>Investigate</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      </form>

      {/* Suggested Quick Queries & Mode Distinction */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 text-xs">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-text-muted text-[11px] font-medium mr-1 flex items-center space-x-1">
            <Sparkles className="w-3 h-3 text-primary/70" />
            <span>Deterministic ID lookups:</span>
          </span>
          {SUGGESTIONS.map((s, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSuggestionClick(s.query)}
              className="px-2.5 py-1 rounded-md bg-surface border border-border hover:border-primary/40 hover:bg-ai-tint text-text-secondary hover:text-primary transition-colors text-[11px] font-mono"
              title={s.label}
            >
              {s.query}
            </button>
          ))}
        </div>
        <span className="text-[11px] text-text-muted font-sans italic">
          For contextual Q&amp;A (&ldquo;Why did this fail?&rdquo;), use Follow-up Chat below.
        </span>
      </div>
    </div>
  );
}
