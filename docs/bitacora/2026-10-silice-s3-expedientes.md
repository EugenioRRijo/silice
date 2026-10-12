# Expedientes de la 0.8.0 (S3, auditor y paquete): núcleo

**Fecha:** 2026-10-11 · **Plan:** `PLAN_SILICE_080.md` · **Spec:** `docs/especificaciones/ 2026-10-11-silice-s3-auditor-paquete-design.md` §14.1 · **Bitácora:** [2026-10-silice-080.md] (2026-10-silice-080.md)

Cuatro expedientes, uno por cambio de `core/` (rama única `inc/080-s3-2-nucleo`), cada uno
commiteado antes de su código y aprobado por el tutor antes de abrir la rama. `core/contracts/`
no se toca. Ningún expediente agrega columnas a una tabla existente.

## SL‑E8 Documento canónico de una versión y su lectura

**Problema.** Para sellar, enviar y reauditar una versión hace falta un solo texto que diga qué es,
con los mismos bytes en cualquier instalación y sin identificadores de fila.
**Diseño.** `core/budget/canonico.py`: `documento(session, version) -> bytes` serializa, desde las
filas guardadas (nunca recalculadas), claves ordenadas, sin espacios, UTF‑8 sin escapar, `Decimal`
como `format(valor, "f")` y sin ningún `id`; `leer(objeto) -> DocumentoLeido` es la inversa y valida
cada cifra con `PATRON_CIFRA` (`^-?[0-9]{1,20}(\.[0-9]{1,28})?$`) antes de construir un `Decimal`.
Incluye la moneda del proyecto (RP8‑3) y el origen de cada precio. `VERSION_FORMATO = 1`.
**Por qué es genérico.** Describe cualquier presupuesto versionado, de cualquier dominio; lo usan la
cadena, el paquete y la API (DRY).
**Qué no toca.** Ninguna tabla, ningún escritor; solo lee. No importa `seguridad` (el patrón de cifra
se repite y una prueba lo compara con el del lector estricto, RP8‑2).
**Pruebas que lo fijan.** `tests/integration/test_canonico.py`: el vector a mano (2271 bytes,
SHA‑256 `b4b952dd…3936`), ida y vuelta, determinismo entre dos bases, rechazo de cifras fuera de
patrón y del campo `id`.
**Impacto.** Un módulo nuevo. **Costo si es erróneo.** Cambiar el documento exige subir
`VERSION_FORMATO`; los eslabones ya sellados conservan el suyo y se verifican con él.

## SL‑E7 Cadena de huellas sellada en el embudo

**Problema.** Nada impide editar la historia de una versión ni dice quién la confirmó (RF‑83).
**Diseño.** Tabla aditiva `eslabon_version` (`core/models/cadena.py`, revisión
`caso_0007_s3_cadena`, índice único `(proyecto_id, anterior)` que impide dos hijos del mismo
eslabón). `core/budget/cadena.py`: `marcar_por_sellar` (la llama `guardar_presupuesto`, que ahora
recibe `usuario` y `anexos_de`), el sellado en un evento `before_commit` de la transacción raíz
(ignora savepoints, RP8‑8), `verificar_cadena` (recalcula cada huella desde la base),
`sellar_historial` (versiones anteriores a S3, `tipo = "retroactivo"`), `anexos_por_omision`.
Un `commit` sin `usuario` falla con `SelladoSinUsuario` y no escribe nada.
**Por qué es genérico.** Cualquier presupuesto versionado se encadena igual, sin conocer dominios.
**Qué no toca.** El cómputo, los contratos ni las tablas existentes; los llamadores del núcleo
(`cotizacion`, `actualizacion`, `edicion`, `importacion`) solo pasan `usuario`.
**Pruebas que lo fijan.** `tests/integration/test_cadena.py` (huella por componente, sellado
retroactivo, raíz y savepoints, ramificación imposible, `usuario` obligatorio, ruptura detectada
por contenido, por registro, por anexo y por eslabón).
**Impacto.** Una tabla, un módulo, dos parámetros del embudo. **Costo si es erróneo.** Una revisión
de Alembic más; los eslabones se pueden resellar con `tipo = "retroactivo"` declarado.

## SL‑E12 WAL y `BEGIN IMMEDIATE` para varios usuarios

**Problema.** Dos personas guardando a la vez pueden bifurcar la cadena o chocar con
`database is locked`.
**Diseño.** `core/catalog/sesion.py`: `crear_motor` fija WAL, `busy_timeout = 5000`, claves
foráneas e `isolation_level = None`; un evento `begin` emite `BEGIN IMMEDIATE` cuando la opción de
ejecución `silice_inmediata` está puesta (RP8‑10); `abrir_sesion_de_escritura(motor)` la pone.
**Por qué es genérico.** Sirve a cualquier base SQLite con varios escritores.
**Qué no toca.** Las lecturas siguen con `abrir_sesion`; ninguna tabla.
**Pruebas que lo fijan.** `tests/integration/test_concurrencia.py` (PRAGMA, `threading.Barrier`
con 3 hilos por 10 guardados: 30 versiones, cadena lineal, ningún `database is locked`).
**Impacto.** Un cambio de motor. **Costo si es erróneo.** Quitar la opción vuelve al `BEGIN` por
omisión; el índice único de SL‑E7 sigue impidiendo la bifurcación (falla el segundo, no se corrompe).

## SL‑E9 Diferencia entre versiones y revaloración

**Problema.** Quien revisa necesita saber cuánto cambió una entrega respecto de la anterior y por
qué (cantidad o precio), y valorar un paquete con su propia lista.
**Diseño.** `core/budget/comparacion.py` (puro): `diferencia_entre_versiones` por partida,
`Δ total = (q2 − q1)·PU1 + (PU2 − PU1)·q2` (el término cruzado queda en el precio), partida nueva
o eliminada como desvío de cantidad entero; `revalorar` valora un documento con otra lista
emparejando por referencia de precio o por código, y lista lo que no empareja.
**Por qué es genérico.** Compara dos presupuestos cualesquiera; es distinta de la separación del
desvío de S2 (término cruzado en el consumo) y no la reutiliza (RV‑10).
**Qué no toca.** Ninguna tabla ni lectura de la base.
**Pruebas que lo fijan.** `tests/unit/test_comparacion.py` con `diferencias_s3.md` (840 → 1130,
Δq 250, Δp 40; entrega Q 550 → 589) y su rehacer con fracciones.
**Impacto.** Un módulo nuevo. **Costo si es erróneo.** Cambiar la descomposición es cambiar una
función y su memoria.
