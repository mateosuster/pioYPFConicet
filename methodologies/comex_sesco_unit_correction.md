# Corrección de errores de unidad en datos SESCO de comercio exterior

## 1. Contexto

La variable `renta_expo_sobrevaluada` (apropiación de renta vía sobrevaluación cambiaria) se
calcula en `renta_sobrevaluacion.py` como:

```
renta = expo * precio_externo * tcp  -  expo * precio_externo * tcc
```

Donde `expo` es la cantidad exportada anual (barril para crudo, MMBTU para gas). Si `expo`
es cero o NaN, la renta resulta cero independientemente de los precios y el diferencial
cambiario.

Al analizar la hoja `RTPG_mecanismos` del Excel de salida se detectaron ceros en:

- `renta_expo_sobrevaluada_gas` desde 2010
- `renta_expo_sobrevaluada_crudo` desde 2021

El archivo `comex_post2010.csv` (fuente SESCO original) estaba desactualizado y no cubría
esos años. La solución fue integrar dos archivos SESCO de formato nuevo que sí tienen
cobertura actualizada.

---

## 2. Fuente de datos: archivos SESCO de formato nuevo

| Archivo | Cobertura |
|---|---|
| `importaciones-exportaciones.csv` | 2010–2015 |
| `importaciones-exportaciones-a-partir-del-2016-.csv` | 2016–presente |

Ambos archivos comparten un esquema idéntico de 13 columnas (separador coma, codificación
UTF-8 BOM):

| Columna | Descripción |
|---|---|
| `anio`, `mes` | Año y mes de la operación |
| `empresa` | Empresa exportadora/importadora |
| `tipodecomercializacion` | `"Exportación"` / `"Importación"` |
| `producto` | Nombre del producto, con unidad embebida (ej.: `"Gas Natural(miles/m3)"`) |
| `unidad` | Unidad declarada: `(m3)`, `(miles/m3)`, `(Ton)` |
| `cantidad` | Volumen físico en la unidad declarada |
| `monto` | Valor en USD (FOB) |
| `pais` | País de destino/origen |

### Filtros aplicados

- **Crudo:** `producto.str.contains("Cuenca")` y `unidad == "(m3)"` → m3 → barriles
- **Gas natural (gasoducto):** `producto.str.startswith("Gas Natural(")` y `unidad == "(miles/m3)"` → miles/m3 × 1000 → m3 → MMBTU
  - La condición `startswith` excluye `"Gas Natural Licuado(miles/m3)"` (GNL, diferente
    mercado y precio de referencia)
- Para **totales de exportación**: se suman todas las empresas y países destino sin filtrar
  (los datos reflejan los despachos al exterior con independencia del destino)

---

## 3. Detección de errores de unidad: precio implícito

### Metodología

Al cargar los archivos se calcula el **precio implícito** por fila:

```
precio_implicito = monto / cantidad    [USD / miles/m3]
```

Este ratio debe ser aproximadamente constante en el tiempo para un mismo producto, ya que
refleja el precio de exportación del gas en USD por unidad de volumen. Una desviación de
tres órdenes de magnitud (factor 1000×) respecto a la mediana es la firma de un error de
unidad: la cantidad fue ingresada en m3 en lugar de miles/m3.

**Umbral de detección:** `precio_implicito < mediana / 100`

El factor 100 es deliberadamente conservador. Un error de unidad produce una desviación de
1000×, por lo que el umbral captura todos los casos genuinos sin riesgo de falsos positivos
dentro del rango normal de variación de precios.

### Distribución del precio implícito (gas, exportaciones)

| Estadístico | USD / miles/m3 |
|---|---|
| N | 766 filas con cantidad > 0 |
| Mediana | 227.53 |
| Media | 333.30 |
| Percentil 25 | 147.87 |
| Percentil 75 | 446.69 |
| Mínimo (post-corrección) | ~136 |
| Máximo | 1,616 |

La distribución es amplia pero unimodal. Los tres outliers detectados están entre 0.14 y
0.24 USD/miles/m3, es decir, entre 900× y 1600× por debajo de la mediana.

---

## 4. Outliers detectados: gas natural

| Fecha | Empresa | Cantidad raw (miles/m3) | Monto (USD) | Precio implícito raw | Precio implícito corregido |
|---|---|---|---|---|---|
| 2017-04 | PAN AMERICAN SUR S.A. | 822 | 112 | 0.14 USD/miles/m3 | 136.54 USD/miles/m3 |
| 2025-04 | PAN AMERICAN ENERGY SL | 17,901,160 | 3,960,477 | 0.22 USD/miles/m3 | 221.24 USD/miles/m3 |
| 2025-07 | PAN AMERICAN ENERGY SL | 10,168,012 | 2,442,787 | 0.24 USD/miles/m3 | 240.24 USD/miles/m3 |

**Corrección aplicada:** `cantidad_corregida = cantidad / 1000`

Tras la corrección los tres precios implícitos caen dentro del rango normal de la
distribución (136–240 vs. mediana 228 USD/miles/m3). El `monto` (USD) se conserva intacto
porque es la variable ancla: el valor monetario de las exportaciones es objeto de
declaración aduanera y fiscalización independiente.

La corrección se aplica automáticamente en `_extract_gas_new()` dentro de `comex.py`
cada vez que se ejecuta el pipeline, por lo que no modifica los archivos fuente originales.

---

## 5. Control: crudo

Para el crudo se ejecutó la misma detección sobre los 327,182 registros de exportaciones
por cuenca (unidad `(m3)`). Se encontraron **38 filas con `monto == 0`**, principalmente
de ENAP Sipetrol Argentina S.A. (2011–2022) y algunas de Petrolera LF/TDF, Vista Oil y YPF.

Estas filas representan un fenómeno distinto al error de unidad:

- `cantidad > 0` pero `monto == 0`: el volumen está registrado pero el valor monetario no.
  Pueden ser transferencias intra-grupo, exportaciones con precio de liquidación diferido,
  o simplemente datos faltantes en la declaración original.

**No se aplica ninguna corrección:** al agregar por año, estas filas aportan cero al
`monto` total (comportamiento correcto — se ignora la componente de valor no declarada)
y su contribución a la `cantidad` es legítima.

---

## 6. Impacto en las series anuales

### Gas natural exportado (MMBTU)

| Año | Serie raw | Serie corregida | Diferencia |
|---|---|---|---|
| 2010–2024 | correcta | sin cambio | 0 % |
| 2017 | 2,408,075 | 2,379,077 | −1 % |
| 2025 | 1,062,486,282 | 72,635,353 | −93 % |
| 2026 | sin cambio | sin cambio | 0 % |

El año 2025 tenía una inflación artificial de ~15× debida a los dos outliers de
PAN AMERICAN ENERGY SL. La serie corregida es coherente con la tendencia de crecimiento
sostenido de exportaciones de gas asociada al desarrollo de Vaca Muerta
(54 M MMBTU en 2024 → 73 M MMBTU en 2025).

### Crudo exportado (barriles)

La integración de los archivos nuevos recupera datos que faltaban en `comex_post2010.csv`:

| Año | Fuente vieja | Fuente nueva | Serie final |
|---|---|---|---|
| 2019 | 23.9 M bbl | 23.9 M bbl | 23.9 M bbl |
| 2020 | 12.0 M bbl | 31.5 M bbl | 31.5 M bbl (más completa) |
| 2021 | NaN | 27.5 M bbl | 27.5 M bbl |
| 2022 | NaN | 41.9 M bbl | 41.9 M bbl |
| 2023 | NaN | 46.7 M bbl | 46.7 M bbl |
| 2024 | NaN | 57.6 M bbl | 57.6 M bbl |
| 2025 | NaN | 83.5 M bbl | 83.5 M bbl |

La diferencia en 2020 se debe a que la fuente vieja tenía datos parciales del año
(probablemente solo hasta septiembre u octubre).

---

## 7. Implementación

El pipeline integra los archivos nuevos en `src/preproc/comex.py`:

- `_load_comex_sesco_new()` — carga y concatena los dos archivos nuevos
- `_extract_crudo_new()` — agrega cantidades y montos de crudo por año
- `_extract_gas_new()` — ídem gas, con detección y corrección de errores de unidad
- Funciones modificadas con parámetro `sesco_new`: `build_expo_crudo()`,
  `build_expo_gas()`, `build_expo_usd_crudo()`, `build_expo_usd_gas()`

Jerarquía de fuentes resultante:

```
expo_crudo :  nuevo SESCO (2010+)  >  viejo SESCO (1999+)  >  Comtrade (<1999)
expo_gas   :  nuevo SESCO (2010+)  >  viejo SESCO           >  MECON
expo_usd_* :  nuevo SESCO (2010+)  >  viejo SESCO           >  INDEC
```

El script de diagnóstico completo está en:
`src/analysis/comex_sesco_unit_correction.py`

Los outputs del análisis se guardan en:
`results/argentina/analisis_comex_sesco/`

---

## 8. Supuestos y limitaciones

- **`monto` como ancla:** se asume que los valores USD (FOB) son más confiables que las
  cantidades físicas. Esta es la hipótesis central de la corrección. Si `monto` también
  fuera incorrecto en los registros outlier, la corrección podría ser errónea.
- **Factor de corrección fijo (1000):** el error m3 ↔ miles/m3 implica exactamente este
  factor. Si existieran errores de otra magnitud (por ejemplo, m3 vs. Mm3, factor 10⁶),
  el threshold de mediana/100 no los capturaría.
- **Crudo sin corrección de unidades:** la detección muestra 38 casos de monto cero pero
  ningún error de unidad clásico, lo que es consistente con que el crudo se reporta en m3
  (unidad directa, sin multiplicador) y su variación de precio es menor.
- **Datos 2026:** es un año incompleto (datos parciales al momento del análisis). Los
  valores anuales de 2026 deben interpretarse como acumulados a la fecha del último
  reporte disponible.
