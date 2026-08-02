import { useMemo, useState, type FormEvent } from "react";

import { getErrorMessage } from "@/api/client";
import { ingestRagDocuments, queryRag } from "@/api/endpoints";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
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
        patient_id: "demo-patient",
      };
    })
    .filter((doc) => doc.content);
}

function SourceCard({ source }: { source: RagSource }) {
  return (
    <article className="rounded-xl border border-brand-100 bg-white/80 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-brand-900">
          {source.title || source.document_id}
        </p>
        {typeof source.score === "number" && (
          <span className="text-xs text-brand-500">score {source.score.toFixed(3)}</span>
        )}
      </div>
      <p className="mt-2 text-sm leading-relaxed text-brand-800">{source.excerpt}</p>
      <p className="mt-2 font-mono text-[11px] text-brand-500/80">{source.document_id}</p>
    </article>
  );
}

export function RagPage() {
  const [corpus, setCorpus] = useState(SAMPLE_DOCS);
  const [question, setQuestion] = useState(EXAMPLE_QUESTIONS[0]);
  const [result, setResult] = useState<RagQueryResponse | null>(null);
  const [ingestMessage, setIngestMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const documents = useMemo(() => parseDocuments(corpus), [corpus]);

  const onIngest = async () => {
    setBusy(true);
    setError(null);
    setIngestMessage(null);
    try {
      const response = await ingestRagDocuments({
        patient_id: "demo-patient",
        documents,
      });
      setIngestMessage(response.message);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const onAsk = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    try {
      // Ensure corpus is indexed for the demo flow.
      await ingestRagDocuments({ patient_id: "demo-patient", documents });
      const response = await queryRag({
        question: question.trim(),
        patient_id: "demo-patient",
        top_k: 5,
      });
      setResult(response);
      setIngestMessage((prev) => prev ?? "Corpus indexed for this question.");
    } catch (err) {
      setResult(null);
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl font-semibold text-brand-900">Ask AI</h1>
        <ConfidenceBadge confidence={result?.confidence} />
      </div>
      <p className="max-w-2xl text-brand-700/80">
        RAG over ingested medical notes. Ask about diagnosis dates, medicine conflicts,
        or changes between visits — answers include confidence and supporting references.
      </p>

      <label className="block space-y-2">
        <span className="text-sm font-medium text-brand-800">
          Knowledge corpus (separate documents with a line containing only ---)
        </span>
        <textarea
          value={corpus}
          onChange={(event) => setCorpus(event.target.value)}
          rows={10}
          className="w-full rounded-xl border border-brand-100 bg-white/80 px-3 py-2 font-mono text-sm outline-none ring-brand-500 focus:ring-2"
        />
      </label>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={() => void onIngest()}
          className="rounded-lg border border-brand-100 bg-white px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50 disabled:opacity-50"
        >
          Ingest corpus
        </button>
        {EXAMPLE_QUESTIONS.map((item) => (
          <button
            key={item}
            type="button"
            disabled={busy}
            onClick={() => {
              setQuestion(item);
            }}
            className="rounded-lg border border-brand-100 bg-brand-50 px-3 py-2 text-xs font-medium text-brand-700 hover:bg-brand-100 disabled:opacity-50"
          >
            {item}
          </button>
        ))}
      </div>

      <form onSubmit={(event) => void onAsk(event)} className="flex flex-col gap-3 sm:flex-row">
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a follow-up question…"
          className="flex-1 rounded-xl border border-brand-100 bg-white/80 px-3 py-2.5 text-sm outline-none ring-brand-500 focus:ring-2"
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {busy ? "Working…" : "Ask"}
        </button>
      </form>

      {ingestMessage && (
        <p className="rounded-xl border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-700">
          {ingestMessage}
        </p>
      )}

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-brand-100 bg-white/80 p-5">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="font-display text-xl font-semibold text-brand-900">Answer</h2>
              <ConfidenceBadge confidence={result.confidence} />
              {result.llm_provider && (
                <span className="text-xs text-brand-500">model: {result.llm_provider}</span>
              )}
              {result.retrieval_backend && (
                <span className="text-xs text-brand-500">index: {result.retrieval_backend}</span>
              )}
            </div>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-brand-900">
              {result.answer}
            </p>
          </div>

          <div className="space-y-3">
            <h2 className="font-display text-xl font-semibold text-brand-900">
              Supporting references
            </h2>
            {result.sources.length === 0 ? (
              <p className="text-sm text-brand-500">No supporting documents retrieved.</p>
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {result.sources.map((source) => (
                  <SourceCard
                    key={`${source.document_id}-${source.score}-${source.excerpt.slice(0, 24)}`}
                    source={source}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
