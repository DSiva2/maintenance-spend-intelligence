"""
cleaning.py
-----------
Reusable data cleaning functions for the GulfChem maintenance spend data.
The notebook notebooks/03_cleaning_classification.ipynb calls these functions
step by step and explains the results.
"""

import re

import pandas as pd
from rapidfuzz import fuzz

# ---------------------------------------------------------------------------
# Sites and units: small, known lists, so a mapping table is the right tool.
# ---------------------------------------------------------------------------
SITE_MAP = {
    "BTR": "BTR", "BATON ROUGE": "BTR", "BATON ROUGE PLANT": "BTR", "BR": "BTR", "BATON ROUGE PLT": "BTR",
    "LCH": "LCH", "LAKE CHARLES": "LCH", "LAKE CHARLES PLANT": "LCH", "LC": "LCH", "L. CHARLES": "LCH",
    "FRP": "FRP", "FREEPORT": "FRP", "FREEPORT PLANT": "FRP", "FPT": "FRP", "FREEPORT PLT": "FRP",
    "PAS": "PAS", "PASADENA": "PAS", "PASADENA PLANT": "PAS", "PSD": "PAS", "PASADENA TX": "PAS",
    "CNR": "CNR", "CONROE": "CNR", "CONROE PLANT": "CNR", "CON": "CNR", "CONROE PLT": "CNR",
}

UNIT_MAP = {
    "EA": "EA", "EACH": "EA", "HR": "HR", "HRS": "HR", "HOUR": "HR", "JOB": "JOB", "LS": "LOT",
    "LOT": "LOT", "WK": "WK", "WEEK": "WK", "DAY": "DAY", "DY": "DAY", "SHIFT": "SHIFT",
    "SHFT": "SHIFT", "DR": "DR", "DRUM": "DR", "PL": "PL", "PAIL": "PL", "CS": "CS", "CASE": "CS",
}


def standardize(series: pd.Series, mapping: dict) -> pd.Series:
    """Map messy values to standard codes. Unmapped values become NaN so they get noticed."""
    return series.astype("string").str.strip().str.upper().map(mapping)


# ---------------------------------------------------------------------------
# Supplier names
# ---------------------------------------------------------------------------
LEGAL_SUFFIXES = {"INC", "INCORPORATED", "LLC", "CO", "COMPANY", "CORP", "CORPORATION", "LP", "LTD"}
NAME_ABBREVIATIONS = {"EQUIP": "EQUIPMENT", "IND": "INDUSTRIAL", "SVCS": "SERVICES",
                      "SVC": "SERVICE", "SUP": "SUPPLY", "MECH": "MECHANICAL"}


def clean_supplier_name(name: str) -> str:
    """Reduce a supplier name to a comparable core.

    'Gulf Valve Co., Inc.' and 'GULF  VALVE COMPANY' both become 'GULF VALVE'.
    """
    s = str(name).upper()
    s = s.replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)                  # drop punctuation: L.L.C. -> L L C
    s = re.sub(r"\bL L C\b", "LLC", s)
    s = re.sub(r"\bL P\b", "LP", s)
    words = [NAME_ABBREVIATIONS.get(w, w) for w in s.split()]
    words = [w for w in words if w not in LEGAL_SUFFIXES]
    return " ".join(words)


class UnionFind:
    """Groups items that are linked directly or through a chain (A~B and B~C -> A, B, C)."""

    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a, b):
        self.parent[self.find(a)] = self.find(b)


def group_vendors(vm: pd.DataFrame, threshold: int = 90) -> pd.DataFrame:
    """Assign a supplier_group to each vendor record.

    Two records are the same supplier if they share a tax ID, or if their cleaned
    names are very similar (fuzzy score >= threshold) and they are in the same state.
    Returns vm with clean_name, supplier_group and match_reason columns added.
    """
    vm = vm.copy()
    vm["clean_name"] = vm["vendor_name"].map(clean_supplier_name)
    uf = UnionFind(vm["vendor_id"])
    reasons = {}

    # Rule 1: same tax ID (strongest evidence)
    for _, grp in vm.dropna(subset=["tax_id"]).groupby("tax_id"):
        ids = grp["vendor_id"].tolist()
        for other in ids[1:]:
            uf.union(ids[0], other)
            reasons[other] = "tax_id"

    # Rule 2: similar names in the same state
    rows = vm[["vendor_id", "clean_name", "state"]].to_dict("records")
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a["state"] != b["state"]:
                continue
            score = fuzz.token_sort_ratio(a["clean_name"], b["clean_name"])
            if score >= threshold and uf.find(a["vendor_id"]) != uf.find(b["vendor_id"]):
                uf.union(a["vendor_id"], b["vendor_id"])
                reasons.setdefault(b["vendor_id"], f"name_match_{score:.0f}")

    vm["supplier_group"] = vm["vendor_id"].map(uf.find)
    vm["match_reason"] = vm["vendor_id"].map(reasons).fillna("group_anchor")
    return vm


def canonical_names(vm: pd.DataFrame, po_counts: pd.Series) -> pd.DataFrame:
    """Pick one official name per supplier group.

    Preference order: the most common cleaned spelling in the group (outvotes typos),
    then properly capitalized names over ALL CAPS, then names without abbreviations,
    then full legal names (ending in Inc, LLC...) over shortened ones, then the most-used vendor record.
    """
    vm = vm.copy()
    vm["po_lines"] = vm["vendor_id"].map(po_counts).fillna(0)
    vm["spelling_votes"] = vm.groupby(["supplier_group", "clean_name"])["vendor_id"].transform("count")
    vm["not_all_caps"] = vm["vendor_name"] != vm["vendor_name"].str.upper()
    last_word = vm["vendor_name"].str.upper().str.replace(r"[^A-Z ]", "", regex=True).str.split().str[-1]
    vm["has_legal_suffix"] = last_word.isin(LEGAL_SUFFIXES)
    tokens = vm["vendor_name"].str.upper().str.replace(r"[^A-Z ]", " ", regex=True).str.split()
    vm["no_abbreviation"] = ~tokens.map(lambda ws: any(w in NAME_ABBREVIATIONS for w in ws))
    best = (vm.sort_values(["spelling_votes", "not_all_caps", "no_abbreviation", "has_legal_suffix",
                            "po_lines"], ascending=False)
              .groupby("supplier_group")["vendor_name"].first()
              .str.replace(r"\s+", " ", regex=True).str.strip())
    groups = sorted(vm["supplier_group"].unique(), key=lambda g: best[g])
    ids = {g: f"SUP{i:03d}" for i, g in enumerate(groups, start=1)}
    vm["supplier_id"] = vm["supplier_group"].map(ids)
    vm["supplier_name"] = vm["supplier_group"].map(best)
    return vm.drop(columns=["supplier_group", "po_lines", "spelling_votes", "not_all_caps",
                            "has_legal_suffix", "no_abbreviation"])


# ---------------------------------------------------------------------------
# Item descriptions
# ---------------------------------------------------------------------------
DESCRIPTION_ABBREVIATIONS = {
    "VLV": "VALVE", "GT": "GATE", "GLB": "GLOBE", "CHK": "CHECK", "PRESS": "PRESSURE",
    "ST": "STRAIGHT TIME", "OT": "OVERTIME", "INSP": "INSPECTION", "TECH": "TECHNICIAN",
    "REPL": "REPLACEMENT", "SVC": "SERVICE", "BRG": "BEARING", "MECH": "MECHANICAL",
    "COMP": "COMPRESSOR", "W/": "WITH", "OPR": "OPERATOR", "MATLS": "MATERIALS",
    "SCAF": "SCAFFOLD", "INSUL": "INSULATION", "ELEC": "ELECTRIC", "XMTR": "TRANSMITTER",
    "FLG": "FLANGE", "ELL": "ELBOW", "SS": "STAINLESS", "CS": "CARBON STEEL", "RNTL": "RENTAL",
    "DEG": "DEGREE", "FITTER": "PIPEFITTER", "WLDR": "WELDER", "FMN": "FOREMAN",
    "HLPR": "HELPER", "HYD": "HYDRAULIC", "EQUIP": "EQUIPMENT", "CLNG": "CLEANING",
    "OVHL": "OVERHAUL", "SMLS": "SEAMLESS", "EXCH": "EXCHANGER",
}
NOISE_PATTERNS = [r"\s-\sTA\d{4}$", r"\bURGENT\b", r"\bRUSH\b", r"\bPER QUOTE Q\d+\b",
                  r"\bREF WO#\d+\b", r"\bPER CONTRACT\b", r"\bSEE ATTACHED\b"]


def clean_description(text: str) -> str:
    """Standardize a free-text description: uppercase, strip noise, expand abbreviations."""
    s = re.sub(r"\s+", " ", str(text).upper()).strip()
    for pattern in NOISE_PATTERNS:
        s = re.sub(pattern, "", s)
    words = [DESCRIPTION_ABBREVIATIONS.get(w, w) for w in s.split()]
    return " ".join(words).strip()


def turnaround_tag(text: str):
    """Return the turnaround year if a description is tagged like '- TA2024', else None."""
    m = re.search(r"-\s*TA(\d{4})\s*$", str(text).upper())
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Price outliers
# ---------------------------------------------------------------------------
def flag_price_outliers(po: pd.DataFrame, group_cols: list, ratio: float = 20) -> pd.Series:
    """Flag lines priced more than `ratio` times the median price of comparable lines."""
    median = po.groupby(group_cols, dropna=False)["unit_price"].transform("median")
    return po["unit_price"] > ratio * median


# ---------------------------------------------------------------------------
# Recover missing material numbers
# ---------------------------------------------------------------------------
def recover_material_numbers(po: pd.DataFrame, item_master: pd.DataFrame, min_score: int = 90) -> pd.Series:
    """Fill missing material numbers by fuzzy-matching the cleaned description
    against the item master. Returns the completed material_number column."""
    from rapidfuzz import process

    master = item_master.assign(key=item_master["description"].map(clean_description))
    choices = dict(zip(master["material_number"], master["key"]))
    missing = po["material_number"].isna()
    lookup = {}
    for desc in po.loc[missing, "desc_clean"].unique():
        match = process.extractOne(desc, choices, scorer=fuzz.token_sort_ratio)
        lookup[desc] = match[2] if match and match[1] >= min_score else None
    return po["material_number"].fillna(po["desc_clean"].map(lookup))
