# Funciones de conversión para crudo
## Metro cubico a barril (_p = precio, _q = cantidad)
conversor_m3bbl_p <- function(x) {x / 6.2898}
conversor_m3bbl_q <- function(x) {x * 6.2898}

# Funciones de conversión para gas
## Pies cúbico a metro cúbico
## 1ft³= 0.02831685m³
conversor_ft3m3_p <- function(x) {x / 0.02831685}
conversor_ft3m3_q <- function(x) {x * 0.02831685}

## Pie cúbico a Millón de BTU
# 1 ft3 =  0.001028 MM BTU
conversor_ft3MMBTU_q <- function(x) {x * 0.001028}
conversor_ft3MMBTU_p <- function(x) {x / 0.001028}

## Millón de BTU a metro cúbico
## 1 MM Btu =  27,8 m3 de gas (IAPG) ó 28.32861 m3 (Canada Energy Regulator)  
conversor_MMBTUm3gas_p <- function(x) {x / 28.32861}

## m3 a  MMBTU de gas
# 1 m3 = 0.0353 MM BTU  (Canada Energy Regulator)
# otra opción 1 m3 = 34.121 MM BTU  (BP)
conversor_m3MMBTU_q <- function(x){x * 0.0353}
conversor_m3MMBTU_p <- function(x){x / 0.0353}

## m3 a  MMBTU (Alternativa, revisar)
# conversor_m3MMBTU_q <- function(x){x * 1/27.8}
# conversor_m3MMBTU_p <- function(x){x / 1/27.8}

## Conversión a BEP desde distintas medidas
conversor_m3bep_q <- function(x) {x * 5883}
conversor_MMBTUbep_q <- function(x) {x * 0.17245496} # BP
conversor_MMBTUbep_p <- function(x) {x / 0.17245496}
conversor_bepMMBTU_p <- function(x) {x / 5.798615}

# Otras funciones
cambio_porcentual <- function(x) {x/lag(x) - 1}

generar_indice <-  function(serie,fecha, fecha_base){
  valor_base <- serie[which(fecha==fecha_base)]
  if_else(serie == 0, 0, serie/valor_base)
}



variacion_interanual <- function(x) {x  - lag(x)}

tasa_crecimiento <- function(x) {(x  - lag(x))/lag(x)}


generar_indice <-  function(serie,fecha, fecha_base){
  valor_base <- serie[which(fecha==fecha_base)]
  (serie/valor_base)
}

