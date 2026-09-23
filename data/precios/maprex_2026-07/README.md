# Listados MaPreX — julio 2026 (referencia de precios)

Evidencia primaria transversal a los cuatro dominios, aportada por el autor el 02/09/2026.
Son los tres listados oficiales del software **MaPreX v26.0.0.1** (base de datos
`BDLaing08072026.mdb` del 08/07/2026, zona predeterminada), impresos el 13/07/2026. Los archivos
originales se llamaban «Materiales Julio 2026.pdf», «Equipos Julio 2026.pdf» y «Mano de Obra
Julio 2026.pdf»; aquí se renombran sin cambiar su contenido.

**Papel: referencia y contexto de precios, no lista vigente.** Los listados son de julio 2026
(un mes pasado respecto de su incorporación). Sirven para contrastar, componer proxies fechados y
declarar criterios; una ronda vigente de precios sigue pendiente como trabajo de campo
([PLAN_MULTIDOMINIO.md](../../../PLAN_MULTIDOMINIO.md), Fase M0).

## Moneda y tasa

Todos los precios están en **bolívares**. La tasa declarada dentro del propio listado de mano de
obra (agrupaciones «01JUL @ 633,3644 BS/$») es **633,3644 Bs/USD al 01/07/2026**. Toda conversión
a USD que se derive de estos PDF debe registrar esa tasa y esa fecha; nunca convertir con una tasa
de otro día sin declararlo.

## Los tres archivos

| Archivo | Págs. | Renglones (aprox.) | Columnas | Fecha de precio |
|---|---|---|---|---|
| `materiales.pdf` | 190 | ≈ 12 500 | Ref, Descripción, Und, Fecha, Precio, Proveedor | 09/07/2026 |
| `equipos.pdf` | 51 | ≈ 2 850 | Ref, Descripción, Precio/Alq., **Cop/Depr.**, Total, Proveedor, Fecha | 09/07/2026 |
| `mano_de_obra.pdf` | 13 | ≈ 790 | Ref, Descripción, Jornal, Bono, Agrupación, Nivel/Oficio, Fecha | 01/07/2026 |

Particularidades que importan a la tesis:

- **`equipos.pdf` trae el factor de depreciación por equipo** (columna Cop/Depr.;
  Total = Precio × factor). Es un criterio de mercado externo y fechado para la regla **R6**
  (`CriterioDepreciacion`): permite declarar el criterio en vez de heredarlo del APU manual.
- **`mano_de_obra.pdf` agrupa por tabulador**: construcción («SAL CONST» del 25/03/2026 + bono
  equivalente a 240 USD/mes), **tabulador CIV al 01/07/2026 (43 filas, escalafón P-1…P-10**, con
  ingeniero computista, analista de telecomunicaciones, ingeniero de mantenimiento y gerente de
  proyectos**)**, sector petrolero, PEQUIVEN, METOR, petroquímica y profesionales/TSU. El par
  jornal + bono del tabulador de la construcción es evidencia para la decisión de fuente del FCAS
  del [dossier G0](../../../docs/dossier_g0.md).

## Cobertura por dominio

| Dominio | Qué hay | Qué NO hay |
|---|---|---|
| civil | Los insumos de la línea base: PVC (≈ 829 menciones), cemento, arena, encofrado; retroexcavadoras (49) y compactadoras (44) en equipos; tabulador de la construcción en MO | — |
| telecom | Fibra óptica (≈ 58), UTP, patch panels, racks, telefonía, coaxial; fusionadoras y equipos de red | precios de distribuidores específicos como los de ARENAZA (sirven de contraste, no de reemplazo) |
| industrial | Válvulas (≈ 172), rodamientos, compresores, correas; herramientas y equipos de taller; mecánicos y electricistas por tabulador | cotizaciones reales de repuestos/servicios de los activos concretos de `activos_planta.csv` |
| sistemas | El tabulador CIV (roles de ingeniería, incluido computista y analistas) | tarifas TI de mercado (programadores/desarrolladores) y productividad HH/PF — esta última siempre sale de benchmark declarado (ISBSG) |

## Reglas de uso

1. Nada de estos PDF entra al catálogo directamente. Primero se estructura en CSV canónico
   (Sesión M0.2 del PLAN_MULTIDOMINIO), **verificando cada fila a mano contra el PDF**, con
   columnas de `origen` (archivo + Ref MaPreX) y `fecha_vigencia` (2026-07-09; mano de obra
   2026-07-01), y la conversión Bs→USD con la tasa declarada arriba.
2. Solo se extraen los insumos que los catálogos necesitan; jamás el volcado completo de
   ≈ 16 000 renglones.
3. Cualquier precio citado en la tesis referencia archivo, Ref y fecha.

## CSV de referencia (Sesión M0.2)

`scripts/extraer_maprex.py` (ejecutar con `uv run --with pymupdf python scripts/extraer_maprex.py`)
parsea los tres PDF y escribe cuatro CSV en esta misma carpeta, uno por dominio, con la cabecera
exacta:

```
tipo,insumo,unidad,precio_bs,bono_bs,factor_depreciacion,precio_usd,fecha_vigencia,archivo,ref_maprex,notas
```

`tipo` es `material` | `equipo` | `mano_obra`; `bono_bs` solo aplica a mano de obra y
`factor_depreciacion` solo a equipos (las demás filas dejan esas columnas vacías). `precio_usd`
se calcula como `(precio_bs / 633,3644).quantize(0,0001, ROUND_HALF_UP)`. Cada fila fue elegida a
mano y verificada dígito a dígito contra el PDF (Ref, descripción, unidad y precio); las
decisiones de equivalencia y las filas sin equivalente claro (omitidas, nunca adivinadas) están en
[docs/bitacora/2026-09-02-M0.2-referencia-maprex.md](../../bitacora/2026-09-02-M0.2-referencia-maprex.md).

| CSV | Alcance | Filas |
|---|---|---|
| `referencia_civil.csv` | Los 37 insumos (materiales, equipos y roles de mano de obra) de los cinco APU de `tests/fixtures/apu_linea_base.py` | 37 |
| `referencia_telecom.csv` | Renglones comparables con los presupuestos ARENAZA (`data/telecom/plantilla_precios.csv`): UTP, tubo corrugado, conectores RJ45, canalización, cajetines, más fibra óptica, patch panel y rack como referencia de categoría | 18 |
| `referencia_industrial.csv` | Repuestos y servicios aplicables a los activos de `data/samples/industrial/activos_planta.csv`: rodamientos, correas, válvulas, aceites, filtros, sello mecánico, transformadores y técnicos por tabulador | 13 |
| `referencia_sistemas.csv` | Las 43 filas completas del tabulador CIV (agrupación `TAB CIV`, escalafón P-1…P-10) | 43 |

Algunas descripciones de MaPreX vienen truncadas por el ancho fijo de columna del propio reporte
(terminan en `\` o cortan una palabra a mitad, típicamente en el tabulador CIV cuando el nombre del
rol es largo). Se conservan tal como las imprime el PDF —no se completan por conjetura— y se marcan
en `notas` con «descripcion truncada en el PDF».

## Lista canónica en USD (`lista_maprex_usd.csv`)

`scripts/lista_maprex_usd.py` deriva de los cuatro CSV de referencia anteriores el formato de
cuatro columnas que exige el cargador de UC‑02 (`tipo,insumo,unidad,precio`,
`core.catalog.precios.COLUMNAS_ARCHIVO`), copiando como texto la columna `precio_usd` ya calculada
arriba, sin volver a tocar bolívares. Sirve para cargar MaPreX como una lista de precios más y
contrastarla con lo que compone el sistema.

**ADVERTENCIA para `tipo=equipo`:** el `precio` de esta lista es el valor de reposición del activo
completo, no una tarifa diaria de uso. Ejemplo, la fila
`equipo,CAMION VOLTEO 8 M3 FORD 7000 O SIM,dia,113244.4451`: no dice que el camión cueste
113 244,4451 USD por día — ese número es lo que cuesta comprarlo nuevo. La tarifa diaria aproximada
sale de multiplicarlo por el `factor_depreciacion` del CSV crudo (`referencia_civil.csv`, columna
`factor_depreciacion = 0,004000` para ese camión): 113 244,4451 × 0,004 ≈ 453 USD/día. El formato
canónico de cuatro columnas no tiene dónde poner ese factor: quien componga un APU con un equipo de
esta lista debe traer `factor_depreciacion` del CSV crudo correspondiente, igual que lo exige
`LineaEquipo.depreciacion` (`core/contracts/apu.py`) y la regla **R6** (`CriterioDepreciacion`),
que pide que el factor viva declarado en la composición, no en la lista de precios.

## Depreciación MaPreX de los equipos de la línea base

Criterio externo y fechado para la regla **R6** (`CriterioDepreciacion`): el factor Cop/Depr. de
`equipos.pdf` para el equivalente MaPreX de cada equipo de la línea base, contrastado con el factor
que usó el presupuesto manual (columna «Línea base»). Fuente: `referencia_civil.csv`.

| Equipo (línea base) | Factor línea base | Ref MaPreX | Factor MaPreX | Coincide |
|---|---|---|---|---|
| Retroexcavadora | 1,00 | MOV027 | 0,003500 | No |
| Pico | 0,03 | ALB072 | 0,033000 | Aprox. |
| Pala | 0,03 | EZ0576 | 0,016700 | No |
| Camión de volteo | 1,00 | VEH010 | 0,004000 | No |
| Vehículo de transporte | 1,00 / 0,03 (hallazgo 7) | EZ0512 | 1,000000 | Coincide con el 1,00 |
| Segueta | 0,03 | CAR010 | 0,022000 | Aprox. |
| Cinta métrica | 0,03 | MED001 | 0,010000 | No |
| Sierra circular eléctrica | 0,03 | ALB045 | 0,020000 | Aprox. |
| Martillo | 0,03 | DEM005 | 0,022000 | Aprox. |
| Nivel de mano | 0,03 | ALB024 | 0,011000 | No |
| Alicate | 0,03 | ELE046 | 0,003000 | No |
| Mezcladora de concreto | 1,00 | CON007 | 0,007000 | No |
| Vibrador de concreto | 1,00 | CON041 | 0,009500 | No |
| Carretilla | 0,03 | ALB073 | 0,020000 | Aprox. |
| Tobos plásticos | 0,03 | ALB146 | 0,070000 | No |
| Compactadora de percusión tipo sapo | 1,00 | CPT018 | 1,000000 | Coincide |
| Herramientas menores | 1,00 | ALB213 | 1,000000 | Coincide |

Lectura para la tesis: el presupuesto manual usa solo dos valores (1,00 o 0,03) sin que quede
declarado un criterio de por qué un equipo deprecia distinto a otro (el propio hallazgo 7 lo
expone: el vehículo de transporte lleva 1,00 en cuatro APU y 0,03 en el de tubería). MaPreX, en
cambio, trae un factor propio por referencia de equipo, calculado por el proveedor de la base de
datos con un criterio de mercado — no siempre cercano al valor del presupuesto manual, pero sí
externo, fechado y reproducible. Ese contraste (no la sustitución silenciosa de un valor por otro)
es lo que la regla R6 y el indicador correspondiente de la tesis necesitan declarar.

## Jornal + bono del tabulador construcción

Evidencia para la decisión de fuente del FCAS del [dossier G0](../../../docs/dossier_g0.md). El
tabulador de la construcción (agrupación `a-SAL CONST-25032026+BONO X240$/ME`, `mano_de_obra.pdf`)
trae un jornal y un bono de alimentación distintos por nivel (N1…N9); como referencia del rol más
usado en la línea base («Ayudante», presente en las cinco partidas), el par exacto es:

| Ref MaPreX | Rol | Jornal (Bs) | Jornal (USD) | Bono (Bs) | Bono (USD) |
|---|---|---|---|---|---|
| `1-1.2` | AYUDANTE - TABULADOR CONSTRUCCION -N2 | 1.128,42 | 1,7816 | 3.939,53 | 6,2192 |

El nombre de la agrupación («BONO X240$/ME») es la etiqueta interna de MaPreX para la política de
bono vigente (equivalente declarado a 240 USD/mes); el monto en bolívares del bono varía por nivel
del escalafón (N1…N9), por lo que no se fuerza aquí una reconciliación exacta día-a-día con esa
cifra mensual — se deja el valor diario tal como lo imprime el PDF, con su Ref, para que el dossier
G0 decida cómo lo usa.
