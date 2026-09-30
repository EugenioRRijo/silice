# `data/industrial/fuentes/` — precios del catálogo de mantenimiento (Sesión M2.1)

> **Degradación GM2 declarada.** No llegaron cotizaciones de campo; los precios provienen de la
> referencia nacional **MaPreX julio 2026** (proxy fechado, degradación GM2 declarada según
> PLAN_MULTIDOMINIO §2: «si no llegan cotizaciones: … siguiente instancia: referencia nacional
> MaPreX jul‑2026 declarada como proxy fechado»). Cada precio cita archivo + Ref. Los supuestos de
> alcance de cada intervención están listados abajo, marcados como tales.

Sesión M2.1 del [PLAN_MULTIDOMINIO.md](../../../PLAN_MULTIDOMINIO.md). Esta carpeta es la que el
[protocolo de precios](../../../docs/protocolo_precios.md) §1.3 reserva para la evidencia
específica del dominio industrial (cotizaciones, facturas). Hoy no contiene ninguna cotización:
contiene la declaración de la degradación, los supuestos y la lista canónica de UC‑02 derivada de
la referencia MaPreX. Cuando el autor complete la ronda de cotizaciones
(`data/industrial/plantilla_precios.csv`, Fase M0), la evidencia se archiva aquí y sustituye el
proxy insumo por insumo.

## Archivos

| Archivo | Contenido | Fuente |
|---|---|---|
| `README.md` | Esta declaración: degradación, activos, alcances supuestos, correspondencia insumo ↔ Ref | — |
| `lista_maprex_2026-07.csv` | Lista canónica de UC‑02 (`tipo,insumo,unidad,precio`) con los 9 insumos del catálogo de mantenimiento a precio MaPreX jul‑2026 (USD) | `data/precios/maprex_2026-07/referencia_industrial.csv` (Sesión M0.2) |

La **única copia estructurada** de las composiciones es `tests/fixtures/mantenimiento_industrial.py`,
que **lee los precios de `referencia_industrial.csv` al importarse** (no los transcribe: principio
DRY, NORMAS.md §2). `tests/unit/test_mantenimiento_industrial.py` comprueba que cada línea del
fixture coincide con su fila de la referencia y que la lista canónica de esta carpeta es
exactamente la que el fixture deriva.

## Vigencia y moneda

Materiales y equipos: **09/07/2026** (`materiales.pdf`, `equipos.pdf`). Mano de obra:
**01/07/2026** (`mano_de_obra.pdf`, tabulador de la construcción). Precios en USD convertidos por
M0.2 desde bolívares con la tasa declarada en el propio listado, 633,3644 Bs/USD (01/07/2026),
cuantizados a 0,0001. La lista canónica declara como vigencia la de materiales y equipos
(09/07/2026), la más reciente de las dos.

## Activos elegidos (4 de los 10 de `data/samples/industrial/activos_planta.csv`)

Se eligieron los activos rotativos, que son los que tienen repuestos de mantenimiento genuinos
en la referencia MaPreX (rodamientos, grasa, correas, filtros, aceite, sello mecánico). Los demás
quedan fuera de esta sesión, no por falta de interés sino porque su repuesto MaPreX es un proxy de
capacidad o diámetro (transformadores `ELA073`/`ELA067`, válvula `PLOG46`) o no existe (tableros).

| Partida | Activo | Intervenciones (adaptador: `frecuencia_anual × horizonte_anios`) |
|---|---|---|
| `MNT-BOM-CEN` | `IN-001` Bomba centrífuga de agua potable, 15 HP | 4 × 5 = 20 |
| `MNT-COM-REC` | `IN-003` Compresor de aire reciprocante, 25 HP | 6 × 5 = 30 |
| `MNT-MOT-TRI` | `IN-006` Motor eléctrico trifásico de inducción, 50 HP | 4 × 5 = 20 |
| `MNT-BOM-SUM` | `IN-007` Bomba sumergible de aguas residuales, 10 HP | 6 × 5 = 30 |

## Alcance de cada intervención — SUPUESTO (pendiente validacion del autor)

Ninguna orden de trabajo real respalda estas cantidades: son el alcance **supuesto** de una
intervención preventiva, elegido para que cada partida tenga repuestos (materiales), herramienta
(equipo) y técnico (mano de obra), como pide la sesión. Las cantidades fraccionarias expresan
consumo prorrateado entre intervenciones (por ejemplo, «0,25 sello» = un sello mecánico cada
cuatro intervenciones). El autor debe confirmarlas o corregirlas con la ronda de cotizaciones.

| Partida | Materiales (repuestos) | Equipo (herramienta) | Mano de obra (técnicos, 1 día) |
|---|---|---|---|
| `MNT-BOM-CEN` | 0,25 sello mecánico tipo cartucho · 0,5 rodamiento · 1 envase de grasa | 1 día de taladro de banco (herramienta de taller) | 1 mecánico de 1ra |
| `MNT-COM-REC` | 4 l de aceite · 1 filtro de aceite · 0,5 correa A41 | 1 día de taladro de banco | 1 mecánico de 1ra |
| `MNT-MOT-TRI` | 0,5 rodamiento · 1 envase de grasa · 0,5 correa A41 | 1 día de taladro de banco | 1 mecánico de 1ra + 1 electricista de 1ra |
| `MNT-BOM-SUM` | 0,25 sello mecánico tipo cartucho · 0,5 rodamiento · 1 envase de grasa | — (sin equipo MaPreX aplicable: el izaje de la bomba no está en la referencia) | 1 mecánico de 1ra + 1 electricista de 1ra |

Otros supuestos, todos **SUPUESTO (pendiente validacion del autor)**:

- **Rendimiento = 1 intervención por día de cuadrilla** en las cuatro partidas. La bitácora de la
  Sesión I5 industrial ya anticipó que una intervención de mantenimiento no tiene el rendimiento
  «unidades por día» de una partida civil; se toma un día por evento.
- **El taladro industrial de banco (`EZ0453`) representa la herramienta de taller** de las tres
  intervenciones que se hacen en taller. Es el único equipo de taller que M0.2 estructuró para
  este dominio; se usa con su factor MaPreX (1,000000: precio de alquiler diario completo).
- **Los repuestos son proxies de categoría** cuando la referencia no tiene el SKU exacto
  (`MZ0623` es «rodamientos de alternador»: MaPreX no lista un rodamiento industrial genérico).

## Correspondencia insumo ↔ Ref MaPreX

Las descripciones del catálogo son **las de MaPreX, literales**, para que la procedencia sea
evidente en el catálogo, en el informe de auditoría y en la lista canónica.

| Tipo | Insumo (descripción MaPreX) | Unidad | Precio (USD) | Ref | Archivo | Usado en |
|---|---|---|---|---|---|---|
| material | MAT. P/INSTALACION SELLO MECANICO TIPO CARTUCHO | sg | 298,0117 | `MZ0471` | `materiales.pdf` | BOM-CEN, BOM-SUM |
| material | RODAMIENTOS DE ALTERNADOR | unidad | 69,1387 | `MZ0623` | `materiales.pdf` | BOM-CEN, MOT-TRI, BOM-SUM |
| material | GRASA PARA RODAMIENTOS | env | 20,2648 | `MZ0341` | `materiales.pdf` | BOM-CEN, MOT-TRI, BOM-SUM |
| material | ACEITE PARA MAQUINAS/MOTORES | lt | 15,4966 | `COM032` | `materiales.pdf` | COM-REC |
| material | FILTRO DE ACEITE DE MOTOR | unidad | 14,3046 | `MZ0294` | `materiales.pdf` | COM-REC |
| material | CORREA INDUSTRIAL A41 PARA MOTOR | pieza | 10,7284 | `MEC528` | `materiales.pdf` | COM-REC, MOT-TRI |
| equipo | TALADRO INDUSTRIAL BANCO 3/4" 750W | (día; factor 1,000000) | 21,4568 | `EZ0453` | `equipos.pdf` | BOM-CEN, COM-REC, MOT-TRI |
| mano_obra | MECANICO DE EQUIPO PESADO DE 1RA -N8 | (jornal) | 2,5560 | `24-6.7` | `mano_de_obra.pdf` | las cuatro |
| mano_obra | ELECTRICISTA DE 1RA -N5 | (jornal) | 2,1877 | `19-215` | `mano_de_obra.pdf` | MOT-TRI, BOM-SUM |

Las unidades `und` y `pza` de MaPreX se guardan en su forma canónica (`unidad`, `pieza`,
`core.contracts.unidades`); `env`, `lt` y `sg` no tienen alias y pasan tal cual. Equipos y mano
de obra no llevan unidad en el catálogo (columna vacía en la lista canónica, como en civil y
telecom); la tarifa de ambos es diaria.

## Mano de obra: jornal del tabulador y estructura de costos

`LineaManoObra.sueldo` es el **jornal** MaPreX en USD (columna `precio_usd` de la referencia:
1 618,86 Bs → 2,5560 para el mecánico; 1 385,63 Bs → 2,1877 para el electricista). La estructura
sobre ese jornal —FCAS, bono de alimentación, administración y utilidad— es la de
`core.contracts.apu.ParametrosCosto` **por defecto** (600 %, 1,00 USD/obrero‑día, 15 %, 10 %), la
misma de la línea base civil, porque el motor recibe un único juego de parámetros por presupuesto.

Esto deja una **discrepancia declarada, no resuelta aquí**: MaPreX trae un bono de alimentación
propio por nivel (`bono_bs`: 3 445,50 Bs ≈ 5,44 USD/día para el N8; 3 679,85 Bs ≈ 5,81 USD/día
para el N5), distinto del 1,00 USD del contrato y distinto entre niveles, así que no cabe en un
parámetro único de presupuesto. Es evidencia para la decisión sobre la fuente del FCAS y del bono
del dossier G0 (`docs/dossier_g0.md`); hasta que el tutor decida, esta sesión usa los valores por
defecto y lo deja escrito.

## Qué falta para cruzar GM2 sin degradación

La ronda de cotizaciones del autor (≥ 3 activos, `data/industrial/plantilla_precios.csv`,
protocolo §2.3). Cada cotización fechada se archiva en esta carpeta y su precio sustituye al
proxy MaPreX del insumo correspondiente por UC‑02 (lista nueva con fecha de la cotización); el
fixture no cambia de forma, solo de fuente de precios, y `referencia_industrial.csv` pasa a ser
la lista anterior del histórico de `CambioPrecio`.
