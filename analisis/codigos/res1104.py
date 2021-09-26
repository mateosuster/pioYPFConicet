"precio_s_imp", "precio_c_imp", "precio_surtidor"# -*- coding: utf-8 -*-
"""
Created on Mon Jul  5 17:05:33 2021

@author: mateo
"""

import pandas as pd
import numpy as np
from scipy import stats

import seaborn as sns
import os

os.chdir("C:/Archivos/repos/hidrocarburos/analisis/data/secretaria_energia/1104")

# =============================================================================
# # carga de bases
# =============================================================================
se07 = pd.read_csv( "public_vi_access_eess_hasta_2007.txt"  , delimiter= ";" , encoding= "latin-1", na_values=['N/D'], decimal=',')
se0710 = pd.read_csv( "public_vi_access_eess_de_2007_a_2010.txt"  , delimiter= ";" , encoding= "latin-1", na_values=['N/D'], decimal=',')
se1013 = pd.read_csv( "public_vi_access_eess_2010_2013.txt"  , delimiter= ";" , encoding= "latin-1", na_values=['N/D'], decimal=',')
se1321 = pd.read_csv( "public_vi_access_eess_2013_en_adelante.txt"  , delimiter= ";" , encoding= "latin-1", na_values=['N/D'], decimal=',')


dfs = [se07, se0710, se1013, se1321]

# =============================================================================
# preprocesamiento
# =============================================================================

def preprocesamiento(x):
    data = pd.concat(x)
    data.rename(columns = {"Período": "periodo", "Producto": "producto", "Canal de Comercialización": "canal_comer" , "Tipo Negocio": "tipo_negocio",
                       'Precio sin impuestos': "precio_s_imp", 'Precio con impuestos': "precio_c_imp", 'Precio surtidor': "precio_surtidor",
                       "Volumen": 'volumen'},inplace = True)
    
    filtro = ["periodo", "anio", "mes", "producto",  "canal_comer" , "tipo_negocio",
         "precio_s_imp", "precio_c_imp", "precio_surtidor", 'volumen']
    
    data["anio"] = data["periodo"].str[:4]
    data["mes"] = data["periodo"].str[5:]
    
    data = data[filtro]
    
    # ordenamiento columns
    # cols = data.columns.tolist()
    # cols = cols[-2:] + cols[:-2]
    # data = data[cols]
    
    # transformacion a num
    # cols_not_num = [ "periodo", 'producto', 'canal_comer']
    # data.loc[:, ~data.columns.isin(cols_not_num)].apply(pd.to_numeric)
    
    num_cols = ["precio_s_imp", "precio_c_imp", "precio_surtidor"]
    gnc = data.loc[data["producto"]=="GNC" ]
    gnc[num_cols] = gnc[num_cols].apply(lambda x: x/1000, axis = 1) 
    
    data = pd.concat([data.loc[data["producto"]!="GNC" ] , gnc], axis = 0)
    
    filtro_prod = ["Gas Oil Grado 2", "Nafta (súper) entre 92 y 95 Ron",  "Nafta (premium) de más de 95 Ron", "Nafta (común) hasta 92 Ron" ]
    
    data =data[data["producto"].isin(filtro_prod)] 
        
    return data

data = preprocesamiento(dfs)

# =============================================================================
# Detección de outliers con modify z score 
# =============================================================================

def z_score(x):
    mad_val = x.mad()
    median_val = x.median()
    z_score = np.abs(((0.6745*(x - median_val))/mad_val))
    return z_score
    
filtro_precios =["precio_s_imp", "precio_c_imp", "precio_surtidor"]

group_data  = data.set_index(['anio', "mes" , "producto"])[filtro_precios]
# group_data  = data.set_index(['anio', "producto"])[filtro_precios]

melt_data = pd.melt(data, id_vars = ['anio', "mes" , "producto"], value_vars = filtro_precios, var_name ="tipo_precio", value_name = "valor")

mediana = melt_data.groupby(['anio', "mes" , "producto", "tipo_precio"]).median("valor").rename(columns = {"valor": "mediana"}).reset_index()
mad = pd.DataFrame(melt_data.groupby(['anio', "mes" , "producto", "tipo_precio"])["valor"].mad()).rename(columns = {"valor": "mad"}).reset_index()

x1 = pd.merge(melt_data, mediana , how = "left", right_on = ['anio', "mes" , "producto", "tipo_precio"] , left_on = ['anio', "mes" , "producto", "tipo_precio"] )
join_data = pd.merge(x1, mad, how = "left", right_on = ['anio', "mes" , "producto", "tipo_precio"] , left_on = ['anio', "mes" , "producto", "tipo_precio"] )

join_data["zscore"] = np.abs((.6745 *(join_data["valor"] - join_data["mediana"])) / join_data["mad"] )

clean_data = join_data[join_data["zscore"] < 3.5] 

# len(join_data )- len(clean_data )

precios_mensuales = clean_data.groupby(['anio', "mes" , "producto", "tipo_precio"])["valor"].mean()
precios_anuales = clean_data.groupby(['anio', "producto", "tipo_precio"])["valor"].mean()
precios_anuales.to_csv("precios_promedio_res1104.csv")





# =============================================================================
# visualizacion
# =============================================================================

precios_anuales.loc[ "2019"]
# [ (precios_anuales["anio"]=="2020")  &  (precios_anuales["producto"]== "Nafta (premium) de más de 95 Ron" ) & (precios_anuales["tipo_precio"]=="precio_c_imp" )]["valor"]


# x = melt_data[ (melt_data["anio"]=="2020")  &  (melt_data["producto"]== "Nafta (premium) de más de 95 Ron" ) & (melt_data["tipo_precio"]=="precio_c_imp" )]["valor"]
x = melt_data[ (melt_data["anio"]=="2019")  &  (melt_data["producto"]== "Nafta (súper) entre 92 y 95 Ron" ) & (melt_data["tipo_precio"]=="precio_c_imp" )]["valor"]
sns.histplot(  x )



# =============================================================================
# sucioooooooooo
# =============================================================================
##################################




df = group_data.copy()
threshold = 3.5
for col in df.columns:
    col_zscore = col +'_zscore'
    median_y = df[col].median()
    median_absolute_deviation_y = (np.abs(df[col]-median_y)).median()
    # median_absolute_deviation_y = df[col].mad()
    # modified_z_scores = 0.6745 *((df[col] - median_y)/median_absolute_deviation_y)
    modified_z_scores = (0.6745 *(df[col] - median_y))/median_absolute_deviation_y
    df[col_zscore] = np.abs(modified_z_scores)

precio_s_imp =  df[(np.abs(df["precio_s_imp_zscore"]) < threshold)]["precio_s_imp"].reset_index().groupby(['anio', "mes" , "producto"]).mean()
precio_c_imp = df[(np.abs(df["precio_c_imp_zscore"]) < threshold)]["precio_c_imp"].reset_index().groupby(['anio', "mes" , "producto"]).mean()
precio_surtidor = df[(np.abs(df["precio_surtidor_zscore"]) < threshold)]["precio_surtidor"].reset_index().groupby(['anio', "mes" , "producto"]).mean()


x1 = pd.merge(precio_s_imp, precio_c_imp, how =  "outer" , left_on= ['anio', "mes" , "producto"], right_on=['anio', "mes" , "producto"])
precios_mensuales = pd.merge(x1, precio_surtidor, how =  "outer" , left_on= ['anio', "mes" , "producto"], right_on=['anio', "mes" , "producto"])
precios_anuales = precios_mensuales.groupby(['anio', "producto"]).mean()













df = group_data.copy()

for col in df.columns:
    
    col_median= col +'_median'
    df[col_median] = df[col].median()
    
    col_mad= col +'_mad'
    df[col_mad] = df[col].mad()
    


len(precio_s_imp) - len(df)

x = df[(df.index.get_level_values("anio") =="2021") &(df.index.get_level_values("producto") =="Nafta (premium) de más de 95 Ron") &(df.index.get_level_values("mes") =="01") ].sort_index()

median = x["precio_s_imp"].median()
# mad = np.abs(x["precio_s_imp"] - median).median()
mad = x["precio_s_imp"].mad()
zscore =  0.6745 * ((69.28 - median)/mad)


# =============================================================================
# precio promedio
# =============================================================================



data["tipo_negocio"].value_counts()
data["canal_comer"].value_counts()
data["producto"].value_counts(dropna = False)
data["precio_s_imp"].value_counts()


data_productos = data.iloc[:,[1,3,-3,-4, -2,]]

desc_p_surtidor = data_productos.iloc[:,[0,1,-1]].groupby(["anio", "producto"]).describe().unstack(1)
desc_p_s_imp= data_productos.iloc[:,[0,1,-2]].groupby(["anio", "producto"]).describe().unstack(1)
desc_p_c_imp= data_productos.iloc[:,[0,1,-3]].groupby(["anio", "producto"]).describe().unstack(1)

# precios_promedio = data[(data["canal_comer"]== "Al público")&(data["tipo_negocio"]=="Estación de servicio")].groupby(["anio", "producto"])[filtro_precios].median()
# precios_promedio.to_csv("precios_promedio_res1104.csv")

# https://www.argentina.gob.ar/economia/energia/hidrocarburos/resolucion-se-11042004/aclaraciones-y-recomendaciones




######
# cuit_clae = pd.read_csv( "../data/cuit 2017 impo_con_actividad.csv")
cuit_clae = pd.read_csv( "../data/Datos scrapeados de CUIT Online - result_DF2_simplificado.csv" )
cuit_clae = cuit_clae[cuit_clae["Numero_actividad_cuit"]<=6].drop(["Clae6_desc","Fecha_actividad", "Cantidad_actividades_cuit"], axis =1)
# cuit_clae.pivot(index="CUIT", columns= "Numero_actividad_cuit", values= "Clae6")

cuit_clae6 = cuit_clae.set_index(["CUIT", "Numero_actividad_cuit"], append=True)
cuit_clae6.unstack().droplevel(0, axis = 1).groupby("CUIT").sum().astype(int)

cuit_clae_letra = pd.merge(cuit_clae, clae[["clae6", "letra"]], left_on="Clae6", right_on= "clae6", how = "left").drop(["clae6", "Clae6", "Numero_actividad_cuit"], axis =1)
cuit_clae_letra = cuit_clae_letra[~cuit_clae_letra["letra"].isnull()]
x = pd.DataFrame(cuit_clae_letra.groupby("CUIT")["letra"].agg(",".join)).reset_index()
x["letra"].str.split(pat=",", expand=True)


