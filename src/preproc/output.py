"""
Final assembly and export of all preprocessed variables.
Replaces Sections 13-14 of preprocesamiento.Rmd (lines ~4021-4600).
Outputs:
  results/argentina/variables.csv
  results/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx
  results/argentina/base_csv/stock_*.csv
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parents[2]
RESULTS = ROOT / "results" / "argentina"
BASE_CSV = RESULTS / "base_csv"


def _to_long(df: pd.DataFrame, id_cols: list, var_name: str = "variable",
             value_name: str = "valor", fuente: str = "") -> pd.DataFrame:
    """Melt wide DataFrame to long form with fuente column."""
    val_cols = [c for c in df.columns if c not in id_cols]
    long = df.melt(id_vars=id_cols, value_vars=val_cols,
                   var_name=var_name, value_name=value_name)
    if fuente:
        long["fuente"] = fuente
    return long.dropna(subset=[value_name])


def assemble_variables(
    ipc: pd.DataFrame,
    tcp_anual: pd.DataFrame,
    prod_crudo: pd.DataFrame,
    prod_gas_mmbtu: pd.DataFrame,
    prod_total: pd.DataFrame,
    expo_crudo: pd.DataFrame,
    expo_gas: pd.DataFrame,
    impo_crudo: pd.DataFrame,
    impo_gas: pd.DataFrame,
    precio_crudo_mi: pd.DataFrame,
    precio_gas_mi_mmbtu: pd.DataFrame,
    regalias: pd.DataFrame,
    retenciones: pd.DataFrame,
    subsidios: pd.DataFrame,
    masa_salarial: pd.DataFrame,
    stock_rama: pd.DataFrame,
    renta_crudo_dif: pd.DataFrame,
    renta_gas_dif: pd.DataFrame,
    ganancia_pbi: pd.DataFrame,
    ipc_us: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assemble all preprocessed data into the canonical long-form variables table.
    Schema: anio, variable, codigo_variable, unidad, valor, fuente
    """
    frames = []

    # IPC
    ipc_long = ipc[["anio", "ipc_03", "ipc_18", "ipc_70"]].melt(
        id_vars="anio", var_name="variable", value_name="valor"
    )
    ipc_long["unidad"] = "index"
    ipc_long["fuente"] = "INDEC/BCRA"
    frames.append(ipc_long)

    # IPC US
    ipc_us_long = ipc_us.rename(columns={"ipc_us_20": "valor"})
    ipc_us_long["variable"] = "ipc_us_20"
    ipc_us_long["unidad"] = "index (2020=1)"
    ipc_us_long["fuente"] = "BLS"
    frames.append(ipc_us_long[["anio", "variable", "unidad", "valor", "fuente"]])

    # TCP / TCC
    tc_long = tcp_anual[["anio", "tcc", "tcp", "sobrevaluacion"]].melt(
        id_vars="anio", var_name="variable", value_name="valor"
    )
    tc_long["unidad"] = "ARS/USD"
    tc_long["fuente"] = "BCRA/MECON"
    frames.append(tc_long)

    # Production crude
    pc = prod_crudo[["anio", "unidad", "prod_crudo"]].copy()
    pc["variable"] = "Q_crudo_prod"
    pc["fuente"] = "SecEnergia/SESCO/Anuario"
    pc = pc.rename(columns={"prod_crudo": "valor"})
    frames.append(pc[["anio", "variable", "unidad", "valor", "fuente"]])

    # Production gas (MMBTU)
    pg = prod_gas_mmbtu[["anio", "unidad", "prod_gas"]].copy()
    pg["variable"] = "Q_gas_prod"
    pg["fuente"] = "SecEnergia/SESCO/Anuario"
    pg = pg.rename(columns={"prod_gas": "valor"})
    frames.append(pg[["anio", "variable", "unidad", "valor", "fuente"]])

    # Trade
    for df, var, fuente in [
        (expo_crudo[["anio", "unidad", "expo_crudo"]], "Q_crudo_expo", "SESCO/Comtrade"),
        (impo_crudo[["anio", "unidad", "impo_crudo"]], "Q_crudo_impo", "SESCO/MECON"),
        (expo_gas[["anio", "unidad", "expo_gas"]], "Q_gas_expo", "SESCO/MECON"),
        (impo_gas[["anio", "unidad", "impo_gas"]], "Q_gas_impo", "SESCO/MECON"),
    ]:
        df2 = df.copy()
        val_col = [c for c in df2.columns if c not in ("anio", "unidad")][0]
        df2 = df2.rename(columns={val_col: "valor"})
        df2["variable"] = var
        df2["fuente"] = fuente
        frames.append(df2[["anio", "variable", "unidad", "valor", "fuente"]])

    # Domestic prices
    pc_mi = precio_crudo_mi[["anio", "unidad", "precio_crudo_mdoint"]].copy()
    pc_mi["variable"] = "Pi_crudo"
    pc_mi["fuente"] = "MECON/IDEE/YPF"
    pc_mi = pc_mi.rename(columns={"precio_crudo_mdoint": "valor"})
    frames.append(pc_mi[["anio", "variable", "unidad", "valor", "fuente"]])

    pg_mi = precio_gas_mi_mmbtu[["anio", "unidad", "precio_gas_mdoint"]].copy()
    pg_mi["variable"] = "Pi_gas"
    pg_mi["fuente"] = "MECON/Regalias/IDEE"
    pg_mi = pg_mi.rename(columns={"precio_gas_mdoint": "valor"})
    frames.append(pg_mi[["anio", "variable", "unidad", "valor", "fuente"]])

    # Fiscalidad
    reg = regalias[["anio", "unidad", "regalias_total"]].copy()
    reg["variable"] = "regalias"
    reg["fuente"] = "SecEnergia"
    reg = reg.rename(columns={"regalias_total": "valor"})
    frames.append(reg[["anio", "variable", "unidad", "valor", "fuente"]])

    ret_col = "retenciones_hc" if "retenciones_hc" in retenciones.columns else retenciones.columns[-1]
    ret = retenciones[["anio", "unidad", ret_col]].copy()
    ret["variable"] = "retenciones"
    ret["fuente"] = "AFIP"
    ret = ret.rename(columns={ret_col: "valor"})
    frames.append(ret[["anio", "variable", "unidad", "valor", "fuente"]])

    sub = subsidios[["anio", "unidad", "subsidios_ejes"]].dropna().copy()
    sub["variable"] = "subsidios"
    sub["fuente"] = "EJES/CEFIP"
    sub = sub.rename(columns={"subsidios_ejes": "valor"})
    frames.append(sub[["anio", "variable", "unidad", "valor", "fuente"]])

    # Wage bill
    ms_col = "masa_salarial_total_oede" if "masa_salarial_total_oede" in masa_salarial.columns else "masa_salarial_total_ccnn"
    ms = masa_salarial[["anio", "unidad", ms_col]].dropna().copy()
    ms["variable"] = "MS"
    ms["fuente"] = "MinTrabajo/MECON"
    ms = ms.rename(columns={ms_col: "valor"})
    frames.append(ms[["anio", "variable", "unidad", "valor", "fuente"]])

    # Rent differential
    rc = renta_crudo_dif[["anio", "unidad_renta", "renta_dif_precios_crudo"]].dropna().copy()
    rc["variable"] = "renta_dif_precios_crudo"
    rc["fuente"] = "Propia"
    rc = rc.rename(columns={"unidad_renta": "unidad", "renta_dif_precios_crudo": "valor"})
    frames.append(rc[["anio", "variable", "unidad", "valor", "fuente"]])

    rg = renta_gas_dif[["anio", "unidad_renta", "renta_dif_precios_gas"]].dropna().copy()
    rg["variable"] = "renta_dif_precios_gas"
    rg["fuente"] = "Propia"
    rg = rg.rename(columns={"unidad_renta": "unidad", "renta_dif_precios_gas": "valor"})
    frames.append(rg[["anio", "variable", "unidad", "valor", "fuente"]])

    # GDP + profit
    gpbi = ganancia_pbi[["anio", "unidad", "pbi", "ganancia"]].melt(
        id_vars=["anio", "unidad"], var_name="variable", value_name="valor"
    )
    gpbi["fuente"] = "MECON/CCNN"
    frames.append(gpbi)

    # Stock assets
    stock = stock_rama[["anio", "unidad", "sector", "variable", "valor", "fuente"]].copy()
    stock["variable"] = stock["sector"] + "_" + stock["variable"]
    frames.append(stock[["anio", "variable", "unidad", "valor", "fuente"]])

    variables = pd.concat(frames, ignore_index=True)
    variables["codigo_variable"] = variables["variable"]
    variables = variables[["anio", "variable", "codigo_variable", "unidad", "valor", "fuente"]]
    variables = variables.dropna(subset=["valor"]).sort_values(["variable", "anio"])
    return variables


def write_outputs(
    variables: pd.DataFrame,
    ipc: pd.DataFrame,
    tcp_anual: pd.DataFrame,
    prod_crudo: pd.DataFrame,
    prod_gas_mmbtu: pd.DataFrame,
    precio_crudo_mi: pd.DataFrame,
    renta_crudo_dif: pd.DataFrame,
    renta_gas_dif: pd.DataFrame,
    stock_balances_empresas: pd.DataFrame,
    stock_segmentos: pd.DataFrame,
    stock_ypf: pd.DataFrame,
    # New rent calculus outputs (optional — skipped if None)
    renta_indirecto: pd.DataFrame = None,
    renta_directo: pd.DataFrame = None,
    tasa_ganancia_rama_stock: pd.DataFrame = None,
    ccnn_oficial: pd.DataFrame = None,
    empalme_ccnn: pd.DataFrame = None,
    costos: pd.DataFrame = None,
    renta_comparacion: pd.DataFrame = None,
) -> None:
    """Write all output files."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    BASE_CSV.mkdir(parents=True, exist_ok=True)

    # Main CSV
    variables.to_csv(RESULTS / "variables.csv", index=False)
    print(f"  variables.csv: {variables.shape}")

    # Stock CSVs
    stock_balances_empresas.to_csv(BASE_CSV / "stock_balances_empresas.csv", index=False)
    stock_segmentos.to_csv(BASE_CSV / "stock_segmentos.csv", index=False)
    stock_ypf.to_csv(BASE_CSV / "stock_ypf.csv", index=False)

    # Build sheet list for index
    sheet_names = [
        "variables", "tipo_cambio", "ipc", "produccion_crudo",
        "produccion_gas", "precios_mi", "renta_dif_crudo", "renta_dif_gas",
        "stock_empresas", "stock_segmentos",
    ]
    optional_sheets = {
        "RTPG_mecanismos": renta_indirecto,
        "RTPG_PextQ": renta_directo,
        "tg_pg_total": tasa_ganancia_rama_stock,
        "ccnn_pg": ccnn_oficial,
        "empalme_ccnn_pg": empalme_ccnn,
        "costos_pg": costos,
        "RTPG_comparacion": renta_comparacion,
    }
    for name, df in optional_sheets.items():
        if df is not None:
            sheet_names.append(name)

    # Master Excel workbook
    xlsx_path = RESULTS / "renta_de_la_tierra_hidrocarburifera_arg.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame({"sheet": sheet_names}).to_excel(writer, sheet_name="indice", index=False)
        variables.to_excel(writer, sheet_name="variables", index=False)
        tcp_anual.to_excel(writer, sheet_name="tipo_cambio", index=False)
        ipc.to_excel(writer, sheet_name="ipc", index=False)
        prod_crudo.to_excel(writer, sheet_name="produccion_crudo", index=False)
        prod_gas_mmbtu.to_excel(writer, sheet_name="produccion_gas", index=False)
        precio_crudo_mi.to_excel(writer, sheet_name="precios_mi", index=False)
        renta_crudo_dif.to_excel(writer, sheet_name="renta_dif_crudo", index=False)
        renta_gas_dif.to_excel(writer, sheet_name="renta_dif_gas", index=False)
        stock_balances_empresas.to_excel(writer, sheet_name="stock_empresas", index=False)
        stock_segmentos.to_excel(writer, sheet_name="stock_segmentos", index=False)
        for name, df in optional_sheets.items():
            if df is not None:
                df.to_excel(writer, sheet_name=name, index=False)
    n_sheets = len(sheet_names) + 1  # +1 for indice
    print(f"  {xlsx_path.name}: {n_sheets} sheets")


def run(data: dict) -> pd.DataFrame:
    """
    Run final assembly given a dict of all preprocessed DataFrames.
    Returns the assembled variables DataFrame.
    """
    variables = assemble_variables(
        ipc=data["ipc"],
        tcp_anual=data["tcp_anual"],
        prod_crudo=data["prod_crudo"],
        prod_gas_mmbtu=data["prod_gas_mmbtu"],
        prod_total=data["prod_total"],
        expo_crudo=data["expo_crudo"],
        expo_gas=data["expo_gas"],
        impo_crudo=data["impo_crudo"],
        impo_gas=data["impo_gas"],
        precio_crudo_mi=data["precio_crudo_mi"],
        precio_gas_mi_mmbtu=data["precio_gas_mi_mmbtu"],
        regalias=data["regalias"],
        retenciones=data["retenciones"],
        subsidios=data["subsidios"],
        masa_salarial=data["masa_salarial_hidrocarburos"],
        stock_rama=data["stock_rama"],
        renta_crudo_dif=data["renta_crudo_dif"],
        renta_gas_dif=data["renta_gas_dif"],
        ganancia_pbi=data["ganancia_pbi"],
        ipc_us=data["ipc_us"],
    )
    write_outputs(
        variables=variables,
        ipc=data["ipc"],
        tcp_anual=data["tcp_anual"],
        prod_crudo=data["prod_crudo"],
        prod_gas_mmbtu=data["prod_gas_mmbtu"],
        precio_crudo_mi=data["precio_crudo_mi"],
        renta_crudo_dif=data["renta_crudo_dif"],
        renta_gas_dif=data["renta_gas_dif"],
        stock_balances_empresas=data["stock_balances_empresas"],
        stock_segmentos=data["stock_segmentos"],
        stock_ypf=data["stock_ypf"],
        renta_indirecto=data.get("renta_indirecto"),
        renta_directo=data.get("renta_directo"),
        tasa_ganancia_rama_stock=data.get("tasa_ganancia_rama_stock"),
        ccnn_oficial=data.get("ccnn_oficial"),
        empalme_ccnn=data.get("empalme_ccnn"),
        costos=data.get("costos"),
        renta_comparacion=data.get("renta_comparacion"),
    )
    return variables
