"""
Crude oil and natural gas production from multiple sources.
Replaces Section 2 (Producción) of preprocesamiento.Rmd (lines ~380-720).
"""

from functools import reduce
from pathlib import Path
import pandas as pd
import numpy as np

from utils.conversores import (
    m3_to_bbl_q,
    m3_to_mmbtu_q,
    ft3_to_m3_q,
    mmbtu_to_bep_q,
)
from preproc.indices_precios import YEAR_LAST, YEAR_SEC_ENERGIA_UPPER

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"


# ---- Shared helpers ----

def _load_anuario() -> pd.DataFrame:
    """Combustibles yearbook 1911+. Returns anio, crudo_anuario (m3), gas_anuario_MMm3."""
    df = pd.read_excel(DATA / "anuario_de_combustibles/Produccion_Desde_1911.xls")
    df = df.rename(columns={
        "AÑO": "anio",
        "PETROLEO (Mm3)": "crudo_anuario_Mm3",
        "GAS NATURAL (Mill. m3)": "gas_h",
        "CARBON (MTn) (*)": "carbon_h",
    })
    df["gas_anuario_MMm3"] = pd.to_numeric(df["gas_h"], errors="coerce")
    df["carbon_anuario_Mtn"] = pd.to_numeric(df["carbon_h"], errors="coerce")
    df["crudo_anuario"] = df["crudo_anuario_Mm3"] * 1000  # Mm3 → m3
    return df[["anio", "crudo_anuario", "gas_anuario_MMm3", "carbon_anuario_Mtn"]]


def _load_mecon_base() -> pd.DataFrame:
    """MECON monthly hydrocarbon production/prices base (ISO-8859-1 CSV)."""
    df = pd.read_csv(
        DATA / "mecon/hidrocarburos_produccion.csv",
        encoding="ISO-8859-1",
    )
    df["fecha"] = pd.to_datetime(df["indice_tiempo"], dayfirst=True, errors="coerce")
    drop_cols = [c for c in df.columns[:3]] + ["fuente", "indice_tiempo", "alcance_id"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    df.insert(0, "fecha", df.pop("fecha"))
    return df


# ========== CRUDE OIL ==========

def _load_prod_mecon_crudo(mecon_base: pd.DataFrame) -> pd.DataFrame:
    indicadores = mecon_base["indicador"].unique()
    df = mecon_base[
        (mecon_base["indicador"] == indicadores[2])
        & (mecon_base["actividad_producto_nombre"] == "Petróleo crudo")
        & (mecon_base["frecuencia_nombre"] == "Mensual")
    ].copy()
    df["anio"] = df["fecha"].dt.year
    return (
        df.groupby(["anio", "actividad_producto_nombre", "indicador", "unidad_de_medida"])["valor"]
        .sum()
        .reset_index()
        .rename(columns={"valor": "crudo_mecon"})
    )


def _load_prod_regalias_crudo() -> pd.DataFrame:
    df = pd.read_csv(
        DATA / "secretaria_energia/regalias/produccion_crudo_regalias.csv",
        sep=";",
        encoding="utf-8",
    )
    df = df.rename(columns={"AÑO": "anio"})
    df["anio"] = df["anio"].ffill()
    df["unidad"] = "m3"
    return (
        df.groupby(["anio", "unidad"])["TOTAL CUENCA"]
        .sum()
        .reset_index()
        .rename(columns={"TOTAL CUENCA": "crudo_regalias"})
    )


def _load_prod_sesco_crudo() -> pd.DataFrame:
    conceptos = {
        "Producción Primaria (m3)",
        "Producción Secundaria (m3)",
        "Producción por Recuperación Aisistida (m3)",
    }

    pre = pd.read_csv(DATA / "secretaria_energia/sesco/produccin-de-petrleo-anterior-al-2009.csv")
    pre = pre.rename(columns={"Cantidad": "cantidad"})
    pre = pre[pre["concepto"].isin(conceptos)]

    post = pd.read_csv(DATA / "secretaria_energia/sesco/produccin-de-petrleo-por-yacimiento.csv")
    post = post[post["concepto"].isin(conceptos)]

    df = pd.concat([pre, post], ignore_index=True)
    result = (
        df.groupby("anio")["cantidad"]
        .sum()
        .reset_index()
        .rename(columns={"cantidad": "crudo_sesco"})
    )
    result["unidad"] = "m3"
    return result


def _load_prod_sec_energia_crudo() -> pd.DataFrame:
    df = pd.read_csv(DATA / "secretaria_energia/sesco/serie-produccion-petroleo-total-pais-desde-1950.csv")
    df["produccion_petroleo"] = df["produccion_petroleo"] * 1000
    df["unidad"] = "m3"
    return df.rename(columns={"produccion_petroleo": "crudo_sec_energia"})


def _load_prod_eia_crudo() -> pd.DataFrame:
    """EIA crude oil production (Mb/d) → annual barrels."""
    df = pd.read_csv(DATA / "eia/oil_production_arg.csv", skiprows=1)
    df = df[df["API"].notna()].drop(columns=["API"])
    df = df.melt(id_vars=[df.columns[0]], var_name="anio", value_name="valor")
    df = df.pivot_table(index="anio", columns=df.columns[0], values="valor", aggfunc="first").reset_index()
    # Rename long column names
    col_map = {c: c.strip() for c in df.columns}
    df = df.rename(columns=col_map)

    # Convert Mb/d → annual barrels
    mb_d_cols = [c for c in df.columns if "Mb/d" in c or "Mb" in c]
    for c in mb_d_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce") * 365 * 1000

    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    # Find crude condensate column
    crude_col = next((c for c in df.columns if "Crude oil including" in c or "crude_oil_condensate" in c), None)
    if crude_col:
        df = df[["anio", crude_col]].rename(columns={crude_col: "crudo_eia"})
    df["unidad"] = "barriles"
    return df


def build_prod_crudo() -> pd.DataFrame:
    """
    Merge all crude production sources, select primary series by year range.
    Returns DataFrame with columns: anio, variable, unidad, prod_crudo,
    regalias, mecon, sesco, anuario_combustibles, sec_energia, eia
    """
    mecon_base = _load_mecon_base()
    anuario = _load_anuario()
    regalias = _load_prod_regalias_crudo()
    mecon = _load_prod_mecon_crudo(mecon_base)
    sesco = _load_prod_sesco_crudo()
    sec_energia = _load_prod_sec_energia_crudo()
    eia = _load_prod_eia_crudo()

    # All sources are in m3; outer-join on anio so no year from any source is lost.
    sources = [
        regalias[["anio", "crudo_regalias"]],
        mecon[["anio", "crudo_mecon"]],
        sesco[["anio", "crudo_sesco"]],
        anuario[["anio", "crudo_anuario"]],
        sec_energia[["anio", "crudo_sec_energia"]],
    ]
    if "crudo_eia" in eia.columns:
        sources.append(eia[["anio", "crudo_eia"]])

    df = reduce(lambda l, r: l.merge(r, on="anio", how="outer"), sources)

    # Convert all m3 cols to barrels
    for col in ["crudo_regalias", "crudo_mecon", "crudo_sesco", "crudo_anuario", "crudo_sec_energia"]:
        if col in df.columns:
            df[col] = m3_to_bbl_q(pd.to_numeric(df[col], errors="coerce"))

    # Select primary series by year range
    conditions = [
        df["anio"] < 1950,
        (df["anio"] >= 1950) & (df["anio"] <= YEAR_SEC_ENERGIA_UPPER),
        df["anio"] > YEAR_SEC_ENERGIA_UPPER,
    ]
    choices = [
        df.get("crudo_anuario", np.nan),
        df.get("crudo_sec_energia", np.nan),
        df.get("crudo_sesco", np.nan),
    ]
    df["prod_crudo"] = np.select(conditions, choices, default=np.nan)
    df["unidad"] = "barriles"
    df["variable"] = "Producción de crudo según distintas fuentes"
    df = df.rename(columns={
        "crudo_regalias": "regalias",
        "crudo_mecon": "mecon",
        "crudo_sesco": "sesco",
        "crudo_anuario": "anuario_combustibles",
        "crudo_sec_energia": "sec_energia",
    })
    df = df[df["anio"] <= YEAR_LAST].sort_values("anio").reset_index(drop=True)
    front = ["anio", "variable", "unidad", "prod_crudo"]
    rest = [c for c in df.columns if c not in front]
    return df[front + rest]


# ========== NATURAL GAS ==========

def _load_prod_mecon_gas(mecon_base: pd.DataFrame) -> pd.DataFrame:
    indicadores = mecon_base["indicador"].unique()
    df = mecon_base[
        (mecon_base["indicador"] == indicadores[2])
        & (mecon_base["actividad_producto_nombre"] == "Gas natural")
        & (mecon_base["frecuencia_nombre"] == "Mensual")
    ].copy()
    df["anio"] = df["fecha"].dt.year
    return (
        df.groupby(["anio", "actividad_producto_nombre", "indicador", "unidad_de_medida"])["valor"]
        .sum()
        .reset_index()
        .rename(columns={"valor": "gas_mecon"})
    )


def _load_prod_regalias_gas() -> pd.DataFrame:
    df = pd.read_csv(
        DATA / "secretaria_energia/regalias/produccion_gas_regalias.csv",
        sep=";",
    )
    df = df.rename(columns={"AÑO": "anio"})
    df["anio"] = df["anio"].ffill()
    df["unidad"] = "Miles de m3"
    # Remove thousands separator and convert
    for col in df.select_dtypes("object").columns:
        if col not in ("anio", "MES", "unidad"):
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
    return (
        df.groupby(["anio", "unidad"])["TOTAL CUENCA"]
        .sum()
        .reset_index()
        .rename(columns={"TOTAL CUENCA": "gas_regalias"})
    )


def _load_prod_sesco_gas() -> pd.DataFrame:
    pre = pd.read_csv(DATA / "secretaria_energia/sesco/produccin-de-gas-anterior-al-2009.csv")
    pre = pre.rename(columns={"Cantidad": "cantidad"})
    pre = pre[pre["idconcepto"] != 4]

    post = pd.read_csv(DATA / "secretaria_energia/sesco/produccin-de-gas-por-yacimiento.csv")
    post = post[post["idconcepto"].isin([1, 2, 3])]

    df = pd.concat([pre, post], ignore_index=True)
    result = (
        df.groupby("anio")["cantidad"]
        .sum()
        .reset_index()
        .rename(columns={"cantidad": "gas_sesco"})
    )
    result["unidad"] = "Miles de m3"
    return result


def _load_prod_sec_energia_gas() -> pd.DataFrame:
    df = pd.read_csv(DATA / "secretaria_energia/sesco/producciongasnaturaldesde-1950.csv")
    df["produccion_gas_natural"] = df["produccion_gas_natural"] * 1000
    df["unidad"] = "Miles de m3"
    return df.rename(columns={"produccion_gas_natural": "sec_energia_prod"})


def _load_prod_eia_gas() -> pd.DataFrame:
    """EIA dry natural gas (BCF) → thousands of m3."""
    df = pd.read_csv(DATA / "eia/Dry_natural_gas_production_Argentina_Annual.csv", skiprows=4)
    df = df.rename(columns={
        "Year": "anio",
        df.columns[1]: "prod_eia",
    })
    # BCF → ft3 (×1e9) → m3, then /1000 for Mm3
    df["prod_eia"] = ft3_to_m3_q(pd.to_numeric(df["prod_eia"], errors="coerce") * 1_000_000)
    df["unidad"] = "Miles de m3"
    return df[["anio", "prod_eia", "unidad"]]


def build_prod_gas() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Merge all gas production sources, select primary series.
    Returns:
      prod_gas_Mm3    — in thousands of m3 (Miles de m3)
      prod_gas_mmbtu  — converted to MMBTU
      prod_gas_bep    — converted to BEP
    """
    mecon_base = _load_mecon_base()
    anuario = _load_anuario()
    regalias = _load_prod_regalias_gas()
    mecon = _load_prod_mecon_gas(mecon_base)
    sesco = _load_prod_sesco_gas()
    sec_energia = _load_prod_sec_energia_gas()
    eia = _load_prod_eia_gas()

    # All sources are in Miles de m3; outer-join on anio so no year from any source is lost.
    sources = [
        regalias[["anio", "gas_regalias"]],
        mecon[["anio", "gas_mecon"]],
        sesco[["anio", "gas_sesco"]],
        anuario[["anio", "gas_anuario_MMm3"]].assign(gas_anuario=lambda x: x["gas_anuario_MMm3"] * 1000)[["anio", "gas_anuario"]],
        sec_energia[["anio", "sec_energia_prod"]],
        eia[["anio", "prod_eia"]].rename(columns={"prod_eia": "gas_eia"}),
    ]
    df = reduce(lambda l, r: l.merge(r, on="anio", how="outer"), sources)
    df["unidad"] = "Miles de m3"

    conditions = [df["anio"] < 1993, df["anio"] >= 1993]
    choices = [df.get("gas_anuario", np.nan), df.get("gas_sesco", np.nan)]
    df["prod_gas"] = np.select(conditions, choices, default=np.nan)
    df["variable"] = "Producción de gas según distintas fuentes"
    df = df.dropna(subset=["prod_gas"])
    df = df.rename(columns={
        "gas_regalias": "regalias",
        "gas_mecon": "mecon",
        "gas_sesco": "sesco",
        "gas_anuario": "anuario_combustibles",
        "gas_eia": "eia",
    })
    df = df[df["anio"] <= YEAR_LAST].sort_values("anio").reset_index(drop=True)

    # Convert to MMBTU (Miles de m3 × 1000 → m3, then m3 → MMBTU)
    numeric_cols = [c for c in df.columns if c not in ("anio", "variable", "unidad")]
    mmbtu = df.copy()
    for col in numeric_cols:
        mmbtu[col] = m3_to_mmbtu_q(pd.to_numeric(df[col], errors="coerce") * 1000)
    mmbtu["unidad"] = "MMBTU"

    bep = mmbtu.copy()
    for col in numeric_cols:
        bep[col] = mmbtu_to_bep_q(pd.to_numeric(mmbtu[col], errors="coerce"))
    bep["unidad"] = "BEP"

    return df, mmbtu, bep


def build_prod_total(prod_crudo: pd.DataFrame, prod_gas_bep: pd.DataFrame) -> pd.DataFrame:
    """Total production in BEP (crude + gas)."""
    crudo = prod_crudo[["anio", "prod_crudo"]].copy()
    crudo["unidad"] = "BEP"
    crudo["prod_crudo"] = m3_to_bbl_q(crudo["prod_crudo"])  # already in bbl ≈ BEP for crude

    gas = prod_gas_bep[["anio", "prod_gas"]].copy()
    df = crudo.merge(gas, on="anio", how="outer")
    df["produccion_total_bep"] = df["prod_crudo"].add(df["prod_gas"], fill_value=0)
    return df


def run() -> dict:
    prod_crudo = build_prod_crudo()
    prod_gas_Mm3, prod_gas_mmbtu, prod_gas_bep = build_prod_gas()
    prod_total = build_prod_total(prod_crudo, prod_gas_bep)

    return dict(
        prod_crudo=prod_crudo,
        prod_gas_Mm3=prod_gas_Mm3,
        prod_gas_mmbtu=prod_gas_mmbtu,
        prod_gas_bep=prod_gas_bep,
        prod_total=prod_total,
    )


if __name__ == "__main__":
    result = run()
    print("produccion OK")
    for k, v in result.items():
        print(f"  {k}: {v.shape}")
