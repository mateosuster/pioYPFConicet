
## Base de datos de estimaciones económicas del sector hidrocarburífero de América Latina
Repositorio del Proyecto de Investigación Orientada (PIO) Conicet-YPF "La apropiación de la renta petrolera diferencial por distintos sujetos sociales en Argentina comparado con Venezuela y Brasil (2002 a la actualidad)"

## Python Environment Setup

```bash
# Create and activate venv
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

## Preprocessing Pipeline (Python)

The main preprocessing pipeline is run from the **project root**:

```bash
python src/preprocesamiento.py
```

To also save each module's intermediate outputs to `results/intermedios/<module_name>/` for inspection:

```bash
python src/preprocesamiento.py --intermediates
```

This runs 15 steps in sequence and writes:
- `results/argentina/variables.csv`
- `results/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx` (see sheet list below)
- `results/argentina/base_csv/stock_*.csv`
- `results/argentina/plots_python/<timestamp>_<source>/` — 8 PNG plots + `notes.txt` + a copy of the Excel

Each module can also be run and tested independently:

```bash
python -m src.preproc.indices_precios
python -m src.preproc.produccion
# etc.
```

### Module overview

| Module | Replaces (Rmd section) | Description |
|---|---|---|
| `src/preproc/indices_precios.py` | IPC y TCP | IPC, TCP/TCC, US CPI, peso converters |
| `src/preproc/produccion.py` | Producción | Crude and gas production series |
| `src/preproc/precios_mi.py` | Precios internos | Domestic crude and gas prices |
| `src/preproc/comex.py` | Comercio exterior | Exports and imports |
| `src/preproc/fiscalidad.py` | Fiscalidad | Regalías, retenciones, subsidios |
| `src/preproc/empleo.py` | Empleo | Employment and wage bill |
| `src/preproc/activos.py` | Activos | Capital stock and balances |
| `src/preproc/renta_dif.py` | Renta diferencial | Differential rent by commodity |
| `src/preproc/valor_produccion.py` | Valor producción | Total production value and CCNN splicing |
| `src/preproc/tasa_ganancia.py` | Tasa de ganancia | Sector profit rate by stock source |
| `src/preproc/renta_sobrevaluacion.py` | Renta sobrevaluación | Overvalued-exchange-rate rent component |
| `src/preproc/renta_total.py` | Renta total | All rent methods + multi-source comparison |
| `src/preproc/output.py` | Salidas | Assembles long-form table and writes files |

Shared helpers (`src/utils/`) are Python translations of `src/functiones_hidrocarburos.R`:
- `indices.py` — `generar_indice`, `cambio_porcentual`, `tasa_crecimiento`, `variacion_interanual`
- `conversores.py` — unit converters (m³↔bbl, ft³↔m³, MMBTU↔m³, BEP)

### Annual update parameters

Defined at the top of `src/preproc/indices_precios.py`:

```python
YEAR_LAST = 2025            # last year with complete data
YEAR_EMPLEO_CORTE = 2025    # last year with annual employment/wages data
YEAR_SEC_ENERGIA_UPPER = 2015  # cutoff for SecEnergia vs SESCO crude source
```

### Capital stock source flag

Set in `src/preprocesamiento.py` or passed via CLI:

```bash
python src/preprocesamiento.py                            # uses S&P Capital IQ (default)
python src/preprocesamiento.py --STOCK_SOURCE="Bolsar"
python src/preprocesamiento.py --STOCK_SOURCE="AFIP (combinada)"
python src/preprocesamiento.py --STOCK_SOURCE="S&P Capital IQ" --RENTA_SV_SOURCE=indec
python src/preprocesamiento.py --STOCK_SOURCE="S&P Capital IQ" --RENTA_SV_SOURCE=sesco

```

The module-level default can also be changed at the top of `src/preprocesamiento.py`:

```python
STOCK_SOURCE = "S&P Capital IQ"  # default
```

Controls which capital stock series is used as the **primary** source for:
- `consumo_k_fijo` (capital depreciation in `empalme_ccnn` and `criterio_propio`)
- `tasa_ganancia_rama` (sector profit rate: Criterio propio EBE / selected stock)
- `renta_directo` / `renta_indirecto` (direct and indirect rent methods)

All available sources are always written to the `tg_pg_total` sheet for comparison.
Multi-source enterprise-rent inputs live in the `renta_empresas` sheet (wide format: one
column per stock source for `ppye`, `tg`, and `renta_empresas`, plus shared `pv`, EBE and
`tg_normal`). Enterprise rent in `RTPG_mecanismos` uses the same EBE/ppye series as the
matching column on `renta_empresas` for the selected `STOCK_SOURCE`. The `notas` sheet records both source selections and the run timestamp.

| Value | Source | Coverage |
|---|---|---|
| `"Bolsar"` | Balance sheets from Bolsar (listed companies, sectors integrada + produccion) | dynamic |
| `"AFIP (v8)"` | Old AFIP series from `data/afip/gcia_v8.xlsx` | ~2000–2014 |
| `"AFIP (nuevo)"` | New AFIP series from `update/Serie_AFIP_Consolidada_2002_2022_V2.xlsx` | 2002–2022 |
| `"AFIP (combinada)"` | Old series pre-2014 spliced with new series from 2014 onward | 2000–2022 |
| `"S&P Capital IQ"` | S&P Capital IQ data via `src/preproc/petroarg.py` | dynamic |

### Currency-overvaluation rent source flag (`RENTA_SV_SOURCE`)

Controls which export series feeds the **sobrevaluación cambiaria** component in indirect rent (`renta_indirecto` / `RTPG_mecanismos`).

Set in `src/preprocesamiento.py` or passed via CLI:

```bash
python src/preprocesamiento.py                              # uses sesco (default)
python src/preprocesamiento.py --RENTA_SV_SOURCE=sesco
python src/preprocesamiento.py --RENTA_SV_SOURCE=indec
python src/preprocesamiento.py --STOCK_SOURCE="Bolsar" --RENTA_SV_SOURCE=indec
```

The module-level default can also be changed at the top of `src/preprocesamiento.py`:

```python
RENTA_SV_SOURCE = "sesco"  # default
# RENTA_SV_SOURCE = "indec"
```

| Value | Method | Notes |
|---|---|---|
| `"sesco"` | `expo_q × precio_externo × (tcp - tcc)` | Crude and gas computed separately from SESCO trade data |
| `"indec"` | `expo_USD × (tcp - tcc)` | INDEC *Complejos Exportadores*; 2002+ with petróleo/gas split; pre-2002 combined value in petróleo column; pre-1993 falls back to SESCO |

Both SESCO and INDEC overvaluation series are always written to the `renta_sv_crudo&gas` sheet for comparison; only the selected source enters `renta_indirecto`.

### Output Excel sheets

`results/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx`

| Sheet | Contents |
|---|---|
| `notas` | Run timestamp, `STOCK_SOURCE`, and `RENTA_SV_SOURCE` selections (with descriptions) |
| `variables` | Long-form table of all variables (variable × anio × valor) |
| `RTPG_mecanismos` | Indirect rent by mechanism for the selected `STOCK_SOURCE` (ARS ctes., TCC, TCP) |
| `renta_empresas` | Inputs for enterprise-captured rent by stock source (`ppye_*`, `tg_*`, `renta_empresas_*`, plus shared `pv`, EBE, `tg_normal`) |
| `RTPG_PextQ` | Direct rent (PextQ method) |
| `RTPG_comparacion` | Rent comparison with other authors |
| `tg_pg_total` | Profit rates by stock source |
| `tipo_cambio` | Exchange rate series (TCC, TCP) |
| `stock_balances_empresas` | Company-level capital stock |
| `stock_segmentos` | Segment-level capital stock |
| `stock_ypf` | YPF-specific capital stock |

## QuickFS API (company financials)

Scripts in `src/quick fs/` pull company balance-sheet data via the QuickFS API. Create a `.env` file in the project root:

```
QUICKFS_API_KEY=your_key_here
```

Also install `python-dotenv` and `requests` (already in `requirements.txt`). The `.env` file is git-ignored.

## Renta Plots (Python)

`src/plots_renta_argentina.py` generates 8 PNG plots from the master Excel.

It is run automatically at the end of `python src/preprocesamiento.py`. It can also be run standalone:

```bash
python src/plots_renta_argentina.py
python src/plots_renta_argentina.py --RENTA_SV_SOURCE=indec
```

When run standalone without flags, `STOCK_SOURCE` and `RENTA_SV_SOURCE` are read from the Excel `notas` sheet.

Plots are saved to a **timestamped subfolder** inside `results/argentina/plots_python/`, e.g.:
`results/argentina/plots_python/20260525_143000_SP_Capital_IQ/`

Each run folder contains:
- `notes.txt` — run timestamp, `STOCK_SOURCE`, and `RENTA_SV_SOURCE` selections
- `renta_de_la_tierra_hidrocarburifera_arg.xlsx` — copy of the master Excel used for the plots
- 8 PNG files (see table below)

| File | Description |
|---|---|
| `renta_mecanismos_y_pxq_ARG.png` | Total rent: PextQ vs. sum-of-mechanisms comparison (line, M USD TCp 2020) |
| `renta_mecanismos.png` | Rent by mechanism, stacked bar (M ARS 2018) |
| `renta_mecanismos_tcp.png` | Rent by mechanism, stacked bar (M USD TCc 2020) |
| `comparacion_autores.png` | Total rent vs. other authors (M USD TCp 2020, TCP subtitle) |
| `comparacion_autores_usd_tcp.png` | Total rent vs. other authors (M USD TCp 2020) |
| `comparacion_autores_tipo_renta.png` | Rent by type, faceted, vs. other authors (M USD TCp 2020) |
| `comparacion_autores_tipo_renta_usd_tcp.png` | Rent by type, faceted, vs. other authors (M USD TCp 2020, alt subtitle) |
| `comparacion_autores_tipo_renta_usd_tcc.png` | Rent by type, faceted, vs. other authors (M USD TCc 2020) |

Requires `kaleido` for PNG export (`pip install kaleido`).

## Analysis: Capital Stock Source Comparison

`src/analysis/tg_stock_analysis.py` reads the master Excel and produces a self-contained analysis folder.

```bash
python src/analysis/tg_stock_analysis.py
```

Output: `results/argentina/analisis_tg_stock/`

| File | Description |
|---|---|
| `report.md` | Markdown report with descriptions, computed insights, and plot links |
| `01_tg_por_fuente.png` | Profit rate over time by stock source |
| `02_ppye_por_fuente.png` | ppye by source in 3 currency units (M$ ctes. 2018, USD TCC, USD TCP) |
| `03_ebe_tiempo.png` | Excedente Bruto de Explotación in 3 currency units |
| `04_ppye_bolsar.png` | ppye by company — Bolsar source |
| `05_ppye_ciq.png` | ppye by company — S&P Capital IQ source |
| `06_ppye_sector.png` | ppye by sector, all sources stacked |
| `07_cobertura.png` | Heatmap: company × year coverage by source |
| `14_renta_total_por_fuente.png` | Total rent (M USD TCP) over time, one line per stock source (from `renta_empresas` + `RTPG_mecanismos`) |
| `15_renta_empresas_brecha.png` | Enterprise rent component + total rent spread across sources |

Requires `kaleido` for PNG export (`pip install kaleido`).

**Monetary conversions** applied to all current-peso values:

| Label | Formula |
|---|---|
| Pesos constantes 2018 | `valor / ipc_18` |
| USD TCC | `valor / tcc` |
| USD TCP | `valor / tcp` |
