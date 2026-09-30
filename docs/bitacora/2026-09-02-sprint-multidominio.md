# Bitácora final — Sprint multidominio (M0.1–M4.2)

**Fechas:** 2026‑09‑02 (meta y M0.1–M3.2) y 2026‑09‑14 (M4.1–M4.2) · **Rama:**
`worktree-sprint-multidominio` (worktree `.claude/worktrees/sprint-multidominio`) · **Base:**
etiqueta `m-base` = `62986ec` · **Plan ejecutable:**
`2026-09-02-sprint-multidominio.md` · **Spec:** `PLAN_MULTIDOMINIO.md`

## Objetivo y resultado

Que telecom, industrial y sistemas entren por la misma puerta que civil: catálogo, presupuesto
auditado y lista de precios real y fechada, **sin tocar `core/`**.

**Cumplido en los cuatro dominios.** `git diff m-base --stat -- core/` quedó vacío al cierre de
cada sesión y al cierre del sprint; ninguna sesión encontró una insuficiencia de contratos que
obligara a detenerse (NORMAS.md §9). Meta del sprint: **12/12**.

## Compuertas

| Compuerta | Estado | Evidencia | Qué falta para cruzarla sin salvedad |
|---|---|---|---|
| **GM1** telecom | CRUZADA | Los dos presupuestos ARENAZA se reproducen del catálogo con diferencia 0,00 (1 109,29 y 5 410,73 USD); R1 detecta la inconsistencia 80/90 m del tubo corrugado con su `origen_id` (M1.2, M1.3) | — |
| **GM2** industrial | CRUZADA‑CON‑DEGRADACIÓN | Presupuesto `MNT-001`, cuatro activos, 18 124,09 USD, precios de la referencia MaPreX jul‑2026 como proxy declarado antes del código (M2.1, M2.2) | La ronda de cotizaciones del autor (≥ 3 activos) |
| **GM3** sistemas | CRUZADA | Presupuesto `SIS-001`, nueve casos de uso, 145 PF, 16 093,89 USD, tarifas del tabulador CIV al 01/07/2026 (M3.1, M3.2) | La cita de la productividad HH/PF, hoy supuesto declarado |
| **GM4** G2 | CRUZADA (informativa) | Conteos 5 / 40 / 4 / 9, técnica reglas; telecom evaluado sobre su histórico real (M4.1) | — (el plan no promete revertir G2) |

## Números del sprint

| Indicador | Antes del sprint | Cierre |
|---|---|---|
| Pruebas con `-W error` | 395 (registro de `plan_pruebas.md`, 2026‑08‑31) | **481** (122,02 s) |
| Registros G2 civil / telecom / industrial / sistemas | 5 / 0 / 0 / 0 | 5 / 40 / 4 / 9 |
| Presupuestos auditados con precios reales y fechados | 1 (civil, caso de ejemplo) | 5 (civil, ARENAZA 1 y 2, `MNT-001`, `SIS-001`) |
| Líneas de `core/` cambiadas | — | **0** (cobertura 98,10 %) |
| Meta del sprint | — (se creó en la Task 1) | **12/12** |

## Sesiones

| Sesión | Commits | Bitácora |
|---|---|---|
| Task 1, meta del sprint | `5e61a85` | — |
| M0.1 protocolo de precios | `b909f4c` | `2026-09-02-M0.1-protocolo.md` |
| M0.2 referencia MaPreX estructurada | `e5aa9e6`, `38c8f53` | `2026-09-02-M0.2-referencia-maprex.md` |
| M1.1 fuentes ARENAZA | `e92f880`, `a8f4be8` | `2026-09-02-M1.1-fuentes-arenaza.md` |
| M1.2 catálogo telecom | `49db4c6`, `e4c7764` | `2026-09-02-M1.2-catalogo-telecom.md` |
| M1.3 auditoría telecom (GM1) | `147a336` | `2026-09-02-M1.3-auditoria-telecom.md` |
| M2.1 catálogo industrial | `8ed7f3e` | `2026-09-02-M2.1-catalogo-industrial.md` |
| M2.2 presupuesto industrial (GM2) | `85e0eef` | `2026-09-02-M2.2-presupuesto-industrial.md` |
| M3.1 tarifas sistemas | `85e08b0` | `2026-09-02-M3.1-tarifas-sistemas.md` |
| M3.2 presupuesto sistemas (GM3) | `6c3163c` | `2026-09-02-M3.2-presupuesto-sistemas.md` |
| M4.1 recuento G2 (GM4) | `acde98e` | `2026-09-02-M4.1-recuento-g2.md` |
| M4.2 cierre | `4af914e` (fix de la meta) y el commit de esta bitácora | este archivo |

## Hallazgos para la tesis

1. **La hipótesis central resiste con datos reales.** Cuatro dominios con catálogo, presupuesto,
   auditoría y UC‑02, y cero líneas cambiadas en `core/`. Los contratos sirvieron sin cambios
   incluso donde la «partida» no es una unidad de obra: un evento periódico de mantenimiento
   (M2.2) y un APU de solo mano de obra con cantidades fraccionarias (M3.2).
2. **La fuente primaria ARENAZA es internamente inconsistente** (80 m en cómputos, 90 m en
   presupuesto) y el sistema lo detecta: segundo caso de auditoría, esta vez sobre un documento
   real (M1.3).
3. **La degradación G2, demostrada con datos reales.** Sobre el histórico telecom la regla sin
   composición da MAPE 27,83 % y 38 advertencias AACE que describen al estimador, no a la
   construcción; UC‑02 reproduce los PU exactos porque recorre la composición (M4.1).
4. **R4 compara por subcadena:** «auditor» coincide dentro de «auditoria» y marca como
   contrastable algo que no lo es. Inocuo en el caso, pero la revisión corresponde a una sesión
   de núcleo (M3.2).
5. **La convención de presentación (`ROUND_HALF_UP`) vive fuera de `core.contracts`**, así que
   `ml/` tuvo que replicarla (M4.1).
6. **Una meta de sprint también es código.** La meta M8 contaba 3 partidas industriales donde hay
   4 (el patrón `MNT-\w+` cortaba en el segundo guion) y habría pasado con una partida menos;
   `scripts/meta_multidominio.py` no tenía pruebas hasta este cierre (M4.2, `4af914e`).
7. **Duplicación consciente:** los tres seeds de dominio repiten la misma estructura. Se extrae
   una utilidad común solo si aparece un quinto dominio (M3.2).

## Correcciones documentales de M4.2

- `docs/manual_tecnico.md`: §7 afirmaba que `ml/` no importa de `core` «ni siquiera contratos»,
  y `ml/prediction/reglas.py` importa `core.contracts.verificacion` desde I6.3; corregido. §8
  ahora lista los scripts del sprint, y la nueva §8.1 da por dominio la fuente de precios, la
  copia única y el seed.
- `docs/manual_usuario.md` §2: cómo sembrar los tres catálogos nuevos y cómo apuntar la UI
  (campo «Archivo SQLite») y la API (`APU_BASE`) a cada base.
- `PLAN_MULTIDOMINIO.md` §2: columna Estado con las cuatro compuertas.

## Pendientes del autor

- **Cotizaciones industriales** en `data/industrial/plantilla_precios.csv` (≥ 3 activos): cruza
  GM2 sin degradación y abre el histórico industrial. Confirmar también el alcance supuesto de
  cada intervención (M2.1).
- **Cita ISBSG** (o literatura del marco teórico) para la productividad HH/PF y el reparto de
  horas por rol; encuesta salarial TI fechada, opcional (M3.1).
- **Verificación manual de filas MaPreX marcadas** como equivalencia imperfecta: civil `ENC010`,
  `ENC048`, `PLO560`, `ALB213` (tres homónimas, se eligió la de menor precio); telecom, switches
  referenciados por categoría (M0.2).
- **Telecom:** decidir si se admiten las conversiones de empaque (RJ45 ×100, UTP ×300/305),
  confirmar las tres equivalencias sin salvedad (anillo, tomacorriente, cajetín) y aportar la
  lista 3 de distribuidores si llega (M1.3).
- **FCAS y bono** (dossier G0), incluido su tratamiento sobre honorarios profesionales en
  sistemas (M2.1, M3.1).
- **Carta de acceso a la serie mensual MaPreX** (protocolo M0.1): daría histórico real a
  industrial y sistemas, hoy no evaluables en `resultados_ml.md`.

## Pendientes en archivos vedados por el sprint

- «actualizar plan_redaccion (cap. IV §9 y cap. V) cuando el usuario commitee su sesión de
  redacción», y con ello añadir a sus cifras citables (§5) los conteos y métricas de M4.1.

## Pendientes técnicos

- `docs/plan_pruebas.md` §8 (trazabilidad RF → prueba) todavía no lista las pruebas de
  integración del sprint (`test_presupuesto_arenaza`, `test_auditoria_arenaza`,
  `test_presupuesto_industrial`, `test_presupuesto_sistemas`).
- `docs/calidad_iso25010.md` conserva la evidencia del corte F.2 (395/395, 98,05 %); ningún
  veredicto cambió, y el registro vigente está en `plan_pruebas.md` §10.
- R4 por token en vez de por subcadena: sesión de núcleo, fuera de este sprint.

## Estado final

- `uv run pytest -W error`: **481 passed in 122,02 s**.
- `uv run ruff check .`: limpio.
- `git diff m-base --stat -- core/`: **vacío**.
- `uv run python scripts/meta_multidominio.py`:

```
M1  protocolo con las cuatro secciones de dominio                    OK
M2  cuatro plantillas data/<dominio>/plantilla_precios.csv           OK
M3  referencia MaPreX por dominio con ref_maprex y archivo           OK
M4  presupuestos ARENAZA suman 1109.29 y 5410.73                     OK
M5  fixture ARENAZA registra la discrepancia 80/90                   OK
M6  presupuesto ARENAZA reproducido del catalogo: 27 pasadas         OK
M7  auditoria telecom detecta 80/90: 8 pasadas                       OK
M8  4 partidas MNT-* (BOM-CEN, BOM-SUM, COM-REC, MOT-TRI): 6 pasadas OK
M9  fixture de tarifas y presupuesto sistemas: 6 pasadas             OK
M10 resultados_ml.md con conteos por dominio                         OK
M11 git diff m-base --stat -- core/ vacio                            OK
M12 ruff check . limpio                                              OK
RESULTADO: 12/12 metas OK
```

## Integración

**Sin fusionar a `main`**: la fusión (`--no-ff`, sin push, como el resto del proyecto) la decide
el usuario. El sprint no editó ninguno de los archivos con cambios sin commitear en el checkout
principal (`NORMAS.md`, `README.md`, `docs/README.md`, `docs/linea_base.md`, `docs/tesis/**`),
así que la fusión no los toca.
