/**
 * client/src/hooks/useExceptionsDashboard.js
 * 
 * React hook managing exception dashboard state, filters, sorting, and API lifecycle.
 * Adheres strictly to Zero Float Parsing rule: all currency amounts are handled as strings.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { fetchExceptionsDashboard } from '../services/api';

const SEVERITY_ORDER = {
  CRITICAL: 4,
  HIGH: 3,
  MEDIUM: 2,
  LOW: 1,
  NONE: 0,
};

export function useExceptionsDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [filters, setFilters] = useState({
    date: '',
    severity: 'ALL',
    exceptionType: 'ALL',
    status: 'ALL',
    search: '',
  });

  const [sortConfig, setSortConfig] = useState({
    field: 'severity',
    direction: 'desc',
  });

  const loadData = useCallback(async (dateFilter = filters.date) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchExceptionsDashboard({ date: dateFilter || null });
      setData(res);
    } catch (err) {
      console.error('Failed to load exceptions dashboard:', err);
      setError({
        status: err.status || 500,
        code: err.code || 'DASHBOARD_ERROR',
        message: err.message || 'Unable to retrieve exceptions dashboard records.',
      });
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [filters.date]);

  // Initial load and on date filter change
  useEffect(() => {
    loadData(filters.date);
  }, [filters.date, loadData]);

  const setFilter = useCallback((key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({
      date: '',
      severity: 'ALL',
      exceptionType: 'ALL',
      status: 'ALL',
      search: '',
    });
  }, []);

  const toggleSort = useCallback((field) => {
    setSortConfig((prev) => {
      if (prev.field === field) {
        return {
          field,
          direction: prev.direction === 'asc' ? 'desc' : 'asc',
        };
      }
      return { field, direction: 'desc' };
    });
  }, []);

  // Filtered and sorted exception queue (presentation-level only, no truth reconstruction)
  const filteredExceptions = useMemo(() => {
    if (!data || !data.flagged_transactions) return [];

    let list = [...data.flagged_transactions];

    // Search filter
    if (filters.search && filters.search.trim()) {
      const q = filters.search.trim().toLowerCase();
      list = list.filter((item) => {
        const txnId = (item.transaction_id || '').toLowerCase();
        const ordId = (item.order_id || '').toLowerCase();
        const utr = (item.utr || '').toLowerCase();
        const diag = (item.diagnosis || '').toLowerCase();
        const exc = (item.exception_type || '').toLowerCase();
        return txnId.includes(q) || ordId.includes(q) || utr.includes(q) || diag.includes(q) || exc.includes(q);
      });
    }

    // Severity filter
    if (filters.severity && filters.severity !== 'ALL') {
      const target = filters.severity.toUpperCase();
      list = list.filter((item) => (item.severity || '').toUpperCase() === target);
    }

    // Exception Type filter
    if (filters.exceptionType && filters.exceptionType !== 'ALL') {
      const target = filters.exceptionType.toUpperCase();
      list = list.filter((item) => {
        const diag = (item.diagnosis || '').toUpperCase();
        const exc = (item.exception_type || '').toUpperCase();
        return diag === target || exc === target;
      });
    }

    // Status filter
    if (filters.status && filters.status !== 'ALL') {
      const target = filters.status.toUpperCase();
      list = list.filter((item) => (item.status || '').toUpperCase() === target);
    }

    // Sorting
    list.sort((a, b) => {
      const dir = sortConfig.direction === 'asc' ? 1 : -1;
      if (sortConfig.field === 'severity') {
        const aVal = SEVERITY_ORDER[(a.severity || '').toUpperCase()] || 0;
        const bVal = SEVERITY_ORDER[(b.severity || '').toUpperCase()] || 0;
        return (aVal - bVal) * dir;
      }
      if (sortConfig.field === 'transaction_id') {
        return (a.transaction_id || '').localeCompare(b.transaction_id || '') * dir;
      }
      if (sortConfig.field === 'diagnosis') {
        return (a.diagnosis || '').localeCompare(b.diagnosis || '') * dir;
      }
      if (sortConfig.field === 'captured_at') {
        const aTime = a.captured_at ? new Date(a.captured_at).getTime() : 0;
        const bTime = b.captured_at ? new Date(b.captured_at).getTime() : 0;
        return (aTime - bTime) * dir;
      }
      return 0;
    });

    return list;
  }, [data, filters, sortConfig]);

  const hasActiveFilters = useMemo(() => {
    return (
      filters.date !== '' ||
      filters.severity !== 'ALL' ||
      filters.exceptionType !== 'ALL' ||
      filters.status !== 'ALL' ||
      filters.search.trim() !== ''
    );
  }, [filters]);

  return {
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
    refresh: () => loadData(filters.date),
  };
}
