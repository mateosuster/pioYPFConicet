"""
Download Argentina crude oil and natural gas export/import data from UN Comtrade.

Classifications:
  HS  : 2709 (crude petroleum), 271111 (LNG), 271121 (natural gas gaseous)
  SITC: 3310 (crude petroleum), 3411 (natural gas)

Coverage: 1962 to present (annual). Years batched to respect API limits.

Requires: pip install requests pandas python-dotenv
API key: https://comtradeapi.un.org/  (free registration)
Set COMTRADE_API_KEY in .env at repo root.

Country codes reference:
  https://comtradeapi.un.org/files/v1/app/reference/Reporters.json
"""

import os
import time
import datetime
import requests
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

# load .env from repo root (one level up from src/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── config ────────────────────────────────────────────────────────────────────
API_KEY = os.environ.get("COMTRADE_API_KEY", "")
if not API_KEY:
    raise EnvironmentError("COMTRADE_API_KEY not set. Add it to .env at repo root.")

# Reporter/partner codes
ARGENTINA = "32"
BOLIVIA   = "68"
WORLD     = "0"

FLOWS = {"X": "export", "M": "import"}

START_YEAR = 1962
END_YEAR = datetime.date.today().year
BATCH_SIZE = 12  # Comtrade free tier: max 12 periods per request

# "HS" = generic HS (covers all revisions, best for long history)
# "S3" = SITC Rev 3
QUERIES = [
    # Argentina <-> World
    ("HS", "crude_petroleum_hs",          ["2709"],            ARGENTINA, WORLD),
    ("HS", "natural_gas_hs",              ["271111", "271121"], ARGENTINA, WORLD),
    ("S2", "crude_petroleum_sitc_s2",        ["333"],              ARGENTINA, WORLD),
    ("S2", "natural_gas_sitc_s2",            ["341"],              ARGENTINA, WORLD),
    ("S1", "crude_petroleum_sitc_s1",        ["33101"],              ARGENTINA, WORLD),
    ("S1", "natural_gas_sitc_s1",            ["3411"],              ARGENTINA, WORLD),
    # Argentina <-> Bolivia (bilateral natural gas)
    ("HS", "natural_gas_hs_bol",          ["271111", "271121"], ARGENTINA, BOLIVIA),
    ("S2", "natural_gas_sitc_s2_bol",        ["341"],              ARGENTINA, BOLIVIA),
    ("S1", "natural_gas_sitc_s1_bol",        ["3411"],              ARGENTINA, BOLIVIA),
]

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "comtrade"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://comtradeapi.un.org/data/v1/get/C/A/{cl}"

SLEEP_BETWEEN = 5   # seconds between requests (free tier is strict)
MAX_RETRIES   = 3   # retries on 429
RETRY_SLEEP   = 30  # seconds to wait after a 429

# ── helpers ───────────────────────────────────────────────────────────────────

def year_batches(start: int, end: int, size: int) -> list[list[int]]:
    years = list(range(start, end + 1))
    return [years[i:i + size] for i in range(0, len(years), size)]


def fetch_batch(
    cl: str,
    cmd_codes: list[str],
    flow: str,
    years: list[int],
    reporter: str = ARGENTINA,
    partner: str = WORLD,
) -> pd.DataFrame:
    url = BASE_URL.format(cl=cl)
    params = {
        "reporterCode": reporter,
        "partnerCode": partner,
        "cmdCode": ",".join(cmd_codes),
        "flowCode": flow,
        "period": ",".join(str(y) for y in years),
        "includeDesc": "true",
        "subscription-key": API_KEY,
    }
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code == 429:
            print(f"429 rate-limit (attempt {attempt}/{MAX_RETRIES}), sleeping {RETRY_SLEEP}s ...", flush=True)
            time.sleep(RETRY_SLEEP)
            continue
        resp.raise_for_status()
        data = resp.json()
        if "message" in data and data.get("count", 1) == 0:
            print(f"[API msg] {data['message']}", flush=True)
        records = data.get("data", [])
        return pd.DataFrame(records) if records else pd.DataFrame()
    raise requests.HTTPError(f"429 after {MAX_RETRIES} retries")


def fetch_all_years(
    cl: str,
    cmd_codes: list[str],
    flow: str,
    reporter: str = ARGENTINA,
    partner: str = WORLD,
) -> pd.DataFrame:
    frames = []
    batches = year_batches(START_YEAR, END_YEAR, BATCH_SIZE)
    for batch in batches:
        print(f"    years {batch[0]}-{batch[-1]} ...", end=" ", flush=True)
        try:
            df = fetch_batch(cl, cmd_codes, flow, batch, reporter=reporter, partner=partner)
            print(f"{len(df)} rows")
            if not df.empty:
                frames.append(df)
        except requests.HTTPError as e:
            print(f"ERROR {e}")
        time.sleep(SLEEP_BETWEEN)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def keep_cols(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "refYear", "flowCode", "flowDesc",
        "reporterCode", "reporterDesc",
        "partnerCode", "partnerDesc",
        "cmdCode", "cmdDesc",
        "primaryValue", "netWgt", "qty", "qtyUnit",
        "classificationCode",
    ]
    return df[[c for c in cols if c in df.columns]]


# ── main ──────────────────────────────────────────────────────────────────────

all_frames = []

for cl, label, cmd_codes, reporter, partner in QUERIES:
    for flow_code, flow_name in FLOWS.items():
        out = OUTPUT_DIR / f"{label}_{flow_name}.csv"
        if out.exists():
            print(f"\nSkipping {label} | flow={flow_name} (already downloaded: {out})")
            if (df := pd.read_csv(out)).shape[0] > 0:
                df["commodity_label"] = label
                all_frames.append(df)
            continue

        print(f"\nFetching {label} | flow={flow_name} | cl={cl} | codes={cmd_codes}")
        df = fetch_all_years(cl, cmd_codes, flow_code, reporter=reporter, partner=partner)

        if df.empty:
            print("  no data")
            continue

        df = keep_cols(df)
        df["commodity_label"] = label
        all_frames.append(df)

        df.to_csv(out, index=False)
        print(f"  → {len(df)} rows saved to {out}")

# combined file
if all_frames:
    combined = pd.concat(all_frames, ignore_index=True)
    out = OUTPUT_DIR / "argentina_hydrocarbons_comtrade.csv"
    combined.to_csv(out, index=False)
    print(f"\nCombined: {len(combined)} rows → {out}")
else:
    print("\nNo data retrieved. Check API key and codes.")

# ── update legacy files ────────────────────────────────────────────────────────

import shutil

LEGACY_DIR  = Path(__file__).resolve().parent.parent / "data" / "un_comtrade"
NEW_CRUDE   = OUTPUT_DIR / "crude_petroleum_hs_export.csv"
NEW_GAS     = OUTPUT_DIR / "natural_gas_hs_export.csv"
CRUDE_LEGACY = LEGACY_DIR / "expo_crudo_uncomtrade_hs.csv"
GAS_LEGACY   = LEGACY_DIR / "expo_gas_sitc.csv"

LITRES_PER_BBL  = 158.987
GAS_DENSITY_KG_M3 = 0.7370  # empirical: legacy Qty(kg) / expo_Mm3(m3) = 0.7370

today_str = datetime.date.today().strftime("%Y%m%d")


def backup(path: Path) -> None:
    dest = path.with_name(path.stem + f"_backup_{today_str}" + path.suffix)
    shutil.copy2(path, dest)
    print(f"  backup → {dest.name}")


# ── crude update ──────────────────────────────────────────────────────────────
print("\n── Updating crude legacy ──")

if not NEW_CRUDE.exists():
    print(f"  {NEW_CRUDE.name} not found, skipping")
else:
    legacy_crude = pd.read_csv(CRUDE_LEGACY)
    # legacy first col is R row.names — rename for clarity
    legacy_crude.rename(columns={legacy_crude.columns[0]: "rownum"}, inplace=True)
    max_year_crude = legacy_crude["Period"].max()
    print(f"  legacy ends at {max_year_crude}")

    new_crude = pd.read_csv(NEW_CRUDE)
    # deduplicate (some years appear twice with same classificationCode)
    new_crude = new_crude.drop_duplicates(subset=["refYear", "cmdCode", "classificationCode"])
    new_crude = new_crude[new_crude["refYear"] > max_year_crude].copy()
    print(f"  new years to append: {sorted(new_crude['refYear'].unique())}")

    if not new_crude.empty:
        new_crude["expo_bbl"]       = new_crude["netWgt"] / LITRES_PER_BBL
        new_crude["expo_precio_bbl"] = new_crude["primaryValue"] / new_crude["expo_bbl"]

        append_crude = pd.DataFrame({
            "rownum":           range(len(legacy_crude) + 1, len(legacy_crude) + len(new_crude) + 1),
            "Period":           new_crude["refYear"].values,
            "Trade Flow":       new_crude["flowDesc"].values,
            "Reporter":         new_crude["reporterDesc"].values,
            "Partner":          new_crude["partnerDesc"].values,
            "Commodity Code":   new_crude["cmdCode"].values,
            "Trade Value (US$)": new_crude["primaryValue"].values,
            "Netweight (kg)":   new_crude["netWgt"].values,
            "Qty Unit":         "Weight in kilograms",
            "Qty":              new_crude["qty"].values,
            "Flag":             0,
            "expo_bbl":         new_crude["expo_bbl"].values,
            "expo_precio_bbl":  new_crude["expo_precio_bbl"].values,
        })

        backup(CRUDE_LEGACY)
        updated_crude = pd.concat([legacy_crude, append_crude], ignore_index=True)
        updated_crude.to_csv(CRUDE_LEGACY, index=False)
        print(f"  → {len(updated_crude)} rows saved to {CRUDE_LEGACY.name}")
    else:
        print("  no new years beyond legacy — nothing to append")


# ── gas update ────────────────────────────────────────────────────────────────
print("\n── Updating gas legacy ──")

if not NEW_GAS.exists():
    print(f"  {NEW_GAS.name} not found, skipping")
else:
    legacy_gas = pd.read_csv(GAS_LEGACY)
    legacy_gas.rename(columns={legacy_gas.columns[0]: "rownum"}, inplace=True)
    max_year_gas = legacy_gas["anio"].max()
    print(f"  legacy ends at {max_year_gas}")

    new_gas = pd.read_csv(NEW_GAS)
    # deduplicate within (year, cmdCode, classificationCode), then aggregate by year
    new_gas = new_gas.drop_duplicates(subset=["refYear", "cmdCode", "classificationCode"])
    new_gas = new_gas[new_gas["refYear"] > max_year_gas]
    new_gas = (
        new_gas.groupby("refYear", as_index=False)
        .agg(primaryValue=("primaryValue", "sum"), netWgt=("netWgt", "sum"))
    )
    print(f"  new years to append: {sorted(new_gas['refYear'].unique())}")

    if not new_gas.empty:
        new_gas["expo_Mm3"]       = new_gas["netWgt"] / GAS_DENSITY_KG_M3
        new_gas["expo_precio_Mm3"] = new_gas["primaryValue"] / new_gas["expo_Mm3"]

        append_gas = pd.DataFrame({
            "rownum":            range(len(legacy_gas) + 1, len(legacy_gas) + len(new_gas) + 1),
            "anio":              new_gas["refYear"].values,
            "Reporter":          "Argentina",
            "Partner":           "World",
            "Commodity Code":    271121,
            "Commodity":         "Gas, natural (HS)",
            "Qty":               new_gas["netWgt"].values,
            "Trade Value (US$)": new_gas["primaryValue"].values,
            "expo_Mm3":          new_gas["expo_Mm3"].values,
            "expo_precio_Mm3":   new_gas["expo_precio_Mm3"].values,
            "unidad_cantidad":   "kg",
            "unidad_precio":     "m3/usd",
        })

        backup(GAS_LEGACY)
        updated_gas = pd.concat([legacy_gas, append_gas], ignore_index=True)
        updated_gas.to_csv(GAS_LEGACY, index=False)
        print(f"  → {len(updated_gas)} rows saved to {GAS_LEGACY.name}")
    else:
        print("  no new years beyond legacy — nothing to append")
