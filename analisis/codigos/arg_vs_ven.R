
rm(list = ls())
gc()

library(tidyverse)
library(ggplot2)
library(readxl)
source("functions_hidrocarburos.R")



#tipos de cambio
tcp_arg <- read_excel("../resultados/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx",
                      sheet = "tipo_cambio") %>% 
  select(-c(sv, fuente))

# tcp_ven <- read_excel("../data/venezuela/renta_de_la_tierra_petrolera_venGAMMA.xlsx", 
#                       sheet = "10. Tipos de cambio") %>% 
#   select(-Unidad) %>% 
#   rename(anio = Anio)

tcp_ven <- read_excel("../data/venezuela/TCP Ven(1).xlsx", sheet = "TCP") %>% 
  select(anio = "...1", TCC= "TCC b", TCP = "...11") %>% 
  mutate_all(as.double) %>% 
  na.omit()



tcp = tcp_arg %>% 
  mutate(pais = "Argentina", 
         sv = TCp/TCc) %>% 
  rbind(tcp_ven %>%  
          rename(TCc = TCC, TCp = "TCP" ) %>% 
          mutate(pais = "Venezuela",sv = TCp/TCc-1))
tcp_long = tcp %>% pivot_longer(cols = c("TCc", "TCp", "sv"))

plt_sv = tcp_long %>% 
    filter(name == "sv") %>%
  ggplot(aes(anio,value, color =pais)) +
  # geom_col(aes(fill= name))+
  geom_line()+
  scale_y_continuous(labels = scales::percent_format())+
  scale_color_manual(name = "País" , 
                     values=c(  "dodgerblue1", "#CC6666"))+
  labs(title = "Sobrevaluación cambiaria",
       subtitle = "Expresada como la diferencia porcentual entre TCp y TCc",
       caption =  "Nota: 0% representa la paridad cmabiaria",
       y = "TCP/TCC - 1", x = "")+
  scale_x_continuous(breaks=seq(min(tcp_long$anio)-1,max(tcp_long$anio),5))
plt_sv = plot_theme(plt_sv)+theme(axis.text.x = element_text(angle =45, vjust = 0.6, hjust = 0.5))
ggsave("../resultados/comparacion_paises/sv.png",
       plot = plt_sv, height = 5, width = 10)

plt_tcp = tcp_long %>% 
  filter(name %in% c("TCc", "TCp")) %>%
  ggplot(aes(anio,log(value), color =pais)) +
  # geom_col(aes(fill= name))+
  geom_line(aes(linetype = name))+
  # scale_y_continuous(labels = scales::percent_format())+
  scale_color_manual(name = "País" , 
                     values=c(  "dodgerblue1", "#CC6666"))+
  scale_linetype_manual( "Variable", 
                        values = c("solid", "dotdash"))+
  labs(title = "Tipo de cambio comercial y de paridad",
       y = "log(tipo de cambio)", x = "")
plt_tcp = plot_theme(plt_tcp)

#ipc us
# ipc_us <- read_excel("../data/venezuela/renta_de_la_tierra_petrolera_venGAMMA.xlsx", 
#                       sheet = "11. Precios") %>% 
#   select(anio = Anio, ipc_us_97 = "IPC_EEUU_1=1997" ) 

ipc_us <- read_csv("../data/bls/cpi.csv") %>% 
  rename(anio = Year) %>% 
  group_by(anio) %>% 
  summarise(ipc_us_20 = mean(Value, na.rm = T)) %>% 
  mutate(ipc_us_20 = generar_indice(serie = ipc_us_20, 
                                    fecha = anio, fecha_base = 2020))


#pbi ven
pbi_ven = read_excel("../data/venezuela/renta_de_la_tierra_petrolera_venGAMMA.xlsx",
           sheet = "1. PIB") %>% rename(anio = Anio) 
# pv ven
pv_ven = read_excel("../data/venezuela/renta_de_la_tierra_petrolera_venGAMMA.xlsx",
           sheet = "6. Plusvalía ") %>% rename(anio = Anio) 



#rentas 
rt_ven <- read_excel("../data/venezuela/renta_de_la_tierra_petrolera_venGAMMA.xlsx",
                     sheet = "9. Renta de la tierra petrolera") %>% rename(anio = Anio) %>% 
  mutate(anio = as.double(anio))

rt_arg_desc <- read_excel("../resultados/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx", 
                          sheet = "RTPG_PextQ")  %>%  select(anio, unidad,  Rpq = Rtt) 

rt_arg <- read_excel("../resultados/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx",
                     sheet = "RTPG_mecanismos") %>% 
  # ungroup() %>% 
  mutate(Rsvx = rowSums(cbind(Rsvx_gas, Rsvx_crudo), na.rm = T )
         ,Rdifp = rowSums(cbind(Rdifp_gas, Rdifp_crudo) , na.rm =T),
         Imp = rowSums(cbind(Rreg, Rret) , na.rm =T),
         Subs = Subs*-1
         ) %>% 
  select(-c(Rsvx_gas, Rsvx_crudo,
            Rdifp_gas, Rdifp_crudo ,
            Rreg, Rret)) %>% 
  left_join(rt_arg_desc)


##renta mecanismos
rt_ven_mc = rt_ven  %>%
  select(anio, Rmec , Rkindv= Rt, Rsvx, Imp,
         Rdifp= "Rdifp_GasolinaMotor+Diesel" , Rpq ) %>%
  pivot_longer(cols = c(Rmec , Rkindv, Rsvx, Imp, Rdifp ,Rpq ) ) %>%
  left_join(tcp_ven) %>% 
  mutate(unidad = "USD TCP", 
         pais = "Venezuela",
         value = (value*10^6) / TCP) %>% 
  select(-c(TCC, TCP))

rt_arg_mc <- rt_arg %>%
  select( -c(unidad, IPC_18) ) %>%
  rename(Rmec = Rtt) %>%
  # reshape::melt(id = "anio")
  pivot_longer(cols = c( "Rsvx", "Rdifp",  
                         # "Rret",  "Rreg",
                         "Imp", "Rpq", "Rkindv" ,
                         "Subs", "Rmec") ) %>%
  left_join(tcp_arg) %>% 
  mutate(unidad = "USD TCP", 
         pais = "Argentina",
         value = value / TCp) %>% 
  select(-c(TCc, TCp))
  
rt_mec <- rbind(rt_arg_mc, rt_ven_mc) %>% 
  left_join(ipc_us, by = "anio") %>% 
  mutate(value = value/ipc_us_20)

plt_mec = rt_mec %>% 
  filter(!name %in% c("Rmec", "Rpq")) %>% 
  ggplot(aes(anio, value, fill = name))+
  geom_col(position = "stack")+
  scale_y_continuous(labels = scales::unit_format(unit = "MM", scale = 1e-6))+
  labs(title= "Renta de la tierra del petróleo y gas apropiada por diversos mecanismos", subtitle = "Millones de dólares de 2020 a tipo de cambio de paridad",
       x = "", y = "USD TCP", fill = "Variable")+
  facet_wrap(~pais, scales = "free")+
  scale_x_continuous(breaks = seq(1960, 2020, 5))
plt_mec = plot_theme(plt_mec)+theme(axis.text.x = element_text(angle = 45, vjust = 0.5, hjust=1))
ggsave("../resultados/comparacion_paises/renta_mecanismos_arg_vs_ven.png", 
       plot = plt_mec,  width = 10, height = 5)

# PxQ
plt_pxq = rt_mec %>% 
  filter(name %in% c( "Rpq")) %>% 
  ggplot(aes(anio, value, fill = pais))+
  geom_col(position = "stack")+
  scale_y_continuous(labels = scales::unit_format(unit = "MM", scale = 1e-6))+
  labs(title= "Renta de la tierra del petróleo y gas calculada desde el descuento sobre el valor a precio internacional",
       subtitle = "Millones de dólares de 1997 a tipo de cambio de paridad",
       x = "", y = "USD TCP")+
  scale_fill_manual("Paises", values=c(  "dodgerblue1", "#CC6666"))+
  scale_x_continuous(breaks = 
                       seq(min(rt_mec$anio, na.rm=T), 
                           max(rt_mec$anio, na.rm=T), 
                           5) )+
  facet_wrap(~pais, scales = "free")
plt_pxq =plot_theme(plt_pxq)+theme(axis.text.x=element_text(angle = 45, vjust = 0.9, hjust = 1)  )
ggsave("../resultados/comparacion_paises/renta_PxQ_arg_vs_ven.png", 
       plot = plt_pxq,  width = 10, height = 5)

# Renta sobre PBI y PV
# PxQ
rt_arg_pxq_pbi = read_excel("../resultados/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx", 
           sheet = "RTPG_PextQ_vs_pib")  %>%  select(-unidad) %>% 
  mutate(pais = "Argentina",
         tipo_renta = "PxQ")

rt_ven_pxq_pbi <- rt_ven %>% 
  select(anio, RvsPBI  = "Rpq/PIB",RvsPV   =  "Rpq/PvTotal") %>% 
  mutate(pais = "Venezuela",
         tipo_renta = "PxQ")

rt_pxq_pbi = rbind(rt_ven_pxq_pbi, rt_arg_pxq_pbi)  %>% 
  pivot_longer(cols = c("RvsPBI", "RvsPV"))

# Mecanismos
rt_arg_mec_pbi = read_excel("../resultados/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx", 
                            sheet = "RTPG_mecanismos_vs_pib")  %>%  select(-unidad) %>% 
  mutate(pais = "Argentina",
         tipo_renta = "Mecanismos")

rt_ven_mec_pbi = rt_ven %>% 
  left_join(pbi_ven %>% select(anio, PIB_Total )) %>% 
  left_join(pv_ven %>% select(anio, Pv_Total )) %>% 
  mutate(RvsPBI = Rmec/PIB_Total,
         RvsPV = Rmec/Pv_Total,
         pais = "Venezuela",
         tipo_renta = "Mecanismos") %>% 
  select(anio, pais, tipo_renta, RvsPBI, RvsPV)

rt_mec_pbi = rbind(rt_ven_mec_pbi, rt_arg_mec_pbi)  %>% 
  pivot_longer(cols = c("RvsPBI", "RvsPV"))

rt_pbi = rbind(rt_mec_pbi, rt_pxq_pbi)

renta_wb_plt <- renta_wb %>% 
  filter(pais %in% c("Argentina", "Venezuela")) %>% 
  rename(value = renta_pbi) %>% 
    mutate(name = "RvsPBI",
         # tipo_renta = "",
         anio = as.double(anio))

#rompe pero no importa
rt_pbi %>% 
  filter(tipo_renta == "PxQ", name == "RvsPBI") %>%
  mutate(fuente = "Estimación propia") %>% 
  rbind(renta_wb_plt) %>% 
  ggplot(aes(anio, value, color = fuente))+
  geom_line()+
  scale_y_continuous(labels = scales::percent_format())+
  facet_wrap(~pais, scales = "free")
  
# plt_rt_vs_pbi_y_pv = rt_pxq_pbi %>% 
plt_rt_vs_pbi_y_pv = rt_pbi %>% 
  # filter(tipo_renta == "PxQ") %>% 
  mutate(fuente = "Estimación propia") %>% 
  ggplot(aes(anio, value, fill = pais))+
  geom_col(position = "stack")+
  geom_line(data = renta_wb_plt, mapping = aes(anio, value, color = fuente)  , label = "Banco Mundial" )+
  scale_y_continuous(labels = scales::percent_format())+
  labs(title= "Renta de la tierra del petróleo y gas",
       subtitle = "Peso sobre el PBI y plusvalía total",
       x = "", y = "")+
  scale_fill_manual("País", values=c(  "dodgerblue1", "#CC6666"))+
  scale_color_manual(name = "",  values = c("black"))+
  facet_wrap(tipo_renta~pais~name,
  # facet_wrap(pais~name, 
             scales = "free",
             ncol = 4)
  # facet_wrap(name~pais, scales = "free")
plt_rt_vs_pbi_y_pv = plot_theme(plt_rt_vs_pbi_y_pv)+
  theme(axis.text.x = element_text(angle = 45, vjust = 0.9, hjust=1),
          axis.text = element_text(size = 7),
        strip.text = element_text(size=10))
plt_rt_vs_pbi_y_pv
ggsave(filename =  
         "../resultados/comparacion_paises/renta_plt_rt_vs_pbi_y_pv.png", 
       plot = plt_rt_vs_pbi_y_pv,  width = 12, height = 7) 

# Renta vzla plot
plot_rt_ven = rt_ven_pxq_pbi %>% 
  ggplot(aes(anio, RvsPV, fill  = "CC6666" ))+
  geom_col()+
  # geom_col(aes(fill = "CC6666"))+
  labs(title = "Renta de la tierra petrolera y gasífera de Venezuela sobre plusvalía",
       subtitle = "Descuentos sobre producto de valor a precio internacional",
       y = "", x ="")+
  scale_y_continuous(labels = scales::percent_format())+
  # scale_fill_manual("Paises", values=c(  "#CC6666"))+
  scale_x_continuous(breaks = seq(1960, 2020, 5) )
plot_rt_ven = plot_theme(plot_rt_ven)+theme(legend.position = "none",
                                            axis.text.x = element_text(angle = 45, vjust = 0.9, hjust=1))
plot_rt_ven
ggsave("../resultados/comparacion_paises/renta_pv_venezuela.png",
       plot_rt_ven, width = 10, height = 5)


# Renta hidrocarburífera + agria vs PBI
renta_agraria_post09 = read_excel("../data/renta_agraria/Renta (1).xlsx") %>% 
  select(anio = "...1", 
         # "Hidrocarburífero"= "renta_hidrocarburifera_sobre_pv"  ,
         "Agrario"=  "renta_agraria_sobre_pv" ) %>% 
  mutate(anio = as.double(anio)) %>% 
  na.omit() %>% 
  filter(anio > 2009)

renta_agraria_pre09 = read_excel("C:/Archivos/datos/agro/Series_de_Iñigo.xlsx", sheet = "RD") %>% 
  select(anio = "Cuadro 1", "Agrario" = "...15") %>% 
  mutate_all(as.double) %>% na.omit()

renta_agraria_hidrocarburifera <- rt_arg_mec_pbi %>% 
  select(anio, "Hidrocarburífero" = RvsPV) %>% 
  left_join(rbind(renta_agraria_pre09,renta_agraria_post09))

plt_rt_tot =renta_agraria_hidrocarburifera %>% 
  gather(key = "var", value = "value", 2:3) %>% 
  ggplot(aes(anio, value, fill = var))+
  geom_col()+
  scale_fill_manual("Sector", 
                    # names("Agraria", "Hidrocarburífera"),
                    values=c(  "olivedrab4", "black"))+
  labs(title = "Renta de la tierra del Sector agrario e hidrocarburífero sobre plusvalía de Argentina",
       subtitle = "Suma de mecanismos de apropiación", 
       y="", x ="")+
  scale_y_continuous(labels = scales::percent_format())+
  scale_x_continuous(breaks=seq(1960,2020,5))

plt_rt_tot = plot_theme(plt_rt_tot)
plt_rt_tot
ggsave( "../resultados/comparacion_paises/renta_total_arg.png", plt_rt_tot,
        width = 10, height = 5)

# TG
tg_arg <- read_excel("../resultados/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx", 
                     sheet = "tg_pg_total") %>% 
  filter(stock_seleccionado == "Bolsar") %>% 
  select(anio, TG_pg, TG_norm = TG_manuf) %>% 
  mutate(pais = "Argentina")

tg_ven <- read_excel("../data/venezuela/renta_de_la_tierra_petrolera_venGAMMA.xlsx",
                     sheet = "7. Tasas de ganancia") %>% rename(anio = Anio) %>% 
  select(anio, TG_pg = "TG_Pet",TG_norm = TG_noPet) %>% 
  mutate(pais = "Venezuela")

tg <- rbind(tg_arg, tg_ven) %>% 
  pivot_longer(cols = c(TG_pg, TG_norm), names_to = "tipo_de_TG") 
plt_tg <- tg %>% 
  filter(anio >1997) %>% 
  ggplot( aes(anio, value, color = tipo_de_TG))+
  # geom_line(aes(linetype=tipo_de_TG))+ 
  geom_line()+ 
  labs(title = "Tasa de ganancia de empresas hidrocarburíferas",
       y = "%", x="", color = "Tipo de tasa de ganancia",
       caption = "Nota: la tasa de ganancia normal se presenta como la industrial para Argentina y la no petrolera para Venezuela")+
  scale_y_continuous(labels=function(x) scales::percent(x, accuracy = 2) )+
  scale_color_manual(labels = c("Normal", "Hidrocarburífera"), 
                     values = c("darkslateblue","darkorange4") )+
  facet_wrap(~pais)
plt_tg = plot_theme(plt_tg)
ggsave("../resultados/comparacion_paises/tg_arg_ven.png", 
       plot = plt_tg,  width = 10, height = 5)

# IPT
# Evolución de indices
ipt_ven = read_excel("../data/venezuela/renta_de_la_tierra_petrolera_venGAMMA.xlsx",
           sheet = "12. Productividad") %>% 
  select(anio = Anio, value = "IPT_noPet_Ven_1=1997" )%>% 
  mutate(pais = "Venezuela",
         value = value *100)

ipt_arg = read_excel("../data/productividad/Productividad Industrial_2020.xlsx", 
           sheet = "Arg Industria ") %>% 
  select(anio =  "Millones de pesos",value=  "...27") %>% 
  mutate_all(as.double) %>% 
  na.omit()%>% 
  mutate(pais = "Argentina")

ipt_eeuu = read_excel("../data/productividad/Productividad Industrial_2020.xlsx", 
                     sheet = "EEUU prod") %>% 
  select(anio = "...2", value= "...7" ) %>% 
  mutate_all(as.double) %>% 
  na.omit()%>% 
  mutate(pais = "EEUU")
write_csv(ipt_eeuu %>% mutate(value = generar_indice(value,
                                                     anio,
                                                     2004))
          , "../resultados/comparacion_paises/ipt_us.csv")

# base_brecha_ipt_arg = 19.9
ipt_brecha =  ipt_eeuu %>% select(anio, ipt_eeuu = value) %>% 
  left_join(ipt_ven%>% select(anio, ipt_ven = value)) %>% 
   left_join( ipt_arg%>% select(anio, ipt_arg = value)) %>% 
    mutate(evo_rel_arg = cumprod(ipt_arg/lag(ipt_arg))/(ipt_eeuu/lag(ipt_eeuu)))
    # mutate(evo_rel_arg = (ipt_arg/lag(ipt_arg))/(ipt_eeuu/lag(ipt_eeuu)),
           # evo_rel_ven = (ipt_ven/lag(ipt_ven))/(ipt_eeuu/lag(ipt_eeuu)))

# calculo brecha
prod_ven <- read_excel("../data/venezuela/TCP Ven(1).xlsx", sheet = "IPT Ven") %>% 
  select(anio = "...1",  ocupados_no_pet ="...6", pbi_no_pet= "...9") %>% 
  mutate_all(as.double) %>% 
  na.omit() %>% 
  left_join(tcp_ven) %>% 
  mutate(prod_tcp_ven = (pbi_no_pet/ocupados_no_pet)/TCP) %>% 
  select(anio,prod_tcp_ven )
prod_ven

prod_us = read_delim("../resultados/comparacion_paises/prod_us.csv", delim =";")

brecha_ven =prod_ven  %>% inner_join(prod_us %>% select(anio, prod_us)) %>% 
  mutate(brecha_ven = prod_tcp_ven/prod_us, pais = "Venezuela") %>% 
  select(anio, brecha = brecha_ven, pais )

brecha_arg = read_excel("../data/productividad/Productividad Industrial_2020_copia.xlsx", 
           sheet = "Brecha productividad", skip = 3)  %>% 
  select(anio = "...1", brecha_arg = "Relativa...12") %>% 
  mutate_all(as.double) %>% 
  na.omit() %>% 
  mutate(brecha_arg = brecha_arg/100,
         pais = "Argentina") %>% 
  select(anio, brecha = brecha_arg, pais )

brechas = rbind(brecha_arg, brecha_ven) %>% 
  filter(anio >1987)

brechas_plot = brechas %>% ggplot(aes(anio, brecha, color = pais)) +
  geom_line()+
  labs(title = "Brecha de productividad industrial frente a Estados Unidos",
       y = "", x="")+
  scale_y_continuous(labels = scales::percent_format())+
  scale_x_continuous(breaks = seq(1985, 2020, 5))+
  scale_color_manual(name = "País" ,  values=c(  "dodgerblue1", "#CC6666"))
brechas_plot =plot_theme(brechas_plot)
brechas_plot
ggsave(plot = brechas_plot ,
       filename = "../resultados/comparacion_paises/brecha_productividad.png",
       width = 10, height = 5)

#graficos
ipt_brecha %>% 
  select(anio, brecha_ven, brecha_arg ) %>% 
  pivot_longer(cols = c(brecha_ven, brecha_arg)) %>% 
  ggplot(aes(anio, value)) +
  geom_line(aes(color = name))
  

ipt = rbind(ipt_ven, ipt_arg , ipt_eeuu)
plot_ipt = ipt %>% 
  filter(anio > 1985) %>% 
  ggplot(aes(anio, value, color = pais))+
  geom_line()+
  labs(title = "Evolución de la productividad del trabajo industrial",
       y = "base 1997 = 100", x ="")

plot_ipt = plot_theme(plot_ipt)  
ggsave("../resultados/comparacion_paises/ipt_arg_ven.png", 
       plot = plot_ipt,  width = 10, height = 5)



