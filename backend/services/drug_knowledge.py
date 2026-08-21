"""Curated drug knowledge for prescription conflict analysis.

This is a competition-oriented knowledge base of common clinical patterns,
not a substitute for a full clinical decision-support system.

Extended for MedCross v2: added common Indian generics, additional interactions,
and broader class-level rules.
"""

from __future__ import annotations

# Canonical name -> aliases (lowercase)
DRUG_ALIASES: dict[str, set[str]] = {
    "amoxicillin": {"amoxil", "amoxycillin"},
    "ampicillin": set(),
    "penicillin": {"penicillin v", "penicillin g", "benzylpenicillin"},
    "augmentin": {"amoxicillin-clavulanate", "amoxicillin clavulanate", "co-amoxiclav"},
    "metformin": {"glucophage"},
    "atorvastatin": {"lipitor"},
    "simvastatin": {"zocor"},
    "lisinopril": {"zestril", "prinivil"},
    "enalapril": {"vasotec"},
    "ramipril": {"altace"},
    "losartan": {"cozaar"},
    "amlodipine": {"norvasc"},
    "metoprolol": {"lopressor", "toprol"},
    "atenolol": {"tenormin"},
    "warfarin": {"coumadin"},
    "aspirin": {"asa", "acetylsalicylic acid"},
    "ibuprofen": {"advil", "motrin"},
    "naproxen": {"aleve"},
    "diclofenac": set(),
    "paracetamol": {"acetaminophen", "tylenol"},
    "tramadol": {"ultram"},
    "sertraline": {"zoloft"},
    "fluoxetine": {"prozac"},
    "escitalopram": {"lexapro"},
    "omeprazole": {"prilosec"},
    "pantoprazole": {"protonix"},
    "clarithromycin": {"biaxin"},
    "erythromycin": set(),
    "itraconazole": {"sporanox"},
    "ketoconazole": set(),
    "amiodarone": {"cordarone", "pacerone"},
    "digoxin": {"lanoxin"},
    "spironolactone": {"aldactone"},
    "potassium": {"potassium chloride", "kcl"},
    "insulin": {"insulin glargine", "insulin aspart", "lantus", "novolog", "humalog"},
    "prednisone": set(),
    "methotrexate": set(),
    "ciprofloxacin": {"cipro"},
    "levofloxacin": {"levaquin"},
    "sulfamethoxazole": {"bactrim", "cotrimoxazole", "trimethoprim-sulfamethoxazole", "tmp-smx"},
    "clopidogrel": {"plavix"},
    "heparin": set(),
    "enoxaparin": {"lovenox"},
    "sildenafil": {"viagra"},
    "nitroglycerin": {"gtn", "glyceryl trinitrate"},
    "theophylline": set(),
    "lithium": set(),
    "piperacillin": set(),
    "oxacillin": set(),
    "rosuvastatin": {"crestor"},
    "pravastatin": set(),
    "perindopril": set(),
    "morphine": set(),
    "oxycodone": set(),
    "hydrocodone": set(),
    "codeine": set(),
    "sulfadiazine": set(),
    "sulfasalazine": set(),
    # Common Indian-market / generic additions
    "azithromycin": {"zithromax", "azee", "azithral"},
    "doxycycline": {"doxy", "doxt"},
    "metronidazole": {"flagyl", "metro"},
    "ceftriaxone": {"rocephin"},
    "cefixime": {"taxim", "cefspan"},
    "amikacin": set(),
    "gentamicin": set(),
    "vancomycin": set(),
    "glipizide": {"glucotrol"},
    "glimepiride": {"amaryl"},
    "glibenclamide": {"glyburide", "daonil"},
    "sitagliptin": {"januvia"},
    "vildagliptin": {"galvus"},
    "empagliflozin": {"jardiance"},
    "dapagliflozin": {"forxiga", "farxiga"},
    "amlodipine": {"norvasc", "stamlo"},
    "nifedipine": {"adalat"},
    "verapamil": {"calan"},
    "diltiazem": {"cardizem"},
    "atenolol": {"tenormin", "aten"},
    "bisoprolol": {"concor", "biselect"},
    "carvedilol": {"coreg"},
    "furosemide": {"lasix", "frusemide"},
    "hydrochlorothiazide": {"hctz"},
    "torsemide": {"dytor"},
    "chlorthalidone": set(),
    "levothyroxine": {"eltroxin", "thyrox", "synthroid"},
    "carbimazole": set(),
    "prednisolone": {"omnacortil"},
    "dexamethasone": {"decadron"},
    "montelukast": {"singulair", "montair"},
    "salbutamol": {"albuterol", "asthalin"},
    "budesonide": {"pulmicort"},
    "cetirizine": {"zyrtec"},
    "fexofenadine": {"allegra"},
    "loratadine": {"claritin"},
    "alprazolam": {"xanax"},
    "diazepam": {"valium"},
    "zolpidem": {"ambien"},
    "gabapentin": {"neurontin"},
    "pregabalin": {"lyrica"},
    "phenytoin": {"dilantin"},
    "carbamazepine": {"tegretol"},
    "valproate": {"depakote", "sodium valproate", "valproic acid"},
    "levetiracetam": {"keppra"},
    "donepezil": {"aricept"},
    "risperidone": {"risperdal"},
    "olanzapine": {"zyprexa"},
    "ondansetron": {"zofran"},
    "domperidone": {"motilium"},
    "rabeprazole": {"aciphex", "razo"},
    "esomeprazole": {"nexium"},
    "ranitidine": {"zantac"},
    "calcium": {"calcium carbonate", "calcirol", "shelcal"},
    "vitamin d": {"cholecalciferol", "calciferol"},
    "iron": {"ferrous sulphate", "ferrous sulfate", "fefol"},
    "folic acid": {"folate"},
    "vitamin b12": {"cyanocobalamin", "mecobalamin"},
}

# Allergy label/canonical drug -> related drugs that may cross-react
ALLERGY_CROSSWALK: dict[str, set[str]] = {
    "penicillin": {
        "penicillin",
        "amoxicillin",
        "ampicillin",
        "augmentin",
        "piperacillin",
        "oxacillin",
    },
    "amoxicillin": {"amoxicillin", "augmentin", "ampicillin", "penicillin"},
    "ampicillin": {"ampicillin", "amoxicillin", "augmentin", "penicillin"},
    "sulfa": {"sulfamethoxazole", "sulfadiazine", "sulfasalazine"},
    "sulfonamide": {"sulfamethoxazole", "sulfadiazine", "sulfasalazine"},
    "bactrim": {"sulfamethoxazole"},
    "aspirin": {"aspirin", "ibuprofen", "naproxen", "diclofenac"},
    "nsaid": {"ibuprofen", "naproxen", "diclofenac", "aspirin"},
    "ibuprofen": {"ibuprofen", "naproxen", "diclofenac", "aspirin"},
    "codeine": {"codeine", "tramadol", "morphine", "oxycodone"},
    "opioid": {"codeine", "tramadol", "morphine", "oxycodone", "hydrocodone"},
    "ace inhibitor": {"lisinopril", "enalapril", "ramipril", "perindopril"},
    "acei": {"lisinopril", "enalapril", "ramipril", "perindopril"},
    "statin": {"atorvastatin", "simvastatin", "rosuvastatin", "pravastatin"},
}

# Unordered pairs: frozenset({drug_a, drug_b}) -> (severity, explanation)
# Severity values: Low | Medium | High
KNOWN_INTERACTIONS: dict[frozenset[str], tuple[str, str]] = {
    frozenset({"warfarin", "aspirin"}): (
        "High",
        "Combining warfarin with aspirin increases bleeding risk because both impair hemostasis "
        "(anticoagulant + antiplatelet effect).",
    ),
    frozenset({"warfarin", "ibuprofen"}): (
        "High",
        "NSAIDs such as ibuprofen can increase warfarin-related bleeding risk via antiplatelet effects "
        "and potential INR changes.",
    ),
    frozenset({"warfarin", "naproxen"}): (
        "High",
        "Naproxen with warfarin raises gastrointestinal and systemic bleeding risk.",
    ),
    frozenset({"warfarin", "amiodarone"}): (
        "High",
        "Amiodarone inhibits warfarin metabolism and can markedly elevate INR, increasing bleed risk.",
    ),
    frozenset({"lisinopril", "spironolactone"}): (
        "High",
        "ACE inhibitors with spironolactone can cause hyperkalemia; potassium should be monitored closely.",
    ),
    frozenset({"enalapril", "spironolactone"}): (
        "High",
        "ACE inhibitors with spironolactone can cause hyperkalemia; potassium should be monitored closely.",
    ),
    frozenset({"ramipril", "spironolactone"}): (
        "High",
        "ACE inhibitors with spironolactone can cause hyperkalemia; potassium should be monitored closely.",
    ),
    frozenset({"lisinopril", "potassium"}): (
        "High",
        "ACE inhibitors reduce potassium excretion; adding potassium supplements may cause dangerous hyperkalemia.",
    ),
    frozenset({"simvastatin", "clarithromycin"}): (
        "High",
        "Clarithromycin strongly inhibits CYP3A4 and can raise simvastatin levels, increasing myopathy/rhabdomyolysis risk.",
    ),
    frozenset({"simvastatin", "itraconazole"}): (
        "High",
        "Itraconazole inhibits CYP3A4-mediated simvastatin metabolism and elevates myopathy risk.",
    ),
    frozenset({"simvastatin", "ketoconazole"}): (
        "High",
        "Ketoconazole inhibits CYP3A4 and can dangerously increase simvastatin exposure.",
    ),
    frozenset({"atorvastatin", "clarithromycin"}): (
        "Medium",
        "Clarithromycin may increase atorvastatin levels via CYP3A4 inhibition; monitor for muscle symptoms.",
    ),
    frozenset({"digoxin", "amiodarone"}): (
        "High",
        "Amiodarone increases digoxin concentrations; digoxin dose reduction and level monitoring are typically required.",
    ),
    frozenset({"sertraline", "tramadol"}): (
        "High",
        "SSRIs with tramadol increase serotonin syndrome risk and may lower seizure threshold.",
    ),
    frozenset({"fluoxetine", "tramadol"}): (
        "High",
        "SSRIs with tramadol increase serotonin syndrome risk and may lower seizure threshold.",
    ),
    frozenset({"escitalopram", "tramadol"}): (
        "High",
        "SSRIs with tramadol increase serotonin syndrome risk and may lower seizure threshold.",
    ),
    frozenset({"metformin", "alcohol"}): (
        "Medium",
        "Heavy alcohol use with metformin increases lactic acidosis risk.",
    ),
    frozenset({"sildenafil", "nitroglycerin"}): (
        "High",
        "PDE5 inhibitors with nitrates can cause profound, life-threatening hypotension.",
    ),
    frozenset({"ibuprofen", "lisinopril"}): (
        "Medium",
        "NSAIDs can blunt antihypertensive effects of ACE inhibitors and worsen renal function, especially in volume-depleted patients.",
    ),
    frozenset({"ibuprofen", "enalapril"}): (
        "Medium",
        "NSAIDs can blunt antihypertensive effects of ACE inhibitors and worsen renal function.",
    ),
    frozenset({"ibuprofen", "losartan"}): (
        "Medium",
        "NSAIDs may reduce ARB effectiveness and increase risk of kidney injury.",
    ),
    frozenset({"aspirin", "ibuprofen"}): (
        "Medium",
        "Ibuprofen may interfere with aspirin's antiplatelet effect when timed incorrectly and increases GI bleed risk.",
    ),
    frozenset({"clopidogrel", "omeprazole"}): (
        "Medium",
        "Omeprazole can reduce bioactivation of clopidogrel via CYP2C19 inhibition, potentially lowering antiplatelet efficacy.",
    ),
    frozenset({"methotrexate", "ibuprofen"}): (
        "High",
        "NSAIDs may reduce methotrexate clearance and increase methotrexate toxicity.",
    ),
    frozenset({"lithium", "ibuprofen"}): (
        "High",
        "NSAIDs can increase lithium levels and precipitate lithium toxicity.",
    ),
    frozenset({"ciprofloxacin", "warfarin"}): (
        "Medium",
        "Fluoroquinolones may potentiate warfarin anticoagulation; monitor INR closely.",
    ),
    frozenset({"levofloxacin", "warfarin"}): (
        "Medium",
        "Fluoroquinolones may potentiate warfarin anticoagulation; monitor INR closely.",
    ),
    frozenset({"insulin", "metformin"}): (
        "Low",
        "Insulin with metformin is often intentional in diabetes care, but combined therapy increases hypoglycemia awareness needs.",
    ),
    frozenset({"prednisone", "ibuprofen"}): (
        "Medium",
        "Corticosteroids with NSAIDs raise gastrointestinal ulcer and bleeding risk.",
    ),
    frozenset({"heparin", "aspirin"}): (
        "High",
        "Combining anticoagulants with antiplatelets substantially increases bleeding risk.",
    ),
    frozenset({"enoxaparin", "aspirin"}): (
        "High",
        "Combining anticoagulants with antiplatelets substantially increases bleeding risk.",
    ),
    frozenset({"warfarin", "paracetamol"}): (
        "Low",
        "Prolonged high-dose paracetamol/acetaminophen may modestly increase INR in patients on warfarin; short courses are usually lower risk.",
    ),
    # ── Additional interactions ────────────────────────────────────────────
    frozenset({"azithromycin", "warfarin"}): (
        "Medium",
        "Azithromycin can potentiate warfarin; INR should be monitored during and after the antibiotic course.",
    ),
    frozenset({"azithromycin", "amiodarone"}): (
        "High",
        "Both azithromycin and amiodarone prolong the QT interval; combination increases risk of life-threatening arrhythmia (Torsades de Pointes).",
    ),
    frozenset({"ciprofloxacin", "amiodarone"}): (
        "High",
        "Fluoroquinolones with amiodarone can cause additive QT prolongation and increase arrhythmia risk.",
    ),
    frozenset({"carbamazepine", "warfarin"}): (
        "High",
        "Carbamazepine is a strong CYP3A4 inducer that reduces warfarin levels; anticoagulation may become sub-therapeutic.",
    ),
    frozenset({"phenytoin", "warfarin"}): (
        "High",
        "Phenytoin can both inhibit and induce warfarin metabolism; INR is unpredictable and requires close monitoring.",
    ),
    frozenset({"valproate", "aspirin"}): (
        "Medium",
        "Aspirin can displace valproate from protein binding and inhibit its metabolism, potentially raising valproate levels and toxicity risk.",
    ),
    frozenset({"metformin", "contrast"}): (
        "Medium",
        "Iodinated contrast media can cause acute kidney injury, impairing metformin excretion and raising lactic acidosis risk. Metformin is typically held 48 h around contrast procedures.",
    ),
    frozenset({"furosemide", "gentamicin"}): (
        "High",
        "Loop diuretics combined with aminoglycosides increase ototoxicity and nephrotoxicity risk synergistically.",
    ),
    frozenset({"furosemide", "amikacin"}): (
        "High",
        "Loop diuretics with aminoglycosides increase ototoxicity and nephrotoxicity risk.",
    ),
    frozenset({"furosemide", "digoxin"}): (
        "High",
        "Furosemide-induced hypokalemia potentiates digoxin toxicity; electrolytes should be monitored.",
    ),
    frozenset({"levothyroxine", "calcium"}): (
        "Medium",
        "Calcium supplements can bind levothyroxine in the GI tract, reducing absorption. Separate doses by at least 4 hours.",
    ),
    frozenset({"levothyroxine", "iron"}): (
        "Medium",
        "Iron preparations impair levothyroxine absorption. Separate doses by at least 4 hours.",
    ),
    frozenset({"sildenafil", "amlodipine"}): (
        "Low",
        "Additive vasodilatory effect may cause mild blood pressure lowering; monitor for hypotension.",
    ),
    frozenset({"metoprolol", "verapamil"}): (
        "High",
        "Beta-blocker combined with non-dihydropyridine calcium channel blocker can cause profound bradycardia, heart block, or cardiac arrest.",
    ),
    frozenset({"atenolol", "verapamil"}): (
        "High",
        "Beta-blocker combined with verapamil can cause dangerous bradycardia or AV block.",
    ),
    frozenset({"sertraline", "alprazolam"}): (
        "Low",
        "SSRIs may modestly increase benzodiazepine levels via CYP inhibition; monitor for excess sedation.",
    ),
    frozenset({"prednisone", "warfarin"}): (
        "Medium",
        "Corticosteroids can unpredictably alter INR in patients on warfarin; closer monitoring is advised.",
    ),
    frozenset({"prednisolone", "warfarin"}): (
        "Medium",
        "Corticosteroids can unpredictably alter INR in patients on warfarin; closer monitoring is advised.",
    ),
}

# Class-level interaction helpers (any member of set A with any member of set B)
CLASS_INTERACTIONS: list[tuple[set[str], set[str], str, str]] = [
    (
        {"lisinopril", "enalapril", "ramipril"},
        {"ibuprofen", "naproxen", "diclofenac"},
        "Medium",
        "ACE inhibitors combined with NSAIDs can reduce kidney perfusion and blunt blood-pressure control "
        "(especially with diuretics — the 'triple whammy').",
    ),
    (
        {"sertraline", "fluoxetine", "escitalopram"},
        {"tramadol"},
        "High",
        "Serotonergic antidepressants with tramadol increase serotonin syndrome risk.",
    ),
    (
        {"warfarin"},
        {"ibuprofen", "naproxen", "diclofenac", "aspirin"},
        "High",
        "Warfarin with antiplatelet/NSAID therapy significantly elevates bleeding risk.",
    ),
    (
        {"morphine", "oxycodone", "codeine", "hydrocodone", "tramadol"},
        {"alprazolam", "diazepam", "zolpidem"},
        "High",
        "Opioids combined with benzodiazepines or sedative-hypnotics can cause profound CNS/respiratory depression and death.",
    ),
    (
        {"azithromycin", "ciprofloxacin", "levofloxacin"},
        {"amiodarone"},
        "High",
        "QT-prolonging antibiotics with amiodarone create additive QT prolongation risk and potential for fatal arrhythmia.",
    ),
    (
        {"metoprolol", "atenolol", "bisoprolol", "carvedilol"},
        {"verapamil", "diltiazem"},
        "High",
        "Beta-blockers with rate-limiting calcium channel blockers (verapamil/diltiazem) can cause severe bradycardia, AV block, or cardiac arrest.",
    ),
]
