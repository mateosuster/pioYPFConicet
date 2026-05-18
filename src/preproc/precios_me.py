"""
External (world) market reference prices for crude oil and natural gas.
Corresponds to Section 'Precios de Referencia del Mercado Mundial' of
preprocesamiento.Rmd (lines ~1134-1766).

Outputs:
  precios_referencia_crudo  — crude export + world reference prices (USD/bbl)
  precio_mdomundial_gas_MMBTU — gas world prices (USD/MMBTU), all sources
"""

from pathlib import Path
import pandas as pd
import numpy as np

from utils.conversores import (
    m3_to_bbl_p,
    m3_to_mmbtu_p,
    ft3_to_mmbtu_p,
)

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"
UPDATE = ROOT / "update"


# ============================================================
#  Shared helper
# ============================================================

def _load_mecon_precios() -> pd.DataFrame:
    """
    'Precios' sheet from MECON national accounts XLS.
    Annual averages of: crude and gas internal/external prices,
    Brent UK, Brent-Dubai-WTI average.
    """
    df = pd.read_excel(
        DATA / "mecon/base-mineria-e-hidrocarburos cuentas nacionales.xls",
        sheet_name="Precios",
        skiprows=7,
        header=0,
    )
    # Columns by position (names are locale-encoded / unnamed):
    # 0=anio, 1=mes, 8=gas_me_ars_Mm3, 9=gas_mi_ars_Mm3,
    # 10=crudo_me_usd_m3, 11=crudo_me_usd_bbl, 12=crudo_mi_usd_m3,
    # 13=crudo_mi_usd_bbl, 14=prom_brent_dubai_wti, 15=brent_uk
    cols = df.columns
    df = df.rename(columns={
        cols[0]:  "anio",
        cols[1]:  "mes",
        cols[8]:  "precio_gas_me_pesos_Mm3",
        cols[9]:  "precio_gas_mi_pesos_Mm3",
        cols[10]: "precio_crudo_me_usd_m3",
        cols[11]: "precio_crudo_me_usd_bbl",
        cols[12]: "precio_crudo_mi_usd_m3",
        cols[13]: "precio_crudo_mi_usd_bbl",
        cols[14]: "promedio_brent_dubai_wti_usd_bbl",
        cols[15]: "brent_uk_usd_bbl",
    })
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df = df[df["anio"].notna() & ~df["anio"].between(2002, 2003)]
    num_cols = [c for c in df.columns if c not in ("anio", "mes")]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    return (
        df.groupby("anio")[
            ["precio_gas_me_pesos_Mm3", "precio_gas_mi_pesos_Mm3",
             "precio_crudo_me_usd_bbl", "precio_crudo_mi_usd_bbl",
             "promedio_brent_dubai_wti_usd_bbl", "brent_uk_usd_bbl"]
        ].mean()
        .reset_index()
    )


# ============================================================
#  CRUDE — loaders
# ============================================================

def _load_regalias_expo_crudo() -> pd.DataFrame:
    """
    Crude export reference price from royalties report (USD/bbl).
    Source: update/Regalias_CRUDO/Informe Regalias CRUDO.xlsx, sheet 'Tabla precios'.
    """
    path = UPDATE / "Regalias_CRUDO/Informe Regalias CRUDO.xlsx"
    if not path.exists():
        return pd.DataFrame(columns=["anio", "precio_expo_regalias_crudo"])

    df = pd.read_excel(path, sheet_name="Tabla precios", skiprows=12)
    # Columns: AÑO (encoding-safe: col 0), MES (col 1), …, TOTAL PROVINCIA (last)
    df = df.rename(columns={df.columns[0]: "anio", df.columns[1]: "mes",
                             df.columns[-1]: "total_tipo_crudo"})
    df["anio"] = df["anio"].ffill()
    df = df[df["total_tipo_crudo"].notna() & (df["total_tipo_crudo"] != 0)]
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["total_tipo_crudo"] = pd.to_numeric(df["total_tipo_crudo"], errors="coerce")
    result = (
        df[df["anio"] >= 2006]
        .groupby("anio")["total_tipo_crudo"]
        .mean()
        .reset_index()
        .rename(columns={"total_tipo_crudo": "precio_expo_regalias_crudo"})
    )
    # Source unit: USD/m3 → convert to USD/bbl
    result["precio_expo_regalias_crudo"] = m3_to_bbl_p(result["precio_expo_regalias_crudo"])
    result["unidad"] = "USD/barriles"
    return result


def _load_expo_crudo_sitc() -> pd.DataFrame:
    """UN Comtrade SITC crude export price (USD/bbl)."""
    path = DATA / "un_comtrade/expo_crudo_sitc.csv"
    if not path.exists():
        return pd.DataFrame(columns=["anio", "precio_expo_comtrade_sitc_crudo"])
    df = pd.read_csv(path)
    if "Period" in df.columns:
        df = df.rename(columns={"Period": "anio"})
    df = df.rename(columns={"expo_precio_bbl": "precio_expo_comtrade_sitc_crudo"})
    return df[["anio", "precio_expo_comtrade_sitc_crudo"]].dropna(subset=["anio"])


def _load_expo_crudo_hs() -> pd.DataFrame:
    """UN Comtrade HS crude export price (USD/bbl)."""
    path = DATA / "un_comtrade/expo_crudo_uncomtrade_hs.csv"
    if not path.exists():
        return pd.DataFrame(columns=["anio", "precio_expo_comtrade_hs_crudo"])
    df = pd.read_csv(path)
    if "Period" in df.columns:
        df = df.rename(columns={"Period": "anio"})
    df = df.rename(columns={"expo_precio_bbl": "precio_expo_comtrade_hs_crudo"})
    return df[["anio", "precio_expo_comtrade_hs_crudo"]].dropna(subset=["anio"])


def _load_indec_expo_crudo() -> pd.DataFrame:
    """INDEC crude export annual average price (USD/bbl)."""
    path = DATA / "indec/precio_anual_promedio_expo_hidro_indec.csv"
    if not path.exists():
        return pd.DataFrame(columns=["anio", "precio_expo_crudo_indec"])
    df = pd.read_csv(path)
    crudo = df[df["unidad"] == "usd/bbl"][["anio", "precio_expo_crudo_indec"]].copy()
    crudo["precio_expo_crudo_indec"] = pd.to_numeric(
        crudo["precio_expo_crudo_indec"], errors="coerce"
    )
    # Drop outlier (2002: ~5000, clearly an artifact)
    crudo.loc[crudo["precio_expo_crudo_indec"] > 300, "precio_expo_crudo_indec"] = np.nan
    return crudo


def _load_brent() -> pd.DataFrame:
    """Brent: historic nominal (data/precios_mundiales/brent.xlsx) + IEA daily (data/eia/RBRTEd.xls)."""
    frames = {}

    hist_path = DATA / "precios_mundiales/brent.xlsx"
    if hist_path.exists():
        b = pd.read_excel(hist_path, skiprows=4)
        b.columns = ["anio", "brent_historic", "brent_adjusted"]
        b["anio"] = pd.to_numeric(b["anio"], errors="coerce")
        b = b.dropna(subset=["anio"])
        b["anio"] = b["anio"].astype(int)
        frames["hist"] = b[["anio", "brent_historic"]]

    eia_path = DATA / "eia/RBRTEd.xls"
    if eia_path.exists():
        eia = pd.read_excel(eia_path, sheet_name="Data 1", skiprows=2)
        eia.columns = ["fecha", "brent_iea"]
        eia["fecha"] = pd.to_datetime(eia["fecha"], errors="coerce")
        eia = eia.dropna(subset=["fecha"])
        eia["anio"] = eia["fecha"].dt.year
        frames["iea"] = eia.groupby("anio")["brent_iea"].mean().reset_index()

    if not frames:
        return pd.DataFrame(columns=["anio", "brent_historic", "brent_iea"])

    df = frames.get("hist", pd.DataFrame(columns=["anio"]))
    if "iea" in frames:
        df = df.merge(frames["iea"], on="anio", how="outer")

    df["unidad"] = "USD/barriles"
    return df.sort_values("anio").reset_index(drop=True)


def _load_wti() -> pd.DataFrame:
    """WTI: EIA daily (data/eia/RWTCd.xls) + FRED (data/fread/WTISPLC.csv)."""
    frames = {}

    eia_path = DATA / "eia/RWTCd.xls"
    if eia_path.exists():
        eia = pd.read_excel(eia_path, sheet_name="Data 1", skiprows=2)
        eia.columns = ["fecha", "wti_eia"]
        eia["fecha"] = pd.to_datetime(eia["fecha"], errors="coerce")
        eia = eia.dropna(subset=["fecha"])
        eia["anio"] = eia["fecha"].dt.year
        frames["eia"] = eia.groupby("anio")["wti_eia"].mean().reset_index()

    fred_path = DATA / "fread/WTISPLC.csv"
    if fred_path.exists():
        fred = pd.read_csv(fred_path)
        fred["anio"] = pd.to_datetime(fred["DATE"]).dt.year
        frames["fred"] = (
            fred.groupby("anio")["WTISPLC"].mean().reset_index()
            .rename(columns={"WTISPLC": "wti_spot_price_fred"})
        )

    if not frames:
        return pd.DataFrame(columns=["anio"])

    df = frames.get("eia", pd.DataFrame(columns=["anio"]))
    if "fred" in frames:
        df = df.merge(frames["fred"], on="anio", how="outer")

    df["unidad"] = "USD/barriles"
    return df.sort_values("anio").reset_index(drop=True)


# ============================================================
#  CRUDE — builder
# ============================================================

def build_precios_referencia_crudo(tcp_anual: pd.DataFrame) -> pd.DataFrame:
    """
    Annual crude export and world reference prices (USD/bbl).
    Final column `precio_me_crudo` uses:
      MECON  for 1993-2001 and 2004-2014
      Comtrade HS for 2002-2003
      Regalías for > 2014
      Comtrade SITC for < 1993 (brent_historic where SITC is NA)
    """
    mecon = _load_mecon_precios()
    regalias = _load_regalias_expo_crudo()
    sitc = _load_expo_crudo_sitc()
    hs = _load_expo_crudo_hs()
    indec = _load_indec_expo_crudo()
    brent = _load_brent()
    wti = _load_wti()

    # Merge all sources (full outer)
    df = (
        sitc
        .merge(hs, on="anio", how="outer")
        .merge(
            regalias[["anio", "precio_expo_regalias_crudo"]],
            on="anio", how="outer",
        )
        .merge(
            mecon[["anio", "precio_crudo_me_usd_bbl"]].rename(
                columns={"precio_crudo_me_usd_bbl": "precio_expo_mecon_crudo"}
            ),
            on="anio", how="outer",
        )
        .merge(indec, on="anio", how="outer")
        .merge(brent[["anio", "brent_historic", "brent_iea"]], on="anio", how="outer")
        .merge(wti.drop(columns=["unidad"], errors="ignore"), on="anio", how="outer")
    )

    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df = df.sort_values("anio").reset_index(drop=True)
    df["unidad"] = "USD/barriles"

    # Composite price: mirror R case_when order
    sitc_col = df.get("precio_expo_comtrade_sitc_crudo", pd.Series(np.nan, index=df.index))
    conditions = [
        df["anio"].between(1993, 2001) | df["anio"].between(2004, 2014),
        df["anio"].between(2002, 2003),
        df["anio"] > 2014,
        sitc_col.isna(),
    ]
    choices = [
        df.get("precio_expo_mecon_crudo", pd.Series(np.nan, index=df.index)),
        df.get("precio_expo_comtrade_hs_crudo", pd.Series(np.nan, index=df.index)),
        df.get("precio_expo_regalias_crudo", pd.Series(np.nan, index=df.index)),
        df.get("brent_historic", pd.Series(np.nan, index=df.index)),
    ]
    df["precio_me_crudo"] = np.select(conditions, choices, default=sitc_col)

    front = ["anio", "unidad", "precio_me_crudo"]
    rest = [c for c in df.columns if c not in front]
    return df[front + rest].reset_index(drop=True)


# ============================================================
#  GAS — loaders
# ============================================================

def _load_regalias_expo_gas() -> pd.DataFrame:
    """
    Gas export reference price from royalties (ARS/Miles de m3).
    Source: update/Regalias_GAS/Informe Regalias GAS.xlsx, sheet 'Tabla precios'.
    """
    path = UPDATE / "Regalias_GAS/Informe Regalias GAS.xlsx"
    if not path.exists():
        return pd.DataFrame(columns=["anio", "precio_expo_gas_regalias"])

    df = pd.read_excel(path, sheet_name="Tabla precios", skiprows=12)
    df = df.rename(columns={df.columns[0]: "anio", df.columns[1]: "mes",
                             df.columns[-1]: "total_provincia"})
    df["anio"] = df["anio"].ffill()
    df = df[df["total_provincia"].notna() & (df["total_provincia"] != 0)]
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["total_provincia"] = pd.to_numeric(df["total_provincia"], errors="coerce")
    return (
        df.groupby("anio")["total_provincia"]
        .mean()
        .reset_index()
        .rename(columns={"total_provincia": "precio_expo_gas_regalias"})
    )


def _load_expo_gas_sitc(tcp_anual: pd.DataFrame) -> pd.DataFrame:
    """
    UN Comtrade SITC gas export price.
    Returns prices in USD/MMBTU and ARS/Miles de m3.
    """
    path = DATA / "un_comtrade/expo_gas_sitc.csv"
    if not path.exists():
        return pd.DataFrame(columns=["anio"])

    df = pd.read_csv(path)
    if "Period" in df.columns:
        df = df.rename(columns={"Period": "anio"})
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["expo_precio_Mm3"] = pd.to_numeric(df["expo_precio_Mm3"], errors="coerce")

    tcc_map = tcp_anual.set_index("anio")["tcc"]
    df["tcc"] = df["anio"].map(tcc_map)

    # expo_precio_Mm3 is in USD/m3 (column named Mm3 but values are per m3)
    df["expo_precio_MMBTU"] = m3_to_mmbtu_p(df["expo_precio_Mm3"])
    df["expo_precio_Mm3_ars"] = df["expo_precio_Mm3"] * df["tcc"]

    # Filter years used in R (drop isolated 1970/1979)
    df = df[~df["anio"].isin([1970, 1979])]

    return df[["anio", "expo_precio_MMBTU", "expo_precio_Mm3_ars"]].rename(
        columns={
            "expo_precio_MMBTU": "precio_expo_gas_comtrade_mmbtu",
            "expo_precio_Mm3_ars": "precio_expo_gas_comtrade_ars_Mm3",
        }
    )


def _load_henry_hub() -> pd.DataFrame:
    """Henry Hub spot price, annual average (USD/MMBTU). Uses update/ if available."""
    for path in [UPDATE / "RNGWHHDd.xls", DATA / "eia/RNGWHHDd.xls"]:
        if path.exists():
            df = pd.read_excel(path, sheet_name="Data 1", skiprows=2)
            df.columns = ["fecha", "henry_hub_spot"]
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            df = df.dropna(subset=["fecha"])
            df["anio"] = df["fecha"].dt.year
            return (
                df.groupby("anio")["henry_hub_spot"].mean().reset_index()
                .rename(columns={"henry_hub_spot": "eia_henry_hub_spot"})
            )
    return pd.DataFrame(columns=["anio", "eia_henry_hub_spot"])


def _load_wellhead_eeuu() -> pd.DataFrame:
    """US natural gas wellhead price (USD/Mft3 → USD/MMBTU)."""
    path = DATA / "eia/natural_gas_wellhead_price_eeuu.xls"
    if not path.exists():
        return pd.DataFrame(columns=["anio"])
    df = pd.read_excel(path, sheet_name="Data 1", skiprows=2)
    df.columns = ["fecha", "us_wellhead_price_Mft3"]
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"])
    df["anio"] = df["fecha"].dt.year
    agg = df.groupby("anio")["us_wellhead_price_Mft3"].mean().reset_index()
    # USD/Mft3 → USD/ft3 → USD/MMBTU
    agg["us_wellhead_price_MMBTU"] = ft3_to_mmbtu_p(agg["us_wellhead_price_Mft3"] / 1000)
    return agg[["anio", "us_wellhead_price_MMBTU"]]


def _load_prices_eeuu() -> pd.DataFrame:
    """US natural gas prices — 7 categories (USD/MMBTU). Selects cols 0-7 by position."""
    path = DATA / "eia/natural_gas_prices_usa.xls"
    if not path.exists():
        return pd.DataFrame(columns=["anio"])
    df = pd.read_excel(path, sheet_name="Data 1", skiprows=2, usecols=range(8))
    df.columns = [
        "fecha",
        "us_wellhead_gas_price",
        "us_import_gas_price",
        "us_pipeline_import_price",
        "us_lng_import_price",
        "us_export_gas_price",
        "us_export_gas_pipeline_price",
        "us_export_lng_price",
    ]
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"])
    df["anio"] = df["fecha"].dt.year

    value_cols = [c for c in df.columns if c not in ("fecha", "anio")]
    agg = df.groupby("anio")[value_cols].mean().reset_index()
    # Source is USD/Mft3; convert to USD/MMBTU
    for col in value_cols:
        agg[col] = ft3_to_mmbtu_p(agg[col] / 1000)
    agg["unidad"] = "USD/MMBTU"
    return agg


def _load_bp_gas() -> pd.DataFrame:
    """BP Statistical Review gas prices (USD/MMBTU)."""
    path = DATA / "bp/bp-stats-review-2020-all-data.xlsx"
    if not path.exists():
        return pd.DataFrame(columns=["anio"])
    df = pd.read_excel(path, sheet_name="Gas - Prices ", skiprows=3)
    df = df.rename(columns={
        df.columns[0]: "anio",
        "Japan": "bp_lng_japan_cif",
        "Japan Korea Marker": "bp_lng_jkm",
        "Average German": "bp_gas_german_import_price",
        "UK": "bp_gas_nbp",
        "Netherlands TTF": "bp_gas_netherlands_ttf",
        "US": "bp_gas_henry_hub",
        "Canada": "bp_gas_canada",
        "OECD": "bp_oil_mix_mean_oecd",
    })
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df = df.dropna(subset=["anio"])
    num_cols = [c for c in df.columns if c != "anio"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    df["anio"] = df["anio"].astype(int)
    df["unidad"] = "USD/MMBTU"
    return df


def _load_fmi_gas(bp_gas: pd.DataFrame) -> pd.DataFrame:
    """
    FMI commodity price index for gas, anchored to BP 2016 prices (USD/MMBTU).
    """
    path = DATA / "fmi/PCPS_09-16-2020 15-07-10-66_timeSeries.csv"
    if not path.exists() or bp_gas.empty:
        return pd.DataFrame(columns=["anio"])

    fmi = pd.read_csv(path)
    gas_names = ["Natural gas, EU", "Natural Gas, US Henry Hub Gas", "LNG, Asia"]
    fmi = fmi[
        fmi["Commodity Name"].isin(gas_names) & (fmi["Unit Name"] == "Index")
    ]

    year_cols = [c for c in fmi.columns if c.isdigit()]
    fmi_long = fmi.melt(
        id_vars=["Commodity Name"],
        value_vars=year_cols,
        var_name="anio",
        value_name="valor",
    )
    fmi_long["anio"] = pd.to_numeric(fmi_long["anio"], errors="coerce")
    fmi_long["valor"] = pd.to_numeric(fmi_long["valor"], errors="coerce") / 100
    fmi_wide = fmi_long.pivot_table(
        index="anio", columns="Commodity Name", values="valor"
    ).reset_index()
    fmi_wide.columns.name = None
    rename_map = {
        "LNG, Asia": "fmi_lng_asia",
        "Natural gas, EU": "fmi_natural_gas_eu",
        "Natural Gas, US Henry Hub Gas": "fmi_henry_hub",
    }
    fmi_wide = fmi_wide.rename(columns={k: v for k, v in rename_map.items() if k in fmi_wide.columns})

    # Anchor to BP 2016
    bp_2016 = bp_gas[bp_gas["anio"] == 2016].iloc[0] if 2016 in bp_gas["anio"].values else None
    if bp_2016 is not None:
        if "fmi_lng_asia" in fmi_wide.columns and "bp_lng_jkm" in bp_2016.index:
            fmi_wide["fmi_lng_asia"] = fmi_wide["fmi_lng_asia"] * bp_2016["bp_lng_jkm"]
        if "fmi_henry_hub" in fmi_wide.columns and "bp_gas_henry_hub" in bp_2016.index:
            fmi_wide["fmi_henry_hub"] = fmi_wide["fmi_henry_hub"] * bp_2016["bp_gas_henry_hub"]
        if "fmi_natural_gas_eu" in fmi_wide.columns and "bp_gas_netherlands_ttf" in bp_2016.index:
            fmi_wide["fmi_natural_gas_eu"] = fmi_wide["fmi_natural_gas_eu"] * bp_2016["bp_gas_netherlands_ttf"]

    fmi_wide["unidad"] = "USD/MMBTU"
    return fmi_wide


def _load_bolivia_ypfb() -> pd.DataFrame:
    """YPFB Bolivia gas export prices to Argentina/Brazil (USD/MMBTU)."""
    path = DATA / "ypfb/precio_expo_bolivia.xlsx"
    if not path.exists():
        return pd.DataFrame(columns=["anio"])
    df = pd.read_excel(path)
    # Original unit: USD/1000 ft3 → USD/MMBTU via ft3_to_mmbtu_p(x/1000)
    for col in ["precio_expo_bolivia_arg_gas", "precio_expo_bolivia_bzl_gas"]:
        if col in df.columns:
            df[col] = ft3_to_mmbtu_p(pd.to_numeric(df[col], errors="coerce") / 1000)
    df["unidad"] = "USD/MMBTU"
    return df.rename(columns={
        "precio_expo_bolivia_arg_gas": "precio_expo_bolivia_arg_ypfb",
        "precio_expo_bolivia_bzl_gas": "precio_expo_bolivia_bzl_ypfb",
    })


def _load_bolivia_impo_comtrade() -> pd.DataFrame:
    """Argentina's gas imports from Bolivia — UN Comtrade (USD/MMBTU)."""
    path = DATA / "un_comtrade/gas_impo_bolivia_comtrade.csv"
    if not path.exists():
        return pd.DataFrame(columns=["anio", "precio_impo_gas_arg_bolivia_comtrade"])
    df = pd.read_csv(path)
    if "Period" in df.columns:
        df = df.rename(columns={"Period": "anio"})
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["precio_impo_gas_bolivia"] = pd.to_numeric(df["precio_impo_gas_bolivia"], errors="coerce")
    # Unit: USD/Mm3 (thousands of m3); convert to USD/MMBTU
    df["precio_impo_gas_arg_bolivia_comtrade"] = m3_to_mmbtu_p(df["precio_impo_gas_bolivia"])
    # Drop years with suspect data (R filters 1994-1997)
    df = df[~df["anio"].between(1994, 1997)]
    return df[["anio", "precio_impo_gas_arg_bolivia_comtrade"]]


def _load_bolivia_expo_comtrade() -> pd.DataFrame:
    """Bolivia's gas exports to Argentina — UN Comtrade (USD/MMBTU)."""
    path = DATA / "un_comtrade/gas_expo_bolivia_comtrade.csv"
    if not path.exists():
        return pd.DataFrame(columns=["anio", "precio_expo_gas_bolivia_arg_comtrade"])
    df = pd.read_csv(path)
    if "Period" in df.columns:
        df = df.rename(columns={"Period": "anio"})
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["precio_expo_gas_bolivia"] = pd.to_numeric(df["precio_expo_gas_bolivia"], errors="coerce")
    df["precio_expo_gas_bolivia_arg_comtrade"] = m3_to_mmbtu_p(df["precio_expo_gas_bolivia"])
    return df[["anio", "precio_expo_gas_bolivia_arg_comtrade"]]


def _load_idee_bolivia(ipc: pd.DataFrame, conversor_pesos: pd.Series,
                       tcp_anual: pd.DataFrame) -> pd.DataFrame:
    """IDEE historical Bolivia gas price, converted to USD/MMBTU."""
    path = DATA / "idee/Precios del gas natural y derivados 1970 - 1988.xlsx"
    if not path.exists():
        return pd.DataFrame(columns=["anio"])
    df = pd.read_excel(path, skiprows=1, sheet_name=2)  # cuadro 4.3
    if "precio_gas_bolivia" not in df.columns:
        return pd.DataFrame(columns=["anio"])

    ipc_70 = ipc.set_index("anio")["ipc_70"] if "ipc_70" in ipc.columns else None
    if ipc_70 is None:
        return pd.DataFrame(columns=["anio"])

    df["ipc_70"] = df["anio"].map(ipc_70)
    # Convert pesos de 1970/Mm3 → ARS/Mm3
    df["precio_gas_bolivia_idee_ars"] = (
        df["precio_gas_bolivia"] * df["ipc_70"] / conversor_pesos["$Ley"]
    )
    tcc_map = tcp_anual.set_index("anio")["tcc"]
    df["tcc"] = df["anio"].map(tcc_map)
    df["precio_gas_bolivia_usd_Mm3"] = df["precio_gas_bolivia_idee_ars"] / df["tcc"]
    # USD/Mm3 → USD/MMBTU: divide by 1000 (Mm3→m3) then m3_to_mmbtu_p
    df["precio_impo_gas_bolivia_idee"] = m3_to_mmbtu_p(df["precio_gas_bolivia_usd_Mm3"] / 1000)
    return df[["anio", "precio_impo_gas_bolivia_idee"]]


# ============================================================
#  GAS — builder
# ============================================================

def build_precio_mdomundial_gas(
    tcp_anual: pd.DataFrame,
    ipc: pd.DataFrame,
    conversor_pesos: pd.Series,
) -> pd.DataFrame:
    """
    World gas market prices (USD/MMBTU), all sources merged.
    Final column `precio_externo_gas` uses:
      Bolivia Comtrade import for 1966-2019
      Regalías export price for > 2019
      Bolivia Comtrade export as default (pre-1966)
    """
    regalias = _load_regalias_expo_gas()
    sitc = _load_expo_gas_sitc(tcp_anual)
    indec = pd.read_csv(DATA / "indec/precio_anual_promedio_expo_hidro_indec.csv") \
        if (DATA / "indec/precio_anual_promedio_expo_hidro_indec.csv").exists() \
        else pd.DataFrame()
    henry = _load_henry_hub()
    wellhead = _load_wellhead_eeuu()
    us_prices = _load_prices_eeuu()
    bp = _load_bp_gas()
    fmi = _load_fmi_gas(bp)
    bol_ypfb = _load_bolivia_ypfb()
    bol_impo = _load_bolivia_impo_comtrade()
    bol_expo = _load_bolivia_expo_comtrade()
    idee_bol = _load_idee_bolivia(ipc, conversor_pesos, tcp_anual)

    # INDEC gas export price (USD/Mm3, years 2002-2019)
    indec_gas = pd.DataFrame(columns=["anio", "precio_expo_gas_indec"])
    if not indec.empty and "unidad" in indec.columns:
        indec_gas = (
            indec[indec["unidad"] == "usd/Mm3"][["anio", "precio_expo_gas_indec"]]
            .copy()
        )

    tcc_map = tcp_anual.set_index("anio")["tcc"]

    # Convert regalias gas (ARS/Mm3) → USD/MMBTU
    reg_usd = regalias.copy()
    if not reg_usd.empty:
        reg_usd["tcc"] = reg_usd["anio"].map(tcc_map)
        # ARS/Mm3 → ARS/m3 (/1000) → USD/m3 (/tcc) → USD/MMBTU (m3_to_mmbtu_p)
        reg_usd["precio_expo_gas_regalias_usd_mmbtu"] = m3_to_mmbtu_p(
            (reg_usd["precio_expo_gas_regalias"] / 1000) / reg_usd["tcc"]
        )
        reg_usd = reg_usd[["anio", "precio_expo_gas_regalias", "precio_expo_gas_regalias_usd_mmbtu"]]

    # Merge all sources
    df = us_prices.drop(columns=["unidad"], errors="ignore")
    for frame, key in [
        (henry, "anio"),
        (fmi.drop(columns=["unidad"], errors="ignore"), "anio"),
        (bol_ypfb.drop(columns=["unidad"], errors="ignore"), "anio"),
        (bol_impo, "anio"),
        (bol_expo, "anio"),
        (idee_bol, "anio"),
        (reg_usd, "anio"),
        (sitc, "anio"),
        (indec_gas, "anio"),
    ]:
        if not frame.empty:
            df = df.merge(frame, on=key, how="outer") if not df.empty \
                else frame.copy()

    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df = df.sort_values("anio").reset_index(drop=True)
    df["unidad"] = "USD/MMBTU"

    # Composite price
    impo_bol = df.get(
        "precio_impo_gas_arg_bolivia_comtrade",
        pd.Series(np.nan, index=df.index),
    )
    expo_reg = df.get(
        "precio_expo_gas_regalias_usd_mmbtu",
        pd.Series(np.nan, index=df.index),
    )
    expo_bol = df.get(
        "precio_expo_gas_bolivia_arg_comtrade",
        pd.Series(np.nan, index=df.index),
    )

    conditions = [
        df["anio"].between(1966, 2019),
        df["anio"] > 2019,
    ]
    choices = [impo_bol, expo_reg]
    df["precio_externo_gas"] = np.select(conditions, choices, default=expo_bol)

    # Argentine gas export price (what Argentina receives on its exports)
    expo_comtrade = df.get("precio_expo_gas_comtrade_mmbtu", pd.Series(np.nan, index=df.index))
    expo_regalias = df.get("precio_expo_gas_regalias_usd_mmbtu", pd.Series(np.nan, index=df.index))
    df["precio_exportacion_gas_ar"] = np.where(df["anio"] < 1999, expo_comtrade, expo_regalias)

    front = ["anio", "unidad", "precio_externo_gas", "precio_exportacion_gas_ar"]
    rest = [c for c in df.columns if c not in front]
    return df[front + rest].reset_index(drop=True)


# ============================================================
#  Entry point
# ============================================================

def run(
    tcp_anual: pd.DataFrame,
    ipc: pd.DataFrame,
    conversor_pesos: pd.Series,
) -> dict:
    precios_crudo = build_precios_referencia_crudo(tcp_anual)
    precio_gas = build_precio_mdomundial_gas(tcp_anual, ipc, conversor_pesos)

    return dict(
        precios_referencia_crudo=precios_crudo,
        precio_mdomundial_gas_MMBTU=precio_gas,
    )


if __name__ == "__main__":
    from preproc.indices_precios import run as run_indices
    aux = run_indices()
    result = run(aux["tcp_anual"], aux["ipc"], aux["conversor_pesos"])
    print("precios_me OK")
    for k, v in result.items():
        print(f"  {k}: {v.shape}")
        print(f"    columns: {v.columns.tolist()}")
        if "precio_me_crudo" in v.columns or "precio_externo_gas" in v.columns:
            key = "precio_me_crudo" if "precio_me_crudo" in v.columns else "precio_externo_gas"
            print(f"    {key} non-null: {v[key].notna().sum()}")
