# Asistente de IA en la Hoja del proyecto (React): diseño de la etapa 1

**Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-adm-empresa` (base `05861c43`) · **Estado:** PROPUESTO. Lo juzga el
árbitro (`docs/planes/MANUAL_ARBITRO.md`, criterios B2, B3, B4, C1, C2, D1 y D2 aplicados al diseño). Sin su aprobación no
hay código. Las decisiones que no son de ingeniería están en §11 (D-1 a D-7), cada una con su recomendación.

**Origen del encargo.** Eugenio decidió el 2026-10-21 (opción B) construir el panel por etapas. **Etapa 1** (este documento,
con todo el detalle): elegir proveedor, escribir el pedido, ver las propuestas, aceptar o rechazar cada una y ver el
resultado hipotético (total y cambios si se aceptan). **Etapa 2** (solo extensión prevista, §9): preguntas de la IA y
respuestas, cierre de la sesión al guardar la versión. **Etapa 3** (solo extensión prevista, §9): historial y costos.

**Alcance de este documento:** solo diseño. No se escribió código de producción ni se tocó ninguna prueba. `git diff --
asistente ui core` queda vacío.

**Qué leí (enteros salvo donde se dice):** `docs/especificaciones/2026-10-19-hoja-react-design.md` (§0 a §11 y §12; el §6.1 a
§6.4 por títulos y tablas), `docs/planes/MANUAL_SUBAGENTES_MIGRACION.md`, `docs/planes/MANUAL_ARBITRO.md`; `ui/paginas/hoja.py`
líneas 1 a 300 y 640 a 1160 (todo el panel clásico) y las referencias a `_cerrar_asistente_al_guardar` y `_descartar_asistente`;
`asistente/servicio.py`, `propuestas.py`, `privacidad.py`, `tarifas.py`, `instalacion.py`, `catalogo.py`, `fabrica.py`,
`configuracion.py` enteros; `orquestador.py` líneas 1 a 130 y 395 a 498; `registro.py` líneas 1 a 135 y 225 a 366;
`proveedores/base.py` y `guionado.py` (cabecera), `claude.py` líneas 160 a 200; `api/rutas/admin_asistente.py` (cabecera y
esquemas), `api/rutas/hoja.py` (cabecera, rutas y `_editar`/`_vivo`), `api/rutas/hoja_plano.py` (cabecera), `api/dependencias.py`;
`aplicacion/hoja_borradores.py` entero, `hoja_edicion.py` líneas 1 a 165, `hoja_guardado.py` cabecera, `hoja_vista.py` firmas;
`frontend-desktop/src/paginas/hoja/index.tsx` y `useBorrador.ts` enteros; `frontend-desktop/src/paginas/administracion/
Asistente.tsx` cabecera; `docs/especificaciones/2026-10-11-silice-s4-asistente-ia-design.md` §3.1, §3.2, §3.3 y §8;
`tests/unit/test_arquitectura.py` (reglas de la API), `test_arquitectura_asistente.py`, la cabecera y los dobles de
`test_ui_hoja_asistente.py`; `docs/bitacora/2026-10-19-congelado-del-experimento-roto-por-la-migracion.md`;
`asistente/precios_ia.json` y `config_ia.json`. **No corrí ninguna prueba ni la aplicación**: lo que afirmo sale de la
lectura y cada afirmación dudosa lo dice (§13).

**Convención de referencias:** `P:línea` = `ui/paginas/hoja.py`; `S:línea` = `asistente/servicio.py`. Los números de línea
son del commit `05861c43`.

---

## 0. Resumen en doce líneas

1. El motor del asistente (`asistente/*`) **se reutiliza tal cual, sin un solo byte nuevo**; lo que falta es una capa
   delgada en `aplicacion/` (`hoja_asistente*.py`) y una ruta nueva (`api/rutas/hoja_asistente.py`). La página clásica no se
   modifica ni se importa desde `api/`.
2. **Hallazgo que condiciona todo (§1.1):** `asistente/orquestador.py`, `propuestas.py`, `privacidad.py`, `validacion.py` y
   `servicio.py` operan sobre `ui.hoja.Borrador`, **no** sobre `aplicacion.hoja.Borrador` (Plan C: son dos clases distintas).
   Cuatro de esos archivos están en el congelado del experimento. Se resuelve con **un puente de un solo módulo**
   (`aplicacion/hoja_asistente_puente.py`: conversión campo a campo, importación perezosa) que no toca nada congelado (D-1).
3. **La llamada al proveedor es larga y bloqueante** (hasta 12 turnos; el cliente de Claude no fija un plazo propio). Por eso
   proponer es un **trabajo en segundo plano**: `POST` responde 202 al instante, el navegador consulta el estado (sondeo cada
   2 s), hay plazo por turno y total, cancelación, **una petición por borrador** y un tope global de sesiones en vuelo.
4. **La sesión del asistente vive atada al borrador vivo y nunca dentro de él** (en la clásica la sesión es otra clave de estado, `CLAVE_ASISTENTE` `P:114`, aparte de `CLAVE_BORRADOR` `P:96`, y el docstring `P:25-29` aplica la misma disciplina a R17: nada ligado al borrador que se quede viejo al editar).
   Nace con el borrador y muere con él por cualquier camino (descartar, reemplazar, vencer a las 8 h, expulsar, cambiar de
   caso) usando el gancho que ya existe, `hoja_borradores.al_quitar`.
5. **Aplicar lo aceptado es una operación atómica propia**, no una cadena de rutas E1 a E11: las propuestas de partida
   entran a `items_base`, que ninguna ruta de edición toca. Pasa por el mismo núcleo que las ediciones (`rev`, `completar_
   composiciones`, `reemplazar`) en dos fases (calcular sin efectos, registrar, aplicar), así que un fallo no deja nada a medias.
6. **La IA nunca es autora.** Quien decide es la cuenta de la sesión (`Nombre <login>`); el cuerpo no trae ningún campo de
   persona; cada fila aceptada cita su origen «propuesta de IA» y el guardado sigue exigiendo fuente y responsable humanos.
7. **Privacidad:** viaja solo lo de la lista blanca de `asistente/privacidad.py` (sin precios, montos, APU ni nombres); la clave
   de IA **nunca llega al navegador** (ni en una respuesta, ni en un error, ni en el 422); el pedido que parezca llevar una
   clave se rechaza antes de enviarse y antes de registrarse (hoy solo se filtran las **respuestas**, `orquestador.py:313`).
8. **Gasto:** estimación previa (`estimar_costo`: 1,2144 USD con Opus 5.5, a mano), tope por sesión del administrador
   (`topes_de_la_instalacion`, 2 USD de fábrica), 12 turnos y 60 llamadas, plazo, cancelación, ritmo por cuenta y tope de
   concurrencia. **Ninguna prueba ni agente llama a un proveedor real**; la prueba real espera la autorización de gasto de
   Eugenio (D-2).
9. **Interfaz:** el `<aside aria-label="Asistente de IA">` pasa a ser un desplegable (cerrado de fábrica) entre el estado del
   borrador y las pestañas. Sin anchos fijos: con letra Grande y Muy grande se apila solo. Las propuestas son una lista (no una
   tabla) para no depender del ancho; montos `{texto, exacto}` en es-VE; texto de la IA siempre escapado.
10. **Trazabilidad que ya existe y se conserva:** `OrigenMedida` de tipo `ia` en las filas del espacio, `ItemComputo` MANUAL con
    `origen_id = "ia:<sesión>:<propuesta>"`, registro `ia_*` con `decidida_por`, fuente prellenada «propuesta de IA, sesion N,
    proveedor/modelo». **Hueco que hay que cerrar ya (D-3):** sin marcar la sesión como guardada, el anexo `ia.json` del paquete
    no la incluye; el gancho es solo de servidor y no añade pantalla.
11. Siete sub-rebanadas (4a-1 a 4a-7; 4a-7 bloqueada por D-2). Backend y front arrancan **en paralelo** desde el primer día porque
    el contrato de §5 ya es el contrato.
12. Etapas 2 y 3 dejan sus ganchos hechos en la 1: estado `pregunta` (se muestra, no se responde), lista `aceptadas` por sesión,
    número de sesión `ia_*` en todas las respuestas, gancho `al_guardar`.

---

## 1. Hallazgos que cambian el plan (verificados por lectura)

### 1.1 El asistente no puede recibir el borrador de la hoja nueva sin un puente (condiciona todo)

- `asistente/orquestador.py:59`, `privacidad.py:24`, `propuestas.py:20-26`, `validacion.py:34` y `servicio.py:29-30` importan de
  **`ui.hoja`** (`Borrador`, `HojaInvalida`, `espacio_desde_filas`, `filas_desde_espacio`, `PREFIJO_ORIGEN_IA`, y `servicio` usa
  `hoja.elaborar_borrador`). La hoja nueva trabaja con `aplicacion.hoja.Borrador` (`aplicacion/hoja.py:334`), copia por el Plan C
  (`docs/especificaciones/2026-10-19-hoja-react-design.md` §5.6): **dos dataclasses distintas con los mismos nueve campos**
  (`fecha, moneda, espacio, items_base, composiciones, parametros, plan, cantidades, reglas_extra`; comprobado comparando
  `ui/hoja.py` y `aplicacion/hoja.py` a ojo, la prueba de §7 lo fija). `HojaInvalida` sí es **la misma clase**
  (`aplicacion/errores.py`; `ui/hoja.py` la importa de allí desde el commit `bdf77cc`).
- `asistente/experimento/protocolo.json`, `archivos_del_auditor`, lista `orquestador.py`, `propuestas.py`, `privacidad.py`,
  `validacion.py`, `herramientas.py`, `catalogo.py`, `tarifas.py`, `precios_ia.json`, `config_ia.json`, `proveedores/base.py`,
  `claude.py`, `ollama_local.py`, `ui/hoja.py` y `ui/composicion.py`. **`servicio.py`, `instalacion.py`, `registro.py`,
  `fabrica.py`, `clave.py`, `configuracion.py`, `administracion.py` y `proveedores/guionado.py` no están en esa lista.** Cambiar
  cualquier línea de los congelados contradice RS-9 (decisión de Eugenio del 2026-10-18) y rompe más la guardia
  `test_experimento_congelado_vigente.py`, que ya falla por otra causa (bitácora `2026-10-19-congelado-del-experimento-roto-
  por-la-migracion.md`).
- Tres guardias del repositorio impiden el atajo obvio de importar `asistente.servicio` desde la API o desde `aplicacion/`:
  (a) `tests/unit/test_arquitectura.py`, `test_importar_la_api_no_carga_scripts_tests_ni_ui`: importar `api.main` en un proceso
  limpio no puede dejar ningún módulo `ui` en `sys.modules`, y `asistente.servicio` arrastra `ui.hoja`; (b)
  `test_arquitectura_asistente.py`, `test_aplicacion_entrega_solo_importa_el_registro_del_asistente`: en `aplicacion/` **solo
  `entrega.py`** puede importar `asistente`, y solo `asistente.registro`; (c) `aplicacion/` no importa `ui` (regla RM-1).
- `api/rutas/admin_asistente.py` ya importa `asistente.administracion`, `clave`, `configuracion` e `instalacion`, y pasa las
  guardias porque ninguno de esos cuatro toca `ui`. Es el precedente: lo que no toca `ui.hoja` se importa sin más.

**Consecuencia (D-1).** Se construye **un único módulo puente** que (1) importa de forma perezosa los cinco módulos que cargan
`ui.hoja`, (2) toma la clase `Borrador` que el asistente espera **del propio asistente** (`asistente.servicio.Borrador`), de modo
que `aplicacion/` nunca nombra a `ui`, y (3) convierte `aplicacion.hoja.Borrador` ↔ ese `Borrador` campo a campo. Costo
declarado: la primera propuesta carga `ui.hoja` en el proceso de la API (nunca al arrancar). La alternativa limpia (repuntar
`asistente/*` a `aplicacion.hoja`) exige revocar RS-9 y re-congelar: es de Eugenio y es el camino natural **cuando se retire
Streamlit** (§11, D-1).

### 1.2 Proponer es largo, bloqueante y sin gancho de cancelación

- `orquestador.py` corre hasta `Topes.turnos = 12` turnos y `Topes.llamadas = 60`; cada turno es una llamada de red síncrona
  (`self.proveedor.turno(...)`, `orquestador.py:~399`). `claude.py:169` crea el cliente con `max_retries=2` y **sin `timeout`**
  (se usa el del SDK, que no leí). `ollama_local.py:149` usa `timeout=5` solo para comprobar la versión.
- El bucle no ofrece progreso ni cancelación; solo `Topes`, `Servicios.responder` y `ErrorDeProveedor` (que sí termina la
  sesión conservando las propuestas, `MotivoFin.ERROR_DE_PROVEEDOR`). Eso basta para una **envoltura del proveedor** que cuente
  turnos, vigile el plazo y la cancelación y lance `ErrorDeProveedor` (§3.3), sin tocar ningún archivo congelado.
- La clásica lo hacía en la propia ejecución de Streamlit (la pantalla quedaba bloqueada). Una ruta síncrona de FastAPI ocuparía
  un hilo del grupo de rutas minutos; el precedente de `hoja_plano` (503 con `Retry-After` cuando hay `LECTURAS_SIMULTANEAS`)
  muestra que el proyecto ya cuida ese grupo de hilos.

### 1.3 Los proveedores llevan la clave y algunos preguntan a la red

`proveedores_de_la_instalacion()` (`instalacion.py`) construye `ProveedorClaude(clave.vigente, …)`: el objeto **contiene la clave
de IA** y por eso `servicio.proponer` lo suelta de la sesión (`_soltar_proveedor`, `S:67`). `ProveedorOllama.disponible()`
comprueba la versión por HTTP (`ollama_local.py:149`, `timeout=5`; lo deduje de esa línea, no lo probé): listar proveedores puede
tardar hasta 5 s si hay un modelo local configurado (hoy en pausa por RS-8). La ruta de proveedores **nunca serializa el objeto**:
proyecta nombre, modelo, disponibilidad y motivo.

### 1.4 La ruta de administración no sirve a quien arma

`GET /v1/admin/asistente` exige `ADMINISTRAR_EMPRESA`. La persona que arma (rol `arma`, `EDITAR_HOJA`) necesita ver qué
proveedores hay y cuánto costaría, sin ver la clave ni la configuración: se necesita una lectura propia en la ruta de la hoja.

### 1.5 Ninguna ruta de edición toca `items_base`

Las propuestas de tipo `partida` entran a `Borrador.items_base` como `ItemComputo` MANUAL (`propuestas.py:_item`). E1 a E7 editan
espacio, cantidades escritas, parámetros, plan y APU; ninguna agrega ítems base. Aceptar por la «cadena de rutas» es imposible
(§3.5).

### 1.6 El pedido no se filtra de secretos hoy

`orquestador.py:313` aplica `contiene_secreto` solo a las **respuestas** a una pregunta. El pedido viaja tal cual al proveedor
(`privacidad.primer_mensaje`), se guarda en `ia_sesiones.pedido` y **entra al anexo `ia.json` del paquete firmado**
(`registro.anexo_ia`, campo `pedido`). Una clave pegada por error en el pedido llegaría al proveedor, a la base y al paquete. La
capa nueva lo rechaza antes (§4.2).

### 1.7 El anexo `ia.json` solo incluye sesiones marcadas como guardadas

`registro.anexo_ia` filtra `version_guardada IS NOT NULL` y exige alguna propuesta aceptada o editada. Si la etapa 1 deja aceptar y
guardar **sin** llamar a `marcar_guardada`, la versión guardada contiene filas con origen `ia` y el paquete **no** trae la sesión
que las explica. Es un hueco de trazabilidad, no un detalle de interfaz: D-3 propone cerrarlo ya con un gancho de servidor.

### 1.8 Otros hallazgos menores

| # | Hallazgo | Consecuencia |
|---|---|---|
| 1 | El diseño de la hoja (§2.10) prometía `useBorradorHoja()`; no existe (`grep` en `frontend-desktop/src`). `index.tsx` pasa `id`, `rev` y `aplicar(resumen)` por props a cada pestaña | el panel recibe las mismas props; no se crea ningún hook global |
| 2 | `Hoja.test.tsx:256` afirma que el `<aside aria-label="Asistente de IA">` existe vacío y oculto | 4a-3 cambia esa prueba (es suya) |
| 3 | Los mensajes de `asistente/*` (`MENSAJES` del orquestador, `DependenciaPendiente`, `descripcion`) no llevan tildes y están congelados | se muestran tal cual donde son contenido del motor; lo que compone la capa nueva o el front lleva tildes (misma regla que D-3 de la hoja) |
| 4 | `entrega.py` y `registro.py` ya escriben el registro `ia_*` con una conexión propia que confirma cada escritura (`RegistroIA(conexion, confirmar=True)`, `P:177-199`) | el trabajo en segundo plano abre su propia conexión del motor del caso (`obtener_motor`) y nunca usa la `Session` de la petición |
| 5 | `Disponibilidad.motivo` y los mensajes de `ErrorDeProveedor` salen de código que "nunca incluye la clave" (`claude.py:_traducir`), pero la garantía es de ese archivo | la proyección los pasa por `asistente.clave.enmascarar` y los corta a 300 caracteres (defensa en profundidad) |
| 6 | La API nunca importa `ui` y la clásica queda en el congelado | la clásica no se modifica; su código de pantalla (`_proponer_con_asistente` y compañía) se **reescribe de intención** en la capa nueva; ese pegamento duplicado (~120 líneas) es deuda con retiro junto a Streamlit |

---

## 2. Alcance por etapas y qué se reutiliza

### 2.1 Etapas

| Etapa | Incluye | No incluye |
|---|---|---|
| **1 (este diseño)** | proveedores y estimación; vista previa de lo que se envía; proponer (segundo plano, progreso, cancelar); lista de propuestas con supuestos y citas; aceptar / aceptar y editar / rechazar cada una; resultado hipotético; descartar lo pendiente; retomar la sesión tras recargar; gancho servidor de cierre al guardar (D-3) | responder preguntas de la IA; historial; costos acumulados |
| **2** | responder o cancelar una pregunta de la IA; mensaje de cierre de la sesión al guardar la versión (el gancho de servidor ya está) | — |
| **3** | historial de sesiones del proyecto; costos reales por sesión y acumulados; tope por instalación | — |

### 2.2 Qué se reutiliza y qué es nuevo

| Pieza | Tratamiento | Bytes nuevos en archivos existentes |
|---|---|---|
| `asistente/servicio.py`: `proponer`, `decidir`, `hipotetico`, `resumen_hipotetico`, `descripcion`, `estimar_costo`, `fuente_del_cambio`, `SesionDeAsistente`, `DependenciaPendiente` | **tal cual**, vía el puente | 0 |
| `asistente/orquestador.py` (`Servicios`, `Topes`, `ESPERAR`, `MotivoFin`, el bucle), `propuestas.py`, `validacion.py`, `herramientas.py` | **tal cual** | 0 (congelados) |
| `asistente/privacidad.py` (`vista_previa`, `primer_mensaje`, `contiene_secreto`, lista blanca), `catalogo.py` (`CatalogoDeLaBase`, `PartidaVista`) | **tal cual** | 0 (congelados) |
| `asistente/tarifas.py` (`tarifa_de`), `registro.py` (`RegistroIA`, `anexo_ia`), `instalacion.py` (`proveedores_de_la_instalacion`, `topes_de_la_instalacion`, `proveedor_por_defecto`, `prefijos_de_maprex`), `clave.py` (`enmascarar`), `proveedores/guionado.py` (doble de prueba) | **tal cual** | 0 |
| `aplicacion/hoja_borradores.py`: `obtener`, `reemplazar`, `descartar`, `al_quitar`, `BorradorVivo`, topes de memoria | **tal cual** (la sesión del asistente es un registro aparte, ligado por `id`) | 0 |
| `aplicacion/hoja_edicion.py`: el núcleo `_cambiar` (guardado, `rev`, `completar_composiciones`, `reemplazar`) | se hace **público** (`cambiar`) y gana el parámetro opcional `antes_de_reemplazar` (§3.5) | ~15 líneas (4a-1) |
| `aplicacion/hoja_guardado.py`: `guardar` | gana la lista `al_guardar` (gancho posterior al `commit`, D-3) | ~20 líneas (4a-2) |
| `aplicacion/hoja_vista.py`: `elaborar`, `con_r17`, `resumen`, `_base_de_comparacion` | **tal cual** (`_base_de_comparacion` se usa como `hoja_vista.base_de_comparacion`; 4a-2 lo expone sin cambiar su cuerpo si hace falta) | ~2 líneas |
| `api/`: `cuenta_con`, `_vivo`, `IdDeBorrador`, `RutaSinCache`, `RutaSinEco`, `Resumen`/`Monto` de `api/esquemas_hoja.py`, `obtener_motor`, `url_de_la_peticion` | **tal cual** | 0 |
| **Nuevo en `aplicacion/`** | `hoja_asistente_puente.py` (único acople con `ui.hoja`), `hoja_asistente.py` (sesión, estado, decidir, hipotético), `hoja_asistente_trabajo.py` (hilos, plazos, cancelación) | — |
| **Nuevo en `api/`** | `rutas/hoja_asistente.py`, `esquemas_hoja_asistente.py` | — |
| **Nuevo en el front** | `src/paginas/hoja/asistente/` (§6.10) | `index.tsx` (montaje del panel) |
| **No se toca** | `ui/paginas/hoja.py` y todo `ui/`, `asistente/*`, `core/`, `adapters/` | 0 |

### 2.3 Lo que la clásica hace y la capa nueva reescribe

`_proponer_con_asistente`, `_decidir_propuesta`, `_hoja_editada_a_mano`, `_resumen_hipotetico`, `_formulario_del_asistente`,
`_panel_asistente`, `_cerrar_asistente_al_guardar` y `_descartar_asistente` son **pegamento de Streamlit** alrededor del motor. Se
reescriben (no se copian) contra la sesión del servidor, y la prueba de paridad (§7, 4a-5) compara su efecto con el del motor
llamado directamente sobre `ui.hoja.Borrador`, que es lo que la clásica hace por dentro.

---

## 3. Arquitectura

### 3.1 El puente (`aplicacion/hoja_asistente_puente.py`)

Es el **único** módulo de la capa nueva que nombra a `asistente.servicio`, `orquestador`, `propuestas`, `privacidad` o
`validacion` (los que cargan `ui.hoja`). Reglas:

1. **Importación perezosa**: dentro de funciones, con caché en una variable del módulo. Importar `api.main` no deja `asistente.
   servicio` ni `ui` en `sys.modules` (prueba de subproceso, §7).
2. **`aplicacion/` no importa `ui`**: la clase del asistente se obtiene como `asistente.servicio.Borrador`; la conversión usa
   `dataclasses.fields` de ambas clases y construye con `kw_only`. `a_motor(borrador)` y `de_motor(borrador)` son funciones puras;
   `reglas_extra` (que no se compara) viaja igual.
3. **Superficie mínima** (todo recibe y devuelve tipos de `aplicacion`): `proponer`, `decidir`, `hipotetico`, `descripcion`,
   `vista_previa`, `estimar_costo`, `fuente_del_cambio`, `resumen_hipotetico`, más los re-exportes `Servicios`, `Topes`, `ESPERAR`,
   `EstadoPropuesta`, `MotivoFin`, `DependenciaPendiente`. `HojaInvalida` no se re-exporta: es la de `aplicacion.errores`.
4. **Salida de emergencia documentada**: el día que `asistente/*` se repunte a `aplicacion.hoja` (D-1, opción R), el puente se
   reduce a re-exportes y se borran las dos funciones de conversión; ninguna otra línea de la capa nueva cambia.
5. **Guardia contra la deriva** (prueba 4a-B1): los nombres, el orden y las banderas `compare` de los campos de las dos clases
   `Borrador` coinciden contra una **lista literal** escrita a mano; si alguien agrega un campo a una sola, falla. Es la misma
   disciplina de la prueba de paridad del Plan C (`tests/unit/test_aplicacion_hoja_paridad.py`).

Costo declarado (D-1): `ui.hoja` se carga en el proceso de la API la primera vez que alguien propone o previsualiza.

### 3.2 La sesión del asistente: dónde vive y cuándo muere

- **Registro propio** en `aplicacion/hoja_asistente.py`: `dict[id_de_borrador, SesionDelAsistente]` con un cerrojo, **fuera** de
  `BorradorVivo` (que no gana ningún campo: su `tamano` y su `pickle` no cambian; la disciplina del docstring `P:25-29`). La clave es el
  `id` del borrador, así que la autorización es la del borrador: `hoja_borradores.obtener(huella, id)` ya devuelve 404 para uno
  ajeno.
- **Contenido de `SesionDelAsistente`**: `estado`; la `SesionDeAsistente` del motor (sin proveedor ni clave: `proponer` ya lo
  suelta); `pedido`; `proveedor`, `modelo`, `destino`; `rev_base`; `aplicado` (el borrador que dejó la última decisión del
  asistente, o `None`; equivale a `CLAVE_ASISTENTE_APLICADO`, `P:122`); `aceptadas` (números de sesión `ia_*` con propuestas
  aceptadas aún sin guardar, equivale a `CLAVE_ASISTENTE_ACEPTADAS`: **sobrevive a descartar la sesión**); `progreso`; `error`;
  `cache_hipotetico` (clave: estados de las propuestas + borrador comparado); `cancelado` (un `threading.Event`); `creado`.
- **Ciclo de vida** (todos pasan por `hoja_borradores.al_quitar`, que avisa **fuera** del cerrojo del registro y sin dejar que un
  aviso fallido frene a los demás; mismo patrón que `hoja_plano.py:258`):

| Evento | Qué pasa con la sesión del asistente |
|---|---|
| `DELETE /v1/hoja/borradores/{id}` | se quita; si hay un trabajo en vuelo se le fija `cancelado` |
| abrir otra versión (el front descarta el borrador anterior) | igual: el borrador sale del registro |
| E11 `reemplazar: true` | igual |
| vencimiento a las **8 h** sin uso (`VIGENCIA`) | igual (el barrido perezoso ya existe) |
| expulsión por tope (4 por ficha, 64 globales, 256 MiB) | igual |
| cambio de caso (`caso_web.fijar` → `olvidar`), cierre de sesión, ficha vencida | igual |
| `guardar` (S1) con éxito | el borrador queda `guardado_como`; la sesión **sigue** hasta que el borrador salga, pero ya no se puede decidir (409 «ya se guardó») y el gancho de cierre (§3.5) marca las sesiones aceptadas |
| reinicio de la API | se pierde, como el borrador (costo declarado, D-2 de la hoja); el registro `ia_*` conserva lo hecho |

- **Nunca se guarda en el borrador** y nunca se serializa en la base fuera de `ia_*`. La prueba 4a-B13 recorre los objetos de la
  sesión buscando la clave de prueba y la ausencia de campos nuevos en `BorradorVivo`.
- **Tope de memoria**: como máximo una sesión por borrador y, por tanto, `GLOBALES = 64`; no hace falta un tope propio.
- **Una sesión por borrador a la vez**: proponer de nuevo con una sesión terminada la reemplaza (como `_descartar_asistente()` en
  `P:800`); lo ya aceptado se queda en el borrador y su número de sesión se conserva en `aceptadas`.

### 3.3 El trabajo de la IA: segundo plano, plazos, cancelación, concurrencia

`aplicacion/hoja_asistente_trabajo.py`:

- **Ejecutor propio** `ThreadPoolExecutor(max_workers=EN_VUELO)` con `EN_VUELO = 2` (SUPUESTO, D-4). Las rutas **no** esperan
  el trabajo: `POST …/asistente` valida todo lo síncrono (§5.4), reserva un cupo y responde **202** con el estado `pensando`.
- **Una petición de IA en vuelo por borrador**: un segundo `POST` mientras el estado es `pensando` da 409
  «Ya hay una petición de IA en curso en este borrador: espere a que termine o cancélela.».
- **Tope global**: sin cupo libre, `503` con `Retry-After: 30` y texto fijo «El asistente está atendiendo otras sesiones: intente de
  nuevo en un momento.» (mismo patrón que `hoja_plano`). **Ritmo por cuenta**: como máximo `PROPUESTAS_POR_HORA = 20` por ficha
  (SUPUESTO, D-4); la 21.ª da `429` con `Retry-After` en segundos. El reloj es inyectable.
- **`ProveedorAcotado`** (envoltura del `ProveedorIA`; cumple el protocolo: `nombre`, `modelo`, `envia_fuera_del_equipo`,
  `disponible`, `turno`). Antes de cada turno: si `cancelado` está activo o venció el **plazo total** (`PLAZO_TOTAL = 300 s`),
  lanza `ErrorDeProveedor("otro", …)`; el turno se ejecuta en un hilo auxiliar y se espera como máximo `PLAZO_POR_TURNO = 120 s`
  (SUPUESTOS, D-4): al vencer lanza `ErrorDeProveedor("otro", "tiempo")`. El orquestador responde con `ERROR_DE_PROVEEDOR` y
  **conserva las propuestas ya validadas**. Cuenta turnos y, con el `uso` que devuelve cada turno y la tarifa, el **costo parcial**
  para el progreso. No guarda la clave en ningún atributo propio.
- **Costo de un turno abandonado (declarado, D-3 de §11)**: si un turno vence por plazo, su hilo sigue vivo hasta que el SDK
  regrese; el proveedor puede cobrarlo y el orquestador no lo registra. Por eso esos hilos **cuentan contra `EN_VUELO`** hasta
  que terminen (cupo honesto) y el mensaje al usuario lo dice. La corrección verdadera es un `timeout` en el cliente de Claude
  (`claude.py:169`, congelado): D-5.
- **Cancelación**: `DELETE …/asistente` con estado `pensando` fija `cancelado`, **desacopla** el registro (el estado pasa a
  `sin_sesion` al instante) y responde 204. El hilo termina cuando regrese el turno en curso y descarta su resultado; el registro
  `ia_*` conserva la sesión cerrada con su motivo. Un `POST` nuevo es posible de inmediato si hay cupo.
- **El trabajo no usa la `Session` de la petición** (ya se cerró): abre `abrir_sesion(motor)` para leer el catálogo (la cierra
  **antes** de llamar al modelo, como en la clásica, `P:~775`) y `motor.connect()` para el `RegistroIA(confirmar=True)` (un bloqueo de
  escritura de SQLite dura una sentencia, no todo el bucle). El `motor` es el de `obtener_motor(vivo.caso)`, que la ruta pasa
  como argumento (`aplicacion/` no importa `api/`).
- **Qué ve el trabajo**: una **copia inmutable** del borrador en el instante de proponer (`vivo.borrador`, `vivo.rev`) y nada del
  cerrojo del borrador; mientras la IA piensa, **todas las ediciones siguen funcionando** (E1 a E11 no esperan al asistente).
- **Errores del trabajo** (no son HTTP, porque ocurren después del 202; quedan en `error` del estado): `ErrorDeProveedor` →
  categorías `sin_conexion`, `clave_invalida`, `otro`; plazo → `tiempo`; `ImportError` (falta el extra `ia`) → `componente`;
  `SQLAlchemyError` → `base`. Cualquier otra excepción → `otro` con texto fijo y se registra sin el contenido.

### 3.4 Máquina de estados (con los ganchos de la etapa 2)

```
sin_sesion ──proponer──▶ pensando ──fin──▶ lista        (propuestas, sin propuestas, o detenida por tope/rechazos)
                          │  │ └─pregunta de la IA──▶ pregunta   (etapa 1: solo se muestra; etapa 2: se responde)
                          │  └─fallo del proveedor/plazo/base──▶ error   (se conservan las propuestas previas)
                          └─DELETE──▶ sin_sesion
lista / pregunta / error ──proponer──▶ pensando (reemplaza)
cualquiera ──DELETE / borrador sale──▶ sin_sesion
```

- `lista` agrupa los finales de `MotivoFin` con o sin propuestas (`terminar`, `fin_del_modelo`, `tope_de_turnos`,
  `tope_de_llamadas`, `tope_de_costo`, `rechazos_seguidos`, `rehusado`, `limite_de_salida`); el campo `resultado.motivo` dice
  cuál. Una sesión `lista` sin propuestas se pinta como vacío con la nota de la IA, no como error.
- `pregunta` existe **desde la etapa 1**: el orquestador se invoca con `responder=lambda _: ESPERAR` (como la clásica, `P:782`),
  así que una pregunta del modelo pausa la sesión y guarda su continuación en `SesionDeAsistente.resultado.continuacion`. La etapa 1
  la **muestra** (rotulada, escapada) y ofrece descartar o reformular el pedido; la etapa 2 agrega `POST …/respuesta` sobre la
  misma continuación. Decidir propuestas con una pregunta pendiente da 409 (la clásica ni siquiera pinta los botones, `P:989`).

### 3.5 Aplicar lo aceptado: atómico, con `rev`, con trazabilidad

**Decisión: operación `decidir` propia sobre el núcleo de edición, no la cadena E1 a E11.** Motivo: §1.5 (las partidas van a
`items_base`) y porque aplicar una propuesta es una sola operación del motor (`servicio.decidir`) que ya garantiza la misma puerta
que una edición a mano (`espacio_desde_filas`, RF-92) y registra la decisión.

Pasos de `POST …/asistente/propuestas/{propuesta}` (todo dentro de `vivo.cerrojo`, mismo orden de bloqueos que `hoja_edicion`):

1. ya guardado → 409; `rev` distinto → 409 `MENSAJE_REV` (**antes** que el contenido; no aplica a `rechazada`, que no toca el
   borrador).
2. **Calcular sin efectos**: `servicio.decidir` sobre una **copia de trabajo** de la sesión (`Pendientes` copiada, `registro=None`),
   con `sobre = a_motor(vivo.borrador)` si la persona editó a mano desde la última decisión del asistente (`vivo.borrador !=
   aplicado`), o `None` si no. Aquí salen `DependenciaPendiente` y `HojaInvalida` (409, «No se decidió nada»).
3. `de_motor(...)` y `completar_composiciones` (la partida nueva toma su APU del catálogo con la lista de precios de la versión
   abierta, `P:256-275`). Un fallo de lectura es 503 y **no cambió nada**.
4. **Registrar** la decisión con `RegistroIA(confirmar=True).decidir(sesion, id, estado, quien)` en una conexión propia, con
   `quien = activa.usuario`. Si la base falla: 503 y nada cambió. (Es la misma llamada que hace `servicio.decidir` cuando recibe
   registro; se hace aquí porque el orden "registrar antes de aplicar" debe ocurrir **después** del paso 3 para no dejar una
   decisión registrada sin su efecto. Una línea duplicada de intención, probada con el volcado `ia_*`.)
5. `hoja_borradores.reemplazar(huella, id, nuevo, rev)` (sube `rev`, invalida la caché) y recién entonces se publica la copia de
   trabajo como `sesion.pendientes`, se fija `aplicado = nuevo` y, si cambió el borrador, se agrega el número de sesión a
   `aceptadas`. Los pasos 5 son en memoria: no pueden fallar.

El paso 3 y el 4 caben como el parámetro `antes_de_reemplazar` de `hoja_edicion.cambiar` (la función pública que sale de
`_cambiar`): se ejecuta después de `completar_composiciones` y antes de `reemplazar`. Es un cambio aditivo (valor por omisión
`None`; las siete ediciones existentes no cambian) y evita duplicar la guarda de `rev`, de "ya guardado" y el cerrojo.

**Aceptar y editar** (`editada`) es lo que la clásica hace: la propuesta entra al borrador igual que `aceptada` y la persona
retoca la fila a mano en la pestaña Espacio y metrajes; el panel lo dice. No hay edición dentro del panel.

**Trazabilidad (la IA nunca es autora):**

| Eslabón | Qué queda |
|---|---|
| Fila aceptada del espacio | `OrigenMedida(tipo=ia, referencia="modelo=…; propuesta=P1; proveedor=…; sesion=N; supuesto.<campo>=…")` con `id = "IA-N-P1"` (`propuestas.referencia_de`), visible en el Estado de la fila, en el Excel y en las tablas `esp_*` al guardar |
| Partida aceptada | `ItemComputo` MANUAL, `origen_id = "ia:N:P1"` (`PREFIJO_ORIGEN_IA`; `estado_de_items` ya lo reconoce) |
| Decisión | `ia_propuestas.estado` y `decidida_por = "Nombre <login>"` (la cuenta; **ningún campo del cuerpo** puede decirlo: `extra="forbid"` → 422 sin eco) |
| Guardado | `fuente_sugerida = servicio.fuente_del_cambio(...)` («propuesta de IA, sesion N, proveedor/modelo») que el front **prellena solo si la fuente está vacía** (`P:865`); `RegistroCambio.responsable` sigue siendo la cuenta (RF-82) |
| Paquete | `anexo_ia` (`ia.json`) vía `marcar_guardada` (gancho de D-3) |

**Gancho de cierre al guardar (D-3, solo servidor).** `hoja_guardado.al_guardar: list[Callable[[BorradorVivo, Guardado], None]]`
se avisa **después del `commit`** y fuera de los cerrojos. El de la sesión del asistente llama a `RegistroIA(confirmar=True).
marcar_guardada(n, codigo, proyecto=vivo.proyecto)` para cada `n` de `aceptadas` (incluidas sesiones descartadas) y vacía la lista.
Si falla, **la versión ya está guardada y no se deshace**: queda un `aviso` en la respuesta de S1 (campo aditivo `avisos: list[str]`
en `GuardadoRespuesta`, vacío de fábrica) con el texto de la clásica («La versión se guardó, pero no se pudo anotar la sesión del
asistente. …») y la lista `aceptadas` se conserva para el siguiente guardado. Etapa 2 solo agrega el mensaje de pantalla.

### 3.6 Qué pasa si el borrador cambia mientras la IA piensa

- La IA trabaja sobre `vivo.borrador` **tal como estaba** al proponer (`rev_base`). Las ediciones posteriores (cualquier E1 a E11,
  otra ventana) suben `rev` y siguen funcionando.
- Al terminar, las propuestas quedan **pendientes** y válidas contra la base antigua. Como la hoja actual ya no es `aplicado`
  (que arranca siendo `sesion.base`), el estado trae `sobre_la_hoja_editada = true` y cada propuesta se aplica **sobre la hoja
  vigente** (la regla de `_hoja_editada_a_mano`, `P:805-811`): las ediciones se conservan y, si una propuesta ya no cabe (por
  ejemplo, usa un id que la persona creó o quitó), el 409 dice «No se decidió nada» y se puede rechazar.
- El panel muestra el aviso «Usted editó la hoja mientras la IA trabajaba (o después): cada propuesta se aplicará sobre la hoja
  tal como está ahora.» Es un aviso, no un bloqueo.
- `rev` en el cuerpo de `decidir` es el que el **front** vio del borrador: si otra ventana lo cambió, 409 y recarga (idéntico a E1
  a E7). El resultado hipotético se calcula y se cachea por `(estados de las propuestas, rev)`.

---

## 4. Privacidad y gasto

### 4.1 Qué viaja al proveedor (lista blanca única: `asistente/privacidad.py`)

- **Se envía:** instrucciones y esquemas fijos; el **pedido tal como se escribió**; `resumen_del_borrador` (ids, geometría,
  códigos, descripciones, unidades, cantidades de `items_base`, nombres limpios de ≤ 80 caracteres); candidatas de catálogo (≤ 10
  por búsqueda, ≈ 50 por sesión); hallazgos minimizados (R2, R7, R11 a R14 con texto fijo; sin `impacto`).
- **No se envía:** precios, montos, totales, APU, curva, punto de equilibrio, cotizaciones, listas de precios, el nombre del
  proyecto (va el alias `P1`), nombres de empresa o de usuarios, archivos, la clave, el registro `ia_*`.
- **El catálogo que ve la IA** se arma con `CatalogoDeLaBase` sobre `PartidaVista(codigo, descripcion, unidad, dominio,
  de_maprex)`: ninguno de esos campos es dinero. En modo nube las partidas de MaPreX viajan solo con código y unidad.
- La capa nueva **no agrega ni quita** nada de esa lista: usa `vista_previa`, `primer_mensaje` y las herramientas tal cual. La
  prueba 4a-B26 lo comprueba **desde lo que recibe el proveedor** (`ProveedorGuionado.recibidos`), no desde la capa.

### 4.2 La clave de IA y lo que se rechaza antes de enviar

- **La clave nunca sale del servidor.** Las respuestas proyectan nombre, modelo, destino, disponibilidad y motivo; el motivo y los
  mensajes de error pasan por `enmascarar` y se cortan a 300 caracteres. El 422 no repite lo enviado (`RutaSinEco`). El estado del
  trabajo no guarda el proveedor (`ProveedorAcotado` lo libera al terminar). No hay campo `clave` en ningún esquema (prueba de
  recorrido sobre `docs/api.json`).
- **Pedido**: obligatorio no vacío tras recortar espacios; **≤ 4 000 caracteres** (SUPUESTO, D-4); si `contiene_secreto(pedido)`
  (`sk-ant-`, `-----BEGIN`) → 422 «El pedido parece contener una clave de acceso: quítela y vuelva a intentarlo. No se envió
  nada.» **sin eco, sin llamar al proveedor y sin fila en `ia_sesiones`** (cierra §1.6). El límite de longitud y el rechazo se
  aplican también a la vista previa.
- **Vista previa**: `POST …/asistente/previa` devuelve el texto **exacto** del primer mensaje (`primer_mensaje`) y el destino. Es
  de solo lectura y no gasta. El texto se corta a 100 000 caracteres con la bandera `truncada` y el total (`caracteres`); lo que
  se corta se dice, no se oculta («se muestra el comienzo; se envía completo»).
- **Advertencia permanente** en el formulario (copia de `P:1064`, con tildes): «El pedido viaja tal como lo escribe: no escriba
  datos personales, claves ni precios.» El sistema **no** filtra datos personales (límite declarado de S4 §8.1).
- **Texto ajeno**: lo que dice la IA (descripciones, supuestos, citas, notas, pregunta, mensajes de error de herramientas) se
  muestra **siempre como texto**, nunca como Markdown ni HTML, sin enlaces ni imágenes (RV-14).

### 4.3 Gasto

| Control | Dónde | Valor |
|---|---|---|
| Estimación previa (`estimar_costo`) | por proveedor, en `GET …/proveedores` | cota de la tarea: 12 turnos × (10 000 entrada + 3 000 salida + 6 000 caché) con la tarifa de `precios_ia.json`. **Opus 5.5: 0,1012 × 12 = 1,2144 USD** (oráculo a mano, P-2); local: 0 |
| ¿Supera el tope? | el servidor compara `Decimal` y manda `estimacion_supera_el_tope` | el front no compara números |
| Tope por sesión | `topes_de_la_instalacion().costo` (`tope_usd` de la configuración, 2 USD de fábrica) | el turno que alcanza el tope se completa y la sesión se detiene conservando lo propuesto (`tope_de_costo`) |
| Turnos y llamadas | `Topes` por omisión | 12 y 60 |
| Ritmo | por cuenta | 20 por hora (D-4) |
| Concurrencia | global | 2 en vuelo (D-4) |
| Plazos | por turno y total | 120 s y 300 s (D-4) |
| Costo real | `resultado.costo` de la sesión, `{texto, exacto}` en USD, más el parcial mientras piensa | sale del `uso` que devuelve la API |
| Tope **acumulado** por instalación | no existe | etapa 3 (D-6) |

El gasto es del proveedor y de la clave de la empresa; esta capa solo lo **acota**. Ninguna ruta de lectura (`proveedores`,
`previa`, estado, hipotético) llama al proveedor.

### 4.4 Sin proveedor real en pruebas ni en el desarrollo

- **Costura de inyección** (`hoja_asistente.fijar_proveedores(fuente)`, un administrador de contexto para pruebas): por omisión
  vale `asistente.instalacion.proveedores_de_la_instalacion`. Las pruebas ponen `ProveedorGuionado` (sin red) con
  `nombre="claude"`, `modelo="claude-opus-5-5"`, `envia_fuera_del_equipo=True` (como `test_ui_hoja_asistente.py:62-72`) para que
  la tarifa exista sin cobrar nada.
- **Doble guardia**: un `autouse` en los archivos de prueba del asistente hace fallar `asistente.fabrica.proveedores` y
  `ProveedorClaude.turno` si se llaman sin la inyección (prueba negativa 4a-B18), y la guardia de red de `tests/conftest.py`
  (RV-17, RNF-18 d) sigue activa. Ninguna prueba abre la red.
- **Auditoría visual y demostraciones**: `scripts/auditoria_visual_asistente.py` (nuevo, solo desarrollo) arranca la API en
  `127.0.0.1` con la costura apuntando a un guion de `tests/fixtures`. **No** hay variable de entorno ni interruptor de "modo
  simulado" en el código de producción: una instalación no puede activarlo por error.
- **Prueba real** (`scripts/prueba_real_asistente.py` ya existe): solo con la autorización de gasto de Eugenio (D-2; T20).
- **Datos de prueba**: únicamente OF-001 (`plantilla_of001`, `NOMBRE_OF001`) y TI-001 (`caso_ti001`) y los pedidos ficticios de
  `tests/fixtures/asistente_pedidos.py` (`AMBIENTE`, `PEDIDO`). Nunca un libro, nombre de empresa ni cifra reales.

---

## 5. Contrato de API (etapa 1)

### 5.1 Reglas comunes

| Regla | Detalle |
|---|---|
| Módulos | `api/rutas/hoja_asistente.py` (rutas), `api/esquemas_hoja_asistente.py` (esquemas y proyecciones); lógica en `aplicacion/hoja_asistente*.py`; la API **no importa `ui`** ni los cinco módulos del asistente que cargan `ui.hoja` (solo el puente, vía `aplicacion`) |
| Clase de ruta | `class _RutaAsistente(RutaSinCache, RutaSinEco)` **en ese orden** (diseño de la hoja §1.3-7); `mensaje_por_omision` = «Los datos del asistente no tienen la forma esperada: elija un proveedor y escriba el pedido como texto.» |
| Acceso | `CuentaDelAsistente = Depends(cuenta_con(Accion.EDITAR_HOJA, MENSAJE_SOLO_CUENTA_IA))`: **solo cuenta con `EDITAR_HOJA`** (la acción de la clásica, `P:2252` según el diseño de la hoja; en la matriz solo el rol `arma`). Con `X-Silice-Clave` → **403** «El asistente de IA de la hoja se usa con una cuenta; la clave de API no sirve.»; sin sesión → 401; rol sin permiso (`revisa`, `administrador`) → 403; CSRF y `Origin` en los métodos que escriben (los comprueba `exigir_clave_o_sesion`) |
| Borrador | `_vivo(request, activa, id)` de `api/rutas/hoja.py`: borrador de otra ficha → **404** (no 403); abierto en otro caso → 409 «El caso cambió desde que abrió este borrador…» |
| Responsable | siempre `activa.usuario`. Los cuerpos llevan `extra="forbid"`: un campo `usuario`, `responsable`, `clave` o cualquier otro → 422 sin eco |
| Caché | `Cache-Control: no-store` en éxito **y** error |
| 422 | sin eco: nunca repite el pedido ni la propuesta; los mensajes de dominio (`HojaInvalida`, `DependenciaPendiente`) son del motor |
| Montos | `Monto {texto, exacto}` (2 decimales y exacto); ningún `float` en el JSON (prueba de recorrido). Los costos van en USD |
| Texto de la IA | solo en los campos marcados `ia:` en §5.2; el servidor no lo interpreta ni lo recorta salvo el tope de §5.2 |
| Tamaños | pedido ≤ 4 000 caracteres; `proveedor` ∈ {`claude`, `ollama`}; `propuesta` con `^P[0-9]{1,4}$`; respuesta del estado ≤ 64 propuestas (el tope de llamadas es 60) |

### 5.2 Esquemas

```
ProveedoresDelAsistente {
  activo: bool,                    # hay al menos uno disponible
  motivo: str | null,              # si activo=false: los motivos juntos y sin repetir (como P:1093-1096), enmascarados
  por_defecto: str | null,         # proveedor_por_defecto() si está disponible
  tope_sesion: Monto | null,       # USD; null = sin tope
  proveedores: [{ nombre, modelo: str | null, disponible: bool, motivo: str,
                  envia_fuera_del_equipo: bool | null, destino: str | null,      # "este equipo" | "Anthropic, en internet" | "{n} en {anfitrión}, fuera de este equipo"
                  tarifa: bool, estimacion: Monto | null, estimacion_supera_el_tope: bool }] }

PreviaDelPedido { destino: str, caracteres: int, truncada: bool, texto: str }

AsistenteEstado {
  estado: "sin_sesion" | "pensando" | "lista" | "pregunta" | "error",
  sesion: int | null,                       # número en ia_sesiones (clave para etapas 2 y 3)
  proveedor: str | null, modelo: str | null, destino: str | null,
  pedido: str | null,                       # el que escribió la persona
  progreso: { turno: int, turnos_max: int, segundos: int, costo: Monto } | null,   # solo pensando
  resultado: { motivo: str, mensaje: str, costo: Monto, turnos: int, llamadas: int,
               notas: [str] } | null,       # ia: mensaje de MensajesDelMotor; notas del modelo
  pregunta: str | null,                     # ia: texto ajeno
  error: { categoria: "sin_conexion"|"clave_invalida"|"tiempo"|"componente"|"base"|"otro", mensaje: str } | null,
  propuestas: [Propuesta],
  sobre_la_hoja_editada: bool,              # cada propuesta se aplicará sobre la hoja vigente (§3.6)
  fuente_sugerida: str | null,              # solo si hay aceptadas
  hay_aceptadas: bool }

Propuesta { id: "P1", tipo: "ambiente"|"fuente"|"punto"|"recorrido"|"partida"|"sin_partida",
            clave: str, descripcion: str,                 # ia: servicio.descripcion(...)
            estado: "pendiente"|"aceptada"|"editada"|"rechazada",
            supuestos: [{campo, motivo}], citas: [{campo, texto}],      # ia
            declarado: bool }

DecisionDePropuesta   (cuerpo)  { estado: "aceptada"|"editada"|"rechazada", rev: int | null }
RespuestaDeDecision             { resumen: Resumen, asistente: AsistenteEstado }
Hipotetico {
  rev: int, disponible: bool, mensaje: str | null,     # mensaje: HojaInvalida si no se puede calcular
  moneda: str, total_actual: Monto, total_si_acepta: Monto | null, diferencia: Monto | null,
  cambios_si_acepta: int | null,
  hallazgos: [{severidad, total}], hallazgos_total: int, pendientes: int }
```

`Resumen` y `Monto` son los de `api/esquemas_hoja.py`. El orden de `hallazgos` es el alfabético de la clásica (`P:1022`,
`sorted`). `diferencia` = `total_si_acepta − total_actual` en `Decimal`, con signo, calculada en el servidor.

### 5.3 Rutas

| # | Ruta | Cuerpo | Responde |
|---|---|---|---|
| A0 | `GET /v1/hoja/asistente/proveedores` | — | 200 `ProveedoresDelAsistente`. No gasta. No necesita borrador |
| A1 | `POST /v1/hoja/borradores/{id}/asistente/previa` | `{proveedor, pedido}` | 200 `PreviaDelPedido`. No gasta |
| A2 | `POST /v1/hoja/borradores/{id}/asistente` | `{rev, proveedor, pedido}` | **202** `AsistenteEstado` (`pensando`). Reemplaza una sesión terminada |
| A3 | `GET /v1/hoja/borradores/{id}/asistente` | — | 200 `AsistenteEstado` (`sin_sesion` si no hay: **no** es un error, para que el sondeo y F5 no sean 404) |
| A4 | `GET /v1/hoja/borradores/{id}/asistente/hipotetico` | — | 200 `Hipotetico`; 404 «No hay propuestas del asistente en este borrador.» si no hay sesión `lista` |
| A5 | `POST /v1/hoja/borradores/{id}/asistente/propuestas/{propuesta}` | `{estado, rev}` | 200 `RespuestaDeDecision` |
| A6 | `DELETE /v1/hoja/borradores/{id}/asistente` | — | 204, idempotente. Con `pensando` cancela; con otra cosa descarta lo pendiente (**lo aceptado se queda en el borrador**) |

### 5.4 Errores por ruta

| Situación | Código | Texto (con tildes: los compone la capa nueva; los del motor, tal cual) |
|---|---|---|
| sin sesión | 401 | el de siempre |
| clave de API | 403 | «El asistente de IA de la hoja se usa con una cuenta; la clave de API no sirve.» |
| rol sin `EDITAR_HOJA` | 403 | el de siempre |
| borrador ajeno o inexistente | 404 | `MENSAJE_FALTA` de la hoja |
| borrador de otro caso | 409 | `MENSAJE_OTRO_CASO` |
| `rev` desactualizado (A2, A5 salvo rechazar) | 409 | `MENSAJE_REV` |
| borrador ya guardado | 409 | «Este borrador ya se guardó como la versión {c}; abra esa versión para seguir.» |
| versión de solo lectura (A2) | 409 | «El asistente de IA no se abre en una versión de solo lectura: alguna partida ya no tiene composición vigente en el catálogo. Abra la versión vigente para usarlo.» (`P:1085`, caso 9i) |
| proveedor no disponible o desconocido (A1, A2) | 409 | «Elija un proveedor disponible.» (`P:763`); si no hay ninguno, el motivo de A0 |
| sin tarifa (A1, A2) | 409 | «No hay tarifa para el modelo {modelo}: pida al administrador agregarla.» (`P:769`) |
| falta el extra `ia` | 409 | `FALTA_EL_COMPONENTE` + «. Instálelo y vuelva a abrir Sílice.» |
| ya hay una petición en curso (A2) | 409 | «Ya hay una petición de IA en curso en este borrador: espere a que termine o cancélela.» |
| pedido vacío, largo, forma o campo extra (A1, A2, A5) | 422 | sin eco: «El pedido debe tener entre 1 y 4 000 caracteres.» / `mensaje_por_omision` |
| pedido con una clave | 422 | «El pedido parece contener una clave de acceso: quítela y vuelva a intentarlo. No se envió nada.» |
| propuesta inexistente (A5) | 404 | «Esa propuesta no existe en esta sesión.» |
| propuesta ya decidida (A5) | 409 | «{id} ya no está pendiente: ya se decidió.» (`P:844`, con tildes) |
| pregunta de la IA sin responder (A5) | 409 | «La IA hizo una pregunta que todavía no se responde: descarte la sesión o reformule su pedido.» |
| depende de otra pendiente (A5) | 409 | texto de `DependenciaPendiente`, tal cual |
| no cabe en la hoja editada (A5) | 409 | «{id} no se puede aplicar sobre la hoja tal como usted la dejó: {error}. Revise lo que editó a mano (por ejemplo, si quitó una fila que la propuesta usa) o rechace la propuesta. No se decidió nada.» (`P:850-856`) |
| ritmo por cuenta (A2) | 429 | «Hizo muchas peticiones al asistente en poco tiempo: espere unos minutos.» + `Retry-After` |
| sin cupo global (A2) | 503 | «El asistente está atendiendo otras sesiones: intente de nuevo en un momento.» + `Retry-After: 30` |
| la base no se pudo leer o escribir | 503 | `MENSAJE_BASE` (sin `orig`) |
| sin sesión del asistente (A4, A5) | 404 | «No hay una sesión del asistente en este borrador.» |

Los fallos del **proveedor** (sin conexión, clave rechazada, límite de tasa, plazo, rechazo del modelo) ocurren después del 202 y
llegan por A3 en `error` o `resultado.motivo`; el 429 y el 503 de arriba son del propio servidor (cupo y ritmo).

---

## 6. Interfaz

### 6.1 Colocación

El `<aside aria-label="Asistente de IA">` deja de estar vacío y oculto y pasa a ser un **desplegable (Carbon `Accordion`) cerrado de
fábrica**, colocado en `index.tsx` **entre la zona «Estado del borrador / Descargar Excel» y las pestañas** (hoy está debajo de
ellas, donde a 768 px de alto nunca se vería sin recorrer una tabla). Una sola fila cerrada (≈ 40 px) con el título y una
etiqueta de estado («2 propuestas pendientes», «La IA está trabajando…»). Se abre solo si hay sesión al cargar (F5 la recupera).

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

- **Sin anchos fijos en píxeles.** La rejilla interna es `grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr))`:
  a 1366 px caben formulario y resultado lado a lado; a 1056 px (≈ 800 px de contenido) y con **letra Grande o Muy grande**
  (`--silice-escala-letra` 1,25 y 1,5; el menú pasa a capa) se apila en una columna. `min-inline-size: 0` y `overflow-wrap:
  anywhere` en todo texto de la IA; ningún elemento del panel provoca desplazamiento horizontal de la **página** (criterio de
  T11, §7.6 de la hoja: `scrollWidth <= clientWidth`).
- **Sin desplazamiento interno propio** salvo el cuadro de «Lo que se enviará» (región con `role="region"`, `tabindex="0"`,
  `aria-label`, `max-block-size: 20rem`): el resto fluye con la página. Así no hay regiones con barra de desplazamiento
  invisibles al teclado.
- **Lista y no tabla** para las propuestas (`<ol aria-label="Propuestas de la IA">`): con texto largo de la IA y letra grande una
  tabla de tres columnas desbordaría.
- **Carbon g10, esquinas rectas, densidad `sm`, sin animación decorativa** (el `InlineLoading` es el de Carbon). Un solo `h1`
  en la página; el panel usa `h2` (`heading-compact-02`) «Asistente de IA: propone, usted decide» y `h3` (`heading-compact-01`) por
  bloque. **Sin verde ni rojo** (la diferencia de total es un número con signo y texto; el color nunca va solo).
- **Con el asistente apagado o sin el extra `ia`** el desplegable existe y, abierto, dice por qué (los motivos de A0) y que lo
  activa el administrador; no se oculta (el diseño de la hoja pedía "sin contenido muerto": un panel que explica por qué no
  funciona no es contenido muerto, y la clásica hace lo mismo, `P:1093-1096`).
- **Versión de solo lectura**: el cuerpo es el mensaje del caso 9i y no hay formulario.

### 6.2 Formulario

1. **Proveedor** — Carbon `Select` con los disponibles («Claude (claude-opus-5-5)», «Modelo local (…)»); preselecciona
   `por_defecto`. Los no disponibles **no son opciones**: salen como líneas de texto «No disponible: {nombre}: {motivo}»
   (copia de `P:1040-1043`). Un solo disponible: el `Select` sigue visible (la persona ve a dónde irá).
2. **Pedido** — `TextArea` con etiqueta visible «¿Qué necesita armar? (en sus palabras)», `maxLength = 4000`, contador «n de 4.000
   caracteres» (texto, en `aria-describedby`; no es `aria-live`), `rows = 4`, texto de ayuda con la advertencia de §4.2. **Se
   guarda solo en memoria del componente**: ni `localStorage` ni `sessionStorage` (puede traer datos de la empresa).
3. **Destino, estimación y tope** — tres líneas de texto que se recomponen al cambiar de proveedor (sin otra petición): «Destino:
   {destino}», «Estimación de costo por tarea (cota): {estimación} USD», «Tope por sesión (lo fija el administrador): {tope} USD |
   sin tope». Si `estimacion_supera_el_tope`: aviso `InlineNotification` de tipo `warning`: «La estimación supera el tope: la
   sesión se detendrá al alcanzar el tope y conservará lo que haya propuesto.»
4. **«Lo que se enviará»** — `Accordion` anidado cerrado; al abrirlo pide A1 (con una pausa de 600 ms tras la última tecla y
   solo mientras está abierto). Muestra destino, `caracteres` y el texto en un `<pre>` dentro de la región desplazable; si
   `truncada`, la frase de §4.2. Errores de A1 se muestran dentro del acordeón.
5. **Proponer** — botón primario, **deshabilitado** sin pedido, sin proveedor, con la hoja de solo lectura, mientras hay una
   petición en curso o cuando el proveedor no tiene tarifa (el servidor lo vuelve a comprobar). Al pulsarlo: pasa a «Proponiendo…»,
   el formulario queda de solo lectura (campos `readOnly`, no `disabled`, para no perder el foco) y el foco se queda en el botón.

### 6.3 Progreso de la IA (estado `pensando`)

- Un `InlineLoading` con «La IA está trabajando: turno {t} de {máx}. Llevo {costo} USD de un tope de {tope}.» y un botón
  secundario **Cancelar** (sin confirmación: no pierde nada de la hoja; el aviso dice que ya se pagó lo consumido).
- **`aria-live="polite"` en un solo `div role="status"`** que **siempre está montado** (de lo contrario los lectores no anuncian
  la primera vez). Se anuncia: al empezar («La IA empezó a trabajar.»), **al cambiar de turno** (máximo uno cada 10 s) y al
  terminar («La IA terminó: {n} propuestas pendientes.» / «La IA terminó sin propuestas.» / «La IA no pudo completar la tarea.»).
  Los segundos transcurridos y el sondeo **no** se anuncian.
- **Sondeo**: `GET …/asistente` cada 2 s mientras `pensando`; se pausa con la pestaña oculta y se hace una lectura al volver
  (`visibilitychange`); tres fallos seguidos detienen el sondeo y muestran «Se perdió la conexión con el servidor. Reintentar» (el
  trabajo sigue en el servidor). 401 → `alExpirar()`. 404 del borrador → el aviso «El borrador ya no está» de la página.
- Al montar el panel se hace **una lectura de A3**: si había sesión (F5, retomar borrador), se recupera tal cual.

### 6.4 Propuestas

Cada elemento de la lista:

- Numeración visible («1.»), `descripcion` (texto de la IA, escapado), una `Tag` con el **estado en texto** («pendiente»,
  «aceptada», «aceptada: edítela en Espacio y metrajes», «rechazada») y un ícono distinto por estado (el color nunca va solo).
- Si hay `supuestos`: «Supuestos de la IA: {campo}: {motivo}; …» (copia de `P:1012`).
- Si hay `citas`: un `<details>` nativo «Dónde lo dice el pedido» con cada `campo: «cita»`; mejora declarada (DV-IA-3).
- Botones **solo para `pendiente`**: «Aceptar», «Aceptar y editar», «Rechazar». Cada uno es `Button size="sm"`; su nombre accesible
  es el rótulo y `aria-describedby` apunta al texto de la propuesta (no se mete texto de la IA en `aria-label`).
- **Una por una** (RF-92): no hay «aceptar todas» (D-7).
- **Descartar lo pendiente** (al final de la lista): si hay pendientes, confirmación **en línea** («¿Descartar {n} propuestas
  pendientes? Lo ya aceptado se queda en la hoja.» [Descartar] [Seguir revisando]), con el mismo patrón y foco que «Descartar
  cambios» de `EstadoDelBorrador`; sin pendientes, descarta directo.
- **Qué pasa al decidir**: la fila pasa a su estado, se anuncia «{id}: {estado}.» en el `role="status"`, el **foco** va al primer
  botón «Aceptar» de la siguiente propuesta pendiente o, si no queda ninguna, al título del resultado (`h3` con `tabindex=-1`). Si
  se aceptó o editó, el panel llama a `alAceptar(resumen)` de la página (la misma función que usan las pestañas, `useBorrador.
  aplicar`): se actualizan `rev`, total y cambios, y las pestañas abiertas vuelven a leer su vista (ya lo hacen cuando cambia
  `rev`). Y pide de nuevo A4.
- **Aviso fijo** (si `sobre_la_hoja_editada`): «Usted editó la hoja a mano: cada propuesta se aplicará sobre la hoja tal como está
  ahora.»
- **Fuente**: si hay `fuente_sugerida` y el campo de fuente del diálogo de guardado está vacío, la página la prellena; nunca pisa
  lo escrito (`P:865`).

### 6.5 Resultado hipotético

Un bloque `h3` «Resultado si acepta lo pendiente», **calculado por el sistema, no por la IA**:

- **Total ahora** y **Total si acepta todo** como `{texto, exacto}`: `formatoEsVe(texto)` a la vista, `exacto` en `title` y en un
  texto `cds--visually-hidden` («Valor exacto …»), igual que el total del estado del borrador. La **diferencia** también (con signo,
  tal como la manda el servidor).
- «Hallazgos del auditor si acepta todo: {n} ({SEVERIDAD}: {k}, …)» (o «ninguno»); «Cambios sin guardar si acepta todo: {n}».
- Si `disponible` es `false`: «No se puede calcular el resultado si se aceptara todo: {mensaje}» (`P:1019`), en `role="status"`.
- Si no hay pendientes: se muestra el resultado de lo ya aceptado, rotulado «Resultado con lo aceptado».
- Se pide A4 al aparecer la lista y tras cada decisión; mientras se pide, se conserva el último valor con la etiqueta «Actualizando…»
  (no parpadea a vacío).
- **El front no calcula ni redondea**: ningún `Number`, `parseFloat`, `toFixed` ni `Intl.NumberFormat` sobre estos montos (prueba
  estática, §7).

### 6.6 Estados de carga, error y vacío

| Estado | Qué se ve |
|---|---|
| Leyendo proveedores / sesión | `EsqueletoPagina` con etiqueta «Cargando el asistente» dentro del desplegable |
| Sin proveedores / apagado / sin extra | motivos de A0 en texto; sin formulario |
| Solo lectura | caso 9i; sin formulario |
| `sin_sesion` | formulario |
| `pensando` | progreso (§6.3) |
| `lista` con propuestas | lista + resultado + descartar |
| `lista` sin propuestas | «La IA terminó sin propuestas.» + `mensaje` y `notas` del modelo (escapadas) + formulario para reformular |
| `lista` por tope | la frase del motivo con tildes: «Se alcanzó el tope de costo; se conservan las propuestas.» (tabla `motivo → texto` en `logica.ts`; si llega un motivo desconocido se muestra el `mensaje` del motor) |
| `pregunta` | aviso `warning` «Pregunta generada por la IA: no escriba contraseñas, claves ni precios.» + texto escapado + «Por ahora esta versión del asistente no permite responder: descarte la sesión o escriba un pedido con más detalle.» (la etapa 2 agrega el cuadro de respuesta) |
| `error` | `AvisoError`-like por categoría: sin_conexion «No hay conexión con el proveedor de IA.», clave_invalida «La clave de IA fue rechazada: pida al administrador que la revise.», tiempo «El proveedor tardó demasiado: lo ya propuesto se conservó.», componente «Falta el componente del asistente en este equipo: pídalo a quien instaló Sílice.», base «No se pudo leer o escribir el caso. …», otro «El asistente no pudo completar la tarea.» + las propuestas que se conservaron |
| 409 «ya se guardó» | «Este borrador ya se guardó: abra esa versión para seguir.» |
| 404 del borrador | el aviso «El borrador ya no está» de la página |
| 401 | `alExpirar()` |

### 6.7 Teclado y accesibilidad (D2)

- Orden natural de tabulación; ninguna acción sin teclado; Carbon aporta foco visible. **Esc no cancela nada** (una cancelación por
  accidente cuesta dinero); «Cancelar» es un botón.
- Al abrir el desplegable el foco se queda en su cabecera; al cerrarlo, también. Al terminar la IA el foco **no se roba**: se anuncia
  por `role="status"` y la persona decide (si estaba en el botón «Proponer», sigue allí).
- Etiquetas visibles para todos los campos; `aria-invalid` + `aria-describedby` en el pedido cuando el servidor lo rechaza.
- Un estado cada vez: no hay `aria-live` anidados ni más de uno por panel.
- Contraste y tamaño: tokens del sistema; sin tamaños en px para texto.

### 6.8 Textos (todos con tildes; los del motor, tal cual)

Títulos: «Asistente de IA: propone, usted decide», «Resultado si acepta lo pendiente», «Propuestas de la IA». Botones: «Proponer»,
«Cancelar», «Aceptar», «Aceptar y editar», «Rechazar», «Descartar lo pendiente», «Reintentar». Etiquetas: «Proveedor», «¿Qué necesita
armar? (en sus palabras)», «Lo que se enviará». Descripciones y notas de la IA: lo que manda el servidor, como **texto**.

### 6.9 Qué cambia en `index.tsx`

1. Quitar `<aside aria-label="Asistente de IA" hidden />` del final y montar `<PanelDelAsistente borrador={…} alAplicar={aplicar}
   alRecargar={refrescar} alUsarFuente={…} />` entre `BotonExcel` y `<ContextoAuditoria.Provider>`; el panel renderiza su propio
   `<aside aria-label="Asistente de IA">`.
2. `hayCambios` para `beforeunload` pasa a `hayCambios || asistenteConPendientes` (el panel avisa a la página con un callback):
   salir sin decidir pierde las propuestas pendientes.
3. El diálogo de guardado recibe la `fuente_sugerida` solo si su campo está vacío.
4. `Hoja.test.tsx:256` se reescribe (el aside ya no es vacío ni está oculto).

### 6.10 Estructura de archivos del front

`frontend-desktop/src/paginas/hoja/asistente/`: `PanelDelAsistente.tsx` (el `aside`, el desplegable, el orquestador de estados),
`FormularioDelAsistente.tsx`, `ProgresoDeLaIA.tsx`, `ListaDePropuestas.tsx`, `ResultadoHipotetico.tsx`, `useAsistente.ts`
(máquina de estados, sondeo, acciones), `logica.ts` (tipos de §5.2, tabla motivo → texto, categorías de error, helpers puros) con
`logica.test.ts`, `asistente.scss`, y una prueba por componente. Datos de prueba en `datosDePrueba.ts` del propio directorio
(ficticios). **No** se toca `src/api/tipos.ts` (hay cambios ajenos sin confirmar): los tipos viven en `logica.ts`.

---

## 7. Pruebas por capa y criterios de aceptación

### 7.1 Principios

TDD con rojo visto; oráculos escritos a mano desde la clásica, la ERS, `precios_ia.json` o `core`, nunca del código bajo prueba;
`-W error`, cero omitidas; **ninguna prueba abre la red** (§4.4). Casos: OF-001 y TI-001. La suite completa no se corre en
sub-rebanadas (manual §1.6); las pruebas `test_ui_*` de AppTest que agotan 3 s en este equipo se anotan, no se "arreglan".

### 7.2 Backend (ids 4a-B*, estilo 3b)

| Id | Qué prueba | Oráculo |
|---|---|---|
| B1 | **puente**: nombres, orden y bandera `compare` de los campos de las dos clases `Borrador` | lista literal a mano de los nueve campos; ida y vuelta igual (OF-001 y TI-001); `reglas_extra` no cuenta |
| B2 | **arquitectura**: solo el puente nombra `asistente.servicio/orquestador/propuestas/privacidad/validacion`, y dentro de funciones; `import api.main` en subproceso no deja `asistente.servicio` ni `ui` en `sys.modules` | barrido AST del repositorio y salida del subproceso `[]` |
| B3 | A0 sin clave: serializa y busca la clave de prueba y `sk-ant` | ausentes; apagado → `activo=false` y el motivo exacto «El asistente esta apagado: lo activa el administrador de la instalacion.»; sin extra → `FALTA_EL_COMPONENTE`; un proveedor no disponible con su motivo |
| B4 | acceso: `ana` (arma) 200; `rita` (revisa) y `admin` 403; sin sesión 401; clave de API 403 con el texto; CSRF/Origin en los POST; `no-store` en éxito y error | fixtures de `tests/fixtures/sesion_web.py` |
| B5 | A1: el texto es el de `primer_mensaje(PEDIDO, borrador)`; ningún precio ni el nombre del proyecto ni de la persona; `truncada` y `caracteres` a la frontera de 100 000 | cadena literal construida a mano |
| B6 | A2 feliz: 202 → sondeo → `lista` con 1 propuesta; el borrador no cambia (igualdad exacta y mismo `rev`) | guion `AMBIENTE`; filas `ia_*` esperadas |
| B7 | pedido vacío, de 4 001 caracteres y con `sk-ant-`: 422 sin eco; el de la clave no llama al proveedor ni crea fila `ia_sesiones` | conteo SQL y `recibidos == []` |
| B8 | precondiciones: solo lectura (9i), sin proveedor, proveedor desconocido, sin tarifa, falta el extra, ya hay una petición | los textos de §5.4 |
| B9 | concurrencia: dos POST simultáneos al mismo borrador (proveedor que espera una señal) → uno 202, uno 409; tercera sesión en otro borrador con `EN_VUELO=2` ocupados → 503 con `Retry-After`; ritmo: la 21.ª en una hora → 429 (reloj inyectado); los turnos abandonados cuentan en el cupo | hilos y barreras, sin `sleep` |
| B10 | plazos: proveedor colgado → `error` categoría `tiempo` con plazos pequeños inyectados; propuestas previas conservadas; **otra edición E3 funciona mientras se espera** (el cerrojo del borrador está libre) | |
| B11 | cancelar: DELETE durante `pensando` → 204; A3 `sin_sesion`; al volver el hilo el resultado no reaparece; `ia_sesiones.motivo_fin` cerrado; borrador intacto | |
| B12 | ciclo de vida: DELETE del borrador, E11 `reemplazar`, vencimiento a las 8 h, expulsión, `olvidar(huella)`, cambio de caso, cierre de sesión → la sesión desaparece y el trabajo en vuelo se cancela; otra ficha en A2 a A6 → 404, nunca 403 | reloj inyectado |
| B13 | la sesión nunca está en el borrador: `BorradorVivo` sin campos nuevos; `tamano` y `pickle` iguales antes y después de proponer; recorrido de objetos de la sesión buscando la clave de prueba | |
| B14 | errores del proveedor: `sin_conexion`, `clave_invalida`, `otro` con la clave dentro del mensaje; `ImportError`; `SQLAlchemyError` → `error` con categoría y texto saneado; propuestas previas conservadas | la clave de prueba no aparece en ninguna respuesta |
| B15 | el borrador cambia mientras la IA piensa: queda `sobre_la_hoja_editada` y decidir conserva la edición | OF-001 con `administracion = 0.20` (total ≈ 2 821,42, P13 de la hoja) |
| B16 | recorrido del JSON de A0 a A5: sin `float`; todo monto es `Monto` | |
| B17 | `pregunta`: guion con `preguntar_al_usuario` → estado `pregunta`; decidir da 409; DELETE la descarta; el texto no se interpreta | |
| B18 | **ningún proveedor real**: sin la costura, `proveedores_de_la_instalacion` y `ProveedorClaude.turno` fallan en estas pruebas (prueba negativa) | |
| B19 | aceptar: `rev`+1; fila con `OrigenMedida` `ia` y referencia literal `modelo=claude-opus-5-5; propuesta=P1; proveedor=claude; sesion=N`; partida en `items_base` con `ia:N:P1` y su APU del catálogo | construido a mano; OF-001 y TI-001 |
| B20 | rechazar: borrador idéntico y `rev` igual; `ia_propuestas.estado = rechazada`, `decidida_por = "Nombre <login>"` | volcado `ia_*` |
| B21 | `rev` viejo → 409 y nada decidido ni registrado; doble decisión → 409; dependencia → 409 con el texto del motor; no cabe en la hoja editada → 409; base que falla → 503 sin cambios (decisión **no** registrada) | volcado `ia_*` y borrador antes/después |
| B22 | hipotético: `disponible=false` con `HojaInvalida`; `diferencia` exacta en `Decimal`; caché por `(estados, rev)` (un segundo GET no recalcula) | cálculo a mano |
| B23 | responsable: un campo `usuario`/`responsable` en el cuerpo → 422 sin eco; la decisión lleva la cuenta | |
| B24 | trazabilidad e2e: aceptar y guardar por S1 → versión con filas `esp_origenes` tipo `ia`, `RegistroCambio.responsable` = la cuenta, cadena íntegra, `ia_sesiones.version_guardada` = la nueva (gancho D-3), `anexo_ia` incluye la sesión; si el gancho falla, la versión sigue guardada y S1 trae `avisos` | réplica de `test_ui_hoja_responsable.py:97-126` |
| B25 | tope de costo: el turno exacto en que el costo acumulado alcanza el tope (cálculo a mano con la tarifa), `motivo = tope_de_costo`, propuestas conservadas; turnos 12 y llamadas 60 en la frontera | réplica de RF-94 |
| B26 | **privacidad e2e**: todo lo que recibe el proveedor en todos los turnos (`ProveedorGuionado.recibidos`) no contiene ninguna cifra de precio ni total de OF-001 (lista literal), ni los nombres del proyecto, de la empresa ni `ana`, ni la clave de prueba; sí el alias `P1` | lista literal a mano |
| B27 | la clave de IA nunca aparece en la base, en `ia_*`, en registros (`caplog`), en el 422 ni en `docs/api.json` | RNF-18 c |
| B28 | `hoja_edicion.cambiar` y `antes_de_reemplazar`: las siete ediciones existentes pasan sin cambios; un fallo en el gancho no cambia el borrador | |

### 7.3 Paridad con la clásica (4a-5)

La paridad se hace contra **el motor llamado directamente sobre `ui.hoja.Borrador`** (lo que la clásica hace por dentro), no contra
`AppTest` (que en este equipo agota su espera). Mismo guion de `ProveedorGuionado`, mismo caso:

- Mismas propuestas (`id`, `tipo`, `clave`, `descripcion` = `servicio.descripcion`, `supuestos`) y mismo orden.
- Mismo `resumen_hipotetico` (total y hallazgos por severidad) que `servicio.resumen_hipotetico(con_r17(hipotetico(...)))`.
- Mismo borrador resultante al aceptar la secuencia P1, P2 en las dos rutas (igualdad de `Borrador` tras convertir).
- Mismas filas `ia_*` (`registro.volcado`, que omite las marcas de tiempo).
- Mismos mensajes: igualdad de cadena para lo que sale del motor; igualdad tras `normalizar_texto` (sin tildes ni mayúsculas) para
  lo que compone la capa nueva y en la clásica está en `ui/paginas/hoja.py`.
- Una corroboración **no bloqueante** con `AppTest` queda como opcional si el equipo la soporta; el veredicto no depende de ella.

### 7.4 Frontend (ids 4a-F*)

| Id | Qué prueba |
|---|---|
| F1 | formulario: preselecciona `por_defecto`; los no disponibles son texto y no opciones; «Proponer» deshabilitado sin pedido, sin proveedor, sin tarifa y en solo lectura; el contador y `maxLength` |
| F2 | destino, estimación y tope se recomponen al cambiar de proveedor sin otra petición; el aviso de estimación sobre el tope sale de `estimacion_supera_el_tope` (el front no compara números) |
| F3 | «Lo que se enviará»: pide A1 solo abierto y con la pausa de 600 ms; muestra `truncada` y el total |
| F4 | proponer: `fetch` simulado → 202 → sondeo con relojes falsos → `lista`; pausa del sondeo con pestaña oculta; tres fallos detienen el sondeo; 401 → `alExpirar`; unmount limpia el temporizador |
| F5 | `role="status"` siempre montado; anuncia inicio, cambio de turno (≤ 1 cada 10 s) y fin; **no** anuncia el sondeo ni los segundos |
| F6 | cancelar: DELETE y vuelve al formulario sin esperar el hilo |
| F7 | lista: botones solo en `pendiente`; estado como texto e ícono; foco a la siguiente pendiente o al título del resultado; anuncio de la decisión |
| F8 | decisiones: aceptar llama a `alAplicar(resumen)` con el `rev` enviado; 409 por `rev` → recarga; 409 «ya no está pendiente»; 409 por hoja editada muestra el texto del servidor |
| F9 | descartar lo pendiente: confirmación en línea con pendientes; directo sin ellas; lo aceptado se queda |
| F10 | resultado hipotético: `formatoEsVe` + `exacto` en `title` y texto oculto; diferencia con signo; `disponible=false`; sin pendientes; **prueba estática** de que ningún archivo de `asistente/` usa `Number(`, `parseFloat`, `toFixed` ni `Intl.NumberFormat` sobre montos |
| F11 | texto de la IA escapado: una descripción con `<img src=x onerror=…>`, `[x](http://…)` y `![x](http://…)` se ve como texto, sin nodos `img` ni `a`; la pregunta lleva el rótulo |
| F12 | `pregunta`, `error` por categoría, `lista` sin propuestas, `lista` por tope: el texto con tildes de la tabla `motivo → texto`; todo `MotivoFin` tiene entrada (lista literal de los once valores) |
| F13 | persistencia: tras proponer, `localStorage` y `sessionStorage` quedan vacíos de pedido, propuestas y claves; ninguna petición del navegador contiene la clave |
| F14 | F5 / retomar: al montar se lee A3 y se recupera la sesión; el desplegable se abre solo si hay sesión |
| F15 | la página: con propuestas pendientes `beforeunload` avisa; la `fuente_sugerida` prellena solo un campo vacío; el `aside` ya no está oculto ni vacío |
| F16 | estilos (como `estilosPlano.test.ts`): sin `px` en tamaños de texto del panel, `min-inline-size: 0`, `overflow-wrap: anywhere`, `auto-fit/minmax(min(100%, …))` presentes |

### 7.5 Auditoría visual (4a-6; con navegador, perfil propio, `127.0.0.1`, cierre por PID)

Con el guion simulado: 1366×768 y 1056 px, letra Normal, Grande y Muy grande: `scrollWidth <= clientWidth` en cada estado
(`sin_sesion`, `pensando`, `lista` con 3 y con 30 propuestas, `error`, `pregunta`, vacío); recorrido solo con teclado; foco visible;
un solo `h1`; el cuadro de «Lo que se enviará» alcanzable con teclado; el desplegable no empuja las pestañas fuera de pantalla.

### 7.6 Criterios de aceptación (P-n)

(No son los P1 a P39 de la hoja; llevan guion.)

| Id | Criterio | Oráculo | Sub-rebanada |
|---|---|---|---|
| P-1 | A0 lista proveedores sin ningún dato secreto y con los motivos de los no disponibles | B3 | 4a-1 |
| P-2 | La estimación de Opus 5.5 es **1,2144 USD exacta** (texto «1.21») y el tope 2.00 | (10 000×4 + 3 000×20 + 6 000×0,20) / 10⁶ = 0,1012; ×12 | 4a-1 |
| P-3 | La vista previa es exactamente `primer_mensaje(pedido, borrador)` y no trae precios, montos, nombre del proyecto ni de personas | B5 | 4a-1 |
| P-4 | Proponer con guion no cambia el borrador (igualdad exacta, mismo `rev`) y deja las filas `ia_*` esperadas | B6 | 4a-1 |
| P-5 | Pedido vacío, largo o con clave: 422 sin eco; el de la clave no llega al proveedor ni a la base | B7 | 4a-1 |
| P-6 | Solo lectura, sin proveedor, sin tarifa, sin extra y "ya en curso" dan su 409 con el texto de §5.4 | B8 | 4a-1 |
| P-7 | Una petición por borrador, tope global (503), ritmo (429) | B9 | 4a-1 |
| P-8 | Plazo vencido y cancelación terminan la sesión sin perder lo propuesto ni bloquear las ediciones | B10, B11 | 4a-1 |
| P-9 | La sesión muere con el borrador por todos los caminos y es invisible para otra ficha (404) | B12 | 4a-1 |
| P-10 | La sesión nunca se guarda dentro del borrador y la clave nunca está en la sesión | B13, B27 | 4a-1 |
| P-11 | Los fallos del proveedor (cuatro categorías) y de la base llegan como `error`, saneados | B14 | 4a-1 |
| P-12 | Aceptar entra al borrador con origen IA, sube `rev`, completa el APU de una partida y es todo o nada | B19, B21 | 4a-2 |
| P-13 | Rechazar deja el borrador idéntico; la decisión queda con la cuenta como autora | B20, B23 | 4a-2 |
| P-14 | Con la hoja editada a mano las ediciones se conservan al aceptar; si no cabe, 409 sin decidir nada | B15, B21 | 4a-2 |
| P-15 | El resultado hipotético coincide con el motor sobre OF-001 y TI-001, con la diferencia exacta y `disponible=false` cuando no se puede | B22 | 4a-2 |
| P-16 | Guardar tras aceptar deja la versión con origen IA, responsable humano, cadena íntegra, sesión marcada y `ia.json` | B24 | 4a-2 |
| P-17 | El tope de costo detiene la sesión en el turno exacto y conserva lo propuesto | B25 | 4a-2 |
| P-18 | Paridad con el motor directo: mismas propuestas, hipotético, borrador y `ia_*` en OF-001 y TI-001 | §7.3 | 4a-5 |
| P-19 | Lo que recibe el proveedor, en todos los turnos, cumple la lista blanca | B26 | 4a-5 |
| P-20 | `git diff <base>..HEAD -- asistente ui core` vacío; el resultado de `test_experimento_congelado_vigente.py` no cambia | `git diff` | todas |
| P-21 | Formulario, progreso y errores accesibles y completos | F1 a F6, F12 | 4a-3 |
| P-22 | Lista, decisiones, foco y anuncios | F7 a F9, F11 | 4a-4 |
| P-23 | Montos en es-VE con el exacto accesible; ni `Number` ni `parseFloat` ni `toFixed` | F10 | 4a-4 |
| P-24 | Nada del asistente en `localStorage`/`sessionStorage`; la clave nunca llega al navegador | F13, B27 | 4a-3/4 |
| P-25 | F5 recupera la sesión; salir con pendientes avisa | F14, F15 | 4a-4 |
| P-26 | 1366×768 y 1056 px, letra Normal/Grande/Muy grande, sin desplazamiento horizontal de la página; solo teclado | §7.5 | 4a-6 |
| P-27 | Ninguna prueba abre la red; la prueba real espera la autorización | B18, D-2 | 4a-7 |

---

## 8. Sub-rebanadas, dependencias y paralelismo

| Sub-rebanada | Hace | Archivos suyos | Depende de | Pruebas |
|---|---|---|---|---|
| **4a-1** backend: puente, proveedores, previa, proponer, estado, descartar | `hoja_asistente_puente.py`, `hoja_asistente.py` (sesión, ciclo de vida, `al_quitar`), `hoja_asistente_trabajo.py`, `hoja_edicion.cambiar` público; rutas A0 a A3 y A6 | `aplicacion/hoja_asistente*.py`, `aplicacion/hoja_edicion.py` (solo `cambiar`), `api/rutas/hoja_asistente.py`, `api/esquemas_hoja_asistente.py`, `tests/unit/test_aplicacion_hoja_asistente*.py`, `tests/unit/test_api_hoja_asistente*.py`, `docs/bitacora/2026-10-2x-hoja-4a1-*` | este diseño aprobado | B1 a B14, B16 a B18, B27, B28; P-1 a P-11 |
| **4a-2** backend: decidir, hipotético, gancho de guardado | A4 y A5, `decidir` de dos fases, `antes_de_reemplazar`, `fuente_sugerida`, `hoja_guardado.al_guardar` y el campo `avisos` | mismos archivos + `aplicacion/hoja_guardado.py` | 4a-1 | B15, B19 a B25; P-12 a P-17 |
| **4a-3** front: formulario y progreso | `useAsistente`, `PanelDelAsistente`, `FormularioDelAsistente`, `ProgresoDeLaIA`, montaje en `index.tsx` | `frontend-desktop/src/paginas/hoja/asistente/**`, `index.tsx`, `Hoja.test.tsx` | solo el **contrato de §5** (fetch simulado) | F1 a F6, F12 (parte), F13, F14, F16; P-21, P-24 |
| **4a-4** front: propuestas, decisiones, hipotético | `ListaDePropuestas`, `ResultadoHipotetico`, foco, anuncios, `beforeunload`, fuente sugerida | mismo directorio + `index.tsx` | 4a-3 (y el contrato de A4/A5) | F7 a F11, F12 (resto), F15; P-22, P-23, P-25 |
| **4a-5** paridad y privacidad e2e | las pruebas de §7.3 y B26 con el servidor real y el guion | `tests/unit/test_aplicacion_hoja_asistente_paridad.py`, `tests/unit/test_api_hoja_asistente_privacidad.py` | 4a-2 | P-18, P-19, P-20 |
| **4a-6** auditoría visual y registro de paridad | `scripts/auditoria_visual_asistente.py`, medición con navegador, bitácora `2026-10-2x-hoja-4a-paridad.md` | `scripts/auditoria_visual_asistente.py`, `docs/bitacora/**` | 4a-4 y 4a-5 | P-26 |
| **4a-7** prueba real | una sesión real, con el tope de gasto que autorice Eugenio, sobre OF-001; se anota el costo real | `scripts/prueba_real_asistente.py` (ya existe) | **D-2 (BLOQUEADA)** | P-27 |

**Orden y paralelismo**

```
4a-1 ──▶ 4a-2 ──▶ 4a-5 ─────────────┐
  ║                                  ├─▶ 4a-6 ─▶ (4a-7 si D-2)
4a-3 ──▶ 4a-4 ─────────────────────┘
```

- **4a-1 y 4a-3 corren en paralelo desde el primer día**: el front trabaja contra el contrato de §5 con `fetch` simulado y no
  espera al servidor; si 4a-1 desvía el contrato, lo corrige en `docs/bitacora/…-hoja-4a-contrato-rutas.md` (patrón de las
  rebanadas 3b a 3e) y avisa.
- 4a-2 es secuencial con 4a-1 (mismo módulo `hoja_asistente.py`); lo hace el mismo implementador para evitar choques.
- 4a-4 es secuencial con 4a-3 (mismo directorio); **4a-5 corre en paralelo con 4a-4** (archivos de prueba distintos).
- Un solo árbol de trabajo: cada agente toca solo sus carpetas; `index.tsx` lo editan 4a-3 y luego 4a-4 en orden, nunca a la vez.
  Los agentes de zoom e indicadores trabajan en `src/visor` y `src/indicadores`, que este diseño no toca.
- Cada sub-rebanada pasa implementador → árbitro antes de empezar la siguiente que dependa de ella.

**Roles sugeridos:** implementador de backend (Python), implementador de front (TypeScript/React), árbitro (manual del árbitro).

---

## 9. Etapas 2 y 3: ganchos que deja la etapa 1

**Etapa 2 (preguntas y cierre)**

| Gancho | Dónde queda hecho en la etapa 1 |
|---|---|
| Estado `pregunta` | existe en la máquina de estados, en `AsistenteEstado.pregunta` y en el panel (solo lectura) |
| Continuación pausada | se conserva en `SesionDeAsistente.resultado.continuacion`; `servicio.responder(sesion, texto, registro, proveedor=…)` ya existe y soltar el proveedor también |
| Ruta de respuesta | `POST …/asistente/respuesta {texto \| null}` (null cancela, caso 9h): sería un trabajo en segundo plano con las mismas reglas de plazo, cancelación y cupo; usa `ProveedorAcotado` y el **proveedor vigente por nombre** (si ya no está o cambió el modelo, la sesión se cancela con el texto de `P:910`); la respuesta con una clave se rechaza (`contiene_secreto`, ya en el orquestador) |
| Cierre al guardar | el gancho `al_guardar` y la lista `aceptadas` (D-3); la etapa 2 solo agrega el mensaje en pantalla |
| Número de sesión | `AsistenteEstado.sesion` en todas las respuestas |

**Etapa 3 (historial y costos)**

| Gancho | Dónde |
|---|---|
| Datos | el registro `ia_*` ya guarda sesión, turnos (uso y costo), llamadas, propuestas, decisiones y versión guardada; no hace falta tabla nueva |
| Lectura | `GET /v1/hoja/asistente/historial?proyecto=` y `…/costos` sobre `registro.volcado`/consultas propias; clave de API o sesión con `EDITAR_HOJA` (solo lectura) |
| Tope acumulado | D-6; usa `ia_turnos` (suma de costos por día) y se comprueba en A2 antes de reservar cupo |
| Pantalla | un segundo `h3` o pestaña del panel; los `Monto` y el patrón de `TablaDensa` |

---

## 10. Riesgos

| # | Riesgo | Efecto | Mitigación | Estado |
|---|---|---|---|---|
| R-A1 | **Deriva del puente**: alguien agrega un campo a una sola de las dos clases `Borrador` | el asistente trabajaría con un borrador incompleto | B1 con lista literal; el puente se borra al repuntar el asistente (D-1) | mitigado |
| R-A2 | **Hilos de turno colgados** (el SDK no tiene plazo propio) | cupos ocupados y posible cobro de un turno no registrado | plazo por turno y total; los hilos abandonados cuentan en `EN_VUELO`; texto honesto; D-5 (plazo en el cliente de Claude) | declarado |
| R-A3 | **Gasto**: una sesión consume hasta el tope aunque la persona se vaya | USD | tope por sesión, estimación previa, cancelar, ritmo por cuenta; el tope acumulado es de etapa 3 (D-6) | declarado |
| R-A4 | **Pérdida de la sesión** al salir de la hoja o reiniciar la API (el borrador sin cambios se descarta) | propuestas pagadas y no decididas se pierden | `beforeunload` con pendientes; aviso en el panel; el borrador con aceptadas se conserva y su sesión con él; el registro `ia_*` queda | declarado |
| R-A5 | **Texto ajeno** de la IA o de un DXF en la pantalla (inyección, imágenes, enlaces) | exfiltración por renderizado | solo texto escapado, nada de Markdown/HTML, sin `a`/`img`; F11 | mitigado |
| R-A6 | **El pedido lleva datos personales o una clave** | fuga al proveedor, a la base y al paquete | rechazo de claves antes de enviar (§4.2); advertencia permanente; vista previa del texto exacto | parcial: los datos personales no se filtran (límite de S4 §8.1) |
| R-A7 | **Hueco de `ia.json`** si no se marca la sesión al guardar | trazabilidad incompleta en el paquete | gancho de D-3 | abierto hasta D-3 |
| R-A8 | **Dos verdades**: el pegamento reescrito diverge del de la clásica | resultados distintos | paridad con el motor directo (§7.3); el pegamento duplicado se retira con Streamlit | declarado |
| R-A9 | **Una decisión registrada sin su efecto** si falla la base entre el registro y el borrador | auditoría inconsistente | `decidir` en dos fases: calcular, completar, registrar, reemplazar; B21 | mitigado |
| R-A10 | **Carga de la API**: ejecutor propio más el grupo de hilos | latencia de otras rutas | `EN_VUELO = 2`; el sondeo es una lectura en memoria; el trabajo no usa la sesión de la petición | por medir (4a-6) |
| R-A11 | **El congelado** | RS-9 | 0 bytes en `asistente/`, `ui/`, `core/` (P-20); el puente evita editarlos | mitigado |
| R-A12 | **Guardias de arquitectura** deben enmendarse (§12) | CI en rojo si se olvida | el texto exacto está en §12 y lo aplica el orquestador antes de integrar 4a-1 | abierto |
| R-A13 | **Modelo local (Ollama) en pausa por RS-8**: `disponible()` pregunta a la red local | A0 lento (≤ 5 s) si hay modelo local configurado | A0 es la única ruta que lo hace; el front la pide una vez al abrir el panel | declarado |
| R-A14 | **Una sesión con la hoja ya guardada** | decisiones sobre un borrador cerrado | 409 «ya se guardó» en A2 y A5; la sesión sigue visible hasta que el borrador salga | mitigado |
| R-A15 | **Sondeo y varias pestañas del navegador** sobre el mismo borrador | lecturas repetidas | lectura barata en memoria; `rev` protege las escrituras | declarado |

---

## 11. Decisiones abiertas (recomendación conservadora y reversible)

| Id | Decisión | Quién | Recomendación | Si se elige otra cosa |
|---|---|---|---|---|
| **D-1** | Cómo llega la capa nueva a `asistente/*`, que opera sobre `ui.hoja.Borrador` y tiene cuatro archivos congelados que lo importan. **P**: puente perezoso con conversión campo a campo, sin tocar nada congelado. **R**: repuntar `asistente/*` a `aplicacion.hoja` y re-congelar (exige revocar RS-9) | Eugenio (y el tutor si el protocolo es suyo) | **P** ahora. **R** cuando se retire Streamlit, porque entonces `ui/hoja.py` desaparece y los cinco módulos tendrán que repuntarse de todos modos | R: se borra el puente (§3.1-4) y cambian cinco archivos del asistente; el congelado se re-congela en un commit aparte con árbol limpio |
| **D-2** | Autorización de gasto para la **prueba real** (4a-7) y para cualquier demostración con un proveedor real. Mientras no exista, nadie llama a un proveedor real | Eugenio | **No autorizar todavía**; cuando se autorice, un tope explícito (por ejemplo ≤ 3 USD en total), una sola sesión sobre OF-001 y el costo real anotado en la bitácora | Autorizar antes: 4a-7 se adelanta; el resto no cambia |
| **D-3** | **Adelantar el cierre de sesión al guardar** (solo servidor, sin pantalla) a la etapa 1, para no dejar versiones guardadas con origen IA cuya sesión no sale en `ia.json` | Eugenio | **Sí**: son ~20 líneas en `hoja_guardado.py` y no cambian lo que se ve | No: la etapa 1 debe avisar en el panel «No guarde versiones con propuestas de la IA hasta la etapa 2» y la ERS declara el hueco |
| **D-4** | Topes y plazos supuestos: `EN_VUELO = 2`, 20 peticiones por hora por cuenta, `PLAZO_POR_TURNO = 120 s`, `PLAZO_TOTAL = 300 s`, pedido ≤ 4 000 caracteres, sondeo cada 2 s, estimación y tope de fábrica (2 USD) | Eugenio | adoptarlos como supuestos declarados y ajustarlos con la medición de 4a-6 y la prueba real | cambiar números en `aplicacion/hoja_asistente_trabajo.py` y `api/esquemas_hoja_asistente.py` |
| **D-5** | Poner un `timeout` real en el cliente de Claude (`claude.py:169`, congelado) para que un turno colgado muera de verdad y no deje hilos ni cobros sin registrar | Eugenio (RS-9) | dejarlo para el re-congelado de D-1/R; mientras tanto vale la envoltura | hacerlo ahora: edición mínima de un archivo congelado + re-congelar |
| **D-6** | Tope de costo **acumulado** por instalación (día o mes), además del tope por sesión | Eugenio | etapa 3, leyendo `ia_turnos`; en la etapa 1 solo el tope por sesión y el ritmo por cuenta | adelantarlo: una consulta a `ia_turnos` en A2 y un campo en la configuración del administrador |
| **D-7** | ¿«Aceptar todas»? | Eugenio | **No**: RF-92 pide decidir una por una; el resultado hipotético ya dice qué pasa si se acepta todo | un botón con confirmación que llame a A5 en orden |

Decisiones de ingeniería ya tomadas (informan, no esperan): sesión atada al borrador y no dentro de él; trabajo en segundo plano con
sondeo; operación `decidir` propia en dos fases; acceso por `EDITAR_HOJA` solo con cuenta; preguntas de la IA visibles y no
respondibles en la etapa 1; panel como desplegable entre el estado y las pestañas; lista y no tabla; citas visibles; resultado
hipotético con diferencia exacta calculada en el servidor.

### 11.1 Diferencias deliberadas con la clásica

| # | Diferencia | Motivo |
|---|---|---|
| DV-IA-1 | La llamada es en segundo plano con progreso y cancelación (la clásica bloqueaba la pantalla) | no ocupar un hilo de la API minutos |
| DV-IA-2 | El pedido se limita a 4 000 caracteres y se rechaza si parece llevar una clave | §1.6 |
| DV-IA-3 | Se muestran las citas del pedido que respaldan cada cifra | RF-91; verificar es parte de decidir |
| DV-IA-4 | El resultado hipotético trae el total actual, la diferencia exacta y los cambios | pedido de Eugenio; la clásica solo daba el total y los hallazgos |
| DV-IA-5 | La decisión es de dos fases (calcular, completar, registrar, aplicar) | la clásica podía registrar una decisión y fallar al aplicarla |
| DV-IA-6 | La sesión se recupera tras recargar | el borrador vive en el servidor |
| DV-IA-7 | Una pregunta de la IA se muestra pero no se responde (hasta la etapa 2) | decisión de etapas |
| DV-IA-8 | Mensajes compuestos por la capa nueva con tildes; los del motor, tal cual | misma regla que D-3 de la hoja |
| DV-IA-9 | Los motivos de las sesiones detenidas se muestran con la tabla `motivo → texto` con tildes | los del motor están congelados sin tildes |
| DV-IA-10 | Confirmación en línea al descartar pendientes | la clásica descartaba sin preguntar y las propuestas costaron dinero |

---

## 12. Texto exacto para los archivos compartidos (lo aplica el orquestador)

**Antes de integrar 4a-1**

- `tests/unit/test_arquitectura_asistente.py`: `IMPORTAN_ASISTENTE_APLICACION` pasa a
  `{"aplicacion/entrega.py", "aplicacion/hoja_asistente.py", "aplicacion/hoja_asistente_puente.py", "aplicacion/hoja_asistente_trabajo.py"}`;
  la prueba `test_aplicacion_entrega_solo_importa_el_registro_del_asistente` mantiene su comprobación de `entrega.py` y suma:
  (1) solo `hoja_asistente_puente.py` importa `asistente.servicio`, `asistente.orquestador`, `asistente.propuestas`,
  `asistente.privacidad` y `asistente.validacion`, y solo dentro de funciones; (2) `hoja_asistente.py` y `hoja_asistente_trabajo.py`
  importan únicamente de `asistente`: `catalogo`, `clave`, `instalacion`, `registro`, `tarifas` y `proveedores.base`.
- `tests/unit/test_arquitectura.py`: sin cambios en las reglas existentes; se **agrega** una prueba de subproceso hermana de
  `test_importar_la_api_no_carga_scripts_tests_ni_ui` que importa `api.main` y comprueba que `asistente.servicio` y
  `asistente.orquestador` **no** están en `sys.modules` (la importación sigue perezosa).

**Al aprobar cada sub-rebanada**

- `api/main.py`: añadir `hoja_asistente` a `from api.rutas import (...)` (alfabético, tras `hoja_exportar`... según el orden del
  archivo) y, tras `hoja_plano`:
  `# Migracion final (T10 · 4a): asistente de IA de la hoja (A0 a A6), solo con sesion`
  `app.include_router(hoja_asistente.router)`
- `tests/unit/test_api_acceso_por_ruta.py`: una fila por ruta A0 a A6 («solo sesión con `editar_hoja`»), y la comprobación de que
  `rita`, `admin` y la clave de API reciben 403.
- `CHANGELOG.md`, una línea por cambio: «Asistente de IA en la hoja de la interfaz nueva, etapa 1: `/v1/hoja/asistente/proveedores` y
  `/v1/hoja/borradores/{id}/asistente` (previa, proponer en segundo plano, estado, decidir cada propuesta, resultado hipotético,
  descartar); `aplicacion/hoja_asistente*.py` nuevos; `asistente/`, `ui/` y `core/` sin cambios.» y, al cerrar 4a-2, «El guardado
  de la hoja anota la sesión del asistente en el registro `ia_*` (`avisos` en la respuesta).»
- `docs/api.json`: regenerar con `scripts/exportar_openapi.py` en cada rebanada de backend (hoy tiene cambios ajenos sin confirmar:
  el orquestador los integra primero).
- `docs/ERS.md` (numeración **propuesta**, el orquestador la confirma): RF-156 *UC-09 en la interfaz nueva* (proponer, decidir una por
  una y ver el resultado hipotético desde la hoja); RF-157 *Gasto del asistente* (estimación previa, tope por sesión, plazo,
  cancelación, una petición por borrador, tope de concurrencia); RF-158 *Privacidad del asistente en la interfaz nueva* (la clave de
  IA nunca llega al navegador, el pedido con una clave se rechaza, vista previa del texto exacto); RF-159 *Trazabilidad del asistente*
  (origen «propuesta de IA» en lo aceptado, decisión a nombre de la cuenta, sesión anotada al guardar). Anotar que UC-09 se cubre
  también en la interfaz nueva al cerrar 4a-4.
- `frontend-desktop/src/shell/rutas.ts`: **no cambia** (el panel vive dentro de la página de la hoja).

---

## 13. Lo que no pude determinar

1. El plazo por omisión del cliente de `anthropic` (lo fija el SDK; no lo leí). Por eso se pone plazo propio.
2. Si `ProveedorOllama.disponible()` hace la comprobación de versión por HTTP en cada llamada (lo deduzco de `ollama_local.py:149`,
   `timeout=5`; no lo probé).
3. El comportamiento de `exigir_clave_o_sesion` con CSRF y `Origin` en métodos que escriben: lo tomo del diseño de la hoja (§4.1) y de
   `api/rutas/hoja.py`; no abrí `api/sesion_web.py`.
4. El tiempo real de A4 (R17 + `elaborar` por decisión) con cientos de puntos: RNF-11 midió 0,125 s sin R17 (bitácora `2026-10-sf.md`).
   Lo mide 4a-2.
5. Si 64 propuestas en pantalla (tope de 60 llamadas) son manejables con letra Muy grande: lo decide 4a-6.
6. Si el SDK de `anthropic` cobra o no un turno cuyo hilo se abandonó antes de regresar (depende del proveedor; no lo verifiqué).
7. Si `ml.normalization.proponedor` (búsqueda semántica del catálogo) puede cargarse en un hilo de trabajo sin problemas en este
   equipo (la clásica lo hace en el hilo de Streamlit); 4a-1 lo comprueba con la búsqueda por palabras como respaldo, que
   `CatalogoDeLaBase` ya trae.
8. Que `ui.hoja.Borrador` y `aplicacion.hoja.Borrador` tienen exactamente los mismos nueve campos: lo comprobé leyendo ambas
   definiciones; la prueba B1 lo fija contra una lista escrita a mano.
