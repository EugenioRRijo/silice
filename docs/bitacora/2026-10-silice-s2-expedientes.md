# Expedientes de la 0.7.0 (S2, presupuesto vivo): núcleo

**Fecha:** 2026-10-11 · **Plan:** `PLAN_SILICE_070.md` · **Spec:** `docs/especificaciones/2026-10-11-silice-s2-presupuesto-vivo-design.md` §5.4 · **Bitácora de la versión:** [2026-10-silice-070.md](2026-10-silice-070.md)

Tres expedientes, uno por rama de núcleo (`inc/070-s2-1-nucleo`, `inc/070-s2-2-nucleo`, `inc/070-s2-3-nucleo`), cada uno commiteado antes de su código y aprobado por el tutor antes de abrir la rama. `core/contracts/` no se toca. El método es el de los expedientes de la 0.6.0.

## SL‑E4 Valuaciones, línea base de control y su auditoría

**Problema.** Un presupuesto no dice qué se ejecutó de él: no hay dónde registrar cantidades ejecutadas por período, con fuente, ni nada que impida que lo ejecutado supere lo presupuestado sin una variación registrada (H‑D5, RF‑72 a RF‑74, principio 7).
**Diseño.** Nueve tablas aditivas en `core/models/control.py` (revisión `caso_0005_s2_valuaciones`); el calendario hábil (`core/budget/calendario.py`); los tipos y las reglas R13 y R14 en `core/verification/valuaciones.py`, **fuera de `REGLAS`** (reciben una instantánea de control con `habiles_entre` inyectado); el registro, la anulación, la instantánea y la importación de Excel en `core/budget/valuaciones.py`; el puente a S1 en `core/budget/puente.py` (`ejecutado_por_periodo`, `estudio_con_valuaciones`, tabla `cita_valuacion`). Las valuaciones y los costos reales son solo-agregar; una valuación registrada y no anulada cuenta desde su registro (RV‑18). La lectura de la instantánea trae la versión con cuatro consultas (`selectinload`) y no con unas tres por renglón (RP7‑9); se agrega al final de S2‑4, en su propia rama de núcleo, tras medir RNF‑15, con una prueba que cuenta sentencias; no cambia ningún resultado.
**Por qué es genérico.** Toda obra se valúa por cantidades de sus partidas, sea del dominio que sea; nada de lo anterior nombra una especialidad.
**Qué no toca.** Ninguna tabla existente gana columnas; ninguna lectura anterior cambia; R13 y R14 no entran a `REGLAS` ni al informe guardado (S2‑R13).
**Pruebas que lo fijan.** `tests/unit/test_calendario.py`; `tests/unit/test_r13_r14.py` (conjunto exacto de hallazgos de V‑S, SIS‑001 y fronteras); `tests/integration/test_valuaciones.py` (OB‑S2 a mano y por Excel; inmutabilidad; anulación); `tests/integration/test_importar_valuaciones.py` (Excel malformado se rechaza entero); `tests/integration/test_ejecutado_por_periodo.py` y `test_estudio_cita_valuaciones.py` (asignación por *hasta*, registradas no anuladas, reajustable con `min`, línea base invalidada por cambio de moneda); `tests/integration/test_migracion_s2.py` (una base de la 0.6.0 abre con las tablas de control).
**Impacto.** 8 tablas en `caso_0005` (las 7 del spec más `cita_valuacion`, RP7‑4); `calendario.py` entra aquí y no en SL‑E5 (RP7‑2). **Costo si es erróneo.** Una revisión de Alembic más (RV‑3); las severidades de R13 y R14 son parámetros.

## SL‑E5 Valor ganado, separación del desvío de control y reproyección

**Problema.** El presupuesto no dice cómo va la obra contra su plan ni cuánto del desvío es de plazo, de precio o de consumo (H‑D2, RF‑75 a RF‑77, aporte central del horizonte §5).
**Diseño.** `core/budget/valor_ganado.py` (funciones puras sobre `Presupuesto`, plan y valuaciones: PV, EV, AC, SV, CV, SPI, CPI, BAC, EAC por índice y por sistema, VAC; separación `CV = precio + consumo` exacta; reproyección por partida con el ritmo `r = s/n·mult`; alertas AL‑1 a AL‑6 con umbrales SUPUESTO_DECLARADO; `equilibrio_proyectado`); `core/budget/control.py` (orquesta instantánea, estado y precios del corte); `core/budget/puente.py` gana `reajuste_reconocido`; `core/budget/equilibrio.py` se refactoriza extrayendo `equilibrio(venta, costo_variable, costo_fijo, curva)` sin cambiar `punto_equilibrio`.
**Por qué es genérico.** Se calcula sobre `Presupuesto`, plan y valuaciones, sin conocer dominios.
**Qué no toca.** El resultado de `punto_equilibrio` (TI‑001 sigue en 28 586,76 USD, Día 6); ninguna tabla.
**Pruebas que lo fijan.** `tests/unit/test_valor_ganado.py` (OB‑S2, §7.1; la identidad de la separación); `tests/unit/test_equilibrio_extraido.py` (TI‑001 literal sin editar); `tests/unit/test_reproyeccion.py`, `test_alertas.py`, `test_pe_proyectado.py` (los dos escenarios, sin reajuste y con el reconocido; la obra «según el plan» da el PE de SF‑E3 con su misma ubicación); `tests/integration/test_control.py`, `test_reajuste_reconocido.py`.
**Impacto.** `equilibrio.py` se refactoriza sin cambiar su resultado; funciones puras nuevas. **Costo si es erróneo.** Si el tutor prefiere otra separación u otro EAC, cambian dos funciones puras y su memoria (S2‑R1, S2‑R11).

## SL‑E6 Opciones de recuperación y decisión

**Problema.** Ante un retraso, el sistema no dice qué cuesta recuperarlo ni deja decidir con el costo a la vista (H‑D2, RF‑78, RF‑79; horizonte §4).
**Diseño.** `core/budget/recuperacion.py` (puro): costo diario de la ruta, `E(k) = Σ η^(j−1)`, límites de la LOTTT (arts. 118, 173, 178, 182, a cotejar), las cuatro opciones; `core/budget/decision.py`: `aplicar_decision` crea la versión por `guardar_edicion(motivo="recuperacion")`, que pasa por el embudo único `guardar_presupuesto`, y guarda la decisión con la foto de lo que el usuario vio (`caso_0006_s2_decision`, tabla `decision_recuperacion`).
**Por qué es genérico.** El costo sale del rendimiento y la cuadrilla de cualquier APU; una partida sin jornal da «no aplica» sin dividir.
**Qué no toca.** `guardar_edicion` gana un parámetro con valor por defecto (`motivo: str = "edicion"`); `MOTIVOS_VERSION` gana un valor (`"recuperacion"`); no hay otro camino que cree versiones.
**Pruebas que lo fijan.** `tests/unit/test_recuperacion.py` (cuatro opciones de OB‑S2, límites de la LOTTT, monotonía, «no aplica» en TI‑001 y SIS‑001); `tests/integration/test_decision_crea_version.py` (siete registros de cambio, curva, línea base intacta, un solo paso por el embudo, `test_guardar_edicion_sin_motivo_sigue_siendo_edicion_y_rechaza_un_motivo_desconocido`).
**Impacto.** Un parámetro con defecto, un motivo más, una tabla. **Costo si es erróneo.** Cambiar `η`, `k_máx` o `a` es un parámetro; cambiar el modelo `E(k)` es una función pura (S2‑R5).
