/**
 * client/src/utils/formatters.js
 * Strict formatting utilities for financial and operational data.
 * INVARIANT: Zero float parsing (no parseFloat, no floating-point arithmetic).
 * All monetary amounts are formatted purely through string operations.
 */

import {
  CheckCircle2,
  Clock,
  XCircle,
  AlertOctagon,
  Scale,
  HelpCircle,
  FileQuestion,
  GitFork,
  Copy,
  AlertTriangle,
  ShieldAlert,
} from 'lucide-react';

/**
 * Format currency amount as a string with exact 2 decimal places and locale comma grouping.
 * Strictly avoids parseFloat() or floating point arithmetic.
 *
 * @param {string|number|null} amount - Decimal string representation from backend
 * @param {string} currency - Currency code (e.g. 'INR', 'USD')
 * @returns {string} Formatted currency string (e.g. "₹1,113.58") or "—" if empty
 */
export function formatCurrency(amount, currency = 'INR') {
  if (amount === null || amount === undefined || amount === '') {
    return '—';
  }

  const rawStr = String(amount).trim();
  if (rawStr === '—' || rawStr === '-' || rawStr === 'None') {
    return '—';
  }

  const isNegative = rawStr.startsWith('-');
  const cleanStr = isNegative ? rawStr.slice(1).trim() : rawStr.replace(/^\+/, '').trim();

  const parts = cleanStr.split('.');
  const integerPart = parts[0] || '0';
  let decimalPart = parts[1] || '00';

  if (decimalPart.length === 1) {
    decimalPart += '0';
  } else if (decimalPart.length > 2) {
    decimalPart = decimalPart.slice(0, 2);
  }

  // Format integer with commas via regex grouping
  const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  const symbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : '₹';

  return `${isNegative ? '-' : ''}${symbol}${formattedInteger}.${decimalPart}`;
}

/**
 * Format timestamp into clean human-readable UTC representation.
 *
 * @param {string|number|null} timestamp - ISO 8601 string or Unix epoch in seconds
 * @returns {string} Formatted UTC date-time string
 */
export function formatTimestamp(timestamp) {
  if (!timestamp) return '—';

  try {
    let date;
    if (typeof timestamp === 'number' || /^\d+$/.test(String(timestamp).trim())) {
      const num = Number(timestamp);
      // If epoch is in seconds (10 digits), convert to ms
      date = new Date(num > 10000000000 ? num : num * 1000);
    } else {
      date = new Date(timestamp);
    }

    if (isNaN(date.getTime())) {
      return String(timestamp);
    }

    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    const hours = String(date.getUTCHours()).padStart(2, '0');
    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
    const seconds = String(date.getUTCSeconds()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} UTC`;
  } catch {
    return String(timestamp);
  }
}

/**
 * Controlled metadata dictionary for all 11 Settlement Diagnosis states.
 */
export const DIAGNOSIS_METADATA = {
  SUCCESSFULLY_SETTLED: {
    label: 'Successfully Settled',
    code: 'SUCCESSFULLY_SETTLED',
    icon: CheckCircle2,
    colorFamily: 'emerald',
    textColor: 'text-emerald-700',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    dotColor: 'bg-emerald-500',
    description: 'Gateway payment captured, bank settlement confirmed with UTR, and ledger balance booked.',
  },
  SETTLEMENT_PENDING: {
    label: 'Settlement Pending',
    code: 'SETTLEMENT_PENDING',
    icon: Clock,
    colorFamily: 'amber',
    textColor: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    dotColor: 'bg-amber-500',
    description: 'Payment captured and ledger booked; bank clearing rail transfer is currently in-flight.',
  },
  GATEWAY_FAILED: {
    label: 'Gateway Failed',
    code: 'GATEWAY_FAILED',
    icon: XCircle,
    colorFamily: 'rose',
    textColor: 'text-rose-700',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-200',
    dotColor: 'bg-rose-500',
    description: 'Transaction failed at payment gateway authorization; funds were not collected from customer.',
  },
  BANK_REJECTED: {
    label: 'Bank Rejected',
    code: 'BANK_REJECTED',
    icon: AlertOctagon,
    colorFamily: 'rose',
    textColor: 'text-rose-700',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-200',
    dotColor: 'bg-rose-500',
    description: 'Nodal clearing bank returned an explicit rejection; payout was declined.',
  },
  AMOUNT_MISMATCH: {
    label: 'Amount Mismatch',
    code: 'AMOUNT_MISMATCH',
    icon: Scale,
    colorFamily: 'orange',
    textColor: 'text-orange-700',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    dotColor: 'bg-orange-500',
    description: 'Numerical discrepancy detected between Gateway Net, Bank Disbursed, and Ledger Posted amounts.',
  },
  MISSING_BANK_RECORD: {
    label: 'Missing Bank Record',
    code: 'MISSING_BANK_RECORD',
    icon: HelpCircle,
    colorFamily: 'blue',
    textColor: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    dotColor: 'bg-blue-500',
    description: 'Payment was captured, but no matching settlement clearing record exists in bank files.',
  },
  MISSING_LEDGER_RECORD: {
    label: 'Missing Ledger Record',
    code: 'MISSING_LEDGER_RECORD',
    icon: FileQuestion,
    colorFamily: 'blue',
    textColor: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    dotColor: 'bg-blue-500',
    description: 'Transaction was processed or settled, but lacks an internal accounting ledger journal entry.',
  },
  REFERENCE_MISMATCH: {
    label: 'Reference Mismatch',
    code: 'REFERENCE_MISMATCH',
    icon: GitFork,
    colorFamily: 'amber',
    textColor: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    dotColor: 'bg-amber-500',
    description: 'Inconsistent reference IDs across systems; batch or UTR pointers do not align.',
  },
  DUPLICATE_RECORD: {
    label: 'Duplicate Record',
    code: 'DUPLICATE_RECORD',
    icon: Copy,
    colorFamily: 'rose',
    textColor: 'text-rose-800',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-300',
    dotColor: 'bg-rose-600',
    description: 'Multiple conflicting records found for the same identifier in downstream files.',
  },
  CONFLICTING_EVIDENCE: {
    label: 'Conflicting Evidence',
    code: 'CONFLICTING_EVIDENCE',
    icon: AlertTriangle,
    colorFamily: 'purple',
    textColor: 'text-purple-700',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    dotColor: 'bg-purple-500',
    description: 'Direct status contradiction across systems (e.g. Bank settled but Gateway failed).',
  },
  INSUFFICIENT_EVIDENCE: {
    label: 'Insufficient Evidence',
    code: 'INSUFFICIENT_EVIDENCE',
    icon: ShieldAlert,
    colorFamily: 'sky',
    textColor: 'text-sky-700',
    bgColor: 'bg-sky-50',
    borderColor: 'border-sky-200',
    dotColor: 'bg-sky-500',
    description: 'Crucial evidence components are absent; definitive settlement determination impossible.',
  },
};

export function getDiagnosisMeta(diagnosis) {
  const code = (diagnosis || '').toUpperCase();
  return DIAGNOSIS_METADATA[code] || {
    label: code || 'Unknown Diagnosis',
    code: code,
    icon: ShieldAlert,
    colorFamily: 'gray',
    textColor: 'text-slate-700',
    bgColor: 'bg-slate-100',
    borderColor: 'border-slate-200',
    dotColor: 'bg-slate-500',
    description: 'Diagnosis state not recognized.',
  };
}

export const CONFIDENCE_METADATA = {
  HIGH: {
    label: 'High Confidence',
    badgeText: 'HIGH',
    textColor: 'text-emerald-700',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    dotColor: 'bg-emerald-500',
    meterPercent: 95,
  },
  MEDIUM: {
    label: 'Medium Confidence',
    badgeText: 'MEDIUM',
    textColor: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    dotColor: 'bg-amber-500',
    meterPercent: 65,
  },
  LOW: {
    label: 'Low Confidence',
    badgeText: 'LOW',
    textColor: 'text-rose-700',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-200',
    dotColor: 'bg-rose-500',
    meterPercent: 30,
  },
};

export function getConfidenceMeta(confidence) {
  const level = (confidence || '').toUpperCase();
  return CONFIDENCE_METADATA[level] || CONFIDENCE_METADATA.LOW;
}

export const SEVERITY_METADATA = {
  CRITICAL: {
    label: 'Critical',
    textColor: 'text-rose-700',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-300',
  },
  HIGH: {
    label: 'High',
    textColor: 'text-rose-600',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-200',
  },
  MEDIUM: {
    label: 'Medium',
    textColor: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
  LOW: {
    label: 'Low',
    textColor: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  NONE: {
    label: 'None',
    textColor: 'text-slate-600',
    bgColor: 'bg-slate-50',
    borderColor: 'border-slate-200',
  },
};

export function getSeverityMeta(severity) {
  const code = (severity || '').toUpperCase();
  return SEVERITY_METADATA[code] || SEVERITY_METADATA.NONE;
}

export const STATUS_METADATA = {
  RESOLVED: {
    label: 'Resolved',
    textColor: 'text-emerald-700',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
  },
  INVESTIGATING: {
    label: 'Investigating',
    textColor: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  EXCEPTION: {
    label: 'Exception',
    textColor: 'text-rose-700',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-200',
  },
  MANUAL_REVIEW: {
    label: 'Manual Review',
    textColor: 'text-purple-700',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
  },
  INSUFFICIENT_DATA: {
    label: 'Insufficient Data',
    textColor: 'text-sky-700',
    bgColor: 'bg-sky-50',
    borderColor: 'border-sky-200',
  },
};

export function getStatusMeta(status) {
  const code = (status || '').toUpperCase();
  return STATUS_METADATA[code] || {
    label: code || 'Unknown',
    textColor: 'text-slate-600',
    bgColor: 'bg-slate-100',
    borderColor: 'border-slate-200',
  };
}


export const EXCEPTION_TYPE_METADATA = {
  ERR_STATUS_MISMATCH: {
    label: 'Status Mismatch',
    code: 'ERR_STATUS_MISMATCH',
    textColor: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
  ERR_AMOUNT_MISMATCH: {
    label: 'Amount Mismatch',
    code: 'ERR_AMOUNT_MISMATCH',
    textColor: 'text-orange-700',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
  },
  ERR_MISSING_BANK: {
    label: 'Missing Bank',
    code: 'ERR_MISSING_BANK',
    textColor: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  ERR_MISSING_LEDGER: {
    label: 'Missing Ledger',
    code: 'ERR_MISSING_LEDGER',
    textColor: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  ERR_MISSING_GATEWAY: {
    label: 'Missing Gateway',
    code: 'ERR_MISSING_GATEWAY',
    textColor: 'text-sky-700',
    bgColor: 'bg-sky-50',
    borderColor: 'border-sky-200',
  },
  ERR_REFERENCE_MISMATCH: {
    label: 'Reference Mismatch',
    code: 'ERR_REFERENCE_MISMATCH',
    textColor: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
  ERR_DUPLICATE_RECORD: {
    label: 'Duplicate Record',
    code: 'ERR_DUPLICATE_RECORD',
    textColor: 'text-rose-800',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-300',
  },
  ERR_CONFLICTING_EVIDENCE: {
    label: 'Conflicting Evidence',
    code: 'ERR_CONFLICTING_EVIDENCE',
    textColor: 'text-purple-700',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
  },
  ERR_BANK_REJECTION: {
    label: 'Bank Rejection',
    code: 'ERR_BANK_REJECTION',
    textColor: 'text-rose-700',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-200',
  },
  ERR_GATEWAY_FAILURE: {
    label: 'Gateway Failure',
    code: 'ERR_GATEWAY_FAILURE',
    textColor: 'text-rose-700',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-200',
  },
  INFO_UNBATCHED: {
    label: 'Unbatched Settlement',
    code: 'INFO_UNBATCHED',
    textColor: 'text-slate-600',
    bgColor: 'bg-slate-100',
    borderColor: 'border-slate-200',
  },
  NONE: {
    label: 'None',
    code: 'NONE',
    textColor: 'text-slate-500',
    bgColor: 'bg-slate-50',
    borderColor: 'border-slate-200',
  },
};

export function getExceptionTypeMeta(type) {
  const code = (type || '').toUpperCase();
  return EXCEPTION_TYPE_METADATA[code] || {
    label: code || 'Unknown Exception',
    code: code,
    textColor: 'text-slate-600',
    bgColor: 'bg-slate-100',
    borderColor: 'border-slate-200',
  };
}
