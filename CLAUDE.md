# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research project (PIO Conicet-YPF) estimating hydrocarbons sector rent, profits, wages, and investment in Argentina (2002–present), with comparisons to Venezuela and Brazil. Preprocessing is in Python (`src/preprocesamiento.py` + `src/preproc/`); downstream analysis is in R Markdown notebooks.

## Running the Analysis

**Preprocessing (Python)** — run from the project root:
```bash
python src/preprocesamiento.py
```

**Downstream analysis (R)** — run interactively in RStudio via `src/pioYPF.Rproj`, or from the terminal:
```r
rmarkdown::render("src/valor_produccion_y_renta.Rmd")
```

R packages required: `here`, `tidyverse`, `data.table`, `readxl`, `lubridate`, `zoo`, `ggplot2`, `plotly`, `knitr`, `kableExtra`, `Hmisc`, `fs`.
Python packages: see `requirements.txt` (`pandas`, `numpy`, `openpyxl`, `xlrd`, `plotly`).

## Analysis Pipeline

**Step 1 — Python preprocessing** (`src/preprocesamiento.py`): loads and harmonizes all raw sources, handles historical currency conversions (m$n → $Ley → $a → ARS), builds IPC and tipo de cambio de paridad series. The pipeline is split into 9 submodules in `src/preproc/`, each exposing a `run()` function that returns a dict of named DataFrames. `output.py` assembles everything into the long-form variables table and writes:

- `results/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx` (11-sheet master file)
- `results/argentina/variables.csv`
- `results/argentina/base_csv/` (stock/balance CSVs)

**Annual update parameters** (`YEAR_LAST`, `YEAR_EMPLEO_CORTE`, `YEAR_SEC_ENERGIA_UPPER`) are constants at the top of `src/preproc/indices_precios.py` — update these first on each data refresh.

**Step 2 — R downstream notebooks**: read from `results/` and `data/`, never from each other.

- **`src/valor_produccion_y_renta.Rmd`** — decomposes total production value into wages, profits, and rent
- **`src/costos_inversiones_rentabilidad.Rmd`** — costs, investment, profitability
- **`src/comparacion_paises.Rmd`** — Argentina vs. Venezuela and Brazil
- **`src/preparation_data_to_upload.Rmd`** — produces `results/argentina/data_renta_hidrocarburifera_arg_para_carga.csv` for external sharing

## Shared Helpers

**R** (`src/functiones_hidrocarburos.R`) — sourced at the top of every R notebook:
- Unit converters: `conversor_m3bbl_p/q`, `conversor_ft3m3_p/q`, `conversor_MMBTUm3gas_p`, `conversor_m3bep_q`, etc.
- Index builder: `generar_indice(serie, fecha, fecha_base)`
- Growth helpers: `cambio_porcentual()`, `tasa_crecimiento()`, `variacion_interanual()`
- ggplot themes: `theme_propio()`, `plot_theme()`, `plot_ggplotly()`

**Python** (`src/utils/`) — translations of the R helpers for the Python pipeline:
- `indices.py` — `generar_indice`, `cambio_porcentual`, `tasa_crecimiento`, `variacion_interanual`
- `conversores.py` — unit converters (same conversions, snake_case names)

## Path Conventions

- **Python modules** (`src/preproc/*.py`, `src/utils/`) resolve paths from the project root via `Path(__file__).parents[N]`. Always run `python src/preprocesamiento.py` from the project root.
- **R notebooks** use `here()` (project root) or relative paths from `src/`: `../data/`, `../results/`.
- `auxiliares.R` uses absolute `C:/Archivos/...` paths and is a scratch/helper script, not part of the main pipeline.

## Data Sources (key ones)

| Folder | Source |
|---|---|
| `data/secretaria_energia/sesco/` | Argentine Energy Secretariat (SESCO) production & trade |
| `data/eia/` | US EIA international oil & gas prices and production |
| `data/indec/` | INDEC export quantities and values |
| `data/mecon/` | MECON national accounts, GDP, hydrocarbon variables |
| `data/balances/` | Company balance sheets (YPF and others) |
| `data/iapg/` | IAPG drilling data by year |
| `data/bls/` | US BLS CPI (for constant-dollar conversions) |
| `data/indices/` | IPC Argentina annual averages |
| `data/tcp/` | Tipo de cambio de paridad and historical TCC series |
| `data/conversores/` | Currency conversion factors (historical peso denominations) |
| `update/` | Pending data updates not yet integrated |

## Key Variables Convention

- `anio`: year (integer)
- `valor`: numeric value (amount/price)
- `variable` / `codigo_variable`: variable name/code (used for pivoting)
- `fuente`: data source label
- Monetary values are in ARS unless suffixed `_usd`; real series use `IPC_18` (2018 base) or `ipc_us_20` (2020 base for USD series)

## Python Environment

See README.md for setup. The `.venv` is git-ignored; activate it before running `src/preprocesamiento.py`. QuickFS API scripts (`src/quick fs/`) require a `.env` file at the project root with `QUICKFS_API_KEY=your_key_here`.

## Working Style

### Clarification Protocol
Before exploring or modifying data sources, restate the specific target (column, variable, sheet) and confirm with the user. Do not begin broad exploration when the user has named a specific target.
