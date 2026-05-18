
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

This runs 9 modules in sequence and writes:
- `results/argentina/variables.csv`
- `results/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx` (11 sheets)
- `results/argentina/base_csv/stock_*.csv`

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

## QuickFS API (company financials)

Scripts in `src/quick fs/` pull company balance-sheet data via the QuickFS API. Create a `.env` file in the project root:

```
QUICKFS_API_KEY=your_key_here
```

Also install `python-dotenv` and `requests` (already in `requirements.txt`). The `.env` file is git-ignored.
