export const demoPatient = {
  id: "demo-patient",
  name: "Jane Doe",
  age: 54,
  sex: "F",
  mrn: "MRN-10482",
  primaryDiagnosis: "Type 2 Diabetes Mellitus, Hypertension",
  allergies: ["Penicillin"],
  physician: "Dr. Smith",
  hospital: "City General Hospital",
};

export const demoVisits = [
  {
    id: "v1",
    date: "2024-01-10",
    type: "Outpatient",
    summary: "Diabetes follow-up. Metformin continued. Baseline labs ordered.",
    diagnosis: ["Type 2 Diabetes Mellitus"],
    medicines: [
      { name: "Metformin", dosage: "500mg", frequency: "twice daily", duration: "30 days" },
    ],
    labs: [
      { test_name: "HbA1c", value: "6.8", unit: "%" },
      { test_name: "Creatinine", value: "0.9", unit: "mg/dL" },
      { test_name: "LDL", value: "110", unit: "mg/dL" },
    ],
  },
  {
    id: "v2",
    date: "2024-06-15",
    type: "Outpatient",
    summary: "Rising HbA1c. Added Lisinopril for hypertension.",
    diagnosis: ["Type 2 Diabetes Mellitus", "Hypertension"],
    medicines: [
      { name: "Metformin", dosage: "1000mg", frequency: "twice daily", duration: "30 days" },
      { name: "Lisinopril", dosage: "10mg", frequency: "once daily", duration: "ongoing" },
    ],
    labs: [
      { test_name: "HbA1c", value: "7.4", unit: "%" },
      { test_name: "Creatinine", value: "0.95", unit: "mg/dL" },
      { test_name: "LDL", value: "128", unit: "mg/dL" },
    ],
  },
  {
    id: "v3",
    date: "2024-12-01",
    type: "Clinic review",
    summary: "Worsening glycemic control. Lipid therapy discussed. Warfarin + aspirin noted.",
    diagnosis: ["Type 2 Diabetes Mellitus", "Hypertension", "Atrial fibrillation"],
    medicines: [
      { name: "Metformin", dosage: "1000mg", frequency: "twice daily", duration: "30 days" },
      { name: "Lisinopril", dosage: "10mg", frequency: "once daily", duration: "ongoing" },
      { name: "Warfarin", dosage: "5mg", frequency: "once daily", duration: "ongoing" },
      { name: "Aspirin", dosage: "81mg", frequency: "once daily", duration: "ongoing" },
      { name: "Amoxicillin", dosage: "500mg", frequency: "TID", duration: "7 days" },
    ],
    labs: [
      { test_name: "HbA1c", value: "8.1", unit: "%" },
      { test_name: "Creatinine", value: "1.0", unit: "mg/dL" },
      { test_name: "LDL", value: "145", unit: "mg/dL" },
    ],
  },
] as const;

export const demoMedicinesText = demoVisits[demoVisits.length - 1].medicines
  .map((m) => `${m.name} | ${m.dosage} | ${m.frequency} | ${m.duration}`)
  .join("\n");

export const demoAllergiesText = demoPatient.allergies.join(", ");

export const demoLabVisits = demoVisits.map((visit) => ({
  visit_id: visit.id,
  visit_date: visit.date,
  labs: visit.labs.map((lab) => ({ ...lab })),
}));
