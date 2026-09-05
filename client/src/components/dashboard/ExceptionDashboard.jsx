/**
 * client/src/components/dashboard/ExceptionDashboard.jsx
 * 
 * Root Operations Exception Dashboard Workspace.
 * Composes Summary Cards, Distribution, Filters, and Queue.
 */

import React from 'react';
import {
  AlertTriangle,
  Loader2,
  AlertCircle,
  RotateCcw,
} from 'lucide-react';
import ExceptionSummaryCards from './ExceptionSummaryCards';
import ExceptionDistribution from './ExceptionDistribution';
import ExceptionFilters from './ExceptionFilters';
import ExceptionQueue from './ExceptionQueue';
import ExceptionEmptyState from './ExceptionEmptyState';
import { useExceptionsDashboard } from '../../hooks/useExceptionsDashboard';

export default function ExceptionDashboard({ onSelectTransaction }) {
  const {
    data,
    loading,
    error,
    filters,
    sortConfig,
    filteredExceptions,
    hasActiveFilters,
    setFilter,
    resetFilters,
    toggleSort,
    refresh,
  } = useExceptionsDashboard();

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Dashboard Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-bold text-text-primary tracking-tight">
              Settlement Exception Dashboard
            </h2>
            <span className="px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-200 rounded-full">
              Operations Queue
            </span>
          </div>
          <p className="text-xs text-text-secondary font-sans mt-0.5">
            Deterministic Exception Triage & Discrepancy Monitoring &bull; Grounded strictly in Verified Evidence
          </p>
        </div>

        {data && (
          <div className="flex items-center space-x-2 text-xs text-text-secondary font-mono">
            <span>Showing {filteredExceptions.length} of {data.total_exceptions || data.actionable_exceptions_count || 0} flagged</span>
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && !data ? (
        <div className="py-16 text-center space-y-3">
          <Loader2 className="w-7 h-7 animate-spin text-primary mx-auto" />
          <p className="text-xs text-text-secondary font-medium font-mono">
            Loading exception dashboard records...
          </p>
        </div>
      ) : error ? (
        /* Error State */
        <div className="bg-rose-50/50 border border-rose-200 rounded-xl p-6 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-rose-600 mx-auto" />
          <div>
            <h3 className="text-sm font-bold text-rose-900">
              Unable to Load Exception Data
            </h3>
            <p className="text-xs text-rose-700 mt-1 max-w-md mx-auto">
              {error.message}
            </p>
          </div>
          <button
            type="button"
            onClick={refresh}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-2xs cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry Connection</span>
          </button>
        </div>
      ) : data ? (
        <>
          {/* 1. Macro Summary Cards */}
          <ExceptionSummaryCards data={data} />

          {/* 2. Exception Distribution Breakdown */}
          <ExceptionDistribution
            byType={data.by_type}
            onSelectCategory={(cat) => setFilter('exceptionType', cat)}
            activeCategory={filters.exceptionType}
          />

          {/* 3. Filter Controls */}
          <ExceptionFilters
            filters={filters}
            onFilterChange={setFilter}
            onResetFilters={resetFilters}
            onRefresh={refresh}
            loading={loading}
            hasActiveFilters={hasActiveFilters}
          />

          {/* 4. Main Operational Queue or Filtered Empty State */}
          {filteredExceptions.length === 0 ? (
            <ExceptionEmptyState onResetFilters={resetFilters} />
          ) : (
            <ExceptionQueue
              exceptions={filteredExceptions}
              sortConfig={sortConfig}
              onSort={toggleSort}
              onSelectTransaction={onSelectTransaction}
            />
          )}
        </>
      ) : null}
    </div>
  );
}
