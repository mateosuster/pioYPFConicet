"""
Main preprocessing pipeline entry point.
Run: python src/preprocesamiento.py

Loads all data sources, runs all preprocessing modules in order,
and writes results/argentina/variables.csv + master .xlsx.

Optional flag --intermediates saves each module's output DataFrames to
results/intermedios/<module_name>/ for inspection.
"""

import sys
from pathlib import Path

# Ensure src/ is on the path when run directly
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from preproc import (
    indices_precios, produccion, precios_mi, precios_me,
    comex, fiscalidad, empleo, activos, renta_dif,
    valor_produccion, tasa_ganancia, renta_sobrevaluacion, renta_total,
    output,
)

ROOT = Path(__file__).parent.parent
INTERMEDIOS = ROOT / "results" / "intermedios"


def _save_intermediates(module_name: str, data: dict) -> None:
    """Save all DataFrames and Series in *data* to results/intermedios/<module_name>/."""
    out = INTERMEDIOS / module_name
    out.mkdir(parents=True, exist_ok=True)
    for key, val in data.items():
        if isinstance(val, pd.DataFrame):
            val.to_csv(out / f"{key}.csv", index=False)
        elif isinstance(val, pd.Series):
            val.to_csv(out / f"{key}.csv", header=True)
    n = sum(1 for v in data.values() if isinstance(v, (pd.DataFrame, pd.Series)))
    print(f"    -> intermedios/{module_name}/ ({n} files)")


def run(save_intermediates: bool = False) -> None:
    print("=== preprocesamiento.py ===")

    print("[1/15] indices_precios...")
    idx = indices_precios.run()
    if save_intermediates:
        _save_intermediates("indices_precios", idx)

    print("[2/15] produccion...")
    prod = produccion.run()
    if save_intermediates:
        _save_intermediates("produccion", prod)

    print("[3/15] precios_mi...")
    prec = precios_mi.run(idx["tcp_anual"], idx["ipc"], idx["ipim"], idx["conversor_pesos"])
    if save_intermediates:
        _save_intermediates("precios_mi", prec)

    print("[4/15] precios_me...")
    pme = precios_me.run(idx["tcp_anual"], idx["ipc"], idx["conversor_pesos"])
    if save_intermediates:
        _save_intermediates("precios_me", pme)

    print("[5/15] comex...")
    cx = comex.run()
    if save_intermediates:
        _save_intermediates("comex", cx)

    print("[6/15] fiscalidad...")
    fisc = fiscalidad.run(idx["tcp_anual"], idx["ganancia_pbi"])
    if save_intermediates:
        _save_intermediates("fiscalidad", fisc)

    print("[7/15] empleo...")
    emp = empleo.run(idx["conversor_pesos"])
    if save_intermediates:
        _save_intermediates("empleo", emp)

    print("[8/15] activos...")
    act = activos.run(idx["ipc_18"])
    if save_intermediates:
        _save_intermediates("activos", act)

    print("[9/15] renta_dif...")
    renta = renta_dif.run(
        prod_crudo=prod["prod_crudo"],
        prod_gas_mmbtu=prod["prod_gas_mmbtu"],
        expo_crudo=cx["expo_crudo"],
        expo_gas=cx["expo_gas"],
        precio_mi_crudo=prec["precio_crudo_mi"],
        precio_mi_gas_mmbtu=prec["precio_gas_mi_mmbtu"],
        tcp_anual=idx["tcp_anual"],
        precios_referencia_crudo=pme["precios_referencia_crudo"],
        precio_mdomundial_gas=pme["precio_mdomundial_gas_MMBTU"],
    )
    if save_intermediates:
        _save_intermediates("renta_dif", renta)

    print("[10/15] valor_produccion...")
    vprod = valor_produccion.run(
        masa_salarial_hidrocarburos=emp["masa_salarial_hidrocarburos"],
        prod_crudo=prod["prod_crudo"],
        expo_crudo=cx["expo_crudo"],
        prod_gas_mmbtu=prod["prod_gas_mmbtu"],
        expo_gas=cx["expo_gas"],
        precio_crudo_mi=prec["precio_crudo_mi"],
        precio_gas_mi_usd_mmbtu=prec["precio_gas_mi_usd_mmbtu"],
        precio_mdomundial_gas=pme["precio_mdomundial_gas_MMBTU"],
        precios_referencia_crudo=pme["precios_referencia_crudo"],
        tcp_anual=idx["tcp_anual"],
        ipc=idx["ipc"],
    )
    if save_intermediates:
        _save_intermediates("valor_produccion", {
            k: v for k, v in vprod.items() if isinstance(v, pd.DataFrame)
        })

    print("[11/15] tasa_ganancia...")
    tg = tasa_ganancia.run(
        empalme_ccnn=vprod["empalme_ccnn"],
        valor_total_produccion=vprod["valor_total_produccion"],
        stock_estimado=vprod["stock_estimado"],
        ipc=idx["ipc"],
    )
    if save_intermediates:
        _save_intermediates("tasa_ganancia", tg)

    print("[12/15] renta_sobrevaluacion...")
    rsv = renta_sobrevaluacion.run(
        renta_crudo_dif=renta["renta_crudo_dif"],
        renta_gas_dif=renta["renta_gas_dif"],
        expo_usd_crudo=cx["expo_usd_crudo"],
        regalias=fisc["regalias"],
        retenciones=fisc["retenciones"],
    )
    if save_intermediates:
        _save_intermediates("renta_sobrevaluacion", rsv)

    print("[13/15] renta_total...")
    rtot = renta_total.run(
        renta_tg=tg["renta_tg"],
        criterio_propio=vprod["criterio_propio"],
        subsidios=fisc["subsidios"],
        renta_crudo_dif=renta["renta_crudo_dif"],
        renta_gas_dif=renta["renta_gas_dif"],
        retenciones_regalias=rsv["retenciones_regalias"],
        renta_tcp_crudo=rsv["renta_tcp_crudo"],
        renta_tcp_gas=rsv["renta_tcp_gas"],
        tcp_anual=idx["tcp_anual"],
        ipc=idx["ipc"],
        ganancia_pbi=idx["ganancia_pbi"],
        prod_total=prod["prod_total"],
        valor_total_produccion=vprod["valor_total_produccion"],
        empalme_ccnn=vprod["empalme_ccnn"],
        ipc_us=idx["ipc_us"],
        precios_referencia_crudo=pme["precios_referencia_crudo"],
    )
    if save_intermediates:
        _save_intermediates("renta_total", rtot)

    # Assemble full data dict for output
    data = {
        **idx,
        **prod,
        **prec,
        **pme,
        **cx,
        **fisc,
        **emp,
        **act,
        **renta,
        **vprod,
        **tg,
        **rsv,
        **rtot,
    }

    print("[14/15] output...")
    variables = output.run(data)

    print(f"\nDone. variables shape: {variables.shape}")
    print(f"Unique variables: {variables['variable'].nunique()}")
    print(f"Year range: {variables['anio'].min()}–{variables['anio'].max()}")


if __name__ == "__main__":
    run(save_intermediates="--intermediates" in sys.argv)
