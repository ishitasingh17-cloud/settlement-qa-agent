/**
 * client/src/components/dashboard/ExceptionFilters.jsx
 * 
 * Filter bar supporting date selection, severity, exception category, status, and text search.
 */

import React from 'react';
import {
  Search,
  Calendar,
  Filter,
  RotateCcw,
  RefreshCw,
} from 'lucide-react';

const SEVERITY_OPTIONS = [
  { value: 'ALL', label: 'All Severities' },
  { value: 'CRITICAL', label: 'Critical' },
  { value: 'HIGH', label: 'High' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW', label: 'Low' },
];

const EXCEPTION_OPTIONS = [
  { value: 'ALL', label: 'All Discrepancy Types' },
  { value: 'MISSING_BANK_RECORD', label: 'Missing Bank Record' },
  { value: 'CONFLICTING_EVIDENCE', label: 'Conflicting Evidence' },
  { value: 'BANK_REJECTED', label: 'Bank Rejected' },
  { value: 'MISSING_LEDGER_RECORD', label: 'Missing Ledger Record' },
  { value: 'INSUFFICIENT_EVIDENCE', label: 'Insufficient Evidence' },
];

const STATUS_OPTIONS = [
  { value: 'ALL', label: 'All Statuses' },
  { value: 'EXCEPTION', label: 'Exception' },
  { value: 'INVESTIGATING', label: 'Investigating' },
  { value: 'MANUAL_REVIEW', label: 'Manual Review' },
  { value: 'INSUFFICIENT_DATA', label: 'Insufficient Data' },
];

const QUICK_DATES = [
  { label: 'All Dates', value: '' },
  { label: '2026-09-01', value: '2026-09-01' },
  { label: '2026-09-02', value: '2026-09-02' },
  { label: '2026-09-03', value: '2026-09-03' },
  { label: '2026-09-10', value: '2026-09-10' },
];

export default function ExceptionFilters({
  filters,
  onFilterChange,
  onResetFilters,
  onRefresh,
  loading = false,
  hasActiveFilters = false,
}) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4 shadow-xs space-y-3">
      {/* Top Filter Row: Search & Dropdowns */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
        {/* Universal Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-700 dark:text-white absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => onFilterChange('search', e.target.value)}
            placeholder="Search by transaction ID, order ID, or UTR..."
            className="w-full pl-9 pr-3 py-2 bg-surface-muted/60 border border-border rounded-lg text-xs text-text-primary placeholder:text-text-muted focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>

        {/* Filter Dropdowns */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Severity Selector */}
          <select
            value={filters.severity}
            onChange={(e) => onFilterChange('severity', e.target.value)}
            className="px-2.5 py-2 bg-surface border border-border rounded-lg text-xs text-text-primary focus:outline-hidden focus:ring-2 focus:ring-primary/20 cursor-pointer"
          >
            {SEVERITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Exception Type Selector */}
          <select
            value={filters.exceptionType}
            onChange={(e) => onFilterChange('exceptionType', e.target.value)}
            className="px-2.5 py-2 bg-surface border border-border rounded-lg text-xs text-text-primary focus:outline-hidden focus:ring-2 focus:ring-primary/20 cursor-pointer"
          >
            {EXCEPTION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Status Selector */}
          <select
            value={filters.status}
            onChange={(e) => onFilterChange('status', e.target.value)}
            className="px-2.5 py-2 bg-surface border border-border rounded-lg text-xs text-text-primary focus:outline-hidden focus:ring-2 focus:ring-primary/20 cursor-pointer"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Reset Filters Button */}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={onResetFilters}
              className="inline-flex items-center space-x-1 px-2.5 py-2 rounded-lg bg-surface hover:bg-surface-muted text-xs text-text-secondary border border-border transition-colors cursor-pointer"
              title="Reset all active filters"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-700 dark:text-white" />
              <span>Reset</span>
            </button>
          )}

          {/* Refresh Button */}
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-primary/10 hover:bg-primary/15 text-primary border border-primary/25 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
            title="Refresh exceptions dashboard from backend"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Date Filter Bar */}
      <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-border text-xs">
        <div className="flex items-center space-x-1.5 text-text-muted mr-1.5 text-[11px]">
          <Calendar className="w-3.5 h-3.5 text-slate-700 dark:text-white" />
          <span>Settlement Date:</span>
        </div>

        {QUICK_DATES.map((qd) => {
          const isSelected = filters.date === qd.value;
          return (
            <button
              key={qd.value}
              type="button"
              onClick={() => onFilterChange('date', qd.value)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-mono transition-colors cursor-pointer ${
                isSelected
                  ? 'bg-primary text-white font-semibold shadow-2xs'
                  : 'bg-surface hover:bg-surface-muted text-text-secondary border border-border'
              }`}
            >
              {qd.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
