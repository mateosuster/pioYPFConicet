"""
IPC, TCP, exchange rates, currency converters.
Replaces Section 1 (IPC y TCP) of preprocesamiento.Rmd (lines ~52-220).
"""

from pathlib import Path
import pandas as pd
import numpy as np

from utils.indices import generar_indice

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"
UPDATE = ROOT / "update"

# ---- Constants ----
YEAR_LAST = 2025
YEAR_SEC_ENERGIA_UPPER = 2015
YEAR_EMPLEO_CORTE = 2025


def load_conversor_pesos() -> pd.Series:
    """
    Peso currency conversion factors (m$n, $ley, $arg, austral → ARS).
    Returns the single 'pesos' row as a Series.
    """
    df = pd.read_excel(DATA / "conversores/conversor_peso.xlsx")
    df.columns = df.columns.str.strip()
    df = df.apply(pd.to_numeric, errors="coerce")
    df["moneda"] = ["moneda nacional", "pesos ley", "peso argentino", "austral", "pesos"]
    row = df[df["moneda"] == "pesos"].iloc[0]
    return row


def load_tcp() -> pd.DataFrame:
    """
    Annual commercial (TCC) and parity (TCP) exchange rates, 1950–YEAR_LAST.
    Columns: anio, tcc, tcp, sobrevaluacion
    """
    tcp_hist = pd.read_excel(DATA / "tcp/tcc_tcp_historico.xlsx")
    tcp_hist = tcp_hist.rename(columns={
        "TCC exportaciones": "tcc",
        "Sobrevaluación (TCP/ TCC) 1952-1972=1": "sobrevaluacion",
        "TCP": "tcp",
    })
    # Normalize anio: Excel may read year cells as datetime objects
    tcp_hist["anio"] = tcp_hist["anio"].apply(
        lambda x: x.year if hasattr(x, "year") else int(x)
    )
    tcp_hist = tcp_hist[["anio", "tcc", "tcp", "sobrevaluacion"]]

    tcp_new = pd.read_excel(
        DATA / "tcp/tcp_anual.xlsx",
        dtype={"fecha": int, "TCC": float, "TCP": float},
    ).rename(columns={"fecha": "anio", "TCC": "tcc", "TCP": "tcp"})
    tcp_new["sobrevaluacion"] = tcp_new["tcp"] / tcp_new["tcc"]

    pre91 = tcp_hist[tcp_hist["anio"] < 1991]
    tcp_anual = pd.concat([pre91, tcp_new], ignore_index=True)
    return tcp_anual


def load_tcc_dic63(tcp_anual: pd.DataFrame, conversor_pesos: pd.Series) -> pd.DataFrame:
    """
    TCC in original currency units (pre-decimal reform years).
    Columns: anio, moneda, tcc, tcc_moneda
    """
    tcc_dic = pd.read_excel(DATA / "tcp/tcc_dic_63.xlsx")
    tcc_dic = tcc_dic.drop(columns=["usd_dic"], errors="ignore")
    tcc_dic = tcc_dic.merge(tcp_anual[["anio", "tcc"]], on="anio", how="left")

    tcc_dic.loc[tcc_dic["anio"] == 1984, "moneda"] = "$arg"

    conditions = [
        tcc_dic["moneda"] == "m$n",
        tcc_dic["moneda"] == "$ley",
        tcc_dic["moneda"] == "$arg",
        tcc_dic["moneda"] == "A",
    ]
    choices = [
        tcc_dic["tcc"] * conversor_pesos["m$n"],
        tcc_dic["tcc"] * conversor_pesos["$Ley"],
        tcc_dic["tcc"] * conversor_pesos["$a"],
        tcc_dic["tcc"] * conversor_pesos["A"],
    ]
    tcc_dic["tcc_moneda"] = np.select(conditions, choices, default=tcc_dic["tcc"])
    return tcc_dic


def load_ipc() -> pd.DataFrame:
    """
    Annual CPI (base 2003-07 = 1), extended through YEAR_LAST.
    Columns: anio, fecha, ipc_03, ipc_70, ipc_18
    """
    ipc_raw = pd.read_excel(DATA / "indices/ipc_mensual_1963_2018.xlsx")
    ipc_raw["anio"] = ipc_raw["anio"].ffill()
    ipc_raw = ipc_raw.rename(columns={"Base 7/2003 = 1": "ipc_0703"})
    ipc_hist = ipc_raw.groupby("anio")["ipc_0703"].mean().reset_index()
    ipc_hist.columns = ["anio", "ipc_03"]

    # Extension 2019–YEAR_LAST from update file (ARG IPC 2004=1, col H, sheet Propia)
    ipc_tcp = pd.read_excel(
        UPDATE / "TCP_me (2).xlsx",
        sheet_name="Propia",
        header=None,
        skiprows=4,
        nrows=35,
        usecols=[0, 7],
    )
    ipc_tcp.columns = ["anio", "ipc_tcp"]
    ipc_tcp["anio"] = ipc_tcp["anio"].astype(int)

    ipc_03_2018 = ipc_hist.loc[ipc_hist["anio"] == 2018, "ipc_03"].iloc[0]
    ipc_tcp_2018 = ipc_tcp.loc[ipc_tcp["anio"] == 2018, "ipc_tcp"].iloc[0]

    ext = ipc_tcp[(ipc_tcp["anio"] > 2018) & (ipc_tcp["anio"] <= YEAR_LAST)].copy()
    ext["ipc_03"] = ipc_03_2018 * (ext["ipc_tcp"] / ipc_tcp_2018)
    ext = ext[["anio", "ipc_03"]]

    ipc = pd.concat([ipc_hist, ext], ignore_index=True)
    # ipc["fecha"] = pd.to_datetime(ipc["anio"].astype(str) + "-01-01")
    ipc["fecha"] = pd.to_datetime(ipc["anio"].astype(int).astype(str) + "-01-01")
    ipc["ipc_70"] = generar_indice(ipc["ipc_03"], ipc["fecha"], pd.Timestamp("1970-01-01"))
    ipc["ipc_18"] = generar_indice(ipc["ipc_03"], ipc["fecha"], pd.Timestamp("2018-01-01"))
    ipc["ipc_24"] = generar_indice(ipc["ipc_03"], ipc["fecha"], pd.Timestamp("2024-01-01"))
    return ipc[["anio", "fecha", "ipc_03", "ipc_70", "ipc_18", "ipc_24"]]


def load_ipim() -> pd.DataFrame:
    """
    IPIM/IPIB/IPP (base 1993=100). Historical series 19xx years only.
    Columns: anio, ipim_nivel_gral, ipim_nivel_gral_94
    """
    df = pd.read_excel(DATA / "indec/sipm-serie56-95.xls", skiprows=6, header=0)
    col_map = {
        df.columns[0]: "anio",
        df.columns[1]: "ipim_nivel_gral",
        df.columns[2]: "ipim_nivel_nac",
        df.columns[3]: "ipim_nivel_impo",
        df.columns[4]: "ipib_nivel_gral",
        df.columns[5]: "ipib_nivel_nac",
        df.columns[6]: "ipib_nivel_impo",
        df.columns[7]: "ipp_nivel_gral",
    }
    df = df.rename(columns=col_map)
    df = df[df["anio"].astype(str).str.startswith("19")].copy()
    df["anio"] = df["anio"].astype(float)
    from utils.indices import generar_indice as gi
    df["ipim_nivel_gral_94"] = gi(df["ipim_nivel_gral"], df["anio"], 1994)
    return df[["anio", "ipim_nivel_gral", "ipim_nivel_gral_94"]]


def load_ipc_us() -> pd.DataFrame:
    """
    US CPI annual average, reindexed to 2020 = 1.
    Columns: anio, ipc_us_20
    """
    df = pd.read_csv(DATA / "bls/CPIAUCSL.csv")
    df["anio"] = pd.to_datetime(df["observation_date"]).dt.year
    df = df.groupby("anio")["CPIAUCSL"].mean().reset_index()
    df.columns = ["anio", "ipc_us_20"]
    df["ipc_us_20"] = generar_indice(df["ipc_us_20"], df["anio"], 2020)
    return df


def load_ganancia_pbi() -> pd.DataFrame:
    """
    GDP and profit in current pesos, 1960–2021.
    Columns: anio, pbi, ganancia, unidad
    """
    hist = pd.read_excel(DATA / "ccnn/ganancia y pbi.xlsx")
    ext = pd.read_excel(
        UPDATE / "TG General. 1993 - 2021. 18102022 (5).xlsx",
        sheet_name="TG",
        header=None,
        skiprows=7,
        nrows=29,
    )[[0, 1, 5]]
    ext.columns = ["anio", "pbi", "ganancia"]
    ext = ext.dropna(subset=["anio"])
    ext["anio"] = ext["anio"].astype(int)
    ext = ext[ext["anio"] > hist["anio"].max()]
    df = pd.concat([hist, ext], ignore_index=True)
    df["unidad"] = "Millones de pesos corrientes"
    return df[["anio", "unidad", "pbi", "ganancia"]]


# ---- Assembled result ----

def run() -> dict:
    """
    Run the full indices/prices preprocessing.
    Returns a dict of named DataFrames/Series for downstream modules.
    """
    conversor_pesos = load_conversor_pesos()
    tcp_anual = load_tcp()
    tcc_dic = load_tcc_dic63(tcp_anual, conversor_pesos)
    ipc = load_ipc()
    ipim = load_ipim()
    ipc_us = load_ipc_us()
    ganancia_pbi = load_ganancia_pbi()

    # Convenience series keyed by anio (used by downstream modules)
    ipc_18 = ipc.set_index("anio")["ipc_18"]
    ipc_24 = ipc.set_index("anio")["ipc_24"]
    ipc_us_20 = ipc_us.set_index("anio")["ipc_us_20"]

    return dict(
        conversor_pesos=conversor_pesos,
        tcp_anual=tcp_anual,
        tcc_dic=tcc_dic,
        ipc=ipc,
        ipc_18=ipc_18,
        ipc_24=ipc_24,
        ipim=ipim,
        ipc_us=ipc_us,
        ipc_us_20=ipc_us_20,
        ganancia_pbi=ganancia_pbi,
    )


if __name__ == "__main__":
    result = run()
    print("indices_precios OK")
    for k, v in result.items():
        if hasattr(v, "shape"):
            print(f"  {k}: {v.shape}")
        else:
            print(f"  {k}: Series({len(v)})")
