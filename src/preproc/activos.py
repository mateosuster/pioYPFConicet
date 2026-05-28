"""
Company assets (balance sheets, AFIP, YPF historical segments).
Replaces Section 9+10 (Activos) of preprocesamiento.Rmd (lines ~2656-2910).
"""

from pathlib import Path
import pandas as pd
import numpy as np

from preproc import petroarg

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"
UPDATE_DATA = ROOT / "update"


def build_stock_segmentos(ipc_18: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    YPF and Petrobras segment-level assets.
    Returns:
      stock_segmentos   — raw in current pesos, long form
      union_segmentos   — in current pesos, aggregated by sector+variable
    """
    ypf = pd.read_csv(DATA / "ypf/ypf_segmentos.csv").drop(columns=["...1"], errors="ignore")
    ypf["sector"] = ypf["sector"].replace("quimica", "petroquimica")
    ypf["anio"] = pd.to_datetime(ypf["fecha"]).dt.year
    ypf_sel = ypf[["anio", "empresa", "sector", "unidad"]].copy()
    ypf_sel["activo"] = ypf["activos"]

    pet = pd.read_csv(DATA / "balances/petrobras_arg_segmentos.csv").drop(columns=["...1"], errors="ignore")
    pet = pet.rename(columns={"fecha": "anio", "ppye": "prop_planta_equipo", "activos": "activo"})
    pet_sel = pet[["anio", "empresa", "unidad", "sector", "prop_planta_equipo", "activo"]].copy()

    # Melt to long form
    ypf_long = ypf_sel.melt(id_vars=["anio", "empresa", "sector", "unidad"],
                             var_name="variable", value_name="valor")
    pet_long = pet_sel.melt(id_vars=["anio", "empresa", "sector", "unidad"],
                             var_name="variable", value_name="valor")
    stock_seg = pd.concat([ypf_long, pet_long], ignore_index=True)
    stock_seg["unidad"] = "Millones de pesos corrientes"

    union = stock_seg.copy()
    union["unidad"] = "Millones de pesos corrientes"
    union = (
        union.groupby(["anio", "sector", "variable", "unidad"])["valor"]
        .sum()
        .reset_index()
    )
    union["fuente"] = "Activo de YPF y Petrobras"
    union["variable_sector"] = union["variable"] + " " + union["sector"]

    return stock_seg, union


def build_stock_balances_empresas(ipc_18: pd.Series) -> pd.DataFrame:
    """
    Company-level assets from balance sheets (Bolsar).
    In current pesos.
    """
    df = pd.read_csv(DATA / "balances/balances_arg.csv",
                     usecols=lambda c: c not in ["...1", "Unnamed: 0"])
    df = df[~df["empresa"].isin(["chevron_global", "petrobras_global"])]
    df["anio"] = pd.to_datetime(df["fecha"]).dt.year
    df["fuente"] = "Bolsar"
    df["unidad"] = "Millones de pesos corrientes"
    drop_cols = ["fecha", "pais", "rotacion"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    id_cols = ["anio", "fuente", "unidad", "empresa", "sector"]
    val_cols = [c for c in df.columns if c not in id_cols]
    long = df.melt(id_vars=id_cols, value_vars=val_cols, var_name="variable", value_name="valor")

    long["valor"] = pd.to_numeric(long["valor"], errors="coerce")

    empresa_map = {
        "petrobras_ar": "Petrobras",
        "tecpetrol": "Tecpetrol",
        "camuzzi_pamp": "Camuzzi Gas Pampeana",
        "metrogas": "Metrogas",
    }
    long["empresa"] = long["empresa"].replace(empresa_map)

    long = (
        long.groupby(["anio", "empresa", "fuente", "sector", "unidad", "variable"])["valor"]
        .sum()
        .reset_index()
    )
    keep_vars = ["KTA", "ppye", "ppye_neta", "inventarios", "activo_no_corr", "activo",
                 "gcia_ant", "gcia_desp", "tg_ant", "tg_desp"]
    return long[long["variable"].isin(keep_vars)].reset_index(drop=True)


def build_stock_balances_rama(
    stock_balances_empresas: pd.DataFrame,
    union_segmentos: pd.DataFrame,
) -> pd.DataFrame:
    """
    Branch-level capital stock: company balance sheets + YPF/Petrobras upstream segment.
    """
    upstream_ppye = union_segmentos[
        union_segmentos["variable_sector"] == "activo upstream"
    ].copy()
    upstream_ppye["sector"] = "produccion"
    upstream_ppye["variable"] = "ppye"
    upstream_ppye["fuente"] = "Bolsar"
    upstream_ppye["empresa"] = "YPF y Petrobras"
    upstream_ppye = upstream_ppye.drop(columns=["variable_sector"])

    combined = pd.concat([
        stock_balances_empresas.reset_index(drop=True),
        upstream_ppye[["anio", "sector", "variable", "unidad", "fuente", "valor"]],
    ], ignore_index=True)

    return (
        combined.groupby(["anio", "sector", "variable", "unidad", "fuente"])["valor"]
        .sum()
        .reset_index()
    )


def build_stock_afip(ipc_18: pd.Series) -> pd.DataFrame:
    """
    AFIP capital stock for extraction and petroleum services sectors.
    Deflated to 2018 pesos.
    """
    df = pd.read_excel(DATA / "afip/gcia_v8.xlsx", skiprows=4)
    df = df.iloc[:, :48]  # drop columns 49+
    df = df.rename(columns={"year": "anio", "idrama": "idsector"})
    df["sector"] = np.where(
        df["rama"] == "petro", "extraccion_petroleo_gas",
        np.where(df["rama"] == "ser_petro", "servicios_petroleros", df["rama"])
    )
    df["unidad"] = "pesos corrientes"

    agg = (
        df.groupby(["anio", "idsector", "sector", "unidad"])
        .apply(lambda g: pd.Series({
            "KTA": g[["disponibilidades", "bscambio", "inventarios", "bsuso"]].sum(axis=1).sum(),
            "ppye": g["bsuso"].sum(),
            "activo": g["activo"].sum(),
        }))
        .reset_index()
    )
    for col in ["KTA", "ppye", "activo"]:
        agg[col] = agg[col] / 1e6
    agg["unidad"] = "Millones de pesos corrientes"
    agg = agg.drop(columns=["idsector"])

    agg = agg[agg["sector"].isin(["extraccion_petroleo_gas", "servicios_petroleros"])]
    long = agg.melt(id_vars=["anio", "sector", "unidad"],
                    value_vars=["KTA", "ppye", "activo"],
                    var_name="variable", value_name="valor")
    long["fuente"] = "AFIP"
    return long.sort_values(["sector", "anio"]).reset_index(drop=True)


def _build_afip_old_raw() -> pd.DataFrame:
    """Old AFIP series (gcia_v8) in current pesos (millions) — for unit comparison only."""
    df = pd.read_excel(DATA / "afip/gcia_v8.xlsx", skiprows=4)
    df = df.iloc[:, :48].rename(columns={"year": "anio", "idrama": "idsector"})
    df["sector"] = np.where(
        df["rama"] == "petro", "extraccion_petroleo_gas",
        np.where(df["rama"] == "ser_petro", "servicios_petroleros", df["rama"])
    )
    df = df[df["sector"].isin(["extraccion_petroleo_gas", "servicios_petroleros"])].copy()
    df["_KTA"] = df[["disponibilidades", "bscambio", "inventarios", "bsuso"]].sum(axis=1)
    agg = (
        df.groupby(["anio", "sector"])
        .agg(KTA=("_KTA", "sum"), ppye=("bsuso", "sum"), activo=("activo", "sum"))
        .reset_index()
    )
    for col in ["KTA", "ppye", "activo"]:
        agg[col] = agg[col] / 1e6
    long = agg.melt(id_vars=["anio", "sector"],
                    value_vars=["KTA", "ppye", "activo"],
                    var_name="variable", value_name="valor")
    long["unidad"] = "Millones de pesos corrientes"
    long["fuente"] = "AFIP (v8)"
    return long.sort_values(["sector", "anio"]).reset_index(drop=True)


def build_stock_afip_new(ipc_18: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    New AFIP series from update/Serie_AFIP_Consolidada_2002_2022_V2.xlsx, sheet 'activo'.
    Sectors: 061+062 → extraccion_petroleo_gas, 091 → servicios_petroleros.
    Note: bienes_de_cambio in this source subsumes the old bscambio + inventarios.
    Returns: (raw current pesos, deflated to 2018 pesos), both long form.
    """
    df = pd.read_excel(
        UPDATE_DATA / "Serie_AFIP_Consolidada_2002_2022_V2.xlsx",
        sheet_name="activo",
    )
    sector_map = {
        "061": "extraccion_petroleo_gas",
        "062": "extraccion_petroleo_gas",
        "091": "servicios_petroleros",
    }
    df["code"] = df["actividad_economica"].str[:3]
    df = df[df["code"].isin(sector_map)].copy()
    df["sector"] = df["code"].map(sector_map)
    df = df.rename(columns={
        "anio_fiscal": "anio",
        "activo_total_importe": "activo",
        "activo_disponibilidades_importe": "disponibilidades",
        "activo_bienes_de_cambio_importe": "bscambio",
        "activo_bienes_de_uso_importe": "bsuso",
    })
    df["KTA"] = df["disponibilidades"] + df["bscambio"] + df["bsuso"]
    df["ppye"] = df["bsuso"]

    agg = (
        df.groupby(["anio", "sector"])[["KTA", "ppye", "activo"]]
        .sum()
        .reset_index()
    )

    # Raw: values are already in millions of pesos corrientes in the source file
    raw = agg.melt(id_vars=["anio", "sector"],
                   value_vars=["KTA", "ppye", "activo"],
                   var_name="variable", value_name="valor")
    raw["unidad"] = "Millones de pesos corrientes"
    raw["fuente"] = "AFIP (nuevo)"
    raw = raw.sort_values(["sector", "anio"]).reset_index(drop=True)

    deflated = agg.copy()
    deflated = deflated.melt(id_vars=["anio", "sector"],
                             value_vars=["KTA", "ppye", "activo"],
                             var_name="variable", value_name="valor")
    deflated["unidad"] = "Millones de pesos corrientes"
    deflated["fuente"] = "AFIP (nuevo)"
    deflated = deflated.sort_values(["sector", "anio"]).reset_index(drop=True)

    return raw, deflated


def build_stock_afip_combined(
    stock_afip_old: pd.DataFrame,
    stock_afip_new: pd.DataFrame,
    cutoff_year: int = 2014,
) -> pd.DataFrame:
    """
    Collage: old AFIP series (anio < cutoff_year) + new series (anio >= cutoff_year).
    Both inputs must be deflated long-form DataFrames with the same columns.
    """
    old_part = stock_afip_old[stock_afip_old["anio"] < cutoff_year].copy()
    new_part = stock_afip_new[stock_afip_new["anio"] >= cutoff_year].copy()
    combined = pd.concat([old_part, new_part], ignore_index=True)
    combined["fuente"] = "AFIP (combinada)"
    return combined.sort_values(["sector", "variable", "anio"]).reset_index(drop=True)


def build_balance_ypf(ipc_18: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    YPF historical balance sheet (Betania spreadsheet).
    Returns: balance_ypf (wide), stock_ypf (long, KTA/activo/ppye only)
    """
    df = pd.read_excel(
        DATA / "ypf/Calculos Betania Tg.xls",
        sheet_name="YPF_A $HOY_PARADEFLACYCALCULAR",
        skiprows=1,
    )
    df = df.iloc[:, :11].apply(pd.to_numeric, errors="coerce")
    df = df.rename(columns={
        "Año": "anio",
        "moneda": "unidad",
        "Ventas...3": "ventas",
        "Costo de las Ventas...4": "costo_ventas",
        "Utilidad neta": "utilidad_neta",
        "Utilidad operativa": "utilidad_operativa",
        "Bs Uso": "ppye",
        "Bs Cambio": "bienes_de_cambio",
        "UN antes de impuestos (g´ activos y dividendos)": "utilidad_neta_antes_impuestos",
        "Activo Total": "activo",
        "Patrimonio Neto": "patrimonio_neto",
    })
    df = df.dropna(subset=["anio"])
    num_cols = [c for c in df.columns if c not in ("anio", "unidad")]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce") / 1e6

    df["unidad"] = "Millones de pesos corrientes"
    df["KTA"] = df["ppye"] + df["bienes_de_cambio"]
    df["sector"] = "Memoria de YPF"

    # Zero out known bad years
    bad_years = [1983, 1985, 1986, 1987, 1988]
    for col in ["KTA", "activo", "ppye"]:
        df.loc[df["anio"].isin(bad_years), col] = 0

    stock_ypf = df.melt(
        id_vars=["anio", "sector", "unidad"],
        value_vars=["KTA", "activo", "ppye"],
        var_name="variable",
        value_name="valor",
    )
    return df, stock_ypf


def build_stock_balances_rama_alt(stock_petroarg: pd.DataFrame) -> pd.DataFrame:
    """
    Branch-level capital stock from S&P Capital IQ only.
    Each source (Bolsar, S&P CIQ, AFIP) must remain independent — no mixing.
    """
    return (
        stock_petroarg
        .groupby(["anio", "sector", "variable", "unidad", "fuente"])["valor"]
        .sum()
        .reset_index()
    )


def build_stock_estimado(
    stock_balances_empresas: pd.DataFrame,
    stock_afip_old: pd.DataFrame,
    stock_afip_new: pd.DataFrame,
    stock_afip: pd.DataFrame,
    stock_rama_alt: pd.DataFrame,
) -> pd.DataFrame:
    """
    Unified ppye table (one row/year per source) replacing stock_estimado(temporal).csv.
    Schema: anio, unidad, fuente_ppye, valor  (Millones de pesos corrientes)
    """
    def _ppye(df, fuente, sectors=None):
        sel = df[df["variable"] == "ppye"].copy()
        if sectors:
            sel = sel[sel["sector"].isin(sectors)]
        agg = sel.groupby("anio", as_index=False)["valor"].sum()
        agg["fuente_ppye"] = fuente
        agg["unidad"] = "Millones de pesos corrientes"
        return agg[["anio", "unidad", "fuente_ppye", "valor"]]

    parts = [
        _ppye(stock_balances_empresas, "Bolsar", ["integrada", "produccion"]),
        _ppye(stock_afip_old,  "AFIP (v8)"),
        _ppye(stock_afip_new,  "AFIP (nuevo)"),
        _ppye(stock_afip,      "AFIP (combinada)"),
        _ppye(stock_rama_alt,  "S&P Capital IQ", ["integrada", "produccion"]),
    ]
    return (
        pd.concat(parts, ignore_index=True)
        .sort_values(["fuente_ppye", "anio"])
        .reset_index(drop=True)
    )


def run(ipc_18: pd.Series) -> dict:
    stock_seg, union_seg = build_stock_segmentos(ipc_18)
    stock_empresas = build_stock_balances_empresas(ipc_18)
    stock_rama = build_stock_balances_rama(stock_empresas, union_seg)
    stock_afip_old = build_stock_afip(ipc_18)
    stock_afip_old_raw = _build_afip_old_raw()
    stock_afip_new_raw, stock_afip_new = build_stock_afip_new(ipc_18)
    stock_afip = build_stock_afip_combined(stock_afip_old, stock_afip_new)
    balance_ypf, stock_ypf = build_balance_ypf(ipc_18)

    stock_total = pd.concat([stock_afip, stock_rama], ignore_index=True)

    pet_result = petroarg.run(ipc_18)
    stock_pet = pet_result["stock_petroarg"]
    stock_rama_alt = build_stock_balances_rama_alt(stock_pet)

    stock_est = build_stock_estimado(
        stock_empresas, stock_afip_old, stock_afip_new, stock_afip, stock_rama_alt
    )

    return dict(
        stock_segmentos=stock_seg,
        union_segmentos=union_seg,
        stock_balances_empresas=stock_empresas,
        stock_balances_rama=stock_rama,
        stock_afip=stock_afip,               # combined (2001-2013 old + 2014-2022 new), deflated
        stock_afip_old=stock_afip_old,        # old source only, deflated
        stock_afip_new=stock_afip_new,        # new source only, deflated
        stock_afip_old_raw=stock_afip_old_raw,  # old source, current pesos (for comparison)
        stock_afip_new_raw=stock_afip_new_raw,  # new source, current pesos (for comparison)
        balance_ypf=balance_ypf,
        stock_ypf=stock_ypf,
        stock_rama=stock_total,
        stock_petroarg=stock_pet,
        stock_rama_alt=stock_rama_alt,
        stock_estimado=stock_est,
    )


if __name__ == "__main__":
    from preproc.indices_precios import run as run_indices
    aux = run_indices()
    result = run(aux["ipc_18"])
    print("activos OK")
    for k, v in result.items():
        print(f"  {k}: {v.shape}")

    # Quick unit comparison at 2014
    print("\n=== Unit check at 2014 (current pesos, millions) ===")
    for sector in ["extraccion_petroleo_gas", "servicios_petroleros"]:
        for var in ["KTA", "ppye", "activo"]:
            old_val = result["stock_afip_old_raw"].query(
                "anio==2014 and sector==@sector and variable==@var")["valor"]
            new_val = result["stock_afip_new_raw"].query(
                "anio==2014 and sector==@sector and variable==@var")["valor"]
            o = old_val.values[0] if len(old_val) else float("nan")
            n = new_val.values[0] if len(new_val) else float("nan")
            print(f"  {sector[:6]} {var}: old={o:,.0f}  new={n:,.0f}")
