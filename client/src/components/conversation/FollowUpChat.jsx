/**
 * client/src/components/conversation/FollowUpChat.jsx
 * 
 * Multi-turn Conversational Follow-Up Q&A Component.
 * Grounded strictly in the Verified Evidence Pack (VEO).
 * Restructured hierarchy:
 *   1. Header: "Ask About This Investigation" + VEO Grounded badge + Reset Thread
 *   2. Input Omnibar: Immediately accessible input + Send action
 *   3. Quick Prompt Chips: One-click suggested questions with Sparkles
 *   4. Conversation Stream: Message thread streaming below the input with scoped scrolling
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  MessageSquare,
  Send,
  Loader2,
  Copy,
  Check,
  RotateCcw,
  ShieldCheck,
  Bot,
  User,
  Sparkles,
  AlertTriangle,
} from 'lucide-react';

const SUGGESTED_QUESTIONS = [
  'Was this settlement rejected by the bank?',
  'What is the bank reference / UTR?',
  'What was the exact amount received?',
  'Why is the internal ledger entry missing?',
];

export default function FollowUpChat({
  transactionId,
  messages = [],
  askingQuestion = false,
  onAskQuestion,
  onResetThread,
}) {
  const [inputValue, setInputValue] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  const chatContainerRef = useRef(null);

  // Auto-scroll ONLY internal chat box container, preventing outer page viewport shifts
  useEffect(() => {
    if (chatContainerRef.current && messages.length > 0) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages.length, askingQuestion]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim() && !askingQuestion) {
      onAskQuestion(inputValue.trim());
      setInputValue('');
    }
  };

  const handleCopy = async (id, text) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  return (
    <div className="bg-surface border border-border rounded-xl p-5 shadow-xs space-y-4">
      {/* 1. SECTION HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
            <MessageSquare className="w-4 h-4 text-primary" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                Ask About This Investigation
              </h3>
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface-muted border border-border text-primary font-medium">
                {transactionId}
              </span>
            </div>
            <p className="text-[11px] text-text-muted mt-0.5">
              Dialogue history provides conversational context only &bull; Grounded strictly in Verified Evidence Pack
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <div className="flex items-center space-x-1 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-[10px] font-medium">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>VEO Grounded</span>
          </div>

          {messages.length > 0 && (
            <button
              type="button"
              onClick={onResetThread}
              className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md bg-surface hover:bg-surface-muted text-text-secondary hover:text-text-primary text-[11px] font-medium border border-border transition-colors cursor-pointer"
              title="Clear conversational thread for this investigation"
            >
              <RotateCcw className="w-3 h-3 text-slate-700 dark:text-white" />
              <span>Reset Thread</span>
            </button>
          )}
        </div>
      </div>

      {/* 2. INTERACTIVE INPUT OMNIBAR */}
      <form onSubmit={handleSubmit} className="flex items-center space-x-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder={`Ask a follow-up question about ${transactionId} (e.g. bank reference, fee variance, timing)...`}
          disabled={askingQuestion}
          className="flex-1 px-3.5 py-2.5 bg-surface-muted border border-border rounded-lg text-xs text-text-primary placeholder:text-text-muted focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
        />
        <button
          type="submit"
          disabled={askingQuestion || !inputValue.trim()}
          className="px-4 py-2.5 bg-primary hover:bg-primary-dark disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors flex items-center space-x-1.5 shrink-0 cursor-pointer"
        >
          <span>Ask</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>

      {/* 3. QUICK SUGGESTION CHIPS */}
      <div className="flex items-center flex-wrap gap-1.5 text-[11px]">
        <span className="text-text-muted text-[10px] font-medium flex items-center space-x-1 mr-1">
          <Sparkles className="w-3 h-3 text-primary" />
          <span>Suggested:</span>
        </span>
        {SUGGESTED_QUESTIONS.map((q, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onAskQuestion(q)}
            disabled={askingQuestion}
            className="px-2.5 py-1 rounded-full bg-surface-muted hover:bg-surface border border-border hover:border-primary/40 text-[11px] text-text-secondary hover:text-primary transition-colors disabled:opacity-50 cursor-pointer"
          >
            {q}
          </button>
        ))}
      </div>

      {/* 4. CONVERSATION STREAM (Rendered when messages exist or query is in-flight) */}
      {(messages.length > 0 || askingQuestion) && (
        <div
          ref={chatContainerRef}
          className="mt-3 pt-3 border-t border-border space-y-4 max-h-[380px] overflow-y-auto"
        >
          {messages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={msg.id}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-1`}
              >
                {/* Speaker Header */}
                <div className="flex items-center space-x-1.5 text-[10px] text-text-secondary px-1">
                  {isUser ? (
                    <>
                      <span className="font-semibold text-text-primary">Operator</span>
                      <User className="w-3 h-3 text-slate-700 dark:text-white" />
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3 h-3 text-primary" />
                      <span className="font-semibold text-text-primary">
                        AI Settlement Analyst
                      </span>
                      {msg.llmUsed ? (
                        <span className="px-1.5 py-0.2 rounded bg-primary/10 text-primary font-mono text-[9px]">
                          {msg.model || 'LLM'}
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.2 rounded bg-surface-muted text-text-secondary border border-border font-mono text-[9px]">
                          Fallback
                        </span>
                      )}
                    </>
                  )}
                </div>

                {/* Message Bubble */}
                <div
                  className={`max-w-[85%] rounded-xl p-3 text-xs leading-relaxed ${
                    isUser
                      ? 'bg-slate-800 dark:bg-primary/90 text-white rounded-tr-none'
                      : msg.isError
                      ? 'bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 rounded-tl-none'
                      : 'bg-surface-muted border border-border text-text-primary rounded-tl-none shadow-xs'
                  }`}
                >
                  <p className="whitespace-pre-line font-sans">{msg.content}</p>

                  {/* Assistant Turn Badges & Actions */}
                  {!isUser && !msg.isError && (
                    <div className="mt-2.5 pt-2 border-t border-border-subtle flex items-center justify-between gap-2 text-[10px]">
                      <div className="flex items-center space-x-1.5">
                        {msg.validated && (
                          <span
                            className="inline-flex items-center space-x-1 text-emerald-700 dark:text-emerald-400 font-medium"
                            title="Audited by Phase 9 Validator: 0 hallucinations, 0 status contradictions"
                          >
                            <ShieldCheck className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                            <span>Validated</span>
                          </span>
                        )}

                        {msg.validationResult && !msg.validationResult.is_valid && (
                          <span
                            className="inline-flex items-center space-x-1 text-amber-700 dark:text-amber-400 font-medium"
                            title="Hallucination prevented: fallback applied"
                          >
                            <AlertTriangle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                            <span>Fallback Enforced</span>
                          </span>
                        )}
                      </div>

                      <button
                        type="button"
                        onClick={() => handleCopy(msg.id, msg.content)}
                        className="inline-flex items-center space-x-1 text-text-secondary hover:text-primary transition-colors cursor-pointer"
                        title="Copy answer to clipboard"
                      >
                        {copiedId === msg.id ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                            <span className="text-emerald-700 dark:text-emerald-400 font-medium">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3 text-slate-700 dark:text-white" />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Loading Indicator */}
          {askingQuestion && (
            <div className="flex items-start space-x-2 text-xs text-primary animate-pulse">
              <div className="p-1.5 rounded-full bg-primary/10">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
              </div>
              <div className="bg-surface-muted border border-border rounded-xl rounded-tl-none p-2.5 text-xs text-text-secondary">
                Validating against Verified Evidence Pack...
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
