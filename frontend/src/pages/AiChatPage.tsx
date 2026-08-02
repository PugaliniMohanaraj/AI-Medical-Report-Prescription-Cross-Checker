import { useMemo, useState, type FormEvent } from "react";

import { getErrorMessage } from "@/api/client";
import { ingestRagDocuments, queryRag } from "@/api/endpoints";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { demoPatient } from "@/data/demoPatient";
import type { RagQueryResponse, RagSource } from "@/types/api";

const SAMPLE_DOCS = `Visit 2023-02-10
Patient Jane Doe diagnosed with Type 2 Diabetes Mellitus on 2023-02-10 at City General Hospital. Started Metformin 500mg twice daily.

---
Visit 2024-06-15
Follow-up visit 2024-06-15. HbA1c rose from 6.8% to 7.4%. Added Lisinopril 10mg daily for hypertension. Allergy: Penicillin.

---
Prescription analysis
High severity interaction between Warfarin and Aspirin due to increased bleeding risk. Allergy conflict: Amoxicillin with Penicillin allergy.`;

const EXAMPLE_QUESTIONS = [
  "When was diabetes diagnosed?",
  "Did any medicine conflict?",
  "What changed between visits?",
];

function parseDocuments(raw: string) {
  return raw
    .split(/\n---\n/)
    .map((block, index) => {
      const lines = block.trim().split("\n");
      const title = lines[0] || `Document ${index + 1}`;
      const content = lines.slice(1).join("\n").trim() || block.trim();
      return {
        document_id: `doc-${index + 1}`,
        title,
        content,
        source: "manual",
        patient_id: demoPatient.id,
      };
    })
    .filter((doc) => doc.content);
}

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
  const [corpus, setCorpus] = useState(SAMPLE_DOCS);
  const [question, setQuestion] = useState(EXAMPLE_QUESTIONS[0]);
  const [result, setResult] = useState<RagQueryResponse | null>(null);
  const [ingestMessage, setIngestMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const documents = useMemo(() => parseDocuments(corpus), [corpus]);

  const onAsk = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const ingest = await ingestRagDocuments({ patient_id: demoPatient.id, documents });
      setIngestMessage(ingest.message);
      const response = await queryRag({
        question: question.trim(),
        patient_id: demoPatient.id,
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

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Chat"
        description="Ask follow-up questions over ingested reports with confidence scores and citations."
        actions={<ConfidenceBadge confidence={result?.confidence} />}
      />

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Ask a clinical question">
          <div className="mb-3 flex flex-wrap gap-2">
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
          <form onSubmit={(event) => void onAsk(event)} className="flex flex-col gap-3 sm:flex-row">
            <input
              className="field"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about diagnosis dates, conflicts, visit changes…"
            />
            <button type="submit" className="btn-primary shrink-0" disabled={busy}>
              {busy ? "Thinking…" : "Ask"}
            </button>
          </form>

          {ingestMessage && (
            <p className="mt-3 text-xs text-surface-500">{ingestMessage}</p>
          )}
          {error && (
            <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100">
              {error}
            </div>
          )}

          {result && (
            <div className="mt-5 space-y-4">
              <div className="rounded-2xl border border-brand-100 bg-brand-50/70 p-4 dark:border-brand-800 dark:bg-brand-950/40">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold">Answer</h3>
                  <ConfidenceBadge confidence={result.confidence} />
                </div>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{result.answer}</p>
              </div>
              <div className="space-y-3">
                <h3 className="font-semibold">Supporting references</h3>
                {result.sources.map((source) => (
                  <SourceCard
                    key={`${source.document_id}-${source.excerpt.slice(0, 20)}`}
                    source={source}
                  />
                ))}
              </div>
            </div>
          )}
        </Panel>

        <Panel title="Knowledge corpus" description="Documents indexed for retrieval">
          <textarea
            className="field min-h-[28rem] font-mono text-xs"
            value={corpus}
            onChange={(event) => setCorpus(event.target.value)}
          />
        </Panel>
      </div>
    </div>
  );
}
