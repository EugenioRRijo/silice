# Hallazgo: la migracion rompio la guardia del experimento congelado (decision pendiente de Eugenio)

**Fecha:** 2026-10-19 · **Detectado por:** el subagente del diseno de la Hoja (T10a), confirmado por el orquestador.

## Que pasa
`tests/unit/test_experimento_congelado_vigente.py` falla en la rama de la migracion (`inc/ruta-s2-mig*`) con
«auditor cambio desde el congelado». Eugenio decidio el 2026-10-18 (opcion A) que el protocolo del experimento **no se
toca** (RS-9, RF-141): `asistente/experimento/protocolo.json` lista `archivos_del_auditor`, entre ellos `ui/hoja.py` y
`ui/composicion.py`, y `congelado.json` (commit `cd46732`) guarda su huella.

Los dos archivos cambiaron por la migracion, no por el producto de `main` (los commits **no** estan en `origin/main`):

| Archivo | Cambio desde el congelado | Commit |
|---|---|---|
| `ui/composicion.py` | RM-1: 729 lineas salen a `aplicacion/composicion.py`; queda reexportacion | `a582847` |
| `ui/hoja.py` | 5 lineas (importa errores desde `aplicacion/errores`) | `bdf77cc` |

`git diff cd46732 HEAD` confirma que **solo esos dos** de los archivos congelados que miramos difieren (`core/verification` y
`adapters/espacio/reglas.py` no cambiaron).

## Por que importa
La CI de `main` quedaria en rojo al fusionar la migracion, y re-congelar cambia la huella de un protocolo que Eugenio declaro
inmutable. Son cambios mecanicos (equivalentes), pero la guardia existe justamente para obligar a una decision consciente.

## Opciones (no ejecutadas)
- **A. Re-congelar a proposito** tras una prueba de equivalencia de comportamiento, en un commit aparte con ruling de Eugenio
  (y, si se quiere, nota al tutor). Es lo mas limpio para el codigo (DRY) y reversible por git.
- **B. Restaurar los dos archivos byte a byte** a su version congelada y mantener la logica duplicada en `aplicacion/` hasta
  retirar Streamlit. Respeta la decision literal; viola DRY temporalmente (729 lineas de composicion; la hoja seria mucho mas).
- **C. Para la Hoja:** no tocar `ui/hoja.py`; el front nuevo usa un `aplicacion/hoja*.py` propio (sin mover codigo) y la
  clasica queda intacta hasta retirarla. No resuelve `ui/composicion.py` ni `ui/hoja.py` ya modificados.

## Ruling del orquestador mientras Eugenio no decide
1. **No se re-congela** ni se restaura nada: es una decision de Eugenio sobre el protocolo del experimento.
2. La migracion **no debe fusionarse a `main`** mientras esta prueba falle; el PR, si se abre, lo declara.
3. T10 (Hoja): no se toca `ui/hoja.py` ni `ui/composicion.py`. La implementacion queda bloqueada hasta elegir A, B o C.

## Ruling 2 del orquestador (2026-10-19): la Hoja sigue por el Plan C

- El diseno de la Hoja (`docs/especificaciones/2026-10-19-hoja-react-design.md`, commit `0e0427c`) pasó 3 rondas de arbitraje: la
  ronda 3 dejo 3 hallazgos MAYOR de texto (sin BLOQUEANTE); el implementador los corrigio y los verifico el orquestador
  (con las rondas agotadas, manual del arbitro §3). **Estado: aprobado por el orquestador, no por el arbitro.**
- **D-1 por defecto = Plan C**: `aplicacion/hoja*.py` propio, sin tocar `ui/hoja.py` ni `ui/composicion.py`, con la clasica intacta y
  una prueba de paridad contra ella. Es el unico camino que respeta la decision de Eugenio del 2026-10-18 (RS-9) y es reversible
  (se borra `aplicacion/hoja*`). Costo aceptado: ~2 100 lineas duplicadas, deuda con retiro junto a Streamlit.
- Sigue **pendiente de Eugenio** la guardia del congelado ya rota por `ui/composicion.py` y `ui/hoja.py` (opciones A/B/C arriba) y,
  por tanto, la fusion de la migracion a `main`.

**Cierre (2026-10-21):** resuelto por el re-congelado a propósito (opción A); ver `docs/bitacora/2026-10-21-recongelado-del-experimento.md`.
