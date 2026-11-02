# Asistente de IA en la Hoja del proyecto (React): diseño de la etapa 1

**Fecha:** 2026-10-21 (ronda 2) · **Rama:** `inc/ruta-s2-mig-adm-empresa` (base `05861c43`; el estado de partida de la construcción es el
de **después del retiro de Streamlit**, §0.1) · **Estado:** PROPUESTO, corregido tras el veredicto DEVUELTO de la ronda 1 (8 MAYOR y
6 MENOR; la tabla de §14 dice qué cambió por hallazgo). Lo juzga el árbitro (`docs/planes/MANUAL_ARBITRO.md`, criterios B2, B3, B4,
C1, C2, D1 y D2 aplicados al diseño). Sin su aprobación no hay código. Las decisiones que no son de ingeniería están en §11 (D-1 a
D-8), cada una con su recomendación.

**Origen del encargo.** Eugenio decidió el 2026-10-21 (opción B) construir el panel por etapas. **Etapa 1** (este documento,
con todo el detalle): elegir proveedor, escribir el pedido, ver las propuestas, aceptar o rechazar cada una y ver el
resultado hipotético (total y cambios si se aceptan). **Etapa 2** (solo extensión prevista, §9): responder las preguntas de la IA
y cierre de la sesión al guardar la versión. **Etapa 3** (solo extensión prevista, §9): historial y costos.

**Alcance de este documento:** solo diseño. No se escribió código de producción ni se tocó ninguna prueba.

**Este documento reemplaza al §2.10 del diseño de la Hoja** (`2026-10-19-hoja-react-design.md`) en tres puntos: (a) la ruta futura
`api/rutas/asistente_hoja.py` se llama aquí `api/rutas/hoja_asistente.py`; (b) «nada del asistente entra en `aplicacion/hoja*.py`» se
precisa así: **ningún archivo existente** de `aplicacion/hoja*.py` importa el asistente; solo los tres módulos nuevos
`aplicacion/hoja_asistente*.py` (más el gancho `al_guardar` de `hoja_guardado.py`, que no importa nada del asistente); (c)
`useBorradorHoja()` no existe y no se crea: el panel recibe las mismas props que las pestañas.

**Qué leí (enteros salvo donde se dice):** `docs/especificaciones/2026-10-19-hoja-react-design.md` (§0 a §12), los dos manuales,
`ui/paginas/hoja.py` líneas 1 a 300 y 640 a 1160, `asistente/servicio.py`, `propuestas.py`, `privacidad.py`, `tarifas.py`,
`instalacion.py`, `catalogo.py`, `fabrica.py`, `configuracion.py` enteros; `orquestador.py` 1 a 130 y 286 a 498; `registro.py`;
`proveedores/base.py`, `guionado.py` (cabecera), `claude.py` 138 a 200; `api/rutas/admin_asistente.py`, `api/rutas/hoja.py`,
`api/rutas/hoja_plano.py` (cabeceras y rutas), `api/dependencias.py`; `aplicacion/hoja_borradores.py` entero, `hoja_edicion.py` 1 a 165,
`hoja_plano.py` 478 a 492, `hoja_guardado.py` cabecera, `hoja_vista.py` firmas, `aplicacion/hoja.py` 330 a 350 y 1764 a 1787;
`frontend-desktop/src/paginas/hoja/index.tsx` y `useBorrador.ts` enteros y los mocks de `Hoja.test.tsx`; el S4
(`2026-10-11-silice-s4-asistente-ia-design.md` §3 y §8); las guardias de arquitectura; y, **en la ronda 2**, la rama
`inc/ruta-s2-mig-retiro-streamlit` (F7 `f2b3c5e5`, F8 `1e1f976e`: `asistente/*`, `tests/unit/test_arquitectura_asistente.py`,
`tests/fixtures/asistente_pedidos.py`, `hoja_edicion.py`, `hoja_plano.py`). **No corrí ninguna prueba ni la aplicación**: lo que afirmo
sale de la lectura y cada afirmación dudosa lo dice (§13). Los números de medición del SDK (`anthropic` 1.17: `DEFAULT_TIMEOUT`
connect 5 s, read/write/pool 600 s, 2 reintentos) los midió el coordinador; no los repetí.

**Convención de referencias:** `P:línea` = `ui/paginas/hoja.py` (que el retiro borra: se cita como **fuente de la regla**, no como
código vivo); `S:línea` = `asistente/servicio.py`. Los números de línea son del commit `05861c43` (las líneas de `asistente/*` que
mencionan `ui.hoja` cambian en F7, solo en los `import`).

---

## 0. Resumen en doce líneas

1. El motor del asistente (`asistente/*`) **se reutiliza tal cual, sin un solo byte nuevo**; falta una capa delgada en `aplicacion/`
   (`hoja_asistente*.py`) y una ruta nueva (`api/rutas/hoja_asistente.py`). La página clásica no se modifica ni se importa.
2. **Orden de fusión (ruling del orquestador, §0.1): primero el retiro de Streamlit, después 4a.** F7 ya repuntó `asistente/*` a
   `aplicacion.hoja`; el motor y la hoja nueva comparten la clase `Borrador`. **No hay conversión de borradores**; el «puente» queda
   como fachada del motor con tres oficios reales: único punto de contacto con el asistente, copia saneada para la regla P7 de
   MaPreX y cliente acotado en plazo.
3. **La llamada al proveedor es larga y bloqueante** (hasta 12 turnos; sin `timeout` propio: el SDK pone 600 s y 2 reintentos). Proponer
   es un **trabajo en segundo plano con hilos demonio propios**, un semáforo de cupo, plazo por turno y total, cancelación, una petición
   por borrador, ritmo por cuenta (`usuario_id`) y un gancho de apagado que no espera.
4. **La sesión del asistente vive atada al borrador vivo y nunca dentro de él**; muere con él por cualquier camino
   (`hoja_borradores.al_quitar`). Lo aceptado y la fuente sugerida sobreviven a descartar la sesión.
5. **Aplicar lo aceptado es una operación atómica propia** (las partidas van a `items_base`), en dos fases, sobre el mismo núcleo de
   edición (`rev`, `completar_composiciones`, `reemplazar`). Reproduce la regla de la clásica «reconstruir o aplicar sobre la hoja
   editada» (`aplicado` pasa a `None` y se queda así) y cubre `sin_partida`, que no cambia el borrador pero sí se decide y se registra.
6. **La IA nunca es autora.** Decide la cuenta de la sesión; el cuerpo no trae ningún campo de persona.
7. **Privacidad:** viaja la lista blanca de `asistente/privacidad.py` **más** una copia saneada que cumple P7 (las partidas MaPreX de
   `items_base` van solo con código y unidad a proveedores en la nube); la clave de IA nunca llega al navegador; el pedido con una
   clave conocida se rechaza antes de enviarse. Límites declarados: `contiene_secreto` es heurístico y los nombres libres no tienen
   filtro de nombres de empresa.
8. **Gasto:** estimación orientativa previa (1,2144 USD con Opus 5.5), tope por sesión, 12 turnos y 60 llamadas, plazo, cancelación,
   ritmo, cupo. Ninguna prueba ni agente llama a un proveedor real (D-2).
9. **Interfaz:** `<aside>` con encabezado `h2 > button` (desplegable propio, HTML válido) entre el estado del borrador y las pestañas;
   sin anchos fijos; lista y no tabla; montos `{texto, exacto}`; texto de la IA escapado; un fallo del panel nunca pinta un `alert`.
10. **El resultado hipotético es el de aceptar de verdad:** completa composiciones (solo lectura) antes de elaborar, así que una
    partida propuesta no se subestima como «pendiente».
11. **Preguntas de la IA:** el prompt manda preguntar, así que ocurrirá. En la etapa 1 el panel ofrece «Seguir sin responder», que
    cierra la sesión (`ia_sesiones`), registra lo propuesto y deja decidir; responder de verdad es la etapa 2.
12. Siete sub-rebanadas (4a-1 a 4a-7; 4a-7 bloqueada por D-2). Ganchos de las etapas 2 y 3 listos en la 1.

### 0.1 Orden de fusión y estado de partida

La rama `inc/ruta-s2-mig-retiro-streamlit` (worktree `s2m4`, otra sesión) ya tiene **F7** (`f2b3c5e5`: `asistente/*`, fixtures y pruebas
pasan de `ui.hoja` a `aplicacion.hoja`; «solo líneas de import en `asistente/**` (equivalencia por AST contra `cd46732`: EQUIVALENTE en
los 7 archivos); el banco calculado coincide con `congelado.json`») y **F8** (`1e1f976e`: se borra `ui/` y se reescriben las guardias de
arquitectura). Ruling del orquestador: **el orden de fusión es primero el retiro (que fusiona este árbol) y después 4a sobre ese estado.**
Consecuencias, todas ya reflejadas abajo:

- `ui/` no existe: no hay `ui.hoja`, ni conversión de clases, ni importación perezosa por culpa de `ui`, ni regla «la API no carga `ui`».
- `asistente/*` importa de `aplicacion` solo `aplicacion.hoja` y `aplicacion.errores` (`DE_APLICACION_PERMITIDO` en la guardia reescrita).
- Las pruebas `test_ui_*` desaparecen: este diseño cita fixtures neutras (`tests/fixtures/asistente_pedidos.py`, `caso_of001.py`,
  `caso_ti001.py`, `hoja_borrador.py`, `hoja_en_base.py`, `sesion_web.py`) y pruebas `test_api_*` / `test_aplicacion_*`.
- **4a-1 no empieza hasta que la rama de trabajo contenga `f2b3c5e5` y `1e1f976e`** (comprobable con `git merge-base --is-ancestor`).
  4a-3 (solo front) puede empezar antes.

---

## 1. Hallazgos que cambian el plan (verificados por lectura)

### 1.1 Qué cambió con el retiro (y qué queda del hallazgo de la ronda 1)

Antes de F7, `asistente/orquestador.py`, `propuestas.py`, `privacidad.py`, `validacion.py` y `servicio.py` operaban sobre `ui.hoja.Borrador`,
clase distinta de `aplicacion.hoja.Borrador`, y cuatro estaban en el congelado (RS-9). **F7 lo resolvió** repuntando los `import`
(`orquestador.py:24` y `servicio.py:18-19` en la rama del retiro importan `aplicacion.hoja`). Ya no hace falta convertir. Lo que
sigue siendo cierto y condiciona la capa nueva:

- La guardia reescrita `tests/unit/test_arquitectura_asistente.py` (rama del retiro) fija `IMPORTAN_ASISTENTE_APLICACION = {"aplicacion/
  entrega.py"}` y comprueba **igualdad** con los importadores reales: los tres módulos nuevos exigen enmendarla (§12).
- `asistente/*` solo puede importar de `aplicacion` lo de `DE_APLICACION_PERMITIDO = {aplicacion, aplicacion.hoja, aplicacion.errores}`;
  la capa nueva vive en módulos distintos que **el asistente no importa**: no hay ciclo.
- `api/rutas/admin_asistente.py` ya importa partes del paquete `asistente` (`administracion`, `clave`, `configuracion`, `instalacion`):
  la API puede importar el asistente; lo que no puede es importar `scripts` ni `tests`.

### 1.2 Proponer es largo, bloqueante y sin gancho de cancelación

- `orquestador.py` corre hasta `Topes.turnos = 12` y `Topes.llamadas = 60`; cada turno es una llamada de red síncrona
  (`self.proveedor.turno(...)`, `orquestador.py:~399`). Ante un `ErrorDeProveedor` el orquestador termina con
  `MotivoFin.ERROR_DE_PROVEEDOR` y **solo conserva `str(error)`**: la categoría se pierde (`orquestador.py:401-402`), por eso la envoltura
  debe registrarla (§3.3).
- `claude.py:169` crea `anthropic.Anthropic(api_key=…, max_retries=2)` sin `timeout`; el SDK instalado (medido por el coordinador,
  `anthropic` 1.17) usa `DEFAULT_TIMEOUT` connect 5 s / read 600 s / write 600 s / pool 600 s: un turno colgado puede tardar
  3 × 600 s con los reintentos. **No hace falta editar `claude.py`**: `ProveedorClaude.__init__` acepta `cliente=` (`claude.py:141-153`) y
  `_crear_cliente()` devuelve `self._cliente` si existe; el cliente del SDK acepta `with_options(timeout=…, max_retries=0)` (§3.3).
- El bucle no ofrece progreso ni cancelación, solo `Topes`, `Servicios.responder` y `ErrorDeProveedor`.
- Un `ThreadPoolExecutor` usa hilos **no demonio** que Python espera al salir: un turno colgado bloquearía el apagado de la API. Y con
  `EN_VUELO = 2` y turnos abandonados de 600 s el asistente se quedaría sin cupo. Por eso §3.3 usa hilos demonio propios.

### 1.3 Los proveedores llevan la clave y algunos preguntan a la red

`proveedores_de_la_instalacion()` construye `ProveedorClaude(clave.vigente, …)`: el objeto **contiene la clave de IA**; `servicio.proponer`
lo suelta de la sesión (`_soltar_proveedor`, `S:67-70`). `ProveedorOllama.disponible()` comprueba la versión por HTTP (`ollama_local.py:149`,
`timeout=5`; deducción por lectura, no probada): listar proveedores puede tardar hasta 5 s si hay modelo local (en pausa por RS-8). La ruta de
proveedores **nunca serializa el objeto**: proyecta nombre, modelo, disponibilidad y motivo.

### 1.4 La ruta de administración no sirve a quien arma

`GET /v1/admin/asistente` exige `ADMINISTRAR_EMPRESA`. Quien arma (`EDITAR_HOJA`) necesita ver proveedores y costo sin ver la clave ni la
configuración: lectura propia en la ruta de la hoja (A0).

### 1.5 Ninguna ruta de edición toca `items_base`; y `sin_partida` no cambia el borrador

- Las propuestas `partida` entran a `Borrador.items_base` (`propuestas._item`); E1 a E7 no lo editan (§3.5).
- **`aplicar()` hace `continue` ante `SIN_PARTIDA`** (`propuestas.py:132-133`): aceptar una propuesta `sin_partida` devuelve un borrador **igual**.
  `hoja_edicion._cambiar` retorna *antes* del gancho cuando `nuevo == vivo.borrador` (`hoja_edicion.py:134-135`), así que la decisión no se
  registraría y la propuesta quedaría pendiente. §3.5 define el camino.

### 1.6 El pedido no se filtra de secretos hoy, y el filtro es heurístico

`orquestador.py:313` aplica `contiene_secreto` solo a las **respuestas**. El pedido viaja tal cual (`privacidad.primer_mensaje`), se guarda en
`ia_sesiones.pedido` y **entra al anexo `ia.json` del paquete firmado** (`registro.anexo_ia`). `contiene_secreto` busca solo `sk-ant-` y
`-----BEGIN` (`privacidad.py:MARCAS_DE_SECRETO`): **una clave de otro proveedor (`sk-…`, `AKIA…`, `ghp_…`) o una contraseña no se detecta**.

### 1.7 El anexo `ia.json` solo incluye sesiones marcadas como guardadas

`registro.anexo_ia` filtra `version_guardada IS NOT NULL` y exige alguna propuesta aceptada o editada. Sin `marcar_guardada`, la versión
guardada tendría filas con origen `ia` sin la sesión que las explica: D-3 propone cerrarlo ya, solo en servidor.

### 1.8 La lista blanca **no** respeta P7 con descripciones de `items_base`

`privacidad.resumen_del_borrador` (`privacidad.py:136-148`) envía `limpiar(i.descripcion)` de **todos** los `items_base`, sin distinguir
MaPreX ni nube; la regla P7 («las partidas de MaPreX viajan en nube solo con código y unidad», ratificada por Eugenio el 2026-10-11) solo se
aplica a las partidas del catálogo que devuelven las herramientas (`describir_partida`, `privacidad.py:152-157`). Además
`ConfiguracionIA.prefijos_de_maprex` vale `()` por defecto (`configuracion.py:29`): si el administrador no lo llena, **ninguna** partida se
considera MaPreX. La versión de la ronda 1 de este documento afirmaba lo contrario; queda corregida en §4.1 y §4.2.

### 1.9 Otros hallazgos

| # | Hallazgo | Consecuencia |
|---|---|---|
| 1 | `useBorradorHoja()` no existe; `index.tsx` pasa `id`, `rev` y `aplicar(resumen)` por props | el panel recibe esas props (`alAplicar`) |
| 2 | `Hoja.test.tsx:256` afirma que el `<aside>` existe vacío y oculto; `Hoja.test.tsx:103` responde `500 «ruta inesperada»` a toda URL que no conoce; `Edicion.test.tsx:151`, `Edicion3c2.test.tsx:171`, `EdicionApu.test.tsx:206` y `Vistas.test.tsx:425` cuentan avisos/alertas únicos; `Hoja`, `Edicion`, `Guardar`, `Retomar`, `Vistas` responden 404 «FALTA» a `GET /v1/hoja/borradores/…` | el panel pide A3 al montarse: §6.3 y 4a-3 fijan que un fallo del panel **no pinta `alert`** y actualizan los mocks |
| 3 | `retirar_propuesta` (herramienta de la IA) marca la propuesta `RECHAZADA` (`orquestador.py:291-294`) sin distinguirla de un rechazo humano; al cerrar la sesión el registro la guarda como `rechazada` con `decidida_por` vacío | `Propuesta.retirada_por_la_ia` (§5.2) |
| 4 | Con `ESPERAR`, `_resultado(ESPERANDO_RESPUESTA)` **no escribe `ia_propuestas` ni cierra `ia_sesiones`** (`orquestador.py:333-345`); solo `continuar(…, None)` → `CANCELADO` lo hace | §3.4 y §6.6: «Seguir sin responder» |
| 5 | El costo de la sesión se calcula con la tarifa del modelo **pedido**; con `fallbacks="default"` (`con_respaldo=True`) otro modelo puede responder (`Turno.modelo_que_respondio`) | el costo mostrado es una estimación; se dice (§4.3) |
| 6 | `hoja_plano.fusionar` llama a `hoja_edicion._cambiar` (`hoja_plano.py:352` en la rama del retiro; `:486` en esta) | es el octavo consumidor; 4a-1 lo actualiza (§3.5) |
| 7 | No hay `lifespan` en `api/main.py` (`grep` sin resultados; `app = FastAPI(` en la línea 63) | texto en §12 |
| 8 | `Disponibilidad.motivo` y los mensajes de `ErrorDeProveedor` salen de código que «nunca incluye la clave», pero la garantía es de ese archivo | se pasan por `asistente.clave.enmascarar` y se cortan a 300 caracteres |

---

## 2. Alcance por etapas y qué se reutiliza

### 2.1 Etapas

| Etapa | Incluye | No incluye |
|---|---|---|
| **1 (este diseño)** | proveedores y estimación; vista previa; proponer (segundo plano, progreso, cancelar); lista de propuestas con supuestos y citas; aceptar / aceptar y editar / rechazar; resultado hipotético; descartar lo pendiente; «Seguir sin responder» ante una pregunta; retomar la sesión tras recargar; gancho de servidor de cierre al guardar (D-3) | responder preguntas de la IA; historial; costos acumulados |
| **2** | responder o cancelar una pregunta de la IA; mensaje de cierre al guardar | — |
| **3** | historial de sesiones; costos reales y acumulados; tope por instalación | — |

### 2.2 Qué se reutiliza y qué es nuevo

| Pieza | Tratamiento | Bytes nuevos en archivos existentes |
|---|---|---|
| `asistente/servicio.py`: `proponer`, `decidir`, `hipotetico`, `resumen_hipotetico`, `responder`, `descripcion`, `estimar_costo`, `fuente_del_cambio`, `SesionDeAsistente`, `DependenciaPendiente` | **tal cual**, vía el puente | 0 |
| `asistente/orquestador.py`, `propuestas.py`, `validacion.py`, `herramientas.py`, `privacidad.py`, `catalogo.py`, `tarifas.py`, `registro.py`, `instalacion.py`, `clave.py`, `proveedores/*` | **tal cual** | 0 |
| `aplicacion/hoja_borradores.py` (`obtener`, `reemplazar`, `descartar`, `al_quitar`, `BorradorVivo`, topes) | **tal cual** | 0 |
| `aplicacion/hoja_edicion.py`: el núcleo `_cambiar` | pasa a público (`cambiar`), gana `antes_de_reemplazar` (§3.5) y **se actualizan sus 8 consumidores**: las 7 ediciones de `hoja_edicion.py` y `hoja_plano.fusionar` | ~20 líneas (4a-1) |
| `aplicacion/hoja_plano.py` | una línea: `hoja_edicion._cambiar` → `hoja_edicion.cambiar` | 1 línea (4a-1) |
| `aplicacion/hoja_guardado.py`: `guardar` | gana la lista `al_guardar` (gancho posterior al `commit`) | ~20 líneas (4a-2) |
| `aplicacion/hoja_vista.py`: `elaborar`, `con_r17`, `resumen`, `_base_de_comparacion` | tal cual; 4a-2 hace pública la comparación (`base_de_comparacion`) sin cambiar su cuerpo | ~2 líneas (4a-2) |
| `api/`: `cuenta_con`, `_vivo`, `IdDeBorrador`, `RutaSinCache`, `RutaSinEco`, `Resumen`/`Monto`, `obtener_motor`, `url_de_la_peticion` | tal cual | 0 |
| `api/main.py` | `include_router` y `lifespan` (texto en §12; lo aplica el orquestador) | compartido |
| **Nuevo en `aplicacion/`** | `hoja_asistente_puente.py`, `hoja_asistente.py`, `hoja_asistente_trabajo.py` | — |
| **Nuevo en `api/`** | `rutas/hoja_asistente.py`, `esquemas_hoja_asistente.py` | — |
| **Nuevo en el front** | `src/paginas/hoja/asistente/` (§6.10) y `index.tsx` | — |
| **Nuevo en pruebas** | `tests/fixtures/asistente_guiones.py` (guion, guion con pregunta, proveedor con clave) | — |
| **No se toca** | `asistente/*`, `core/`, `adapters/` | 0 |

### 2.3 Lo que la clásica hacía y la capa nueva reescribe

`_proponer_con_asistente`, `_decidir_propuesta`, `_hoja_editada_a_mano`, `_resumen_hipotetico`, `_formulario_del_asistente`, `_panel_asistente`,
`_cerrar_asistente_al_guardar` y `_descartar_asistente` eran **pegamento de Streamlit** alrededor del motor. Se reescriben de intención contra
la sesión del servidor; la prueba de paridad (§7.3) compara su efecto con el motor llamado directamente. El código clásico se borra en F8:
sus reglas viven en este documento.

**Dónde se construye lo que el motor necesita** (`hoja_asistente.py`, dentro del trabajo, no en la petición): `Servicios.auditar` =
`lambda b: hoja_vista.elaborar(b).elaboracion.informe` (con R17); `CatalogoDeLaBase` = las partidas de `Catalogo(sesion).partidas()` como
`PartidaVista(codigo, descripcion, unidad, Dominio(dominio), de_maprex=codigo.startswith(prefijos_de_maprex()))`, leídas con una sesión propia
que se **cierra antes** de llamar al modelo; la búsqueda semántica (`ml.normalization.proponedor`) se arma en la primera búsqueda, dentro del
hilo; `Servicios.tarifa` = `tarifa_de(modelo, local=not envia_fuera_del_equipo)`; `Servicios.responder = lambda _: ESPERAR`; `proyecto` y
`version_partida` del borrador abierto.

---

## 3. Arquitectura

### 3.1 El puente (`aplicacion/hoja_asistente_puente.py`)

Fachada del motor. **Es el único módulo de la capa nueva que llama a `asistente.servicio` y `asistente.orquestador`** (los demás reciben
sus resultados). Con la clase `Borrador` compartida ya no convierte borradores; sus oficios son:

1. **Punto de contacto único**: `proponer`, `decidir`, `responder`, `hipotetico`, `resumen_hipotetico`, `descripcion`, `vista_previa`,
   `estimar_costo`, `fuente_del_cambio` y los re-exportes `Servicios`, `Topes`, `ESPERAR`, `EstadoPropuesta`, `MotivoFin`,
   `DependenciaPendiente`. Si el motor cambia, cambia aquí.
2. **Copia saneada y catálogo envuelto para P7** (`para_el_motor(borrador, nube)`, `catalogo_para_el_motor`, `del_motor(resultado, real, catalogo_real)`), §4.1.
3. **Cliente acotado** (`acotar(proveedor, plazo)`), §3.3.
4. **Guardia**: la prueba 4a-B1 comprueba que `asistente.servicio.Borrador is aplicacion.hoja.Borrador` (la identidad es lo que permite
   no convertir); si algún día difirieran, la prueba falla y obliga a decidir (no hay conversión muerta que mantener).

Ya no hay importación perezosa por culpa de `ui`. El puente importa el motor al cargarse; `api.main` lo carga al arrancar (el costo de
importar `asistente.servicio` es el de `pydantic` y unos módulos; `admin_asistente.py` ya importa partes del paquete). Quedan fuera de
`aplicacion/` y de `api/` el SDK de `anthropic` y `keyring`, que la guardia limita a sus adaptadores: el puente acota el cliente **sin
importarlo** (duck typing, §3.3).

### 3.2 La sesión del asistente: dónde vive y cuándo muere

- **Registro propio** en `aplicacion/hoja_asistente.py`: `dict[id_de_borrador, RegistroDelBorrador]` con un cerrojo, **fuera** de
  `BorradorVivo` (que no gana ningún campo: su `tamano` y su `pickle` no cambian; la disciplina del docstring `P:25-29`). La clave es el `id`
  del borrador: la autorización es la del borrador (`hoja_borradores.obtener(huella, id)` ya da 404 al ajeno).
- **`RegistroDelBorrador`** tiene dos partes con vidas distintas:
  - `aceptadas`: lista **persistente mientras viva el borrador** de `(numero_de_sesion, texto_de_fuente)` de cada sesión con propuestas
    aceptadas o editadas desde que se abrió el borrador (el texto es `servicio.fuente_del_cambio(sesion)` calculado al aceptar). **Sobrevive a
    descartar o reemplazar la sesión** (equivale a `CLAVE_ASISTENTE_ACEPTADAS`, `P:125`).
  - `sesion`: la `SesionDelAsistente` actual o `None`.
- **Contenido de `SesionDelAsistente`**: `estado`; la `SesionDeAsistente` del motor (`base` saneada, sin proveedor ni clave); `pedido`;
  `proveedor`, `modelo`, `destino`, `nube`; `testigo` (un `object()` único, §3.3); `rev_base`; **`aplicado: Borrador | None`** tipado
  `aplicacion.hoja.Borrador` (la regla de §3.5), inicializado al borrador **real** de proponer; `progreso`; `error`; `cache_hipotetico`
  (clave: estados de las propuestas + `rev`); `cancelado` (un `threading.Event`); `creado`; `cerrojo` propio.
- **Orden de bloqueos** (el mismo en todo el código nuevo): primero `vivo.cerrojo` y, **dentro**, el cerrojo del registro y el de la sesión.
  **Nunca** se llama a `hoja_borradores.obtener` ni `reemplazar` con un cerrojo de sesión tomado. Los avisos `al_quitar` llegan **fuera del
  cerrojo del registro de borradores pero a veces dentro de un cerrojo ajeno** (el hilo que barre puede estar editando otro borrador):
  el aviso solo toma el cerrojo del registro del asistente y el de la sesión, **no toma `vivo.cerrojo` ni hace E/S**; si hay que cerrar una
  sesión con pregunta pendiente en la base, lo hace en un hilo demonio corto (§3.4). Prueba de estrés B32.
- **Ciclo de vida** (todo pasa por `hoja_borradores.al_quitar`, patrón de `hoja_plano.py:258`):

| Evento | Qué pasa con el registro del asistente |
|---|---|
| `DELETE /v1/hoja/borradores/{id}` | se quita todo; un trabajo en vuelo recibe `cancelado` |
| abrir otra versión (el front descarta el borrador anterior) | igual: el borrador sale del registro |
| E11 `reemplazar: true` | igual |
| vencimiento a las **8 h** sin uso | igual (barrido perezoso existente) |
| expulsión por tope (4 por ficha, 64 globales, 256 MiB) | igual |
| cambio de caso (`caso_web.fijar` → `olvidar`), cierre de sesión, ficha vencida | igual |
| `guardar` (S1) con éxito | el borrador queda `guardado_como`; el registro **sigue** hasta que el borrador salga, no se puede decidir (409) y el gancho de cierre (§3.5) marca las sesiones de `aceptadas` |
| reinicio de la API | se pierde, como el borrador; `ia_*` conserva lo hecho (una sesión con pregunta sin cerrar queda con `fin` vacío: lo señala la etapa 3) |

- **Una sesión por borrador a la vez**: proponer de nuevo la reemplaza (como `P:800`); si la anterior estaba en `pregunta`, se cierra primero
  con `servicio.responder(sesion, None, registro)` (§3.4). Lo aceptado se queda en el borrador y en `aceptadas`.
- **Memoria**: como máximo un registro por borrador y, por tanto, `GLOBALES = 64`.

### 3.3 El trabajo de la IA: hilos demonio, cupo, plazos, cancelación

`aplicacion/hoja_asistente_trabajo.py`:

- **Traspaso del cupo.** El semáforo se toma en la ruta (`acquire(blocking=False)`) y su «testigo» (un token de un solo uso que sabe liberarlo una vez) **viaja con el hilo principal del trabajo y de ahí al hilo auxiliar de cada turno**: el hilo auxiliar lo libera en su `finally`, es decir, cuando el turno **de verdad regresa** (no cuando se abandona por plazo), y el principal lo libera si termina sin haber lanzado ningún turno. Un solo liberador por token (si dos lo intentan, el segundo no hace nada). B9 prueba: con un turno abandonado el cupo **sigue ocupado hasta que regresa** y entonces se libera exactamente una vez; y que fallar al arrancar el hilo libera el cupo.
- **Hilos demonio propios, sin `ThreadPoolExecutor`.** Cada propuesta arranca un `threading.Thread(daemon=True)`. El **cupo** es un
  `threading.BoundedSemaphore(EN_VUELO)` con `EN_VUELO = 2` (D-4) que `POST` toma **sin esperar** (`acquire(blocking=False)`; si no hay, 503) y
  que el hilo libera al terminar **o al abandonar** (un turno vencido libera su cupo cuando su hilo auxiliar regresa, §abajo). Así un hilo
  colgado no bloquea el apagado del proceso (los demonio no se esperan) y los abandonados son pocos y acotados.
- **Gancho de apagado**: `apagar()` fija `cancelado` en todas las sesiones, marca el semáforo como cerrado (los `POST` nuevos dan 503) y
  **no espera a ningún hilo**. Lo llama el `lifespan` de la aplicación (§12). Prueba B29: `apagar()` vuelve en menos de un segundo con un
  turno bloqueado, y un subproceso que arranca un trabajo bloqueado y termina, sale sin esperarlo.
- **Una petición de IA en vuelo por borrador**: un segundo `POST` mientras `pensando` da 409.
- **Ritmo por cuenta**: `PROPUESTAS_POR_HORA = 20` por **`usuario_id`** de la sesión (`SesionActiva.usuario_id`, `seguridad/sesiones.py:34`),
  **no** por huella de ficha: cerrar sesión y abrir otra ficha no reinicia el contador. 429 con `Retry-After` en segundos. Reloj inyectable.
- **Tope global**: sin cupo, 503 con `Retry-After: 30` (patrón de `hoja_plano`).
- **`ProveedorAcotado`** (envoltura del `ProveedorIA`: `nombre`, `modelo`, `envia_fuera_del_equipo`, `disponible`, `turno`):
  - Antes de cada turno: si `cancelado` o venció `PLAZO_TOTAL = 300 s`, lanza `ErrorDeProveedor("otro", …)`.
  - Ejecuta el turno en un hilo auxiliar demonio y espera `PLAZO_POR_TURNO = 120 s` (D-4); al vencer, lanza `ErrorDeProveedor("otro", …)`.
  - **Registra la categoría** antes de relanzar, porque el orquestador la pierde (`orquestador.py:401-402`): `ultima_categoria` ∈
    `sin_conexion`, `clave_invalida` (las de `ErrorDeProveedor`), `tiempo` (la agrega la envoltura: el protocolo solo admite tres categorías, así
    que lanza «otro» y anota «tiempo»), `cancelado` (cancelación de la persona) y `otro`.
  - Cuenta turnos y, con el `uso` de cada `Turno` y la tarifa, el **costo parcial** (para el progreso).
  - No guarda la clave en ningún atributo propio y se libera al terminar.
- **Cliente acotado** (`acotar(proveedor, plazo)`, en el puente): si el proveedor tiene `_crear_cliente` (`ProveedorClaude`), se hace
  `proveedor._cliente = proveedor._crear_cliente().with_options(timeout=PLAZO_POR_TURNO, max_retries=0)`, así el SDK **corta de verdad** en
  120 s y no reintenta (el reintento lo decide la persona). No se importa `anthropic` (la guardia lo limita a `claude.py`) y no se edita
  `claude.py`. Costo declarado: toca dos atributos privados de una clase congelada; si el SDK instalado no ofrece `with_options`, **la propuesta
  con ese proveedor no se hace** (409 «El proveedor no admite plazos: pida al administrador revisar el componente de IA.»), nunca se cae a un
  cliente sin plazo. 4a-1 lo verifica con el SDK instalado (B33). Ollama y los dobles no tienen cliente que acotar: valen la envoltura y su
  hilo auxiliar.
- **Cancelación**: `DELETE …/asistente` con `pensando` fija `cancelado`, **desacopla** el registro (el estado pasa a `sin_sesion` al instante)
  y responde 204. El hilo termina cuando regrese el turno en curso, **descarta su resultado** y cierra `ia_sesiones` con el motivo
  **`cancelado`** (no `error_de_proveedor`: `RegistroIA.cerrar` es un `UPDATE`, se sobrescribe el motivo que escribió el orquestador). Un `POST`
  nuevo es posible de inmediato si hay cupo.
- **Publicación con testigo de identidad**: al arrancar, el trabajo recibe el `testigo` de su sesión; al terminar publica el resultado **solo si**
  `registro.sesion is not None and registro.sesion.testigo is testigo` (si la sesión se desacopló, reemplazó o descartó, el resultado se
  tira). Sin esta comprobación un trabajo cancelado podría resucitar encima de una sesión nueva.
- **El trabajo no usa la `Session` de la petición**: abre `abrir_sesion(motor)` para el catálogo (la cierra antes del modelo) y
  `motor.connect()` para `RegistroIA(confirmar=True)`; el `motor` es el de `obtener_motor(vivo.caso)`, que la ruta pasa como argumento
  (`aplicacion/` no importa `api/`).
- **Qué ve el trabajo**: una copia inmutable del borrador al proponer; las ediciones siguen funcionando mientras la IA piensa.
- **Errores del trabajo** (después del 202, quedan en `error`): `sin_conexion`, `clave_invalida`, `tiempo`, `otro`; `ImportError` →
  `componente`; `SQLAlchemyError` → `base`; cualquier otra → `otro` con texto fijo. Siempre se conservan las propuestas ya validadas.
- **Costo de un turno abandonado (declarado)**: si un turno vence, el proveedor puede haberlo cobrado y el orquestador no lo registra. Con el
  cliente acotado el hilo muere a lo sumo a los 120 s; con otros proveedores sigue hasta que regrese y el semáforo lo cuenta hasta entonces.

### 3.4 Máquina de estados y preguntas de la IA

```
sin_sesion ──proponer──▶ pensando ──fin──▶ lista        (propuestas, sin propuestas, o detenida por tope/rechazos/cancelada)
                          │  │ └─pregunta de la IA──▶ pregunta ──seguir sin responder / DELETE──▶ lista (motivo cancelado) / sin_sesion
                          │  └─fallo del proveedor/plazo/base──▶ error   (se conservan las propuestas previas)
                          └─DELETE──▶ sin_sesion
lista / pregunta / error ──proponer──▶ pensando (reemplaza; una pregunta pendiente se cierra antes)
cualquiera ──DELETE / borrador sale──▶ sin_sesion
```

- `lista` agrupa los finales de `MotivoFin` (`terminar`, `fin_del_modelo`, `tope_de_turnos`, `tope_de_llamadas`, `tope_de_costo`,
  `rechazos_seguidos`, `rehusado`, `limite_de_salida`, `cancelado`); `resultado.motivo` dice cuál.
- **La pregunta es un caso esperado, no raro**: la regla 4 de las instrucciones (`privacidad.py:48`) manda `preguntar_al_usuario` cuando
  falta un dato, y el orquestador se invoca con `responder=lambda _: ESPERAR` (como la clásica, `P:782`). Con ESPERAR, el resultado queda en
  `ESPERANDO_RESPUESTA` **sin escribir `ia_propuestas` ni cerrar `ia_sesiones`** (`orquestador.py:333-345`), y decidir da 409. Sin salida, la
  persona pagaría y no obtendría nada. **Ruling de la etapa 1:** el panel ofrece **«Seguir sin responder»** (ruta A7), que llama a
  `servicio.responder(sesion, None, registro)`: el orquestador cancela la sesión, **escribe las propuestas y cierra `ia_sesiones` con
  `cancelado`**, y las propuestas hechas antes de la pregunta quedan **decidibles**. `DELETE` sobre una sesión en `pregunta` hace lo mismo
  antes de descartar (para no dejar `ia_sesiones` abierta); el aviso `al_quitar` lo intenta en un hilo demonio corto, con registro propio, y
  si falla solo lo anota en el log (sin contenido). Responder de verdad es la etapa 2 (misma continuación; §9).
- Mientras haya una pregunta sin atender, decidir una propuesta da 409 (la clásica ni pintaba los botones, `P:989`).

### 3.5 Aplicar lo aceptado: atómico, con `rev`, con trazabilidad

**Decisión: operación `decidir` propia sobre el núcleo de edición, no la cadena E1 a E11.** Motivos: §1.5 y que aplicar una propuesta es una
sola operación del motor que ya garantiza la misma puerta que una edición a mano (`espacio_desde_filas`, RF-92) y registra la decisión.

**La regla de la clásica que se reproduce** (`P:805-811` y `P:862-864`, `CLAVE_ASISTENTE_APLICADO`):

- `aplicado` arranca siendo el borrador de la sesión (aquí: el borrador **real** al proponer, tipado `aplicacion.hoja.Borrador`; con la clase
  compartida `==` funciona: sin eso la comparación entre dos clases devolvería siempre `False` por `NotImplemented`, y 4a-B15 lo cubre).
- `editada_a_mano = (aplicado is None) or (vivo.borrador != aplicado)`.
- Si **no** está editada a mano: se **reconstruye** (`sobre=None`: base de la sesión más todo lo aceptado) y tras decidir **`aplicado = nuevo`**.
- Si **está** editada a mano: se aplica **solo esa propuesta sobre la hoja vigente** (`sobre=vivo.borrador`) y tras decidir **`aplicado = None`**,
  y **se queda `None`** hasta que se proponga de nuevo. Así la segunda propuesta también se aplica sobre la hoja y la edición manual
  sobrevive. (La versión de la ronda 1 fijaba `aplicado = nuevo` siempre y perdía la edición al decidir la segunda propuesta.)

**Pasos de `POST …/asistente/propuestas/{propuesta}`** (todo dentro de `vivo.cerrojo`; el cerrojo de la sesión solo se toma dentro):

1. ya guardado → 409; `rev` distinto → 409 `MENSAJE_REV` (antes que el contenido; no aplica a `rechazada`); pregunta pendiente → 409.
2. **Calcular sin efectos**: `servicio.decidir` sobre una **copia de trabajo** de la sesión (`Pendientes` copiada, `registro=None`) con
   `sobre = para_el_motor(vivo.borrador)` si está editada a mano, o `None`. De aquí salen `DependenciaPendiente` y `HojaInvalida` (409,
   «No se decidió nada»).
3. `del_motor(...)` (devuelve las descripciones reales, §4.1) y `completar_composiciones` (la partida nueva toma su APU del catálogo con la
   lista de precios de la versión abierta, `P:256-275`). Un fallo de lectura es 503 y no cambió nada.
4. **Registrar** `RegistroIA(confirmar=True).decidir(sesion, id, estado, activa.usuario)` en una conexión propia. Si falla: 503 y nada cambió.
   (La misma llamada que haría `servicio.decidir` con registro; se hace aquí para que «registrar» ocurra **después** del paso 3.)
5. Reemplazar (sube `rev`) y publicar: la copia de trabajo pasa a ser `pendientes`, se fija `aplicado` según la regla, y si la decisión no es
   `rechazada` se agrega a `aceptadas` la sesión (con su texto de fuente).

**Los pasos 4 y 5 no son "en memoria y sin fallo posible"**: `hoja_borradores.reemplazar` llama a `obtener`, que puede lanzar
`BorradorInexistente` si el borrador fue expulsado entre medias. El daño es solo de auditoría (la decisión quedó registrada y el borrador ya no
existe, así que no hay hoja a la que no se aplicó); la ruta responde 404 `MENSAJE_FALTA`. B21 lo cubre.

**Cómo encaja `cambiar`.** `hoja_edicion._cambiar` pasa a público (`cambiar`) y gana `antes_de_reemplazar: Callable[[hoja.Borrador], None] | None
= None`. Orden dentro: guardado, `rev`, `construir`, `completar_composiciones`, `antes_de_reemplazar`, `reemplazar`. Los pasos 3 y 4 de arriba
caben así (el 3 en `construir`, el 4 en `antes_de_reemplazar`). Cambio aditivo: valor por omisión `None`; los **8 consumidores** (las siete
ediciones de `hoja_edicion.py` y `hoja_plano.fusionar`, `hoja_plano.py`: `:486` aquí, `:352` tras el retiro) se actualizan a `cambiar` y no cambian de comportamiento.

**`sin_partida` (y cualquier decisión que deje el borrador igual).** `aplicar()` ignora `SIN_PARTIDA` (`propuestas.py:132-133`) y `_cambiar`
devuelve antes de `antes_de_reemplazar` si `nuevo == vivo.borrador`. **Ruling (lo menos invasivo):** `cambiar` llama a `antes_de_reemplazar`
**también cuando no hay cambio**, pasándole el borrador vigente, y devuelve `vivo` con el mismo `rev` (3 líneas, solo si el parámetro viene;
las otras ediciones no lo pasan y su comportamiento no cambia). Efecto en `decidir`: se registra la decisión, la propuesta deja de estar
pendiente, **`rev` no sube** y el `resumen` es el mismo. **Sí cuenta en `aceptadas`** (como en la clásica, que agrega la sesión cuando el
estado no es `RECHAZADA`, aunque `_poner_borrador` no cambie nada): la necesidad sin partida es un hallazgo que la persona *aceptó* y que
`ia.json` debe poder mostrar. Rechazarla tampoco cambia el borrador y se registra igual; como `rechazada` no exige `rev` del cliente, la ruta pasa a `cambiar` el **`vivo.rev` actual leído dentro del cerrojo** (con un `rev` viejo `cambiar` daría 409 `RevDesactualizado` a un rechazo que no toca nada). B20 lo prueba: rechazar con un `rev` viejo funciona.

**Aceptar y editar** (`editada`): entra al borrador igual que `aceptada`; la persona retoca a mano. Dónde, según el tipo (tabla en
`logica.ts`): `ambiente`, `fuente`, `punto` → pestaña «Espacio y metrajes»; `recorrido` declarado → «Espacio y metrajes» (vértices de
recorridos); `recorrido` propuesto (lo calcula el sistema) → «no hay nada que editar a mano»; `partida` → pestaña «Presupuesto» (su
cantidad); `sin_partida` → nada que editar. No es la misma frase para todos.

**Trazabilidad (la IA nunca es autora):**

| Eslabón | Qué queda |
|---|---|
| Fila aceptada del espacio | `OrigenMedida(tipo=ia, referencia="modelo=…; propuesta=P1; proveedor=…; sesion=N; supuesto.<campo>=…")` con `id = "IA-N-P1"` (`propuestas.referencia_de`) |
| Partida aceptada | `ItemComputo` MANUAL, `origen_id = "ia:N:P1"` (`PREFIJO_ORIGEN_IA`; `estado_de_items` ya lo reconoce) |
| Decisión | `ia_propuestas.estado` y `decidida_por = "Nombre <login>"` (la cuenta; ningún campo del cuerpo puede decirlo: `extra="forbid"`) |
| Guardado | `fuente_sugerida` (abajo); `RegistroCambio.responsable` = la cuenta (RF-82) |
| Paquete | `anexo_ia` (`ia.json`) vía `marcar_guardada` (gancho de D-3) |

**`fuente_sugerida`** se deriva de **`aceptadas` de todas las sesiones del borrador**, no solo de la vigente: una por sesión («propuesta de IA,
sesion N, proveedor/modelo», el texto del motor) unidas con «; » y cortadas a 300 caracteres (el tope de la fuente de S1). Está presente en el
estado `sin_sesion` y en todos los demás: tras «Descartar lo pendiente», o al reemplazar la sesión, la fuente sigue citando a la IA.

**Gancho de cierre al guardar (D-3, solo servidor).** `hoja_guardado.al_guardar: list[Callable[[BorradorVivo, Guardado], None]]` se avisa
**después del `commit`** y fuera de los cerrojos. El de la sesión del asistente llama a `RegistroIA(confirmar=True).marcar_guardada(n, codigo,
proyecto=vivo.proyecto)` para cada `n` de `aceptadas` y vacía la lista. Si falla, la versión ya está guardada y no se deshace: la respuesta de S1
lleva un `avisos` aditivo (`list[str]`, vacío de fábrica) con el texto de la clásica y `aceptadas` se conserva para el siguiente guardado.

### 3.6 Qué pasa si el borrador cambia mientras la IA piensa

- La IA trabaja sobre `vivo.borrador` al proponer (`rev_base`); las ediciones siguientes suben `rev` y siguen funcionando.
- Al terminar, las propuestas son válidas contra la base antigua. Como la hoja actual ya no es `aplicado`, `editada_a_mano` es verdadera y cada
  propuesta se aplica **sobre la hoja vigente**. Si ya no cabe, el 409 dice «No se decidió nada» y se puede rechazar.
- El panel avisa: «Usted editó la hoja mientras la IA trabajaba (o después): cada propuesta se aplicará sobre la hoja tal como está ahora.»
- `rev` en el cuerpo de `decidir` es el que el front vio; si otra ventana lo cambió, 409. El hipotético se cachea por `(estados, rev)`.

---

## 4. Privacidad y gasto

### 4.1 Qué viaja al proveedor

- **Se envía** (lista blanca de `asistente/privacidad.py`): instrucciones y esquemas fijos; el **pedido tal como se escribió**;
  `resumen_del_borrador` (ids, geometría, códigos, descripciones, unidades, cantidades de `items_base`, nombres de ambientes y puntos
  limpios de caracteres de control y cortados a 80); candidatas de catálogo (≤ 10 por búsqueda, ≈ 50 por sesión); hallazgos minimizados.
- **No se envía:** precios, montos, totales, APU, curva, punto de equilibrio, cotizaciones, listas de precios, el nombre del proyecto (va el
  alias `P1`), nombres de empresa o de usuarios **cuando el motor los tiene en campos conocidos**, archivos, la clave, el registro `ia_*`.
- **Regla P7 y la brecha que había (§1.8).** `resumen_del_borrador` envía la descripción de **todos** los `items_base`. **Ruling (Eugenio
  delegado): la regla P7 se respeta en la capa nueva**: con un proveedor de nube (`proveedor.envia_fuera_del_equipo`), el puente entrega al
  motor una **copia saneada** del borrador en la que cada ítem de `items_base` cuyo `codigo_partida` empieza por alguno de
  `prefijos_de_maprex` lleva `descripcion = ""` (queda código, unidad y cantidad). Con un proveedor local no se sanea. No se toca ningún
  archivo congelado.
  - `para_el_motor(borrador, nube)` hace la copia; el motor trabaja con ella (`proponer`, `decidir`, `hipotetico`, `auditar`).
  - **Segunda fuga que cerrar: los ítems que el propio motor crea.** `propuestas._item` (`propuestas.py:165-178`) arma el `ItemComputo` de una
    partida propuesta con `partida.descripcion` de `CatalogoDeLaBase.partida()` (`catalogo.py:52`), que devuelve la descripción **real**
    aunque `de_maprex=True`. Escenario: nube, prefijos `("ELE-",)`, el modelo busca `ELE-001`, llama `proponer_partida` y luego
    `consultar_borrador`: `resumen_del_borrador(self.hipotetico())` (`orquestador.py:262-263`) enviaría la descripción MaPreX real y quedaría
    en el historial que se reenvía en cada turno. Por eso el puente entrega al motor, además de la copia del borrador, un **catálogo
    envuelto** (`catalogo_para_el_motor(catalogo_real, nube)`): su `partida(codigo)` devuelve la `PartidaVista` con `descripcion=""` cuando
    `nube and de_maprex`, y su `buscar` igual (`describir_partida` ya oculta la descripción; el envoltorio cubre el camino de `_item`).
    El envoltorio es el `catalogo` de `Servicios` y de la `SesionDeAsistente`, así que lo usan `proponer`, `decidir` e `hipotetico`.
  - `del_motor(resultado, real, catalogo_real)` **devuelve las descripciones reales** al resultado antes de usarlo: toma `real.items_base` sin
    los ítems de origen IA, más, en el orden del motor, los ítems IA del resultado, usando la versión de `real` si ese `origen_id` ya estaba
    (una partida MaPreX aceptada antes conserva su descripción) y, **si es nueva, la descripción real por código desde el catálogo REAL**
    (`catalogo_real.partida(codigo).descripcion`; sin ese paso quedaría en blanco). Los demás campos son los del resultado.
  - **Alcance honesto de P7:** queda cubierto todo lo que el motor envía y que sale de `items_base` o del catálogo: `consultar_borrador`,
    `pedir_informe_auditoria` (el informe se elabora sobre la copia saneada y los ítems nuevos nacen con descripción vacía), `buscar_partidas`
    y `consultar_partida`. No es «P7 antes de cualquier envío» de cualquier texto: los nombres libres y el pedido siguen su regla propia (límites
    de más abajo).
  - **Si `prefijos_de_maprex` está vacío** (el valor de fábrica) con un proveedor de nube, nada es MaPreX y las descripciones viajan: A0 lo
    avisa (`aviso_maprex`), el panel lo muestra junto a la estimación y **no bloquea** (D-8: el administrador los configura).
- **El catálogo que ve la IA** se arma con `CatalogoDeLaBase` sobre `PartidaVista(codigo, descripcion, unidad, dominio, de_maprex)`: ningún
  campo es dinero; en nube las MaPreX viajan solo con código y unidad (ya lo hace `describir_partida`).
- **Límites declarados (no son garantías):**
  - Los **nombres y especificaciones** (ambientes, puntos; texto libre ≤ 80 caracteres tras `limpiar`) y las descripciones no MaPreX **no
    tienen un filtro de nombres de empresa o de personas**: si alguien escribió «Casa de Fulano» en un ambiente, viaja.
  - `contiene_secreto` es **heurístico**: solo `sk-ant-` y `-----BEGIN`. No detecta otras claves ni contraseñas.
  - El sistema no filtra datos personales del pedido (S4 §8.1).
- La prueba 4a-B26 lo comprueba **desde lo que recibe el proveedor** (`ProveedorGuionado.recibidos`), incluido el caso MaPreX.

### 4.2 La clave de IA y lo que se rechaza antes de enviar

- **La clave nunca sale del servidor.** Las respuestas proyectan nombre, modelo, destino, disponibilidad y motivo (enmascarados y cortados a 300). El
  422 no repite lo enviado. El estado no guarda el proveedor. Ningún esquema tiene campo `clave` (prueba de recorrido sobre `docs/api.json`).
- **Pedido**: obligatorio no vacío tras recortar espacios; **≤ 4 000 caracteres** (D-4); si `contiene_secreto(pedido)` → 422 «El pedido parece
  contener una clave de acceso: quítela y vuelva a intentarlo. No se envió nada.» **sin eco, sin llamar al proveedor y sin fila en
  `ia_sesiones`**. El rechazo es **parcial por naturaleza** (§4.1, heurístico); por eso la advertencia permanente.
- **Vista previa**: `POST …/asistente/previa` devuelve el texto **exacto** de `primer_mensaje(pedido, borrador_saneado)` (lo que de verdad
  viajaría, ya saneado) y el destino. Solo lectura. Se corta a 100 000 caracteres con `truncada` y `caracteres`.
- **Advertencia permanente** (copia de `P:1064`, con tildes): «El pedido viaja tal como lo escribe: no escriba datos personales, claves ni
  precios.»
- **Texto ajeno**: lo que dice la IA (descripciones, supuestos, citas, notas, pregunta, errores de herramientas) se muestra **siempre como
  texto**, nunca Markdown ni HTML, sin enlaces ni imágenes (RV-14).

### 4.3 Gasto

| Control | Dónde | Valor |
|---|---|---|
| Estimación previa | por proveedor, en A0 | **orientativa**: 12 turnos × (10 000 entrada + 3 000 salida + 6 000 caché) con la tarifa del modelo **pedido** (`precios_ia.json`). **Opus 5.5: 0,1012 × 12 = 1,2144 USD** (oráculo a mano, P-2); local: 0. **El tope real es el de la sesión.** |
| ¿Supera el tope? | el servidor compara `Decimal` y manda `estimacion_supera_el_tope` | el front no compara números |
| Tope por sesión | `topes_de_la_instalacion().costo` (`tope_usd`, 2 USD de fábrica) | el turno que lo alcanza se completa y la sesión se detiene conservando lo propuesto (`tope_de_costo`) |
| Turnos y llamadas | `Topes` | 12 y 60 |
| Ritmo / cupo / plazos | por `usuario_id` / global / por turno y total | 20 por hora / 2 / 120 s y 300 s (D-4) |
| Costo mostrado | `resultado.costo` y el parcial de la envoltura, `{texto, exacto}` en USD | **estimación con la tarifa del modelo pedido**: con `fallbacks="default"` (`con_respaldo=True`, el valor de fábrica) otro modelo puede responder (`Turno.modelo_que_respondio`) y se cobra a su tarifa; el costo real lo da la factura del proveedor. El panel lo dice («costo estimado») |
| Tope acumulado por instalación | no existe | etapa 3 (D-6) |

El gasto es del proveedor y de la clave de la empresa; esta capa solo lo **acota**. Ninguna ruta de lectura llama al proveedor.

### 4.4 Sin proveedor real en pruebas ni en el desarrollo

- **Costura de inyección** `hoja_asistente.fijar_proveedores(fuente)` (administrador de contexto para pruebas); por omisión
  `asistente.instalacion.proveedores_de_la_instalacion`. Las pruebas usan `ProveedorGuionado` (sin red) con `nombre="claude"`,
  `modelo="claude-opus-5-5"`, `envia_fuera_del_equipo=True` para que la tarifa exista sin cobrar. Los guiones viven en el fixture nuevo
  `tests/fixtures/asistente_guiones.py` (`guion`, `guion_con_pregunta`, `ProveedorConClave`), con los pedidos de
  `tests/fixtures/asistente_pedidos.py` (`PEDIDO`, `AMBIENTE`, `PARTIDAS`, donde `ELE-001` es `de_maprex=True`).
- **Doble guardia**: un `autouse` hace fallar `asistente.fabrica.proveedores` y `ProveedorClaude.turno` si se llaman sin la inyección
  (B18), y la guardia de red de `tests/conftest.py` sigue activa. Ninguna prueba abre la red.
- **Auditoría visual**: `scripts/auditoria_visual_asistente.py` (solo desarrollo) arranca la API en `127.0.0.1` con la costura apuntando a un
  guion. **No** hay variable de entorno ni interruptor de «modo simulado» en producción.
- **Prueba real**: solo con la autorización de gasto de Eugenio (D-2; T20).
- **Datos de prueba**: únicamente OF-001, TI-001 y los pedidos ficticios. Nunca libros, nombres de empresa ni cifras reales.

---

## 5. Contrato de API (etapa 1)

### 5.1 Reglas comunes

| Regla | Detalle |
|---|---|
| Módulos | `api/rutas/hoja_asistente.py`, `api/esquemas_hoja_asistente.py`; lógica en `aplicacion/hoja_asistente*.py`; la API no importa `scripts` ni `tests` |
| Clase de ruta | `class _RutaAsistente(RutaSinCache, RutaSinEco)` **en ese orden**; `mensaje_por_omision` = «Los datos del asistente no tienen la forma esperada: elija un proveedor y escriba el pedido como texto.» |
| Acceso | `Depends(cuenta_con(Accion.EDITAR_HOJA, MENSAJE_SOLO_CUENTA_IA))`: **solo cuenta con `EDITAR_HOJA`** (la acción de la clásica; solo el rol `arma`). Clave de API → **403** «El asistente de IA de la hoja se usa con una cuenta; la clave de API no sirve.»; sin sesión → 401; rol sin permiso → 403; CSRF y `Origin` en los métodos que escriben |
| Borrador | `_vivo(request, activa, id)` de `api/rutas/hoja.py`: ajeno → **404**; de otro caso → 409 |
| Responsable | siempre `activa.usuario`. Cuerpos con `extra="forbid"`: un campo `usuario`, `responsable`, `clave` u otro → 422 sin eco |
| Caché | `Cache-Control: no-store` en éxito y error |
| 422 | sin eco; los mensajes de dominio son del motor |
| Montos | `Monto {texto, exacto}`; ningún `float`; costos en USD |
| Texto de la IA | solo en los campos `ia:` de §5.2 |
| Tamaños | pedido ≤ 4 000 caracteres; `proveedor` ∈ {`claude`, `ollama`}; `propuesta` con `^P[0-9]{1,4}$`; estado ≤ 64 propuestas |

### 5.2 Esquemas

```
ProveedoresDelAsistente {
  activo: bool, motivo: str | null,           # si activo=false: motivos juntos y sin repetir, enmascarados
  por_defecto: str | null,
  tope_sesion: Monto | null,                  # USD; null = sin tope
  aviso_maprex: str | null,                   # nube + prefijos_de_maprex vacío (§4.1)
  proveedores: [{ nombre, modelo: str | null, disponible: bool, motivo: str,
                  envia_fuera_del_equipo: bool | null, destino: str | null,
                  tarifa: bool, estimacion: Monto | null, estimacion_supera_el_tope: bool }] }

PreviaDelPedido { destino: str, caracteres: int, truncada: bool, texto: str }

AsistenteEstado {
  estado: "sin_sesion" | "pensando" | "lista" | "pregunta" | "error",
  sesion: int | null, proveedor: str | null, modelo: str | null, destino: str | null, pedido: str | null,
  progreso: { turno: int, turnos_max: int, segundos: int, costo: Monto } | null,
  resultado: { motivo: str, mensaje: str, costo: Monto, turnos: int, llamadas: int, notas: [str] } | null,   # ia: mensaje, notas
  pregunta: str | null,                       # ia
  error: { categoria: "sin_conexion"|"clave_invalida"|"tiempo"|"componente"|"base"|"otro", mensaje: str } | null,
  propuestas: [Propuesta],
  sobre_la_hoja_editada: bool,                # editada_a_mano (§3.5)
  fuente_sugerida: str | null,                # de `aceptadas` de TODAS las sesiones; también en sin_sesion
  hay_aceptadas: bool }

Propuesta { id, tipo, clave, descripcion: str,                       # ia
            estado: "pendiente"|"aceptada"|"editada"|"rechazada",
            retirada_por_la_ia: bool,                                # estaba RECHAZADA en el resultado de la sesión (la retiró la IA)
            supuestos: [{campo, motivo}], citas: [{campo, texto}],   # ia
            declarado: bool }

DecisionDePropuesta  (cuerpo) { estado: "aceptada"|"editada"|"rechazada", rev: int | null }
RespuestaDeDecision           { resumen: Resumen, asistente: AsistenteEstado }
Hipotetico {
  rev: int, disponible: bool, mensaje: str | null,
  moneda: str, total_actual: Monto, total_si_acepta: Monto | null, diferencia: Monto | null,
  cambios_si_acepta: int | null,
  hallazgos: [{severidad, total}], hallazgos_total: int,
  propuestas_pendientes: int, partidas_sin_apu: int }                # sin APU en el catálogo: quedan pendientes y no suman
```

`retirada_por_la_ia` se calcula comparando con `sesion.resultado.propuestas` (el estado al terminar la corrida): una propuesta que ya estaba
`RECHAZADA` ahí la retiró la IA (`retirar_propuesta`); los rechazos humanos son posteriores. Se pinta distinto de «rechazada» (§6.4).
`diferencia` = `total_si_acepta − total_actual` en `Decimal`, con signo, en el servidor. El orden de `hallazgos` es el alfabético de la
clásica (`P:1022`).

### 5.3 Rutas

| # | Ruta | Cuerpo | Responde |
|---|---|---|---|
| A0 | `GET /v1/hoja/asistente/proveedores` | — | 200 `ProveedoresDelAsistente`. No gasta. Sin borrador |
| A1 | `POST /v1/hoja/borradores/{id}/asistente/previa` | `{proveedor, pedido}` | 200 `PreviaDelPedido`. No gasta |
| A2 | `POST /v1/hoja/borradores/{id}/asistente` | `{rev, proveedor, pedido}` | **202** `AsistenteEstado` (`pensando`). Reemplaza una sesión terminada |
| A3 | `GET /v1/hoja/borradores/{id}/asistente` | — | 200 `AsistenteEstado` (`sin_sesion` si no hay: no es un error) |
| A4 | `GET /v1/hoja/borradores/{id}/asistente/hipotetico` | — | 200 `Hipotetico`; **completa composiciones** antes de elaborar (§5.5); 404 si no hay sesión `lista` |
| A5 | `POST /v1/hoja/borradores/{id}/asistente/propuestas/{propuesta}` | `{estado, rev}` | 200 `RespuestaDeDecision` |
| A6 | `DELETE /v1/hoja/borradores/{id}/asistente` | — | 204, idempotente. `pensando` cancela; `pregunta` cierra la sesión antes de descartar; si no, descarta lo pendiente (**lo aceptado se queda**) |
| A7 | `POST /v1/hoja/borradores/{id}/asistente/seguir` | — | 200 `AsistenteEstado` (`lista`, motivo `cancelado`). Solo con estado `pregunta` |

### 5.4 Errores por ruta

| Situación | Código | Texto (con tildes si los compone la capa nueva; los del motor, tal cual) |
|---|---|---|
| sin sesión | 401 | el de siempre |
| clave de API | 403 | «El asistente de IA de la hoja se usa con una cuenta; la clave de API no sirve.» |
| rol sin `EDITAR_HOJA` | 403 | el de siempre |
| borrador ajeno o inexistente | 404 | `MENSAJE_FALTA` |
| borrador de otro caso | 409 | `MENSAJE_OTRO_CASO` |
| `rev` desactualizado (A2, A5 salvo rechazar) | 409 | `MENSAJE_REV` |
| borrador ya guardado | 409 | «Este borrador ya se guardó como la versión {c}; abra esa versión para seguir.» |
| versión de solo lectura (A2) | 409 | «El asistente de IA no se abre en una versión de solo lectura: alguna partida ya no tiene composición vigente en el catálogo. Abra la versión vigente para usarlo.» (`P:1085`) |
| proveedor no disponible o desconocido (A1, A2) | 409 | «Elija un proveedor disponible.» (`P:763`); si no hay ninguno, el motivo de A0 |
| sin tarifa (A1, A2) | 409 | «No hay tarifa para el modelo {modelo}: pida al administrador agregarla.» (`P:769`) |
| falta el extra `ia` | 409 | `FALTA_EL_COMPONENTE` + «. Instálelo y vuelva a abrir Sílice.» |
| el proveedor no admite plazos (A2) | 409 | «El proveedor no admite plazos: pida al administrador revisar el componente de IA.» |
| ya hay una petición en curso (A2) | 409 | «Ya hay una petición de IA en curso en este borrador: espere a que termine o cancélela.» |
| pedido vacío, largo, forma o campo extra | 422 | sin eco: «El pedido debe tener entre 1 y 4 000 caracteres.» / `mensaje_por_omision` |
| pedido con una clave | 422 | «El pedido parece contener una clave de acceso: quítela y vuelva a intentarlo. No se envió nada.» |
| sin sesión del asistente (A4, A5, A7) | 404 | «No hay una sesión del asistente en este borrador.» |
| propuesta inexistente (A5) | 404 | «Esa propuesta no existe en esta sesión.» |
| propuesta ya decidida (A5) | 409 | «{id} ya no está pendiente: ya se decidió.» (`P:844`) |
| pregunta sin atender (A5) | 409 | «La IA hizo una pregunta que todavía no se responde: pulse «Seguir sin responder» o descarte la sesión.» |
| no hay pregunta (A7) | 409 | «La IA no tiene una pregunta pendiente.» |
| depende de otra pendiente (A5) | 409 | texto de `DependenciaPendiente`, tal cual |
| no cabe en la hoja editada (A5) | 409 | «{id} no se puede aplicar sobre la hoja tal como usted la dejó: {error}. Revise lo que editó a mano (por ejemplo, si quitó una fila que la propuesta usa) o rechace la propuesta. No se decidió nada.» (`P:850-856`) |
| ritmo por cuenta (A2) | 429 | «Hizo muchas peticiones al asistente en poco tiempo: espere unos minutos.» + `Retry-After` |
| sin cupo global o apagando (A2) | 503 | «El asistente está atendiendo otras sesiones: intente de nuevo en un momento.» + `Retry-After: 30` |
| la base no se pudo leer o escribir | 503 | `MENSAJE_BASE` (sin `orig`) |

Los fallos del **proveedor** ocurren después del 202 y llegan por A3 en `error` o `resultado.motivo`.

### 5.5 El resultado hipotético es el de aceptar de verdad

El hipotético de la clásica (`P:965-980`) elaboraba `servicio.hipotetico(...)` **sin completar composiciones**: una partida propuesta cuyo APU
no está aún en `borrador.composiciones` quedaba como pendiente, sumaba 0 y añadía un hallazgo `ERROR` con `CODIGO_PENDIENTE`
(`core/budget/presupuesto.py:148-189`; `completar_composiciones` es quien trae el APU del catálogo, `aplicacion/hoja.py:1764-1787`). Entonces
`total_si_acepta` y `diferencia` (DV-IA-4) saldrían **subestimados** frente a lo que pasa al aceptar, que sí completa (paso 3 de §3.5).
**Ruling:** A4 aplica `completar_composiciones(Catalogo(sesion), hipotético, lista=lista_de_la_version)` (solo lectura, con la sesión de la
petición y la misma lista de precios) **antes** de `con_r17` y `servicio.resumen_hipotetico`. Una partida sin APU en el catálogo sigue pendiente
y se cuenta en `partidas_sin_apu`. La cifra es la que quedará al aceptar.

---

## 6. Interfaz

### 6.1 Colocación

El `<aside aria-label="Asistente de IA">` deja de estar vacío y oculto. Estructura (HTML válido; **el `h2` no va dentro del botón de un
acordeón**):

```
<aside aria-label="Asistente de IA">
  <h2 class="cds--type-heading-compact-02"><button type="button" aria-expanded aria-controls="…">Asistente de IA: propone, usted decide</button></h2>
  <span class="etiqueta de estado">2 propuestas pendientes</span>
  <div id="…" role="region" aria-labelledby="…" hidden={!abierto}> … contenido … </div>
</aside>
```

Es un **desplegable propio** (el patrón de encabezado `h2 > button` de WAI-ARIA), no un `Accordion` de Carbon (cuyo `AccordionItem` mete el
título dentro del botón), estilado con los tokens de Carbon. Va en `index.tsx` **entre «Estado del borrador / Descargar Excel» y las
pestañas**, cerrado de fábrica; se abre solo si hay sesión al cargar.

```
┌ Contenido (≈ 1078 px a 1366 px; ≈ 800 px a 1056 px) ──────────────────────────────────────────────┐
│ Hoja del proyecto                                                                                   │
│ Estado del borrador · 3 cambios sin guardar · Total 2.703,86 USD     [Guardar versión…] [Excel]    │
│ ┌ aside · Asistente de IA: propone, usted decide ───────────────────────────  [2 pendientes] ▾ ┐   │
│ │ ┌ Formulario ────────────────────┐ ┌ Resultado si acepta lo pendiente ──────────────────────┐ │   │
│ │ │ Proveedor [Claude ▾]           │ │ Total ahora            2.703,86 USD                     │ │   │
│ │ │ ¿Qué necesita armar? [        ] │ │ Total si acepta todo   2.750,12 USD  (+46,26)          │ │   │
│ │ │ Destino · Estimación · Tope    │ │ Hallazgos: 3 (ADVERTENCIA: 2, INFO: 1) · 5 cambios     │ │   │
│ │ │ ▸ Lo que se enviará            │ └─────────────────────────────────────────────────────────┘ │   │
│ │ │ [Proponer]                     │ Propuestas de la IA (3)                                     │   │
│ │ └────────────────────────────────┘ 1. Ambiente BAN-01: 2 x 1.5 x 2.5 m   [pendiente]          │   │
│ │                                       [Aceptar] [Aceptar y editar] [Rechazar]  ▸ citas        │   │
│ │                                    [Descartar lo pendiente]                                   │   │
│ └────────────────────────────────────────────────────────────────────────────────────────────┘   │
│ ─ Espacio y metrajes │ APU │ Presupuesto │ … (pestañas)                                           │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Sin anchos fijos en píxeles.** `grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr))`: a 1366 px caben formulario y
  resultado lado a lado; a 1056 px y con **letra Grande o Muy grande** (`--silice-escala-letra` 1,25 y 1,5; el menú pasa a capa) se apila.
  `min-inline-size: 0` y `overflow-wrap: anywhere` en todo texto de la IA; nada provoca desplazamiento horizontal de la **página**.
- **Sin desplazamiento interno propio** salvo el cuadro de «Lo que se enviará» (región `role="region"`, `tabindex="0"`, `aria-label`,
  `max-block-size: 20rem`).
- **Lista y no tabla** para las propuestas (`<ol aria-label="Propuestas de la IA">`).
- **Carbon g10, esquinas rectas, densidad `sm`, sin animación decorativa.** Un solo `h1` en la página; el panel usa un `h2` y `h3` por bloque.
  **Sin verde ni rojo**: la diferencia de total es un número con signo; el color nunca va solo.
- **Asistente apagado o sin el extra `ia`**: el desplegable existe y, abierto, dice por qué (los motivos de A0) y que lo activa el
  administrador. **Versión de solo lectura**: el mensaje del caso 9i y sin formulario.
- Nombre único de la prop del panel para avisar a la página: **`alAplicar(resumen)`** (la página la conecta a `aplicar` de `useBorrador`).

### 6.2 Formulario

1. **Proveedor** — `Select` con los disponibles («Claude (claude-opus-5-5)», «Modelo local (…)»); preselecciona `por_defecto`. Los no disponibles
   salen como texto «No disponible: {nombre}: {motivo}».
2. **Pedido** — `TextArea` con etiqueta visible «¿Qué necesita armar? (en sus palabras)», `maxLength = 4000`, contador «n de 4.000 caracteres»
   con **`formatoEsVe(String(n))`** (no `Intl.NumberFormat`; F10 vale para todo el directorio, contador incluido), `aria-describedby`, `rows = 4`,
   advertencia de §4.2. **Solo en memoria del componente**: ni `localStorage` ni `sessionStorage`.
3. **Destino, estimación y tope** — «Destino: {destino}», «Estimación de costo por tarea (orientativa; el tope real es el de sesión): {x} USD»,
   «Tope por sesión (lo fija el administrador): {t} USD | sin tope». Si `estimacion_supera_el_tope`: aviso `warning` «La estimación supera el
   tope: la sesión se detendrá al alcanzar el tope y conservará lo que haya propuesto.» Si `aviso_maprex`: aviso `warning` con ese texto («Esta
   instalación no tiene prefijos de MaPreX configurados: si usa partidas de MaPreX, sus descripciones viajarán al proveedor en la nube. Lo
   configura el administrador.»).
4. **«Lo que se enviará»** — `<details>` nativo; al abrirlo pide A1 (pausa de 600 ms tras la última tecla, solo abierto). Muestra destino,
   `caracteres` y el texto en un `<pre>` dentro de la región desplazable; si `truncada`, «se muestra el comienzo; se envía completo».
5. **Proponer** — botón primario, **deshabilitado** sin pedido, sin proveedor, en solo lectura, con una petición en curso o sin tarifa. Al
   pulsarlo: «Proponiendo…», campos `readOnly` (no `disabled`) y el foco se queda en el botón.

### 6.3 Progreso, sondeo y lo que nunca hace el panel con los errores

- `InlineLoading` «La IA está trabajando: turno {t} de {máx}. Costo estimado hasta ahora: {costo} USD (tope {tope}).» y botón **Cancelar** (sin
  confirmación; el aviso dice que ya se pagó lo consumido).
- **Un solo `div role="status" aria-live="polite"` siempre montado**. Se anuncia: inicio, **cambio de turno** (máximo uno cada 10 s) y fin
  («La IA terminó: {n} propuestas pendientes.» / «…sin propuestas.» / «La IA no pudo completar la tarea.»). Segundos y sondeo no se anuncian.
- **Sondeo**: `GET …/asistente` cada 2 s mientras `pensando`; pausa con la pestaña oculta y una lectura al volver; tres fallos seguidos
  detienen el sondeo («Se perdió la conexión con el servidor. Reintentar»); 401 → `alExpirar()`.
- **El panel pide A3 al montarse** (para recuperar la sesión tras F5) y A0 al abrirse o si A3 trae sesión. **Un fallo de A0 o de A3 nunca pinta un
  `role="alert"`**: se muestra dentro del panel como texto `role="status"` («No se pudo consultar el asistente. Reintentar») y un 404 de A3 (borrador
  ausente: ya lo atiende la página) o un 500 se ignoran en silencio. Motivo: el asistente es opcional y no puede romper los avisos únicos que
  cuentan las pruebas existentes (`Edicion.test.tsx:151`, `Edicion3c2.test.tsx:171`, `EdicionApu.test.tsx:206`, `Vistas.test.tsx:425`) ni los
  que ve la persona. 4a-3 además actualiza los mocks (ver §8) para que respondan A0/A3 con `sin_sesion`.

### 6.4 Propuestas

Cada elemento de la lista:

- Numeración visible, `descripcion` (texto de la IA, escapado), una `Tag` con el **estado en texto** y un ícono distinto por estado:
  «pendiente», «aceptada», «aceptada: …» (con la frase por tipo de §3.5), «rechazada» y «**retirada por la IA**» (`retirada_por_la_ia`).
- `supuestos`: «Supuestos de la IA: {campo}: {motivo}; …» (`P:1012`). `citas`: `<details>` «Dónde lo dice el pedido» (mejora declarada, DV-IA-3).
- Botones **solo para `pendiente`**: «Aceptar», «Aceptar y editar», «Rechazar» (`Button size="sm"`; `aria-describedby` al texto de la propuesta, sin
  texto de la IA en `aria-label`). **Una por una** (RF-92; D-7).
- **Descartar lo pendiente**: confirmación en línea si hay pendientes («¿Descartar {n} propuestas pendientes? Lo ya aceptado se queda en la
  hoja.» [Descartar] [Seguir revisando]); sin pendientes, directo.
- **Al decidir**: la fila pasa a su estado, se anuncia «{id}: {estado}.», el **foco** va al «Aceptar» de la siguiente pendiente o, si no queda,
  al título del resultado (`h3` con `tabindex=-1`). Si cambió el borrador, el panel llama `alAplicar(resumen)` y pide A4 de nuevo. Una decisión
  de `sin_partida` no cambia el borrador: `resumen.rev` queda igual y la página no recarga nada.
- **Aviso** si `sobre_la_hoja_editada` (§3.6).
- **Fuente**: la página prellena la fuente del diálogo de guardado con `fuente_sugerida` solo si está vacía (`P:866`); nunca pisa lo escrito.

### 6.5 Resultado hipotético

`h3` «Resultado si acepta lo pendiente», **calculado por el sistema**:

- **Total ahora**, **Total si acepta todo** y **diferencia** como `{texto, exacto}`: `formatoEsVe(texto)`, `exacto` en `title` y en texto
  `cds--visually-hidden`.
- «Hallazgos del auditor si acepta todo: {n} ({SEVERIDAD}: {k}, …)» (o «ninguno»); «Cambios sin guardar si acepta todo: {n}»; si
  `partidas_sin_apu > 0`: «{n} partida(s) no tienen composición en el catálogo: quedan pendientes y no suman.»
- `disponible=false`: «No se puede calcular el resultado si se aceptara todo: {mensaje}» (`role="status"`).
- Sin pendientes: «Resultado con lo aceptado». Al recalcular se conserva el último valor con «Actualizando…».
- **El front no calcula ni redondea**: ningún `Number`, `parseFloat`, `toFixed` ni `Intl.NumberFormat` en **todo** el directorio `asistente/`.

### 6.6 Estados de carga, error y vacío

| Estado | Qué se ve |
|---|---|
| Leyendo proveedores / sesión | `EsqueletoPagina` «Cargando el asistente» dentro del desplegable |
| Sin proveedores / apagado / sin extra | motivos de A0 en texto; sin formulario |
| Solo lectura | caso 9i; sin formulario |
| `sin_sesion` | formulario |
| `pensando` | progreso (§6.3) |
| `lista` con propuestas | lista + resultado + descartar |
| `lista` sin propuestas | «La IA terminó sin propuestas.» + `mensaje` y `notas` escapadas + formulario para reformular |
| `lista` por tope o cancelada | frase del motivo con tildes (tabla `motivo → texto` en `logica.ts`; motivo desconocido → `mensaje` del motor) |
| **`pregunta`** | aviso `warning` «Pregunta generada por la IA: no escriba contraseñas, claves ni precios.» + texto escapado + «Esta versión del asistente todavía no permite responder. «Seguir sin responder» le dice a la IA que no hay respuesta: conserva lo que ya propuso para que usted lo revise. Si no propuso nada, escriba el pedido de nuevo con el dato que faltaba.» + botones **«Seguir sin responder»** (primario, A7) y «Descartar la sesión» (A6) |
| `error` | por categoría: sin_conexion «No hay conexión con el proveedor de IA.», clave_invalida «La clave de IA fue rechazada: pida al administrador que la revise.», tiempo «El proveedor tardó demasiado: lo ya propuesto se conservó.», componente «Falta el componente del asistente en este equipo: pídalo a quien instaló Sílice.», base «No se pudo leer o escribir el caso. …», otro «El asistente no pudo completar la tarea.»; las propuestas conservadas se listan |
| 409 «ya se guardó» | «Este borrador ya se guardó: abra esa versión para seguir.» |
| 404 del borrador | el aviso «El borrador ya no está» de la página |
| 401 | `alExpirar()` |

### 6.7 Teclado y accesibilidad (D2)

Orden natural; foco visible de Carbon; **Esc no cancela nada**. Al abrir o cerrar el desplegable el foco se queda en su botón. Al terminar la IA
el foco **no se roba** (se anuncia por `role="status"`). Etiquetas visibles; `aria-invalid` + `aria-describedby` en el pedido rechazado. Un solo
`aria-live` por panel. Tamaños de texto sin `px`.

### 6.8 Textos

Títulos: «Asistente de IA: propone, usted decide», «Resultado si acepta lo pendiente», «Propuestas de la IA». Botones: «Proponer», «Cancelar»,
«Aceptar», «Aceptar y editar», «Rechazar», «Descartar lo pendiente», «Seguir sin responder», «Descartar la sesión», «Reintentar». Etiquetas:
«Proveedor», «¿Qué necesita armar? (en sus palabras)», «Lo que se enviará». Lo de la IA: texto como llega.

### 6.9 Qué cambia en `index.tsx`

1. Quitar `<aside aria-label="Asistente de IA" hidden />` y montar `<PanelDelAsistente borrador={…} alAplicar={aplicar} alRecargar={refrescar}
   alHayPendientes={…} />` entre `BotonExcel` y `<ContextoAuditoria.Provider>`.
2. `hayCambios` para `beforeunload` pasa a `hayCambios || asistenteConPendientes`.
3. El diálogo de guardado recibe `fuente_sugerida` solo si su campo está vacío.
4. `Hoja.test.tsx:256` se reescribe.

### 6.10 Estructura de archivos del front

`frontend-desktop/src/paginas/hoja/asistente/`: `PanelDelAsistente.tsx`, `FormularioDelAsistente.tsx`, `ProgresoDeLaIA.tsx`,
`ListaDePropuestas.tsx`, `ResultadoHipotetico.tsx`, `useAsistente.ts`, `logica.ts` (+ `logica.test.ts`: tipos, tabla motivo → texto, categorías,
frases por tipo), `asistente.scss`, `datosDePrueba.ts`, `respuestasDelAsistente.ts` (**ayudante común de los mocks**: `fetch` simulado que
responde A0 y A3 con `sin_sesion`; lo usan las pruebas del asistente y se agrega a los demás archivos de prueba de la hoja, §8). **No** se toca
`src/api/tipos.ts` (cambios ajenos sin confirmar).

---

## 7. Pruebas por capa y criterios de aceptación

### 7.1 Principios

TDD con rojo visto; oráculos a mano desde la clásica (como regla), la ERS, `precios_ia.json` o `core`, nunca del código bajo prueba; `-W error`,
cero omitidas; **ninguna prueba abre la red**. Casos: OF-001 y TI-001 (`tests/fixtures/caso_of001.py`, `caso_ti001.py`, `hoja_en_base.py`,
`hoja_borrador.py`, `sesion_web.py`). La suite completa no se corre en sub-rebanadas.

### 7.2 Backend (ids 4a-B*)

| Id | Qué prueba | Oráculo |
|---|---|---|
| B1 | **identidad de clase**: `asistente.servicio.Borrador is aplicacion.hoja.Borrador`; sin conversión que mantener; si alguna vez difieren, la prueba falla | comparación de objetos; sin importar nada de `ui` (no existe) |
| B2 | **arquitectura**: solo los tres módulos nuevos (más `entrega.py`) importan `asistente` desde `aplicacion/`; solo el puente llama a `servicio` y `orquestador`; `aplicacion/hoja_asistente*.py` no importa `anthropic` | barrido AST |
| B3 | A0 sin clave: serializa y busca la clave de prueba y `sk-ant`; apagado → `activo=false` con el motivo exacto «El asistente esta apagado: lo activa el administrador de la instalacion.»; sin extra → `FALTA_EL_COMPONENTE`; un no disponible con su motivo; `aviso_maprex` con nube y prefijos vacíos y ausente con prefijos o con local | |
| B4 | acceso: `ana` 200; `rita` y `admin` 403; sin sesión 401; clave de API 403; CSRF/Origin en POST; `no-store` en éxito y error | `tests/fixtures/sesion_web.py` |
| B5 | A1: el texto es `primer_mensaje(PEDIDO, borrador_saneado)`; sin precios, nombre del proyecto ni de personas; frontera de 100 000 | cadena construida a mano |
| B6 | A2 feliz: 202 → sondeo → `lista` con 1 propuesta; el borrador no cambia (igualdad y mismo `rev`) | guion `AMBIENTE`; filas `ia_*` esperadas |
| B7 | pedido vacío, de 4 001 caracteres y con `sk-ant-`: 422 sin eco; el de la clave no llama al proveedor ni crea fila `ia_sesiones` | conteo SQL y `recibidos == []` |
| B8 | precondiciones: solo lectura, sin proveedor, desconocido, sin tarifa, sin extra, cliente sin `with_options`, ya hay una petición | textos de §5.4 |
| B9 | concurrencia y ritmo: dos POST simultáneos al mismo borrador → 202 y 409; con `EN_VUELO=2` ocupados, un tercero → 503 con `Retry-After`; la 21.ª en una hora → 429 (reloj inyectado); **el contador es por `usuario_id`: cerrar sesión y abrir otra ficha con la misma cuenta NO lo reinicia** | hilos y barreras, sin `sleep`; **traspaso y liberación única del cupo (arriba)** |
| B10 | plazos: proveedor colgado → `error` categoría `tiempo` con plazos pequeños; propuestas previas conservadas; **otra edición E3 funciona mientras se espera** | |
| B11 | cancelar: DELETE durante `pensando` → 204 y `sin_sesion`; al volver el hilo el resultado no reaparece (testigo); `ia_sesiones.motivo_fin = "cancelado"` (no `error_de_proveedor`); borrador intacto | volcado `ia_*` |
| B12 | ciclo de vida: DELETE del borrador, E11, 8 h, expulsión, `olvidar`, cambio de caso, cierre de sesión → la sesión desaparece y el trabajo se cancela; otra ficha en A2 a A7 → 404; **`aceptadas` sobrevive a descartar la sesión** | reloj inyectado |
| B13 | la sesión nunca está en el borrador: `BorradorVivo` sin campos nuevos, `tamano` y `pickle` iguales; recorrido de la sesión buscando la clave de prueba | |
| B14 | errores del proveedor: `sin_conexion`, `clave_invalida`, `otro` con la clave dentro, `tiempo`, `ImportError`, `SQLAlchemyError` → `error` con la **categoría registrada por la envoltura** (el orquestador la pierde) y texto saneado | la clave no aparece en ninguna respuesta |
| B15 | **`aplicado`** (la regla de la clásica): (a) recién propuesto, `sobre_la_hoja_editada` es falso (comparación inicial de `aplicacion.hoja.Borrador` con `==`); (b) editar a mano (E3 `administracion = 0.20`), aceptar P1 y luego P2: **ambas entran y la edición sobrevive**, `aplicado` queda `None` y `sobre_la_hoja_editada` verdadero tras P1; (c) sin edición, P1 y P2 reconstruyen y `aplicado` es el borrador resultante | OF-001 con total ≈ 2 821,42 (P13 de la hoja) tras la edición; orden P1, P2 |
| B16 | recorrido del JSON de A0 a A7: sin `float`; todo monto es `Monto` | |
| B17 | `pregunta`: guion con `preguntar_al_usuario` → estado `pregunta`; decidir da 409; el texto no se interpreta | |
| B18 | **ningún proveedor real**: sin la costura, `proveedores_de_la_instalacion` y `ProveedorClaude.turno` fallan (prueba negativa) | |
| B19 | aceptar: `rev`+1; fila con `OrigenMedida` `ia` y referencia literal `modelo=claude-opus-5-5; propuesta=P1; proveedor=claude; sesion=N`; partida en `items_base` con `ia:N:P1` y su APU del catálogo. **Ampliada: aceptar una `sin_partida`** deja el borrador igual y `rev` igual, **registra la decisión** (`ia_propuestas.estado = aceptada`, `decidida_por`), la propuesta deja de estar pendiente y la sesión entra en `aceptadas` | construido a mano; OF-001 y TI-001 |
| B20 | rechazar (incluida una `sin_partida`, **y con un `rev` viejo del cliente: no da 409**): borrador idéntico y `rev` igual; `ia_propuestas.estado = rechazada`, `decidida_por = "Nombre <login>"` | volcado `ia_*` |
| B21 | `rev` viejo → 409 y nada decidido ni registrado; doble decisión (también de `sin_partida`) → 409; dependencia → 409; no cabe en la hoja editada → 409; base que falla → 503 sin decisión registrada; **borrador expulsado entre el registro y el reemplazo → 404 y se anota que la decisión quedó registrada (daño solo de auditoría)** | volcado `ia_*` |
| B22 | **hipotético completa composiciones**: una partida propuesta cuyo APU está en el catálogo pero no en `composiciones` no da `CODIGO_PENDIENTE` y su costo suma; `total_si_acepta` es **igual** al total del borrador tras aceptar de verdad (misma partida, misma lista de precios); una partida sin APU en el catálogo cuenta en `partidas_sin_apu` y no suma; `disponible=false` con `HojaInvalida`; `diferencia` exacta en `Decimal`; caché por `(estados, rev)` | **oráculo a mano**: el literal sale de la **memoria OF-001** (`tests/fixtures/memorias/of001.md`), no del código: `total_actual = 2703.86`, y el incremento de la partida = cantidad × precio unitario de la memoria **con sus indirectos** (administración y utilidad, como en el cierre de partida), escrito en la prueba como literal; además `total_si_acepta` **==** el total que da el borrador tras aceptar de verdad (sin atajos) |
| B23 | responsable: un campo `usuario`/`responsable` en el cuerpo → 422 sin eco; la decisión lleva la cuenta | |
| B24 | trazabilidad e2e: aceptar y guardar por S1 → versión con `esp_origenes` tipo `ia`, `RegistroCambio.responsable` = la cuenta, cadena íntegra, `ia_sesiones.version_guardada` = la nueva (gancho D-3), `anexo_ia` incluye la sesión; si el gancho falla, la versión sigue guardada y S1 trae `avisos`. **B24b: tras aceptar y «Descartar lo pendiente» (o reemplazar la sesión), `fuente_sugerida` sigue citando todas las sesiones aceptadas** (también en `sin_sesion`) | patrón de `tests/unit/test_api_hoja_guardado.py` |
| B25 | tope de costo: el turno exacto en que el costo alcanza el tope (a mano con la tarifa), `motivo = tope_de_costo`, propuestas conservadas; turnos 12 y llamadas 60 en la frontera | RF-94 |
| B26 | **privacidad e2e**: lo que recibe el proveedor en todos los turnos no contiene ninguna cifra de precio ni total de OF-001 (lista literal), ni los nombres del proyecto, de la empresa ni `ana`, ni la clave; sí el alias `P1`. **Caso MaPreX**: `prefijos_de_maprex = ("ELE-",)`, proveedor `claude` (nube) y un `items_base` con `ELE-001` ("descripción de prueba") y `AF-SALIDA`: el proveedor recibe `ELE-001` con su unidad y cantidad **y la descripción vacía**, y recibe la descripción de `AF-SALIDA`; con proveedor local las dos viajan; con prefijos vacíos y nube la descripción de `ELE-001` viaja (y A0 avisa); tras aceptar una propuesta, la descripción real de `ELE-001` en el borrador **se conserva** (`del_motor`); una partida MaPreX aceptada antes conserva la descripción del catálogo. **Caso exacto de N1**: nube, prefijos `("ELE-",)`, el guion busca `ELE-001`, llama `proponer_partida` y luego `consultar_borrador` y `pedir_informe_auditoria`: lo que recibe el proveedor **en ese turno y en los siguientes (el historial reenviado)** no contiene la descripción real de `ELE-001` en ninguna parte (se busca la cadena literal en todos los `recibidos`), y tras aceptar la propuesta el `ItemComputo` del borrador **sí la conserva** (restaurada por código desde el catálogo real); con proveedor local la descripción viaja en todos esos envíos | lista literal a mano |
| B27 | la clave de IA nunca aparece en la base, `ia_*`, registros (`caplog`), el 422 ni `docs/api.json` | RNF-18 c |
| B28 | `hoja_edicion.cambiar`: las siete ediciones y `hoja_plano.fusionar` pasan sin cambios; un fallo en `antes_de_reemplazar` no cambia el borrador; **sin cambio de borrador, `antes_de_reemplazar` se llama y `rev` no sube** | |
| B29 | **apagado y demonio**: `apagar()` vuelve en < 1 s con un turno bloqueado y fija `cancelado`; un subproceso que arranca un trabajo bloqueado y termina, sale sin esperarlo; después de `apagar()` un POST da 503 | |
| B30 | **preguntas**: tras una pregunta, «Seguir sin responder» (A7) → `lista` con motivo `cancelado`, **`ia_propuestas` escritas, `ia_sesiones.fin` y `motivo_fin = "cancelado"`**, las propuestas hechas antes quedan decidibles; DELETE sobre `pregunta` también cierra `ia_sesiones`; proponer de nuevo con una `pregunta` previa la cierra; A7 sin pregunta → 409 | volcado `ia_*` |
| B31 | categorías y retiradas: la categoría `clave_invalida` llega al estado aunque el orquestador la pierda; la cancelación cierra con `cancelado`; una propuesta que la IA retira con `retirar_propuesta` sale con `retirada_por_la_ia = true` y una rechazada por la persona con `false` | |
| B32 | **bloqueos**: estrés con muchas decisiones, ediciones, descartes y barridos por vencimiento en paralelo (sin `sleep`, con barreras y tiempo límite) sin abrazo mortal y respetando el orden `vivo.cerrojo` → sesión; el aviso `al_quitar` no toma `vivo.cerrojo`; publicación con testigo: un trabajo cancelado y uno nuevo a la vez no se pisan | |
| B33 | cliente acotado: con un doble del SDK que registre `with_options`, el puente lo llama con `timeout=PLAZO_POR_TURNO` y `max_retries=0` y la clave no queda en ningún atributo propio; un proveedor sin `with_options` se rechaza (409) | |

### 7.3 Paridad con el motor directo (4a-5)

Contra **el motor llamado directamente sobre `aplicacion.hoja.Borrador`** (lo que la clásica hacía por dentro), sin `ui` ni `AppTest`. Mismo
guion de `ProveedorGuionado`, mismo caso:

- Mismas propuestas (`id`, `tipo`, `clave`, `descripcion` = `servicio.descripcion`, `supuestos`) y orden.
- Mismo `resumen_hipotetico` que el motor sobre el borrador **con composiciones completadas** (el cambio de §5.5 es una diferencia deliberada
  respecto de la clásica; la prueba compara contra el cálculo corregido y, aparte, comprueba con un caso sin partidas nuevas que coincide con el
  de la clásica).
- Mismo borrador al aceptar P1 y P2 en las dos rutas, **con el orden de los ítems IA igual** (orden de aceptación), y mismas filas `ia_*`
  (`registro.volcado`).
- Mismos mensajes: igualdad de cadena para lo que sale del motor; igualdad tras `normalizar_texto` para lo que compone la capa nueva.

### 7.4 Frontend (ids 4a-F*)

| Id | Qué prueba |
|---|---|
| F1 | formulario: preselecciona `por_defecto`; los no disponibles son texto; «Proponer» deshabilitado sin pedido, proveedor, tarifa y en solo lectura; el contador (con `formatoEsVe`) y `maxLength` |
| F2 | destino, estimación («orientativa; el tope real es el de sesión») y tope se recomponen al cambiar de proveedor sin otra petición; los avisos de estimación sobre el tope y de MaPreX salen del servidor |
| F3 | «Lo que se enviará»: pide A1 solo abierto y con 600 ms; muestra `truncada` y el total |
| F4 | proponer: `fetch` simulado → 202 → sondeo con relojes falsos → `lista`; pausa con pestaña oculta; tres fallos detienen el sondeo; 401 → `alExpirar`; unmount limpia el temporizador |
| F5 | `role="status"` siempre montado; anuncia inicio, cambio de turno (≤ 1 cada 10 s) y fin; no anuncia el sondeo ni los segundos |
| F6 | cancelar: DELETE y vuelve al formulario sin esperar |
| F7 | lista: botones solo en `pendiente`; estado como texto e ícono (incluida «retirada por la IA»); **la frase de «aceptada y editar» según el tipo** (ambiente/fuente/punto → Espacio y metrajes; partida → Presupuesto; recorrido propuesto → nada que editar; sin_partida → nada); foco a la siguiente pendiente o al título del resultado; anuncio |
| F8 | decisiones: aceptar llama `alAplicar(resumen)` con el `rev` enviado; 409 por `rev` → recarga; 409 «ya no está pendiente»; 409 por hoja editada muestra el texto del servidor; **una decisión de `sin_partida` no recarga la página** |
| F9 | descartar lo pendiente: confirmación en línea con pendientes; directo sin ellas; lo aceptado se queda |
| F10 | resultado hipotético: `formatoEsVe` + `exacto` en `title` y texto oculto; diferencia con signo; `partidas_sin_apu`; `disponible=false`; **prueba estática de que ningún archivo de `asistente/` (contador incluido) usa `Number(`, `parseFloat`, `toFixed` ni `Intl.NumberFormat`** |
| F11 | texto de la IA escapado: `<img src=x onerror=…>`, `[x](http://…)` y `![x](http://…)` se ven como texto, sin nodos `img` ni `a`; la pregunta lleva el rótulo |
| F12 | `pregunta` (con **«Seguir sin responder»** que llama A7 y muestra la lista; «Descartar la sesión»), `error` por categoría, `lista` sin propuestas, por tope y cancelada: texto con tildes de la tabla; todo `MotivoFin` tiene entrada (lista literal de los once valores) |
| F13 | persistencia: `localStorage` y `sessionStorage` sin pedido, propuestas ni claves; ninguna petición contiene la clave |
| F14 | F5 / retomar: al montar se lee A3 y se recupera la sesión; **un 500 o 404 de A3 y de A0 no pinta `role="alert"` y no cambia el número de alertas de la página** (el panel muestra un `role="status"` con «Reintentar» o nada) |
| F15 | la página: con propuestas pendientes `beforeunload` avisa; la `fuente_sugerida` prellena solo un campo vacío **y sigue disponible tras «Descartar lo pendiente»**; el `aside` ya no está oculto ni vacío y su `h2` está fuera de cualquier botón de acordeón (`h2 > button`, sin `h2` dentro de `button`) |
| F16 | estilos (como `estilosPlano.test.ts`): sin `px` en tamaños de texto, `min-inline-size: 0`, `overflow-wrap: anywhere`, `auto-fit/minmax(min(100%, …))` |
| F17 | **regresión**: los archivos de prueba de la hoja que montan la página (`Hoja`, `Edicion`, `Edicion3c2`, `EdicionApu`, `Guardar`, `HojaExcel`, `PlanoEnHoja`, `Retomar`, `Versiones`, `Vistas`, `Vistas3b3`) siguen pasando con el panel montado, usando el ayudante común `respuestasDelAsistente` |

### 7.5 Auditoría visual (4a-6)

Con el guion simulado: 1366×768 y 1056 px, letra Normal, Grande y Muy grande: `scrollWidth <= clientWidth` en cada estado (`sin_sesion`,
`pensando`, `lista` con 3 y 30 propuestas, `error`, `pregunta`, vacío); solo teclado; foco visible; un `h1`; el cuadro de «Lo que se enviará»
alcanzable; el desplegable no empuja las pestañas fuera de pantalla.

### 7.6 Criterios de aceptación (P-n)

(No son los P1 a P39 de la hoja.)

| Id | Criterio | Oráculo | Sub-rebanada |
|---|---|---|---|
| P-1 | A0 lista proveedores sin datos secretos, con los motivos y con el aviso de MaPreX cuando corresponde | B3 | 4a-1 |
| P-2 | La estimación de Opus 5.5 es **1,2144 USD exactos** (texto «1.21») y el tope 2.00 | (10 000×4 + 3 000×20 + 6 000×0,20)/10⁶ = 0,1012; ×12 | 4a-1 |
| P-3 | La vista previa es exactamente `primer_mensaje` de lo que de verdad viaja (saneado), sin precios, montos, nombre del proyecto ni personas | B5 | 4a-1 |
| P-4 | Proponer con guion no cambia el borrador (igualdad, mismo `rev`) y deja las filas `ia_*` esperadas | B6 | 4a-1 |
| P-5 | Pedido vacío, largo o con clave: 422 sin eco; el de la clave no llega al proveedor ni a la base | B7 | 4a-1 |
| P-6 | Solo lectura, sin proveedor, sin tarifa, sin extra, sin plazos y «ya en curso» dan su 409 | B8 | 4a-1 |
| P-7 | Una petición por borrador, cupo (503), ritmo por `usuario_id` (429) | B9 | 4a-1 |
| P-8 | Plazo vencido y cancelación terminan la sesión sin perder lo propuesto ni bloquear las ediciones; cancelar cierra con `cancelado` | B10, B11 | 4a-1 |
| P-9 | La sesión muere con el borrador por todos los caminos y es invisible a otra ficha | B12 | 4a-1 |
| P-10 | La sesión nunca está dentro del borrador y la clave nunca está en la sesión | B13, B27 | 4a-1 |
| P-11 | Los fallos del proveedor (con su categoría) y de la base llegan como `error`, saneados | B14, B31 | 4a-1 |
| P-12 | Aceptar entra al borrador con origen IA, sube `rev`, completa el APU y es todo o nada; **aceptar o rechazar una `sin_partida` se registra sin cambiar el borrador** | B19, B20, B21 | 4a-2 |
| P-13 | Rechazar deja el borrador idéntico; la decisión queda con la cuenta como autora | B20, B23 | 4a-2 |
| P-14 | Con la hoja editada a mano, **la edición sobrevive a decidir P1 y P2**; si no cabe, 409 sin decidir | B15, B21 | 4a-2 |
| P-15 | El hipotético de OF-001 da `total_actual = 2703.86` y `total_si_acepta` **igual al total tras aceptar de verdad**, con la diferencia exacta a mano; sin APU en el catálogo cuenta y no suma | B22 | 4a-2 |
| P-16 | Guardar tras aceptar deja versión con origen IA, responsable humano, cadena íntegra, sesión marcada y `ia.json`; la fuente sigue citando a la IA tras descartar | B24, B24b | 4a-2 |
| P-17 | El tope de costo detiene la sesión en el turno exacto y conserva lo propuesto | B25 | 4a-2 |
| P-18 | Paridad con el motor directo en OF-001 y TI-001 | §7.3 | 4a-5 |
| P-19 | Lo que recibe el proveedor cumple la lista blanca **y la regla P7 con prefijos configurados**, incluidos los ítems que el propio motor crea al proponer y `pedir_informe_auditoria` (con las salvedades de §4.1: nombres libres, pedido y heurística de secretos) | B26 | 4a-5 |
| P-20 | `git diff <base>..HEAD -- asistente core` vacío; el resultado de `test_experimento_congelado_vigente.py` no cambia | `git diff` | todas |
| P-21 | Formulario, progreso y errores accesibles y completos; un fallo de A0/A3 no pinta `alert` | F1 a F6, F12, F14 | 4a-3 |
| P-22 | Lista, decisiones, foco y anuncios | F7 a F9, F11 | 4a-4 |
| P-23 | Montos en es-VE con el exacto accesible; ni `Number` ni `parseFloat` ni `toFixed` ni `Intl.NumberFormat` | F10 | 4a-4 |
| P-24 | Nada del asistente en `localStorage`/`sessionStorage`; la clave nunca llega al navegador | F13, B27 | 4a-3/4 |
| P-25 | F5 recupera la sesión; salir con pendientes avisa; la fuente se prellena | F14, F15 | 4a-4 |
| P-26 | 1366×768 y 1056 px, letra Normal/Grande/Muy grande, sin desplazamiento horizontal; solo teclado | §7.5 | 4a-6 |
| P-27 | Ninguna prueba abre la red; la prueba real espera la autorización | B18, D-2 | 4a-7 |
| P-28 | El apagado no espera a los hilos de la IA | B29 | 4a-1 |
| P-29 | Una pregunta de la IA no deja la sesión abierta ni sin salida: «Seguir sin responder» cierra `ia_sesiones` y deja decidir | B30, F12 | 4a-1/4a-3 |
| P-30 | Los demás archivos de prueba de la hoja siguen en verde con el panel montado | F17 | 4a-3 |
| P-31 | Sin abrazos mortales entre borradores, sesión y avisos de salida | B32 | 4a-1/4a-2 |

---

## 8. Sub-rebanadas, dependencias y paralelismo

| Sub-rebanada | Hace | Archivos suyos | Depende de | Pruebas |
|---|---|---|---|---|
| **4a-1** backend: fachada, proveedores, previa, proponer, estado, descartar, pregunta | `hoja_asistente_puente.py` (fachada, saneo P7, cliente acotado), `hoja_asistente.py` (registro, `aceptadas`, ciclo de vida, `al_quitar`), `hoja_asistente_trabajo.py` (hilos demonio, cupo, ritmo, plazos, `apagar`), `hoja_edicion.cambiar` público con sus **8** consumidores, rutas A0 a A3, A6, A7; fixture `asistente_guiones.py` | `aplicacion/hoja_asistente*.py`, `aplicacion/hoja_edicion.py` (solo `cambiar` y sus 7 llamadas), **`aplicacion/hoja_plano.py` (una línea)**, `api/rutas/hoja_asistente.py`, `api/esquemas_hoja_asistente.py`, `tests/fixtures/asistente_guiones.py`, `tests/unit/test_aplicacion_hoja_asistente*.py`, `tests/unit/test_api_hoja_asistente*.py`, `docs/bitacora/2026-10-2x-hoja-4a1-*` | **el retiro de Streamlit fusionado** (`f2b3c5e5`, `1e1f976e`) y este diseño aprobado | B1 a B14, B16 a B18, B27 a B33; P-1 a P-11, P-28, P-29, P-31 |
| **4a-2** backend: decidir, hipotético, gancho de guardado | A4 y A5, `decidir` de dos fases con la regla de `aplicado`, `sin_partida`, hipotético con composiciones completadas, `fuente_sugerida` de `aceptadas`, `hoja_guardado.al_guardar` y `avisos`, y en `hoja_vista` la comparación pública | mismos archivos + `aplicacion/hoja_guardado.py` + **`aplicacion/hoja_vista.py`** (dos líneas) | 4a-1 | B15, B19 a B25 (incluida B24b); P-12 a P-17 |
| **4a-3** front: formulario, progreso y mocks | `useAsistente`, `PanelDelAsistente`, `FormularioDelAsistente`, `ProgresoDeLaIA`, montaje en `index.tsx`, `respuestasDelAsistente.ts`, **actualización de los mocks de `Hoja.test.tsx`, `Edicion.test.tsx`, `Edicion3c2.test.tsx`, `EdicionApu.test.tsx`, `Guardar.test.tsx`, `HojaExcel.test.tsx`, `PlanoEnHoja.test.tsx`, `Retomar.test.tsx`, `Versiones.test.tsx`, `Vistas.test.tsx`, `Vistas3b3.test.tsx`** | `frontend-desktop/src/paginas/hoja/asistente/**`, `index.tsx`, esos 11 archivos de prueba | solo el contrato de §5 (`fetch` simulado); **puede empezar antes del retiro** | F1 a F6, F12 (parte), F13, F14, F16, F17; P-21, P-24, P-29, P-30 |
| **4a-4** front: propuestas, decisiones, hipotético | `ListaDePropuestas`, `ResultadoHipotetico`, foco, anuncios, `beforeunload`, fuente sugerida | mismo directorio + `index.tsx` | 4a-3 (y el contrato de A4/A5) | F7 a F11, F12 (resto), F15; P-22, P-23, P-25 |
| **4a-5** paridad y privacidad e2e | las pruebas de §7.3 y B26 con el servidor real y el guion | `tests/unit/test_aplicacion_hoja_asistente_paridad.py`, `tests/unit/test_api_hoja_asistente_privacidad.py` | 4a-2 | P-18, P-19, P-20 |
| **4a-6** auditoría visual y registro | `scripts/auditoria_visual_asistente.py`, medición con navegador, bitácora `2026-10-2x-hoja-4a-paridad.md`; **primera prueba de integración real front-backend** | `scripts/auditoria_visual_asistente.py`, `docs/bitacora/**` | 4a-4 y 4a-5 | P-26 |
| **4a-7** prueba real | una sesión real con el tope que autorice Eugenio sobre OF-001; se anota el costo real | `scripts/prueba_real_asistente.py` (ya existe) | **D-2 (BLOQUEADA)** | P-27 |

**Orden y paralelismo**

```
(retiro fusionado) ──▶ 4a-1 ──▶ 4a-2 ──▶ 4a-5 ──────────┐
                                                           ├─▶ 4a-6 ─▶ (4a-7 si D-2)
4a-3 ──▶ 4a-4 ──────────────────────────────────────────┘
```

- **4a-3 corre en paralelo con 4a-1 y 4a-2** porque trabaja contra el contrato de §5 con `fetch` simulado. Eso **no** prueba que el front y el
  servidor coincidan: lo prueba 4a-6. Si 4a-1 o 4a-2 desvían el contrato, lo corrigen en `docs/bitacora/…-hoja-4a-contrato-rutas.md` y avisan al
  front. 4a-1 no puede empezar antes del retiro; 4a-3 sí.
- 4a-2 es secuencial con 4a-1 (mismo módulo); lo hace el mismo implementador. 4a-4 secuencial con 4a-3 (mismo directorio); **4a-5 en paralelo con 4a-4**.
- Un solo árbol: cada agente toca solo sus carpetas; `index.tsx` lo editan 4a-3 y luego 4a-4 en orden. 4a-3 modifica 11 archivos de prueba que son
  de la hoja: ningún otro agente trabaja en ellos (zoom e indicadores están en `src/visor` y `src/indicadores`).
- Cada sub-rebanada pasa implementador → árbitro antes de empezar la siguiente que dependa de ella.

---

## 9. Etapas 2 y 3: ganchos que deja la etapa 1

**Etapa 2 (responder y cierre)**

| Gancho | Dónde queda hecho en la etapa 1 |
|---|---|
| Estado `pregunta` | en la máquina de estados, `AsistenteEstado.pregunta` y el panel (con «Seguir sin responder») |
| Continuación pausada | `SesionDeAsistente.resultado.continuacion`; `servicio.responder(sesion, texto, registro, proveedor=…)` ya existe y suelta el proveedor |
| Ruta de respuesta | `POST …/asistente/respuesta {texto}` (el `null` ya lo hace A7): trabajo en segundo plano con las mismas reglas de plazo, cancelación y cupo; usa el **proveedor vigente por nombre** (si ya no está o cambió el modelo, la sesión se cancela con el texto de `P:910`); la respuesta con una clave se rechaza (`contiene_secreto`, ya en el orquestador) |
| Cierre al guardar | `al_guardar` y `aceptadas` (D-3); la etapa 2 agrega solo el mensaje en pantalla |
| Número de sesión | `AsistenteEstado.sesion` |

**Etapa 3 (historial y costos)**: los datos ya están en `ia_*` (sesión, turnos con uso y costo, llamadas, propuestas, decisiones, versión
guardada); lectura `GET /v1/hoja/asistente/historial?proyecto=` y `…/costos` (clave de API o sesión con `EDITAR_HOJA`, solo lectura); tope
acumulado (D-6) con `ia_turnos` comprobado en A2 antes de reservar cupo; las sesiones huérfanas por reinicio (`fin` vacío) se señalan allí.

---

## 10. Riesgos

| # | Riesgo | Efecto | Mitigación | Estado |
|---|---|---|---|---|
| R-A1 | **Orden de fusión**: construir 4a-1 antes del retiro | habría dos clases `Borrador` y la capa sin puente de conversión | 4a-1 no empieza hasta que `f2b3c5e5` y `1e1f976e` estén en la rama; B1 falla si las clases difieren | mitigado |
| R-A2 | **Turno colgado** | cupo ocupado, cobro no registrado | cliente acotado a 120 s sin reintentos, hilos demonio, cupo por semáforo, apagado que no espera; Ollama/dobles solo con la envoltura | declarado; **un `read` de 120 s sin reintentos puede cortar un turno legítimo de Opus con razonamiento largo: se paga y se pierde, y la sesión termina en `error`/`tiempo` conservando lo propuesto. El valor se mide en 4a-6/4a-7 sin cambiar el diseño** |
| R-A3 | **Gasto**: una sesión consume hasta el tope aunque la persona se vaya | USD | tope por sesión, estimación, cancelar, ritmo, tope acumulado en etapa 3 | declarado |
| R-A4 | **Pérdida de la sesión** al salir o reiniciar | propuestas pagadas y no decididas | `beforeunload`; aviso; el borrador con aceptadas se conserva con su registro; `ia_*` queda | declarado |
| R-A5 | **Texto ajeno** en pantalla | exfiltración por renderizado | solo texto escapado, sin `a`/`img`; F11 | mitigado |
| R-A6 | **El pedido y los nombres llevan datos personales, nombres de empresa o claves no detectadas** | fuga al proveedor, a la base y al paquete | rechazo de las claves conocidas; advertencia permanente; vista previa del texto exacto; **sin filtro de nombres y con detección heurística** | **parcial, declarado** |
| R-A7 | **Hueco de `ia.json`** | trazabilidad incompleta | gancho de D-3 | abierto hasta D-3 |
| R-A8 | **Dos verdades** (pegamento reescrito) | resultados distintos | paridad con el motor directo (§7.3) | declarado |
| R-A9 | **Decisión registrada sin su efecto** | auditoría inconsistente | dos fases; B21; si el borrador desaparece entre medias el daño es solo de auditoría y se anota | mitigado |
| R-A10 | **Carga de la API** | latencia | cupo 2, sondeo en memoria, sesión propia del trabajo | por medir (4a-6) |
| R-A11 | **El congelado** | RS-9 | 0 bytes en `asistente/` y `core/` (P-20); el cliente acotado usa dos atributos privados de `ProveedorClaude` sin editarla | mitigado |
| R-A12 | **Guardias de arquitectura** | CI en rojo si se olvida enmendarlas | texto exacto en §12 | abierto |
| R-A13 | **Ollama en pausa (RS-8)**: `disponible()` pregunta a la red local | A0 lento (≤ 5 s) | solo A0 lo hace | declarado |
| R-A14 | **Decidir con la hoja guardada** | decisiones sobre un borrador cerrado | 409 | mitigado |
| R-A15 | **Varias pestañas** sobre el mismo borrador | lecturas repetidas | lectura barata; `rev` protege escrituras | declarado |
| R-A16 | **Privados del proveedor**: `_crear_cliente`/`_cliente` pueden cambiar | el cliente deja de acotarse | B33 y el 409 «no admite plazos» (falla cerrado) | mitigado |
| R-A17 | **Bloqueos**: avisos de salida dentro de cerrojos ajenos | abrazo mortal | orden fijo y avisos sin `vivo.cerrojo`; B32 | mitigado |
| R-A18 | **Costo mostrado** ≠ factura (modelo de respaldo) | sorpresa | se rotula «estimado» | declarado |

---

## 11. Decisiones abiertas (recomendación conservadora y reversible)

| Id | Decisión | Quién | Recomendación | Si se elige otra cosa |
|---|---|---|---|---|
| **D-1** | **Resuelta por ruling del orquestador:** primero el retiro de Streamlit (F7 repuntó `asistente/*` a `aplicacion.hoja`, F8 borró `ui/`), después 4a. La opción **R** de la ronda 1 ya está construida allá; la capa nueva no convierte borradores. Se pide a Eugenio **confirmar el orden de fusión** | Eugenio | confirmar | si 4a fuera antes del retiro habría que reintroducir la conversión de clases (la ronda 1 de este documento la describía) |
| **D-2** | Autorización de gasto para la **prueba real** (4a-7) y para cualquier demostración con un proveedor real | Eugenio | **No autorizar todavía**; cuando se autorice, tope explícito (por ejemplo ≤ 3 USD), una sola sesión sobre OF-001 y el costo real anotado | 4a-7 se adelanta; el resto no cambia |
| **D-3** | **Adelantar el cierre de sesión al guardar** (solo servidor, sin pantalla) a la etapa 1 para no dejar versiones con origen IA cuya sesión no sale en `ia.json` | Eugenio | **Sí** (~20 líneas en `hoja_guardado.py`) | No: el panel debe avisar «No guarde versiones con propuestas de la IA hasta la etapa 2» y la ERS declara el hueco |
| **D-4** | Topes y plazos supuestos: `EN_VUELO = 2`, 20 por hora por `usuario_id`, `PLAZO_POR_TURNO = 120 s`, `PLAZO_TOTAL = 300 s`, pedido ≤ 4 000 caracteres, sondeo cada 2 s, tope de fábrica 2 USD | Eugenio | adoptarlos como supuestos y ajustarlos con 4a-6 y la prueba real (en particular `PLAZO_POR_TURNO = 120 s`: un turno legítimo de Opus puede tardar más; cortarlo se paga y se pierde) | cambiar números en `hoja_asistente_trabajo.py` y `api/esquemas_hoja_asistente.py` |
| **D-5** | Plazo real del cliente de Claude. **Ya no requiere editar `claude.py`:** la capa nueva inyecta un cliente acotado (`with_options(timeout=…, max_retries=0)`) sobre dos atributos privados del proveedor | Eugenio solo si prefiere editar el archivo congelado | dejarlo así; si el SDK no ofrece `with_options` la propuesta falla cerrado (409) | editar `claude.py` y re-congelar |
| **D-6** | Tope de costo **acumulado** por instalación | Eugenio | etapa 3, leyendo `ia_turnos` | adelantarlo: consulta en A2 y campo en la configuración |
| **D-7** | ¿«Aceptar todas»? | Eugenio | **No** (RF-92: una por una) | botón con confirmación que llame A5 en orden |
| **D-8** | ¿Qué prefijos de código son de MaPreX en esta instalación (`prefijos_de_maprex`, vacío de fábrica)? Mientras estén vacíos la regla P7 no protege nada y el panel avisa | Eugenio / administrador | que el administrador los configure antes de usar el asistente con partidas MaPreX en la nube | dejarlos vacíos y aceptar que las descripciones viajan |

Decisiones de ingeniería ya tomadas: sesión atada al borrador y no dentro de él; trabajo en segundo plano con hilos demonio y sondeo;
operación `decidir` propia en dos fases con la regla `aplicado` de la clásica; `sin_partida` se registra sin cambiar `rev` y cuenta en
`aceptadas`; acceso por `EDITAR_HOJA` solo con cuenta; hipotético que completa composiciones; copia saneada para P7; «Seguir sin responder»;
desplegable propio con `h2 > button`; lista y no tabla; citas visibles; un fallo del panel no pinta `alert`.

### 11.1 Diferencias deliberadas con la clásica

| # | Diferencia | Motivo |
|---|---|---|
| DV-IA-1 | La llamada es en segundo plano con progreso y cancelación | no ocupar un hilo de la API minutos |
| DV-IA-2 | Pedido ≤ 4 000 caracteres y rechazo si parece llevar una clave conocida | §1.6 |
| DV-IA-3 | Se muestran las citas del pedido | RF-91 |
| DV-IA-4 | El hipotético trae total actual, diferencia exacta, cambios y **completa composiciones** | pedido de Eugenio; la clásica subestimaba una partida nueva |
| DV-IA-5 | La decisión es de dos fases | la clásica podía registrar y fallar al aplicar |
| DV-IA-6 | La sesión se recupera tras recargar | el borrador vive en el servidor |
| DV-IA-7 | Una pregunta de la IA no se responde (etapa 2) pero tiene salida: «Seguir sin responder» | decisión de etapas; §3.4 |
| DV-IA-8 | Mensajes compuestos por la capa nueva con tildes; los del motor, tal cual | misma regla que D-3 de la hoja |
| DV-IA-9 | Los motivos de las sesiones detenidas usan una tabla con tildes | los del motor están congelados sin tildes |
| DV-IA-10 | Confirmación en línea al descartar pendientes | las propuestas costaron dinero |
| DV-IA-11 | La regla P7 de MaPreX se aplica también a los `items_base` y a los ítems que el motor crea al proponer (catálogo envuelto); la clásica solo la aplicaba a las respuestas de las herramientas de catálogo | §1.8, §4.1 |
| DV-IA-12 | «retirada por la IA» se distingue de «rechazada» | §1.9-3 |
| DV-IA-13 | La fuente sugerida se arma con todas las sesiones aceptadas | la clásica solo con la vigente |

---

## 12. Texto exacto para los archivos compartidos (lo aplica el orquestador, contra el estado posterior a F7/F8)

**Antes de integrar 4a-1**

- `tests/unit/test_arquitectura_asistente.py` (ya reescrito por F7): `IMPORTAN_ASISTENTE_APLICACION` pasa a
  `{"aplicacion/entrega.py", "aplicacion/hoja_asistente.py", "aplicacion/hoja_asistente_puente.py", "aplicacion/hoja_asistente_trabajo.py"}`
  (la prueba `test_aplicacion_entrega_solo_importa_el_registro_del_asistente` compara **igualdad** con los importadores reales, así que sin esto
  falla). Se **agrega** una prueba hermana: (1) `entrega.py` sigue limitado a `asistente.registro`; (2) `hoja_asistente_puente.py` es el único que
  importa `asistente.servicio` y `asistente.orquestador`; (3) `hoja_asistente.py` y `hoja_asistente_trabajo.py` importan solo de `asistente`:
  `catalogo`, `clave`, `configuracion`, `instalacion`, `registro`, `tarifas` y `proveedores.base`; (4) ninguno importa `anthropic` ni `keyring`
  (ya lo impone `PAQUETES_DE_TERCEROS`).
- `tests/unit/test_arquitectura.py` (ya reescrito por F7/F8: sin reglas de `ui`): **sin cambios necesarios**. La subprueba de la ronda 1 sobre
  carga perezosa se retira del diseño (ya no hay `ui`). Si hiciera falta agregar alguna prueba allí, va **al final** del archivo, para no
  desplazar las anclas que citan los documentos.

**Al aprobar cada sub-rebanada**

- `api/main.py`: añadir `hoja_asistente` a `from api.rutas import (...)` y, tras `hoja_plano`:
  `# Migracion final (T10 · 4a): asistente de IA de la hoja (A0 a A7), solo con sesion`
  `app.include_router(hoja_asistente.router)`.
  **Apagado** (hoy `api/main.py` no tiene `lifespan`; `app = FastAPI(` en la línea 63): definir antes `@asynccontextmanager async def _vida(_app):
  yield; hoja_asistente_trabajo.apagar()` y pasar `lifespan=_vida` a `FastAPI(...)`, con `from aplicacion import hoja_asistente_trabajo`.
- `tests/unit/test_api_acceso_por_ruta.py`: una fila por ruta A0 a A7 («solo sesión con `editar_hoja`») y la comprobación de que `rita`, `admin` y
  la clave de API reciben 403.
- `CHANGELOG.md`, una línea por cambio: «Asistente de IA en la hoja de la interfaz nueva, etapa 1: `/v1/hoja/asistente/proveedores` y
  `/v1/hoja/borradores/{id}/asistente` (previa, proponer en segundo plano, estado, decidir cada propuesta, resultado hipotético, seguir sin
  responder, descartar); `aplicacion/hoja_asistente*.py` nuevos; `asistente/` y `core/` sin cambios.» y, al cerrar 4a-2, «El guardado de la hoja
  anota la sesión del asistente en el registro `ia_*` (`avisos` en la respuesta).»
- `docs/api.json`: regenerar con `scripts/exportar_openapi.py` en cada rebanada de backend.
- `docs/ERS.md` (numeración **propuesta**, la confirma el orquestador): RF-156 *UC-09 en la interfaz nueva*; RF-157 *Gasto del asistente*
  (estimación orientativa, tope por sesión, plazo, cancelación, una petición por borrador, cupo, ritmo); RF-158 *Privacidad del asistente en la
  interfaz nueva* (la clave nunca llega al navegador, pedido con clave rechazado, vista previa exacta, regla P7 con copia saneada y sus límites
  declarados); RF-159 *Trazabilidad del asistente* (origen «propuesta de IA», decisión a nombre de la cuenta, sesión anotada al guardar). Anotar
  que UC-09 se cubre también en la interfaz nueva al cerrar 4a-4.
- `frontend-desktop/src/shell/rutas.ts`: **no cambia**.

---

## 13. Lo que no pude determinar

1. Los números del SDK (`DEFAULT_TIMEOUT`, 2 reintentos) y que `with_options(timeout=120, max_retries=0)` devuelve un cliente con `timeout=120` y
   `max_retries=0` los **verificó el coordinador con `anthropic` 1.17**; yo no los medí. B33 lo sigue comprobando con un doble y 4a-1 con el SDK instalado.
   Límite conocido de la fuente sugerida: se corta a 300 caracteres (el tope de S1) y con muchas sesiones aceptadas **pierde la cola**; se mantienen
   primero las sesiones más antiguas y la persona la puede reescribir.
2. Si `ProveedorOllama.disponible()` hace la comprobación de versión por HTTP en cada llamada (deducido de `ollama_local.py:149`, no probado).
3. El comportamiento de `exigir_clave_o_sesion` con CSRF y `Origin`: lo tomo del diseño de la hoja y de `api/rutas/hoja.py`; no abrí `api/sesion_web.py`.
4. El tiempo real de A4 (completar composiciones + R17 + `elaborar`) con cientos de puntos: RNF-11 midió 0,125 s sin R17. Lo mide 4a-2.
5. Si 64 propuestas en pantalla son manejables con letra Muy grande: 4a-6.
6. Si el proveedor cobra un turno cuyo hilo se abandonó (no lo verifiqué).
7. Si `ml.normalization.proponedor` puede cargarse en un hilo de trabajo en este equipo (4a-1; `CatalogoDeLaBase` trae la búsqueda por palabras como respaldo).
8. Que el renglón de una partida IA (`items_base`) aparece en la pestaña «Presupuesto» y su cantidad es editable (F7 lo comprueba; lo deduzco de
   `claves_de_items`, no lo ejecuté).
9. Del retiro leí `asistente/*` de la rama, las guardias y los fixtures citados; no leí el resto de sus 72 commits ni sus bitácoras salvo los títulos.
10. Que `orquestador.py` conserve el estado `RECHAZADA` de una propuesta retirada en `resultado.propuestas` (lo leí en `_resultado`: `propuestas=tuple(self.pendientes.propuestas)`);
    B31 lo fija.

---

## 14. Registro de la ronda 2 (qué cambió por hallazgo)

| # | Severidad | Hallazgo | Dónde quedó el cambio de texto | Prueba nombrada (§7) | Sub-rebanada (§8) |
|---|---|---|---|---|---|
| 1 | MAYOR | `sin_partida` no cambia el borrador y `_cambiar` retorna antes del gancho | §1.5, §3.5 («`sin_partida`…»), §5.1 | B19, B20, B21, B28; P-12 | 4a-1 (`cambiar`), 4a-2 (`decidir`) |
| 2 | MAYOR | regla de `aplicado` y comparación entre clases | §3.2, §3.5 («La regla de la clásica…») | B15; P-14 | 4a-2 |
| 3 | MAYOR | el hipotético subestima (no completa composiciones) | §5.5, §5.3 A4, DV-IA-4 | B22; P-15 | 4a-2 |
| 4 | MAYOR | privacidad: P7 sobre `items_base`, prefijos vacíos, límites | §1.8, §4.1, §4.2, §5.2 (`aviso_maprex`), §6.2, D-8 | B26, B3; P-19, P-1 | 4a-1 (saneo), 4a-5 (e2e) |
| 5 | MAYOR | retiro de Streamlit primero | §0.1, §1.1, §3.1, §11 D-1, §12 | B1, B2; P-20 | 4a-1 (depende del retiro) |
| 6 | MAYOR | el panel pide A3 al montar y los mocks existentes | §1.9-2, §6.3, §6.10, §8 | F14, F17; P-21, P-30 | 4a-3 |
| 7 | MAYOR | hilos demonio, cupo, apagado y cliente acotado | §1.2, §3.3, §11 D-5, §12 (`lifespan`) | B29, B33, B9, B10; P-28 | 4a-1 |
| 8 | MAYOR | preguntas: la sesión queda abierta y sin salida | §1.9-4, §3.4, §5.3 A7, §6.6 | B30, B17, F12; P-29 | 4a-1, 4a-3 |
| 9 | MENOR | ritmo por `usuario_id` | §3.3 | B9 | 4a-1 |
| 10 | MENOR | `hoja_plano.fusionar` octavo consumidor; prueba al final de `test_arquitectura.py` | §2.2, §3.5, §8, §12 | B28 | 4a-1 |
| 11 | MENOR | categoría registrada por la envoltura, `tiempo`, `cancelado`, `retirada_por_la_ia` | §1.9-3, §3.3, §5.2 | B14, B11, B31 | 4a-1 |
| 12 | MENOR | orden de bloqueos, testigo, corrección de «no pueden fallar» | §3.2, §3.3, §3.5 | B32, B21 | 4a-1, 4a-2 |
| 13 | MENOR | `fuente_sugerida` de todas las sesiones | §3.2 (`aceptadas`), §3.5 | B24b; F15 | 4a-2, 4a-4 |
| 14 | MENOR | textos: «orientativa», frase por tipo, `h2` fuera del botón, `alAplicar`, `hoja_vista` en 4a-2, reemplazo de §2.10, dónde se construyen `Servicios`/`CatalogoDeLaBase`, costo estimado, `Intl.NumberFormat` | encabezado, §2.3, §4.3, §6.1, §6.2, §6.4, §6.5, §8 | F7, F10, F15 | 4a-2, 4a-3, 4a-4 |

## 15. Registro de la ronda 3

| # | Severidad | Hallazgo | Dónde quedó | Prueba | Sub-rebanada |
|---|---|---|---|---|---|
| N1 | MAYOR | P7 incompleto: el motor crea ítems con la descripción real del catálogo | §4.1 (catálogo envuelto, `del_motor` con catálogo real, alcance honesto), DV-IA-11, P-19 | B26 (caso exacto: `proponer_partida` + `consultar_borrador` + `pedir_informe_auditoria`) | 4a-1, 4a-5 |
| M1 | MENOR | rechazo de `sin_partida` con `rev` viejo | §3.5 | B20 | 4a-2 |
| M2 | MENOR | traspaso del testigo del semáforo | §3.3 | B9 | 4a-1 |
| M3 | MENOR | 120 s puede cortar un turno legítimo | D-4, R-A2 | 4a-6/4a-7 (medición) | 4a-6 |
| M4 | MENOR | línea de `hoja_plano.fusionar` | §3.5 | — | — |
| M5 | MENOR | literal de B22/P-15 desde la memoria OF-001, con indirectos | B22 | B22 | 4a-2 |
| M6 | MENOR | §13.1 y cola de `fuente_sugerida` | §13 | — | — |
