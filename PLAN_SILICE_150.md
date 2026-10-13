# Plan de Silice 1.5: fusión con los libros de la empresa

**Spec:** [`docs/especificaciones/2026-10-13-silice-1.5-fusion-design.md`](docs/especificaciones/2026-10-13-silice-1.5-fusion-design.md)
· **Rama:** `inc/spec-1.5` (worktree `.worktrees/v15`) · **Bitácora:**
[`docs/bitacora/2026-10-13-silice-150.md`](docs/bitacora/2026-10-13-silice-150.md)

Lo que queda se divide en **sesiones**. Dentro de cada sesión, los **subagentes** trabajan en paralelo en archivos
distintos del mismo worktree. El líder integra, confirma cada pieza y abre la sesión siguiente en cuanto se
cumplen sus dependencias. Rige la regla del 2026-10-12: sin pruebas nuevas (solo ruff); la CI corre las pruebas
existentes. Los libros reales se usan en local y nunca entran al repositorio.

## Interfaces fijas (para que las sesiones corran en paralelo)

| Módulo | API |
|---|---|
| `adapters.hoja_empresa.modelo` | `LibroLeido`, `ApuLeido`, `DatosDevolucion`, `ApuCalculado`, `FilaHallazgo`, `FilaAlerta`, `FilaTraza` |
| `adapters.hoja_empresa.guardia` | `ArchivoRechazado`, `verificar_archivo(datos, nombre)` |
| `adapters.hoja_empresa.lector` | `leer_libro(datos, nombre, perfil=None) -> LibroLeido` |
| `adapters.hoja_empresa.pdf` | `leer_pdf_simple`, `reglas_pdf_simple` (L10), `leer_totales_impresos`, `cotejar_con_libro` (L11) |
| `adapters.hoja_empresa.reglas` | `REGLAS_LIBRO`, `reglas_del_libro(libro) -> list[Hallazgo]` (L1-L9) |
| `adapters.hoja_empresa.escritor` | `escribir_devolucion(origen: bytes, datos: DatosDevolucion) -> bytes` |
| `fusion.alertas` | `ContextoPrecios(tasa_en, precio_propio, umbral)`, `alertas_de_precios(...)` |
| `fusion.proceso` | `procesar_libro(datos, nombre, *, pdf=None, pdf_nombre="", contexto=None, fecha_libro=None, fecha_devolucion=None, otro=None) -> ResultadoFusion`; `devolver(resultado) -> bytes`; `servicios_desde_sesion(session) -> ContextoPrecios`; `fecha_del_libro(libro)` |

## Sesiones

| Sesión | Contenido | Subagentes en paralelo | Depende de | Estado |
|---|---|---|---|---|
| **V0** | spec, contrato, enmiendas (NORMAS, horizonte, 1.0.0, S3), meta de datos D4, bitácora | líder | — | hecha |
| **V1** | guardia + perfil + lector · PDF (L10, L11) · anonimizador | 3 | V0 | hecha |
| **V2** | reglas L1-L9 (+ unión del borrador C-1) · `fusion/` (mapeo, F1, alertas, proceso) · escritor calcado | 3 
| **V3** | página "Libro de la empresa" (UI) · rutas `/v1/libros` (API) · `scripts/fusion_verificar.py` (aceptación) | 3 | interfaces fijas (arriba) | hecha |
| **V4** | integración: correr la aceptación sobre los libros reales, corregir por área (un subagente por módulo con fallas), ruff de todo, meta de datos | 1-3 | V2 + V3 | hecha: **96/96 metas OK** con el código congelado (53b6aa2) |
| **V5** | revisión por encargos: requisitos, arquitectura, pruebas y calidad, verificador de hechos, seguridad. Rulings en la bitácora; corrección de lo bloqueante | 5 + arreglos | V4 | en curso |
| **V6** | PR a `main`, CI verde y fusión (autorizada con CI verde y encargos aprobados) · memoria y resumen a Eugenio | líder | V5 | pendiente |

## Aceptación (spec §7)

`uv run python scripts/fusion_verificar.py <carpeta de libros reales>` debe detectar los hallazgos de la tabla del
spec §7. Además, cada libro devuelto debe reabrir sin `#REF!`, sin `INDIRECT` y sin vínculos externos, con un valor
guardado en cada fórmula, y con P.U. y totales iguales a los de Silice.
