# Bitácora final — Sprint del prototipo AREN.IA (fases P0–P5)

**Fechas:** 2026‑09‑16 (P0–P1), 2026‑09‑20 (P2–P3) y 2026‑09‑21 (P4–P5) · **Rama:**
`inc/PLAN-prototipo` (worktree `.claude/worktrees/prototipo`) · **Base:** etiqueta `p-base` =
`471b3e2` · **Plan de sesiones:** [`PLAN_PROTOTIPO.md`](../../PLAN_PROTOTIPO.md) · **Spec
vinculante:** [`docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md`](../superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md) ·
**Planes ejecutables:** los cinco `prototipo-arenia-*.md` de
[`docs/superpowers/plans/`](../superpowers/plans/) (uno del 16/09, tres del 20/09 y uno del 21/09) ·
**PR:** #7, abierto contra `main`, sin fusionar.

Los cuadernos de control de los agentes (`.superpowers/sdd/2026-09-16-prototipo-arenia-fase-p0-p1`,
`2026-09-20-prototipo-arenia-fase-p2-deudas-y-composicion`,
`2026-09-20-prototipo-arenia-pantalla-y-fases-restantes`,
`2026-09-20-prototipo-arenia-fase-p3-flujo-completo` y `2026-09-21-prototipo-arenia-fases-p4-p5`)
están en `.git/info/exclude` y **no viajan con la fusión**. Lo que importa de ellos queda aquí.

## Objetivo y resultado

Dar al sistema la pantalla que le faltaba: **componer y editar una partida a mano** (UC‑10 y UC‑11,
RF‑33 a RF‑35 de la [ERS](../ERS.md)), con la referencia MaPreX como sugerencia editable, el
rendimiento exigido con sus condiciones, la mano de obra a jornal o a destajo por línea, las
ayudas de `ml/` cableadas a la pantalla, y el recorrido completo hasta el presupuesto auditado y su
Excel. Todo lo que el sprint siembra o simula es un **caso didáctico o simulado**, no obra ejecutada
([CLAUDE.md §1](../../CLAUDE.md)).

**Cumplido.** Las tres compuertas cruzadas, meta del sprint **12/12**, suite con **690** pruebas y
0 omitidas (673 al cerrar P5; 690 tras la auditoría de la rama completa, sección «Auditoría de rama
completa» más abajo). El núcleo cambió en **siete** archivos, con expediente previo (D9) y sin
romper la línea base; ninguno de los cambios lo pidió un dominio nuevo, así que la hipótesis central
queda intacta (sección «El cambio al núcleo»).

## Compuertas

| Compuerta | Estado | Evidencia |
|---|---|---|
| **GP0** — ERS y diseño; D9 planteada al tutor | CRUZADA | Decisión **D9** en el [dossier G0](../dossier_g0.md) (commit `9b9de5e`), con el artículo 114 de la LOTTT y la cláusula 1 de la convención colectiva de la construcción archivados en `docs/fuentes/`; **D4** actualizada en el mismo commit con la ausencia de fuente normativa del FCAS. Fundamento en la [bitácora del hallazgo](2026-09-16-P0-hallazgo-destajo.md). `meta_prototipo.py --hasta P0` en 3/3 |
| **GP1** — la línea base da 1 586,61 USD y 7 de 7 | CRUZADA | Commit `1558587`, `tests/integration/test_composicion_extremo_a_extremo.py`: las cinco partidas de la línea base, tecleadas como texto en las tablas y armadas con `ui.composicion.composicion_desde_tablas`, dan un `Presupuesto` y un `InformeAuditoria` **iguales por dataclass** a los del camino del catálogo; total **1 586,61 USD**, hallazgos **7 de 7**. El commit tocó solo ese archivo de pruebas: cero código de producción, como debía pasar si las dos rutas coinciden. La ruta ejercitada es la capa pura de la pantalla, no la pantalla por `AppTest` |
| **GP2** — pruebas de interfaz verdes en Linux y Windows | CRUZADA, sin degradación | Corrida de la CI <https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/35652890698> sobre `6f824b6` (cierre de P4): `calidad` (ruff y guardia del núcleo), `pruebas (ubuntu-latest)` y `pruebas (windows-latest)` en *success*. Las pruebas `AppTest` corren dentro de la CI existente con `-W error`, **sin `filterwarnings` ni marcador**: el criterio de degradación de `PLAN_PROTOTIPO.md` no hizo falta |

## El cambio al núcleo y su expediente

`git diff p-base --stat -- core/` al cierre: **7 archivos, +217 / −18**. La hipótesis central
(CLAUDE.md §1) dice que `core/` no cambia **al agregar un dominio**; ninguno de estos cambios lo
pidió un dominio, ningún adaptador se tocó, `tests/unit/test_costing.py` y
`tests/fixtures/apu_linea_base.py` tienen diff vacío contra `p-base`, y
`scripts/guardia_nucleo.py --base p-base` sale con código 0 (ningún commit toca `core/` junto con
`adapters/` o `ml/`).

| Archivo | Commits | Qué cambió | Por qué no rompe la hipótesis |
|---|---|---|---|
| `core/contracts/apu.py` | `e10440c`, `4ea15a1` | `ModalidadManoObra` (`JORNAL`/`DESTAJO`); `LineaManoObra.modalidad` con `JORNAL` por defecto y coerción del texto (valor desconocido → `ValueError`); `total_obreros` cuenta solo el jornal | Contrato declarado estable: se tocó **con expediente** (D9, GP0) y no por un dominio. Aditivo: el constructor de tres argumentos sigue valiendo |
| `core/contracts/__init__.py` | `4ea15a1` | Reexporta `ModalidadManoObra` | Una línea de fachada, para que nadie importe el tipo de dos sitios |
| `core/costing/motor.py` | `e10440c` | Separa la mano de obra: jornal con la fórmula de siempre; destajo completo, sin FCAS, bono ni división entre el rendimiento | Con todo a jornal, el resultado es idéntico hasta el exponente del `Decimal` (la revisión de la tarea lo comparó contra el motor anterior en los cinco APU de la línea base: 30 campos, 0 diferencias); la meta P5 lo vigila |
| `core/models/entidades.py` | `e6aeeb8` | Columna anulable `composicion_apu.modalidad` | Persistencia de D9; `NULL` se lee como jornal. Originó el hallazgo de las migraciones |
| `core/catalog/mapeo.py` | `e6aeeb8`, `c5434a6`, `bee9132` | La modalidad viaja en los dos sentidos; `a_modelo_rendimiento_estimado` exige `condiciones` | `core/catalog/` no es contrato congelado; es la capa que cumple RF‑33 y RF‑34 |
| `core/catalog/repositorio.py` | `0bd20f3`, `bee9132`, `8100dad`, `c5434a6` | `reemplazar_composicion` (UC‑11); RF‑33 en los dos caminos de escritura; rendimiento nuevo solo si cambia el valor o las condiciones respecto del último **estimado** | Ídem; `partida.rendimientos` nunca se vacía: el histórico es evidencia |
| `core/budget/excel.py` | `9f1f3be` | Columna *Modalidad* en la tabla de mano de obra de la hoja APU | Presentación; sin ella un destajo se leería como sueldo diario |

## Sesiones

| Fase | Commits principales | Bitácora o evidencia |
|---|---|---|
| P0 documentar (GP0) | `b3d2666` ERS, `1a972bf`/`40598d0` meta del sprint, `9b9de5e` D9 | [2026-09-16-P0-hallazgo-destajo.md](2026-09-16-P0-hallazgo-destajo.md) |
| P1 núcleo y catálogo | `e10440c`, `4ea15a1` modalidad; `0bd20f3` reemplazo; `cb2b68c` lista MaPreX en USD; `7f83f3b`, `4f2075a`, `feeaffa` rendimientos sembrados con condiciones; `bee9132`, `8100dad` arreglos de la revisión final | esta bitácora |
| P2.1 deudas y capa pura | `e6aeeb8`, `c5434a6`, `e880bd7`, `263f080`, `98776fb`, `0d4ff1f`; arreglos de auditoría `1ead3dc`, `6048c08`, `c50cdf1`, `aa85699` | [2026-09-20-P2-deudas-y-composicion.md](2026-09-20-P2-deudas-y-composicion.md), [2026-09-20-P2-hallazgo-migraciones.md](2026-09-20-P2-hallazgo-migraciones.md) |
| P2.2–P2.4 pantalla, buscador y ayudas | `a8714b3`, `adc60a5`, `a6763bf`, `3da1391` | esta bitácora |
| P3 flujo completo (GP1) | `9f1f3be`, `dfaaeb9`, `2ae725b`, `1558587`, `f884044` | esta bitácora |
| P4 pruebas (GP2) | `b16ce5e` AppTest, `617861b` siembra en una orden, `1789f12` guion manual, `6f824b6` corpus en cuarentena | [guion_prueba_arenia.md](../guion_prueba_arenia.md) |
| P5 cierre | `a634fda` modo entrega, `649e7b9` el commit de cierre de esta bitácora y `a478cfc` (arranque de la aplicación, hallazgo 7, post cierre) | [manual de usuario §3.7](../manual_usuario.md), [manual técnico §10](../manual_tecnico.md) |

La rama sumaba 48 commits sobre `p-base` al cerrar P5 (siete de ellos son planes ejecutables
`docs(plan)`); con la auditoría de la rama completa (sección siguiente) y el de esta bitácora,
suma 56 (`git log --oneline 471b3e2..HEAD | wc -l`).

## Hallazgos del sprint

1. **El destajo del artículo 114 de la LOTTT no cabía en el contrato (D9).** `LineaManoObra` no
   distinguía modalidad y el motor aplicaba FCAS, bono y división entre el rendimiento a toda línea.
   La sesión se detuvo (CLAUDE.md §9), elevó la decisión al tutor y la implementó como cambio
   aditivo. Detalle en la [bitácora del hallazgo](2026-09-16-P0-hallazgo-destajo.md) y en la
   [D9 del dossier](../dossier_g0.md).
2. **El FCAS del 600 % no tiene fuente normativa publicada (D4).** Ni la convención colectiva de la
   construcción ni los gremios lo publican; la literatura da rangos de 198–293 % y de 78–2 386 %.
   Recomendación: declararlo parámetro configurable del caso de estudio. De paso, la cláusula 20
   respalda que el bono se sume fuera del FCAS, como ya hace el motor. Detalle en la D4 del dossier.
3. **No hay herramienta de migraciones.** La columna `modalidad` no llegó a las bases ya sembradas
   (`create_all` no altera tablas) y la interfaz falló con la suite en verde. Queda la regla:
   toda sesión que cambie una columna declara antes qué pasa con las bases existentes
   ([bitácora](2026-09-20-P2-hallazgo-migraciones.md)).
4. **`AppTest` no conduce `st.data_editor`** (Streamlit 1.62 no expone el editor de tablas). Se
   resolvió sembrando `st.session_state[f"{clave}__filas"]` **antes** del primer `run()` y
   parchando el objeto módulo de `sys.modules`, no una ruta de texto
   ([manual técnico §10.3](../manual_tecnico.md#103-probar-la-interfaz-con-apptest)). Lo que
   `AppTest` no alcanza (teclear en celdas) lo cubre el guion manual.
5. **Un defecto de aislamiento de pruebas escribió en la base local.** `_SinExtraML`
   (`tests/unit/test_composicion_ia.py`) restauraba `sys.modules` pero no el atributo `componer` del
   paquete `ui.paginas`; un `monkeypatch.setattr` por ruta de texto aterrizaba en esa copia huérfana
   y el desvío de la base no surtía efecto. En la primera ejecución de la Tarea 1 de P4, tres
   pruebas de interfaz **escribieron en `data/apu.db` del worktree** una partida `UI-01-TUB`
   (id 6, 10 líneas de composición, 2 rendimientos). Se corrigió la causa en `b16ce5e`
   (`_SinExtraML` sincroniza el atributo del paquete; el arnés parcha el objeto de `sys.modules` y
   afirma que la base temporal existe antes de pulsar nada). **La partida `UI-01-TUB` sigue en esa
   base**, verificado en solo lectura al cerrar: la limpieza espera la decisión de Eugenio. El
   daño es solo de ese archivo local, ignorado por git y regenerable; el checkout principal no
   tiene `data/apu.db`.
6. **La lista de precios de la demostración nacía vacía.** `scripts/seed_demo.py` creaba su lista
   (20/09/2026) sin heredar los precios de la vigente: sembrar la línea base y la demostración en
   la misma base dejaba las cinco partidas `LB-*` con `CatalogoIncompleto` desde esa fecha. La regla
   incumplida ya estaba escrita en `core.catalog.precios.crear_lista_desde_archivo` («la lista nueva
   nace con todos los precios de la anterior»). Corregido en `617861b`, dentro del sembrador (esa
   función exige una lista anterior y el sembrador debe funcionar sobre una base vacía).
   **El mismo patrón está latente, sin corregir, en `scripts/seed_telecom.py`,
   `scripts/seed_industrial.py` y `scripts/seed_sistemas.py`**: cada uno crea su `ListaPrecios` sin
   heredar. Hoy no se manifiesta porque cada uno siembra por defecto su propia base, pero sembrar
   dos de ellos en la misma base dejaría sin precio las partidas del primero. La corrección son
   unas cinco líneas por sembrador, la misma de `seed_demo.sembrar_demo`: antes de crear la lista,
   `anterior = Catalogo(sesion).lista_vigente(FECHA)` atrapando `CatalogoIncompleto` (base vacía:
   nada que heredar), y tras el `flush()` de la lista nueva, copiar
   `models.PrecioInsumo(lista_id=lista.id, insumo_id=p.insumo_id, precio=p.precio)` por cada
   precio de `anterior`. No se aplicó en este sprint.
7. **`streamlit run` a secas no arrancaba la aplicación, con la suite en verde** — otro caso de
   «suite verde con la interfaz rota», como el hallazgo 3 de las migraciones. Las nueve páginas se
   registraban con una función llamada `render`, y `st.navigation` rechazaba la aplicación entera
   por ruta URL repetida; además, `streamlit run` a secas no pone la raíz del repositorio en
   `sys.path`, así que `import ui` fallaba. Ninguna prueba unitaria arrancaba `ui/app.py` completo.
   Corregido en `a478cfc` (cierre de P5): cada `DefinicionPagina` declara su `ruta_url` (el nombre
   de su módulo), la documentación pasa a `python -m streamlit run`, y dos pruebas nuevas arrancan
   `ui/app.py` con `AppTest.from_file`, en modo normal y en modo entrega. Hallazgo de la auditoría
   de la rama completa (2026‑09‑23).
8. **La lista MaPreX no se importó al catálogo** (decisión de la Tarea 2 de P4). La pantalla ya
   ofrece la referencia completa por el buscador, que lee los CSV directamente; y
   `crear_lista_desde_archivo` solo actualiza precios de insumos **ya catalogados**, así que con
   `lista_maprex_usd.csv` los 111 insumos habrían salido como desconocidos sin añadir nada.
9. **En la lista MaPreX, el precio de un equipo es el valor del activo, no una tarifa diaria.** Lo
   que lo lleva a costo diario es la depreciación de la composición (R6 exige que viva ahí). Se
   documentó en el script y en el README de la referencia en vez de convertir el dato, que se
   habría aplicado dos veces (`bee9132`).
10. **El corpus simulado se carga entero como `Dominio.CIVIL`** (`DOMINIO_CORPUS`) aunque sus filas
    salen de las cuatro referencias MaPreX: el dominio no describe su origen. Está en cuarentena
    (base propia obligatoria y meta P11), no alimenta `ml/` ni cuenta para G2.
11. **La advertencia de rendimiento RF‑27 no podía dispararse en la base sembrada**
    (`MINIMO_OBSERVADO_PARA_ADVERTIR = 2` y ninguna partida tenía dos observaciones). La siembra de
    demostración deja ahora dos en `DEMO-01-INST`, y el caso CP‑04 del guion la ejercita.

## Proceso

- Las fases P0–P1 tuvieron revisión por tarea y una revisión final del ramal; las tareas 1–3 del
  plan P2.1, también. El **2026‑09‑20** Eugenio suspendió la revisión por tarea: «las revisiones
  serán pautadas para una auditoría». Desde la Tarea 4 de P2.1 hasta este cierre **ningún revisor
  por tarea corrió**; el controlador verificó con lo objetivo (pytest `-W error`, ruff, metas,
  guardia, `data/apu.db` intacta).
- Coste medido en la auditoría de P2: **tres de los cinco hallazgos importantes estaban en la única
  tarea sin revisor**, y ninguno era detectable por pytest, ruff ni las metas. Las fases P2.2–P5
  tampoco pasaron por revisor: es lo que la auditoría pendiente tiene que mirar.
- Incidencias de entorno: agentes cortados por límite de gasto (429), por 403 de la API y por red
  (ENOTFOUND). Ninguna dejó trabajo a medias sin registrar.

## Métricas finales

| Indicador | Cierre |
|---|---|
| Pruebas con `-W error --strict-markers` | **690** pasan, **0 omitidas**, 0 fallan (101,72 s; resumen de `pytest -v`, que sí lo imprime en este entorno) |
| Evolución registrada | 559 + 4 omitidas sin extra `ml` (cierre P1) → 598 con todos los extras (auditoría P2) → 633 (cierre P2) → 648 (GP1) → 669 (GP2) → 673 (cierre P5) → 676 con `a478cfc` → 689 con el encargo A de la auditoría de la rama completa (UC‑11: editar no borra el desglose) → 690 con este encargo (B: RF‑35 editable) |
| `ruff check .` | limpio |
| `guardia_nucleo.py --base p-base` | código 0 (sin commits que toquen `adapters/` o `ml/`) |
| `git diff p-base --stat -- core/` | 7 archivos, +217 / −18 |
| `meta_datos.py` | 3/3 |
| `docs/api.json` y `docs/resultados_ml.md` regenerados | sin diferencias (el sprint no tocó la API ni `ml/`) |
| `meta_prototipo.py` | **12/12** |

## Pendientes del tutor

- **D9**: aval del cambio al contrato estable (modalidad por línea). Si lo rechaza, el criterio de
  degradación está en `PLAN_PROTOTIPO.md`: la modalidad pasa a trabajo futuro y el resto del
  prototipo no depende de ella.
- **D4**: aval para declarar el FCAS parámetro del caso de estudio, citando los rangos publicados.
- **Numeración de la ERS**: UC‑10/UC‑11 y RF‑33 a RF‑35 dejan RF‑32 y UC‑09 vacantes para el plan
  del asistente (`PLAN_ASISTENTE.md`); conviene que lo confirme.
- **Indicador de la tesis de UC‑10/UC‑11**: la ERS los marca «fuera de los cinco indicadores» en
  vez de forzar uno; observación para su criterio.

## Pendientes de Eugenio

- **Pautar la auditoría de la rama completa antes de fusionar el PR #7.** No se lanza por
  iniciativa propia. Debe mirar, como mínimo: las fases P2.2–P5, sin revisor por tarea; los menores
  diferidos de P0–P2 (entre ellos el mensaje de RF‑33 duplicado en los dos caminos del catálogo, la
  prueba NULL → jornal que no tuvo fase roja diagnóstica, el patrón «FK explícita y luego
  `expire()`» de `reemplazar_composicion`, y P11 acoplada a la ruta fija del generador); el cambio
  a `tests/unit/test_composicion_ia.py`, fuera del alcance original de su tarea por decisión del
  controlador; y del guion manual, que las cantidades se sembraron por `session_state` al obtener
  los resultados esperados y que la edición de la celda de precio se afirma leyendo el código.
- **Decidir qué hacer con `UI-01-TUB`** en `data/apu.db` del worktree (hallazgo 5): borrarla a
  mano, volver a sembrar con `--reiniciar` o dejarla.
- **Ejecutar el guion manual con una persona.** Queda abierta la pregunta de interfaz que se cerró
  «por ahora» el 2026‑09‑20: el buscador **añade una fila nueva** en vez de rellenar una en blanco.
  El guion describe ese comportamiento pero no lo plantea como pregunta al probador; conviene
  anotar si estorba.
- **Ayuda 2 (precio atípico) en la demostración:** la siembra no deja histórico de cambios de
  precio, así que en la base sembrada esa ayuda se abstiene y el guion no la ejercita.
- **Los tres sembradores con el patrón latente** (hallazgo 6): decidir si se corrigen.
- Abrir la aplicación en modo entrega en un navegador: la Tarea 5 lo probó con pruebas unitarias
  del filtro, no en pantalla.

## Estado final

- `uv run --no-sync pytest -q -W error --strict-markers`: **690 passed**, 0 omitidas (673 al cerrar
  P5; ver «Auditoría de rama completa» para la evolución hasta 690).
- `uv run --no-sync ruff check .`: limpio.
- `uv run --no-sync python scripts/guardia_nucleo.py --base p-base`: código 0.
- `uv run --no-sync python scripts/meta_datos.py`: 3/3.
- `uv run --no-sync python scripts/meta_prototipo.py`: 12/12 (P1–P11 en OK antes de esta
  bitácora; P12 la exige).

## Integración

Rama empujada hasta `6f824b6` al cruzar GP2 (autorizado por Eugenio); `a634fda`, `649e7b9` (cierre
de P5) y `a478cfc` (arranque de la aplicación, hallazgo 7) se empujaron después y son el estado
actual de `origin/inc/PLAN-prototipo`. Desde `b4f7321` (encargo A de la auditoría de la rama
completa) hasta el commit de esta bitácora — el encargo B — quedan por empujar, y el PR #7 por
actualizar para describir las fases P0 a P5 y la auditoría.
**Sin fusionar a `main`**: la fusión la decide Eugenio después de la auditoría.

## Auditoría de rama completa (2026‑09‑23)

Pautada por Eugenio antes de fusionar el PR #7 (sección «Pendientes de Eugenio»), con revisores por
encargo (regla vigente desde el 2026‑09‑23: la aprobación de esos encargos es la compuerta, no el
bloque de auditoría del 20/09).

- **Cuatro encargos:** arquitecto, pruebas y calidad, requisitos, verificador de hechos.
- **Veredictos:** tres «fusionar tras correcciones», uno «aprueba con correcciones»; ninguno
  bloqueante.
- **Hallazgo importante — encargo A (UC‑11):** editar una partida existente borraba su desglose en
  vez de precargar las tres tablas (paso 1 de UC‑11 sin cumplir pese a que RF‑33/RF‑34 lo daban por
  hecho). Corregido en `b4f7321` (`ui/composicion.py`: `filas_desde_composicion` y
  `motivo_para_no_reemplazar`; `ui/paginas/componer.py`: precarga tras la cabecera y guarda que
  rechaza con `st.error` si hay motivo) y documentado en `bb37656`; 13 pruebas nuevas
  (`tests/unit/test_composicion.py`, `tests/unit/test_ui_componer.py`), suite 676 → 689.
- **Correcciones de este encargo (B, documentación y menores):**
  1. Prueba de editabilidad del precio sugerido, RF‑35 (`cb19e1c`): 689 → 690.
  2. `docs/ERS.md` al día, RF‑33 a RF‑35 y UC‑10/UC‑11 de pendiente a cumplido (`b9c638f`).
  3. Decimales exactos en `test_costing_destajo.py` y fase roja NULL→JORNAL en
     `test_persistencia.py` (`df9bfc0`).
  4. Dependencia `ui`↔`scripts` documentada en `docs/arquitectura.md`, docstring corregido de
     `scripts/seed_demo.py::sembrar_demo`, riesgo declarado en D9 (`docs/dossier_g0.md`) — sin
     cambiar `PAQUETES_FUERA_DEL_NUCLEO` (`f4aab50`).
  5. Esta sección y el resto de esta bitácora (commit de este encargo).
- **Diferido con registro** (no se corrige en esta ronda):
  - Salvaguarda global de `data/apu.db` y `calidad_iso25010.md`: los resuelve el sprint de UI
    (`PLAN_UI.md`, sesiones U1.1 y U0 — rama `inc/PLAN-ui`, worktree `.claude/worktrees/ui`, no
    presente en esta rama).
  - Ruta de base por defecto (`RUTA_BASE_POR_DEFECTO = "data/apu.db"`) repetida en ocho páginas UI
    y en scripts; el sprint de UI (`PLAN_UI.md`, U1.5) la centraliza en `ui/caso.py`.
  - Mensaje de error de RF‑33 duplicado entre `Catalogo.cargar_composicion` y
    `Catalogo.reemplazar_composicion` (`core/catalog/repositorio.py:162-166` y `:222-227`); no se
    reabre el núcleo por un mensaje.
  - Carpeta de la referencia MaPreX (`data/precios/maprex_2026-07`) duplicada entre
    `ui/composicion.py:398-406` (`_CARPETA_REFERENCIA`) y `scripts/lista_maprex_usd.py:65-69`
    (`CARPETA`) — línea corregida contra el archivo real; el hallazgo original la citaba en
    `ui/composicion.py:304-313`.
  - Etiqueta de la técnica de la compuerta G2 que muestra la ayuda 4
    (`ui/paginas/componer.py:~570`), calculada con partidas `DEMO-`/`SIM-` en vez de solo datos
    reales.
  - El destajo se ejerce por precarga de lectura (`test_teclear_el_codigo_de_una_partida_guardada_precarga_sus_tres_tablas`)
    y en `test_editar_una_cantidad_y_guardar_reemplaza_la_composicion` (`tests/unit/test_ui_componer.py`),
    que guarda `DEMO-01-INST` por la pantalla; esa partida tiene una línea de destajo cuya modalidad
    se verifica tras guardar. Lo que falta es un `AppTest` que teclee una fila de destajo nueva.
  - Puntos menores de usabilidad del UC‑11, diferidos por la compuerta de revisión:
    - la precarga no rellena el encabezado (descripción ni unidad), ni las condiciones del rendimiento;
    - si la partida existente no tiene precio en la lista actual (`CatalogoIncompleto`), no se precarga nada;
    - al pasar de un código existente a uno nuevo, las filas anteriores quedan en las tablas (útil como «copiar una partida», pero no documentado en el guion);
    - `cargar_composicion` aún acepta una composición vacía para una partida NUEVA;
    - la precarga precifica con la lista de hoy;
    - la comparación de descripción es estricta salvo por espacios al borde.
  - Ninguna prueba corre contra un archivo de esquema antiguo real; la de la migración
    (hallazgo 3, y su fase roja de este encargo) solo simula la columna en `NULL`.
  - Herencia de precios en los tres sembradores restantes, sin corregir (hallazgo 6).
  - El mensaje del commit `b32926b` dice «cinco fases»; `PLAN_PROTOTIPO.md` tiene seis, P0 a P5.

Re-revisión acotada de las correcciones (a478cfc..e150d37): arquitecto y pruebas y calidad — se puede fusionar; 690 pruebas en verde, `data/apu.db` intacto. Condición: empujar y confirmar la CI sobre el nuevo HEAD antes de fusionar. Tras la fusión, la primera sesión es U1.1 de `PLAN_UI.md` (salvaguarda de aislamiento).

**D9 sigue pendiente del aval del tutor** (sección «Pendientes del tutor»).
