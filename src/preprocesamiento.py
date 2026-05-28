"""
Main preprocessing pipeline entry point.
Run: python src/preprocesamiento.py

Loads all data sources, runs all preprocessing modules in order,
and writes results/argentina/variables.csv + master .xlsx.

Optional flags:
  --intermediates              save each module's output to results/intermedios/
  --STOCK_SOURCE=<source>      capital stock source (see README)
  --RENTA_SV_SOURCE=<sesco|indec>  overvaluation-rent export source (see README)
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

# Stock source for primary calculations (consumo_k_fijo, tg_rama, renta_directo).
# Options: "Bolsar", "AFIP (v8)", "AFIP (nuevo)", "AFIP (combinada)", "S&P Capital IQ"
STOCK_SOURCE = "S&P Capital IQ"
# STOCK_SOURCE = "Bolsar"

# Source for currency-overvaluation rent in renta_total (indirect method).
# "sesco"  → SESCO-based: expo_q * precio_externo * (tcp - tcc), crude and gas separately
# "indec"  → INDEC Complejos Exportadores: expo_USD * (tcp - tcc), 2002+ with petróleo/gas split;
#             pre-2002 combined value in petróleo column; pre-1993 falls back to SESCO
RENTA_SV_SOURCE = "sesco"
# RENTA_SV_SOURCE = "indec"


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


def run(save_intermediates: bool = False, stock_source: str = None,
        renta_sv_source: str = None) -> None:
    stock_source = stock_source or STOCK_SOURCE
    renta_sv_source = renta_sv_source or RENTA_SV_SOURCE
    if renta_sv_source not in ("sesco", "indec"):
        raise ValueError(
            f"renta_sv_source must be 'sesco' or 'indec', got {renta_sv_source!r}"
        )
    print("=== preprocesamiento.py ===")
    print(f"  STOCK_SOURCE={stock_source!r}, RENTA_SV_SOURCE={renta_sv_source!r}")

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
    fisc = fiscalidad.run(idx["tcp_anual"], idx["ganancia_pbi"], idx["ipc"])
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
        stock_estimado=act["stock_estimado"],
        stock_source=STOCK_SOURCE,
    )
    if save_intermediates:
        _save_intermediates("valor_produccion", {
            k: v for k, v in vprod.items() if isinstance(v, pd.DataFrame)
        })

    print("[11/15] tasa_ganancia...")
    tg = tasa_ganancia.run(
        empalme_ccnn=vprod["empalme_ccnn"],
        valor_total_produccion=vprod["valor_total_produccion"],
        stock_estimado=act["stock_estimado"],
        ipc=idx["ipc"],
        stock_rama_alt=act["stock_rama_alt"],
        stock_source=STOCK_SOURCE,
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
        tcp_anual=idx["tcp_anual"],
    )
    if save_intermediates:
        _save_intermediates("renta_sobrevaluacion", rsv)

    print("[13/15] renta_total...")
    rtot = renta_total.run(
        renta_tg=tg["renta_tg"],
        renta_tg_multi=tg.get("renta_tg_multi"),
        tasa_ganancia_rama_stock=tg.get("tasa_ganancia_rama_stock"),
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
        stock_source=stock_source,
        renta_tcp_indec=rsv["renta_tcp_indec"],
        renta_sv_source=renta_sv_source,
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
    variables = output.run(
        data, stock_source=stock_source, renta_sv_source=renta_sv_source
    )

    print("[15/15] plots_renta_argentina...")
    import plots_renta_argentina
    plots_renta_argentina.main(
        stock_source=stock_source, renta_sv_source=renta_sv_source
    )

    print(f"\nDone. variables shape: {variables.shape}")
    print(f"Unique variables: {variables['variable'].nunique()}")
    print(f"Year range: {variables['anio'].min()}–{variables['anio'].max()}")


if __name__ == "__main__":
    _stock = STOCK_SOURCE
    _renta_sv = RENTA_SV_SOURCE
    for _a in sys.argv[1:]:
        if _a.startswith("--STOCK_SOURCE="):
            _stock = _a.split("=", 1)[1].strip("'\"")
        elif _a.startswith("--RENTA_SV_SOURCE="):
            _renta_sv = _a.split("=", 1)[1].strip("'\"")
    run(
        save_intermediates="--intermediates" in sys.argv,
        stock_source=_stock,
        renta_sv_source=_renta_sv,
    )
