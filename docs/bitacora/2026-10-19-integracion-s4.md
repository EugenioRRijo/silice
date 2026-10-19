# Integración de la sesión 4 (arenera, existencias e historial de auditorías) en la migración

**Fecha:** 2026-10-19 · **Tarea:** T1 de `docs/planes/PLAN_MIGRACION_FINAL_STREAMLIT.md` · **Rama:** `inc/ruta-s2-mig-adm-empresa`

Se fusiona `inc/ruta-s4-existencias-react` (contiene `inc/ruta-s4-arenera`) con un solo commit de fusión. `core/` no se
toca. Los conflictos se resolvieron conservando lo de ambos lados.

## Rulings

1. **Numeración de la ERS.** El historial de auditorías de la sesión 4 ya escribió y probó RF‑142 a RF‑146 (y UC‑30,
   RNF‑28) en la ERS y en 3 archivos de pruebas. La migración había reservado RF‑142 a RF‑150 pero no escribió ninguno.
   Decisión: **el historial conserva RF‑142 a RF‑146**; la migración pasa a **RF‑147 a RF‑155** (S2‑A RF‑147–149,
   S2‑B RF‑150–152, S2‑C RF‑153–155). Se actualizaron `RUTA_SESIONES.md`, `PLAN_SESION_2B_MIGRACION.md`,
   `REPARTO_SESIONES_MIGRACION.md` y la nota de numeración de la ERS. Nunca se reutiliza un número.
2. **`TablaDensa.celda`.** Las dos ramas añadieron una propiedad `celda` con tipos distintos (nombre `"severidad"` o
   `"variacion"` frente a una función `(fila) => ReactNode`). Ahora acepta ambas; la función gana si la columna la trae.
3. **Visor 3D.** Sigue retirado. Los conteos se recalcularon a mano desde `PAGINAS`: 21 pantallas (las 20 de esta rama
   más Existencias de la arenera); 18 en modo entrega (se esconden Escenarios, Partidas similares y el Simulador).
4. **Sección 8.0f de `plan_pruebas.md`.** Ambas ramas crearon una con ese número; la del historial pasa a **8.0g**
   (y `PLAN_SESION_4_HISTORIAL.md` la cita así).
5. `tests/unit/test_ui_importable.py` esperaba 21 páginas con 20 en esta rama (ya fallaba antes de la fusión); queda en
   21, que es ahora el número real.

## Conflictos y resolución

| Archivo | Resolución |
|---|---|
| `api/dependencias.py` | Se conservan `_motores`/`_cerrojo` (esta rama) y el import de `operacion.instalacion`, `USUARIO_API` (S4); se descarta `_motor = None`, que ya no se usa. |
| `api/main.py` | Se agregan `auditorias_libro` y `produccion` a los imports y sus `include_router` junto a los de la migración. |
| `docs/ERS.md` | Se unen las tres filas de trazabilidad (UC‑26, UC‑28, UC‑29, UC‑30); en UC‑26 se mantienen los flujos de la migración y la postcondición dice que la auditoría deja su resumen en el historial. |
| `docs/plan_pruebas.md` | Se conservan ambas secciones (8.0f y 8.0g) y ambas filas de RNF (22/23 y 25/28). |
| `docs/api.json` | Regenerado con `scripts/exportar_openapi.py`, no fusionado a mano. |
| `frontend-desktop/src/comun/TablaDensa.tsx` | Ver ruling 2. |
| `frontend-desktop/src/estilos/app.scss` | Se usan los estilos de `inicio` y de `existencias`. |
| `frontend-desktop/src/shell/rutas.ts` y `rutas.test.ts` | Registro con carga perezosa de la migración y `existencias` (sección Trabajo, acción `operar_arenera`) después de `entregar`; conteos 21, 21 y 18. |
| `instalador/manifiesto.py`, `manifiesto.toml`, `tests/unit/test_manifiesto.py`, `tests/unit/test_arquitectura.py` | Los paquetes `aplicacion` y `produccion` en ambas listas. |
| `tests/unit/test_ui_app.py` | Conteo de pantallas 21 (ruling 3). |
| `tests/unit/test_front_rutas_api.py` | Sin cambios de conflicto; se vació `PENDIENTES_V4` porque las rutas ya existen. |

## Alembic

Destino `instalacion`: `ins_0001_seguridad` → `ins_0002_produccion` → `ins_0003_auditoria_libro`; destino `caso` sin
cambios. Una sola cabeza por destino (la comprueban `tests/integration/test_migraciones*.py`).

## No se corrió

La suite completa y los `test_ui_*` de AppTest (agotan su espera de 3 s en este equipo, también sin cambios).
