# Cálculo de la renta de la tierra petrolera y gasífera y sus cursos de apropiación en la Argentina

**Informe técnico Proyecto de Investigación Orientada (PIO) Conicet-YPF 13320140100023CO:** "La apropiación de la renta petrolera diferencial por distintos sujetos sociales en Argentina comparado con Venezuela y Brasil (2002 a la actualidad)"

**Autores:**
* Juan Kornblihtt (Conicet/UNGS)
* Mateo Suster (Conicet/UNGS)
* Fernando Dachevsky (Conicet/IEALC)
* Manuel Casique (CIC-PBA/UNGS)

---

## Resumen
La metodología presentada a continuación está basada en Iñigo Carrera (2007), y su especificidad para la renta petrolera de Dachevsky y Kornblihtt (2011).

---

## 1. Fuentes recopiladas del sector hidrocarburífero

### 1.1 Producción
* **Anuario de Combustibles** (1911-hoy). Archivo: `data/anuario_de_combustibles/Produccion_Desde_1911.xls`
* **Secretaría de Energía - Serie histórica total país desde 1950** (1950-2015). Archivo: `data/secretaria_energia/sesco/serie-produccion-petroleo-total-pais-desde-1950.csv`. Utilizada como fuente principal de crudo entre 1950 y 2015. También disponible serie de gas desde 1950: `data/secretaria_energia/sesco/producciongasnaturaldesde-1950.csv`
* **Secretaría de Energía - SESCO Downstream por yacimiento** (2009-hoy). Archivos: `data/secretaria_energia/sesco/produccin-de-petrleo-anterior-al-2009.csv`, `data/secretaria_energia/sesco/produccin-de-petrleo-por-yacimiento.csv` (crudo); `data/secretaria_energia/sesco/produccin-de-gas-anterior-al-2009.csv`, `data/secretaria_energia/sesco/produccin-de-gas-por-yacimiento.csv` (gas). Fuente principal de gas desde 1993, y de crudo desde 2016.
* **Secretaría de Energía - Regalías** (1998-hoy). Archivos: `data/secretaria_energia/regalias/produccion_crudo_regalias.csv`, `data/secretaria_energia/regalias/produccion_gas_regalias.csv`. Fuente de cotejo.
* **Ministerio de Hacienda - MECON** (base minería e hidrocarburos de cuentas nacionales, mensual). Archivo: `data/mecon/hidrocarburos_produccion.csv` + actualización en `update/hidrocarburos.csv`. Fuente de cotejo.
* **EIA** (producción anual Argentina). Archivos: `data/eia/oil_production_arg.csv` (crudo, Mb/d → barriles anuales); `data/eia/Dry_natural_gas_production_Argentina_Annual.csv` (gas, BCF → miles de m³). Fuente de cotejo.

### 1.2 Precios del mercado interno
* **Ministerio de Hacienda / MECON** (1993-hoy). Precios promedio ponderados por volumen de venta. Archivo histórico: `data/mecon/hidrocarburos_produccion.csv` (sheet indicador[1]); actualización: `update/hidrocarburos.csv`. Fuente principal de crudo desde 1993 y de gas hasta 2021.
* **Secretaría de Energía - Regalías**. Precio del crudo (2006-hoy): `data/secretaria_energia/regalias/precio_mercado_interno_crudo_regalias.csv`; precio del gas (pre-1999): `data/secretaria_energia/regalias/precio_mi_gas.xlsx`; precio del gas (1999-hoy): `data/secretaria_energia/regalias/precio_mercado_interno_gas_regalias.csv`. Fuente principal de gas (1992-2021) y cotejo de crudo.
* **IDEE - Fundación Bariloche** (1970-1988/89). Precio oficial interno del crudo cuenca neuquina. Archivo: `data/idee/Precios del petroleo crudo y derivados 1970 - 1989.xlsx` (sheet 3). Precio de transferencia del gas natural. Archivo: `data/idee/Precios del gas natural y derivados 1970 - 1988.xlsx` (sheet 1). Fuente principal de precios históricos. (Nota: Fuentes originales del IDEE: Secretaría de Energía, YPF, Gas del Estado, Boletín Informativo de Techint y series propias de IDEE).
* **Memorias anuales de YPF** (1963-1992 para crudo; 1963-1988 para gas). Precio promedio calculado como valor total vendido / cantidad vendida en m³, convertido a USD al tipo de cambio de diciembre. Archivos: `data/ypf/vtas_valor_cantidad_precio_crudo.xlsx`, `data/ypf/vtas_valor_cantidad_precio_gas.xlsx`. Fuente principal para crudo 1989-1991.
* **Anuario de Combustibles** (precio histórico del gas). Archivo: `data/anuario_de_combustibles/anuario de combustible.xlsx`. Fuente de cotejo.

### 1.3 Precios de exportación y referencia del mercado mundial

**Crudo:**
* **MECON - Base Minería e Hidrocarburos** (1993-2014, excepto 2002-2003). Precio de exportación en USD/bbl. Archivo: `data/mecon/base-mineria-e-hidrocarburos cuentas nacionales.xls` (sheet "Precios", col. `precio_crudo_me_usd_bbl`).
* **UN Comtrade HS** (2002-2003). Precio de exportación de crudo en USD/bbl. Archivo: `data/un_comtrade/expo_crudo_uncomtrade_hs.csv`.
* **Secretaría de Energía - Regalías** (2015-hoy). Precio de exportación de crudo en USD/m³, convertido a USD/bbl. Archivo: `update/Regalias_CRUDO/Informe Regalias CRUDO.xlsx` (sheet "Tabla precios").
* **UN Comtrade SITC** (pre-1993). Precio de exportación de crudo argentino. Archivo: `data/un_comtrade/expo_crudo_sitc.csv`. Fallback: Brent histórico.
* **EIA - Brent** (1987-hoy). Archivos: `data/precios_mundiales/brent.xlsx` (histórico); `data/eia/RBRTEd.xls` (IEA diario).
* **EIA - WTI** (1986-hoy). Archivos: `data/eia/RWTCd.xls`; `data/fread/WTISPLC.csv` (FRED). Fuente de cotejo.
* **INDEC** (precio promedio anual de exportación). Archivo: `data/indec/precio_anual_promedio_expo_hidro_indec.csv`. Fuente de cotejo.

**Gas:**
* **UN Comtrade - Argentina importa desde Bolivia** (1966-2019, excl. 1994-1997). Precio de referencia del gas en USD/MMBTU. Archivo: `data/un_comtrade/gas_impo_bolivia_comtrade.csv`. Fuente principal.
* **Secretaría de Energía - Regalías** (2020-hoy). Precio de exportación de gas en ARS/Miles de m³, convertido a USD/MMBTU. Archivo: `update/Regalias_GAS/Informe Regalias GAS.xlsx` (sheet "Tabla precios").
* **UN Comtrade - Bolivia exporta a Argentina** (pre-1966, fallback). Archivo: `data/un_comtrade/gas_expo_bolivia_comtrade.csv`.
* **IDEE - Fundación Bariloche** (precio del gas boliviano 1970-1988). Archivo: `data/idee/Precios del gas natural y derivados 1970 - 1988.xlsx` (sheet 2, cuadro 4.3). Deflactado con IPC 1970=1 y convertido a USD/MMBTU.
* **EIA - Henry Hub** (1997-hoy). Precio spot anual. Archivo: `data/eia/RNGWHHDd.xls`. Fuente de cotejo.
* **EIA - Precio gas boca de pozo EEUU**. Archivo: `data/eia/natural_gas_wellhead_price_eeuu.xls`. Fuente de cotejo.
* **EIA - Precios gas EEUU** (7 categorías en USD/MMBTU). Archivo: `data/eia/natural_gas_prices_usa.xls`. Fuente de cotejo.
* **British Petroleum - Statistical Review of World Energy**. Precios en USD/MMBTU. Archivo: `data/bp/bp-stats-review-2020-all-data.xlsx` (sheet "Gas - Prices"). Fuente de cotejo.
* **FMI - Commodity Price Index** (LNG Asia, Gas Natural EU, Henry Hub). Deflactado a precios 2016 vía BP. Archivo: `data/fmi/PCPS_09-16-2020 15-07-10-66_timeSeries.csv`. Fuente de cotejo.
* **YPFB Bolivia** (precio de exportación a Argentina y Brasil). Archivo: `data/ypfb/precio_expo_bolivia.xlsx`. Fuente de cotejo.
* **UN Comtrade - Argentina exporta gas** (pre-1999 para precio de exportación argentino). Archivo: `data/un_comtrade/expo_gas_sitc.csv`. Precio de cotejo.

### 1.4 Exportaciones e Importaciones

**SESCO Downstream** — fuente principal:
* Pre-2010: `data/secretaria_energia/sesco/expo_pre2010.csv`, `data/secretaria_energia/sesco/impo_pre2010.csv`, `data/secretaria_energia/sesco/comex_post2010.csv`.
* 2010-2016: `data/secretaria_energia/sesco/importaciones-exportaciones.csv`.
* 2016-hoy: `data/secretaria_energia/sesco/importaciones-exportaciones-a-partir-del-2016-.csv`.

Prioridad para exportaciones de crudo: SESCO nuevo (2010+) > SESCO viejo (1999+) > UN Comtrade SITC (pre-1999).
Prioridad para exportaciones de gas: SESCO nuevo (2010+) > SESCO viejo > MECON.

**Fuentes de cotejo:**
* **MECON** (Cuentas Nacionales, sheet "Com. exterior"). Archivos: `data/mecon/base-mineria-e-hidrocarburos cuentas nacionales.xls`.
* **INDEC** (cantidades y valores de exportación). Archivos: `data/indec/cantidades_expo_hidro_indec.csv`, `data/indec/expo_hidro_valor.csv`.
* **UN Comtrade SITC** (exportaciones de crudo, pre-1999). Archivo: `data/un_comtrade/expo_crudo_sitc.csv`.

**Valores en USD de exportación:**
* Prioridad para crudo USD: SESCO nuevo > SESCO viejo > INDEC. Archivos ídem. Utilizado para verificación cruzada de renta por sobrevaluación.
* **INDEC - Complejos Exportadores** (1993-hoy). Exportaciones de petróleo y gas en millones de USD. Fuente alternativa para el cálculo de renta por sobrevaluación. Archivos: `data/indec/complejos_exportadores/complejos_exportadores_serie_2002_2025.xlsx`, `data/indec/complejos_exportadores/complexp_variacion_1993_2025.xls`.

### 1.5 Empleo y remuneraciones
* **MECON - Base Minería e Hidrocarburos** (1996-2013). Sheets "Empleo registrado" y "Remuneraciones". Fuente principal para masa salarial de cotejo pre-2014. Archivo: `data/mecon/base-mineria-e-hidrocarburos cuentas nacionales.xls`.
* **Ministerio de Trabajo - OEDE** (1996-hoy). Serie anual de empleo (hoja C 5) y remuneraciones (hoja C 5). Archivos: `data/min_trabajo/nacional_serie_empleo_anual_1.xlsx`, `data/min_trabajo/nacional_serie_remuneraciones_anual_1.xlsx`. Extensión reciente (trimestral/mensual): `data/min_trabajo/nacional_serie_empleo_trimestral_6.xlsx`, `data/min_trabajo/nacional_serie_remuneraciones_mensual_7.xlsx`.
* **CEPAL** (1991). Masa salarial por rama, en australes. Archivo: `data/cepal/cepal_1991.xlsx`. Fuente de cotejo histórica.

### 1.6 Activos
* **Bolsar** (balances de empresas que cotizan en Bolsa). Empresas: YPF, Petrobras, Tecpetrol, Camuzzi Gas Pampeana, Metrogas, entre otras. Sectores: `integrada`, `produccion`, `transporte`, `distribucion`. Archivo: `data/balances/balances_arg.csv`. Para el cálculo del capital adelantado se excluye el segmento de refinación.
* **S&P Capital IQ** vía base Petroarg (empresas que cotizan en mercados internacionales). Empresas: YPF, Petrobras Argentina, PAE, Capex, CGC, Tecpetrol, y otras. Archivos: `update/Petroarg.zip` → `data/balances/petroarg_all_vars.csv`. **Fuente actualmente utilizada por defecto** (parámetro `STOCK_SOURCE = "S&P Capital IQ"`).
* **AFIP - Anuario de estadísticas tributarias**, serie v8 (años fiscales ~2001-2013). KTA = Disponibilidades + Bienes de cambio + Inventarios + Bienes de uso. Archivo: `data/afip/gcia_v8.xlsx`. Sectores: extracción petróleo/gas (CIIU petro) y servicios petroleros (ser_petro).
* **AFIP - Serie Consolidada 2002-2022 v2** (años fiscales 2002-2022). KTA = Disponibilidades + Bienes de cambio + Bienes de uso. Sectores: 061+062 → extracción; 091 → servicios petroleros. Archivo: `update/Serie_AFIP_Consolidada_2002_2022_V2.xlsx` (sheet "activo"). Se combina con la serie v8 generando la fuente "AFIP (combinada)": v8 para años < 2014, nueva para años ≥ 2014.
* **Memorias de YPF** (Betania). Bienes de Uso + Bienes de Cambio + Activo Total + Patrimonio Neto + Utilidades. Archivo: `data/ypf/Calculos Betania Tg.xls` (sheet "YPF_A $HOY_PARADEFLACYCALCULAR"). KTA = PPyE + Bienes de Cambio. Años con datos inválidos anulados: 1983, 1985-1988.
* **Segmentos de YPF y Petrobras** (activos upstream/downstream). Archivos: `data/ypf/ypf_segmentos.csv`, `data/balances/petrobras_arg_segmentos.csv`.

### 1.7 Regalías
* **Secretaría de Energía - Regalías** (1998-hoy). Cuatro productos: crudo (USD), gas (ARS), gasolina (USD), GLP (ARS). Los productos en USD se convierten a ARS por TCC. Los años previos a 1991 se anulan (regalías = 0 antes de la Ley 24.145 de federalización). Archivos: `data/secretaria_energia/regalias/regalias_crudo.csv`, `data/secretaria_energia/regalias/regalias_gas.csv`, `data/secretaria_energia/regalias/regalias_gasolina.csv`, `data/secretaria_energia/regalias/regalias_glp.csv`.

### 1.8 Retenciones
* **AFIP - Anuario de estadísticas tributarias** (1998-hoy). Serie propia de retenciones al complejo hidrocarburífero (JK) y serie BFR en millones de pesos de 2008 deflactada por IPC. Archivo: `data/afip/retenciones.xlsx` (sheets default y "usd").
* **Campodónico Sánchez, H. (2008). Renta petrolera y minera en países seleccionados de América Latina. CEPAL.** Retenciones históricas en millones de USD, convertidas a ARS por TCC. Archivo: `data/afip/retenciones.xlsx` (sheet "usd", columna `retenciones_hg`).

### 1.9 Subsidios
* **EJES / Zannotti et al. (2017)**. Subsidios a hidrocarburos en millones de USD, convertidos a ARS por TCC. Archivo: `data/ejes/subsidios.xlsx`.
* **CEFIP / Alberto Porto et al. (2021)**. Subsidios como porcentaje del PBI (Plan Gas + Subsidios FF GN y GLP), convertidos a ARS corrientes. Archivo: `data/cefip/subsidios.xlsx`.
* **ACIJ - Base de datos de petroleras en Argentina** (datos por empresa, en pesos constantes de diciembre 2024). Convertidos a pesos corrientes por IPC (base 2024=1). Archivo: `update/Base de datos de petroleras en Argentina.xlsx` (sheet "Base de datos"). Fuente utilizada para años ≥ 2013.

**Criterio de uso:** CEFIP para años ≤ 2012; ACIJ para años ≥ 2013.

### 1.10 Fuentes complementarias
* **Índice de precios al consumidor de Argentina**. Serie mensual base julio 2003 = 1, extendida con variaciones de `update/TCP_me (2).xlsx` hasta el año actual. Archivo base: `data/indices/ipc_mensual_1963_2018.xlsx`.
* **Tipo de cambio comercial (TCC) y de paridad (TCP)**. Serie histórica hasta 1990: `data/tcp/tcc_tcp_historico.xlsx`; 1991-hoy: `data/tcp/tcp_anual.xlsx`.
* **Conversores de moneda** (m$n, $Ley, $Arg, Austral → ARS). Archivo: `data/conversores/conversor_peso.xlsx`.
* **IPIM/IPIB/IPP** (base 1993=100, series históricas 19xx). Archivo: `data/indec/sipm-serie56-95.xls`. Utilizado para estimar precio interno del crudo en 1992.
* **PBI y Ganancia de economía** (Millones de pesos corrientes, 1960-hoy). Archivos: `data/ccnn/ganancia y pbi.xlsx`; extensión: `update/TG General. 1993 - 2021. 18102022 (5).xlsx` (sheet "TG").
* **Tasa de ganancia industrial de referencia** (dos series: JIC pre-1993, EM post-1993). Archivo: `data/ccnn/tg_industrial.csv`.
* **Índice de precios al consumidor de Estados Unidos**. Fuente: BLS. Base 2020 = 1. Archivo: `data/bls/CPIAUCSL.csv`.
* **Coeficiente técnico de la Matriz Insumo Producto 1997** (filas 140 y 149 relativas al sector Extracción de Minas). Archivo: `data/mip/mip_matriz12.xls`.
* **Proporción del VBP de servicios en extracción** (COU 2006-2016). Archivo: `data/mip/sh_cou_06_16.xls`.
* **Cuentas Nacionales INDEC** (VBP y VA sector extracción petróleo, 2004-hoy). Archivo: `data/indec/sh_VBP_VAB_03_26.xls` (sheets 2 y 4: VBP y VA total, filtrado por "Extracción de petróleo"). Fuente principal desde 2004.
* **Cuentas Nacionales MECON base 1993** (VBP y VA minería, 1993-2007). Archivo: `data/mecon/PBI_Base 1993_PM.xlsx` (sheets "VBP c", "VAB c"). Usada para coeficiente de CI pre-2004.
* **Estimaciones de renta de otros autores** (para comparación). Archivo: `data/otros autores/renta_autores.csv`.

---

## 2. Fuentes seleccionadas para la construcción de series

### 2.1 Producción y Exportaciones de crudo
* **Producción (1911-1949):** Anuario de Combustibles
* **Producción (1950-2015):** Secretaría de Energía — serie histórica total país desde 1950
* **Producción (2016-actualidad):** SESCO Downstream — por yacimiento (suma de producción primaria + secundaria + recuperación asistida)
* **Exportaciones (pre-1999):** UN Comtrade SITC (as reported)
* **Exportaciones (1999-2009):** SESCO Downstream — formato pre-2010
* **Exportaciones (2010-actualidad):** SESCO Downstream — nuevo formato (`importaciones-exportaciones.csv` + `importaciones-exportaciones-a-partir-del-2016-.csv`), con corrección de errores de unidad en gas

### 2.2 Precios de crudo (Mercado Interno)
* **Interno (1963-1965):** IDEE estimado — valor IDEE 1972 escalado por cociente YPF 1963-1972 / YPF 1972
* **Interno (1966-1988):** IDEE (Kozulj y Pistonesi) — precio crudo cuenca neuquina a tipo de cambio oficial
* **Interno (1989-1991):** Memorias anuales de YPF — valor total vendido / cantidad vendida en m³, a TCC diciembre
* **Interno (1992):** MECON 1994 × índice IPIM relativo a 1994 (base 1994 = 1)
* **Interno (1993-actualidad):** MECON — promedio ponderado por volumen de venta (USD/m³ → USD/bbl)

### 2.3 Precios de crudo (Mercado Externo / Referencia mundial)
* **Externo (1993-2001 y 2004-2014):** MECON — precio de exportación en USD/bbl
* **Externo (2002-2003):** UN Comtrade HS — precio de exportación
* **Externo (2015-actualidad):** Secretaría de Energía Regalías — precio de exportación en USD/m³ → USD/bbl
* **Externo (pre-1993):** UN Comtrade SITC — precio de exportación; donde no disponible: Brent histórico

### 2.4 Producción y Exportaciones de gas natural
* **Producción (1911-1992):** Anuario de Combustibles
* **Producción (1993-actualidad):** SESCO Downstream (por yacimiento; anterior a 2009: pre-file; posterior a 2009: post-file). Se excluye el concepto "gas no hidrocarburífero" (idconcepto=4 / idconcepto ∉ {1,2,3}).
* **Exportaciones (pre-2010):** SESCO — formato pre-2010 (`expo_pre2010.csv`)
* **Exportaciones (2010-actualidad):** SESCO — nuevo formato, con prioridad al archivo post-2016

### 2.5 Precios de gas natural (Mercado Interno)
* **Interno (1970-1988):** IDEE (Kozulj y Pistonesi) — precio de transferencia en pesos de 1970, deflactado con IPC 1970=1, convertido a ARS corrientes y luego a USD/MMBTU
* **Interno (1992-2021):** Secretaría de Energía - Regalías — precio promedio ponderado por cuenca (ARS/Miles de m³ → ARS/MMBTU → USD/MMBTU)
* **Interno (2022-actualidad):** MECON — promedio ponderado por volumen de venta (ARS/Miles de m³)

### 2.6 Precios de gas natural (Mercado Externo / Referencia mundial)
* **Externo (1966-2019):** UN Comtrade — precio de importación de gas desde Bolivia (USD/m³ → USD/MMBTU). Se excluyen 1994-1997 por datos atípicos.
* **Externo (2020-actualidad):** Secretaría de Energía - Regalías — precio de exportación (ARS/Miles de m³ → USD/MMBTU)
* **Externo (pre-1966, fallback):** UN Comtrade — precio de exportación de Bolivia a Argentina

**Precio de exportación argentino de gas:**
* Pre-1999: UN Comtrade SITC (precio de exportación de gas argentino)
* 1999-actualidad: Secretaría de Energía - Regalías

### 2.7 Variables Laborales
* **Masa salarial (1996-2013):** Calculada como Salario promedio × Empleo × 13, a partir de MECON CCNN (sheets "Remuneraciones" y "Empleo registrado")
* **Masa salarial (1996-actualidad):** Calculada como Salario promedio × Empleo × 13, a partir de Min. Trabajo OEDE (anual + extensión trimestral/mensual). Fuente principal.
* **Coeficiente de masa salarial (pre-1996):** Se aplica el coeficiente promedio MS/VBP calculado con datos MECON-CCNN al VBP estimado con precios propios.

### 2.8 Capital Fijo (Stock)
* **Consumo de Capital Fijo:** Tasa de depreciación promedio histórica estimada como media de (Depreciaciones / PPyE) sobre balances de YPF (fuente Bolsar). Aplicada al stock PPyE del año correspondiente.
* **Stock PPyE — fuente seleccionada (parámetro `STOCK_SOURCE`):**
  - `"S&P Capital IQ"` (por defecto): balances de Petroarg, sectores `integrada` + `produccion`
  - `"Bolsar"`: balances Bolsar, sectores `integrada` + `produccion`
  - `"AFIP (v8)"`: serie AFIP histórica, PPyE (Bienes de Uso), extracción + servicios
  - `"AFIP (nuevo)"`: serie AFIP consolidada 2002-2022, extracción + servicios
  - `"AFIP (combinada)"`: v8 para < 2014; nueva para ≥ 2014

---

## 3. Criterios de cómputo

### 3.1 Valor total de la producción
Se presentan cuatro estimaciones del valor producido:

* **`CCNN oficial`**: VBP y VA oficiales de INDEC Cuentas Nacionales (2004+), sector "Extracción de petróleo" ajustado por proporción de servicios de apoyo.
* **`Criterio CCNN`**: VBP estimado con precios del mercado interno y externo (criterio propio de precios) y cantidades vendidas según destino, a TCC. Estructura de CI y MS a partir de coeficientes técnicos.
* **`Empalme CCNN`**: Serie empalmada: 2004+ desde INDEC; pre-2004 extrapolada con el índice del Criterio CCNN anclado en el valor INDEC de 2004.
* **`Criterio propio`**: VBP estimado con precios internacionales de referencia (Pext × Q_total × TCP).

#### 3.1.1 Formulación Matemática

**Valor Bruto de Producción (Criterio propio):**
$$VBP_{PextTCP} = (Pext_{petroleo} \times Q_{petroleo} + Pext_{gas} \times Q_{gas}) \times TCP$$

**Valor Bruto de Producción (Criterio CCNN — con TCC):**
$$VBP_{CCNN} = (Pint_{petroleo} \times QMInt_{petroleo} + Pext_{petroleo}^{AR} \times Expo_{petroleo} + Pint_{gas} \times QMInt_{gas} + Pext_{gas}^{AR} \times Expo_{gas}) \times TCC$$

donde $Pext_{petroleo}^{AR}$ y $Pext_{gas}^{AR}$ son los precios de exportación argentinos (≠ precio de referencia mundial).

**VBP de extracción pura y proporción de servicios:**
$$VBP_{extr} = VBP_{tot} \times (1 - prop_{servicios})$$
$$prop_{servicios} = \frac{VBP_{serv\_COU}}{VBP_{extr\_COU} + VBP_{serv\_COU}}$$

calculado sobre el COU 2006-2016 (archivo `data/mip/sh_cou_06_16.xls`).

| Variable | Descripción |
|---|---|
| $VBP_{PextTCP}$ | Valor Bruto de la Producción total (criterio propio) |
| $VBP_{CCNN}$ | Valor Bruto de la Producción total (criterio CCNN) |
| $VBP_{extr}$ | Valor Bruto de la Producción de extracción pura |
| $Pext$ / $Pext^{AR}$ | Precio de referencia mundial / Precio de exportación argentino |
| $Pint$ | Precio del mercado interno |
| $Q$ / $QMInt$ / $Expo$ | Cantidad total producida / Vendida en mercado interno / Exportada |
| $TCP$ / $TCC$ | Tipo de Cambio de Paridad / Tipo de Cambio Comercial |
| $prop_{servicios}$ | Proporción del VBP de servicios sobre VBP total extracción+servicios |

**Consumo Intermedio:**
$$CI_{tot} = VBP_{tot} \times Coef_{CI}$$
$$CI_{extr} = VBP_{extr} \times Coef_{CI}$$

donde $Coef_{CI}$ se construye: para años ≥ 2004, de INDEC CCNN ($1 - VA/VBP$); para años < 2004, de la base MECON 1993 indexada al valor de $Coef_{CI}$ del año 2004.

| Variable | Descripción |
|---|---|
| $Coef_{CI}$ | Coeficiente técnico de Consumo Intermedio (construido como $1 - VA/VBP$) |

**Masa Salarial:**
$$MS = W \times Emp \times 13$$
$$MS_{extr} = VBP_{extr} \times Coef_{MS}^{extr}$$

donde $Coef_{MS}^{extr}$ es el cociente promedio histórico $MS_{extr}/VBP_{extr}$ (calculado sobre MECON CCNN disponible).

**Excedente Bruto de Explotación (EBE):**
$$EBE_{tot} = VA_{tot} - MS_{tot}$$
$$EBE_{extr} = VA_{extr} - MS_{extr}$$

**Consumo de Capital Fijo y Plusvalía Neta:**
$$ConKfijo = PPyE \times \overline{\left(\frac{Dep}{PPyE}\right)}_{YPF}$$
$$PV_{extr} = EBE_{extr} - ConKfijo - VBP_{extr} \times Coef_{Imp}$$

donde $Coef_{Imp}$ es el coeficiente promedio de impuestos genéricos de la MIP 1997 (filas 140/149 del archivo `data/mip/mip_matriz12.xls`).

| Variable | Descripción |
|---|---|
| $PPyE$ / $Dep$ | Propiedad, Planta y Equipo neta / Depreciaciones (Balances YPF - Bolsar) |
| $\overline{(Dep/PPyE)}_{YPF}$ | Tasa de depreciación promedio histórica de YPF |
| $PV_{extr}$ | Plusvalía (Excedente Neto de Explotación del sector extracción) |
| $Coef_{Imp}$ | Coeficiente de impuestos genéricos (MIP 1997) |

---

### 3.2 Tasa de ganancia por rama

**Capital Total Adelantado ($KTA$):**
* **S&P Capital IQ (Petroarg):** PPyE (Property, Plant & Equipment neta) por sector `integrada` y `produccion`. *(Fuente por defecto).*
* **Bolsar:** PPyE neta + Inventarios (sectores `integrada` y `produccion`).
* **AFIP:** Bienes de Uso + Bienes de Cambio + Disponibilidades.
* **Memoria YPF:** Bienes de Uso + Bienes de Cambio.

**Tasa de Ganancia de la Rama:**
$$TG_{rama} = \frac{PV_{extr}^{criterio\ propio}}{PPyE_{seleccionada}}$$

donde $PV_{extr} = EBE_{extr} - ConKfijo - VBP_{extr} \times Coef_{Imp}$ es la plusvalía neta del sector extracción bajo criterio propio.

**Renta apropiada por empresas (vía tasa de ganancia):**
$$RTPG_{empresas} = PPyE \times (TG_{rama} - TG_{referencia}) = PV_{extr} - PPyE \times TG_{referencia}$$

donde $TG_{referencia}$ es la tasa de ganancia de la economía general (combinación JIC pre-1993 / EM post-1993, serie `tg_industrial.csv`).

Esta formulación garantiza coherencia con el método directo: $RTPG_{empresas} = RTPG_{total}^{A} + Subsidios$ (ya que $RTPG_{total}^{A} = PV_{extr} - PPyE \times TG_{ref} - Subsidios$).

---

### 3.3 Renta por el diferencial de precios interno/externo

$$RTPG_{dif\_precios} = ProdMdoInt \times Pext \times TCP - ProdMdoInt \times Pint \times TCC$$
$$ProdMdoInt = Q - Expo$$

donde $Q$ es la producción total y $Expo$ son las exportaciones. (Nota: no se incluye el ajuste por variación de existencias $E_{BOE}$ por falta de datos sistemáticos.)

Para crudo: $Pext$ = precio de exportación/referencia (USD/bbl); $Pint$ = precio interno (USD/bbl).
Para gas: $Pint$ se convierte previamente de ARS/MMBTU a USD/MMBTU dividiendo por TCC.

---

### 3.4 Renta apropiada por sobrevaluación cambiaria

**Fuente SESCO (por defecto, `RENTA_SV_SOURCE = "sesco"`):**
$$RTPG_{sv\_crudo} = Expo_{crudo} \times Pext_{crudo} \times (TCP - TCC)$$
$$RTPG_{sv\_gas} = Expo_{gas} \times Pext_{gas} \times (TCP - TCC)$$

**Fuente INDEC Complejos Exportadores (alternativa, `RENTA_SV_SOURCE = "indec"`):**
$$RTPG_{sv\_indec} = Expo_{USD}^{INDEC} \times 10^6 \times (TCP - TCC)$$

donde $Expo_{USD}^{INDEC}$ son los valores en millones de USD de INDEC Complejos Exportadores. Para años 2002+, se desagregan petróleo y gas; para 1993-2001, solo el valor combinado (colocado en la columna de petróleo). Para años previos a la cobertura INDEC, se utiliza como fallback la estimación SESCO.

---

### 3.5 Renta apropiada por el Estado mediante impuestos específicos

$$RTPG_{imp} = Retenciones + Regalías - Subsidios$$

Fuentes y periodicidad:
* **Retenciones:** AFIP - serie JK (archivo `data/afip/retenciones.xlsx`, columna `retenciones_crudo_jk`).
* **Regalías:** Secretaría de Energía (4 productos), anuladas en años < 1991.
* **Subsidios:** CEFIP para años ≤ 2012; ACIJ para años ≥ 2013.

---

### 3.6 Renta Hidrocarburífera Total

**Método A — Directo (descuento de ganancia normal):**
$$RTPG_{total}^{A} = PV_{extr} - PPyE \times TG_{referencia} - Subsidios$$

donde $PV_{extr}$ es el excedente neto de explotación (tras depreciation e impuestos genéricos) del sector extracción en criterio propio. Se calculan también las proporciones $RTPG/Ganancia$ y $RTPG/PBI$ como referencias de magnitud.

**Método B — Indirecto (suma de mecanismos):**
$$RTPG_{total}^{B} = RTPG_{dif\_crudo} + RTPG_{dif\_gas} + RTPG_{sv\_crudo} + RTPG_{sv\_gas} + RTPG_{empresas} + Regalías + Retenciones - Subsidios$$

(con $RTPG_{sv}$ proveniente de SESCO o INDEC según `RENTA_SV_SOURCE`)

Todas las componentes se expresan en Millones de pesos corrientes. Se calcula también la renta en USD (TCC y TCP), la proporción sobre PBI y sobre la Ganancia de la economía.

---

### 3.7 Costos y Precios de Producción/Venta

$$Costos_{totales} = CI_{extr} + MS_{extr} + ConKfijo$$
$$Costos_{totales\_con\_gcia} = Costos_{totales} + PPyE \times TG_{referencia}$$
$$P_{costo} = \frac{Costos_{totales}}{Q_{total}}$$
$$P_{produccion} = \frac{Costos_{totales\_con\_gcia}}{Q_{total}}$$
$$P_{venta\_potencial} = \frac{Q_{total} \times P_{ext\_crudo} - Costos_{totales}}{Q_{total}}$$

donde $CI_{extr}$ y $MS_{extr}$ provienen del Empalme CCNN (en USD TCC), $ConKfijo$ del stock Bolsar/fuente seleccionada, y $Q_{total}$ es la producción total en BEP. Los precios resultan en USD/boe.

---

## 4. Estimaciones alternativas de comparación
* Barrera, M. (2013). Beneficios extraordinarios y renta petrolera en el mercado hidrocarburífero argentino. *Desarrollo Económico*, 53(209/210), 169-194.
* Campodónico Sánchez, H. (2008). Renta petrolera y minera en países seleccionados de América Latina. CEPAL. Serie Documentos de Proyectos No. 188.
* Mansilla, D. (2006). Una aproximación al problema de la renta petrolera en la Argentina (1996-2005). *Realidad Económica*, 223, 11-23.
* Ramón, M. (2019). La renta del sector Hidrocarburífero argentino entre los años 2010 y 2015. *Revista Economía y Desafíos del Desarrollo*. Año 2, Volumen I, Número 4.
* Scheimberg, S. (2007). Experiencia reciente y desafíos para la generación de renta petrolera aguas arriba en la Argentina. CEPAL.

## 5. Bibliografía
* Dachevsky, F., y Kornblihtt, J. (2011). "Aproximación a los problemas metodológicos de la medición de la tasa de ganancia y la renta de la tierra petrolera". Documentos de Jóvenes Investigadores.
* Iñigo Carrera, Juan (2007). "La formación económica de la sociedad argentina. Volumen 1: Renta agraria, ganancia industrial y deuda externa. 1882-2004". Imago Mundi, Buenos Aires.
* Zannotti, G. et al. (2017). Ganadores y perdedores en la Argentina de los hidrocarburos no convencionales. Taller Ecologista Rosario y Observatorio Petrolero Sur en EJES, Argentina.
* Porto, A. et al. (2021). "Precios y tarifas y política económica Argentina: 1945-2019". UNLP.

---

## 6. Resumen de fuentes por función

El proyecto recopila datos de **26 fuentes institucionales distintas**, distribuidas según su rol en el cálculo:

### Fuentes principales (usadas en los cálculos centrales)

| # | Institución | Qué aporta |
|---|---|---|
| 1 | **Secretaría de Energía – SESCO** | Producción, expo/impo, regalías, precios MI gas |
| 2 | **MECON / Ministerio de Hacienda** | Precios MI crudo, masa salarial, cuentas nacionales |
| 3 | **Anuario de Combustibles** | Producción histórica crudo y gas (1911–1949/1992) |
| 4 | **EIA (US Energy Information Administration)** | Brent, WTI, Henry Hub |
| 5 | **UN Comtrade** | Exportaciones/importaciones y precios crudo/gas (históricos e internacionales) |
| 6 | **IDEE / Fundación Bariloche** | Precios internos crudo y gas 1970–1988 (Kozulj & Pistonesi) |
| 7 | **Memorias anuales de YPF** | Precios MI crudo 1989–1991; activos históricos (Betania) |
| 8 | **Ministerio de Trabajo – OEDE** | Empleo y remuneraciones 1996–hoy |
| 9 | **AFIP** | Capital adelantado (KTA/PPyE) y retenciones |
| 10 | **Bolsar** | Balances de empresas que cotizan en bolsa local |
| 11 | **S&P Capital IQ / Petroarg** | Balances de empresas (fuente por defecto para stock PPyE) |
| 12 | **INDEC** | Cuentas Nacionales (VBP, VA), Complejos Exportadores, IPIM |
| 13 | **BLS (US Bureau of Labor Statistics)** | IPC EEUU para conversiones a dólares constantes |
| 14 | **Matriz Insumo-Producto 1997 + COU 2006–2016** | Coeficientes técnicos (CI/VBP, servicios/extracción) |
| 15 | **Tasa de ganancia industrial** | Serie JIC (pre-1993) + EM (post-1993) como tasa de referencia |

### Fuentes de subsidios (combinadas por período)

| # | Institución | Período |
|---|---|---|
| 16 | **EJES / Zannotti et al.** | Subsidios históricos en USD |
| 17 | **CEFIP / Porto et al.** | Subsidios ≤ 2012 |
| 18 | **ACIJ** | Subsidios ≥ 2013 |

### Fuentes de cotejo y verificación cruzada

| # | Institución | Qué verifica |
|---|---|---|
| 19 | **British Petroleum Statistical Review** | Precios gas mundial |
| 20 | **FMI – Commodity Price Index** | LNG Asia, Gas EU, Henry Hub |
| 21 | **YPFB Bolivia** | Precios de exportación de gas boliviano |
| 22 | **CEPAL** | Masa salarial por rama 1991 |
| 23 | **Campodónico Sánchez / CEPAL (2008)** | Retenciones históricas en USD |
| 24 | **INDEC – Complejos Exportadores** | Alternativa para renta por sobrevaluación |
| 25 | **FRED (St. Louis Fed)** | Serie WTI como cotejo de precio del crudo |
| 26 | **Otros autores** (`data/otros autores/renta_autores.csv`) | Comparación de estimaciones de renta |
