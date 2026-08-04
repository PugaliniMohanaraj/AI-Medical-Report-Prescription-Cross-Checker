import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { getErrorMessage } from "@/api/client";
import { queryRag } from "@/api/endpoints";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { MedicalDisclaimer } from "@/components/MedicalDisclaimer";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { usePatient } from "@/hooks/usePatient";
import type { RagQueryResponse, RagSource } from "@/types/api";

const EXAMPLE_QUESTIONS = [
  "When was diabetes diagnosed?",
  "Did any medicine conflict with an allergy?",
  "What changed between visits?",
];

function SourceCard({ source }: { source: RagSource }) {
  return (
    <article className="rounded-xl border border-surface-200 bg-surface-50/80 p-4 dark:border-surface-700 dark:bg-surface-950/50">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold">{source.title || source.document_id}</p>
        {typeof source.score === "number" && (
          <span className="text-xs text-surface-500">score {source.score.toFixed(3)}</span>
        )}
      </div>
      <p className="mt-2 text-sm leading-relaxed text-surface-700 dark:text-surface-200">{source.excerpt}</p>
    </article>
  );
}

export function AiChatPage() {
  const { overview } = usePatient();
  const [question, setQuestion] = useState(EXAMPLE_QUESTIONS[0]);
  const [result, setResult] = useState<RagQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onAsk = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!question.trim() || !overview?.patient_id) return;
    setBusy(true);
    setError(null);
    try {
      const response = await queryRag({
        question: question.trim(),
        patient_id: overview.patient_id,
        top_k: 5,
      });
      setResult(response);
    } catch (err) {
      setResult(null);
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const lowConfidence = (result?.confidence.score ?? 1) < 0.45;

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Chat"
        description="Ask follow-up questions across uploaded reports with confidence scores and citations."
        actions={<ConfidenceBadge confidence={result?.confidence} />}
      />

      <MedicalDisclaimer text={overview?.disclaimer} />

      {!overview?.has_extractions && (
        <Panel>
          <p className="text-sm text-surface-500">
            Upload and analyze reports first so chat can reason over your documents.
          </p>
          <Link to="/uploads" className="btn-primary mt-4 inline-flex">
            Go to uploads
          </Link>
        </Panel>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Ask a clinical question">
          <form className="space-y-3" onSubmit={(event) => void onAsk(event)}>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUESTIONS.map((item) => (
                <button
                  key={item}
                  type="button"
                  className="rounded-full border border-surface-200 px-3 py-1 text-xs dark:border-surface-700"
                  onClick={() => setQuestion(item)}
                >
                  {item}
                </button>
              ))}
            </div>
            <textarea
              className="field min-h-28"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about diagnosis dates, conflicts, visit changes…"
            />
            <button type="submit" className="btn-primary" disabled={busy || !overview?.has_extractions}>
              {busy ? "Thinking…" : "Ask"}
            </button>
          </form>
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </Panel>

        <Panel title="Answer">
          {!result ? (
            <p className="text-sm text-surface-500">Answers appear here with supporting sources.</p>
          ) : (
            <div className="space-y-4">
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{result.answer}</p>
              {lowConfidence && (
                <p className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
                  Low confidence answer. Consult a doctor or pharmacist before acting on this.
                </p>
              )}
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-surface-500">Sources</p>
                {result.sources.map((source) => (
                  <SourceCard key={`${source.document_id}-${source.excerpt.slice(0, 24)}`} source={source} />
                ))}
              </div>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
