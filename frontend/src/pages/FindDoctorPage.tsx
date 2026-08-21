import { useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getErrorMessage } from "@/api/client";
import { recommendDoctors } from "@/api/endpoints";
import { MedicalDisclaimer } from "@/components/MedicalDisclaimer";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { usePatient } from "@/hooks/usePatient";
import type { DoctorRecommendResponse } from "@/types/api";

const AVAILABILITY_OPTIONS = [
  { id: "anytime", label: "Anytime" },
  { id: "this_week", label: "This week" },
  { id: "evenings", label: "Evenings" },
  { id: "weekends", label: "Weekends" },
];

export function FindDoctorPage() {
  const { overview } = usePatient();
  const [searchParams] = useSearchParams();
  const [location, setLocation] = useState("Jaffna");
  const [availability, setAvailability] = useState(searchParams.get("availability") || "anytime");
  const [radiusKm, setRadiusKm] = useState(8);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DoctorRecommendResponse | null>(null);

  const highFlags = useMemo(() => {
    const findings = overview?.findings ?? [];
    const risky = findings.filter((f) => f.severity === "High");
    return risky.length ? risky : findings;
  }, [overview?.findings]);

  const abnormalLabs = overview?.lab_trends?.abnormal_trends.map((t) => t.test_name) ?? [];
  const diagnoses = [...new Set(overview?.visits.flatMap((v) => v.diagnosis) ?? [])];

  const onSearch = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!location.trim()) {
      setError("Enter your city or area.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const data = await recommendDoctors({
        location: location.trim(),
        availability,
        radius_km: radiusKm,
        flags: highFlags.map((flag) => ({
          type: flag.type,
          severity: flag.severity,
          title: flag.title,
          explanation: flag.explanation,
          related_medicines: flag.related_medicines,
        })),
        diagnosis: diagnoses,
        primary_diagnosis: overview?.primary_diagnosis,
        abnormal_labs: abnormalLabs,
      });
      setResult(data);
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
        title="Find a local doctor"
        description="When a flag is high-risk or uncertain, search real nearby clinics from public map data."
      />
      <MedicalDisclaimer text={result?.disclaimer} />

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel title="1. Your situation" description="Specialty is chosen from the flagged issue — not guessed as a diagnosis.">
          {highFlags.length === 0 ? (
            <p className="text-sm text-surface-600 dark:text-surface-300">
              No safety flags yet. You can still search a GP nearby, or{" "}
              <Link to="/uploads" className="font-medium text-brand-500 underline">
                upload reports
              </Link>{" "}
              first.
            </p>
          ) : (
            <ul className="space-y-2">
              {highFlags.slice(0, 4).map((flag) => (
                <li
                  key={`${flag.type}-${flag.title}`}
                  className="rounded-xl border border-surface-200 px-3 py-2 text-sm dark:border-surface-700"
                >
                  <span className="text-[11px] font-semibold uppercase text-red-600">{flag.severity}</span>
                  <p className="font-medium">{flag.title}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="2. Location & availability">
          <form className="space-y-4" onSubmit={(event) => void onSearch(event)}>
            <label className="block space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-surface-500">City or area</span>
              <input
                className="field"
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                placeholder="e.g. Jaffna, Colombo 07"
              />
            </label>
            <fieldset>
              <legend className="text-xs font-semibold uppercase tracking-wide text-surface-500">
                When can you consult?
              </legend>
              <div className="mt-2 flex flex-wrap gap-2">
                {AVAILABILITY_OPTIONS.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setAvailability(option.id)}
                    className={
                      availability === option.id
                        ? "rounded-full bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white"
                        : "rounded-full border border-surface-200 px-3 py-1.5 text-xs dark:border-surface-700"
                    }
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </fieldset>
            <label className="block space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-surface-500">
                Search radius ({radiusKm} km)
              </span>
              <input
                type="range"
                min={3}
                max={30}
                step={1}
                value={radiusKm}
                onChange={(event) => setRadiusKm(Number(event.target.value))}
                className="w-full"
              />
            </label>
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "Searching public listings…" : "Find nearby doctors"}
            </button>
          </form>
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </Panel>
      </div>

      {result && (
        <Panel
          title="3. Nearby listings"
          description={`${result.recommended_specialty} · ${result.source === "google_places" ? "Google Places" : "OpenStreetMap"}`}
        >
          <p className="text-sm text-surface-600 dark:text-surface-300">{result.specialty_reason}</p>
          {result.location_resolved && (
            <p className="mt-1 text-xs text-surface-500">Resolved location: {result.location_resolved}</p>
          )}

          {result.no_results ? (
            <div className="mt-4 rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
              <p className="font-semibold">No doctors or clinics found.</p>
              <p className="mt-1">{result.message}</p>
              {result.suggestion && <p className="mt-1">{result.suggestion}</p>}
            </div>
          ) : (
            <ul className="mt-4 divide-y divide-surface-200 dark:divide-surface-700">
              {result.results.map((place) => (
                <li key={`${place.name}-${place.address}`} className="py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-display text-lg font-semibold">{place.name}</p>
                      <p className="text-sm capitalize text-brand-600 dark:text-brand-100">{place.specialty}</p>
                      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">{place.address}</p>
                      <div className="mt-2 flex flex-wrap gap-3 text-xs text-surface-500">
                        {place.distance_km != null && <span>{place.distance_km} km away</span>}
                        {place.phone && <span>{place.phone}</span>}
                        {place.rating != null && <span>Rating {place.rating.toFixed(1)}</span>}
                        {place.opening_hours && <span>{place.opening_hours}</span>}
                        {place.matches_availability && <span className="font-medium text-brand-600">Fits availability</span>}
                      </div>
                    </div>
                    {place.maps_url && (
                      <a
                        href={place.maps_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-secondary"
                      >
                        Open map
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}
    </div>
  );
}
