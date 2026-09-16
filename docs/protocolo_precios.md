# Protocolo de levantamiento de precios multidominio

Sesión M0.1 de [PLAN_MULTIDOMINIO.md](../PLAN_MULTIDOMINIO.md). Define **cómo** se recoge, evidencia
y estructura un precio real para cualquiera de los cuatro dominios (civil, telecom, industrial,
sistemas) antes de que entre al catálogo mediante UC‑02. Los principios 1‑5 del PLAN_MULTIDOMINIO
("la fuente cambia; el formato no", "evidencia primaria versionada", "supuestos declarados, nunca
silenciosos", "una copia por dominio", "el simulador jamás se presenta como dato de mercado") rigen
todo lo que sigue; este documento solo los hace operativos.

Las sesiones M1.1‑M3.2 citan este protocolo en vez de repetirlo (principio DRY, CLAUDE.md §2).

---

## 1. Procedimiento común

### 1.1 Insumos a levantar

El punto de partida siempre es un catálogo **ya existente** en el repositorio: la línea base civil
(`tests/fixtures/apu_linea_base.py`), las muestras telecom/industrial/sistemas
(`data/samples/<dominio>/`) o la referencia MaPreX estructurada (Sesión M0.2). Nunca se inventa un
insumo nuevo para levantar precio; se levanta precio de lo que el catálogo ya declara que necesita.
La sección 2 lista, por dominio, de qué catálogo sale cada plantilla.

### 1.2 Número mínimo de fuentes

**Al menos dos fuentes independientes por insumo cuando sea posible** (por ejemplo: una cotización
de proveedor y el listado MaPreX; o dos distribuidores distintos). Si solo existe una fuente
disponible para un insumo, se registra igual, pero la columna `fuente` de la plantilla debe declarar
explícitamente por qué no hay una segunda (insumo de un solo proveedor conocido, evidencia de archivo
único, etc.); una plantilla llenada con una sola fuente y sin esa nota se considera incompleta.

### 1.3 Evidencia: qué se guarda y dónde

| Alcance de la evidencia | Carpeta |
|---|---|
| Específica de un dominio (cotización de un proveedor telecom, factura de un repuesto industrial, captura de una encuesta salarial TI) | `data/<dominio>/fuentes/` |
| Transversal a varios dominios (listados MaPreX/Lulowin, tarifario CIV, cualquier fuente que sirva de referencia a más de un dominio a la vez) | `data/precios/<fuente>_<periodo>/` (el patrón que ya usa `data/precios/maprex_2026-07/`) |

Cada archivo de evidencia se guarda tal cual llega (PDF, captura de pantalla fechada, cotización
escaneada); no se transcribe sin conservar el original. La columna `evidencia` de la plantilla
apunta a la ruta relativa de ese archivo dentro del repositorio (por ejemplo
`data/civil/fuentes/cotizacion_cemento_2026-09.pdf`); si la evidencia todavía no se ha archivado
formalmente, se deja una referencia provisional (nombre del archivo que el autor tiene en mano) y se
corrige al mover el archivo a su carpeta definitiva.

### 1.4 Registro de fecha y tasa BCV

Todo precio se registra con:

1. `fecha`: el día en que se obtuvo la cotización o se leyó el listado (no la fecha en que se llena
   la plantilla).
2. La **tasa BCV del día**, si la fuente cotiza en bolívares. El sistema opera en USD (CLAUDE.md §1,
   §4); toda conversión Bs→USD debe declarar la tasa usada y su fecha, siguiendo exactamente la
   regla que ya aplica `data/precios/maprex_2026-07/README.md` a la tasa **633,3644 Bs/USD al
   01/07/2026** ("toda conversión a USD que se derive de estos PDF debe registrar esa tasa y esa
   fecha; nunca convertir con una tasa de otro día sin declararlo"). La plantilla no tiene una
   columna separada para la tasa: cuando el precio se originó en Bs, la columna `fuente` debe leerse
   como `<proveedor o listado> — <monto> Bs @ <tasa> Bs/USD (BCV <fecha de la tasa>)`, y la columna
   `precio` de la plantilla, una vez llena, lleva siempre el monto ya convertido a USD.

### 1.5 Formato canónico de salida (UC‑02)

La plantilla de esta sesión (`tipo,insumo,unidad,precio,fecha,fuente,evidencia`) es un formato de
**campo**, con trazabilidad adicional para la ronda de levantamiento. El formato canónico que
consume el catálogo es el de UC‑02 (`core/catalog/precios.py`, `COLUMNAS_ARCHIVO`):

```
tipo,insumo,unidad,precio
```

con `tipo` ∈ `{material, equipo, mano_obra}` (alias aceptados: `mano de obra`, `mano_de_obra`) y
`insumo` = la descripción del insumo. Al cerrar una ronda de campo, la plantilla llena se reduce a
estas cuatro columnas (se descartan `fecha`, `fuente`, `evidencia` del archivo que se carga al
catálogo, pero esas tres columnas permanecen en el archivo de campo archivado como evidencia de la
ronda).

**Un insumo se identifica por `(tipo, insumo, unidad)`**, no por código (`core/catalog/precios.py`,
docstring del módulo): dos filas con la misma clave son la misma fila de precio y actualizan **todas**
las variantes homónimas del catálogo que compartan esa clave (el caso documentado de `Agua`, `Pala`,
`Cinta métrica`, `Nivel de mano` y `Vehículo de transporte` en la línea base civil, que aparecen con
el mismo `(tipo, insumo, unidad)` y distinto precio histórico en más de un APU). Por esto, cada
plantilla de esta sesión trae **una sola fila por combinación `(tipo, insumo, unidad)`**, aunque el
catálogo de origen use ese insumo en varias partidas con precios o cantidades distintas.

**Convención de `unidad` por tipo** (ya establecida por `data/samples/precios/lista_2026-06-01.csv`,
la única lista de precios de muestra del repositorio): en filas `material` la unidad es la unidad
física del insumo (`m`, `m2`, `m3`, `saco`, `unidad`, `pieza`…, normalizada por
`core.contracts.unidades.normalizar_unidad`); en filas `equipo` y `mano_obra` la unidad se deja
**vacía**, porque `LineaEquipo` y `LineaManoObra` (`core/contracts/apu.py`) no tienen campo `unidad`
propio — el precio de un equipo es su valor de adquisición o alquiler y el de la mano de obra es un
jornal diario, ambos sin unidad física que declarar. La única excepción explícita de este protocolo
es la plantilla de sistemas (sección 2.4): ahí `mano_obra` sí declara `unidad = h` porque el costeo
del dominio es por horas‑hombre, no por jornal, y dejarla vacía confundiría las dos convenciones.

### 1.6 Procedimiento paso a paso

1. Tomar la plantilla del dominio (sección 2) — ya trae `tipo`, `insumo` y `unidad` resueltos desde
   el catálogo existente.
2. Para cada fila, buscar mínimo dos fuentes (1.2) y registrar precio, fecha, fuente y evidencia por
   cada una que se consiga (si hay dos cotizaciones, se documentan ambas y se declara cuál se adopta
   y por qué — normalmente la más reciente o la de mercado local sobre la de referencia nacional).
3. Si el precio original está en bolívares, aplicar 1.4 (tasa BCV + conversión).
4. Archivar la evidencia en la carpeta que corresponda (1.3).
5. Al cerrar la ronda, generar el CSV canónico de UC‑02 (`tipo,insumo,unidad,precio`) a partir de la
   plantilla llena, para cargarlo al catálogo con `core.catalog.precios.crear_lista_desde_archivo`.

---

## 2. Catálogo de fuentes por dominio

### 2.1 Civil

| Fuente | Forma de acceso | Cita |
|---|---|---|
| MaPreX / Lulowin (listados oficiales) | Software de precios de la construcción; acceso mensual bajo licencia/suscripción académica (ver anexo, sección 3) | `data/precios/maprex_2026-07/` — MaPreX v26.0.0.1, BD `BDLaing08072026.mdb` (08/07/2026), impreso 13/07/2026; ya en el repo como referencia de julio 2026, pendiente ronda vigente |
| Cotizaciones de proveedores locales (ferreterías, distribuidoras de materiales y equipos de construcción) | Solicitud directa del autor (trabajo de campo, Fase M0 de PLAN_MULTIDOMINIO, ~9–14 insumos) | Cotización fechada, archivada en `data/civil/fuentes/` |
| Convención colectiva de la construcción (LOTTT y contratación colectiva vigente) | Publicación pública / gremio de la construcción | Pendiente cita normativa exacta (decisión D4 del [dossier G0](dossier_g0.md): el FCAS de 600 % proviene de los APU reales del caso, falta su respaldo normativo citable; el par jornal + bono del tabulador de la construcción dentro de `data/precios/maprex_2026-07/mano_de_obra.pdf` es evidencia fechada disponible mientras se resuelve la cita) |

El catálogo de insumos a re-cotizar es exactamente el de `tests/fixtures/apu_linea_base.py`:
`data/civil/plantilla_precios.csv` (sección 2.5).

### 2.2 Telecom

| Fuente | Forma de acceso | Cita |
|---|---|---|
| Distribuidores de redes y CCTV | Cotización directa (trabajo de campo, mejora opcional; no bloquea GM1) | Cotización fechada, archivada en `data/telecom/fuentes/` |
| Presupuestos ARENAZA (evidencia primaria propia del proyecto) | Ya en el repo | `data/samples/telecom/Presupuesto_1_ARENAZA.pdf` (14 renglones, 1 109,29 USD) y `Presupuesto_2_ARENAZA.pdf` (26 renglones, 5 410,73 USD), computos del 18/05/2026; ver `data/samples/telecom/README.md` |
| MaPreX (contraste, no reemplazo) | Ya en el repo | `data/precios/maprex_2026-07/materiales.pdf` (fibra óptica ≈ 58 menciones, UTP, patch panels, racks, telefonía, coaxial) y `equipos.pdf` (fusionadoras y equipos de red); julio 2026, no sustituye precios de distribuidor específico |

El catálogo de insumos a re-cotizar es la unión de los renglones de los dos presupuestos ARENAZA:
`data/telecom/plantilla_precios.csv` (sección 2.5). La política de mano de obra de ARENAZA ("el
equivalente al 50 % del presupuesto total", analizada en
[docs/bitacora/2026-08-29-I5-telecom.md](bitacora/2026-08-29-I5-telecom.md), hallazgo 1) no genera
un insumo de mano de obra propio en este dominio — no hay un jornal ni una tarifa horaria que
recotizar, es una regla de reparto del costo total que arma la capa de catálogo antes de llamar al
motor — por eso la plantilla telecom solo trae filas `material`.

### 2.3 Industrial

| Fuente | Forma de acceso | Cita |
|---|---|---|
| Cotizaciones de repuestos y servicios de mantenimiento | Solicitud directa del autor (trabajo de campo, Fase M0, ≥ 3 activos para GM2) | Cotización fechada, archivada en `data/industrial/fuentes/` |
| MaPreX como proxy fechado | Ya en el repo, degradación declarada de GM2 si no llegan cotizaciones | `data/precios/maprex_2026-07/materiales.pdf` (válvulas ≈ 172 menciones, rodamientos, compresores, correas), `equipos.pdf` (herramientas y equipos de taller) y `mano_de_obra.pdf` (mecánicos y electricistas por tabulador) |
| Contratos de mantenimiento / factura histórica | Aportados por el autor si las cotizaciones nuevas no llegan a tiempo | Documento fechado, archivado en `data/industrial/fuentes/`, con origen declarado |

El catálogo de insumos es una **lista tentativa** de repuestos, servicios/herramientas y técnicos
plausibles por cada uno de los diez activos de `data/samples/industrial/activos_planta.csv` — no
proviene de una orden de trabajo real, a diferencia de los insumos civil (línea base auditada) o
telecom (presupuestos didácticos ARENAZA). Se marca así explícitamente porque el brief de esta sesión no
tiene todavía cotizaciones de campo que confirmen qué repuesto exacto corresponde a cada activo; la
ronda de cotizaciones de la Fase M0 la reemplazará o la confirmará insumo por insumo:
`data/industrial/plantilla_precios.csv` (sección 2.5).

### 2.4 Sistemas

| Fuente | Forma de acceso | Cita |
|---|---|---|
| Tabulador CIV vía MaPreX | Ya en el repo | `data/precios/maprex_2026-07/mano_de_obra.pdf`, agrupación "tabulador CIV al 01/07/2026" (43 filas, escalafón P‑1…P‑10, incluye ingeniero computista y gerente de proyectos); estructuración a CSV por dominio es la Sesión M0.2 |
| Encuesta salarial TI fechada | Trabajo de campo del autor (mejora opcional; no bloquea GM3) | Encuesta o portal de salarios TI, fechado, archivado en `data/sistemas/fuentes/` |
| ISBSG (International Software Benchmarking Standards Group) u otro benchmark declarado del marco teórico | Literatura / benchmark público, nunca inventado | Cita bibliográfica exacta a incorporar en el capítulo del marco teórico cuando se use la productividad HH/PF |

El tabulador CIV cubre roles de ingeniería reconocidos (ingeniero computista, gerente de proyectos);
no cubre roles de desarrollo de software de mercado (programador backend/frontend, QA, arquitecto de
software), que quedan pendientes de la encuesta TI. La plantilla de sistemas lista ambos grupos de
roles como insumos `mano_obra` a tarifar: `data/sistemas/plantilla_precios.csv` (sección 2.5). La
productividad horas‑hombre por punto de función **nunca** se declara sin fuente (principio 5 del
PLAN_MULTIDOMINIO: "el simulador jamás se presenta como dato de mercado"); sale siempre de ISBSG o
de la literatura citada del marco teórico, nunca de una estimación del autor.

### 2.5 Resumen de las cuatro plantillas

| Archivo | Filas | Tipo(s) | Catálogo de origen |
|---|---|---|---|
| `data/civil/plantilla_precios.csv` | 37 (13 material + 17 equipo + 7 mano_obra) | los tres | `tests/fixtures/apu_linea_base.py`, insumos únicos por `(tipo, insumo, unidad)` |
| `data/telecom/plantilla_precios.csv` | 28 | material | Unión de renglones de `Presupuesto_1_ARENAZA.pdf` y `Presupuesto_2_ARENAZA.pdf`, deduplicados |
| `data/industrial/plantilla_precios.csv` | 18 (9 material + 3 equipo + 6 mano_obra) | los tres | Lista tentativa de repuestos/servicios/técnicos por activo de `activos_planta.csv` |
| `data/sistemas/plantilla_precios.csv` | 7 | mano_obra | Roles del tabulador CIV + roles de mercado TI necesarios para las partidas SI-* |

---

## 3. Anexo: borrador de carta de acceso académico continuo a MaPreX/Lulowin

Los tres listados de julio 2026 (`data/precios/maprex_2026-07/`) ya están en el repositorio como
referencia puntual de un mes pasado. Esta carta no pide ese listado — ya se tiene —, pide la **serie
mensual** (histórico continuo), que es lo que UC‑02 necesita para construir `CambioPrecio` a lo
largo del tiempo en vez de una sola foto de julio. Para firma del tutor.

```
[Membrete de la universidad / tutor]

[Ciudad], [fecha]

Señores
MaPreX / Lulowin
Presente.-

Asunto: Solicitud de acceso académico continuo a los listados de precios de la construcción

Reciban un cordial saludo. Mi nombre es [nombre del tutor], profesor(a) de la [universidad/
facultad], y actúo como tutor(a) del trabajo especial de grado "[título de la tesis]", desarrollado
por [nombre del autor], cuyo objeto de estudio es un sistema de generación y auditoría de Análisis de
Precios Unitarios (APU) multidominio (obra civil, telecomunicaciones, mantenimiento industrial y
desarrollo de sistemas).

El trabajo ya incorporó, como referencia puntual, los listados de materiales, equipos y mano de obra
de MaPreX correspondientes a julio de 2026, aportados por el autor. Para que el sistema pueda
construir y validar un histórico de variación de precios (y no solo un contraste de un único
mes), solicitamos formalmente acceso académico continuo a la **serie mensual** de estos listados —o,
alternativamente, autorización para recibir y conservar como evidencia académica los listados
mensuales sucesivos— durante el período de desarrollo y evaluación del trabajo de grado, con los
siguientes compromisos de nuestra parte:

1. El uso de la información será exclusivamente académico, como evidencia y contraste de precios
   dentro del trabajo de grado y su eventual publicación en el repositorio institucional.
2. No se hará uso comercial de los listados ni se redistribuirán fuera del contexto académico.
3. Toda cita de un precio de MaPreX en el documento de tesis referenciará el archivo, la referencia
   interna ("Ref MaPreX") y la fecha de vigencia exactas, tal como ya se hace con el listado de julio
   2026.

Quedamos atentos a cualquier condición adicional que MaPreX/Lulowin considere pertinente para
autorizar este acceso, y agradecemos de antemano la atención prestada.

Atentamente,

_____________________________
[Nombre del tutor]
[Cargo / universidad]
[Datos de contacto]
```

---

## Próximos pasos

1. **Sesión M0.2** — estructurar `data/precios/maprex_2026-07/` en los cuatro CSV canónicos por
   dominio que este protocolo y las plantillas de campo usarán como segunda fuente de contraste.
2. **Trabajo de campo del autor** (en paralelo, sin bloquear M1): enviar la carta de la sección 3;
   ronda de cotizaciones civil (~9–14 insumos) e industrial (3–5 activos); encuesta TI fechada si se
   quiere superar el tabulador CIV.
3. Las plantillas llenas de esta sesión se reducen al formato UC‑02 (sección 1.5) al cerrar cada
   ronda, y entran al catálogo con `core.catalog.precios.crear_lista_desde_archivo`.
