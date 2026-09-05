/**
 * client/src/App.jsx
 * 
 * PS-8 Settlement Investigation Cockpit Root Workspace.
 * Composes Header, Sidebar, Universal Search Bar, dynamic investigation modules,
 * and the Phase 12 Exception Dashboard.
 */

import React, { useState } from 'react';
import { ArrowLeft, ChevronDown, ChevronUp, Layers } from 'lucide-react';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import SearchBar from './components/investigation/SearchBar';
import DiagnosisHeader from './components/investigation/DiagnosisHeader';
import SystemInspector from './components/investigation/SystemInspector';
import ReferenceChain from './components/investigation/ReferenceChain';
import TimelineView from './components/investigation/TimelineView';
import ExplanationDualView from './components/investigation/ExplanationDualView';
import EpistemicViewer from './components/investigation/EpistemicViewer';
import ProgressLoader from './components/investigation/ProgressLoader';
import EmptyState from './components/investigation/EmptyState';
import ErrorState from './components/investigation/ErrorState';
import FollowUpChat from './components/conversation/FollowUpChat';
import ExceptionDashboard from './components/dashboard/ExceptionDashboard';
import { useInvestigation } from './hooks/useInvestigation';

export default function App() {
  const [currentView, setCurrentView] = useState('investigate'); // 'investigate' | 'exceptions'
  const [navigatedFromDashboard, setNavigatedFromDashboard] = useState(false);
  const [showForensics, setShowForensics] = useState(true);
  React.useEffect(() => {
    document.documentElement.classList.remove('dark');
    document.documentElement.removeAttribute('data-theme');
    try {
      localStorage.removeItem('settlement_qa_theme');
    } catch {}
  }, []);

  const {
    data,
    loading,
    loadingStep,
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
  } = useInvestigation();

  // Handler for drill-down from Exception Dashboard
  const handleDrillDownFromDashboard = (transactionId) => {
    // Reset conversation thread to ensure context isolation for Phase 11
    resetConversationThread();
    setNavigatedFromDashboard(true);
    setCurrentView('investigate');
    executeInvestigation(transactionId);
  };

  // Guarantee that on investigation load or query execution, viewport displays primary result
  React.useEffect(() => {
    if (data && currentView === 'investigate') {
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
  }, [data?.transaction_id, currentView]);

  const handleGlobalReset = () => {
    reset();
    setCurrentView('investigate');
    setNavigatedFromDashboard(false);
  };

  const handleViewChange = (view) => {
    setCurrentView(view);
    if (view === 'exceptions') {
      setNavigatedFromDashboard(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col font-sans text-text-primary antialiased">
      {/* Top Application Header */}
      <Header
        onReset={handleGlobalReset}
        currentView={currentView}
        onViewChange={handleViewChange}
        exceptionCount={17}
      />

      {/* Main Layout: Sidebar + Cockpit Content */}
      <div className="flex-1 flex flex-col md:flex-row">
        {/* Navigation Sidebar */}
        <Sidebar
          onSelectTransaction={(id) => {
            setNavigatedFromDashboard(false);
            executeInvestigation(id);
          }}
          activeId={data?.transaction_id}
          history={history}
          currentView={currentView}
          onViewChange={handleViewChange}
          exceptionCount={17}
        />

        {/* Primary Workspace Canvas */}
        <main className="flex-1 max-w-6xl mx-auto p-4 md:p-6 lg:p-8 space-y-6 w-full">
          {currentView === 'exceptions' ? (
            /* Phase 12 Exception Dashboard */
            <div className="animate-in fade-in duration-200">
              <ExceptionDashboard onSelectTransaction={handleDrillDownFromDashboard} />
            </div>
          ) : (
            /* Phase 10 & 11 Investigation Workspace */
            <>
              {/* Back to Exceptions Queue Breadcrumb Bar */}
              {navigatedFromDashboard && (
                <div className="flex items-center justify-between bg-surface border border-border px-4 py-2.5 rounded-lg text-xs animate-in slide-in-from-top duration-200">
                  <div className="flex items-center space-x-2 text-text-secondary">
                    <span className="font-semibold text-text-primary">Drill-down active</span>
                    <span>&bull;</span>
                    <span>Transaction loaded from Exception Queue</span>
                  </div>
                  <button
                    onClick={() => setCurrentView('exceptions')}
                    className="inline-flex items-center space-x-1.5 text-xs font-medium text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300 transition-colors"
                  >
                    <ArrowLeft className="w-3.5 h-3.5 text-slate-700 dark:text-white" />
                    <span>Back to Exception Queue</span>
                  </button>
                </div>
              )}

              {/* Universal Investigation Search Bar */}
              <SearchBar
                onSearch={(q) => {
                  setNavigatedFromDashboard(false);
                  executeInvestigation(q);
                }}
                loading={loading}
                initialValue={activeQuery}
              />

              {/* Dynamic State Rendering */}
              {loading ? (
                <ProgressLoader query={activeQuery} stepInfo={loadingStep} />
              ) : error ? (
                <ErrorState
                  error={error}
                  onRetryQuery={(id) => executeInvestigation(id)}
                />
              ) : data ? (
                <div className="space-y-6 pb-14 animate-in fade-in duration-300">
                  {/* TIER 1: Primary Investigation Result & Follow-Up Q&A */}
                  <section className="space-y-6">
                    <DiagnosisHeader investigation={data} />

                    {/* Follow-Up Q&A: Right after the primary shown investigation result */}
                    <FollowUpChat
                      transactionId={data.transaction_id}
                      messages={conversationMessages}
                      askingQuestion={askingQuestion}
                      onAskQuestion={askQuestion}
                      onResetThread={resetConversationThread}
                    />

                    <SystemInspector evidencePack={data.evidence_pack} />
                  </section>

                  {/* TIER 2: Secondary / Expandable Forensic Deep-Dive (Graph, Timeline, Epistemic Honesty) */}
                  <section className="bg-surface border border-border rounded-xl p-4 shadow-xs space-y-4">
                    <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
                      <div className="flex items-center space-x-2">
                        <Layers className="w-4 h-4 text-primary" />
                        <div>
                          <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">
                            Forensic Deep-Dive: Graph, Timeline & Epistemic Model
                          </h3>
                          <p className="text-[11px] text-text-muted">
                            Cross-System Reference Topology · Chronological Lifecycle · Epistemic Truth Boundaries
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowForensics((prev) => !prev)}
                        className="inline-flex items-center space-x-1.5 px-2.5 py-1 text-xs font-semibold text-text-secondary hover:text-text-primary bg-surface-muted border border-border rounded-lg transition-colors cursor-pointer"
                      >
                        <span>{showForensics ? 'Collapse Deep-Dive' : 'Expand Deep-Dive'}</span>
                        {showForensics ? (
                          <ChevronUp className="w-3.5 h-3.5 text-slate-700 dark:text-white" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5 text-slate-700 dark:text-white" />
                        )}
                      </button>
                    </div>

                    {showForensics && (
                      <div className="space-y-6 pt-2 animate-in fade-in duration-200">
                        {/* 6. Reference Resolution Graph with Hub-and-Spoke Topology */}
                        <ReferenceChain
                          resolutionPath={data.evidence_pack.resolution_path}
                          evidencePack={data.evidence_pack}
                        />

                        {/* 7 & 8. Lifecycle Timeline & Epistemic Honesty Model */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                          <TimelineView timeline={data.evidence_pack.timeline} />
                          <EpistemicViewer epistemicModel={data.evidence_pack.epistemic_model} />
                        </div>
                      </div>
                    )}
                  </section>

                  {/* TIER 3: Final Communication Layer (Support Ops, Merchant Copy Deck) */}
                  <section className="space-y-6">
                    {/* 9 & 10. AI Explanation & Merchant Copy Script */}
                    <ExplanationDualView
                      explanation={data.explanation}
                      llmUsed={data.llm_used}
                      transactionId={data.transaction_id}
                    />
                  </section>
                </div>
              ) : (
                <EmptyState onSelectId={(id) => executeInvestigation(id)} />
              )}
            </>
          )}
        </main>
      </div>

      {/* Cockpit Status Bar Footer */}
      <footer className="border-t border-border py-3 px-6 text-center text-xs text-text-muted bg-surface flex flex-col sm:flex-row items-center justify-between gap-2">
        <span>PS-8: Settlement Q&A Agent &bull; Fintech Support & Investigation Cockpit</span>
        <span className="font-mono text-[11px]">Strict Trust Boundary: Deterministic Truth Engine</span>
      </footer>
    </div>
  );
}
