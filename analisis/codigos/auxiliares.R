# Datos auxiliares
##Revista de Política de Precios de la Energía
## GAS
#precio transferencia, regalias, compensaciones, etc a noviembre de cada año
cuadro_4.1 <- read_excel("C:/Archivos/Datos/Hidrocarburos/Revistas Políticas de Precios de la Energia en Arg 1970-1988/Precios del gas natural y derivados 1970 - 1988.xlsx", 
                         skip = 1, sheet = 1)


#precio adquisición del Estado y tarifa media de gas distribuido
cuadro_4.4 <- read_excel("C:/Archivos/Datos/Hidrocarburos/Revistas Políticas de Precios de la Energia en Arg 1970-1988/Precios del gas natural y derivados 1970 - 1988.xlsx", 
                         skip = 1, sheet = 4)

## CRUDO

# Precios por cuenca
cuadro_2.2 <- read_excel("C:/Archivos/Datos/Hidrocarburos/Revistas Políticas de Precios de la Energia en Arg 1970-1988/Precios del petroleo crudo y derivados 1970 - 1989.xlsx", 
                         skip = 0, sheet = 2) %>% 
  mutate(unidad = "pesos de 1970")

#evolución de precios por cuencia (indices 1970 = 100)
cuadro_2.3 <- read_excel("C:/Archivos/Datos/Hidrocarburos/Revistas Políticas de Precios de la Energia en Arg 1970-1988/Precios del petroleo crudo y derivados 1970 - 1989.xlsx", 
                         skip = 0, sheet = 3) %>% 
  rename(anio = "...1")


# precio promedio pagado a contratistas en pesos y dolares
cuadro_2.5 <- read_excel("C:/Archivos/Datos/Hidrocarburos/Revistas Políticas de Precios de la Energia en Arg 1970-1988/Precios del petroleo crudo y derivados 1970 - 1989.xlsx", 
                         skip = 1, sheet = 5)

# precios pagados a contratistas vs cobrados por refinadoras privadas (precio crudo neuquina)
cuadro_2.6 <- read_excel("C:/Archivos/Datos/Hidrocarburos/Revistas Políticas de Precios de la Energia en Arg 1970-1988/Precios del petroleo crudo y derivados 1970 - 1989.xlsx", 
                         skip = 1, sheet = 6) %>% 
  mutate(unidad = "pesos_de_1970_m3")

# valores unitarios del producto compuesto a nivel productores y consumidores
cuadro_2.7 <- read_excel("C:/Archivos/Datos/Hidrocarburos/Revistas Políticas de Precios de la Energia en Arg 1970-1988/Precios del petroleo crudo y derivados 1970 - 1989.xlsx", 
                         skip = 1, sheet = 7)

# PROCESAR ESTA BASE
mecon_hidrocarburos_df <-  read_csv("../data/mecon/hidrocarburos.csv", 
                                    col_types = cols(indice_tiempo = col_date(format = "%d/%m/%Y")), 
                                    locale = locale(encoding = "ISO-8859-1"))
unique(mecon_hidrocarburos_df$indicador)


## Ventas
# Crudo y Gas

# * [SESCO - Refinación y Comercialización de petróleo, gas y derivados](http://datos.minem.gob.ar/dataset/refinacion-y-comercializacion-de-petroleo-gas-y-derivados-tablas-dinamicas)
# 
#  Datos de cantidades
#  
#compras empresas del sector
compras <- read_csv("C:/Archivos/Datos/Hidrocarburos/SESCO/Refinación y comercializacion/compras.csv")

#ventas mdo interno. cantidades. post 2010
ventas_mercado_producto_empresa <- read_csv("C:/Archivos/Datos/Hidrocarburos/SESCO/Refinación y comercializacion/ventas-mercado-producto-empresa.csv", 
                                            locale = locale(encoding = "ISO-8859-1"))

#ventas mdo interno. cantidades. post 2010
ventas_a_empresas_del_sector <- read_csv("C:/Archivos/Datos/Hidrocarburos/SESCO/Refinación y comercializacion/ventas-a-empresas-del-sector.csv")

#otra base. solo cantidades. ver de donde apareció
impo_expo <- read_csv("/Archivos/Datos/Hidrocarburos/Estimacion propia/datasets/importaciones-exportaciones (1).csv")


