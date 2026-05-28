"""
Capital stock from S&P Capital IQ financials (Petroarg.zip).
Alternative source for build_stock_balances_rama() in activos.py.

Phase 1 — extract_petroarg(): parse all Balance Sheet and Income Statement
  variables from every XLS in the ZIP and save to an intermediate CSV.
Phase 2 — build_stock_petroarg(): load the CSV, map to standard variable names,
  compute KTA, deflate by ipc_18, and return the same long-form schema as
  build_stock_balances_empresas().
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"

ZIP_PATH = ROOT / "update" / "Petroarg.zip"
INTERMEDIATE_CSV = DATA / "balances" / "petroarg_all_vars.csv"

# Each entry: unique ASCII keyword found in the ZIP filename → company metadata.
# Order matters: more-specific patterns must come before shorter ones.
_COMPANY_PATTERNS: list[tuple[str, dict]] = [
    ("Petrobras Argentina",  {"empresa": "Petrobras",          "sector": "integrada"}),
    ("Pan American Energy",  {"empresa": "PAE",                 "sector": "integrada"}),
    ("YPFD",                 {"empresa": "YPF",                 "sector": "integrada"}),
    ("CAPX",                 {"empresa": "Capex",               "sector": "produccion"}),
    ("Combustibles",         {"empresa": "CGC",                 "sector": "produccion"}),
    ("Aconcagua",            {"empresa": "Aconcagua",           "sector": "produccion"}),
    ("Comodoro",             {"empresa": "PCR",                 "sector": "produccion"}),
    ("Roch S A",             {"empresa": "Roch",                "sector": "produccion"}),
    ("Tecpetrol",            {"empresa": "Tecpetrol",           "sector": "produccion"}),
    ("TGNO4",                {"empresa": "TGN",                 "sector": "transporte"}),
    ("TGSU2",                {"empresa": "TGS",                 "sector": "transporte"}),
    ("Mega",                 {"empresa": "Mega",                "sector": "transporte"}),
    ("RAIZ4",                {"empresa": "Raízen",              "sector": "distribucion"}),
    ("Puma Energy",          {"empresa": "Puma Energy",         "sector": "distribucion"}),
    ("Comercial del Plata",  {"empresa": "Soc. Com. del Plata", "sector": "holding"}),
]

# Row labels that mark section headers or metadata — excluded from data rows.
_SKIP_LABELS = {
    "ASSETS", "LIABILITIES", "Supplemental Items", "Per Share Items",
    "U.S. GAAP Summary", "Supplemental Operating Expense Items",
    "Income Statement", "Balance Sheet", "Currency", "Exchange Rate",
    "Conversion Method", "Filing Date", "Restatement Type", "Calculation Type",
}

# Balance Sheet line items to include in the intermediate CSV mapping.
# All other rows are still extracted (raw label kept), but these get a clean name.
BALANCE_VARS: dict[str, str] = {
    "Total Cash & ST Investments":       "cash_st_inv",
    "Inventory":                         "inventarios",
    "Net Property, Plant & Equipment":   "ppye_neta",
    "Gross Property, Plant & Equipment": "ppye",
    "Total Current Assets":              "activo_corr",
    "Total Assets":                      "activo",
    "Total Liabilities":                 "pasivo",
    "Total Common Equity":               "patrimonio_neto",
    "Total Equity":                      "patrimonio_neto_total",
    "Total Debt":                        "deuda_total",
    "Net Debt":                          "deuda_neta",
    "Long-Term Debt":                    "deuda_lp",
}

INCOME_VARS: dict[str, str] = {
    "Revenue":                           "ventas_raw",
    "Total Revenue":                     "ventas",
    "Cost Of Goods Sold":                "costo_ventas",
    "Gross Profit":                      "ganancia_bruta",
    "Depreciation & Amort.":             "depreciacion",
    "Operating Income":                  "utilidad_operativa",
    "EBT Incl. Unusual Items":           "ebt",
    "Income Tax Expense":                "impuesto_ganancias",
    "Net Income to Company":             "utilidad_neta_empresa",
    "Net Income":                        "utilidad_neta",
    "EBITDA":                            "ebitda",
    "EBIT":                              "ebit",
}


def _match_company(filename: str) -> dict | None:
    for keyword, meta in _COMPANY_PATTERNS:
        if keyword in filename:
            return meta
    return None


def _extract_year(val) -> int | None:
    """Parse a year from a CIQ date cell (datetime object or string)."""
    if isinstance(val, datetime):
        return val.year
    m = re.search(r'\b(19|20)\d{2}\b', str(val))
    return int(m.group()) if m else None


def _parse_ciq_sheet(raw: pd.DataFrame, sheet_type: str) -> pd.DataFrame:
    """
    Parse one Balance Sheet or Income Statement from a raw (no-header) DataFrame.
    Returns long-form rows: variable, anio, valor_usd, exchange_rate, valor_ars_corriente.
    """
    keyword = "Balance Sheet as of:" if sheet_type == "balance_sheet" else "For the Fiscal Period Ending"

    # Find the header row
    header_idx = None
    for i, cell in enumerate(raw.iloc[:, 0]):
        if pd.notna(cell) and keyword in str(cell):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"Header row not found for sheet_type={sheet_type!r}")

    header_row = raw.iloc[header_idx]

    # Map column index → year (skip col 0 which is the label column)
    year_cols: dict[int, int] = {}
    for col_idx in range(1, raw.shape[1]):
        cell = header_row.iloc[col_idx]
        if pd.notna(cell) and str(cell).strip():
            yr = _extract_year(cell)
            if yr is not None:
                year_cols[col_idx] = yr

    if not year_cols:
        raise ValueError("No year columns found")

    # Find exchange rate row → {col_idx: rate}
    exchange_rates: dict[int, float] = {}
    for i, cell in enumerate(raw.iloc[:, 0]):
        if pd.notna(cell) and str(cell).strip() == "Exchange Rate":
            for col_idx in year_cols:
                er = raw.iloc[i, col_idx]
                if pd.notna(er) and er != "-":
                    try:
                        exchange_rates[col_idx] = float(er)
                    except (ValueError, TypeError):
                        pass
            break

    # Extract all data rows
    rows = []
    for i, cell in enumerate(raw.iloc[:, 0]):
        if not pd.notna(cell):
            continue
        label = str(cell).strip()
        if not label:
            continue
        # Skip metadata / section headers / notes
        if label in _SKIP_LABELS:
            continue
        if (label.startswith("Note:") or label.startswith("In Millions")
                or ">" in label or label == keyword):
            continue

        for col_idx, year in year_cols.items():
            raw_val = raw.iloc[i, col_idx]
            if pd.isna(raw_val) or raw_val == "-":
                valor_usd = np.nan
            else:
                try:
                    valor_usd = float(raw_val)
                except (ValueError, TypeError):
                    valor_usd = np.nan

            er = exchange_rates.get(col_idx, np.nan)
            if er and not np.isnan(er) and er != 0:
                valor_ars = valor_usd / er
            else:
                valor_ars = np.nan

            rows.append({
                "sheet":               sheet_type,
                "anio":                year,
                "variable":            label,
                "valor_usd":           valor_usd,
                "exchange_rate":       er,
                "valor_ars_corriente": valor_ars,
            })

    return pd.DataFrame(rows, columns=["sheet", "anio", "variable",
                                        "valor_usd", "exchange_rate", "valor_ars_corriente"])


def extract_petroarg(zip_path: Path = ZIP_PATH, output_csv: Path = INTERMEDIATE_CSV) -> Path:
    """
    Parse all XLS files in the ZIP and write every Balance Sheet and Income
    Statement row to output_csv in long form.  Exchange-rate conversion to
    current ARS is applied at this stage.
    """
    all_dfs: list[pd.DataFrame] = []

    with zipfile.ZipFile(zip_path) as zf:
        for filename in zf.namelist():
            meta = _match_company(filename)
            if meta is None:
                print(f"  Warning: no match for '{filename}', skipping")
                continue

            with zf.open(filename) as f:
                raw_bytes = f.read()

            for sheet_type, sheet_name in (
                ("balance_sheet",    "Balance Sheet"),
                ("income_statement", "Income Statement"),
            ):
                try:
                    buf = io.BytesIO(raw_bytes)
                    raw = pd.read_excel(buf, sheet_name=sheet_name,
                                        header=None, engine="xlrd")
                except Exception as exc:
                    print(f"  Warning: could not read '{sheet_name}' from '{filename}': {exc}")
                    continue

                try:
                    df = _parse_ciq_sheet(raw, sheet_type)
                except Exception as exc:
                    print(f"  Warning: parse failed for '{sheet_name}' / '{filename}': {exc}")
                    continue

                df["empresa"] = meta["empresa"]
                df["sector"]  = meta["sector"]
                all_dfs.append(df)

    result = pd.concat(all_dfs, ignore_index=True)
    col_order = ["empresa", "sector", "sheet", "anio", "variable",
                 "valor_usd", "exchange_rate", "valor_ars_corriente"]
    result = result[col_order]
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_csv, index=False)
    print(f"Saved {len(result):,} rows to {output_csv}")
    return output_csv


def build_stock_petroarg(ipc_18: pd.Series,
                          csv_path: Path = INTERMEDIATE_CSV) -> pd.DataFrame:
    """
    Load the intermediate CSV, select and rename Balance Sheet and Income
    Statement variables, compute KTA, deflate to 2018 pesos.

    KTA = Total Cash & ST Investments + Inventory + Net PPE

    Output schema matches build_stock_balances_empresas():
      columns: anio, empresa, fuente, sector, unidad, variable, valor
    """
    df = pd.read_csv(csv_path)

    all_vars = {**BALANCE_VARS, **INCOME_VARS}

    # Keep only mapped rows and rename
    df = df[df["variable"].isin(all_vars)].copy()
    df["variable"] = df["variable"].map(all_vars)

    # For each (empresa, sector, anio, sheet), take the last value per variable
    # ("last" keeps the restated entry when duplicates exist for the same year)
    df = (
        df.groupby(["empresa", "sector", "sheet", "anio", "variable"])["valor_ars_corriente"]
        .last()
        .reset_index()
    )

    # Pivot wide to compute KTA
    wide = df.pivot_table(
        index=["empresa", "sector", "anio"],
        columns="variable",
        values="valor_ars_corriente",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None

    # KTA = cash_st_inv + inventarios + ppye_neta
    kta_parts = [c for c in ("cash_st_inv", "inventarios", "ppye_neta") if c in wide.columns]
    if kta_parts:
        wide["KTA"] = wide[kta_parts].sum(axis=1, min_count=len(kta_parts))

    # Profit aliases matching Bolsar naming convention
    if "ebt" in wide.columns:
        wide["gcia_ant"] = wide["ebt"]
    if "utilidad_neta" in wide.columns:
        wide["gcia_desp"] = wide["utilidad_neta"]
    # Profit rates: gcia / KTA
    if "gcia_ant" in wide.columns and "KTA" in wide.columns:
        wide["tg_ant"] = wide["gcia_ant"] / wide["KTA"]
    if "gcia_desp" in wide.columns and "KTA" in wide.columns:
        wide["tg_desp"] = wide["gcia_desp"] / wide["KTA"]

    # Re-melt to long form
    id_cols = ["empresa", "sector", "anio"]
    val_cols = [c for c in wide.columns if c not in id_cols]
    long = wide.melt(id_vars=id_cols, value_vars=val_cols,
                     var_name="variable", value_name="valor_ars_corriente")

    long["valor"] = long["valor_ars_corriente"]
    long = long.drop(columns=["valor_ars_corriente"])

    long["fuente"] = "S&P Capital IQ"
    long["unidad"] = "Millones de pesos corrientes"
    long["anio"] = long["anio"].astype(int)

    long = long.dropna(subset=["valor"])

    cols = ["anio", "empresa", "fuente", "sector", "unidad", "variable", "valor"]
    return long[cols].sort_values(["empresa", "anio", "variable"]).reset_index(drop=True)


def run(ipc_18: pd.Series,
        zip_path: Path = ZIP_PATH,
        csv_path: Path = INTERMEDIATE_CSV) -> dict:
    extract_petroarg(zip_path, csv_path)
    stock = build_stock_petroarg(ipc_18, csv_path)
    return {"stock_petroarg": stock}


if __name__ == "__main__":
    from preproc.indices_precios import run as run_indices

    aux = run_indices()
    result = run(aux["ipc_18"])
    stock = result["stock_petroarg"]

    print(f"\nstock_petroarg: {stock.shape}")
    print(stock.head(15).to_string(index=False))
    print(f"\nCompanies  : {sorted(stock['empresa'].unique())}")
    print(f"Sectors    : {sorted(stock['sector'].unique())}")
    print(f"Variables  : {sorted(stock['variable'].unique())}")
    print(f"Year range : {stock['anio'].min()} - {stock['anio'].max()}")
