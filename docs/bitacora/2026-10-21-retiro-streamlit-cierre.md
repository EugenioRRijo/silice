# Retiro de Streamlit y del Visor 3D: cierre de la fase F10 (documentos)

**Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-retiro-streamlit` · **Plan:** `docs/planes/PLAN_RETIRO_STREAMLIT.md` (§1.5, §4 F10, §7) · **Autor:** implementador F10 (documentos).

## 1. Qué se retiró

- **Streamlit y toda la capa `ui/`** (F4, F5, F8): páginas, marco, sesión, utilidades, `.streamlit/config.toml`, la prueba descartable de `st.data_editor` y los 45 archivos de pruebas con `AppTest`. La lógica que vivía en `ui/` está en `aplicacion/`.
- **El extra `ui`** (F9): `streamlit` y `altair` salen de `pyproject.toml`; `python-multipart` pasa al extra `api`; `uv.lock` regenerado.
- **El segundo proceso** (F2): el producto arranca un solo Uvicorn (`api.main:app`) que sirve la API y la interfaz de React en `/app/` por el puerto de `[servidor]` (8501 por omisión). La tabla `[api]` de `silice.toml` se ignora con un aviso.
- **El Visor 3D** (RNF-08): retiro definitivo (ya estaba retirado el 2026-10-19, pendiente de ratificar).
- **Superficie de la interfaz clásica** (carril de código de F10, commits `203cfae3` y `02c997b9`): `url_clasica` en la sesión, `api_activa` y `puerto_api` en la instalación, `PaginaSinMigrar`, `VITE_URL_CLASICA`. Este informe de documentos no tocó ese código; solo lo cita.

## 2. Decisiones de Eugenio (2026-10-21)

1. Un solo proceso y un solo puerto sirviendo API y front.
2. **El asistente de IA de la Hoja queda sin interfaz.** Era un panel de la página de Streamlit de la Hoja; React no lo tiene. `asistente/servicio.py` conserva su lógica y sus pruebas, pero **no tiene llamador de producción**. **DEUDA pendiente de Eugenio** (decidir si se construye en React o se da de baja el servicio).
3. Retiro definitivo de Streamlit y del Visor 3D; el tutor lo avala (palabra de Eugenio, sin acta). **PENDIENTE: avisar al tutor por escrito.**
4. Sin subir versión ni etiquetar.
5. **Sin homólogo comprobado en React** (decisión de producto, `docs/bitacora/2026-10-21-retiro-f3-triaje.md` §7b): (a) los **recorridos guiados** de Streamlit (demostración, presupuesto, precios, paquete; en React solo existe «Auditar un libro de la empresa»); (b) **22 funciones de `ui.libros`** (hallazgos resaltados en la vista calcada del libro, filtros y orden de la tabla de hallazgos, totales, marcas por hoja, tope de celdas combinadas). Su cobertura de prueba se retiró con el módulo. Queda pendiente aceptar la pérdida o abrir tarea. Además, el triaje (§7, punto 2) señala que la **visibilidad del menú por rol** (`ui.app.paginas_visibles`, 15 funciones) no se comprobó en `frontend-desktop/` ni en `api/`.
6. **Dos asuntos que el encargo dejaba «pendientes de permiso»** (`url_clasica`, `api_activa`, `PaginaSinMigrar`): ya están retirados en commits del carril de código de F10 (arriba). Se anota para que el orquestador confirme que el permiso existía.

## 3. Qué documentos se actualizaron (vivos)

| Documento | Cambio |
|---|---|
| `README.md` | extras sin `ui`; el comando de Streamlit y la frase de `.streamlit/config.toml` fuera; mapa del repositorio con `aplicacion/` y `frontend-desktop/`; un solo proceso y puerto |
| `NORMAS.md` | principio 2 (`aplicacion/` en lugar de `ui/`); §6 sin `.streamlit/config.toml`, con `aplicacion/`, `frontend-desktop/` y `operacion/`; línea de `tests/fixtures` (la leen `scripts/` y `start.py`) |
| `docs/ERS.md` | **enmienda fechada 2026-10-21** al final (RT-4, RF-81, RNF-08, RNF-11, RNF-15) y retoques en línea: §2.1, §3.1, la nota de RT-4 en la enmienda 1.2.0, RF-81, RF-97 (h), RF-98, UC-12, RNF-08, RNF-11, RNF-15. **Sin requisitos nuevos ni cifras cambiadas** |
| `docs/arquitectura.md`, `docs/manual_tecnico.md`, `docs/manual_usuario.md` | enmienda con fecha al inicio; `ui.X` a `aplicacion.X` donde el módulo existe; comandos de arranque y extras; diagramas de despliegue y de componentes; secciones de la interfaz de Streamlit marcadas como registro |
| `docs/plan_pruebas.md` | enmienda; alcance y niveles; las citas de pruebas retiradas marcadas «(retirada)» y su estado ya no es «verde»; 18 citas reubicadas a su nuevo archivo; 4 citas de pruebas renombradas actualizadas. Cifras de §10 intactas (son de la corrida de CI citada) |
| `docs/guion_prueba_arenia.md`, `docs/protocolo_indicador3.md`, `docs/metodologia.md` | comandos de arranque (`uvicorn`), `--extra ui` fuera; el guion lleva aviso de que los pasos de pantalla deben revalidarse sobre React |
| `docs/protocolo_asistente.md` (l. 110) | solo la ruta del auditor: `aplicacion/hoja.py` (no se tocó nada del congelado) |
| `scripts/README.md` | fuera `prueba_data_editor.py` y `medir_data_editor.md`; `medir_rnf11.py` dice `aplicacion.hoja` |
| `tests/unit/test_manuales_s5.py` | la guardia del README exigía `--server.address 127.0.0.1` (flag de Streamlit); ahora `--host 127.0.0.1` |
| `CHANGELOG.md` | sección «Retirado» bajo «Sin publicar»: una entrada por fase, F1 a F10 |

## 4. Qué se dejó sin tocar y por qué

- **`docs/bitacora/**`, `docs/auditoria/**`, `docs/especificaciones/**`, `docs/planes/**` anteriores, `docs/tesis/**` y los `PLAN_*.md` de la raíz:** registro de cómo se hizo (el plan lo declara así). Incluye esta carpeta de planes (`PLAN_RETIRO_STREAMLIT.md` y su manual).
- **`docs/fuentes/bcv_formatos.md`** (cita `ui/paginas/hoja.py` línea 1236): nota de fuente fechada, histórica.
- **Cuerpo de las secciones de la interfaz de Streamlit en `arquitectura.md`, `manual_tecnico.md` (§10.3 y §11), `plan_pruebas.md` (filas retiradas) y el guion:** describen cómo se construyó y probó la interfaz anterior; se reescribirían a mano con la interfaz final. Cada documento lleva su enmienda de lectura. No es una verdad vigente, pero tampoco es historia del todo: **queda un repaso de contenido pendiente** (sobre todo `manual_usuario.md`, que nombra pantallas y botones de Streamlit, y el guion, que hay que revalidar con una persona).
- **`docs/api.json`, `uv.lock`, `pyproject.toml`:** los tocan el orquestador y los carriles de código. En el árbol había una modificación de `docs/api.json` sin commitear que no es mía; no la toqué.
- **`frontend-desktop/{README,DESIGN,PRODUCT}.md`:** prohibido en este encargo (los tocó el carril de front, `02c997b9`).
- **`instalador/humo.ps1`:** su 8501 y el chequeo de que no viaja `ui` ni `.streamlit` son correctos (ya describen el producto sin Streamlit); no es texto de documentación. **`instalador/manifiesto.py:198`:** el docstring ya dice «ya no hay `.streamlit/config.toml`». `.github/workflows/`: sin menciones de `ui` (`--all-extras`, sin `--extra ui`).
- **Docstrings de `aplicacion/*.py`** (p. ej. `acerca.py`, `actualizacion.py`, `composicion.py`, `atipicos.py`, `estilo.py`) que aún dicen «sin Streamlit» o citan `ui/paginas/...`: código, prohibido en esta fase. Son inocuos pero quedan como deuda cosmética.
- **`docs/metodologia.md` l. 45** («Streamlit mínimo» en la tabla de valor percibido del plan de 2026): plan histórico de entregas.
- **RF-36/37/42/60/82/100 y UC-12 del ERS:** el texto de los requisitos (con «Streamlit», «AppTest», «pantalla») no se reescribió; la enmienda de la ERS dice cómo leerlos. Cambiar su redacción sería inventar el requisito para React, que es decisión del tutor.

## 5. Verificación

- `pytest -W error -p no:cacheprovider -o addopts=""` sobre las guardias de documentos: `test_nombre_silice`, `test_documentos_s5_1`, `test_documentos_historial_auditorias`, `test_trazabilidad_s5`, `test_manuales_s5`, `test_publicar`, `test_guion_prueba_arenia`, `test_guion_sf`, `test_reinicio_seguro` y `tests/integration/test_guion_cp10_cp11.py`: verdes. Antes de corregir, `test_documentos_s5_1` y `test_trazabilidad_s5` (citas de pruebas que ya no existían) y `test_manuales_s5` (el README) estaban rojas por las fases anteriores.
- `python scripts/meta_datos.py`: 4/4 OK (D1 a D4); las afirmaciones «reales» de datos no se tocaron.
- Barrido (`rg`) de «streamlit run», `--extra ui`, `ui/app.py`, `.streamlit` y «clásica» en documentos vivos: ya no queda ninguno fuera de las enmiendas, de las filas marcadas «(retirada)» y del registro descrito en §4.

## 6. Riesgos y cómo verificar

1. **Producto sin asistente en la Hoja.** Verificar con Eugenio si se construye (decisión 2).
2. **Cobertura sin homólogo en React** (decisión 5): recorridos, `ui.libros`, menú por rol. Pedir una prueba equivalente en `frontend-desktop/` o aceptar la pérdida por escrito.
3. **Plan de pruebas con filas «retiradas»:** el cumplimiento de RF-36 a RF-42, RF-60 y otros que dependían de AppTest ya no se demuestra automáticamente; revisar con el tutor qué sustituye el criterio.
4. **Aviso al tutor** pendiente (por escrito) del retiro del Visor 3D y de Streamlit; la ERS lo declara con «palabra de Eugenio, sin acta».
5. **F11 pendiente:** `protocolo.json` y `congelado.json` (rutas definitivas del auditor); la guardia del congelado sigue roja hasta entonces y **no se debe fusionar antes de F11**. `docs/protocolo_asistente.md` ya cita `aplicacion/hoja.py`.
6. Para verificar: `uv run start.py` abre `http://127.0.0.1:8501/app/` con un solo proceso; `python scripts/meta_datos.py`; las guardias de documentos de §5.
