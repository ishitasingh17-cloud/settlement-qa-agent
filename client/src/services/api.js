/**
 * client/src/services/api.js
 * 
 * HTTP API client for backend investigation endpoints.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * Extract canonical identifier if query is wrapped in natural language text.
 * Matches: pay_..., order_..., set_..., UTR..., led_...
 */
export function extractIdentifier(query) {
  if (!query) return '';
  const match = query.match(/\b(pay_[A-Za-z0-9]+|order_[A-Za-z0-9]+|set_[A-Za-z0-9]+|UTR[A-Za-z0-9]+|led_[A-Za-z0-9]+)\b/i);
  return match ? match[1] : query.trim();
}

/**
 * Check backend health status.
 */
export async function checkHealth() {
  try {
    const res = await fetch(`${BASE_URL}/api/health`);
    if (!res.ok) {
      throw new Error(`Health check failed with status: ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    const errorObj = new Error(err.message || 'Backend service unreachable');
    errorObj.status = 0;
    errorObj.code = 'NETWORK_ERROR';
    throw errorObj;
  }
}

/**
 * Run deterministic investigation and AI explanation for a transaction or identifier.
 * 
 * @param {string} query - Identifier or question
 * @param {string|null} queryType - Optional query type hint
 * @returns {Promise<Object>} InvestigationResponse payload
 */
export async function investigateTransaction(query, queryType = null) {
  const cleanId = extractIdentifier(query);
  const payload = { query: cleanId };
  if (queryType) {
    payload.query_type = queryType;
  }

  let res;
  try {
    res = await fetch(`${BASE_URL}/api/investigate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  } catch (netErr) {
    const err = new Error('Cannot connect to settlement-qa backend on http://127.0.0.1:8000. Please ensure the backend server is running.');
    err.status = 0;
    err.code = 'NETWORK_ERROR';
    err.detail = { message: err.message, error: 'NETWORK_ERROR' };
    throw err;
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const errorDetail = data.detail || data || {};
    const err = new Error(errorDetail.message || 'Investigation request failed');
    err.status = res.status;
    err.code = errorDetail.error || (res.status === 404 ? 'NOT_FOUND' : 'API_ERROR');
    err.detail = errorDetail;
    throw err;
  }

  return data;
}

/**
 * Ask a contextual question about an investigated transaction with optional conversation thread ID.
 * 
 * @param {string} identifier - Transaction ID or identifier
 * @param {string} question - Question to ask
 * @param {string|null} conversationId - Optional ongoing conversation session ID
 * @returns {Promise<Object>} AIAnalystResponse payload
 */
export async function askFollowUpQuestion(identifier, question, conversationId = null) {
  const cleanId = extractIdentifier(identifier);
  const payload = {
    identifier: cleanId,
    question: question.trim(),
  };
  if (conversationId) {
    payload.conversation_id = conversationId;
  }

  let res;
  try {
    res = await fetch(`${BASE_URL}/api/investigate/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  } catch (netErr) {
    const err = new Error('Cannot connect to settlement-qa backend on http://127.0.0.1:8000.');
    err.status = 0;
    err.code = 'NETWORK_ERROR';
    err.detail = { message: err.message, error: 'NETWORK_ERROR' };
    throw err;
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const errorDetail = data.detail || data || {};
    const err = new Error(errorDetail.message || 'Failed to process question');
    err.status = res.status;
    err.code = errorDetail.error || 'QUESTION_ERROR';
    err.detail = errorDetail;
    throw err;
  }

  return data;
}

/**
 * Explicitly reset/clear a conversation session on the backend.
 * 
 * @param {string} conversationId - Conversation ID to reset
 * @returns {Promise<Object>} Reset status payload
 */
export async function resetConversation(conversationId) {
  if (!conversationId) return { success: true };
  try {
    const res = await fetch(`${BASE_URL}/api/conversation/reset`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ conversation_id: conversationId }),
    });
    return await res.json().catch(() => ({ success: true }));
  } catch {
    return { success: true };
  }
}


/**
 * Fetch macro exceptions dashboard summary and flagged transactions.
 * 
 * @param {Object} options - Query filters
 * @param {string|null} options.date - Optional date string (YYYY-MM-DD)
 * @param {string|null} options.severity - Optional severity filter (CRITICAL, HIGH, MEDIUM, LOW)
 * @param {string|null} options.status - Optional status/diagnosis filter
 * @returns {Promise<Object>} ExceptionDashboardSummary payload
 */
export async function fetchExceptionsDashboard({ date = null, severity = null, status = null } = {}) {
  const params = new URLSearchParams();
  if (date && date.trim()) params.append('date', date.trim());
  if (severity && severity !== 'ALL') params.append('severity', severity.trim());
  if (status && status !== 'ALL') params.append('status', status.trim());

  const query = params.toString();
  const url = `${BASE_URL}/api/exceptions${query ? `?${query}` : ''}`;

  let res;
  try {
    res = await fetch(url);
  } catch (netErr) {
    const err = new Error('Cannot connect to settlement-qa backend on http://127.0.0.1:8000.');
    err.status = 0;
    err.code = 'NETWORK_ERROR';
    err.detail = { message: err.message, error: 'NETWORK_ERROR' };
    throw err;
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const errorDetail = data.detail || data || {};
    const err = new Error(errorDetail.message || 'Failed to fetch exceptions dashboard');
    err.status = res.status;
    err.code = errorDetail.error || 'DASHBOARD_ERROR';
    err.detail = errorDetail;
    throw err;
  }

  return data;
}
