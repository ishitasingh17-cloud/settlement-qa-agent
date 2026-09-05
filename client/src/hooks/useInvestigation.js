/**
 * client/src/hooks/useInvestigation.js
 * 
 * React hook managing investigation state, multi-step progress, and history.
 */

import { useState, useCallback, useRef } from 'react';
import {
  investigateTransaction,
  askFollowUpQuestion,
  resetConversation,
  extractIdentifier,
} from '../services/api';

const PROGRESS_STEPS = [
  { step: 1, label: 'Querying Gateway records & trace graph...', percent: 20 },
  { step: 2, label: 'Traversing multi-hop Reference Chain (Bank & Ledger)...', percent: 45 },
  { step: 3, label: 'Executing Gross/Net reconciliation & variance audit...', percent: 70 },
  { step: 4, label: 'Evaluating 11-state settlement diagnosis taxonomy...', percent: 85 },
  { step: 5, label: 'Synthesizing & validating dual-channel AI explanation...', percent: 98 },
];

export function useInvestigation() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState(0);
  const [error, setError] = useState(null);
  const [activeQuery, setActiveQuery] = useState('');
  const [askingQuestion, setAskingQuestion] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [conversationMessages, setConversationMessages] = useState([]);
  const [history, setHistory] = useState(() => {
    try {
      const raw = localStorage.getItem('settlement_qa_history');
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.filter(item => item && typeof item === 'object' && item.transaction_id) : [];
    } catch {
      return [];
    }
  });

  const progressTimerRef = useRef(null);

  const startProgressSimulation = useCallback(() => {
    setLoadingStage(0);
    let stage = 0;
    progressTimerRef.current = setInterval(() => {
      stage += 1;
      if (stage < PROGRESS_STEPS.length) {
        setLoadingStage(stage);
      } else {
        clearInterval(progressTimerRef.current);
      }
    }, 180);
  }, []);

  const stopProgressSimulation = useCallback(() => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
  }, []);

  const executeInvestigation = useCallback(async (query, queryType = null) => {
    if (!query || !query.trim()) return;

    setLoading(true);
    setError(null);
    setActiveQuery(query.trim());
    // Context isolation: reset conversational thread for new investigation
    setConversationId(null);
    setConversationMessages([]);
    startProgressSimulation();

    try {
      const res = await investigateTransaction(query, queryType);
      setData(res);

      // Record to history
      setHistory((prev) => {
        const safePrev = Array.isArray(prev) ? prev : [];
        const item = {
          query: query.trim(),
          transaction_id: res.transaction_id,
          diagnosis: res.diagnosis,
          timestamp: new Date().toISOString(),
        };
        const filtered = safePrev.filter((h) => h && h.transaction_id !== res.transaction_id);
        const next = [item, ...filtered].slice(0, 10);
        try {
          localStorage.setItem('settlement_qa_history', JSON.stringify(next));
        } catch {}
        return next;
      });

      // If user typed an explicit question (e.g. "Why was pay_Gz8x1001 settled?"), ask it
      const trimmed = query.trim();
      const isQuestion = trimmed.includes('?') || /^(why|what|when|how|is|was|can)/i.test(trimmed);
      if (isQuestion && res.transaction_id) {
        try {
          const analystResp = await askFollowUpQuestion(res.transaction_id, trimmed, null);
          if (analystResp.conversation_id) {
            setConversationId(analystResp.conversation_id);
          }
          const userMsg = {
            id: `usr_${Date.now()}`,
            role: 'user',
            content: trimmed,
            timestamp: new Date().toISOString(),
          };
          const asstMsg = {
            id: analystResp.message_id || `ast_${Date.now()}`,
            role: 'assistant',
            content: analystResp.answer || analystResp.merchant_friendly_response,
            internalSummary: analystResp.internal_summary,
            llmUsed: analystResp.llm_used,
            provider: analystResp.provider,
            model: analystResp.model,
            validated: analystResp.validated,
            validationResult: analystResp.validation_result,
            timestamp: new Date().toISOString(),
          };
          setConversationMessages([userMsg, asstMsg]);

          setData((prev) => {
            if (!prev) return prev;
            return {
              ...prev,
              explanation: {
                ...prev.explanation,
                answer: analystResp.answer,
              },
            };
          });
        } catch (qErr) {
          console.warn('Initial natural question query answering failed:', qErr);
        }
      }
    } catch (err) {
      setData(null);
      setError({
        status: err.status || 500,
        code: err.code || 'UNKNOWN_ERROR',
        message: err.message || 'An unexpected error occurred during investigation.',
        query: query.trim(),
      });
    } finally {
      stopProgressSimulation();
      setLoading(false);
    }
  }, [startProgressSimulation, stopProgressSimulation]);

  const askQuestion = useCallback(async (question) => {
    if (!data || !data.transaction_id || !question || !question.trim()) return;

    const trimmed = question.trim();
    const userMsg = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    // Optimistically append user message
    setConversationMessages((prev) => [...prev, userMsg]);
    setAskingQuestion(true);

    try {
      const analystResp = await askFollowUpQuestion(data.transaction_id, trimmed, conversationId);
      if (analystResp.conversation_id) {
        setConversationId(analystResp.conversation_id);
      }

      const asstMsg = {
        id: analystResp.message_id || `ast_${Date.now()}`,
        role: 'assistant',
        content: analystResp.answer || analystResp.merchant_friendly_response,
        internalSummary: analystResp.internal_summary,
        llmUsed: analystResp.llm_used,
        provider: analystResp.provider,
        model: analystResp.model,
        validated: analystResp.validated,
        validationResult: analystResp.validation_result,
        timestamp: new Date().toISOString(),
      };
      setConversationMessages((prev) => [...prev, asstMsg]);

      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          explanation: {
            ...prev.explanation,
            answer: analystResp.answer,
            internal_summary: analystResp.internal_summary || prev.explanation.internal_summary,
            merchant_friendly_response: analystResp.merchant_friendly_response || prev.explanation.merchant_friendly_response,
            validation_result: analystResp.validation_result || prev.explanation.validation_result,
          },
        };
      });
    } catch (err) {
      console.error('Failed to answer question:', err);
      // Append error message to chat
      const errorMsg = {
        id: `err_${Date.now()}`,
        role: 'assistant',
        content: 'Unable to process follow-up query. The investigation engine remains securely grounded in verified records.',
        isError: true,
        timestamp: new Date().toISOString(),
      };
      setConversationMessages((prev) => [...prev, errorMsg]);
    } finally {
      setAskingQuestion(false);
    }
  }, [data, conversationId]);

  const resetConversationThread = useCallback(async () => {
    if (conversationId) {
      try {
        await resetConversation(conversationId);
      } catch (e) {
        console.warn('Reset conversation failed on server:', e);
      }
    }
    setConversationId(null);
    setConversationMessages([]);
  }, [conversationId]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setActiveQuery('');
    setLoading(false);
    setConversationId(null);
    setConversationMessages([]);
    stopProgressSimulation();
  }, [stopProgressSimulation]);

  return {
    data,
    loading,
    loadingStep: PROGRESS_STEPS[loadingStage] || PROGRESS_STEPS[0],
    error,
    activeQuery,
    askingQuestion,
    conversationId,
    conversationMessages,
    history,
    executeInvestigation,
    askQuestion,
    resetConversationThread,
    reset,
  };
}
