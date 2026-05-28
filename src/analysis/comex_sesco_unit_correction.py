"""
Diagnostic analysis: unit-entry errors in new-format SESCO comex files.

Detects and documents rows where gas export quantities (cantidad) were entered
in m3 instead of the declared unit miles/m3, producing implied prices ~1000x
below the median. Applies a divide-by-1000 correction and compares annual
series before and after.

Run from project root:
    python src/analysis/comex_sesco_unit_correction.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "src"))

from utils.conversores import m3_to_bbl_q, m3_to_mmbtu_q

SESCO = ROOT / "data" / "secretaria_energia" / "sesco"
OUT = ROOT / "results" / "argentina" / "analisis_comex_sesco"
OUT.mkdir(parents=True, exist_ok=True)

SEP = "=" * 72


# ── loaders ──────────────────────────────────────────────────────────────────

def load_sesco_new() -> pd.DataFrame:
    files = [
        SESCO / "importaciones-exportaciones.csv",
        SESCO / "importaciones-exportaciones-a-partir-del-2016-.csv",
    ]
    frames = [pd.read_csv(f, encoding="utf-8-sig") for f in files if f.exists()]
    if not frames:
        raise FileNotFoundError("No new-format SESCO comex files found.")
    df = pd.concat(frames, ignore_index=True).drop_duplicates()
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce")
    return df


def filter_gas_expo(sn: pd.DataFrame) -> pd.DataFrame:
    """Pipeline natural gas exports only (excludes LNG = Gas Natural Licuado)."""
    mask = (
        sn["tipodecomercializacion"].str.contains("Exportaci", na=False)
        & sn["producto"].str.startswith("Gas Natural(", na=False)
        & (sn["unidad"] == "(miles/m3)")
        & sn["cantidad"].notna()
        & sn["monto"].notna()
    )
    return sn[mask].copy()


def filter_crudo_expo(sn: pd.DataFrame) -> pd.DataFrame:
    """Crude oil (all cuencas) exports for comparison."""
    mask = (
        sn["tipodecomercializacion"].str.contains("Exportaci", na=False)
        & sn["producto"].str.contains("Cuenca", na=False)
        & (sn["unidad"] == "(m3)")
        & sn["cantidad"].notna()
        & sn["monto"].notna()
    )
    return sn[mask].copy()


# ── implied-price analysis ────────────────────────────────────────────────────

def compute_implied_price(df: pd.DataFrame, qty_col: str = "cantidad") -> pd.Series:
    """USD per declared unit (monto / cantidad). NaN where cantidad == 0."""
    return df["monto"] / df[qty_col].replace(0, np.nan)


def detect_outliers(df: pd.DataFrame, threshold_factor: float = 100) -> pd.Series:
    """
    Boolean mask: rows whose implied price < median / threshold_factor.
    A factor of 100 is very conservative for a 1000× unit error.
    """
    price = compute_implied_price(df)
    threshold = price.median() / threshold_factor
    return price < threshold


def apply_correction(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with outlier cantidad values divided by 1000."""
    out = df.copy()
    mask = detect_outliers(out)
    out.loc[mask, "cantidad"] = out.loc[mask, "cantidad"] / 1000
    return out


# ── summary helpers ───────────────────────────────────────────────────────────

def annual_gas_mmbtu(df: pd.DataFrame, label: str) -> pd.DataFrame:
    agg = df.groupby("anio")[["cantidad", "monto"]].sum().reset_index()
    agg["expo_gas_mmbtu"] = m3_to_mmbtu_q(agg["cantidad"] * 1000)
    agg.columns = ["anio", f"cantidad_miles_m3_{label}",
                   f"monto_usd_{label}", f"expo_gas_mmbtu_{label}"]
    return agg


def annual_crudo_bbl(df: pd.DataFrame, label: str) -> pd.DataFrame:
    agg = df.groupby("anio")[["cantidad", "monto"]].sum().reset_index()
    agg["expo_crudo_bbl"] = m3_to_bbl_q(agg["cantidad"])
    agg.columns = ["anio", f"cantidad_m3_{label}",
                   f"monto_usd_{label}", f"expo_crudo_bbl_{label}"]
    return agg


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print(SEP)
    print("SESCO new-format comex — unit-error diagnostic")
    print(SEP)

    # 1. Load
    sn = load_sesco_new()
    print(f"\nLoaded {len(sn):,} rows from new SESCO files "
          f"({sn['anio'].min():.0f}–{sn['anio'].max():.0f})\n")

    # 2. Filter gas exports
    gas = filter_gas_expo(sn)
    print(f"Gas Natural exports (Exportacion, miles/m3): {len(gas):,} rows\n")

    # 3. Implied-price distribution
    gas["implied_usd_per_miles_m3"] = compute_implied_price(gas)
    pos = gas[gas["implied_usd_per_miles_m3"].notna() & (gas["cantidad"] > 0)]

    print("---Implied price distribution (USD / miles/m3) ---")
    print(pos["implied_usd_per_miles_m3"].describe().rename("value").to_frame().to_string())
    print()

    # 4. Identify outliers
    outlier_mask = detect_outliers(gas)
    outliers = gas[outlier_mask].copy()
    outliers["implied_price"] = compute_implied_price(outliers)

    median_p = gas["implied_usd_per_miles_m3"].median()
    threshold = median_p / 100
    print(f"Median price : {median_p:>10.2f} USD/miles/m3")
    print(f"Threshold    : {threshold:>10.4f} USD/miles/m3  (median / 100)")
    print(f"Outlier rows : {len(outliers)}\n")

    if outliers.empty:
        print("No outliers detected. No correction needed.")
    else:
        display_cols = ["anio", "mes", "empresa", "producto",
                        "cantidad", "monto", "implied_price"]
        print("---Outlier rows ---")
        print(outliers[display_cols].to_string(index=False))
        print()

        # 5. Show correction
        print("---Correction (cantidad ÷ 1000) ---")
        header = f"{'Date':>8}  {'Company':30}  {'Raw qty':>15}  "
        header += f"{'Corrected qty':>15}  {'Raw price':>12}  {'Corrected price':>16}"
        print(header)
        print("-" * len(header))
        for _, r in outliers.iterrows():
            corr_q = r["cantidad"] / 1000
            corr_p = r["monto"] / corr_q if corr_q > 0 else np.nan
            print(
                f"{int(r['anio'])}-{int(r['mes']):02d}  "
                f"{r['empresa'][:30]:30}  "
                f"{r['cantidad']:>15,.0f}  "
                f"{corr_q:>15,.1f}  "
                f"{r['implied_price']:>10.3f}  "
                f"{'->':>2}  {corr_p:>12.2f}"
            )
        print()

    # 6. Before / after annual comparison
    gas_raw = gas.copy()
    gas_corr = apply_correction(gas)

    annual_raw  = annual_gas_mmbtu(gas_raw,  "raw")
    annual_corr = annual_gas_mmbtu(gas_corr, "corrected")
    annual = annual_raw.merge(annual_corr[["anio", "expo_gas_mmbtu_corrected"]], on="anio")
    annual["diff_mmbtu"] = annual["expo_gas_mmbtu_corrected"] - annual["expo_gas_mmbtu_raw"]
    annual["diff_pct"] = annual["diff_mmbtu"] / annual["expo_gas_mmbtu_raw"].replace(0, np.nan) * 100

    print("---Annual gas exports: raw vs corrected (MMBTU) ---")
    cols = ["anio", "expo_gas_mmbtu_raw", "expo_gas_mmbtu_corrected", "diff_pct"]
    print(annual[cols].query("anio >= 2010").to_string(index=False, float_format="{:,.0f}".format))
    print()

    # 7. Crude as control: check for zero-monto rows (different phenomenon from unit errors)
    crudo = filter_crudo_expo(sn)
    crudo["implied_usd_per_m3"] = compute_implied_price(crudo)

    # Zero-monto rows: quantity recorded but no USD value (intra-group transfers, deferred pricing, etc.)
    zero_monto = crudo[crudo["monto"] == 0]
    # True unit errors (very low but non-zero monto): apply same threshold
    crudo_unit_errors = crudo[(crudo["monto"] > 0) & detect_outliers(crudo)]

    print(f"---Crude oil control ---")
    print(f"Crude rows          : {len(crudo):,}")
    print(f"Zero-monto rows     : {len(zero_monto):,}  (missing USD value — not a unit error)")
    print(f"Unit-error suspects : {len(crudo_unit_errors):,}  (non-zero monto, price >> 1000x below median)\n")
    if not zero_monto.empty:
        print("Zero-monto sample (first 10):")
        print(zero_monto[["anio", "mes", "empresa", "cantidad", "monto"]].head(10).to_string(index=False))
        print()

    # 8. Save outputs
    annual_corr_full = annual_gas_mmbtu(gas_corr, "corrected")
    annual_crudo_full = annual_crudo_bbl(crudo, "raw")

    annual.to_csv(OUT / "gas_expo_raw_vs_corrected.csv", index=False)
    outliers.to_csv(OUT / "gas_expo_outliers.csv", index=False)
    annual_crudo_full.to_csv(OUT / "crudo_expo_bbl.csv", index=False)
    pos["implied_usd_per_miles_m3"].describe().to_csv(OUT / "gas_implied_price_distribution.csv")

    print(SEP)
    print(f"Outputs saved to {OUT.relative_to(ROOT)}/")
    print("  gas_expo_raw_vs_corrected.csv")
    print("  gas_expo_outliers.csv")
    print("  crudo_expo_bbl.csv")
    print("  gas_implied_price_distribution.csv")
    print(SEP)


if __name__ == "__main__":
    main()
