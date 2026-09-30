# Prueba del software con precios de referencia publicados (MaPreX jul-2026 y tabulador CIV)

**Fecha:** 2026‑09‑29 · **Rama:** `inc/cierre-C6-R` (pista R de C6, desde `inc/cierre-C6-N` =
`7213524`) · **Commit del script:** `1648d2f` · **Plan:** `C6-plan.md` del directorio de control de
C6 (§5 y rulings C6‑6 y C6‑9) · **Bitácora de la fase:** [2026-09-23-cierre.md, «Fase C6»](2026-09-23-cierre.md).

**Naturaleza de los datos** ([NORMAS.md §1](../../NORMAS.md)). Los casos que se revaloran (el
presupuesto 001 del drenaje de la clínica, los dos de ARENAZA, `MNT-001` y `SIS-001`) son ejercicios
académicos o casos construidos para el proyecto: **didácticos**. Los listados MaPreX de julio de 2026
y el tabulador CIV sí son referencias publicadas. Esta bitácora mide la **sensibilidad de los casos
didácticos a precios de referencia publicados**; no estima el costo de ninguna obra ejecutada.

## Cómo se obtuvo

Orden exacta, desde la raíz del worktree:

```
uv run --all-extras python scripts/probar_precios_maprex.py --salida <temporal>/resultado.md
```

`--all-extras` deja el entorno como lo sincronizan la CI y el README; sin el extra `ml` el script
corre igual, sin detector de atípicos, y el informe lo declara.

- **Bases:** cuatro SQLite nuevas en un `tempfile.TemporaryDirectory()`, sembradas con
  `scripts.seed.sembrar`, `seed_telecom.sembrar_telecom`, `seed_industrial.sembrar_industrial` y
  `seed_sistemas.sembrar_sistemas`. El script no tiene `--db` y no abre `data/apu.db` (la prueba
  `tests/unit/test_probar_precios_maprex.py::test_data_apu_db_no_cambia` lo comprueba con la huella
  del archivo antes y después).
- **Tasa y fechas:** 633,3644 Bs/USD al 01/07/2026 (la del listado de mano de obra; README de
  `data/precios/maprex_2026-07/`). Cada `precio_usd` de `referencia_civil.csv` que se usa se
  verificó contra su `precio_bs` con esa tasa. Vigencia única de la lista civil derivada y de la
  telecom: 2026‑07‑09 (materiales y equipos; la mano de obra de MaPreX es del 01/07/2026). Línea base
  28/04/2026; ARENAZA 18/05/2026; `MNT-001` 09/07/2026; `SIS-001` (tabulador CIV) 01/07/2026.
- **Lista civil derivada:** de las 37 filas de `referencia_civil.csv`, la nota «equivalente de
  '<X>'» casa `<X>` con `data/civil/plantilla_precios.csv` por `normalizar_texto`, con el mismo tipo y
  unidad equivalente (`unidades_equivalentes`); la plantilla no declara unidad para la mano de obra,
  que se paga por jornal, y casa si MaPreX la cotiza por `dia`. Solo materiales y mano de obra; los
  equipos se contrastan aparte (C6‑9). La lista se escribe en un CSV temporal (no se versiona en
  `data/civil/`).
- **Revaloración:** `crear_lista_desde_archivo` + `actualizar_precios(sesion, "Drenaje de la
  clínica", "001", lista, "MAPREX-2026-07", plan=plan_secuencial,
  detectar_atipicos=ml.anomaly.precios_atipicos)`. El 001 es el presupuesto auditado con sus trazas
  (`tests.fixtures.presupuesto_auditado.items_con_trazas`), elaborado con `plan_secuencial`.
  Telecom: TC‑001 y TC‑002 guardados con la lista ARENAZA y revalorados con
  `data/telecom/fuentes/lista_maprex_2026-07.csv`, sin plan (como sus sembradores). Industrial y
  sistemas: revalorados con su propia lista; la versión nueva se deshace.

## Resultado

Las tablas siguientes son la salida del script, tal cual (montos redondeados a dos decimales solo al
presentar; precios de insumos a cuatro).

Tasa 633.3644 Bs/USD (01/07/2026). Vigencia de la lista civil derivada y de la telecom: 2026-07-09. Detector de atipicos: `ml.anomaly.precios_atipicos`.

### 1. Cobertura del listado crudo `lista_maprex_usd.csv`

Carga sin confirmar sobre cada base sembrada (la transaccion se deshace).

| Base | Filas del archivo | Casadas | Desconocidas (2a) | Rechazadas (2b) |
|---|---|---|---|---|
| civil | 111 | 1 | 109 | 1 |
| telecom | 111 | 0 | 111 | 0 |
| industrial | 111 | 6 | 102 | 3 |
| sistemas | 111 | 0 | 108 | 3 |

Rechazadas por unidad no equivalente (flujo 2b):

- civil: equipo 'HERRAMIENTAS MENORES' (dia)
- industrial: equipo 'TALADRO INDUSTRIAL BANCO 3/4" 750W' (dia), mano_obra 'ELECTRICISTA DE 1RA -N5' (dia), mano_obra 'MECANICO DE EQUIPO PESADO DE 1RA -N8' (dia)
- sistemas: mano_obra 'GERENTE DE PROYECTOS C/CERTIFICACION' (dia), mano_obra 'INGENIERO COMPUTISTA P-9 CIV (19-20 AÑOS EX' (dia), mano_obra 'INGENIERO P-5 CIV ANALISTA DIAGNOSTICO' (dia)

### 2. Civil: presupuesto 001 de la linea base

#### Lista civil derivada de `referencia_civil.csv`

12 filas casadas (materiales y mano de obra); 25 excluidas.

| Tipo | Insumo del catalogo | Unidad | USD | Ref MaPreX | Descripcion MaPreX |
|---|---|---|---|---|---|
| material | Tubería PVC 4 pulg | m | 13.9291 | PLOA38 | TUBO PVC A.N. D=4" / 110 MM E = 2,2 MM NORMA |
| material | Arena lavada | m3 | 59.6023 | MZ0027 | ARENA LAVADA |
| material | Piedra picada | m3 | 59.6023 | AGR081 | PIEDRA PICADA PARA CONCRETO |
| material | Agua | m3 | 11.9205 | AGR003 | AGUA SUMINISTRADA EN CAMION CISTERNA O TANQUE |
| material | Material granular | m3 | 7.1523 | BAS006 | MATERIAL GRANULAR INTEGRAL |
| mano_obra | Operador de equipo de 1ra | (jornal) | 2.5560 | 24-5.4 | OPERADOR DE EQUIPO PESADO DE 1RA -N8 |
| mano_obra | Ayudante | (jornal) | 1.7816 | 1-1.2 | AYUDANTE - TABULADOR CONSTRUCCION -N2 |
| mano_obra | Chofer de 2da | (jornal) | 1.9938 | 8-3.5 | CHOFER DE 2DA (DE 3 A 8 TON) -N4 |
| mano_obra | Chofer de 4ta | (jornal) | 1.7816 | 4-3.3 | CHOFER DE 4TA -N2 |
| mano_obra | Maestro (electricista, según el APU original) | (jornal) | 2.3215 | 24-216 | MAESTRO ELECTRICISTA -N7 |
| mano_obra | Carpintero de 1ra | (jornal) | 2.1877 | 19-2.5 | CARPINTERO DE 1RA -N5 |
| mano_obra | Albañil de 1ra | (jornal) | 2.1877 | 19-2.2 | ALBAÑIL DE 1RA -N5 |

Excluidas:

| Tipo | Descripcion MaPreX | Ref | Equivalente de | Motivo |
|---|---|---|---|---|
| material | CODO PVC 90 GRADOS A.N. D=4" | PLO035 | Curva PVC 4 pulg | unidad MaPreX 'pza' no equivale a la del catalogo 'unidad' |
| material | UNION PVC A.B. 4" | PLO560 | Conector PVC 4 pulg | unidad MaPreX 'pza' no equivale a la del catalogo 'unidad' |
| material | PEGAMENTO PARA PVC  1/4 GL TANGIT  O SIM | MT539 | Pegamento para PVC | unidad MaPreX 'env' no equivale a la del catalogo 'unidad' |
| material | MADERA PARA ENCOFRADO DE PINO O SIMILAR | ENC010 | Madera | unidad MaPreX 'm3' no equivale a la del catalogo 'm2' |
| material | LISTON MADERA P/ENCOFRADO 2" X 4" X 3 MT | ENC048 | Listones de madera 2x2 | unidad MaPreX 'und' no equivale a la del catalogo 'm2' |
| material | CLAVO DE ACERO LISO L=2 1/2" | ACE076 | Clavos de acero 2 1/2 pulg | unidad MaPreX 'pza' no equivale a la del catalogo 'unidad' |
| material | DESENCOFRANTE SIKA | MZ0201 | Desencofrante | unidad MaPreX 'lt' no equivale a la del catalogo 'unidad' |
| material | CEMENTO GRIS PORTLAND SACO 42.5 KG/93,7 LB | CEM019 | Cemento Portland | unidad MaPreX 'sco' no equivale a la del catalogo 'saco' |
| equipo | RETROEXCAVADORA CASE O SIM | MOV027 | Retroexcavadora | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | PICO CON CABO | ALB072 | Pico | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | PALA CUADRADA CON CABO DE MADERA | EZ0576 | Pala | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | CAMION VOLTEO 8 M3 FORD 7000 O SIM | VEH010 | Camion de volteo | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | VEHICULO PARA TRANSPORTE DE PERSONAL | EZ0512 | Vehiculo de transporte | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | SEGUETA AJUSTABLE (ARCO) | CAR010 | Segueta | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | CINTA METRICA 3 MT / CINTA Y CARCAZA METALICA | MED001 | Cinta metrica | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | SIERRA ELECTRICA CIRCULAR D=7 1/4" 110V 1,6 KWH | ALB045 | Sierra circular electrica | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | MARTILLO CARPINTERO NACIONAL 0,6 KGM MANGO MAD | DEM005 | Martillo | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | NIVEL DE 3 BURBUJAS Y 18" | ALB024 | Nivel de mano | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | ALICATE PARA ELECTRICISTA | ELE046 | Alicate | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | MEZCLADORA P/CONCRETO CAP=0,40 M3 12,2 HP (DIESE | CON007 | Mezcladora de concreto | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | VIBRADOR PARA CONCRETO | CON041 | Vibrador de concreto | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | CARRETILLA PARA CONSTRUCCION | ALB073 | Carretilla | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | TOBO PLASTICO CAP= 10 LT DE ALBAÑILERIA | ALB146 | Tobos plasticos | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | COMPACTADORA RANA / PLANCHA 0.50 X 1.0M - 280 KG | CPT018 | Compactadora de percusion tipo sapo | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |
| equipo | HERRAMIENTAS MENORES | ALB213 | Herramientas menores | equipo: fuera de la revaloracion (C6-9); su Precio/Alq. MaPreX no es tarifa diaria (falta el factor Cop/Depr.), se contrasta aparte |

#### civil 001 -> MAPREX-2026-07

Lista `lista_civil_maprex_derivada.csv`: 12 filas; desconocidas al cargarla: 0.

##### Cobertura de insumos del presupuesto

| Tipo | Insumos en los APU | Con precio nuevo | Sin revalorar |
|---|---|---|---|
| material | 14 | 6 | 8 |
| equipo | 20 | 0 | 20 |
| mano_obra | 7 | 7 | 0 |

##### Comparativo por partida

| Partida | Descripcion | PU anterior | PU nuevo | Variacion % | Incidencia % |
|---|---|---|---|---|---|
| LB-01-EXC | Excavación | 8.60 | 7.54 | -12.36 | -0.65 |
| LB-02-TUB | Tubería de 4 pulg | 10.19 | 20.23 | +98.44 | +15.18 |
| LB-03-ENC | Encofrado | 33.24 | 29.38 | -11.60 | -5.76 |
| LB-04-CON | Vaciado de concreto | 242.64 | 273.96 | +12.91 | +3.28 |
| LB-05-REL | Relleno | 52.58 | 36.37 | -30.82 | -1.33 |
| **Total** |  | 1586.61 | 1756.70 | +10.72 | +10.72 |

Insumos con precio cambiado por la lista: 13. `IncidenciaCambio` registradas para las partidas de este presupuesto: 22.

##### Hallazgos por regla

| Regla | Nombre | Antes | Despues | Severidades despues |
|---|---|---|---|---|
| R1 | Trazabilidad geometrica | 3 | 3 | 2 ERROR, 1 ADVERTENCIA |
| R2 | Cierre de la curva de inversion | 0 | 0 | - |
| R3 | Coherencia dimensional | 2 | 2 | 2 ERROR |
| R4 | Correspondencia de especificaciones | 1 | 1 | 1 ERROR |
| R5 | Balance volumetrico | 1 | 1 | 1 ERROR |
| R6 | Criterio de depreciacion | 1 | 1 | 1 ERROR |
| R7 | Conciliacion presupuesto-plan | 0 | 0 | - |
| ATIPICO | (no es regla) | 0 | 2 | 2 ADVERTENCIA |

Antes: NO CUMPLE; despues: NO CUMPLE.

##### Atipicos

Variaciones en el historico al revalorar: 13.

| Insumo | Precio anterior | Precio nuevo | Variacion % | Puntaje | Cambio de esta lista |
|---|---|---|---|---|---|
| Agua | 2.0000 | 11.9205 | +496.03 | -0.286 | si |
| Tubería PVC 4 pulg | 6.0000 | 13.9291 | +132.15 | -0.086 | si |

Hallazgos ATIPICO en el informe nuevo: 2.

#### Contraste de equipos (no se cargan; ruling C6-9)

Tarifa diaria del APU = precio x depreciacion; tarifa diaria MaPreX = Precio/Alq. x Cop/Depr. (la columna Total de `equipos.pdf`).

| Equipo | Partidas | Precio APU | Depr. APU | Tarifa APU | Ref | Precio/Alq. MaPreX | Factor MaPreX | Tarifa MaPreX | MaPreX / APU |
|---|---|---|---|---|---|---|---|---|---|
| Retroexcavadora | LB-01-EXC | 200.00 | 1 | 200.0000 | MOV027 | 110025.92 | 0.0035 | 385.0907 | 1.93 |
| Pico | LB-01-EXC | 25.00 | 0.03 | 0.7500 | ALB072 | 40.53 | 0.033 | 1.3375 | 1.78 |
| Pala | LB-01-EXC | 15.00 | 0.03 | 0.4500 | EZ0576 | 35.76 | 0.0167 | 0.5972 | 1.33 |
| Camión de volteo | LB-01-EXC | 150.00 | 1 | 150.0000 | VEH010 | 113244.45 | 0.004 | 452.9778 | 3.02 |
| Vehículo de transporte | LB-01-EXC, LB-03-ENC, LB-04-CON, LB-05-REL | 50.00 | 1 | 50.0000 | EZ0512 | 214.57 | 1 | 214.5684 | 4.29 |
| Segueta | LB-02-TUB | 15.00 | 0.03 | 0.4500 | CAR010 | 34.57 | 0.022 | 0.7605 | 1.69 |
| Cinta métrica | LB-02-TUB | 15.00 | 0.03 | 0.4500 | MED001 | 17.88 | 0.01 | 0.1788 | 0.40 |
| Vehículo de transporte | LB-02-TUB | 50.00 | 0.03 | 1.5000 | EZ0512 | 214.57 | 1 | 214.5684 | 143.05 |
| Sierra circular eléctrica | LB-03-ENC | 100.00 | 0.03 | 3.0000 | ALB045 | 417.22 | 0.02 | 8.3443 | 2.78 |
| Martillo | LB-03-ENC | 15.00 | 0.03 | 0.4500 | DEM005 | 34.57 | 0.022 | 0.7605 | 1.69 |
| Nivel de mano | LB-03-ENC | 10.00 | 0.03 | 0.3000 | ALB024 | 52.45 | 0.011 | 0.5770 | 1.92 |
| Cinta métrica | LB-03-ENC | 160.00 | 0.03 | 4.8000 | MED001 | 17.88 | 0.01 | 0.1788 | 0.04 |
| Alicate | LB-03-ENC | 20.00 | 0.03 | 0.6000 | ELE046 | 50.07 | 0.003 | 0.1502 | 0.25 |
| Mezcladora de concreto | LB-04-CON | 60.00 | 1 | 60.0000 | CON007 | 9536.37 | 0.007 | 66.7546 | 1.11 |
| Vibrador de concreto | LB-04-CON | 20.00 | 1 | 20.0000 | CON041 | 953.64 | 0.0095 | 9.0596 | 0.45 |
| Carretilla | LB-04-CON | 30.00 | 0.03 | 0.9000 | ALB073 | 241.99 | 0.02 | 4.8397 | 5.38 |
| Nivel de mano | LB-04-CON | 40.00 | 0.03 | 1.2000 | ALB024 | 52.45 | 0.011 | 0.5770 | 0.48 |
| Pala | LB-04-CON | 10.00 | 0.03 | 0.3000 | EZ0576 | 35.76 | 0.0167 | 0.5972 | 1.99 |
| Tobos plásticos | LB-04-CON | 3.00 | 0.03 | 0.0900 | ALB146 | 14.30 | 0.07 | 1.0013 | 11.13 |
| Compactadora de percusión tipo sapo | LB-05-REL | 20.00 | 1 | 20.0000 | CPT018 | 95.36 | 1 | 95.3637 | 4.77 |
| Herramientas menores | LB-05-REL | 1.00 | 1 | 1.0000 | ALB213 | 14.30 | 1 | 14.3046 | 14.30 |

### 3. Telecom: TC-001 y TC-002 (ARENAZA) con la lista MaPreX telecom

#### telecom TC-001 -> TC-001-MAPREX-2026-07

Lista `lista_maprex_2026-07.csv`: 5 filas; desconocidas al cargarla: 0.

##### Cobertura de insumos del presupuesto

| Tipo | Insumos en los APU | Con precio nuevo | Sin revalorar |
|---|---|---|---|
| material | 13 | 4 | 9 |
| equipo | 1 | 0 | 1 |
| mano_obra | 0 | 0 | 0 |

##### Comparativo por partida (solo las que cambian, de 14 renglones)

| Partida | Descripcion | PU anterior | PU nuevo | Variacion % | Incidencia % |
|---|---|---|---|---|---|
| TC-P1-03 | Tubo Corrugado Flexible 1 Pulgada | 3.33 | 2.62 | -21.13 | -5.70 |
| TC-P1-10 | Toma Doble Con Tierra 270 20a Con Placa Blanca | 5.05 | 6.79 | +34.55 | +0.79 |
| TC-P1-11 | Anillo E.m.t. 2 | 3.96 | 9.54 | +140.82 | +1.01 |
| TC-P1-13 | Cajetin Plástico 4x2 Pvc Con Grapa Metálica. | 2.00 | 1.91 | -4.64 | -0.04 |
| **Total** |  | 1109.29 | 1065.48 | -3.95 | -3.95 |

Insumos con precio cambiado por la lista: 5. `IncidenciaCambio` registradas para las partidas de este presupuesto: 4.

##### Hallazgos por regla

| Regla | Nombre | Antes | Despues | Severidades despues |
|---|---|---|---|---|
| R1 | Trazabilidad geometrica | 0 | 0 | - |
| R2 | Cierre de la curva de inversion | 1 | 1 | 1 INFO |
| R3 | Coherencia dimensional | 0 | 0 | - |
| R4 | Correspondencia de especificaciones | 0 | 0 | - |
| R5 | Balance volumetrico | 0 | 0 | - |
| R6 | Criterio de depreciacion | 0 | 0 | - |
| R7 | Conciliacion presupuesto-plan | 1 | 1 | 1 INFO |

Antes: CUMPLE; despues: CUMPLE.

##### Atipicos

Variaciones en el historico al revalorar: 5.
Con menos de 8 variaciones el detector no marca nada (`ml.anomaly.MINIMO_OBSERVACIONES`): no hay comportamiento observado que contrastar.

Hallazgos ATIPICO en el informe nuevo: 0.

#### telecom TC-002 -> TC-002-MAPREX-2026-07

Lista `lista_maprex_2026-07.csv`: 5 filas; desconocidas al cargarla: 0.

##### Cobertura de insumos del presupuesto

| Tipo | Insumos en los APU | Con precio nuevo | Sin revalorar |
|---|---|---|---|
| material | 27 | 4 | 23 |
| equipo | 1 | 0 | 1 |
| mano_obra | 0 | 0 | 0 |

##### Comparativo por partida (solo las que cambian, de 26 renglones)

| Partida | Descripcion | PU anterior | PU nuevo | Variacion % | Incidencia % |
|---|---|---|---|---|---|
| TC-P2-05 | Tubo Corrugado Flexible 1 Pulgada 30 MTS | 3.33 | 2.62 | -21.13 | -1.17 |
| TC-P2-23 | Toma Doble Con Tierra 270 20a Con Placa Blanca | 5.05 | 6.79 | +34.55 | +0.16 |
| TC-P2-24 | Anillo E.m.t. 2 | 3.96 | 9.54 | +140.82 | +0.21 |
| TC-P2-25 | Cajetin Plástico 4x2 Pvc Con Grapa Metálica. | 2.00 | 1.91 | -4.64 | -0.01 |
| **Total** |  | 5410.73 | 5366.92 | -0.81 | -0.81 |

Insumos con precio cambiado por la lista: 5. `IncidenciaCambio` registradas para las partidas de este presupuesto: 0.

##### Hallazgos por regla

| Regla | Nombre | Antes | Despues | Severidades despues |
|---|---|---|---|---|
| R1 | Trazabilidad geometrica | 1 | 1 | 1 ERROR |
| R2 | Cierre de la curva de inversion | 1 | 1 | 1 INFO |
| R3 | Coherencia dimensional | 0 | 0 | - |
| R4 | Correspondencia de especificaciones | 0 | 0 | - |
| R5 | Balance volumetrico | 0 | 0 | - |
| R6 | Criterio de depreciacion | 0 | 0 | - |
| R7 | Conciliacion presupuesto-plan | 1 | 1 | 1 INFO |

Antes: NO CUMPLE; despues: NO CUMPLE.

##### Atipicos

Variaciones en el historico al revalorar: 5.
Con menos de 8 variaciones el detector no marca nada (`ml.anomaly.MINIMO_OBSERVACIONES`): no hay comportamiento observado que contrastar.

Hallazgos ATIPICO en el informe nuevo: 0.

### 4. Industrial y sistemas: comprobacion de la siembra

| Caso | Lista | Filas | Desconocidas | Insumos afectados | Total anterior | Total nuevo | Flujo 3a |
|---|---|---|---|---|---|---|---|
| MNT-001 | lista_maprex_2026-07.csv | 9 | 0 | 0 | 18124.09 | 18124.09 | si |
| SIS-001 | lista_tarifas_2026-07.csv | 3 | 0 | 0 | 16093.89 | 16093.89 | si |

### 5. Salvedades

- Los casos son didacticos (NORMAS.md §1): esto mide su sensibilidad a precios de referencia publicados, no el costo de ninguna obra.
- El bono de alimentacion no se revalora: es un parametro de costo (`ParametrosCosto.bono_alimentacion` = 1.00 USD por obrero y dia), no un precio de la lista; MaPreX trae 6.2200 USD/dia para el Ayudante N2 (Ref 1-1.2, bono_bs de `referencia_civil.csv` a la tasa 633.3644), que solo entraria como escenario (UC-08).
- Vigencia unica 2026-07-09 para la lista civil derivada, aunque la mano de obra de MaPreX es del 01/07/2026.
- Tasa 633,3644 Bs/USD al 01/07/2026; cada `precio_usd` de `referencia_civil.csv` que se usa se verifico contra su `precio_bs` con la tasa 633.3644.
- No se convierte ninguna unidad: una fila cuya unidad MaPreX no equivale a la del catalogo se excluye y se reporta (`sco` no es alias de `saco` en `core.contracts.unidades`).
- Los equipos no se revaloran (C6-9): su Precio/Alq. MaPreX no es una tarifa diaria sin el factor Cop/Depr.; se contrastan aparte.
- Descripciones truncadas por el propio PDF de MaPreX (22), conservadas tal cual: referencia_sistemas.csv: DIS001, DIS003, DIS004, DIS014, DIS025, DIS027, DIS028, DIS029, DIS030, DIS031, DIS032, DIS033, DIS034, DIS038, DIS039, DIS040, DIS041, DIS042, DIS043, DIS044; referencia_telecom.csv: ELA633, ELC057. Una lista que las cite casa solo con un catalogo sembrado con la misma grafia.

## Lectura

**Civil (001): el total pasa de 1 586,61 a 1 756,70 USD (+10,72 %), y lo explica casi todo una
partida.** La tubería sube 98,44 % (incidencia +15,18 puntos sobre el total): su material pasa de 6
a 13,9291 USD/m (PLOA38) y entra 1,05 m por pieza. El concreto sube 12,91 % porque la arena lavada
(30 → 59,6023 USD/m³) casi se duplica (+98,67 %) y la piedra picada (35 → 59,6023) sube 70,29 %; el
cemento, el insumo de más peso de esa partida, no se revalora (ver abajo). Las otras tres partidas
bajan: la excavación (−12,36 %) y el encofrado (−11,60 %) solo por la mano de obra, porque sus
materiales no cambian (la excavación no tiene y los del encofrado no casan), y el relleno (−30,82 %)
por el material granular (12 → 7,1523 USD/m³) y la mano de obra, pese a que su agua sube de 2 a
11,9205 USD/m³. La mano de obra baja en todas: los jornales MaPreX del tabulador de la construcción
(1,78 a 2,56 USD/día) quedan por debajo de los sueldos del ejercicio (3 a 5 USD/día), y el FCAS de
600 % multiplica esa diferencia por siete. El bono de alimentación sigue en 1,00 USD por obrero y
día, cuando MaPreX trae 6,2200 para el ayudante N2 (Ref 1‑1.2: 3 939,53 Bs a la tasa): si se
aplicara (escenario UC‑08, fuera de esta prueba), la baja de la mano de obra se reduciría.

**Solo 12 de las 37 referencias civiles se pueden cargar sin convertir unidades.** De los 13
materiales casan 5; los otros 8 tienen en MaPreX otra unidad de venta (`pza`, `env`, `lt`, `und`,
`m3` o `sco` frente a `unidad`, `m2` o `saco`). La prueba no convierte ninguna: `pieza` y `unidad`
son unidades distintas a propósito en `core.contracts.unidades` (la regla R3 depende de ello), la
madera se consume en m² en el APU y se vende en m³, y `sco` no es un alias de `saco`. Por eso el
cemento, los PVC accesorios, la madera, los listones, los clavos, el pegamento y el desencofrante
conservan su precio del ejercicio. Cobertura de insumos del 001: 6 de 14 materiales (el agua cuenta
dos veces: el catálogo la tiene como dos variantes, 12 y 2 USD, y la fila MaPreX actualiza ambas),
7 de 7 roles de mano de obra y 0 de 20 equipos.

**Equipos (contraste, no carga).** La tarifa diaria MaPreX (Precio/Alq. × Cop/Depr., la columna
Total de `equipos.pdf`) supera a la del APU en los equipos pesados (retroexcavadora 1,93×, camión de
volteo 3,02×, vehículo de transporte 4,29× con factor 1,00) y queda por debajo en algunos menores
(vibrador 0,45×, alicate 0,25×, la cinta métrica de 160 USD del encofrado 0,04×). El hallazgo 7 de
la línea base se ve de nuevo: el mismo vehículo con factor 0,03 en la tubería da una tarifa 143
veces menor que la de MaPreX, que para ese equipo usa 1,00, el mismo factor que los otros cuatro
APU.

**Hallazgos: los precios no mueven ninguna de las siete reglas.** R1 (3), R3 (2), R4 (1), R5 (1) y
R6 (1) son los mismos antes y después: miden cantidades, unidades, especificaciones, balance y
depreciación, que la revaloración no toca (lo único que cambia es la lista de precios que valora las
mismas composiciones, `core/budget/actualizacion.py`). R2 y R7 dan 0 porque el 001 se elabora con
`plan_secuencial`, cuya curva cierra al 100 % por construcción; la curva auditada del 99,30 % no
interviene en esta prueba. Lo nuevo son **dos ATIPICO** (RF‑29, expediente C6.5): con 13 variaciones
en el histórico (el mínimo del detector es 8) el Isolation Forest marca la variante de agua de 2 USD
(+496,03 %, puntaje −0,286) y la tubería (+132,15 %, −0,086), y las dos entran al informe de la
versión nueva como ADVERTENCIA.

**Listado crudo `lista_maprex_usd.csv` (111 filas): casi nada casa sin una lista derivada.** Sobre
la base civil casa una fila (`ARENA LAVADA`, que coincide con «Arena lavada» del catálogo), sobre la
telecom ninguna (el catálogo guarda las descripciones de ARENAZA), sobre la industrial 6 y sobre la
de sistemas ninguna. Las 7 rechazadas por el flujo 2b son todas mano de obra o equipo cotizados por
`dia` cuya descripción el catálogo conoce **sin unidad**: las listas de dominio
(`data/industrial/fuentes/`, `data/sistemas/fuentes/`) dejan esa celda vacía, el listado crudo no.
Es el riesgo que anticipaba C6-plan §6 (vocabulario, unidades y valor de reposición): se reporta y
no se convierte.

**Telecom.** TC‑001 pasa de 1 109,29 a 1 065,48 USD (−3,95 %) y TC‑002 de 5 410,73 a 5 366,92
(−0,81 %): de sus 14 y 26 renglones cambian 4 en cada uno (el tubo corrugado baja 21,13 %; el anillo
EMT sube 140,82 %, la toma doble 34,55 % y el cajetín baja 4,64 %). Con 5 variaciones el detector no
marca (mínimo 8), y así lo dice el informe. R2 y R7 son INFO (sin plan, no aplicables) y el 80/90 del
tubo corrugado de TC‑002 (R1, ERROR) sigue en el informe revalorado.

**Industrial y sistemas: flujo 3a confirmado.** `MNT-001` (18 124,09 USD) y `SIS-001` (16 093,89
USD), revalorados con la lista de la que salieron, no cambian ningún insumo ni el total: la siembra
reproduce sus listados MaPreX y CIV.

**Una observación sobre el núcleo (no se parchea; NORMAS.md §9).** Al revalorar TC‑002 con la misma
lista MaPreX que ya revaloró TC‑001 (mismo proyecto, mismo par de listas), `actualizar_precios` no
registra ninguna `IncidenciaCambio` para las partidas de TC‑002 (0 frente a 4 de TC‑001):
`_registrar_incidencias` (`core/budget/actualizacion.py`) considera ya registrado el historial si
existe cualquier incidencia de esos cambios, sin mirar de qué partidas son. El comparativo y el
informe de TC‑002 sí salen bien; lo que se pierde es su fila en la tabla que alimenta el módulo
predictivo. Queda anotado para decidir si entra al inventario.

**Salvedades** (además de las de la sección 5): la lista civil lleva una sola vigencia; las
descripciones truncadas por el PDF se conservan tal cual; la prueba no fija ningún criterio de
equivalencia nuevo, usa los de M0.2 que ya declaraban las notas del CSV.
