# Fases F5, F7 y F8 · Revisión final · Árbitro único, xhigh (2026-11-07): DEVUELTO por 1 MAYOR (corregido después)

> Delta `70977c07..6169047d`. Respuesta literal en lo esencial (sin rutas absolutas del equipo); guardada por Claude.

**VEREDICTO: DEVUELTO** por un MAYOR de minutos; **todo lo demás del delta, aprobado**. El árbitro dejó dicho: «con el
MAYOR 1 corregido y la suite en verde, apruebo sin otra revisión completa».

| Hallazgo de la revisión anterior | Estado | Evidencia |
|---|---|---|
| P1 | RESUELTO | sondas C, C2, D y E rechazadas; la ruta completa de 3 hojas (33.449 bytes) pasa de 751,7 MiB y 302,5 s a 1,4 MiB y 0,1 s. No usar `max_col=101` era lo correcto: openpyxl descarta en silencio una celda en XFD |
| N1 | funciona, pero rompió INV-052 (MAYOR 1) | con `sys.platform` simulado: linux 35 pruebas y 0 de pywebview real; win32 39 y 4; 0 omitidas |
| N3, N4, N5, N6, N7 | RESUELTOS | N5: sin ciclo entre `fusion` y `aplicacion` (Tarjan sobre el AST); las 4 guardias nuevas muerden con mutaciones |
| N8 | PARCIAL (MENOR 3) | |
| Regresión `5f0bcfbb` | corregida por la reversión `452e0326` | `Bandeja.test.tsx` en verde |

**MAYOR 1.** `tests/unit/test_recoleccion_por_plataforma.py:10` importaba de `tests.unit.conftest` y violaba INV-052
(`test_arquitectura.py:350-373`). **Corregido en `6bdac28d`**: la regla vive en `tests/fixtures/plataforma.py`.

**MENOR** (corregidos en `11b77b45`..`064dc010` y `bf65515a`):
1. Sin tope de celdas para el libro entero: 64 hojas en su tope pasaban la guardia (128 millones de celdas, ~1 GiB).
   Ahora `MAX_CELDAS_LIBRO = 2 × MAX_AREA_HOJA`.
2. Una celda con solo formato rechaza el libro con un mensaje confuso: ahora dice «celdas con datos o con formato» y el
   manual de usuario (§12.5) explica qué hacer. Eugenio debe probar una vez, en local, el libro vial real.
3. «caso abierto» en `api/rutas/precios_empresa.py:51` y `api/rutas/similares.py:21` (y el rótulo de Acerca): «la
   carpeta abierta», con una guardia que se salta los docstrings.
4. ESTADO y CHANGELOG: puestos al día con este resultado.

**Preexistente, fuera del delta (expediente aparte):** `adapters/hoja_empresa/lector.py` (`_celdas_reales`, el lector
del libro conocido, desde 1.5) recorre cada celda de relleno: 3,7 s con 12 KB y 39,5 s con 103 KB; lineal, del orden de
45 minutos de CPU en el tope de la guardia. Corrección propuesta: los mismos topes de `_filas`, con prueba roja.

## TDD
Rojos `36833a0a`, `b7747402`, `5b68c02c` y `ac7c00e0` fallan por la razón correcta y sus verdes pasan. Lo que falló fue
el cierre: nadie corrió la suite completa tras `ff3f799c`.
