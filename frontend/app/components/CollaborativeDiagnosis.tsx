"use client";

/**
 * Collaborative Diagnosis panel.
 *
 * Renders the output of POST /api/agent/complex-diagnosis:
 *   - Top-ranked candidate diagnoses with score bars + evidence pills
 *   - Recommended next tests
 *   - Clinician-facing narrative summary
 *   - Full reasoning trace (every node's inputs/outputs/confidence),
 *     collapsible because it can get long with 7+ steps
 *
 * The "Run collaborative diagnosis" button POSTs to the backend; the
 * graph runs synchronously (5-15 s typical for the four LLM calls) so
 * we show a spinner the whole time. No streaming yet — adding the SSE
 * variant is a follow-up improvement.
 */
import { useState, type ReactElement } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  Loader2,
  Play,
  AlertOctagon,
  CheckCircle2,
  XCircle,
  CircleDot,
  ChevronDown,
  ChevronRight,
  ListChecks,
  GitBranch,
  Sparkles,
} from "lucide-react";
import {
  runComplexDiagnosis,
  type ComplexDiagnosisResponse,
  type CandidateDiagnosis,
  type ReasoningStep,
} from "../lib/api";

const RARITY_TONE: Record<string, string> = {
  common: "bg-emerald-500/10 text-emerald-300 border-emerald-400/30",
  uncommon: "bg-amber-500/10 text-amber-300 border-amber-400/30",
  rare: "bg-violet-500/10 text-violet-300 border-violet-400/30",
};

const VERDICT_ICON: Record<string, ReactElement> = {
  supports: <CheckCircle2 className="w-3 h-3 text-emerald-400" />,
  contradicts: <XCircle className="w-3 h-3 text-rose-400" />,
  neutral: <CircleDot className="w-3 h-3 text-muted-foreground" />,
};

const STEP_TONE: Record<string, string> = {
  planner: "border-l-sky-400/50 bg-sky-500/5",
  llm: "border-l-violet-400/50 bg-violet-500/5",
  analyser: "border-l-emerald-400/50 bg-emerald-500/5",
  rag: "border-l-amber-400/50 bg-amber-500/5",
  verdict: "border-l-fuchsia-400/50 bg-fuchsia-500/5",
};

function CandidateCard({ candidate, rank }: { candidate: CandidateDiagnosis; rank: number }) {
  const [open, setOpen] = useState(rank === 0);
  const score = Math.max(0, Math.min(1, candidate.score || 0));
  const scorePct = Math.round(score * 100);
  const supports = (candidate.evidence || []).filter((e) => e.verdict === "supports");
  const contradicts = (candidate.evidence || []).filter((e) => e.verdict === "contradicts");

  return (
    <div className="bg-card border border-border rounded-md overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors text-left"
      >
        <div className="flex items-center justify-center w-7 h-7 rounded-full bg-primary/10 text-primary text-xs font-bold">
          #{rank + 1}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-foreground">{candidate.name}</span>
            {candidate.icd10 && (
              <span className="text-[10px] font-mono text-muted-foreground border border-border rounded px-1.5 py-0.5">
                {candidate.icd10}
              </span>
            )}
            <span
              className={`text-[10px] uppercase tracking-wider font-semibold border rounded px-1.5 py-0.5 ${
                RARITY_TONE[candidate.rarity] || RARITY_TONE.common
              }`}
            >
              {candidate.rarity}
            </span>
          </div>
          <div className="mt-1.5 h-1.5 bg-muted/40 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                score >= 0.75 ? "bg-rose-500" : score >= 0.5 ? "bg-orange-500" : score >= 0.3 ? "bg-amber-500" : "bg-emerald-500"
              }`}
              style={{ width: `${scorePct}%` }}
            />
          </div>
          <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
            <span className="font-mono">score {scorePct}%</span>
            {supports.length > 0 && (
              <span className="flex items-center gap-1 text-emerald-400">
                <CheckCircle2 className="w-3 h-3" /> {supports.length} supports
              </span>
            )}
            {contradicts.length > 0 && (
              <span className="flex items-center gap-1 text-rose-400">
                <XCircle className="w-3 h-3" /> {contradicts.length} contradicts
              </span>
            )}
          </div>
        </div>
        {open ? (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="border-t border-border"
          >
            <div className="p-3 space-y-2">
              {candidate.evidence && candidate.evidence.length > 0 ? (
                candidate.evidence.map((e, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 text-xs border-l-2 border-border pl-3 py-1"
                  >
                    {VERDICT_ICON[e.verdict] || VERDICT_ICON.neutral}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-muted-foreground">{e.source}</span>
                        <span className="font-medium text-foreground">{e.feature}</span>
                        <span className="ml-auto text-[10px] text-muted-foreground/70 font-mono">
                          w={e.weight.toFixed(2)}
                        </span>
                      </div>
                      {e.note && <div className="mt-0.5 text-muted-foreground">{e.note}</div>}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-xs italic text-muted-foreground">No evidence attached yet.</div>
              )}
              {candidate.recommended_tests && candidate.recommended_tests.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border/50">
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                    Tests for this candidate
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {candidate.recommended_tests.map((t) => (
                      <span
                        key={t}
                        className="text-[10px] bg-primary/10 text-primary border border-primary/20 rounded px-1.5 py-0.5"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function TraceStep({ step, idx }: { step: ReasoningStep; idx: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`border-l-2 pl-3 py-2 text-xs ${STEP_TONE[step.kind] || "border-l-border"}`}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-start gap-2 text-left"
      >
        <span className="font-mono text-muted-foreground/70 w-6 shrink-0">{idx + 1}.</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-foreground">{step.node}</span>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground bg-muted/40 px-1.5 py-0.5 rounded">
              {step.kind}
            </span>
            <span className="text-[10px] font-mono text-muted-foreground/60 ml-auto">
              conf {Math.round((step.confidence ?? 0) * 100)}%
            </span>
          </div>
          {step.note && <div className="mt-0.5 text-muted-foreground">{step.note}</div>}
        </div>
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
        )}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden mt-2"
          >
            <pre className="text-[10px] font-mono bg-muted/30 border border-border/50 rounded p-2 overflow-x-auto">
{JSON.stringify({ inputs: step.inputs, outputs: step.outputs }, null, 2)}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function CollaborativeDiagnosis({ patientId }: { patientId: string | null }) {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComplexDiagnosisResponse | null>(null);

  const trigger = async () => {
    setRunning(true);
    setError(null);
    try {
      const r = await runComplexDiagnosis(patientId || undefined);
      setResult(r);
      if (r.status !== "ok") setError(r.error || "Graph returned non-ok status");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-card border border-border rounded-md p-4 shadow-card space-y-4"
    >
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-md bg-violet-500/10 border border-violet-400/30 flex items-center justify-center">
          <Brain className="w-4 h-4 text-violet-300" />
        </div>
        <div className="flex-1">
          <h3 className="font-display text-sm font-semibold text-foreground">
            Collaborative diagnosis
          </h3>
          <p className="text-[11px] text-muted-foreground">
            7-node agent graph: planner → proposer → rare/related KB lookup →
            evidence gather → skeptic → ranked verdict.
          </p>
        </div>
        <button
          onClick={trigger}
          disabled={running}
          className="flex items-center gap-2 px-3 py-2 rounded-md bg-violet-500/10 hover:bg-violet-500/20 text-violet-200 text-xs font-semibold transition-colors disabled:opacity-50"
        >
          {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {running ? "Running..." : "Run collaborative diagnosis"}
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-2 text-xs text-rose-300 bg-rose-500/10 border border-rose-400/30 rounded p-2">
          <AlertOctagon className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {result && result.status === "ok" && (
        <>
          {result.summary_for_clinician && (
            <div className="border border-violet-400/20 bg-violet-500/5 rounded p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <Sparkles className="w-3.5 h-3.5 text-violet-300" />
                <span className="text-[10px] uppercase tracking-wider text-violet-300 font-semibold">
                  Clinician summary
                </span>
              </div>
              <p className="text-xs text-foreground/90 leading-relaxed">
                {result.summary_for_clinician}
              </p>
            </div>
          )}

          {result.planner_rationale && (
            <div className="text-[11px] text-muted-foreground border-l-2 border-sky-400/40 pl-3">
              <div className="text-[10px] uppercase tracking-wider text-sky-300 font-semibold mb-0.5">
                Planner gating
              </div>
              <span>{result.planner_rationale}</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {result.selected_specialties.map((s) => (
                  <span
                    key={s}
                    className="text-[10px] bg-sky-500/10 text-sky-200 border border-sky-400/30 rounded px-1.5 py-0.5"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.final_ranking.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-foreground">
                <ListChecks className="w-3.5 h-3.5" />
                Ranked differential ({result.final_ranking.length})
              </div>
              {result.final_ranking.map((c, i) => (
                <CandidateCard key={`${c.name}-${i}`} candidate={c} rank={i} />
              ))}
            </div>
          )}

          {result.recommended_next_tests.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">
                Recommended next tests
              </div>
              <div className="flex flex-wrap gap-1.5">
                {result.recommended_next_tests.map((t) => (
                  <span
                    key={t}
                    className="text-xs bg-primary/10 text-primary border border-primary/20 rounded px-2 py-1"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.traces.length > 0 && (
            <details className="border border-border rounded">
              <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground flex items-center gap-2">
                <GitBranch className="w-3.5 h-3.5" />
                Reasoning trace ({result.traces.length} steps)
              </summary>
              <div className="px-3 pb-3 space-y-1">
                {result.traces.map((s, i) => (
                  <TraceStep key={i} step={s} idx={i} />
                ))}
              </div>
            </details>
          )}
        </>
      )}

      {!result && !error && !running && (
        <p className="text-xs text-muted-foreground italic">
          Click <strong>Run collaborative diagnosis</strong> to invoke the agentic graph
          on the latest snapshot. Typical runtime 5-15 s for the four LLM calls.
        </p>
      )}
    </motion.div>
  );
}
