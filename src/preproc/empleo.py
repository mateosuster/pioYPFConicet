"""
Employment, wages, and wage bill for the hydrocarbon sector.
Replaces Section 8 (Empleo, remuneraciones y masa salarial) of preprocesamiento.Rmd
(lines ~2379-2600).
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"

YEAR_EMPLEO_CORTE = 2025  # last year in existing annual employment data


def _load_mecon_empleo() -> pd.DataFrame:
    """Employment from MECON national accounts (Empleo registrado sheet)."""
    df = pd.read_excel(
        DATA / "mecon/base-mineria-e-hidrocarburos cuentas nacionales.xls",
        sheet_name="Empleo registrado",
        skiprows=5,
    )
    df = df.rename(columns={
        "Año": "anio",
        "Período": "periodo",
        df.columns[6]: "empleo_extraccion_hidrocarburos",
        df.columns[7]: "empleo_servicios_hidrocarburos",
    })
    df = df[df["periodo"].isna() & df["anio"].notna()]
    df["empleo_extraccion_hidrocarburos"] = pd.to_numeric(
        df["empleo_extraccion_hidrocarburos"], errors="coerce"
    )
    df["empleo_servicios_hidrocarburos"] = pd.to_numeric(
        df["empleo_servicios_hidrocarburos"], errors="coerce"
    )
    df["unidad_empleo"] = "Puestos de trabajo"
    return df[["anio", "empleo_extraccion_hidrocarburos",
               "empleo_servicios_hidrocarburos", "unidad_empleo"]]


def _load_mecon_salarios() -> pd.DataFrame:
    """Wages from MECON national accounts (Remuneraciones sheet)."""
    col_types = {"Año": "str", "Período": "str"}
    df = pd.read_excel(
        DATA / "mecon/base-mineria-e-hidrocarburos cuentas nacionales.xls",
        sheet_name="Remuneraciones",
        skiprows=5,
    )
    df = df.rename(columns={
        "Año": "anio",
        "Período": "periodo",
        df.columns[6]: "salario_extraccion_hidrocarburos",
        df.columns[7]: "salario_servicios_hidrocarburos",
    })
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df = df[df["anio"].notna() & (df["anio"] < 2014)]
    df["salario_extraccion_hidrocarburos"] = pd.to_numeric(
        df["salario_extraccion_hidrocarburos"], errors="coerce"
    )
    df["salario_servicios_hidrocarburos"] = pd.to_numeric(
        df["salario_servicios_hidrocarburos"], errors="coerce"
    )
    df["unidad_salario"] = "Pesos corrientes"
    return df[["anio", "salario_extraccion_hidrocarburos",
               "salario_servicios_hidrocarburos", "unidad_salario"]]


def _load_min_trabajo_empleo_anual() -> pd.DataFrame:
    """Annual employment from Min. Trabajo (hoja C 5)."""
    df = pd.read_excel(
        DATA / "min_trabajo/nacional_serie_empleo_anual_1.xlsx",
        sheet_name="C 5",
        skiprows=4,
        dtype=str,
    )
    code_col, desc_col = df.columns[0], df.columns[1]
    df = df.rename(columns={desc_col: "rama_actividad"}).drop(columns=[code_col])
    df = df.melt(id_vars=["rama_actividad"], var_name="anio", value_name="valor")
    df = df[df["rama_actividad"].str.contains("petróleo", case=False, na=False)]
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["unidad_empleo"] = "Puestos de trabajo"
    df["rama_actividad"] = np.select(
        [df["rama_actividad"].str.contains("servicios", case=False),
         df["rama_actividad"].str.contains("Extracción", case=False)],
        ["empleo_servicios_extraccion", "empleo_extraccion_petroleo_gas"],
        default=None,
    )
    df = df.dropna(subset=["rama_actividad"])
    return df.pivot_table(index="anio", columns="rama_actividad", values="valor").reset_index()


def _load_min_trabajo_empleo_nueva() -> pd.DataFrame:
    """Quarterly employment extension 2020–YEAR_LAST from Min. Trabajo."""
    df = pd.read_excel(
        DATA / "min_trabajo/nacional_serie_empleo_trimestral_6.xlsx",
        sheet_name="C5",
        skiprows=2,
    )
    df = df.rename(columns={df.columns[0]: "rama_actividad"})
    df = df[df["rama_actividad"].str.contains("petróleo", case=False, na=False)]
    df = df.melt(id_vars=["rama_actividad"], var_name="trimestre", value_name="valor")
    df = df[df["trimestre"].astype(str).str.match(r"^[1-4]º Trim\s+\d{4}$")]
    df["anio"] = df["trimestre"].str.extract(r"(\d{4})")[0]
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df[df["anio"].notna() & (df["anio"].astype(int) > YEAR_EMPLEO_CORTE)]
    df["rama_actividad"] = np.select(
        [df["rama_actividad"].str.contains("servicios", case=False),
         df["rama_actividad"].str.contains("Extracción", case=False)],
        ["empleo_servicios_extraccion", "empleo_extraccion_petroleo_gas"],
        default=None,
    )
    df = df.dropna(subset=["rama_actividad"])
    return (
        df.groupby(["rama_actividad", "anio"])["valor"].mean().reset_index()
        .pivot_table(index="anio", columns="rama_actividad", values="valor")
        .reset_index()
    )


def _load_min_trabajo_remuneraciones_anual() -> pd.DataFrame:
    """Annual wages from Min. Trabajo (hoja C 5)."""
    df = pd.read_excel(
        DATA / "min_trabajo/nacional_serie_remuneraciones_anual_1.xlsx",
        sheet_name="C 5",
        skiprows=4,
    )
    code_col, desc_col = df.columns[0], df.columns[1]
    df = df.rename(columns={desc_col: "rama_actividad"}).drop(columns=[code_col])
    df = df.melt(id_vars=["rama_actividad"], var_name="anio", value_name="valor")
    df = df[df["rama_actividad"].str.contains("petróleo", case=False, na=False)]
    df["unidad_salario"] = "Pesos corrientes"
    df["rama_actividad"] = np.select(
        [df["rama_actividad"].str.contains("servicios", case=False),
         df["rama_actividad"].str.contains("Extracción", case=False)],
        ["remuneracion_servicios_extraccion", "remuneracion_extraccion_petroleo_gas"],
        default=None,
    )
    df = df.dropna(subset=["rama_actividad"])
    return df.pivot_table(index="anio", columns="rama_actividad", values="valor").reset_index()


def _load_min_trabajo_remuneraciones_nueva() -> pd.DataFrame:
    """Monthly wages extension 2020–YEAR_LAST from Min. Trabajo."""
    df = pd.read_excel(
        DATA / "min_trabajo/nacional_serie_remuneraciones_mensual_7.xlsx",
        sheet_name="C 8",
        skiprows=4,
    )
    df = df.rename(columns={df.columns[0]: "rama_actividad"})
    df = df.drop(columns=[df.columns[1], df.columns[2]], errors="ignore")
    df = df[df["rama_actividad"].str.contains("petróleo", case=False, na=False)]
    df = df.melt(id_vars=["rama_actividad"], var_name="fecha_str", value_name="valor")
    df["anio"] = pd.to_datetime(df["fecha_str"], errors="coerce").dt.year
    df["anio"] = df["anio"].fillna(
        df["fecha_str"].str.extract(r"(\d{4})")[0].astype(float)
    )
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df[df["anio"].notna() & (df["anio"] > YEAR_EMPLEO_CORTE) & df["valor"].notna()]
    df["rama_actividad"] = np.select(
        [df["rama_actividad"].str.contains("servicios", case=False),
         df["rama_actividad"].str.contains("Extracción", case=False)],
        ["remuneracion_servicios_extraccion", "remuneracion_extraccion_petroleo_gas"],
        default=None,
    )
    df = df.dropna(subset=["rama_actividad"])
    df["unidad_salario"] = "Pesos corrientes"
    return (
        df.groupby(["rama_actividad", "anio"])["valor"].mean().reset_index()
        .pivot_table(index="anio", columns="rama_actividad", values="valor")
        .reset_index()
    )


def build_masa_salarial_ccnn(conversor_pesos: pd.Series) -> pd.DataFrame:
    """Wage bill from MECON national accounts."""
    # CEPAL
    cepal = pd.read_excel(DATA / "cepal/cepal_1991.xlsx")
    cepal["valor"] = cepal["valor"] / conversor_pesos["A"] / 1e3
    cepal["unidad"] = "Millones de pesos corrientes"
    ms_cepal = cepal[cepal["variable"] == "remuneracion_al_trabajo"].rename(columns={"valor": "ms_cepal"})

    empleo = _load_mecon_empleo()
    salarios = _load_mecon_salarios()
    df = empleo.merge(salarios, on="anio", how="outer")
    df["unidad_masa_salarial"] = "Millones de pesos corrientes"
    df["masa_salarial_extraccion"] = (
        df["salario_extraccion_hidrocarburos"] * df["empleo_extraccion_hidrocarburos"] * 13
    ) / 1e6
    df["masa_salarial_servicios"] = (
        df["salario_servicios_hidrocarburos"] * df["empleo_servicios_hidrocarburos"] * 13
    ) / 1e6
    df["masa_salarial_total"] = df["masa_salarial_extraccion"] + df["masa_salarial_servicios"]
    return df


def build_masa_salarial_oede() -> pd.DataFrame:
    """Wage bill from Min. Trabajo (OEDE) data."""
    empleo_anual = _load_min_trabajo_empleo_anual()
    empleo_nueva = _load_min_trabajo_empleo_nueva()
    empleo_all = pd.concat([empleo_anual, empleo_nueva], ignore_index=True)

    rem_anual = _load_min_trabajo_remuneraciones_anual()
    rem_nueva = _load_min_trabajo_remuneraciones_nueva()
    rem_all = pd.concat([rem_anual, rem_nueva], ignore_index=True)

    df = empleo_all.merge(rem_all, on="anio", how="outer")
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["unidad_masa_salarial"] = "Millones de pesos corrientes"
    df["masa_salarial_extraccion"] = (
        df.get("remuneracion_extraccion_petroleo_gas", 0)
        * df.get("empleo_extraccion_petroleo_gas", 0)
        * 13
    ) / 1e6
    df["masa_salarial_servicios"] = (
        df.get("remuneracion_servicios_extraccion", 0)
        * df.get("empleo_servicios_extraccion", 0)
        * 13
    ) / 1e6
    df["masa_salarial_total"] = df["masa_salarial_servicios"] + df["masa_salarial_extraccion"]
    return df


def build_masa_salarial_hidrocarburos(
    ccnn: pd.DataFrame, oede: pd.DataFrame
) -> pd.DataFrame:
    """Combined wage bill from CCNN + OEDE."""
    ccnn_sel = ccnn[["anio", "unidad_masa_salarial",
                      "masa_salarial_extraccion", "masa_salarial_total"]].rename(
        columns={
            "unidad_masa_salarial": "unidad",
            "masa_salarial_extraccion": "masa_salarial_extraccion_ccnn",
            "masa_salarial_total": "masa_salarial_total_ccnn",
        }
    )
    oede_sel = oede[["anio", "unidad_masa_salarial",
                      "masa_salarial_extraccion", "masa_salarial_total"]].rename(
        columns={
            "unidad_masa_salarial": "unidad",
            "masa_salarial_extraccion": "masa_salarial_extraccion_oede",
            "masa_salarial_total": "masa_salarial_total_oede",
        }
    )
    return ccnn_sel.merge(oede_sel, on=["anio", "unidad"], how="outer").sort_values("anio")


def run(conversor_pesos: pd.Series) -> dict:
    ccnn = build_masa_salarial_ccnn(conversor_pesos)
    oede = build_masa_salarial_oede()
    ms = build_masa_salarial_hidrocarburos(ccnn, oede)

    return dict(
        masa_salarial_ccnn=ccnn,
        masa_salarial_oede=oede,
        masa_salarial_hidrocarburos=ms,
    )


if __name__ == "__main__":
    from preproc.indices_precios import run as run_indices
    aux = run_indices()
    result = run(aux["conversor_pesos"])
    print("empleo OK")
    for k, v in result.items():
        print(f"  {k}: {v.shape}")
