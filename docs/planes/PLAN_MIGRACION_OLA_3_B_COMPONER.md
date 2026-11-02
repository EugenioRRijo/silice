# Ola 3 (S2-B) — «Componer una partida»: plan detallado

> Encargo: orquestador de la sesión de front (tesis-39), 2026-10-18. Rama `inc/ruta-s2-mig-b-componer`
> (worktree `.worktrees/s2mb-componer`), desde `inc/ruta-s2-mig` más la base del backend (ola 0a,
> `inc/ruta-s2-mig-backend-base`). Pendiente de la ola 3 en este documento: solo **Componer**; «Índices del BCV»
> y «Precios de la empresa» van en planes aparte cuando esta página cierre.
> Página Streamlit que se reproduce: `ui/paginas/componer.py` (UC-10 componer, UC-11 editar; RF-27, RF-33).

## 1. Rulings (ratificables)

| # | Ruling | Por qué | Costo si es erróneo |
|---|---|---|---|
| RB-1 | **La cola de la página Streamlit no se migra aquí:** «Cantidades de obra» y «Elaborar y auditar» (`_cantidades_de_obra`, `_elaborar_presupuesto`, `_mostrar_resultado_presupuesto`). La página nueva termina en «Guardar» y enlaza a «Elaborar un presupuesto» (S2-A), que hace lo mismo (`elaborar_desde_catalogo` + Excel) con su propio plan. | Duplicar la elaboración chocaría con `ui/elaboracion.py`/`ui/resultado.py` de S2-A y con su contrato de `presupuestos.py`. | Bajo: falta paridad del último tramo mientras Elaborar no esté migrada; la página clásica sigue disponible. |
| RB-2 | **El desglose en vivo lo calcula la API** (`POST /v1/composicion/evaluar`, sin escribir): el navegador envía las tablas como texto y recibe montos como texto; no calcula nada (plan 2b §3). Se pide con retardo de 300 ms tras la última edición y se descarta la respuesta de una petición vieja. | Una sola fuente de la aritmética (`core.costing`); paridad exacta con Streamlit. | Bajo. |
| RB-3 | **`guardar_composicion` y `Guardado` pasan a `aplicacion/composicion.py`** (junto con todo `ui/composicion.py`); `ui/elaboracion.py` los reexporta con `from aplicacion.composicion import Guardado, guardar_composicion` y borra sus definiciones. El resto de `ui/elaboracion.py` (planes, libro de Excel, pendientes) **no se toca**: es de S2-A. | La ruta de guardado de la API no puede importar `ui/`; mover solo esas dos piezas evita pisar a S2-A. | Medio: si S2-A mueve todo `elaboracion.py`, el merge tiene un conflicto pequeño en el encabezado que resuelve el orquestador. |
| RB-4 | **`sugerir_partidas_similares` se mueve con `ui/composicion.py`** a `aplicacion/composicion.py`; «Similares» (S2-orq) la importa de ahí al migrarse (la reexportación en `ui/composicion.py` mantiene viva la página clásica). | Quien la use de ambos lados, un solo lugar (NORMAS §2.1). | Bajo. |
| RB-5 | **Las ayudas 1, 2 y 4 (similares, precio atípico, contraste AACE) y la advertencia de rendimiento (RF-27 + bosque de aislamiento)** viajan como `advertencias` de texto en la respuesta de `evaluar`; la lista de similares es una ruta aparte (se pide al teclear la descripción). Ninguna bloquea el guardado. | Paridad con Streamlit; la UI las pinta como avisos. | Bajo. |

## 2. Contrato de la API (todo texto decimal: `"14.50"`; nunca números JSON)

Rutas nuevas en `api/rutas/composicion.py`, todas con `dependencies=EDITAR` (`Accion.EDITAR_HOJA`, como la página
clásica). Esquemas junto a la ruta (`api/rutas/composicion.py`), no en `api/esquemas.py`. Caso: el de la sesión
(`SesionDep`).

**Tipos**

- `FilaMaterial` `{descripcion, unidad, cantidad, precio}`; `FilaEquipo` `{descripcion, cantidad, precio, depreciacion}`;
  `FilaManoObra` `{descripcion, cantidad, sueldo, modalidad}` con `modalidad` `""` | `"JORNAL"` | `"DESTAJO"`
  (las tres: todos los campos son `str`, vacíos permitidos mientras se teclea).
- `Tablas` `{materiales: FilaMaterial[], equipos: FilaEquipo[], mano_obra: FilaManoObra[]}`.
- `Cabecera` `{codigo, descripcion, unidad, dominio: "civil"|"telecom"|"industrial"|"sistemas", rendimiento}`.
- `Desglose` `{materiales, equipos, mano_obra, costo_directo, con_administracion, precio_unitario}` (texto con
  `DECIMALES_PRESENTACION` decimales, como `_presentar`).
- `Advertencia` `{tipo: "rendimiento" | "rendimiento_ml" | "precio_atipico" | "contraste_aace" | "partida_nueva",
  texto: str}`.

**Rutas**

1. `GET /v1/composicion/opciones` → `{dominios: ["civil", ...], modalidades: ["JORNAL", "DESTAJO"]}`.
2. `POST /v1/composicion/evaluar` — cuerpo `Cabecera & Tablas` → 200
   `{estado: "vacio" | "incompleto" | "valido", aviso: str | null, desglose: Desglose | null,
   advertencias: Advertencia[], requiere_justificacion: bool, contraste: {tecnica, registros, pu_estimado,
   dentro_de_rango: bool} | null}`.
   - `vacio`: `formulario_vacio(...)`; `aviso` = «Comience por la cabecera…» (el texto de la página clásica).
   - `incompleto`: `ComposicionInvalida`; `aviso = str(error)`; nunca 4xx (una tabla a medias es lo normal).
   - `valido`: `desglose` y las advertencias de las ayudas 2 y 4; `rendimiento`/`rendimiento_ml` se calculan aunque la
     composición esté incompleta mientras `rendimiento` sea un decimal válido y haya `codigo` (igual que
     `_advertir_si_corresponde`). `requiere_justificacion` = hay advertencia de tipo `rendimiento`.
3. `GET /v1/composicion/partidas/{codigo}` → `{existe: bool, tablas: Tablas, rendimiento_propuesto: str | null,
   hay_historial: bool}`. Sin partida o sin lista vigente: `existe=false` y tablas vacías (UC-10), 200.
4. `GET /v1/composicion/referencia?tipo=material|equipo|mano_obra&q=` → `[{etiqueta, ref_maprex, fila}]` donde `fila`
   es la fila ya completada (`fila_*_desde_referencia`); 422 si `tipo` no es uno de los tres; `q` vacío → `[]`.
5. `GET /v1/composicion/similares?dominio=&descripcion=` → `[{codigo, descripcion, puntaje, rendimiento: str | null,
   unidad: str | null, tablas: Tablas | null, aviso: str | null}]` (`aviso` = «Desglose incompleto en la lista
   vigente: …» cuando `CatalogoIncompleto`).
6. `POST /v1/composicion/guardar` — cuerpo `Cabecera & Tablas & {fecha: "AAAA-MM-DD", condiciones: str,
   justificacion: str | null}` → 200 `{precio_unitario, mensaje, justificada: bool, avisos: str[]}`;
   `422 {detail}` si las condiciones están vacías (RF-33), la composición es inválida o `motivo_para_no_reemplazar`
   da motivo (nada se escribe); `409` si no hay lista de precios vigente (`CatalogoIncompleto`). Confirma
   (`commit`) solo con resultado. `justificada=true` solo si hubo advertencia de rendimiento, el guardado registró un
   rendimiento nuevo y hay texto de justificación (UC-06 flujo 4a); si no, `avisos` trae los mismos mensajes que la
   página clásica.

## 3. Backend (tareas)

B1. Mover `ui/composicion.py` → `aplicacion/composicion.py` (sin `streamlit`; hoy ya es puro) más
`guardar_composicion`/`Guardado` (RB-3). `ui/composicion.py` queda con una reexportación explícita de todo lo que la
página clásica y los tests importan. Tests existentes de `ui/composicion` y `ui/elaboracion` siguen verdes sin tocarlos.
B2. `api/rutas/composicion.py` con las seis rutas y la lógica de armado de respuestas en
`aplicacion/composicion.py` (funciones puras o sobre `Session`: `evaluar_composicion`, `precarga_de_partida`,
`similares_con_composicion`, `guardar_y_justificar`), de modo que Streamlit también pueda usarlas después. `api/main.py`:
solo agregar `app.include_router(composicion.router)`.
B3. `tests/unit/test_api_composicion.py` (TestClient, caso temporal, clave de API y sesión con rol) y
`tests/unit/test_aplicacion_composicion.py`; `tests/unit/test_api_acceso_por_ruta.py`: **agregar** las seis filas
(EDITAR_HOJA; sin sesión 401; rol sin permiso 403); `tests/unit/test_arquitectura.py` ya cubre `aplicacion/`.
B4. `docs/api.json` regenerado con `uv run python scripts/exportar_openapi.py`; `CHANGELOG.md` una línea.

## 4. Frontend (tareas)

F1. `frontend-desktop/src/paginas/componer/`: `index.tsx` (default export), `cliente.ts` (llamadas con `pedir`),
`tablas.ts` (estado de las tres tablas, filas vacías, agregar/borrar fila), `PanelDesglose.tsx`, `TablaInsumos.tsx`
(Carbon `DataTable` densa `sm`, celdas editables de texto; mano de obra con selector de modalidad),
`BuscadorReferencia.tsx` (texto → resultados → «Usar esta fila», con `ref_maprex` visible), `Similares.tsx` (lista
plegable de solo lectura), `Guardar.tsx` (condiciones obligatorias, justificación solo si
`requiere_justificacion`, botón deshabilitado sin condiciones) y `index.test.tsx` + pruebas de cada pieza con un doble
de `fetch` (como `src/shell/Shell.test.tsx`).
F2. Una línea en `src/shell/rutas.ts` (`cargar: () => import("../paginas/componer")`). `package.json` no se toca.
F3. Etiquetas de la página clásica sin cambiar: «Rendimiento — unidades por día», «Consumo por unidad» (columna
`cantidad` de materiales), «Condiciones del rendimiento». Al terminar de guardar, un enlace a «Elaborar un presupuesto».
F4. `npm test`, `npm run lint`, `npm run build`, `npm run dist`; captura a 1366×768 **solo con datos ficticios**.

## 5. Pruebas con valores (oráculo a mano)

Composición ficticia de la memoria: material 2 u × 10 = 20; equipo 0,5 × 30 ÷ rendimiento…: usar los valores de
`tests/fixtures/` y de `tests/unit/test_composicion.py` ya existentes como oráculo; **no** escribir cifras ni nombres
de ningún libro real (regla de Eugenio, 2026-10-18).
