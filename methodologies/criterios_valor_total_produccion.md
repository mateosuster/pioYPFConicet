# 3. Criterios de Cómputo

## 3.1 Valor Total de la Producción
Se presentan a continuación distintas estimaciones sobre la magnitud de riqueza presente en el sector hidrocarburífero: Valor Bruto y Agregado de Producción (VBP y VA), Consumo Intermedio (CI), Masa Salarial (MS) y Excedente Bruto de Explotación (EBE). 

* **Valor Bruto de Producción (VBP):** Surge de la valuación de la producción a sus precios correspondientes.
* **Valor Agregado (VA):** Resulta de la diferencia entre el VBP y CI. Puede surgir originalmente de esta resta o a partir del coeficiente técnico de la Matriz Insumo Producto (MIP).
* **Excedente Bruto de Explotación (EBE):** Constituye la plusvalía (PV) total de la rama (renta de la tierra más la ganancia normal). Se obtiene tras descontar la MS y los impuestos genéricos (Imp) del VA.
* **Impuestos (Imp):** En todos los casos, se calcularon aplicando sobre el VBP un coeficiente resultante del peso de los impuestos promedio de la MIP de 1997.
* **Depreciación / Consumo de Capital Fijo (ConsKfijo):** Se obtiene aplicando la tasa de depreciación promedio resultante de los balances de YPF (1998-2018) sobre el total de Propiedad, Planta y Equipo (PPyE) de la rama. Esta partida se aplica para obtener el Excedente Neto de Explotación.

### Enfoques y Metodologías de Estimación

| Enfoque / Metodología | Criterio de Cálculo y Variables Incluidas |
| :--- | :--- |
| **CCNN** *(Valores oficiales)* | • El **CI** se estima como la diferencia entre las series oficiales de VBP y VA.<br>• El VBP se separa descontando la proporción de servicios de apoyo (10,7%) extraída del Cuadro de Utilización de Oferta (**COU 2004 de INDEC**) para obtener el VBP neto de extracción.<br>• La **MS** se obtiene del producto entre empleo y salario promedio. Se elaboró un coeficiente promedio de la proporción MS/VBP para uso posterior. |
| **Estimación Propia con Criterio CCNN** | • **VBP:** Valúa la producción del mercado interno (producción menos exportaciones) con precios internos, y las exportaciones con precios de exportación, usando el Tipo de Cambio Comercial (**TCC**). El VBP de extracción se netea de servicios (10,7%).<br>• **CI:** Aplicación del coeficiente técnico (ratio CI/VBP) de la MIP 1997 (equivalente a **0,272**).<br>• **MS:** Se aplica el coeficiente MS/VBP mencionado en el enfoque CCNN.<br>• **VA y EBE:** Calculados por diferencia matemática estándar. |
| **Empalme CCNN** | • Toma valores oficiales de cuentas nacionales para el período disponible (2004-2012).<br>• Imputa los datos faltantes mediante la evolución del índice del VBP propio con criterio CCNN.<br>• Utiliza la **MS** oficial disponible (1996-2018) e imputa los años restantes con el valor propio estimado con criterio CCNN. |
| **Valor a Precio Exterior por TCP ($VBP\_PextTCP$)** | • Refleja la riqueza total del sector valuando el 100% de la producción a precios externos o de referencia internacional y con el Tipo de Cambio de Paridad (**TCP**).<br>• Las variables **totales** (`va_tot`, `ebe_tot`) usan `CI_tot` y `MS_tot` del sector completo. El `EBE_tot` es neto de impuestos por diseño.<br>• Las variables de **extracción** (`vbp_extr`, `va_extr`, `ebe_extr`) usan `CI_extr` y `MS_extr` tomados de la serie de *Empalme CCNN*.<br>• La **PV** se calcula como `EBE_tot - ConKfijo` (Imp ya incluidos en EBE). |

---

## 3.1.1 Formulación Matemática

Las fórmulas descritas a continuación modelan matemáticamente los criterios de cómputo detallados en la sección anterior.

### 1. Valor Bruto de Producción (VBP)

#### Valor Bruto de Producción total (Estimación con criterio propio - $VBP\_PextTCP$)
* **Fórmula:**
  $$\text{VBP\_PextTCP} = (\text{Pext\_petroleo} \times \text{Q\_petroleo} + \text{Pext\_gas} \times \text{Q\_gas}) \times \text{TCP}$$

* **Variables:**
  * `VBP_PextTCP`: Valor Bruto de la Producción total, estimación propia a precios internacionales.
  * `Pext_petroleo`: Precio de exportación o referencia internacional del petróleo crudo.
  * `Pext_gas`: Precio de exportación o referencia internacional del gas natural.
  * `Q_petroleo`: Cantidades producidas totales de petróleo crudo.
  * `Q_gas`: Cantidades producidas totales de gas natural.
  * `TCP`: Tipo de Cambio de Paridad (capacidad real de compra).

#### Valor Bruto de Producción total (Estimación con criterio CCNN)
* **Fórmula:**
  $$\text{VBP\_CCNN} = (\text{Pint\_petroleo} \times \text{QMInt\_petroleo} + \text{Pext\_petroleo} \times \text{Expo\_petroleo} + \text{Pint\_gas} \times \text{QMInt\_gas} + \text{Pext\_gas} \times \text{Expo\_gas}) \times \text{TCC}$$

* **Variables:**
  * `VBP_CCNN`: Valor Bruto de la Producción total, criterio de las Cuentas Nacionales.
  * `Pint_petroleo`: Precio mercado interno del petróleo crudo.
  * `Pint_gas`: Precio mercado interno del gas natural.
  * `QMInt_petroleo`: Cantidades vendidas al mercado interno de petróleo crudo.
  * `QMInt_gas`: Cantidades vendidas al mercado interno del gas natural.
  * `Expo_petroleo`: Exportaciones de petróleo crudo.
  * `Expo_gas`: Exportaciones de gas natural.
  * `TCC`: Tipo de Cambio Comercial.

#### Valor Bruto de Producción extracción (Estimación con criterio CCNN)
* **Fórmula:**
  $$\text{VBP\_extr\_CCNN} = \text{VBP\_CCNN} \times (1 - \text{prop\_servicios})$$

* **Variables:**
  * `VBP_extr_CCNN`: Valor Bruto de la Producción extracción, deduciendo los servicios de apoyo.
  * `VBP_CCNN`: Valor Bruto de la Producción total, criterio de las CCNN.
  * `prop_servicios`: Proporción del VBP de servicios de apoyo sobre el total de extracción (equivalente al 10,7% o 0,107 según COU 2004).

#### Proporción de los servicios de apoyo sobre la extracción de petróleo y gas
* **Fórmula:**
  $$\text{prop\_servicios} = \frac{\text{VBP\_serv\_COU}}{\text{VBP\_extr\_COU} + \text{VBP\_serv\_COU}}$$

* **Variables:**
  * `prop_servicios`: Ratio o ponderador de servicios de apoyo.
  * `VBP_serv_COU`: VBP de servicios de apoyo del Cuadro de Utilización de Oferta.
  * `VBP_extr_COU`: VBP de extracción de petróleo y gas del Cuadro de Utilización de Oferta.

---

### 2. Consumo Intermedio (CI)

#### Consumo Intermedio (Valores oficiales de las CCNN)
* **Fórmula:**
  $$\text{CI\_CCNN} = \text{VBP\_CCNN} - \text{VA\_CCNN}$$

* **Variables:**
  * `CI_CCNN`: Consumo Intermedio total de las CCNN obtenido por residuo.
  * `VBP_CCNN`: Valor Bruto de la Producción total oficial.
  * `VA_CCNN`: Valor Agregado oficial de las CCNN.

#### Consumo Intermedio (Estimación con criterio CCNN)
* **Fórmula:**
  $$\text{CI\_CCNN} = \text{VBP\_CCNN} \times \text{Coef\_tec}$$

* **Variables:**
  * `Coef_tec`: Coeficiente técnico de la Matriz Insumo Producto de 1997 (fijado en 0,272).

#### Consumo Intermedio de extracción (Estimación con criterio CCNN)
* **Fórmula:**
  $$\text{CI\_extr\_CCNN} = \text{VBP\_extr\_CCNN} \times \text{Coef\_tec}$$

* **Variables:**
  * `CI_extr_CCNN`: Consumo Intermedio imputado exclusivamente al sector extracción.
  * `VBP_extr_CCNN`: Valor Bruto de la Producción extracción.

---

### 3. Masa Salarial (MS)

#### Masa Salarial (Valores oficiales de las CCNN)
* **Fórmula:**
  $$\text{MS} = \text{W} \times \text{Emp} \times 13$$

* **Variables:**
  * `MS`: Masa Salarial bruta anualizada.
  * `W`: Salario mensual promedio del sector.
  * `Emp`: Empleo total (puestos de trabajo).
  * `13`: Factor de anualización que incluye el Sueldo Anual Complementario (Aguinaldo).

#### Masa Salarial (Estimación con criterio CCNN)
* **Fórmula:**
  $$\text{MS} = \text{VBP\_CCNN} \times \text{Coef\_MS}$$

* **Variables:**
  * `Coef_MS`: Coeficiente de la proporción histórica promedio de la MS sobre el VBP.

#### Masa Salarial de extracción (Estimación con criterio CCNN)
* **Fórmula:**
  $$\text{MS\_extr} = \text{VBP\_extr\_CCNN} \times \text{Coef\_MS}$$

---

### 4. Valor Agregado (VA)

#### Valor Agregado (Estimación con criterio CCNN)
* **Fórmula:**
  $$\text{VA\_CCNN} = \text{VBP\_CCNN} - \text{CI\_CCNN}$$

#### Valor Agregado de extracción (Estimación con criterio CCNN)
* **Fórmula:**
  $$\text{VA\_extr\_CCNN} = \text{VBP\_extr\_CCNN} - \text{CI\_extr\_CCNN}$$

#### Valor Agregado total (Estimación con criterio propio)
* **Fórmula:**
  $$\text{VA\_tot\_propia} = \text{VBP\_PextTCP} - \text{CI\_tot\_empalme}$$

* **Nota:** `CI_tot_empalme` es el consumo intermedio total (extracción + servicios) tomado de la serie *Empalme CCNN*.

#### Valor Agregado de extracción (Estimación con criterio propio)
* **Fórmula:**
  $$\text{VA\_extr\_propia} = \text{VBP\_extr\_propia} - \text{CI\_extr\_empalme}$$

* **Nota:** `VBP_extr_propia = VBP_PextTCP × (1 − prop\_servicios)`. Los valores de `CI_extr` se toman de la serie *Empalme CCNN* por representar transacciones del mercado interno.

---

### 5. Excedente Bruto de Explotación (EBE)

#### Excedente Bruto de Explotación (Estimación con criterio CCNN)
* **Fórmula:**
  $$\text{EBE\_CCNN} = \text{VA\_CCNN} - \text{MS}$$

#### Excedente Bruto de Explotación de extracción (Estimación con criterio CCNN)
* **Fórmula:**
  $$\text{EBE\_extr\_CCNN} = \text{VA\_extr\_CCNN} - \text{MS\_extr}$$

#### Excedente Bruto de Explotación total (Estimación con criterio propio)
* **Fórmula:**
  $$\text{EBE\_tot\_propia} = \text{VA\_tot\_propia} - \text{MS\_tot} - \text{Imp}$$

* **Nota:** El EBE total en este criterio es un **EBE neto de impuestos** por diseño (a diferencia de los criterios CCNN donde los Imp solo se deducen al calcular la PV). `VA_tot_propia = VBP\_PextTCP - CI\_tot` y `MS\_tot` corresponde a la masa salarial del sector completo (extracción + servicios de apoyo).

#### Excedente Bruto de Explotación de extracción (Estimación con criterio propio)
* **Fórmula:**
  $$\text{EBE\_extr\_propia} = \text{VA\_extr\_propia} - \text{MS\_extr}$$

* **Nota:** Los valores de `CI\_extr` y `MS\_extr` utilizados para el cálculo de las variables de extracción se toman de la serie *Empalme CCNN*.

---

### 6. Depreciación y Plusvalía (Excedente Neto de Explotación)

#### Consumo de Capital Fijo
* **Fórmula:**
  $$\text{ConKfijo} = \text{PPyE} \times \text{prom}\left(\frac{\text{Dep}}{\text{PPyE}}\right)$$

* **Variables:**
  * `ConKfijo`: Consumo de Capital Fijo (depreciación económica de la rama).
  * `PPyE`: Valor neto de Propiedad, Planta y Equipo de la rama hidrocarburífera.
  * `prom(Dep/PPyE)`: Tasa de depreciación promedio calculada a partir de los balances históricos de YPF (periodo 1998-2018).
  * `Dep`: Depreciaciones contables declaradas en los estados financieros.

#### Plusvalía / Excedente Neto de Explotación (criterios CCNN, Estimación CCNN y Empalme CCNN)
* **Fórmula:**
  $$\text{PV} = \text{EBE\_extr} - \text{ConKfijo} - \text{Imp}$$

* **Variables:**
  * `Imp`: estimados aplicando el coeficiente promedio de impuestos de la MIP 1997 sobre el VBP total (`vbp_tot × coef_imp_97`).

#### Plusvalía / Excedente Neto de Explotación (Estimación con criterio propio)
* **Fórmula:**
  $$\text{PV\_propia} = \text{EBE\_tot\_propia} - \text{ConKfijo}$$

* **Nota:** Los impuestos ya están descontados dentro de `EBE\_tot\_propia`, por lo que no se restan nuevamente aquí.

* **Variables:**
  * `PV_propia`: Plusvalía o Excedente Neto de Explotación de la rama.