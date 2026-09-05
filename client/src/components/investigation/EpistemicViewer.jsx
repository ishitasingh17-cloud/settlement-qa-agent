/**
 * client/src/components/investigation/EpistemicViewer.jsx
 * 
 * Epistemic Honesty Breakdown:
 * Strict separation of Known Facts (verified), Inferred Facts (deduced), and Unknowns (unrecorded).
 */

import React from 'react';
import { ShieldCheck, Cpu, HelpCircle, Check, ArrowRight } from 'lucide-react';

export default function EpistemicViewer({ epistemicModel }) {
  if (!epistemicModel) return null;

  const { known_facts = [], inferences = [], unknowns = [] } = epistemicModel;

  return (
    <div className="bg-surface border border-border rounded-xl p-5 shadow-xs space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
        <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">
          Epistemic Honesty Model
        </h3>
        <span className="text-xs text-text-muted font-mono">
          Known · Inferred · Unknown
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 1. Verified Known Facts */}
        <div className="space-y-2 p-3.5 rounded-lg bg-emerald-50/40 border border-emerald-200/80">
          <div className="flex items-center space-x-2 text-emerald-800 dark:text-emerald-300">
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <div>
              <span className="text-xs font-bold uppercase tracking-wider block">Verified / Known Facts</span>
              <span className="text-[10px] text-emerald-700/80 dark:text-emerald-400/80 font-normal">Directly supported by supplied records</span>
            </div>
          </div>
          <ul className="space-y-1.5 text-xs text-text-primary pt-1">
            {known_facts.length > 0 ? (
              known_facts.map((fact, idx) => (
                <li key={idx} className="flex items-start space-x-1.5">
                  <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0" />
                  <span className="leading-relaxed">{fact}</span>
                </li>
              ))
            ) : (
              <li className="text-text-muted italic text-[11px]">No facts verified</li>
            )}
          </ul>
        </div>

        {/* 2. Deterministic Inferences */}
        <div className="space-y-2 p-3.5 rounded-lg bg-blue-50/40 border border-blue-200/80">
          <div className="flex items-center space-x-2 text-blue-800 dark:text-blue-300">
            <Cpu className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
            <div>
              <span className="text-xs font-bold uppercase tracking-wider block">Deterministic Inferences</span>
              <span className="text-[10px] text-blue-700/80 dark:text-blue-400/80 font-normal">Derived via explicit reconciliation rules</span>
            </div>
          </div>
          <ul className="space-y-1.5 text-xs text-text-primary pt-1">
            {inferences.length > 0 ? (
              inferences.map((inf, idx) => (
                <li key={idx} className="flex items-start space-x-1.5">
                  <ArrowRight className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" />
                  <span className="leading-relaxed">{inf}</span>
                </li>
              ))
            ) : (
              <li className="text-text-muted italic text-[11px]">No active inferences</li>
            )}
          </ul>
        </div>

        {/* 3. Honest Unknowns */}
        <div className="space-y-2 p-3.5 rounded-lg bg-amber-50/40 border border-amber-200/80">
          <div className="flex items-center space-x-2 text-amber-800 dark:text-amber-300">
            <HelpCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
            <div>
              <span className="text-xs font-bold uppercase tracking-wider block">Honest Unknowns / Gaps</span>
              <span className="text-[10px] text-amber-700/80 dark:text-amber-400/80 font-normal">Not established from available data</span>
            </div>
          </div>
          <ul className="space-y-1.5 text-xs text-text-primary pt-1">
            {unknowns.length > 0 ? (
              unknowns.map((unk, idx) => (
                <li key={idx} className="flex items-start space-x-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 dark:bg-amber-400 mt-1.5 shrink-0" />
                  <span className="leading-relaxed">{unk}</span>
                </li>
              ))
            ) : (
              <li className="text-text-muted italic text-[11px]">No unresolved unknowns</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
