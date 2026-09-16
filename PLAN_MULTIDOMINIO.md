# PLAN_MULTIDOMINIO.md — Catálogos y precios publicados para las demás ingenierías

Continuación del [PLAN_DESARROLLO.md](PLAN_DESARROLLO.md) (completo, 20 de 20 sesiones). Aquel
plan demostró la **mecánica** multidominio: cuatro adaptadores extraen cantidades trazables y el
núcleo quedó intacto (indicador 4). Este plan cubre lo que quedó declarado en la compuerta G2:
los dominios telecom, industrial y sistemas tienen **cero registros de APU y cero listas de
precios publicados**. El objetivo es que cada ingeniería entre por la misma puerta que civil — con
catálogo, composiciones, presupuesto auditado y lista de precios publicada y fechada — usando su
fuente natural de precios, que es distinta en cada dominio.

**Qué demuestra.** La generalización de la tesis en su segunda mitad: el PLAN original probó que
*el núcleo no cambia al agregar un dominio*; este prueba que *el protocolo de datos no cambia al
cambiar la fuente*. Alimenta el capítulo V y la decisión D3 del [dossier G0](docs/dossier_g0.md)
(OE7). Ninguna sesión de este plan toca `core/`: si un contrato parece insuficiente, se detiene y
se escribe el hallazgo en `docs/bitacora/` (CLAUDE.md §9); el análisis de la política de mano de
obra de ARENAZA ya mostró que no hace falta
([bitácora I5‑telecom](docs/bitacora/2026-08-29-I5-telecom.md), hallazgo 1, opción 1).

> **Errata (2026‑09‑15).** Este plan se escribió llamando «reales» a los presupuestos de ARENAZA y
> a los datos de los cuatro dominios. Son **ejercicios académicos ficticios**; lo publicado y
> fechado son las listas de precios de referencia (MaPreX jul‑2026 y el tabulador del CIV). El
> texto quedó corregido en la sesión de limpieza; los mensajes de commit citados más abajo se
> conservan tal como se hicieron, porque son historia. La fuente única de la naturaleza de los
> datos es [CLAUDE.md §1](CLAUDE.md#1-qué-es-este-proyecto).

---

## 0. Situación de partida (2026‑08‑31, actualizada 2026‑09‑02)

| Dominio | Adaptador | Catálogo/APU | Precios publicados | Fuente natural |
|---|---|---|---|---|
| civil | ✔ IFC + tabular | ✔ 5 APU auditados | línea base 28/04/2026; ✔ referencia MaPreX jul‑2026 en el repo; falta ronda vigente | MaPreX/Lulowin, cotizaciones, convención colectiva |
| telecom | ✔ topología CSV | 0 | **✔ ya en el repo**: 2 presupuestos ARENAZA (14 + 26 renglones, 1 109,29 y 5 410,73 USD) + referencia MaPreX jul‑2026 para contraste | distribuidores de redes; los PDF ARENAZA; MaPreX |
| industrial | ✔ activos CSV | 0 | ✔ referencia MaPreX jul‑2026 (repuestos, equipos de taller, técnicos por tabulador); faltan cotizaciones de los activos concretos | cotizaciones de repuestos/servicios, contratos de mantenimiento; MaPreX como proxy fechado |
| sistemas | ✔ alcance CSV | 0 | ✔ tabulador CIV al 01/07/2026 dentro del listado MO de MaPreX (43 filas, P‑1…P‑10); faltan tarifas TI de mercado | tarifario CIV (ya en el repo vía MaPreX), encuestas salariales TI, benchmark ISBSG (HH/PF) |

**Actualización 2026‑09‑02.** El autor incorporó los tres listados oficiales MaPreX de julio 2026
(materiales ≈ 12 500 renglones, equipos ≈ 2 850 con factor de depreciación por equipo, mano de
obra ≈ 790 con tabuladores construcción/CIV/sectoriales). Evidencia y reglas de uso en
[data/precios/maprex_2026-07/README.md](data/precios/maprex_2026-07/README.md). Qué resuelve:
referencia nacional fechada para civil, contraste de mercado para ARENAZA, proxy declarable para
GM2 y el tarifario CIV que GM3 esperaba. Qué no resuelve: es un listado de un mes pasado (los
precios están en Bs con tasa declarada 633,3644 Bs/USD al 01/07/2026), no una ronda vigente; y no
trae tarifas TI de mercado ni productividad HH/PF. La estructuración a CSV canónico es la nueva
Sesión M0.2.

Telecom va primero: su evidencia primaria ya está en `data/samples/telecom/` y trae su propia
inconsistencia documentada (el tubo corrugado: 80 m en cómputos vs 90 m en presupuesto del mismo
PDF), que convierte al dominio en el **segundo caso de auditoría** de la tesis.

## 1. Principios (además de los de CLAUDE.md)

1. **La fuente cambia; el formato no.** Toda fuente termina en el CSV canónico de UC‑02
   (`tipo,insumo,unidad,precio`) con `fecha_vigencia` y `origen`. Un conector por fuente,
   siempre fuera de `core/`.
2. **Evidencia primaria versionada.** Cada precio citable tiene su respaldo (PDF, cotización,
   captura fechada, tarifario) en `data/<dominio>/fuentes/`; la evidencia transversal a varios
   dominios (como los listados MaPreX) vive en `data/precios/<fuente>_<periodo>/`. La bitácora de
   la sesión lo lista.
3. **Supuestos declarados, nunca silenciosos.** Lo que no venga de la fuente (reparto de metros
   por tramo, horizonte de mantenimiento, HH por punto de función) se declara en el README de la
   muestra, como ya hacen las muestras civil y telecom.
4. **Una copia por dominio.** El desglose verificado de cada dominio vive una sola vez en
   `tests/fixtures/` (como `apu_linea_base.py` para civil); seed y pruebas lo importan de ahí.
5. **El simulador jamás se presenta como dato de mercado.** Ya declarado; se repite porque este
   plan es exactamente donde alguien querría atajarse.

## 2. Compuertas y criterios de degradación

| Compuerta | Criterio de cruce | Degradación declarada si falla | Estado |
|---|---|---|---|
| **GM1** (telecom, tras M1.3) | El presupuesto ARENAZA se reproduce del catálogo ± 0,01 y la auditoría detecta la inconsistencia 80/90 m | sin degradación posible: los datos ya están en el repo | CRUZADA |
| **GM2** (industrial, tras M2.2) | Presupuesto de mantenimiento con ≥ 3 activos costeados con precios cotizados | si no llegan cotizaciones: precios de contrato/factura histórica aportados por el autor, con origen declarado; siguiente instancia: referencia nacional MaPreX jul‑2026 (`data/precios/maprex_2026-07/`) declarada como proxy fechado; última instancia, solo para insumos ausentes en MaPreX: referencia internacional (RSMeans/Richardson) | CRUZADA‑CON‑DEGRADACIÓN |
| **GM3** (sistemas, tras M3.2) | Presupuesto del alcance funcional costeado con tarifas publicadas (CIV o encuesta fechada) y productividad HH/PF con fuente | el tabulador CIV jul‑2026 ya está en el repo (listado MO de MaPreX, estructurado en M0.2); si un rol no aparece ahí: encuesta salarial fechada; la productividad HH/PF siempre se toma de benchmark declarado (ISBSG o literatura), nunca inventada | CRUZADA |
| **GM4** (cierre, tras M4.1) | Recuento G2 regenerado por dominio y `resultados_ml.md` reflejando los dominios poblados | — (informativa) | CRUZADA |

Los cuatro dominios seguirán < 50 registros: la técnica de `ml/prediction/` **sigue siendo
reglas** y la limitación **sigue declarada**. Este plan no promete revertir G2; promete que la
limitación quede demostrada con catálogos poblados en vez de con ausencia de datos.

---

## Fase M0 — Protocolo transversal (2 sesiones + trabajo de campo del autor)

### Sesión M0.1 — Protocolo de levantamiento de precios multidominio

```
Genera docs/protocolo_precios.md: el procedimiento común (insumos del catálogo
por dominio, número mínimo de fuentes por insumo, evidencia que se guarda y
dónde, registro de fecha y tasa BCV, formato canónico de salida) y el catálogo
de fuentes por dominio con su forma de acceso y su cita.

Genera las plantillas data/<dominio>/plantilla_precios.csv con los insumos
exactos que cada catálogo necesita, listas para llenar en campo.

Incluye el borrador de carta de acceso académico continuo (MaPreX/Lulowin)
para la firma del tutor: los listados de julio 2026 ya están en el repo como
referencia (data/precios/maprex_2026-07/); la carta busca la serie mensual
para el histórico de UC-02.
```

**Commit.** `docs(datos): protocolo de levantamiento de precios multidominio`

**Trabajo de campo (dueño: el autor, en paralelo a M1):** enviar la carta; ronda de cotizaciones
civil (~9–14 insumos) e industrial (3–5 activos); encuesta TI fechada si se quiere superar el
tabulador CIV (que ya está en el repo vía MaPreX). El plan no se bloquea esperando: M1 no
necesita nada de esto.

### Sesión M0.2 — Referencia MaPreX estructurada

```
Deriva de data/precios/maprex_2026-07/ los CSV canónicos de referencia POR
DOMINIO, solo con los insumos que los catálogos necesitan (nunca el volcado de
los ~16 000 renglones): civil (los insumos de la línea base), telecom (los
renglones comparables con ARENAZA: fibra, UTP, racks, canalización), industrial
(repuestos/servicios aplicables a los activos de activos_planta.csv) y sistemas
(las 43 filas del tabulador CIV). PyMuPDF asiste; cada fila extraída se
verifica a mano contra el PDF y lleva origen (archivo + Ref MaPreX) y
fecha_vigencia (2026-07-09; mano de obra 2026-07-01). Precios convertidos a
USD con la tasa declarada 633,3644 Bs/USD (01/07/2026), registrada en cada CSV.

Registra en el README de la carpeta la tabla de factores de depreciación
MaPreX de los equipos de la línea base (criterio externo para R6) y el par
jornal + bono del tabulador de la construcción (evidencia para la decisión de
fuente del FCAS del dossier G0).

Criterio de cierre: CSV por dominio verificados fila a fila; ningún precio
entra al catálogo todavía (eso corresponde a M1-M3); git diff --stat core/
vacío.
```

**Commit.** `feat(datos): referencia maprex julio 2026 estructurada por dominio`

---

## Fase M1 — Telecom con ARENAZA (3 sesiones)

### Sesión M1.1 — Fuentes ARENAZA estructuradas

```
Vuelca los renglones de los dos PDF de ARENAZA (14 + 26, con descripcion,
unidad, cantidad y precio) a CSV canónicos fechados en data/telecom/fuentes/,
uno por presupuesto, con una columna de procedencia (PDF y renglón). PyMuPDF
asiste; cada fila se verifica a mano contra el PDF.

Crea tests/fixtures/presupuestos_arenaza.py: la única copia estructurada de los
dos presupuestos (totales 1109.29 y 5410.73), con la inconsistencia 80/90 m del
tubo corrugado REGISTRADA tal cual (no corregida), igual que la linea base
civil conserva sus siete.

Pruebas: los CSV suman exactamente los totales de cada PDF; la fila del tubo
corrugado del presupuesto 2 registra 80 en computos y 90 en presupuesto.
```

**Commit.** `feat(telecom): fuentes arenaza estructuradas con su inconsistencia registrada`

### Sesión M1.2 — Catálogo y costeo telecom

```
Construye las ComposicionAPU de las partidas TC-* desde el fixture: materiales
con los precios impresos en ARENAZA; la política de mano de obra "50 % del total"
se representa con la OPCION 1 del hallazgo 1 de la bitácora I5-telecom (una
LineaManoObra sintética armada por la capa de catálogo ANTES de llamar al
motor; el motor puro no cambia). Equipos según los renglones que correspondan.

Carga el catálogo telecom en SQLite (extensión de scripts/seed.py o script
hermano seed_telecom.py que importe el fixture) y reproduce el presupuesto
ARENAZA completo desde el catálogo.

Criterio de cierre: tests/integration/test_presupuesto_arenaza.py — el total
reproducido coincide con el PDF ± 0.01; git diff --stat core/ vacío.
```

**Commit.** `feat(telecom): catalogo y presupuesto arenaza reproducido desde sqlite`

### Sesión M1.3 — Auditoría telecom y UC‑02 con listas fechadas (compuerta GM1)

```
Audita el presupuesto ARENAZA con R1-R7: la inconsistencia 80/90 m debe salir
como hallazgo con sus origen_id (segunda evidencia empírica de la tesis, ahora
en otro dominio). Documenta qué reglas aplican y cuáles reportan INFO por no
tener datos en este dominio (R5 es volumétrica-civil: que reporte INFO es el
comportamiento correcto de RF-23, no un defecto a corregir).

Carga una lista de precios telecom fechada (los precios ARENAZA como
lista 1; la referencia MaPreX jul-2026 estructurada en M0.2 como lista 2 —
primer contraste de mercado del proyecto; si llegan cotizaciones de
distribuidores, lista 3) y corre UC-02: primer histórico de CambioPrecio
fuera de civil.

Criterio de cierre: 80/90 detectado; UC-02 telecom en verde; GM1 CRUZADA.
```

**Commit.** `feat(telecom): auditoria arenaza y actualizacion de precios reales`

---

## Fase M2 — Industrial (2 sesiones)

### Sesión M2.1 — Catálogo industrial con precios cotizados

```
Con las cotizaciones del protocolo M0.1 (≥ 3 activos del registro de
activos_planta.csv): compone las partidas MNT-* — el APU de una intervención de
mantenimiento: repuestos (materiales), servicio/herramienta (equipos), técnico
(mano de obra con tarifa cotizada). Evidencia en data/industrial/fuentes/.
Fixture único tests/fixtures/mantenimiento_industrial.py con supuestos
declarados (alcance de cada intervención).

Si las cotizaciones no llegaron: degradación GM2 declarada con la referencia
MaPreX jul-2026 (M0.2) como proxy fechado, no inventar.
```

**Commit.** `feat(industrial): catalogo de mantenimiento con precios cotizados`

### Sesión M2.2 — Presupuesto industrial de extremo a extremo (compuerta GM2)

```
AdaptadorIndustrial -> ItemComputo (intervenciones en el horizonte) ->
presupuesto costeado desde el catálogo -> auditoría (R1 verifica
frecuencia_anual * horizonte_anios) -> lista industrial fechada por UC-02.

Criterio de cierre: presupuesto de mantenimiento auditado con >= 3 activos y
precios con evidencia; GM2 CRUZADA (o degradación documentada).
```

**Commit.** `feat(industrial): presupuesto de mantenimiento auditado con datos reales`

---

## Fase M3 — Sistemas (2 sesiones)

### Sesión M3.1 — Tarifas y productividad con fuente

```
Estructura las tarifas publicadas: HH por rol desde el tabulador CIV jul-2026 ya
estructurado en M0.2 (43 filas P-1..P-10; incluye ingeniero computista y
analistas), complementado si existe con encuesta salarial TI fechada
(evidencia adicional en data/sistemas/fuentes/), y productividad HH por punto
de función tomada de benchmark declarado (ISBSG o literatura del marco
teórico, con cita). Compone las partidas SI-*: el APU de un punto de función
por módulo = horas de cada rol x tarifa. Fixture único
tests/fixtures/tarifas_sistemas.py; todo supuesto declarado (en particular la
correspondencia rol del APU -> fila del tabulador y la conversion jornal ->
HH).
```

**Commit.** `feat(sistemas): tarifas reales y apu por punto de funcion`

### Sesión M3.2 — Presupuesto de sistemas de extremo a extremo (compuerta GM3)

```
AdaptadorSistemas -> PFNA por caso de uso (regla IFPUG ya trazable) ->
presupuesto costeado -> auditoría (R1 reevalúa la regla de puntos de función;
R3 con la unidad "pf" documentada) -> lista de tarifas fechada por UC-02.

Criterio de cierre: presupuesto del alcance funcional auditado con tarifas con
fuente; GM3 CRUZADA (o degradación documentada).
```

**Commit.** `feat(sistemas): presupuesto por puntos de funcion con tarifas reales`

---

## Fase M4 — Consolidación (2 sesiones)

### Sesión M4.1 — Recuento G2 y resultados ML multidominio (compuerta GM4)

```
Regenera el conteo de registros por dominio y docs/resultados_ml.md con los
dominios poblados (scripts/generar_resultados_ml.py; extenderlo si hace falta
para iterar dominios). La técnica seguirá siendo reglas (< 50 por dominio):
el documento lo declara con los conteos NUEVOS, y donde el histórico de
variaciones lo permita (telecom tras M1.3), reporta métricas por dominio.

Actualiza docs/plan_pruebas.md (registro de ejecución) y
docs/calidad_iso25010.md si algún veredicto cambia.
```

**Commit.** `feat(ml): resultados multidominio con conteos g2 regenerados`

### Sesión M4.2 — Documentación de cierre

```
Actualiza: manuales (fuentes de precios por dominio y cómo cargar cada
catálogo), docs/tesis/plan_redaccion.md (capítulo IV §9 y capítulo V: la
generalización ahora se redacta con cuatro presupuestos auditados, no con uno),
esqueleto si D3 lo pide, y la bitácora final del plan con el estado de las
cuatro compuertas GM.
```

**Commit.** `docs: cierre del plan multidominio`

---

## Resumen del recorrido

| Fase | Sesiones | Producto | Depende de |
|---|---|---|---|
| M0 Protocolo | 2 | protocolo + plantillas + carta; referencia MaPreX estructurada por dominio | — (la evidencia MaPreX ya está en el repo) |
| M1 Telecom | 3 | catálogo, presupuesto y auditoría ARENAZA; contraste MaPreX; GM1 | nada externo (datos en el repo) |
| M2 Industrial | 2 | mantenimiento costeado; GM2 | cotizaciones del autor (M0); degradación MaPreX disponible |
| M3 Sistemas | 2 | puntos de función costeados; GM3 | tabulador CIV ya en el repo (M0.2); encuesta TI opcional |
| M4 Consolidación | 2 | G2 regenerada, docs al día; GM4 | M1–M3 |

Total: **11 sesiones**, más el trabajo de campo del autor (que corre en paralelo y ya no bloquea
ninguna compuerta: GM2 y GM3 tienen degradación o fuente en el repo; las cotizaciones y la
encuesta solo mejoran la evidencia). Las convenciones operativas son las de CLAUDE.md §3: una
rama por incremento (`inc/M1.1-fuentes-arenaza`), bitácora por sesión, `uv run pytest` y `ruff`
al cierre.

## Los tres momentos que definen este plan

**Sesión M1.2.** Cuando el presupuesto ARENAZA se reproduzca ± 0,01 desde SQLite, la tesis tiene
su **segunda línea base didáctica**, en otro dominio y con otra política de costeo, sin haber tocado
el motor.

**Sesión M1.3.** Cuando la auditoría marque los 80/90 m del tubo corrugado con sus `origen_id`,
el argumento «la verificación automática detecta lo que el proceso manual deja pasar» queda
demostrado **dos veces, en dos ingenierías distintas**.

**Sesión M4.1.** El recuento G2 regenerado es la honestidad del trabajo: la limitación de datos
se declara con los números nuevos en la mano, no con la ausencia de intento.
