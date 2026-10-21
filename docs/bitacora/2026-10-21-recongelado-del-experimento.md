# Re-congelado del experimento tras retirar Streamlit (F11, opción A)

**Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-retiro-streamlit` · **Resuelve:** `2026-10-19-congelado-del-experimento-roto-por-la-migracion.md`.

## Ruling
Eugenio (2026-10-21): retiro definitivo de Streamlit y del Visor 3D, y el experimento se descongela y se vuelve a congelar a propósito
(opción A del hallazgo del 2026-10-19): «este será nuestro definitivo». Palabra de Eugenio, sin acta. **Pendiente:** avisar al tutor
por escrito (ver la enmienda del ERS).

## Qué cambia y qué no
- `asistente/experimento/protocolo.json`: `archivos_del_auditor` pasa de 49 a 50 rutas. `ui/hoja.py` → `aplicacion/hoja.py`,
  `ui/composicion.py` → `aplicacion/composicion.py`, y se añade `aplicacion/errores.py` (donde vive `HojaInvalida`, que el auditor
  captura y que estaba dentro de `ui/hoja.py` al congelar). Commit `7caad16e`.
- **La lógica del auditor no cambia.** Los 7 archivos de `asistente/` que se tocaron (`validacion`, `orquestador`, `privacidad`,
  `propuestas`, `servicio` y `experimento/{banco,ejecucion}`) difieren de la versión congelada (`cd46732`) solo en líneas de
  importación (`ui` → `aplicacion`) y en el orden de los imports. Equivalencia AST demostrada y juzgada por un árbitro independiente:
  `2026-10-21-retiro-f7-equivalencia.md`.
- Los otros 40 archivos de la lista (incluidos `core/verification`, `adapters/espacio`, `core/contracts`,
  `core/budget/presupuesto.py`) son byte a byte los de `cd46732` (`git diff cd46732 HEAD` vacío, comprobado archivo por archivo).
- `aplicacion/hoja.py` es la copia de `ui/hoja.py` (121 definiciones idénticas; cambian el docstring y 3 imports);
  `aplicacion/composicion.py` contiene todas las definiciones de `ui/composicion.py` más 20 propias del producto, de modo que el
  auditor ahora hashea también esas 20.
- **El banco del experimento no cambia:** `calcular()["banco"]` es igual al de `congelado.json` (`29446b12…`).
- Cambian, como se espera, las huellas `protocolo` y `auditor`; se regeneran en el commit siguiente (`congelado.json`).

## Después de re-congelar
Cualquier cambio posterior en un archivo de `archivos_del_auditor` vuelve a poner en rojo
`tests/unit/test_experimento_congelado_vigente.py`. Si hace falta tocar uno, se hace a propósito y se vuelve a congelar con
el mismo procedimiento (árbol limpio, `congelar(<sha>)`, commit aparte).
