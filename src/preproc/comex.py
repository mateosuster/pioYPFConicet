"""
Foreign trade (exports and imports) for crude oil and natural gas.
Replaces Section 4 (Comercio exterior) of preprocesamiento.Rmd (lines ~1800-2210).
"""

from pathlib import Path
import pandas as pd
import numpy as np

from utils.conversores import m3_to_bbl_q, m3_to_mmbtu_q

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"
SESCO = DATA / "secretaria_energia/sesco"


def _load_comex_sesco() -> pd.DataFrame:
    """SESCO combined: pre-2010 + post-2010 exports and imports."""
    post = pd.read_csv(SESCO / "comex_post2010.csv", sep=";", skiprows=5)
    post["unidad"] = np.where(post.get("Datos", "") == "Suma de monto", "USD", post.get("unidad", ""))
    post["unidad"] = post["unidad"].astype(str).str.replace(r"[()]", "", regex=True)
    post["fecha"] = pd.to_datetime(
        post["anio"].astype(str) + post["mes"].astype(str).str.zfill(2), format="%Y%m", errors="coerce"
    )
    rename_map = {"Exportación": "exportacion", "Importación": "importacion"}
    post = post.rename(columns=rename_map)
    post = post[["fecha", "anio", "mes", "producto", "unidad", "exportacion", "importacion"]].copy()
    post = post.melt(id_vars=["fecha", "anio", "mes", "producto", "unidad"],
                     var_name="variable", value_name="valor")

    def _load_pre(path: str, variable: str) -> pd.DataFrame:
        df = pd.read_csv(SESCO / path, sep=";")
        df = df.rename(columns={"Año": "anio", "Mes": "mes", "Producto": "producto", "Total": "valor"})
        df["anio"] = df["anio"].ffill()
        df["mes"] = df["mes"].ffill()
        df["producto"] = df["producto"].ffill()
        df["variable"] = variable
        datos = df.get("Datos", pd.Series(dtype=str)).astype(str)
        df["unidad"] = np.select(
            [datos.str.contains("M3", na=False),
             datos.str.contains("Ton", na=False),
             datos.str.contains("FOB", na=False)],
            ["m3", "ton", "USD"],
            default=None,
        )
        df["fecha"] = pd.to_datetime(
            df["anio"].astype(str) + df["mes"].astype(str).str.zfill(2), format="%Y%m", errors="coerce"
        )
        return df[["fecha", "anio", "mes", "producto", "variable", "unidad", "valor"]]

    expo_pre = _load_pre("expo_pre2010.csv", "exportacion")
    impo_pre = _load_pre("impo_pre2010.csv", "importacion")

    sesco = pd.concat([post, expo_pre, impo_pre], ignore_index=True)
    sesco["valor"] = np.where(sesco["unidad"] == "miles/m3", sesco["valor"] * 1000, sesco["valor"])
    sesco["unidad"] = sesco["unidad"].replace("miles/m3", "m3")
    return sesco.sort_values("fecha").reset_index(drop=True)


def _load_comex_mecon() -> pd.DataFrame:
    """MECON foreign trade from national accounts base."""
    df = pd.read_excel(
        DATA / "mecon/base-mineria-e-hidrocarburos cuentas nacionales.xls",
        sheet_name="Com. exterior",
        skiprows=7,
    )
    df = df.rename(columns={
        df.columns[0]: "anio",
        df.columns[1]: "expo_Mm3_crudo",
        df.columns[2]: "impo_Mm3_crudo",
        df.columns[3]: "saldo_Mm3_crudo",
        df.columns[4]: "expo_MMm3_gas",
        df.columns[5]: "impo_MMm3_gas",
        df.columns[6]: "saldo_Mm3_gas",
    })
    df = df[df["anio"].notna()].apply(pd.to_numeric, errors="coerce")
    df["expo_bbl_crudo"] = m3_to_bbl_q(df["expo_Mm3_crudo"] * 1000)
    df["impo_bbl_crudo"] = m3_to_bbl_q(df["impo_Mm3_crudo"] * 1000)
    df["saldo_bbl_crudo"] = m3_to_bbl_q(df["saldo_Mm3_crudo"] * 1000)
    df["expo_mmbtu_gas"] = m3_to_mmbtu_q(df["expo_MMm3_gas"] * 1e6)
    df["impo_mmbtu_gas"] = m3_to_mmbtu_q(df["impo_MMm3_gas"] * 1e6)
    return df


def _load_indec() -> tuple[pd.DataFrame, pd.DataFrame]:
    """INDEC export quantities and values from Datos_origen_2002_2025.xlsx (2002-2025)."""
    path = DATA / "indec/Datos_origen_2002_2025.xlsx"
    sheets = [
        "datos origen_2002-2011",
        "datos origen_2012-2022",
        "datos origen_2023-2025",
    ]
    frames = [pd.read_excel(path, sheet_name=s, header=0) for s in sheets]
    raw = pd.concat(frames, ignore_index=True)
    raw.columns = [
        "CANIO", "CMES", "PCIA", "DESCRIP_PCIA",
        "CCOD_RUBRO", "DESCRIP_RUBRO",
        "CCOD_PAIS", "DESCRIP_PAIS",
        "DOLARES_FOB", "PESO_NETO_KG",
    ]
    raw["CCOD_RUBRO"] = raw["CCOD_RUBRO"].astype(str).str.strip()

    crude_mask = raw["CCOD_RUBRO"] == "401"
    gas_mask   = raw["CCOD_RUBRO"].isin(["404A", "404Z"])

    # Values (USD)
    crude_v = raw[crude_mask].groupby("CANIO")["DOLARES_FOB"].sum().reset_index()
    gas_v   = raw[gas_mask  ].groupby("CANIO")["DOLARES_FOB"].sum().reset_index()
    v = crude_v.merge(gas_v, on="CANIO", how="outer", suffixes=("_crude", "_gas"))
    v = v.rename(columns={
        "CANIO": "anio",
        "DOLARES_FOB_crude": "expo_indec_crudo",
        "DOLARES_FOB_gas":   "expo_indec_gas",
    })
    v["unidad"] = "usd"

    # Quantities: crude kg → m3 (÷850 kg/m3) → bbl; gas kg → m3 (÷0.7370 kg/m3)
    crude_q = raw[crude_mask].groupby("CANIO")["PESO_NETO_KG"].sum().reset_index()
    gas_q   = raw[gas_mask  ].groupby("CANIO")["PESO_NETO_KG"].sum().reset_index()
    q = crude_q.merge(gas_q, on="CANIO", how="outer", suffixes=("_crude", "_gas"))
    q = q.rename(columns={"CANIO": "anio"})
    q["expo_indec_crudo"] = m3_to_bbl_q(q["PESO_NETO_KG_crude"] / 850)
    q["expo_indec_gas"]   = q["PESO_NETO_KG_gas"] / 0.7370
    q["unidad"] = "m3"

    return (
        q[["anio", "expo_indec_crudo", "expo_indec_gas", "unidad"]],
        v[["anio", "expo_indec_crudo", "expo_indec_gas", "unidad"]],
    )


def _load_comtrade_crudo() -> pd.DataFrame:
    """UN-Comtrade crude oil SITC exports."""
    path = DATA / "un_comtrade/expo_crudo_sitc.csv"
    if not path.exists():
        return pd.DataFrame(columns=["anio", "unidad_cantidad", "expo_bbl"])
    df = pd.read_csv(path)
    if "Period" in df.columns:
        df = df.rename(columns={"Period": "anio"})
    if "expo_bbl" not in df.columns and "m3" in df.columns:
        df["expo_bbl"] = m3_to_bbl_q(df["m3"])
    df["unidad_cantidad"] = "barriles"
    return df


def _load_comtrade_usd_crudo() -> pd.DataFrame:
    """UN-Comtrade crude oil HS export values (USD), updated by comtrade_download.py."""
    path = DATA / "un_comtrade/expo_crudo_uncomtrade_hs.csv"
    if not path.exists():
        return pd.DataFrame(columns=["anio", "expo_comtrade_crudo_usd"])
    df = pd.read_csv(path)
    df = df.rename(columns={"Period": "anio", "Trade Value (US$)": "expo_comtrade_crudo_usd"})
    return df[["anio", "expo_comtrade_crudo_usd"]].dropna()


def _load_comtrade_usd_gas() -> pd.DataFrame:
    """UN-Comtrade natural gas SITC export values (USD) and quantities (MMBTU), updated by comtrade_download.py."""
    path = DATA / "un_comtrade/expo_gas_sitc.csv"
    if not path.exists():
        return pd.DataFrame(columns=["anio", "expo_comtrade_gas_usd", "expo_comtrade_gas"])
    df = pd.read_csv(path)
    df = df.rename(columns={"Trade Value (US$)": "expo_comtrade_gas_usd"})
    df["expo_comtrade_gas"] = m3_to_mmbtu_q(df["expo_Mm3"] * 1e6)
    return df[["anio", "expo_comtrade_gas_usd", "expo_comtrade_gas"]].dropna(subset=["anio"])


def _load_comex_sesco_new() -> pd.DataFrame:
    """
    Load new-format SESCO comex files (2010+, long format, comma-sep, UTF-8 BOM).
    Both files share an identical 13-column schema.
    """
    files = [
        SESCO / "importaciones-exportaciones.csv",
        SESCO / "importaciones-exportaciones-a-partir-del-2016-.csv",
    ]
    frames = []
    for f in files:
        if f.exists():
            frames.append(pd.read_csv(f, encoding="utf-8-sig"))
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True).drop_duplicates()
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce")
    return df


def _extract_crudo_new(sn: pd.DataFrame) -> pd.DataFrame:
    """Annual crude export qty (barrels) + monto (USD) from new SESCO format."""
    if sn.empty:
        return pd.DataFrame(columns=["anio", "expo_crudo_sesco_new", "expo_crudo_usd_sesco_new"])
    mask = (
        sn["tipodecomercializacion"].str.contains("Exportaci", na=False)
        & sn["producto"].str.contains("Cuenca", na=False)
        & (sn["unidad"] == "(m3)")
    )
    agg = sn[mask].groupby("anio")[["cantidad", "monto"]].sum().reset_index()
    agg["expo_crudo_sesco_new"] = m3_to_bbl_q(agg["cantidad"])
    return agg.rename(columns={"monto": "expo_crudo_usd_sesco_new"})[
        ["anio", "expo_crudo_sesco_new", "expo_crudo_usd_sesco_new"]
    ]


def _extract_gas_new(sn: pd.DataFrame) -> pd.DataFrame:
    """Annual gas export qty (MMBTU) + monto (USD) from new SESCO format."""
    if sn.empty:
        return pd.DataFrame(columns=["anio", "expo_gas_sesco_new", "expo_gas_usd_sesco_new"])
    mask = (
        sn["tipodecomercializacion"].str.contains("Exportaci", na=False)
        & sn["producto"].str.startswith("Gas Natural(", na=False)
        & (sn["unidad"] == "(miles/m3)")
    )
    gas = sn[mask].copy()

    # Detect rows where cantidad was entered in m3 instead of miles/m3:
    # their implied price (monto/cantidad) will be ~1000× below the median.
    # Correct by dividing cantidad by 1000 to restore the proper unit.
    pos = gas["cantidad"] > 0
    implied = gas.loc[pos, "monto"] / gas.loc[pos, "cantidad"]
    threshold = implied.median() / 100
    unit_error = pos & ((gas["monto"] / gas["cantidad"].replace(0, np.nan)) < threshold)
    gas.loc[unit_error, "cantidad"] = gas.loc[unit_error, "cantidad"] / 1000

    agg = gas.groupby("anio")[["cantidad", "monto"]].sum().reset_index()
    # miles/m3 × 1000 → m3 → MMBTU
    agg["expo_gas_sesco_new"] = m3_to_mmbtu_q(agg["cantidad"] * 1000)
    return agg.rename(columns={"monto": "expo_gas_usd_sesco_new"})[
        ["anio", "expo_gas_sesco_new", "expo_gas_usd_sesco_new"]
    ]


# ===== CRUDE =====

def build_expo_crudo(mecon: pd.DataFrame,
                     indec_q: pd.DataFrame, comtrade: pd.DataFrame,
                     sesco_new: pd.DataFrame = None) -> pd.DataFrame:
    """
    Annual crude export quantities (barrels).
    Priority: new SESCO (2010+) → Comtrade (pre-1999).
    MECON, INDEC, and Comtrade kept as reference columns.
    """
    df = mecon[["anio", "expo_bbl_crudo"]].rename(
        columns={"expo_bbl_crudo": "expo_mecon_crudo"}).copy()
    df = df.merge(indec_q[["anio", "expo_indec_crudo"]].dropna(), on="anio", how="outer")
    df = df.merge(comtrade[["anio", "expo_bbl"]].rename(
        columns={"expo_bbl": "expo_comtrade_crudo"}), on="anio", how="outer")

    crudo_new = _extract_crudo_new(sesco_new if sesco_new is not None else pd.DataFrame())
    df = df.merge(crudo_new[["anio", "expo_crudo_sesco_new"]], on="anio", how="outer")

    # Priority: new SESCO (2010+) → comtrade (pre-1999)
    df["expo_crudo"] = np.where(
        df["anio"] < 1999,
        df.get("expo_comtrade_crudo", np.nan),
        df["expo_crudo_sesco_new"],
    )
    df["unidad"] = "barriles"
    return df.sort_values("anio").reset_index(drop=True)


def build_impo_crudo(sesco: pd.DataFrame, mecon: pd.DataFrame) -> pd.DataFrame:
    """Annual crude import quantities (barrels)."""
    crudo_sesco_impo = (
        sesco[
            (sesco["producto"].str.contains("PETROLEO|Cuenca|Crudo importado", na=False))
            & (sesco["variable"] == "importacion")
            & (sesco["unidad"] == "m3")
        ]
        .copy()
    )
    crudo_sesco_impo = crudo_sesco_impo.groupby(["anio", "unidad"])["valor"].sum().reset_index()
    crudo_sesco_impo["valor"] = np.where(
        crudo_sesco_impo["unidad"] == "m3",
        m3_to_bbl_q(crudo_sesco_impo["valor"]),
        crudo_sesco_impo["valor"],
    )
    crudo_sesco_impo["unidad"] = "barriles"
    crudo_sesco_impo["anio"] = pd.to_numeric(crudo_sesco_impo["anio"], errors="coerce")
    crudo_sesco_impo = crudo_sesco_impo.rename(columns={"valor": "impo_sesco_crudo"})

    df = crudo_sesco_impo.merge(
        mecon[["anio", "impo_bbl_crudo"]].rename(columns={"impo_bbl_crudo": "impo_mecon_crudo"}),
        on="anio", how="outer",
    )
    df["impo_crudo"] = df.get("impo_sesco_crudo", np.nan).fillna(df.get("impo_mecon_crudo", np.nan))
    df["unidad"] = "barriles"
    return df.sort_values("anio").reset_index(drop=True)


# ===== GAS =====

def build_expo_gas(mecon: pd.DataFrame,
                   sesco_new: pd.DataFrame = None,
                   comtrade_q: pd.DataFrame = None) -> pd.DataFrame:
    """
    Annual gas export quantities in MMBTU.
    Priority: new SESCO (2010+) → MECON.
    comtrade_q added as reference column (not in priority chain).
    """
    df = mecon[["anio", "expo_mmbtu_gas"]].rename(
        columns={"expo_mmbtu_gas": "expo_mecon_gas"}).copy()

    gas_new = _extract_gas_new(sesco_new if sesco_new is not None else pd.DataFrame())
    df = df.merge(gas_new[["anio", "expo_gas_sesco_new"]], on="anio", how="outer")

    # Priority: new SESCO → MECON
    df["expo_gas"] = df["expo_gas_sesco_new"].fillna(df.get("expo_mecon_gas", np.nan))
    df["unidad"] = "MMBTU"

    if comtrade_q is not None and not comtrade_q.empty:
        df = df.merge(comtrade_q[["anio", "expo_comtrade_gas"]], on="anio", how="outer")

    return df.sort_values("anio").reset_index(drop=True)


def build_impo_gas(sesco: pd.DataFrame, mecon: pd.DataFrame) -> pd.DataFrame:
    """Annual gas import quantities in MMBTU."""
    gas_sesco_impo = (
        sesco[
            sesco["producto"].str.contains("GAS|gas", na=False)
            & (sesco["variable"] == "importacion")
            & (sesco["unidad"] != "Ton")
        ]
        .copy()
    )
    gas_sesco_impo = gas_sesco_impo.groupby(["anio", "unidad"])["valor"].sum().reset_index()
    gas_sesco_impo["valor"] = np.where(
        gas_sesco_impo["unidad"] == "m3",
        m3_to_mmbtu_q(gas_sesco_impo["valor"]),
        gas_sesco_impo["valor"],
    )
    gas_sesco_impo["unidad"] = "MMBTU"
    gas_sesco_impo["anio"] = pd.to_numeric(gas_sesco_impo["anio"], errors="coerce")
    gas_sesco_impo = gas_sesco_impo.rename(columns={"valor": "impo_sesco_gas"})

    df = gas_sesco_impo.merge(
        mecon[["anio", "impo_mmbtu_gas"]].rename(columns={"impo_mmbtu_gas": "impo_mecon_gas"}),
        on="anio", how="outer",
    )
    df["impo_gas"] = df.get("impo_sesco_gas", np.nan).fillna(df.get("impo_mecon_gas", np.nan))
    df["unidad"] = "MMBTU"
    return df.sort_values("anio").reset_index(drop=True)


def build_expo_usd_crudo(indec_v: pd.DataFrame,
                         sesco_new: pd.DataFrame = None,
                         comtrade_usd: pd.DataFrame = None) -> pd.DataFrame:
    """
    Annual crude export value (USD).
    Priority: new SESCO → INDEC.
    comtrade_usd added as reference column (not in priority chain).
    """
    df = indec_v[["anio", "expo_indec_crudo"]].dropna().rename(
        columns={"expo_indec_crudo": "expo_crudo_indec_usd"}
    ).copy()

    crudo_new = _extract_crudo_new(sesco_new if sesco_new is not None else pd.DataFrame())
    df = df.merge(crudo_new[["anio", "expo_crudo_usd_sesco_new"]], on="anio", how="outer")

    # Priority: new SESCO → INDEC
    df["expo_crudo_usd"] = df["expo_crudo_usd_sesco_new"].fillna(
        df.get("expo_crudo_indec_usd", np.nan)
    )
    df["unidad"] = "USD"

    if comtrade_usd is not None and not comtrade_usd.empty:
        df = df.merge(comtrade_usd[["anio", "expo_comtrade_crudo_usd"]], on="anio", how="outer")

    return df.sort_values("anio").reset_index(drop=True)


def build_expo_usd_gas(indec_v: pd.DataFrame,
                       sesco_new: pd.DataFrame = None,
                       comtrade_usd: pd.DataFrame = None) -> pd.DataFrame:
    """
    Annual gas export value (USD).
    Priority: new SESCO → INDEC.
    comtrade_usd added as reference column (not in priority chain).
    """
    df = indec_v[["anio", "expo_indec_gas"]].dropna().rename(
        columns={"expo_indec_gas": "expo_gas_indec_usd"}
    ).copy()

    gas_new = _extract_gas_new(sesco_new if sesco_new is not None else pd.DataFrame())
    df = df.merge(gas_new[["anio", "expo_gas_usd_sesco_new"]], on="anio", how="outer")

    # Priority: new SESCO → INDEC
    df["expo_gas_usd"] = df["expo_gas_usd_sesco_new"].fillna(
        df.get("expo_gas_indec_usd", np.nan)
    )
    df["unidad"] = "USD"

    if comtrade_usd is not None and not comtrade_usd.empty:
        df = df.merge(comtrade_usd[["anio", "expo_comtrade_gas_usd"]], on="anio", how="outer")

    return df.sort_values("anio").reset_index(drop=True)


def run() -> dict:
    sesco = _load_comex_sesco()
    mecon = _load_comex_mecon()
    indec_q, indec_v = _load_indec()
    comtrade = _load_comtrade_crudo()
    sesco_new = _load_comex_sesco_new()
    comtrade_usd_crudo = _load_comtrade_usd_crudo()
    comtrade_usd_gas   = _load_comtrade_usd_gas()

    expo_crudo     = build_expo_crudo(mecon, indec_q, comtrade, sesco_new)
    impo_crudo     = build_impo_crudo(sesco, mecon)
    expo_gas       = build_expo_gas(mecon, sesco_new,
                                    comtrade_q=comtrade_usd_gas[["anio", "expo_comtrade_gas"]])
    impo_gas       = build_impo_gas(sesco, mecon)
    expo_usd_crudo = build_expo_usd_crudo(indec_v, sesco_new, comtrade_usd=comtrade_usd_crudo)
    expo_usd_gas   = build_expo_usd_gas(indec_v, sesco_new,   comtrade_usd=comtrade_usd_gas)

    return dict(
        expo_crudo=expo_crudo,
        impo_crudo=impo_crudo,
        expo_gas=expo_gas,
        impo_gas=impo_gas,
        indec_expo_valor=indec_v,
        expo_usd_crudo=expo_usd_crudo,
        expo_usd_gas=expo_usd_gas,
    )


if __name__ == "__main__":
    result = run()
    print("comex OK")
    for k, v in result.items():
        print(f"  {k}: {v.shape}")
