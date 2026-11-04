# Fuentes de las constantes «a cotejar» del plan vial

Investigado el 2026-10-30 por la sesión tesis-e3 para la sesión que desarrolle `docs/planes/PLAN_VIAL_AGREGADOS.md`.
Todo lo de aquí es **público** (leyes, normas, fichas técnicas, series oficiales). Se puede copiar al repositorio, por
ejemplo como `docs/fuentes/2026-10-30-fuentes-plan-vial.md`, sin datos de empresas.

Marcas: **V** = leído en la fuente primaria (texto de la ley en `docs/fuentes/`); **V2** = leído en una fuente
secundaria seria que cita la primaria (tesis o despacho jurídico); **I** = indicio (resumen de buscador, ficha
comercial o norma extranjera usada como referencia). Lo que no es **V** queda «a cotejar» en el código.

## 1. Tarea 17: FCAS por componentes

### 1.1 El método (corrige la fórmula del plan)

El plan dice `fcas = Σ días ÷ días_trabajados + Σ porcentajes`. **Es incorrecto.** El método venezolano que
documentan Dodi y Salas (2019, `docs/fuentes/Dodi_Salas_2019_FCAS_UJAP.pdf`, §4.2 y su ejemplo) es:

    días_trabajados = días calendario del período − descansos − feriados − vacaciones − permisos − lluvia
    días_pagados    = días calendario del período (descansos y feriados son remunerados)
                      + bonificaciones expresadas en días de salario (vacaciones y bono, utilidades, asistencia,
                        garantía de prestaciones, …)
    FCAS (por días) = (días_pagados − días_trabajados) ÷ días_trabajados
    FCAS total      = FCAS por días + aportes patronales (porcentaje sobre el salario pagado, llevados a días trabajados)

**Oráculo para la prueba** (su caso 1, verificado a mano): 365 días, 23,13 días de bonificación, 217,28 días
trabajados → (365 + 23,13 − 217,28) ÷ 217,28 = **0,7863** (78,63 %), que es exactamente el valor que publican. **V2**

Aviso de unidades: el motor de Sílice aplica `sueldo × (1 + fcas)` (`core/costing/motor.py:42-43`). Un libro que escriba el FCAS
como multiplicador (por ejemplo «× 1,90») equivale a **`fcas = 0,90`** en Sílice. El valor por defecto de Sílice (6,00)
multiplica el sueldo por 7. La calculadora debe mostrar las dos formas («90 %» y «× 1,90») para que nadie las confunda.

### 1.2 Componentes en días (LOTTT 2012 y convención colectiva de la construcción 2023)

| Componente | Valor | Fuente | Marca |
|---|---|---|---|
| Jornada | 5 días por semana; 2 días de descanso continuos y remunerados | LOTTT art. 173 | V |
| Pago de los descansos semanales | Se pagan si el trabajador prestó al menos 3 jornadas completas en la semana | CCT 2023 cláusula 8 | V |
| Feriados nacionales | 1.º de enero; lunes y martes de carnaval; jueves y viernes santos; 1.º de mayo; 24, 25 y 31 de diciembre (8) + los de la Ley de Fiestas Nacionales + hasta 3 regionales por año | LOTTT art. 184 | V (el número de la Ley de Fiestas Nacionales: a cotejar) |
| Vacaciones y bono vacacional | 17 días hábiles de disfrute, **pagados con 80 días de salario básico** (incluye el bono vacacional) | CCT 2023 cláusula 47 (mínimo legal: LOTTT arts. 190 y 192, 15 + 15 días) | V |
| Utilidades | **Mínimo 100 días de salario** por año | CCT 2023 cláusula 48 (mínimo legal: 30 días, LOTTT arts. 131 y 132) | V |
| Asistencia puntual y perfecta | 6 días de salario básico por mes con asistencia perfecta (aplicar con una probabilidad declarada) | CCT 2023 cláusula 41 | V |
| Garantía de prestaciones sociales | 6 días por mes (72 días el primer año) | CCT 2023 cláusula 50 (mínimo legal: 15 días por trimestre + 2 por año, LOTTT art. 142) | V |
| Bono de alimentación (cestaticket) | Monto del Ejecutivo **más un 100 % adicional** | CCT 2023 cláusula 20 | V. **No va en el FCAS**: Sílice ya lo lleva aparte en `bono_alimentacion` (contarlo dos veces infla el costo) |
| Permisos remunerados, útiles escolares, nacimiento, matrimonio, botas y trajes, etc. | Por cláusula | CCT 2023 cláusulas 23–25, 38, 61 | V (cada uno se modela con su frecuencia esperada, como en Dodi y Salas) |

### 1.3 Aportes patronales (porcentaje del salario)

| Aporte | Patrono | Fuente | Marca |
|---|---|---|---|
| **Paro forzoso** (Régimen Prestacional de Empleo) | **2,00 %** del salario normal (la tasa es 2,50 %: el 80 % lo paga el patrono y el 20 % el trabajador) | Ley del Régimen Prestacional de Empleo, art. 46, citada textualmente por Dodi y Salas (2019) | V2 |
| Ahorro habitacional (FAOV) | **2,00 %** del salario integral (aporte de 3 %: 2/3 el patrono y 1/3 el trabajador) | Ley del Régimen Prestacional de Vivienda y Hábitat, art. 30, citada por Dodi y Salas (2019) | V2 |
| INCES | **2,00 %** del salario normal (empresas con 5 o más trabajadores) | Ley del INCES, citada por Dodi y Salas (2019) | V2 |
| Seguro social (IVSS) | Según el tipo de riesgo de la empresa; en la práctica se citan 9 %, 10 % y 11 % | Reglamento de la Ley del Seguro Social, art. 109, citado por Dodi y Salas (2019) **sin los porcentajes**; la ley de 1991 en `docs/fuentes/` no los trae | **I: a cotejar**. Por defecto, **11 %** (el más alto: subestimar el costo es peor que sobreestimarlo) |
| **Contribución especial para pensiones** | **9 %** del total de pagos a los trabajadores | Ley de Protección de las Pensiones de Seguridad Social (Gaceta 6.806 Ext., mayo de 2024) y Decreto 4.952 que fija el 9 % | V2/I. **A cotejar**: la base exacta, si es «salario» o «total de pagos», y la exoneración temporal que menciona el decreto. Es el aporte más grande y el más reciente: **no omitirlo** |

## 2. Tarea 18: IVA

| Dato | Valor | Fuente | Marca |
|---|---|---|---|
| Alícuota general | **16 %** | Decreto 3.584, Gaceta 6.395 Ext. del 17-08-2018; la Ley del IVA permite al Ejecutivo fijarla entre 8 % y 16,5 %; no consta reforma publicada a septiembre de 2026 | V2/I (citar la Gaceta al cotejar) |
| Alícuota reducida | 8 % (ciertos bienes) | Secundarias | I (no hace falta para este plan) |

`ALICUOTA_IVA` puede llevar la fuente «Decreto 3.584, G.O. 6.395 Ext., 17-08-2018 (alícuota general 16 %)».

## 3. Tarea 7: códigos de las partidas viales

- La norma de carreteras **no es** la COVENIN 2000-92 (esa es la de edificaciones). Es
  **COVENIN 2000-1:1987, «Sector construcción. Especificaciones, codificación y mediciones. Parte I. Carreteras»**:
  aprobada como provisional en 1980 y definitiva en 1987 (registro del centro de documentación de SENCAMER). **V2**
- En el esquema COVENIN 2000, cada partida es **una letra y nueve dígitos**, y la letra **«C» corresponde a
  carreteras**. **I**
- Consecuencia: `PARTIDAS_VIALES` usa códigos con forma `C-xxx.xxx.xxx` y la fuente «COVENIN 2000-1:1987, Parte I
  Carreteras: código a cotejar con el texto de la norma». Hay copias de la norma en SlideShare y Scribd; el texto
  oficial se consigue en FONDONORMA.

## 4. Tarea 9: rangos de las reglas viales

No encontré especificaciones viales venezolanas públicas en línea. Estos son valores de referencia extranjeros o de
fabricantes (**I**). Todos van «a cotejar con la especificación del proyecto».

| Regla | Referencia | Fuente |
|---|---|---|
| **VR2 asfalto en la mezcla** | **No usar un rango universal**: comparar con la **fórmula de trabajo** de la receta y una tolerancia de **±0,5 puntos**. Los óptimos Marshall típicos de mezcla densa rondan el 5,5 % | Tolerancia contractual ±0,5 % (LanammeUCR, Costa Rica); casos de 5,47 % y 5,50 % (estudios de Perú y Ecuador) |
| **VR3 imprimación** | Ligante residual **≥ 500 g/m²**; con emulsión, de 1.000 a 2.000 g/m² según el suelo | IDU Bogotá (especificación 500-05 / 610-18) y pliego de Madrid |
| **VR3 riego de adherencia** | Ligante residual **≥ 200 g/m²**; un estudio chileno halló un óptimo de 0,11 a 0,21 l/m² de residuo | Pliego de Madrid; Universidad de Chile |
| **VR5 pintura de tráfico** | **≈ 29 a 44 l por km de línea de 10 cm** (rendimiento teórico, sin pérdidas): 2,6 m²/l a 15 mils húmedos; de 23 a 35 m/l según el fabricante | Fichas técnicas de Comex, Hempel, Gruposur y Sherwin-Williams |

## 5. Tarea 12: series de precios

| Serie | Qué hay | Fuente | Nota |
|---|---|---|---|
| Cemento asfáltico | No hay serie pública venezolana. La internacional más usable es el **PPI de asfalto de EE. UU., mensual**: `WPU05810212` (FRED/BLS), con datos hasta mayo de 2026 | https://fred.stlouisfed.org/series/WPU05810212 | Es un **índice**, no un precio: sirve para la variación mensual. Declararlo como **proxy internacional** |
| Gasoil | Precio **administrado**: según la Gaceta, 0,32 USD/l para el sector industrial (antes 0,50 USD/l para el transporte de carga, 2022). Hay noticias contradictorias de 2026 | Prensa que cita la Gaceta (**I**) | Un precio fijado por decreto es una serie en escalones: la proyección la tratará casi como constante salvo los saltos. A cotejar en la Gaceta |
| Tasa BCV | Ya existe en Sílice | BCV | — |

## 6. Fuentes web consultadas

- FRED: https://fred.stlouisfed.org/series/WPU05810212 ; https://fred.stlouisfed.org/series/WPU058102
- SENCAMER (COVENIN 2000-1, Carreteras): https://sigbs.sencamer.gob.ve/cgi-bin/koha/opac-detail.pl?biblionumber=2559
- Cómputos métricos COVENIN 2000-92 (ULA): https://webdelprofesor.ula.ve/arquitectura/bsteiner/catedras/Inspeccion_de_obras/material_de_apoyo/COMPUTOS%20METRICOS%20COVENIN%202000.pdf
- IVA 16 %: https://www.nortonrosefulbright.com/es-es/knowledge/publications/b3c83f55/se-fija-la-alicuota-general-del-impuesto-al-valor-agregado-en-16 ; https://taxsummaries.pwc.com/venezuela/corporate/other-taxes ; https://www.riotimesonline.com/taxes-venezuela-expats-2026/
- Pensiones 9 %: https://accesoalajusticia.org/fijado-en-9-el-monto-de-la-contribucion-especial-prevista-en-la-ley-de-proteccion-de-las-pensiones-de-seguridad-social/ ; https://eldiario.com/2024/05/20/empresas-pagaran-contribucion-especial-por-ley-de-pensiones/ ; Gaceta 6.806: https://www.traviesoevans.com/travieso/wp-content/uploads/gacetas/2024/05-mayo/2024-05-08-6806-extraordinario.pdf
- Riegos: https://www.idu.gov.co/Archivos_Portal/SIIPVIALES/Innovacion/2019/10%20Octubre/especificaciones%20Tecnicas/Versi%C3%B3n%201/Capitulo%205/Secci%C3%B3n%20500-05.pdf ; https://www.madrid.es/UnidadesDescentralizadas/UrbanismoyVivienda/Urbanismo/PUBLICACIONES/CondTecnPav/Capitulo40/40_52.pdf
- Mezcla asfáltica: https://www.lanamme.ucr.ac.cr/images/ensayos/MezclasAsfalticas/Ficha-tecnica-IT-MZ-06-rev-MJA.pdf
- Pintura de tráfico: https://mitienditavirtual.finanzas.cdmx.gob.mx/storage/156/CT-PINTURA-TRAFICO-SECADO-RAPIDO-BS-(1).pdf ; https://www.construmatica.com/archivos/28006/fichas_tecnicas/567e0_hempels_pintura_de_trafico.pdf
- Gasoil: https://diariodelosandes.com/venezuela-pone-fin-al-suministro-de-combustible-gratuito-para-el-sector-industrial ; https://www.vozdeamerica.com/a/gobierno-de-venezuela-oficializa-aumento-del-precio-del-diesel/7176668.html
