# `data/sistemas/fuentes/` — tarifas del dominio sistemas (Sesión M3.1)

Sesión M3.1 del [PLAN_MULTIDOMINIO.md](../../../PLAN_MULTIDOMINIO.md): las tarifas con las que se
costea un punto de función salen del **tabulador CIV al 01/07/2026** (Colegio de Ingenieros de
Venezuela, escalafón P‑1…P‑10), tal como lo publica el listado de mano de obra de MaPreX y como
lo estructuró la Sesión M0.2 en `data/precios/maprex_2026-07/referencia_sistemas.csv` (43 filas,
cada una con `ref_maprex`, jornal en Bs y en USD). **Las tarifas tienen fuente; la productividad
no todavía:** se declara como supuesto, con esta redacción literal y sin cita inventada.

> **Supuestos de esta sesión (todos marcados `SUPUESTO (pendiente validacion del autor)`):**
> jornada de 8 h para convertir jornal en tarifa horaria; correspondencia rol del APU ↔ fila del
> tabulador; productividad HH/PF; reparto de horas por rol; estructura de costos sin prestaciones
> ni bono sobre honorarios profesionales. El autor los confirma o corrige; ninguno bloquea GM3,
> cuyo criterio es «tarifas publicadas (CIV o encuesta fechada) y productividad HH/PF con fuente
> declarada».

## Archivos

| Archivo | Contenido | Fuente |
|---|---|---|
| `README.md` | Esta declaración: fuente, vigencia, conversiones, correspondencias y supuestos | — |
| `lista_tarifas_2026-07.csv` | Lista canónica de UC‑02 (`tipo,insumo,unidad,precio`): los 3 roles del APU a su **jornal** USD del tabulador (equipos y mano de obra van sin unidad en el catálogo) | `referencia_sistemas.csv` (M0.2) |

La **única copia estructurada** de tarifas y composición es `tests/fixtures/tarifas_sistemas.py`,
que lee `referencia_sistemas.csv` al importarse (no transcribe precios) y deriva
`lista_tarifas_2026-07.csv`; `tests/unit/test_tarifas_sistemas.py` comprueba ambas cosas.

## Fuente y vigencia

Tabulador CIV al **01/07/2026** (`mano_de_obra.pdf`, agrupación `TAB CIV`), en bolívares,
convertido por M0.2 a USD con la tasa declarada en el propio listado (633,3644 Bs/USD,
01/07/2026), cuantizado a 0,0001. La columna `bono_bs` del tabulador CIV es 0,00 en las 43 filas:
a diferencia del tabulador de la construcción (industrial), el CIV no publica bono de
alimentación. Las descripciones se conservan **literales**, incluidas las truncadas por el ancho
fijo de columna del reporte MaPreX (M0.2 verificó que el texto faltante no existe en el PDF).

## (a) Conversión jornal → tarifa horaria — SUPUESTO (pendiente validacion del autor)

`tarifa_hh = jornal / 8 h`, cuantizada a 0,0001 USD. Se deriva del jornal en USD de M0.2 (ya
convertido con la tasa única); calcularla desde bolívares (`jornal_bs / 8 / tasa`) difiere como
máximo en 0,0001 por el orden del redondeo. La jornada de 8 h es un supuesto del autor: el
tabulador publica jornales diarios y no declara horas.

**El catálogo guarda el jornal, no la tarifa horaria.** `LineaManoObra.sueldo` es, por contrato,
un jornal diario, y la lista de precios de UC‑02 empareja mano de obra por descripción sin
unidad. Las horas de cada rol por punto de función entran como fracción de obrero‑día
(`cantidad = horas / 8`), de modo que `cantidad × jornal` es exactamente `horas × tarifa_hh`
(salvo el redondeo de la tarifa). La tarifa horaria se publica aquí y en el fixture como dato
derivado, para el lector y para la plantilla `data/sistemas/plantilla_precios.csv` (que pide
precios por hora).

## (b) Correspondencia rol del APU ↔ fila del tabulador — SUPUESTO (pendiente validacion del autor)

Filas **existentes** de `referencia_sistemas.csv`, citadas por Ref, con el criterio que sugiere el
PLAN (analista ↔ ingeniero analista P‑5; desarrollador ↔ ingeniero computista P‑9; líder ↔
gerente de proyectos):

| Rol del APU | Ref | Descripción MaPreX (literal) | Jornal (Bs) | Jornal (USD) | Tarifa HH (USD) |
|---|---|---|---|---|---|
| Analista funcional | `DIS019` | INGENIERO P-5 CIV ANALISTA DIAGNOSTICO | 39 224,26 | 61,9300 | 7,7413 |
| Desarrollador (desarrollo y pruebas) | `DIS042` | INGENIERO COMPUTISTA P-9 CIV (19-20 AÑOS EX | 56 458,10 | 89,1400 | 11,1425 |
| Líder de proyecto | `DIS036` | GERENTE DE PROYECTOS C/CERTIFICACION | 107 671,95 | 170,0000 | 21,2500 |

Roles de la plantilla sin fila propia: **ingeniero de pruebas (QA)** y **arquitecto de software**
no existen en el tabulador CIV; las horas de pruebas se asignan al desarrollador (el computista
P‑9 es el único perfil de computación del escalafón) y no se costea un arquitecto aparte.
Frontend y backend se costean con el mismo perfil. Una encuesta salarial TI fechada
(protocolo §2.4, `data/sistemas/fuentes/`) puede aportar esos roles y sustituir estas filas por
UC‑02.

## (c) Productividad — SUPUESTO (pendiente validacion del autor)

SUPUESTO (pendiente validacion del autor): 8 HH/PF, rango tipico reportado por benchmarks de la
industria (ISBSG); la cita definitiva la fija el autor en el marco teorico.

Con jornada de 8 h, 8 HH/PF equivale a **un obrero‑día por punto de función**, lo que hace la
composición legible: las cantidades de mano de obra por PF suman exactamente 1.

## Reparto de horas por rol — SUPUESTO (pendiente validacion del autor)

| Rol | Fracción | Horas por PF | Obrero‑días por PF (`cantidad`) |
|---|---|---|---|
| Analista funcional | 20 % | 1,6 | 0,20 |
| Desarrollador (desarrollo y pruebas) | 75 % | 6,0 | 0,75 |
| Líder de proyecto | 5 % | 0,4 | 0,05 |
| **Total** | **100 %** | **8,0** | **1,00** |

## Estructura de costos — SUPUESTO (pendiente validacion del autor)

`PARAMETROS_SISTEMAS = ParametrosCosto(fcas=0, bono_alimentacion=0, administracion=0,15,
utilidad=0,10)`. El tabulador CIV es un tabulador de **sueldos mínimos profesionales**: el factor
de prestaciones del 600 % de CLAUDE.md §4 es la convención de la mano de obra de la construcción
y no hay fuente que lo respalde para profesionales; el CIV tampoco publica bono. Se dejan en cero
hasta la decisión sobre la fuente del FCAS del dossier G0 (`docs/dossier_g0.md`); administración
y utilidad se mantienen en sus valores por defecto porque una casa de software también los
carga. Civil e industrial siguen aplicando la estructura completa: el motor recibe un
`ParametrosCosto` por presupuesto y no cambia.

## El APU de un punto de función

Partida plantilla `SIS-PF` (un punto de función; unidad `pf`, la que emite `AdaptadorSistemas`,
sin alias en `core.contracts.unidades`, ver bitácora I5 sistemas). Rendimiento 1 PF/día (con las
cantidades expresadas en obrero‑días por PF, la división entre el rendimiento es neutra). Sin
materiales ni equipos: las licencias y herramientas no están en el tabulador y no se inventan.

| Línea | Cantidad (obrero‑día/PF) | Jornal (USD) | Cantidad × jornal |
|---|---|---|---|
| INGENIERO P-5 CIV ANALISTA DIAGNOSTICO | 0,20 | 61,93 | 12,386 |
| INGENIERO COMPUTISTA P-9 CIV (19-20 AÑOS EX | 0,75 | 89,14 | 66,855 |
| GERENTE DE PROYECTOS C/CERTIFICACION | 0,05 | 170,00 | 8,500 |
| **Mano de obra = costo directo** | | | **87,741** |
| × 1,15 (administración) | | | 100,90215 |
| **× 1,10 (utilidad) = precio unitario** | | | **110,992365 USD/PF** |

Calculado a mano con la fórmula de CLAUDE.md §4 antes de correr el motor; la prueba lo fija como
regresión exacta. Cada caso de uso de `data/samples/sistemas/alcance_funcional.csv` recibe esta
misma composición bajo su propio código (`SIS-PRES-01`, …), porque el alcance funcional no
aporta datos para diferenciar la productividad por módulo sin inventarla.

## Qué mejoraría GM3

- Cita bibliográfica de la productividad HH/PF (ISBSG o literatura del marco teórico), fijada
  por el autor.
- Encuesta salarial TI fechada (roles QA, arquitecto, frontend/backend) como lista nueva por
  UC‑02, con evidencia archivada en esta carpeta.
