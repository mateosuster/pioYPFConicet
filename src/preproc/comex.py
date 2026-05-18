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
    """INDEC export quantities and values."""
    q = pd.read_csv(DATA / "indec/cantidades_expo_hidro_indec.csv",
                    usecols=lambda c: c not in ["...1", "Unnamed: 0"])
    q = q.rename(columns={"petroleo_crudo_expo": "expo_indec_crudo",
                           "gas_natural_expo": "expo_indec_gas"})
    v = pd.read_csv(DATA / "indec/expo_hidro_valor.csv",
                    usecols=lambda c: c not in ["...1", "Unnamed: 0"])
    v = v.rename(columns={"petroleo_crudo_expo": "expo_indec_crudo",
                           "gas_natural_expo": "expo_indec_gas"})
    return q, v


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


# ===== CRUDE =====

def build_expo_crudo(sesco: pd.DataFrame, mecon: pd.DataFrame,
                     indec_q: pd.DataFrame, comtrade: pd.DataFrame) -> pd.DataFrame:
    """
    Annual crude export quantities (barrels).
    Primary: Comtrade pre-1999, SESCO post-1999.
    """
    crudo_sesco = (
        sesco[
            (sesco["producto"].str.contains("PETROLEO|Cuenca|Crudo importado", na=False))
            & (sesco["variable"] == "exportacion")
            & (sesco["unidad"] == "m3")
        ]
        .copy()
    )
    crudo_sesco = crudo_sesco.groupby(["anio", "unidad"])["valor"].sum().reset_index()
    crudo_sesco["valor"] = np.where(
        crudo_sesco["unidad"] == "m3",
        m3_to_bbl_q(crudo_sesco["valor"]),
        crudo_sesco["valor"],
    )
    crudo_sesco["unidad"] = "barriles"
    crudo_sesco = crudo_sesco[crudo_sesco["valor"] > 0].rename(columns={"valor": "expo_sesco_crudo"})
    crudo_sesco["anio"] = pd.to_numeric(crudo_sesco["anio"], errors="coerce")

    df = crudo_sesco.merge(mecon[["anio", "expo_bbl_crudo"]].rename(
        columns={"expo_bbl_crudo": "expo_mecon_crudo"}), on="anio", how="outer")
    df = df.merge(indec_q[["anio", "expo_indec_crudo"]].dropna(), on="anio", how="outer")
    df = df.merge(comtrade[["anio", "expo_bbl"]].rename(
        columns={"expo_bbl": "expo_comtrade_crudo"}), on="anio", how="outer")

    df["expo_crudo"] = np.where(df["anio"] < 1999,
                                df.get("expo_comtrade_crudo", np.nan),
                                df.get("expo_sesco_crudo", np.nan))
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

def build_expo_gas(sesco: pd.DataFrame, mecon: pd.DataFrame) -> pd.DataFrame:
    """Annual gas export quantities in MMBTU."""
    gas_sesco = (
        sesco[
            sesco["producto"].str.contains("GAS|gas", na=False)
            & (sesco["variable"] == "exportacion")
            & (sesco["unidad"] == "m3")
        ]
        .copy()
    )
    gas_sesco = gas_sesco.groupby(["anio", "unidad"])["valor"].sum().reset_index()
    gas_sesco["valor"] = np.where(
        gas_sesco["unidad"] == "m3",
        m3_to_mmbtu_q(gas_sesco["valor"]),
        gas_sesco["valor"],
    )
    gas_sesco["unidad"] = "MMBTU"
    gas_sesco["anio"] = pd.to_numeric(gas_sesco["anio"], errors="coerce")
    gas_sesco = gas_sesco.rename(columns={"valor": "expo_sesco_gas"})

    df = gas_sesco.merge(
        mecon[["anio", "expo_mmbtu_gas"]].rename(columns={"expo_mmbtu_gas": "expo_mecon_gas"}),
        on="anio", how="outer",
    )
    df["expo_gas"] = df.get("expo_sesco_gas", np.nan).fillna(df.get("expo_mecon_gas", np.nan))
    df["unidad"] = "MMBTU"
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


def build_expo_usd_crudo(sesco: pd.DataFrame, indec_v: pd.DataFrame) -> pd.DataFrame:
    """
    Annual crude export value (USD).
    Primary: SESCO USD; fallback INDEC.
    Used to cross-check overvaluation rent calculation.
    """
    crudo_sesco_usd = (
        sesco[
            (sesco["producto"].str.contains("PETROLEO|Cuenca|Crudo importado", na=False))
            & (sesco["variable"] == "exportacion")
            & (sesco["unidad"] == "USD")
        ]
        .copy()
    )
    crudo_sesco_usd = crudo_sesco_usd.groupby("anio")["valor"].sum().reset_index()
    crudo_sesco_usd["anio"] = pd.to_numeric(crudo_sesco_usd["anio"], errors="coerce")
    crudo_sesco_usd = crudo_sesco_usd.rename(columns={"valor": "expo_crudo_sesco_usd"})

    df = crudo_sesco_usd.merge(
        indec_v[["anio", "expo_indec_crudo"]].dropna().rename(
            columns={"expo_indec_crudo": "expo_crudo_indec_usd"}
        ),
        on="anio", how="outer",
    )
    df["expo_crudo_usd"] = df["expo_crudo_sesco_usd"].fillna(df["expo_crudo_indec_usd"])
    df["unidad"] = "USD"
    return df.sort_values("anio").reset_index(drop=True)


def run() -> dict:
    sesco = _load_comex_sesco()
    mecon = _load_comex_mecon()
    indec_q, indec_v = _load_indec()
    comtrade = _load_comtrade_crudo()

    expo_crudo = build_expo_crudo(sesco, mecon, indec_q, comtrade)
    impo_crudo = build_impo_crudo(sesco, mecon)
    expo_gas = build_expo_gas(sesco, mecon)
    impo_gas = build_impo_gas(sesco, mecon)
    expo_usd_crudo = build_expo_usd_crudo(sesco, indec_v)

    return dict(
        expo_crudo=expo_crudo,
        impo_crudo=impo_crudo,
        expo_gas=expo_gas,
        impo_gas=impo_gas,
        indec_expo_valor=indec_v,
        expo_usd_crudo=expo_usd_crudo,
    )


if __name__ == "__main__":
    result = run()
    print("comex OK")
    for k, v in result.items():
        print(f"  {k}: {v.shape}")
