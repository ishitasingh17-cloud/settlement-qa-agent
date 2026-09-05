/**
 * client/src/components/investigation/ExplanationDualView.jsx
 * 
 * Dual Explanation Panel rendering internal support diagnosis,
 * merchant-facing copy script with 1-click clipboard integration,
 * AI safety validation badges, and interactive follow-up Q&A.
 */

import React, { useState } from 'react';
import {
  Sparkles,
  Copy,
  Check,
  ShieldCheck,
  MessageSquare,
  Send,
  Loader2,
  AlertCircle,
  HelpCircle,
  Bot,
} from 'lucide-react';

const QA_CHIPS = [
  'Was the customer charged twice?',
  'What exact fee was deducted?',
  'What is the bank clearing status?',
];

export default function ExplanationDualView({
  explanation,
  llmUsed,
  onAskQuestion,
  askingQuestion,
  transactionId,
}) {
  const [copied, setCopied] = useState(false);
  const [questionInput, setQuestionInput] = useState('');

  if (!explanation) return null;

  const {
    internal_summary,
    merchant_friendly_response,
    merchant_explanation,
    answer,
    provider,
    model,
    validated,
    validation_result,
  } = explanation;

  const merchantText = merchant_friendly_response || merchant_explanation || '';

  const handleCopyMerchant = async () => {
    if (!merchantText) return;
    try {
      await navigator.clipboard.writeText(merchantText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const handleSendQuestion = (e) => {
    e.preventDefault();
    if (questionInput.trim() && !askingQuestion) {
      onAskQuestion(questionInput.trim());
      setQuestionInput('');
    }
  };

  const handleChipClick = (q) => {
    onAskQuestion(q);
  };

  return (
    <div className="bg-ai-tint border border-ai-border rounded-xl p-5 shadow-xs space-y-5">
      {/* Header & AI Provenance Tag */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-border-subtle gap-2">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
            <Sparkles className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-text-primary">
              AI Determined Finding & Merchant Communications
            </h3>
            <p className="text-[11px] text-text-secondary">
              Grounded strictly in Verified Evidence Pack (VEO)
            </p>
          </div>
        </div>

        {/* AI Mode & Validation Badges */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {llmUsed ? (
            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary font-medium text-[11px]">
              <Bot className="w-3.5 h-3.5 text-primary" />
              <span>AI Analyst ({model || 'gemini-1.5-flash'})</span>
            </span>
          ) : (
            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-surface-muted border border-border text-text-secondary font-medium text-[11px]">
              <ShieldCheck className="w-3.5 h-3.5 text-slate-700 dark:text-white" />
              <span>Deterministic Rule-Based Engine</span>
            </span>
          )}

          {validated && (
            <span
              className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-medium text-[11px]"
              title="Verified: 0 hallucinations, 0 status contradictions, exact decimal arithmetic"
            >
              <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
              <span>Validated Against Evidence</span>
            </span>
          )}
        </div>
      </div>

      {/* Internal Support Summary */}
      <div className="space-y-1.5">
        <span className="text-xs font-bold uppercase tracking-wider text-text-primary block">
          Internal Support Determined Finding
        </span>
        <div className="bg-surface/80 p-4 rounded-lg border border-border text-xs text-text-primary leading-relaxed whitespace-pre-line font-sans">
          {internal_summary}
        </div>
      </div>

      {/* Merchant-Ready Response (The Copy Deck) */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center space-x-1.5">
            <span>Customer-Safe Merchant Response</span>
          </span>

          <button
            onClick={handleCopyMerchant}
            className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-all ${
              copied
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-surface hover:bg-surface-muted text-text-primary border border-border hover:border-primary/40'
            }`}
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-white" />
                <span>Copied to Clipboard!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-slate-700 dark:text-white" />
                <span>Copy Merchant Response</span>
              </>
            )}
          </button>
        </div>

        <div className="bg-surface p-4 rounded-lg border-l-4 border-l-emerald-500 border border-border text-xs text-text-primary leading-relaxed shadow-2xs italic font-sans">
          &ldquo;{merchantText}&rdquo;
        </div>
      </div>

      {/* Direct Answer Display (if query was an explicit question) */}
      {answer && (
        <div className="pt-3 border-t border-border-subtle space-y-1.5">
          <div className="flex items-center space-x-1.5">
            <MessageSquare className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs font-bold uppercase tracking-wider text-primary">
              Direct Query Answer
            </span>
          </div>
          <div className="p-3.5 rounded-lg bg-surface border border-primary/20 text-xs text-text-primary leading-relaxed font-sans shadow-2xs">
            {answer}
          </div>
        </div>
      )}
    </div>
  );
}
