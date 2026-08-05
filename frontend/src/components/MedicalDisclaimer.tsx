export function MedicalDisclaimer({ text }: { text?: string | null }) {
  return (
    <div
      role="note"
      className="rounded-xl border border-amber-300/70 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-100"
    >
      {text ||
        "This tool supports clinical review only. It is not a diagnosis. Consult a doctor or pharmacist for high-risk or low-confidence findings."}
    </div>
  );
}
