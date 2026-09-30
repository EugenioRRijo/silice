# Bitácora — Referencia de precios MaPreX julio 2026 en el plan multidominio

**Fecha:** 2026‑09‑02 · **Rama:** `inc/PLAN-maprex` (fusionada a `main` con `--no-ff`) ·
**Base:** `f880907` (plan multidominio) · **Origen:** pedido del usuario («desarrollar el plan
para cubrir las demás ingenierías; te dejo pdf de maprex de un mes pasado para tener referencias
y contexto de precios»), con tres PDF nuevos en la raíz del repo.

## Qué llegó

Los tres listados oficiales **MaPreX v26.0.0.1** (BD `BDLaing08072026.mdb` del 08/07/2026,
impresos el 13/07/2026), aportados por el autor. Era exactamente el «trabajo de campo» que el
PLAN_MULTIDOMINIO dejó como dependencia externa (carta MaPreX/Lulowin, tarifario CIV):

| Listado | Renglones aprox. | Lo que aporta |
|---|---|---|
| materiales | ≈ 12 500 | insumos de la línea base civil (PVC, cemento, arena, encofrado) y cobertura telecom (fibra ≈ 58 menciones, UTP, racks) e industrial (válvulas ≈ 172, rodamientos, compresores) |
| equipos | ≈ 2 850 | retroexcavadoras (49) y compactadoras (44) de la línea base; **factor de depreciación por equipo** (columna Cop/Depr.) |
| mano de obra | ≈ 790 | tabulador construcción (25/03/2026 + bono ≈ 240 USD/mes), **tabulador CIV al 01/07/2026 (43 filas P‑1…P‑10)**, sectoriales (petrolero, PEQUIVEN, METOR) |

Precios en bolívares; la tasa está declarada dentro del propio listado de MO:
**633,3644 Bs/USD al 01/07/2026**.

## Qué se hizo

1. **Evidencia archivada** en `data/precios/maprex_2026-07/` (PDF renombrados sin tocar su
   contenido + [README](../../data/precios/maprex_2026-07/README.md) con estructura, tasa,
   cobertura por dominio y reglas de uso). Se creó `data/precios/` como casa de la evidencia
   transversal: los listados sirven a los cuatro dominios y no pertenecen a ningún
   `data/<dominio>/fuentes/`.
2. **[PLAN_MULTIDOMINIO.md](../../PLAN_MULTIDOMINIO.md) actualizado** (11 sesiones ahora):
   situación de partida al 2026‑09‑02; **nueva Sesión M0.2 «Referencia MaPreX estructurada»**
   (CSV canónicos por dominio, solo los insumos que los catálogos necesitan, fila a fila contra
   el PDF, Bs→USD con tasa declarada); degradación GM2 con MaPreX como proxy nacional fechado
   antes que RSMeans; GM3 reescrita porque el tabulador CIV **ya está en el repo**; M1.3 con la
   referencia MaPreX como lista 2 (primer contraste de mercado real del proyecto); M3.1 partiendo
   del tabulador CIV estructurado.

## Hallazgos

| Hallazgo | Consecuencia |
|---|---|
| El listado de equipos trae factor de depreciación por equipo | Criterio de mercado externo y fechado para **R6** (`CriterioDepreciacion`): el criterio se podrá declarar contra fuente, no heredar del APU manual |
| El listado de MO contiene el tabulador CIV completo (43 filas, incluye ingeniero computista y analista de telecomunicaciones) | La dependencia externa de **GM3** desaparece; queda como mejora opcional la encuesta TI |
| El par jornal + bono del tabulador construcción está fechado | Evidencia para la decisión de **fuente del FCAS** del [dossier G0](../dossier_g0.md) |
| Los listados son de julio 2026 y están en Bs | Son **referencia**, no ronda vigente: todo derivado lleva `fecha_vigencia` 2026‑07 y tasa declarada; la ronda vigente sigue en el trabajo de campo |
| Sin tarifas TI de mercado ni HH/PF | La productividad de sistemas sigue saliendo de benchmark declarado (ISBSG), como ya decía el plan |

## Qué NO se hizo (deliberado)

No se extrajo ningún CSV ni entró ningún precio al catálogo: eso es la Sesión M0.2, con
verificación manual fila a fila (principio 2 del plan). Esta sesión solo archiva la evidencia y
pone el plan al día. Tampoco se tocaron los archivos con cambios pendientes de la sesión de
redacción pausada (`NORMAS.md`, `README.md`, `docs/linea_base.md`, `docs/tesis/…`), que siguen
sin commitear tal como estaban.

## Estado al cierre

```
uv run pytest           -> 395 passed (exit 0; sesión solo de documentos y datos)
uv run ruff check .     -> limpio
git diff --stat core/   -> vacío
```

## Próximos pasos

1. **Sesión M0.2** (estructurar la referencia MaPreX) o **M1.1** (fuentes ARENAZA) — ambas sin
   dependencias externas; M0.2 además deja lista la «lista 2» que M1.3 usa de contraste.
2. Trabajo de campo restante del autor: ronda vigente de cotizaciones (civil ~9–14 insumos,
   industrial 3–5 activos) y carta para la serie mensual MaPreX; ya no bloquea ninguna compuerta.
