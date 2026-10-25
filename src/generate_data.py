"""
generate_data.py
----------------
Generates three years (2023-2025) of synthetic maintenance procurement data for
GulfChem Industries, a FICTIONAL chemical company with five Gulf Coast plants.

What it produces (in data/raw/):
    sites.csv            the five plants
    categories.csv       the maintenance category taxonomy
    item_master.csv      material master for stocked items (like SAP)
    vendor_master.csv    supplier records, deliberately duplicated and messy (SIM-style data)
    contracts.csv        negotiated contracts with payment terms and mark-up caps
    contract_rates.csv   contracted prices (rate cards) by year
    po_lines.csv         purchase order lines with messy descriptions
    goods_receipts.csv   what was delivered, when, and in what condition
    invoices.csv         what suppliers billed and when it was paid
    equipment.csv        plant equipment register
    work_orders.csv      maintenance work orders
    wo_parts.csv         spare parts consumed by work orders

And the answer key (data/answer_key/), used ONLY to check your analysis afterwards:
    vendor_map.csv       which vendor records are really the same supplier
    po_line_truth.csv    true category, true item, and planted-pattern flags per PO line

Price movements follow real FRED price indices if data/external/price_indices.csv
exists (run src/fetch_fred.py first). Otherwise a built-in approximation is used.

Run from the project root:
    python src/generate_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 0. SETTINGS
# ---------------------------------------------------------------------------
SEED = 42  # fixed seed = the same data every time you run it (reproducible)
rng = np.random.default_rng(SEED)

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
KEY_DIR = ROOT / "data" / "answer_key"
INDEX_FILE = ROOT / "data" / "external" / "price_indices.csv"

START = pd.Timestamp("2023-01-01")
END = pd.Timestamp("2025-12-31")
MONTHS = pd.date_range(START, END, freq="MS")

# ---------------------------------------------------------------------------
# 1. SITES
# Each plant has a size factor (scales purchasing volume) and one turnaround.
# ---------------------------------------------------------------------------
SITES = [
    # site_id, name, state, size, turnaround start, turnaround days
    ("BTR", "Baton Rouge Plant", "LA", 1.3, "2024-03-04", 35),
    ("LCH", "Lake Charles Plant", "LA", 1.0, "2023-10-02", 30),
    ("FRP", "Freeport Plant", "TX", 1.2, "2025-04-07", 35),
    ("PAS", "Pasadena Plant", "TX", 0.9, "2024-09-16", 28),
    ("CNR", "Conroe Plant", "TX", 0.6, "2025-10-06", 21),
]

# Messy ways plant names get typed into purchasing systems.
SITE_VARIANTS = {
    "BTR": ["Baton Rouge", "BATON ROUGE PLANT", "BR", "Baton Rouge Plt"],
    "LCH": ["Lake Charles", "LAKE CHARLES PLANT", "LC", "L. Charles"],
    "FRP": ["Freeport", "FREEPORT PLANT", "FPT", "Freeport Plt"],
    "PAS": ["Pasadena", "PASADENA PLANT", "PSD", "Pasadena TX"],
    "CNR": ["Conroe", "CONROE PLANT", "CON", "Conroe Plt"],
}

# ---------------------------------------------------------------------------
# 2. CATEGORIES
# kind: material or service. index: which price index drives prices, with a lag
# in months (prices react to market changes with a delay).
# lam: average PO lines per site-month at size 1.0. ta_mult: volume multiplier
# during a turnaround. median_value: typical line value in dollars.
# ---------------------------------------------------------------------------
CATEGORIES = [
    ("C01", "Pump & Compressor Repair", "service", "PUMPS", 2, 12, 9000, 3.0),
    ("C02", "Valves & Actuators", "material", "VALVES", 3, 25, 3000, 2.5),
    ("C03", "Piping, Flanges & Fittings", "material", "STEEL", 2, 20, 2500, 2.5),
    ("C04", "Mechanical Contractor Labor", "service", "LABOR", 1, 15, 15000, 6.0),
    ("C05", "Scaffolding Services", "service", "LABOR", 1, 14, 10000, 7.0),
    ("C06", "Insulation Services", "service", "LABOR", 1, 8, 8000, 5.0),
    ("C07", "Inspection & NDT Services", "service", "LABOR", 1, 8, 7000, 5.0),
    ("C08", "Industrial Cleaning", "service", "LABOR", 1, 8, 9000, 6.0),
    ("C09", "Electrical & Instrumentation", "material", "GENERIC", 0, 18, 3000, 1.8),
    ("C10", "Equipment & Crane Rental", "service", "GENERIC", 0, 10, 6000, 5.0),
    ("C11", "MRO Parts", "material", "PUMPS", 2, 45, 1200, 1.8),
    ("C12", "Lubricants", "material", "GENERIC", 0, 10, 2000, 1.2),
]
CAT = {c[0]: dict(code=c[0], name=c[1], kind=c[2], index=c[3], lag=c[4],
                  lam=c[5], median_value=c[6], ta_mult=c[7]) for c in CATEGORIES}

# ---------------------------------------------------------------------------
# 3. ITEMS (what gets bought). LOT items are "pass-through" materials that a
# contractor buys on our behalf and bills at cost plus a mark-up.
# ---------------------------------------------------------------------------
ITEMS = {
    "C01": [("Centrifugal Pump Overhaul Service", "JOB", 18000),
            ("Pump Mechanical Seal Replacement Service", "JOB", 4200),
            ("Compressor Valve Overhaul Service", "JOB", 9500),
            ("Pump Bearing Replacement Service", "JOB", 3100),
            ("Rotating Equipment Field Service Technician", "HR", 135),
            ("Pump Shaft Laser Alignment Service", "JOB", 1400)],
    "C02": [("Gate Valve 2in Carbon Steel 300# RF", "EA", 620),
            ("Gate Valve 6in Carbon Steel 300# RF", "EA", 1850),
            ("Globe Valve 4in Carbon Steel 150# RF", "EA", 1400),
            ("Ball Valve 1in Stainless 800# SW", "EA", 310),
            ("Ball Valve 3in Carbon Steel 150# RF", "EA", 980),
            ("Check Valve 4in Carbon Steel 300# RF", "EA", 1250),
            ("Control Valve 3in Globe with Actuator", "EA", 14500),
            ("Pressure Relief Valve 1x2in", "EA", 2600),
            ("Butterfly Valve 8in 150# Wafer", "EA", 1700)],
    "C03": [("Pipe 2in Sch 40 Carbon Steel Seamless 21ft", "EA", 95),
            ("Pipe 6in Sch 40 Carbon Steel Seamless 21ft", "EA", 520),
            ("Pipe 4in Sch 80 Stainless 316 21ft", "EA", 1450),
            ("Weld Neck Flange 4in 300# Carbon Steel", "EA", 140),
            ("Elbow 90 Degree 4in Sch 40 Carbon Steel", "EA", 48),
            ("Tee 6in Sch 40 Carbon Steel", "EA", 160),
            ("Stud Bolt B7 3/4in x 5in with 2 Nuts", "EA", 6.5)],
    "C04": [("Pipefitter Straight Time", "HR", 68),
            ("Pipefitter Overtime", "HR", 98),
            ("Welder Straight Time", "HR", 72),
            ("Millwright Straight Time", "HR", 74),
            ("Mechanical Helper Straight Time", "HR", 42),
            ("Foreman Straight Time", "HR", 85),
            ("Mechanical Materials Pass-Through", "LOT", None)],
    "C05": [("Scaffold Builder Straight Time", "HR", 55),
            ("Scaffold Builder Overtime", "HR", 80),
            ("Scaffold Foreman Straight Time", "HR", 70),
            ("Scaffold Material Rental Week", "WK", 950),
            ("Scaffold Materials Pass-Through", "LOT", None)],
    "C06": [("Insulator Straight Time", "HR", 58),
            ("Insulator Overtime", "HR", 85),
            ("Insulation Removal Labor", "HR", 52),
            ("Insulation Materials Pass-Through", "LOT", None)],
    "C07": [("UT Thickness Inspection Technician", "HR", 95),
            ("Radiography Crew Shift", "SHIFT", 2800),
            ("API 510 Pressure Vessel Inspector", "HR", 125),
            ("Phased Array UT Weld Inspection", "HR", 140),
            ("Heat Exchanger Eddy Current Testing", "JOB", 6500)],
    "C08": [("Hydroblasting Unit 20K PSI with Crew Shift", "SHIFT", 4200),
            ("Vacuum Truck with Operator", "HR", 165),
            ("Heat Exchanger Bundle Cleaning", "JOB", 7800),
            ("Tank Cleaning Service", "JOB", 22000)],
    "C09": [("Pressure Transmitter 0-500 PSI", "EA", 1650),
            ("Thermocouple Type K 12in", "EA", 145),
            ("Electric Motor 50HP TEFC", "EA", 6200),
            ("Variable Frequency Drive 50HP", "EA", 7400),
            ("Cable Tray 12in x 10ft", "EA", 120),
            ("Instrument Technician Straight Time", "HR", 78)],
    "C10": [("Crawler Crane 100T with Operator Day", "DAY", 5200),
            ("Hydraulic Crane 40T with Operator Day", "DAY", 2400),
            ("Air Compressor 375 CFM Rental Week", "WK", 1100),
            ("Diesel Generator 200kW Rental Week", "WK", 1600),
            ("Manlift 60ft Rental Week", "WK", 950)],
    "C11": [("Ball Bearing 6312-2RS", "EA", 85),
            ("Mechanical Seal Cartridge 2.5in", "EA", 2400),
            ("Spiral Wound Gasket 4in 300#", "EA", 22),
            ("O-Ring Kit Viton", "EA", 140),
            ("Pump Impeller 10in Stainless", "EA", 3800),
            ("Coupling Insert Elastomer", "EA", 210),
            ("V-Belt B-Section", "EA", 28)],
    "C12": [("Turbine Oil ISO 32 Drum 55gal", "DR", 1150),
            ("Synthetic Gear Oil ISO 220 Pail 5gal", "PL", 260),
            ("Grease EP2 Tube Case", "CS", 95),
            ("Hydraulic Oil AW46 Drum 55gal", "DR", 980),
            ("Degreaser Solvent Drum 55gal", "DR", 720)],
}

ITEM_LIST = []  # flat list of item dictionaries
for cat_code, items in ITEMS.items():
    for i, (desc, unit, price) in enumerate(items, start=1):
        is_material = CAT[cat_code]["kind"] == "material" and unit not in ("HR",)
        ITEM_LIST.append(dict(
            item_code=f"{cat_code}-{i:02d}", category=cat_code, description=desc,
            unit=unit, base_price=price, passthrough=(unit == "LOT"),
            material_number=f"M{100000 + len(ITEM_LIST) * 37}" if is_material else None,
        ))
ITEM_BY_CODE = {it["item_code"]: it for it in ITEM_LIST}
ITEMS_BY_CAT = {c: [it for it in ITEM_LIST if it["category"] == c] for c in CAT}

# ---------------------------------------------------------------------------
# 4. SUPPLIERS (all names are fictional)
# role: primary / secondary = contracted; spot = no contract.
# base_otd: base on-time delivery probability.
# ---------------------------------------------------------------------------
SUPPLIERS = [
    # name, category, role, city, state, base_otd
    ("Delta Rotating Equipment Inc", "C01", "primary", "Baton Rouge", "LA", 0.94),
    ("Sabine Pump Works LLC", "C01", "secondary", "Orange", "TX", 0.90),
    ("Brazos Machine & Repair Co", "C01", "spot", "Freeport", "TX", 0.85),
    ("Acadiana Compressor Service LLC", "C01", "spot", "Lafayette", "LA", 0.86),
    ("Magnolia Pump Service LLC", "C01", "spot", "Conroe", "TX", 0.84),
    ("Lone Star Valve Supply Inc", "C02", "primary", "Houston", "TX", 0.93),
    ("Crescent Flow Control LLC", "C02", "secondary", "Kenner", "LA", 0.91),
    ("Bayou Valve & Supply Co", "C02", "spot", "Sulphur", "LA", 0.88),
    ("Red River Valve Co", "C02", "spot", "Shreveport", "LA", 0.85),
    ("Southern Industrial Pipe & Supply Corp", "C03", "primary", "Houston", "TX", 0.92),
    ("Trinity Pipe & Fittings LLC", "C03", "secondary", "Baytown", "TX", 0.90),
    ("Calcasieu Steel Supply Inc", "C03", "spot", "Lake Charles", "LA", 0.86),
    ("Pelican Pipe & Valve LLC", "C03", "spot", "Gonzales", "LA", 0.85),
    ("Magnolia Mechanical Constructors LLC", "C04", "primary", "Baton Rouge", "LA", 0.93),
    ("Ironclad Industrial Services Inc", "C04", "secondary", "Pasadena", "TX", 0.90),
    ("Bayport Mechanical LP", "C04", "spot", "La Porte", "TX", 0.87),
    ("Cypress Field Services LLC", "C04", "spot", "Cypress", "TX", 0.86),
    ("Delta Industrial Contractors Inc", "C04", "spot", "Geismar", "LA", 0.85),
    ("Gulf Coast Scaffold Services LLC", "C05", "primary", "Port Allen", "LA", 0.94),
    ("Apex Access Systems Inc", "C05", "secondary", "Deer Park", "TX", 0.91),
    ("Pelican Scaffold & Rigging LLC", "C05", "spot", "Prairieville", "LA", 0.86),
    ("Atchafalaya Insulation Co", "C06", "primary", "Plaquemine", "LA", 0.92),
    ("Summit Thermal Services LLC", "C06", "secondary", "Beaumont", "TX", 0.90),
    ("Republic Insulation Inc", "C06", "spot", "Houston", "TX", 0.86),
    ("Precision NDT Services Inc", "C07", "primary", "Houston", "TX", 0.95),
    ("Allied Inspection Group LLC", "C07", "secondary", "Baton Rouge", "LA", 0.92),
    ("Coastal Integrity Testing LLC", "C07", "spot", "Lake Charles", "LA", 0.88),
    ("Lone Star Inspection Services LLC", "C07", "spot", "Pearland", "TX", 0.87),
    ("Texan Hydroblasting Inc", "C08", "primary", "Pasadena", "TX", 0.93),
    ("Bayou Vacuum & Industrial Cleaning LLC", "C08", "secondary", "Sulphur", "LA", 0.90),
    ("Coastal Hydro Services LLC", "C08", "spot", "Texas City", "TX", 0.84),
    ("Crescent City Electric Supply Inc", "C09", "primary", "New Orleans", "LA", 0.93),
    ("Lone Star Automation LLC", "C09", "secondary", "Sugar Land", "TX", 0.91),
    ("Sabine Instrument Co", "C09", "spot", "Port Arthur", "TX", 0.86),
    ("Bayou Electrical Contractors LLC", "C09", "spot", "Gonzales", "LA", 0.85),
    ("Red River Crane & Rigging LLC", "C10", "primary", "Baton Rouge", "LA", 0.94),
    ("Gulfway Equipment Rentals Inc", "C10", "secondary", "Houston", "TX", 0.91),
    ("Bayport Lift Rentals LLC", "C10", "spot", "La Porte", "TX", 0.87),
    ("Coastal Equipment Rental Co", "C10", "spot", "Lake Charles", "LA", 0.86),
    ("Delta Bearing & Power Transmission Inc", "C11", "primary", "Baton Rouge", "LA", 0.94),
    ("Gulf States Seal & Gasket Co", "C11", "secondary", "Houston", "TX", 0.92),
    ("Pelican Industrial Supply LLC", "C11", "spot", "Conroe", "TX", 0.90),
    ("Brazos Industrial Parts Inc", "C11", "spot", "Angleton", "TX", 0.86),
    ("Trinity Bearing Supply LLC", "C11", "spot", "Baytown", "TX", 0.85),
    ("Petro Lube Distributors Inc", "C12", "primary", "Houston", "TX", 0.94),
    ("Cypress Lubricants LLC", "C12", "secondary", "Cypress", "TX", 0.91),
    ("Acadiana Oil & Chemical Co", "C12", "spot", "Lafayette", "LA", 0.87),
    ("Gulf Lubricants & Supply Inc", "C12", "spot", "Texas City", "TX", 0.86),
]
SUP = pd.DataFrame(SUPPLIERS, columns=["name", "category", "role", "city", "state", "base_otd"])
SUP["supplier_id"] = [f"S{i:03d}" for i in range(1, len(SUP) + 1)]
SUP_BY_NAME = SUP.set_index("name")

# Planted patterns use these suppliers.
P_SCAFFOLD = "Gulf Coast Scaffold Services LLC"      # bills mark-up above its cap
P_DELTA = "Delta Rotating Equipment Inc"             # delivery performance declines in 2025
P_BAYOU_VALVE = "Bayou Valve & Supply Co"            # Lake Charles buys valves off-contract
P_PELICAN = "Pelican Industrial Supply LLC"          # Conroe & Freeport pay premium MRO prices
P_COASTAL_HYDRO = "Coastal Hydro Services LLC"       # blocked for safety, Pasadena keeps using it
P_ATCHAFALAYA = "Atchafalaya Insulation Co"          # contract expires mid-2025, spend continues
P_IRONCLAD = "Ironclad Industrial Services Inc"      # frequent invoice price overcharges

COASTAL_BLOCK_DATE = pd.Timestamp("2024-06-01")
ATCHAFALAYA_EXPIRY = pd.Timestamp("2025-06-30")
SCAFFOLD_OVERBILL_START = pd.Timestamp("2024-07-01")
MARKUP_CAP = 0.08          # contracted mark-up cap on pass-through materials
SCAFFOLD_BILLED_MARKUP = 0.15

# ---------------------------------------------------------------------------
# 5. PRICE INDICES
# ---------------------------------------------------------------------------
def load_indices() -> dict:
    """Return {index_name: monthly pd.Series}. Uses real FRED data when available."""
    months = pd.date_range("2022-01-01", END, freq="MS")
    indices = {}
    if INDEX_FILE.exists():
        df = pd.read_csv(INDEX_FILE, parse_dates=["date"])
        for name, grp in df.groupby("index_name"):
            s = grp.set_index("date")["value"].sort_index()
            indices[name] = s.reindex(months).ffill().bfill()
        print(f"Using real FRED indices: {sorted(indices)}")
    else:
        print("data/external/price_indices.csv not found -> using built-in approximations.")
        print("Run src/fetch_fred.py first to use real price data.\n")

    # Built-in approximations, used for any index not downloaded.
    t = np.arange(len(months))
    approximations = {
        "STEEL": 100 * (1.06 - 0.10 * np.sin(np.pi * t / 30) + 0.004 * t),
        "VALVES": 100 * (1.004 ** t),
        "PUMPS": 100 * (1.0035 ** t),
        "LABOR": 100 * (1.0037 ** t),
    }
    for name, values in approximations.items():
        indices.setdefault(name, pd.Series(values, index=months))
    indices["GENERIC"] = pd.Series(100 * (1.0025 ** t), index=months)  # ~3% per year
    return indices


INDICES = load_indices()


def index_factor(cat_code: str, date: pd.Timestamp) -> float:
    """Price multiplier for a category on a date, relative to January 2023."""
    c = CAT[cat_code]
    series = INDICES[c["index"]]
    month = (date.to_period("M") - c["lag"]).to_timestamp()
    base = (START.to_period("M") - c["lag"]).to_timestamp()
    return float(series.loc[month] / series.loc[base])


# ---------------------------------------------------------------------------
# 6. MESSY TEXT HELPERS
# ---------------------------------------------------------------------------
ABBREVIATIONS = {
    "Valve": "VLV", "Gate": "GT", "Globe": "GLB", "Check": "CHK", "Pressure": "PRESS",
    "Straight Time": "ST", "Overtime": "OT", "Inspection": "INSP", "Technician": "TECH",
    "Replacement": "REPL", "Service": "SVC", "Bearing": "BRG", "Mechanical": "MECH",
    "Compressor": "COMP", "with": "W/", "Operator": "OPR", "Materials": "MATLS",
    "Scaffold": "SCAF", "Insulation": "INSUL", "Electric": "ELEC", "Transmitter": "XMTR",
    "Flange": "FLG", "Elbow": "ELL", "Stainless": "SS", "Carbon Steel": "CS",
    "Rental": "RNTL", "Degree": "DEG", "Pipefitter": "FITTER", "Welder": "WLDR",
    "Foreman": "FMN", "Helper": "HLPR", "Hydraulic": "HYD", "Equipment": "EQUIP",
    "Cleaning": "CLNG", "Overhaul": "OVHL", "Seamless": "SMLS", "Exchanger": "EXCH",
}
NOISE_SUFFIXES = ["URGENT", "RUSH", "PER QUOTE Q{n}", "REF WO#{n}", "PER CONTRACT", "SEE ATTACHED"]


def messify(text: str, date: pd.Timestamp, in_turnaround: bool) -> str:
    """Turn a clean description into the kind of text people actually type."""
    out = text
    for full, short in ABBREVIATIONS.items():
        if full in out and rng.random() < 0.5:
            out = out.replace(full, short)
    if rng.random() < 0.15:  # typo: swap two adjacent letters in one word
        words = out.split()
        candidates = [i for i, w in enumerate(words) if len(w) > 4 and w.isalpha()]
        if candidates:
            i = rng.choice(candidates)
            w = words[i]
            j = rng.integers(1, len(w) - 2)
            words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
            out = " ".join(words)
    if rng.random() < 0.10:
        out = out.replace(" ", "  ", 1)
    if in_turnaround and rng.random() < 0.4:
        out += f" - TA{date.year}"
    elif rng.random() < 0.15:
        out += " " + rng.choice(NOISE_SUFFIXES).format(n=rng.integers(10000, 99999))
    r = rng.random()
    if r < 0.40:
        out = out.upper()
    elif r < 0.55:
        out = out.lower()
    return out


UNIT_VARIANTS = {"EA": ["EA", "Each", "ea"], "HR": ["HR", "HRS", "Hour"], "JOB": ["JOB", "LS"],
                 "LOT": ["LOT", "LS"], "WK": ["WK", "Week"], "DAY": ["DAY", "DY"],
                 "SHIFT": ["SHIFT", "SHFT"], "DR": ["DR", "Drum"], "PL": ["PL", "Pail"],
                 "CS": ["CS", "Case"]}


def messy_unit(unit: str) -> str:
    return unit if rng.random() < 0.85 else rng.choice(UNIT_VARIANTS[unit])


SUFFIX_VARIANTS = {
    "Inc": ["Inc.", ", Inc.", "Incorporated", ""],
    "LLC": ["L.L.C.", ", LLC", ""],
    "Co": ["Co.", "Company", ""],
    "Corp": ["Corp.", "Corporation", ""],
    "LP": ["L.P.", ""],
}
WORD_ABBREVIATIONS = {"Equipment": "Equip", "Industrial": "Ind", "Services": "Svcs",
                      "Service": "Svc", "Supply": "Sup", "Mechanical": "Mech"}


def name_variant(name: str) -> str:
    """Create a different spelling of a supplier name, like duplicate ERP vendor records."""
    words = name.split()
    base, suffix = " ".join(words[:-1]), words[-1]
    out = name
    if suffix in SUFFIX_VARIANTS and rng.random() < 0.8:
        new = rng.choice(SUFFIX_VARIANTS[suffix])
        out = base + new if new.startswith(",") else (base if new == "" else f"{base} {new}")
    if "&" in out and rng.random() < 0.4:
        out = out.replace(" & ", rng.choice([" and ", "&"]), 1)
    for full, short in WORD_ABBREVIATIONS.items():
        if full in out.split() and rng.random() < 0.3:
            out = out.replace(full, short, 1)
            break
    if rng.random() < 0.4:
        out = out.upper()
    if rng.random() < 0.15:
        out = out.replace(" ", "  ", 1)
    if rng.random() < 0.1:  # typo: drop the last letter of the first word
        first, _, rest = out.partition(" ")
        out = first[:-1] + " " + rest
    if out == name:  # make sure the duplicate record actually looks different
        out = name.upper()
    return out


# ---------------------------------------------------------------------------
# 7. BUILD TABLES
# ---------------------------------------------------------------------------
def build_sites():
    return pd.DataFrame([dict(site_id=s[0], site_name=s[1], state=s[2], size_factor=s[3],
                              turnaround_start=s[4], turnaround_days=s[5]) for s in SITES])


def build_categories():
    return pd.DataFrame([dict(category_code=c["code"], category_name=c["name"], kind=c["kind"])
                         for c in CAT.values()])


def build_item_master():
    rows = [dict(material_number=it["material_number"], description=it["description"].upper(),
                 unit=it["unit"], category_code=it["category"])
            for it in ITEM_LIST if it["material_number"]]
    return pd.DataFrame(rows)


def build_vendor_master():
    """Each real supplier gets 1-4 vendor records, as happens in real ERP systems."""
    rows, mapping = [], []
    vendor_counter = 10001
    for _, s in SUP.iterrows():
        n_records = rng.choice([1, 2, 3, 4], p=[0.25, 0.40, 0.25, 0.10])
        tax_id = f"{rng.integers(10, 99)}-{rng.integers(1000000, 9999999)}"
        for k in range(n_records):
            vendor_id = f"V{vendor_counter}"
            vendor_counter += 1
            is_contractor = CAT[s["category"]]["kind"] == "service"
            status = "Active"
            if s["name"] == P_COASTAL_HYDRO:
                status = "Blocked"
            elif k > 0 and rng.random() < 0.15:
                status = "Inactive"
            insurance_expiry = None
            if is_contractor:
                insurance_expiry = (pd.Timestamp("2025-01-01")
                                    + pd.Timedelta(days=int(rng.integers(0, 730)))).date()
            rows.append(dict(
                vendor_id=vendor_id,
                vendor_name=s["name"] if k == 0 else name_variant(s["name"]),
                city=s["city"], state=s["state"],
                tax_id=tax_id if rng.random() < 0.8 else None,  # sometimes missing
                status=status,
                status_reason="Safety violations" if status == "Blocked" else None,
                blocked_date=COASTAL_BLOCK_DATE.date() if status == "Blocked" else None,
                default_payment_terms_days=30,
                safety_emr=round(float(rng.uniform(0.6, 1.3)), 2) if is_contractor else None,
                insurance_expiry=insurance_expiry,
                created_date=(pd.Timestamp("2015-01-01")
                              + pd.Timedelta(days=int(rng.integers(0, 2900)))).date(),
            ))
            mapping.append(dict(vendor_id=vendor_id, supplier_id=s["supplier_id"],
                                true_supplier_name=s["name"]))
    vm, vmap = pd.DataFrame(rows), pd.DataFrame(mapping)

    # Planted: two active contractors with insurance that expired in mid-2025.
    for name in ["Bayport Mechanical LP", "Pelican Scaffold & Rigging LLC"]:
        ids = vmap.loc[vmap.true_supplier_name == name, "vendor_id"]
        vm.loc[vm.vendor_id.isin(ids), "insurance_expiry"] = pd.Timestamp("2025-05-31").date()
    return vm, vmap


def build_contracts(vmap):
    """Primary and secondary suppliers in each category get a 3-year contract."""
    contracts, rates = [], []
    n = 1
    for _, s in SUP[SUP.role.isin(["primary", "secondary"])].iterrows():
        cat = s["category"]
        primary = s["role"] == "primary"
        end = ATCHAFALAYA_EXPIRY if s["name"] == P_ATCHAFALAYA else pd.Timestamp("2025-12-31")
        contract_id = f"CTR-{2023}-{n:03d}"
        n += 1
        vendor_id = vmap.loc[vmap.supplier_id == s["supplier_id"], "vendor_id"].iloc[0]
        has_passthrough = any(it["passthrough"] for it in ITEMS_BY_CAT[cat])
        contracts.append(dict(
            contract_id=contract_id, vendor_id=vendor_id, supplier_name=s["name"],
            category_code=cat, start_date=START.date(), end_date=end.date(),
            payment_terms_days=60 if primary else 45,
            markup_cap_pct=MARKUP_CAP * 100 if has_passthrough else None,
            sites_covered="ALL",
        ))
        discount = 0.10 if primary else 0.07
        for it in ITEMS_BY_CAT[cat]:
            if it["passthrough"]:
                continue
            rate = it["base_price"] * (1 - discount)
            for year in (2023, 2024, 2025):
                if year > 2023:
                    # Annual escalation follows the index change, capped at 4%.
                    change = (index_factor(cat, pd.Timestamp(f"{year}-01-01"))
                              / index_factor(cat, pd.Timestamp(f"{year - 1}-01-01")) - 1)
                    rate *= 1 + min(max(change, 0.0), 0.04)
                rates.append(dict(contract_id=contract_id, rate_year=year,
                                  item_code=it["item_code"],
                                  material_number=it["material_number"],
                                  description=it["description"], unit=it["unit"],
                                  contract_rate=round(rate, 2)))
    return pd.DataFrame(contracts), pd.DataFrame(rates)


def turnaround_overlap(site, month_start):
    """Fraction of a month that falls inside the site's turnaround window."""
    ta_start = pd.Timestamp(site[4])
    ta_end = ta_start + pd.Timedelta(days=site[5])
    month_end = month_start + pd.offsets.MonthEnd(0)
    overlap = (min(ta_end, month_end) - max(ta_start, month_start)).days + 1
    return max(overlap, 0) / month_end.day, ta_start, ta_end


def choose_supplier(cat, site_id, date):
    """Pick which supplier gets a PO line, including the planted buying behaviors."""
    cands = SUP[SUP.category == cat]
    weights = []
    n_spot = (cands.role == "spot").sum()
    for _, s in cands.iterrows():
        w = {"primary": 0.62, "secondary": 0.25}.get(s["role"], 0.13 / n_spot)
        if s["name"] == P_BAYOU_VALVE and site_id == "LCH" and date >= pd.Timestamp("2024-01-01"):
            w = 1.2   # Lake Charles shifts valve buying to a non-contracted supplier
        if s["name"] == P_PELICAN and site_id in ("CNR", "FRP"):
            w = 0.75  # Conroe and Freeport buy MRO parts from a local distributor
        if s["name"] == P_COASTAL_HYDRO:
            if date >= COASTAL_BLOCK_DATE:
                w = 0.55 if site_id == "PAS" else 0.0  # blocked, but Pasadena keeps using it
            else:
                w = 0.10
        if s["name"] == P_ATCHAFALAYA and date > ATCHAFALAYA_EXPIRY:
            w = 0.62  # keeps getting work after the contract expired
        weights.append(w)
    weights = np.array(weights) / sum(weights)
    return cands.iloc[rng.choice(len(cands), p=weights)]


def generate_transactions(vm, vmap, contracts, rates):
    contract_by_supplier = contracts.set_index("supplier_name")
    rate_lookup = rates.set_index(["contract_id", "rate_year", "item_code"])["contract_rate"]
    vendors_by_supplier = vmap.groupby("supplier_id")["vendor_id"].apply(list)
    vendor_names = vm.set_index("vendor_id")["vendor_name"]

    po_rows, truth_rows, gr_rows, inv_rows = [], [], [], []
    po_counter, inv_counter = 4500000001, 900000001

    for site in SITES:
        site_id, size = site[0], site[3]
        for month in MONTHS:
            ta_frac, ta_start, ta_end = turnaround_overlap(site, month)
            # Materials are bought in the six weeks before a turnaround starts.
            pre_frac, _, _ = turnaround_overlap((site[0], 0, 0, 0,
                                                 str((ta_start - pd.Timedelta(days=42)).date()), 42),
                                                month)
            for cat, c in CAT.items():
                boost = ta_frac if c["kind"] == "service" else max(ta_frac, pre_frac)
                lam = c["lam"] * size * (1 + (c["ta_mult"] - 1) * boost)
                n_pos = rng.poisson(lam / 2)
                for _ in range(n_pos):
                    day = int(rng.integers(0, month.days_in_month))
                    po_date = month + pd.Timedelta(days=day)
                    in_ta = ta_start - pd.Timedelta(days=42) <= po_date <= ta_end
                    s = choose_supplier(cat, site_id, po_date)
                    vendor_id = rng.choice(vendors_by_supplier[s["supplier_id"]])
                    po_number = str(po_counter)
                    po_counter += 1

                    # PO cycle time: Pasadena's approval process is much slower.
                    cycle = rng.gamma(3, 5) if site_id == "PAS" else rng.gamma(2, 2.2)
                    req_date = po_date - pd.Timedelta(days=int(round(cycle)))

                    contract = None
                    if s["name"] in contract_by_supplier.index:
                        ct = contract_by_supplier.loc[s["name"]]
                        if po_date <= pd.Timestamp(ct["end_date"]) and rng.random() > 0.05:
                            contract = ct  # 5% of contracted-supplier lines skip the contract
                    terms = int(contract["payment_terms_days"]) if contract is not None else 30

                    n_lines = 1 + rng.poisson(1.0)
                    for line_no in range(1, n_lines + 1):
                        it = ITEMS_BY_CAT[cat][rng.integers(len(ITEMS_BY_CAT[cat]))]
                        factor = index_factor(cat, po_date)
                        market = (it["base_price"] or 0) * factor * rng.normal(1, 0.03)
                        flags = []

                        # ---- quantity and price ----
                        if it["passthrough"]:
                            cost = float(rng.lognormal(np.log(8000 * (2 if in_ta else 1)), 0.6))
                            qty, unit_price = 1, round(cost * (1 + MARKUP_CAP), 2)
                        else:
                            target = rng.lognormal(np.log(c["median_value"] * (1.6 if in_ta else 1)), 0.8)
                            qty = max(1, int(round(target / it["base_price"])))
                            if contract is not None:
                                unit_price = rate_lookup[(contract["contract_id"], po_date.year,
                                                          it["item_code"])]
                            elif s["role"] != "spot":
                                unit_price = market * rng.uniform(1.04, 1.10)  # contracted supplier, no contract ref
                                flags.append("contract_bypassed")
                            elif s["name"] in (P_BAYOU_VALVE, P_PELICAN):
                                unit_price = market * rng.uniform(1.22, 1.35)
                                flags.append("premium_spot_supplier")
                            else:
                                unit_price = market * rng.uniform(1.08, 1.25)
                            unit_price = round(float(unit_price), 2)
                        if s["name"] == P_ATCHAFALAYA and po_date > ATCHAFALAYA_EXPIRY:
                            flags.append("expired_contract")
                            if not it["passthrough"]:
                                unit_price = round(unit_price * 1.06, 2)
                        if s["name"] == P_COASTAL_HYDRO and po_date >= COASTAL_BLOCK_DATE:
                            flags.append("blocked_supplier")

                        # Planted data-entry errors: decimal point slips.
                        recorded_price = unit_price
                        if rng.random() < 0.0004:
                            recorded_price = round(unit_price * 100, 2)
                            flags.append("price_outlier")

                        # ---- messy fields ----
                        category_code = cat if rng.random() > 0.15 else None
                        material_number = it["material_number"] if rng.random() > 0.10 else None
                        site_raw = site_id if rng.random() > 0.04 else rng.choice(SITE_VARIANTS[site_id])

                        po_rows.append(dict(
                            po_number=po_number, po_line=line_no * 10, site=site_raw,
                            vendor_id=vendor_id, vendor_name=vendor_names[vendor_id],
                            requisition_date=req_date.date() if rng.random() > 0.01 else None,
                            po_date=po_date.date(), category_code=category_code,
                            material_number=material_number,
                            description=messify(it["description"], po_date, in_ta),
                            quantity=qty, unit=messy_unit(it["unit"]),
                            unit_price=recorded_price,
                            line_amount=round(qty * recorded_price, 2),
                            contract_id=contract["contract_id"] if contract is not None else None,
                            currency="USD",
                        ))
                        truth_rows.append(dict(
                            po_number=po_number, po_line=line_no * 10, true_site=site_id,
                            true_supplier_id=s["supplier_id"], true_category=cat,
                            true_item_code=it["item_code"], true_unit_price=unit_price,
                            in_turnaround_window=in_ta, flags=";".join(flags) or None,
                        ))

                        # ---- goods receipt ----
                        lead = int(rng.integers(5, 26)) if c["kind"] == "material" else int(rng.integers(0, 11))
                        promised = po_date + pd.Timedelta(days=lead)
                        p_on_time = s["base_otd"]
                        if s["name"] == P_DELTA and po_date >= pd.Timestamp("2025-01-01"):
                            p_on_time = 0.94 - 0.40 * (po_date.dayofyear / 365)  # steady decline
                        late = rng.random() > p_on_time
                        delay = int(rng.integers(1, 8) + rng.exponential(6)) if late else int(rng.integers(-2, 1))
                        if late and s["name"] == P_DELTA and po_date.year == 2025:
                            delay += int(rng.integers(5, 15))
                        actual = promised + pd.Timedelta(days=delay)
                        qty_received = qty if (qty == 1 or rng.random() > 0.03) else int(qty * rng.uniform(0.5, 0.9))
                        qty_rejected = (int(rng.integers(1, 3)) if c["kind"] == "material"
                                        and qty_received >= 3 and rng.random() < 0.015 else 0)
                        gr_rows.append(dict(
                            gr_id=f"GR{len(gr_rows) + 1:07d}", po_number=po_number, po_line=line_no * 10,
                            promised_date=promised.date(), actual_date=actual.date(),
                            qty_received=qty_received, qty_rejected=qty_rejected,
                        ))

                        # ---- invoice ----
                        inv_qty, inv_price = qty_received, unit_price
                        cost_basis, markup_billed = None, None
                        if qty_received < qty and rng.random() < 0.3:
                            inv_qty = qty  # billed for goods never received
                            truth_rows[-1]["flags"] = (truth_rows[-1]["flags"] or "") + ";billed_undelivered"
                        if it["passthrough"]:
                            cost_basis = round(cost * rng.uniform(0.9, 1.1), 2)
                            markup_billed = MARKUP_CAP
                            if s["name"] == P_SCAFFOLD and po_date >= SCAFFOLD_OVERBILL_START:
                                markup_billed = SCAFFOLD_BILLED_MARKUP
                                truth_rows[-1]["flags"] = (truth_rows[-1]["flags"] or "") + ";markup_over_cap"
                            inv_price = round(cost_basis * (1 + markup_billed), 2)
                        elif rng.random() < (0.10 if s["name"] == P_IRONCLAD else 0.015):
                            inv_price = round(unit_price * rng.uniform(1.03, 1.12), 2)
                            truth_rows[-1]["flags"] = (truth_rows[-1]["flags"] or "") + ";invoice_price_over_po"
                        inv_date = actual + pd.Timedelta(days=int(rng.integers(0, 11)))
                        if site_id == "FRP":
                            paid = inv_date + pd.Timedelta(days=int(rng.integers(10, 21)))  # pays early
                        else:
                            paid = inv_date + pd.Timedelta(days=terms + int(rng.integers(-3, 8)))
                        invoice_number = f"INV-{inv_counter}"
                        inv_counter += 1
                        inv = dict(
                            invoice_id=f"I{len(inv_rows) + 1:07d}", invoice_number=invoice_number,
                            vendor_id=vendor_id, po_number=po_number, po_line=line_no * 10,
                            invoice_date=inv_date.date(), invoice_qty=inv_qty,
                            invoice_unit_price=inv_price,
                            invoice_amount=round(inv_qty * inv_price, 2),
                            passthrough_cost=cost_basis,
                            markup_pct_billed=markup_billed * 100 if markup_billed is not None else None,
                            payment_terms_days=terms, paid_date=paid.date(),
                        )
                        inv_rows.append(inv)
                        if rng.random() < 0.004:  # planted duplicate invoice
                            dup = dict(inv)
                            dup["invoice_id"] = f"I{len(inv_rows) + 1:07d}"
                            dup["invoice_number"] = invoice_number + rng.choice(["", "A", "-1"])
                            dup["invoice_date"] = (inv_date + pd.Timedelta(days=int(rng.integers(5, 30)))).date()
                            dup["paid_date"] = (pd.Timestamp(dup["invoice_date"])
                                                + pd.Timedelta(days=terms)).date()
                            inv_rows.append(dup)
                            truth_rows[-1]["flags"] = (truth_rows[-1]["flags"] or "") + ";duplicate_invoice"

    truth = pd.DataFrame(truth_rows)
    truth["flags"] = truth["flags"].str.strip(";")
    return pd.DataFrame(po_rows), truth, pd.DataFrame(gr_rows), pd.DataFrame(inv_rows)


# ---------------------------------------------------------------------------
# 8. EQUIPMENT AND WORK ORDERS (for spare parts demand forecasting)
# ---------------------------------------------------------------------------
EQUIPMENT_TYPES = {
    # type: (count per site at size 1, PM per year, corrective per year, parts used)
    "Centrifugal Pump": (30, 3.0, 1.0, {"C11-02": (1, 0.7), "C11-01": (2, 0.6), "C11-05": (1, 0.15),
                                        "C11-06": (1, 0.3), "C11-03": (2, 0.5)}),
    "Compressor": (4, 4.0, 1.2, {"C11-04": (1, 0.6), "C11-03": (4, 0.7), "C11-01": (2, 0.5)}),
    "Control Valve": (40, 1.0, 0.5, {"C11-03": (2, 0.8), "C11-04": (1, 0.5)}),
    "Heat Exchanger": (15, 0.5, 0.15, {"C11-03": (8, 0.9)}),
    "Electric Motor": (25, 1.5, 0.3, {"C11-01": (2, 0.7), "C11-07": (2, 0.4)}),
}


def generate_work_orders():
    eq_rows, wo_rows, part_rows = [], [], []
    for site in SITES:
        site_id, size = site[0], site[3]
        for eq_type, (count, pm_rate, cm_rate, parts) in EQUIPMENT_TYPES.items():
            for k in range(max(1, int(round(count * size)))):
                eq_id = f"{site_id}-{eq_type.split()[-1][:4].upper()}-{k + 1:03d}"
                eq_rows.append(dict(equipment_id=eq_id, site_id=site_id, equipment_type=eq_type,
                                    criticality=rng.choice(["A", "B", "C"], p=[0.2, 0.5, 0.3]),
                                    install_year=int(rng.integers(1985, 2020))))
                for year in (2023, 2024, 2025):
                    cm = cm_rate
                    if site_id == "BTR" and eq_type == "Centrifugal Pump" and year == 2025:
                        cm *= 2.5  # planted: rising pump failures at Baton Rouge
                    for wo_type, rate in (("PM", pm_rate), ("CM", cm)):
                        for _ in range(rng.poisson(rate)):
                            created = pd.Timestamp(f"{year}-01-01") + pd.Timedelta(days=int(rng.integers(0, 365)))
                            wo_id = f"WO{len(wo_rows) + 1:07d}"
                            wo_rows.append(dict(
                                wo_id=wo_id, site_id=site_id, equipment_id=eq_id, wo_type=wo_type,
                                created_date=created.date(),
                                completed_date=(created + pd.Timedelta(days=int(rng.integers(0, 15)))).date(),
                            ))
                            use_prob = 1.0 if wo_type == "CM" else 0.35
                            for item_code, (qty, p) in parts.items():
                                if rng.random() < p * use_prob:
                                    part_rows.append(dict(
                                        wo_id=wo_id,
                                        material_number=ITEM_BY_CODE[item_code]["material_number"],
                                        qty_used=int(rng.integers(1, qty + 1)),
                                    ))
    return pd.DataFrame(eq_rows), pd.DataFrame(wo_rows), pd.DataFrame(part_rows)


# ---------------------------------------------------------------------------
# 9. MAIN
# ---------------------------------------------------------------------------
def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    KEY_DIR.mkdir(parents=True, exist_ok=True)

    sites, categories, items = build_sites(), build_categories(), build_item_master()
    vm, vmap = build_vendor_master()
    contracts, rates = build_contracts(vmap)
    print("Generating purchase orders, receipts and invoices (takes about a minute)...")
    po, truth, gr, inv = generate_transactions(vm, vmap, contracts, rates)
    equipment, work_orders, wo_parts = generate_work_orders()

    outputs = {
        RAW_DIR / "sites.csv": sites, RAW_DIR / "categories.csv": categories,
        RAW_DIR / "item_master.csv": items, RAW_DIR / "vendor_master.csv": vm,
        RAW_DIR / "contracts.csv": contracts, RAW_DIR / "contract_rates.csv": rates,
        RAW_DIR / "po_lines.csv": po, RAW_DIR / "goods_receipts.csv": gr,
        RAW_DIR / "invoices.csv": inv, RAW_DIR / "equipment.csv": equipment,
        RAW_DIR / "work_orders.csv": work_orders, RAW_DIR / "wo_parts.csv": wo_parts,
        KEY_DIR / "vendor_map.csv": vmap, KEY_DIR / "po_line_truth.csv": truth,
    }
    for path, df in outputs.items():
        df.to_csv(path, index=False)
        print(f"  {path.relative_to(ROOT)!s:<40} {len(df):>7,} rows")

    po["year"] = pd.to_datetime(po["po_date"]).dt.year
    clean_amount = truth["true_unit_price"] * po["quantity"]
    print("\nSpend by year (excluding planted price errors):")
    print(clean_amount.groupby(po["year"]).sum().map("${:,.0f}".format).to_string())
    print("\nPlanted pattern counts (PO lines):")
    print(truth["flags"].str.split(";").explode().value_counts().to_string())


if __name__ == "__main__":
    main()
