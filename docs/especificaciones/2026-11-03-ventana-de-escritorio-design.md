# Ventana de escritorio propia para Sílice: diseño

**Fecha:** 2026-11-03 · **Rama:** `feature/disenos-f5` (árbol `.worktrees/s2m5`) · **Estado:** PROPUESTO (por aprobar por
Eugenio). **2026-11-06:** construido V0 a V3 en `feature/f5-ventana` con las decisiones **provisionales** de §10
(recomendaciones del orquestador, pendientes de ratificar por Eugenio); §6.1 (punto 6) y §7.3 quedan enmendados por la
decisión 3. **2026-11-07:** Eugenio ratificó la decisión 7 de §10 (perfil de WebView2 en la carpeta de datos).
**Origen:** Eugenio aprobó el 2026-10-25 que, después de la auditoría, Sílice tuviera una ventana de escritorio propia en vez
de abrirse en el navegador. Diseños y planes que esto toca: `2026-10-11-silice-s5-producto-instalador-design.md` (instalador,
arranque, prueba de humo), `docs/planes/RUTA_SESIONES.md` (rulings RT-2, RT-3 y RT-5; sesión 5),
`2026-10-25-barra-superior-design.md` (que nombra «la aplicación de escritorio (pywebview)» y deja la ventana al final del
orden aprobado ese día).

## 1. Intención

Hoy el acceso directo «Sílice» ejecuta `python -m operacion arrancar` (`instalador/silice.iss`, sección `[Icons]`): el
lanzador (`operacion/lanzador.py`) prepara las bases, levanta **un solo proceso** de Uvicorn en `127.0.0.1:8501`, espera
`GET /salud` y abre el navegador predeterminado en `/app/` con `webbrowser.open`. Para detener Sílice hay que cerrar una
ventana de consola minimizada (DA-S5-5 del diseño S5). Para quien no es experto eso son dos ventanas que no se explican
solas: una pestaña más del navegador, mezclada con las suyas, y una consola que no debe cerrar sin querer.

Lo que se quiere: **una ventana con el nombre y el ícono de Sílice**, que muestre la misma interfaz y que al cerrarse
detenga Sílice. Sin cambiar la interfaz, la API ni la seguridad que ya tienen.

## 2. Metas, no-metas y anti-metas

**Metas**
- M1: el acceso directo abre una ventana propia («Sílice», su ícono, su botón en la barra de tareas) con la interfaz de
  `/app/`.
- M2: cerrar esa ventana detiene Sílice, sin procesos huérfanos.
- M3: si el equipo no puede mostrar la ventana, Sílice se abre en el navegador como hoy y dice por qué.
- M4: nada de lo que hoy se garantiza empeora: bucle local, CSP, RNF-22 (sin red externa), RNF-19 (tamaño del
  instalador), `SHA256SUMS` firmado con Ed25519 y la prueba de humo.

**No-metas**
- Cambiar la interfaz de React, sus rutas o su CSP.
- Quitar el acceso por navegador: los otros equipos de la red local siguen entrando con su navegador (RT-2), y el
  navegador queda como camino de respaldo.
- Firma de código del instalador (RS5-10 sigue igual), actualización automática, Linux o macOS.
- Un puente entre la página y Python: la interfaz habla con la API por HTTP, como hoy.

**Anti-metas** (fracasos aunque funcione)
- Una ventana que abra conexiones fuera del equipo o que exponga herramientas de desarrollo.
- Un instalador que pase de 150 MB o que dependa de internet para la ventana.
- Un lenguaje o una cadena de construcción nuevos solo para envolver una URL.
- Una instalación en la que Sílice no abra en absoluto porque falta un componente de Windows.

## 3. Lo que ya se decidió y lo que este diseño cambia

- **RT-3 (ruta, 2026-10-18):** «Tauri v2 como envoltorio» de la misma interfaz en la sesión 5, con dos condiciones
  abiertas: el instalador pesaba 129,80 MB de 150 MB y WebView2 **no está garantizado** en Windows 10 22H2, y su
  instalador sin conexión no cabe en el margen; la tarea 5.0b debía decidirlo o enmendar RNF-19. Además, el trabajo de
  Windows de la CI necesitaría Rust y Eugenio tendría que instalarlo (bloqueo B-5).
- **RT-5:** puerto efímero y una clave por sesión entregada por el IPC de Tauri.
- **RT-9 (posterior a RT-5):** la interfaz entra con la cuenta de la persona y una cookie `HttpOnly` + `SameSite=Strict`
  con ficha anti-CSRF; la clave de API queda para integraciones. Con eso, la clave por IPC de RT-5 ya no hace falta
  para la interfaz.
- **2026-10-25:** el diseño aprobado de la barra superior nombra la aplicación de escritorio como **pywebview**.

Este diseño **recomienda pywebview y propone enmendar RT-3 y RT-5** (§6). El motivo no es una preferencia: el problema de
WebView2 es el mismo con Tauri y con pywebview (los dos usan WebView2 en Windows), y lo que Tauri añade (IPC, un
ejecutable propio) ya no lo necesita Sílice desde RT-9, mientras su costo (Rust, cientos de dependencias de Cargo, un
segundo proceso que vigilar) sigue entero.

## 4. Hechos que condicionan el diseño (leídos el 2026-11-03)

- `operacion/lanzador.py`: `arrancar(…, sin_navegador=False, abrir=webbrowser.open, …)` ya recibe la función que
  presenta la interfaz como parámetro (así lo prueban hoy); el proceso principal espera en un bucle a que Uvicorn
  termine y, al salir, `_terminar` los procesos y borra `estado\servidor.json`. Una segunda ejecución con Sílice en
  marcha solo abre el navegador.
- `api/interfaz.py`: la CSP de `/app` es `default-src 'self'`, `script-src 'self'`, `connect-src 'self'`,
  `frame-ancestors 'none'`, `form-action 'self'`, entre otras. `api/sesion_web.py`: la cookie se pone con
  `httponly=True, samesite="strict", secure=False` (bucle local en HTTP) y todo método que escribe exige `Origin` igual a
  `http://<Host>`.
- `frontend-desktop/src/comun/DescargaArchivo.tsx`: las descargas (Excel, PDF, paquetes) se hacen con un enlace
  `download` sobre un `blob:`. Las subidas, con `<input type="file">`.
- `instalador/tamanos.py`: tope del básico 150.000.000 bytes (RNF-19). La última cifra anotada es 129,80 MB (entrega de
  la 1.0.0, `docs/bitacora/2026-10-15-entrega-release-1.0.0-auditoria.md`); desde entonces se retiró Streamlit y entró
  el `dist` de React, así que **hay que volver a medir** antes de decidir nada por tamaño.
- RNF-23: el `dist` ≤ 15.000.000 bytes sin comprimir. RNF-22: sin anfitriones externos (`scripts/verificar_dist.mjs`),
  nada en `localStorage`.
- `instalador/humo.ps1` arranca con `arrancar --sin-navegador`, espera la salud, comprueba puertos y corre
  `instalador/navegador.py` (Playwright con Edge sin interfaz) para anotar toda petición fuera de `127.0.0.1`. La CI de
  Windows corre en `windows-2025` (`.github/workflows/instalador.yml`).
- El instalador es per-usuario (`PrivilegesRequired=lowest`), exige Windows 10 22H2 (`MinVersion=10.0.19045`) y sus
  accesos directos usan `python.exe`, así que hoy el ícono de Sílice es el de Python.
- `cffi` ya está en `uv.lock` (lo trae `argon2-cffi`).

## 5. Opciones comparadas

### 5.1 Las tres opciones

- **A. pywebview.** Biblioteca de Python (licencia BSD) que abre una ventana nativa con WebView2 en Windows, a través de
  `pythonnet` y WinForms. El lanzador, después de la salud, abre la ventana sobre `http://127.0.0.1:8501/app/`; al
  cerrarse, termina Uvicorn como hoy.
- **B. Tauri v2.** Un ejecutable de Rust con WebView2 que lanza el Python instalado como proceso hijo y muestra la
  interfaz (la de `/app/` por URL externa, o el `dist` empaquetado dentro del ejecutable).
- **C. Navegador en modo aplicación.** El acceso directo abre Edge con `--app=http://127.0.0.1:8501/app/` (una ventana sin
  barra de direcciones), con un perfil propio en la carpeta del usuario. Sin dependencias nuevas.

### 5.2 Criterios

| Criterio | A. pywebview | B. Tauri v2 | C. Edge en modo aplicación |
|---|---|---|---|
| **Seguridad: bucle local** | Igual que hoy: la ventana carga `127.0.0.1` | Igual si carga la URL; si empaqueta el `dist`, el origen pasa a ser el de Tauri y la API tendría que aceptar otro `Origin` (CORS), lo que debilita la comprobación de `api/sesion_web.py` | Igual que hoy |
| **Seguridad: CSP** | La de `api/interfaz.py`, sin cambios (misma página, mismo origen) | Con URL externa, la misma; con `dist` empaquetado, una CSP más en `tauri.conf.json` que mantener alineada | La misma |
| **Superficie nueva** | Sin puente: no se expone ninguna función de Python a la página (`js_api` vacío); herramientas de desarrollo apagadas | IPC y permisos de Tauri (capacidades), bien diseñados pero que hay que configurar y auditar; un proceso de Rust que vigila a Python | El perfil de Edge: extensiones si se usara el perfil de la persona (por eso perfil propio), avisos de inicio de sesión y sincronización de Edge |
| **RNF-22 (sin red)** | Lo que pide la página es lo de hoy y lo mide la humo por CDP (§7.5). WebView2 es un componente de Microsoft con su propio servicio de actualización: fuera del control de Sílice, igual que el navegador hoy | Igual que A | Igual, más lo que Edge hace por su cuenta con un perfil nuevo (primer arranque, sincronización), que hay que apagar con banderas |
| **RNF-19 (instalador ≤ 150 MB)** | Suma unos pocos paquetes de Python (pywebview, pythonnet, clr_loader, bottle, proxy_tools; `cffi` ya está). Cifra **a medir** con `instalador/medir_capas.py` en la tarea V0; se espera del orden de unos pocos MB | El ejecutable de Tauri (unos pocos MB, a medir) y, si se empaqueta, una segunda copia del `dist` | Cero |
| **Tope del `dist` (RNF-23)** | Sin cambio | Sin cambio con URL externa | Sin cambio |
| **WebView2 en Windows 10 22H2** | Hace falta. Si no está, se detecta y se abre el navegador (§6.3): Sílice abre siempre | Hace falta, el mismo problema de RT-3. Sin él, el ejecutable no muestra nada salvo que se programe un respaldo | No hace falta WebView2; Edge viene con Windows 10 22H2 y 11 |
| **Mantenimiento** | Solo Python; el lanzador ya existe y se extiende. pywebview es un proyecto pequeño: si se rompe, queda el navegador | Un segundo lenguaje (Rust), `rustup` en el equipo de Eugenio (B-5) y en la CI, `Cargo.lock` con cientos de crates y su auditoría; el vigilante de procesos se reescribe en Rust | Mínimo, pero el ciclo de vida no es fiable: si Edge ya está abierto con ese perfil, el proceso lanzado puede terminar enseguida y el lanzador no sabe cuándo se cerró la ventana (a verificar) |
| **Dependencias nuevas** | 4 o 5 paquetes de Python, permisivos, a confirmar con `instalador/licencias.py` y `pip-audit` (`instalador/auditar.py`) | Toda la cadena de Rust y Tauri | Ninguna |
| **Firma y huella** | Todo va dentro del instalador, que ya cubre `SHA256SUMS` firmado con Ed25519; no aparece un ejecutable nuevo | Un ejecutable nuevo sin firma de código dentro del instalador: lo cubre `SHA256SUMS`, pero SmartScreen y los antivirus lo ven como desconocido | Nada nuevo |
| **Prueba de humo** | Se extiende: la ventana se abre en la CI y Playwright se conecta a su WebView2 por CDP solo en la prueba (§7.5) | Igual, más compilar Rust en el trabajo de Windows | Fácil de abrir; difícil de comprobar que cerrar detiene Sílice |
| **Quien no es experto** | Una sola ventana, «Sílice», con su ícono; se cierra como cualquier programa | Igual que A | Parece Sílice, pero es Edge: su ícono agrupado con Edge según cómo se configure, menús y atajos de Edge, y cerrar la ventana no detiene el servidor |

### 5.3 Lectura

C es lo más barato y no resuelve lo que pidió Eugenio: sigue siendo el navegador, y no se puede prometer que cerrar la
ventana detenga Sílice. B resuelve lo mismo que A con un costo mucho mayor y sin quitar el problema de WebView2, que era
la condición abierta de RT-3. A es la única que cumple M1 a M4 con dependencias de Python y con un respaldo que garantiza
que Sílice abre en cualquier equipo.

## 6. Recomendación: pywebview con el navegador como respaldo

### 6.1 Cómo funciona

1. El acceso directo sigue ejecutando `python -m operacion arrancar`. El lanzador prepara las bases, emite el código de
   instalación si hace falta, levanta Uvicorn y espera la salud, **como hoy**.
2. Después decide cómo presentar la interfaz: si el ajuste `interfaz` de `silice.toml` es `ventana` (por defecto) y el
   equipo tiene WebView2, abre la ventana (enmienda 2026-11-06: el ajuste vive en la tabla `[interfaz]` que ya existía,
   con la clave `abrir_en = "ventana" | "navegador"`); si no, abre el navegador como hoy y deja un AVISO en la consola y en el registro
   que dice por qué.
3. La ventana: título «Sílice», ícono propio, abierta maximizada, tamaño mínimo de 1056 px de ancho (el más chico que la
   interfaz soporta), sin `js_api`, sin herramientas de desarrollo, con las descargas permitidas (las necesita
   `DescargaArchivo`) y los enlaces a otro anfitrión abiertos fuera (no debería haber ninguno: RNF-22).
4. pywebview exige el hilo principal: la vigilancia de Uvicorn, que hoy es el bucle principal, pasa a un hilo. Si Uvicorn
   muere, la ventana muestra un mensaje fijo («Sílice se detuvo; ciérrela y vuelva a abrir Sílice») y no queda colgada.
5. Al cerrar la ventana, `webview.start()` regresa y el `finally` de hoy termina los procesos y borra el estado.
6. ~~Una segunda ejecución con Sílice en marcha abre una ventana más sobre el mismo servidor; esa ventana no es dueña del
   servidor y cerrarla no lo detiene (o abre el navegador si no hay WebView2).~~ **Enmienda 2026-11-06 (decisión 3,
   provisional):** una segunda ejecución con Sílice en marcha **trae al frente la ventana que ya está** (la del lanzador
   vivo, primer PID de `servidor.json`, buscada por su título «Sílice») y sale sin lanzar nada; si la instancia viva no
   tiene ventana (abrió el navegador), abre el navegador como hoy. La «ventana no dueña» no existe.
7. `--sin-ventana` fuerza el navegador; `--sin-navegador` (el de la humo) sigue sin presentar nada.

**Puerto:** se queda fijo (8501, `operacion/config.py`). El puerto efímero de RT-5 rompería «abra
`http://127.0.0.1:8501/app/` a mano» del manual y no añade protección que no den ya el bucle local, la cookie de sesión y
la comprobación de `Origin`.

### 6.2 Dónde vive

| Pieza | Qué cambia |
|---|---|
| `pyproject.toml` | extra nuevo `escritorio = ["pywebview==<versión fijada>"]` (solo Windows) |
| `instalador/manifiesto.toml` | `escritorio` en la capa básica |
| `operacion/ventana.py` (nuevo) | detectar WebView2, abrir la ventana con sus ajustes, mensaje si Uvicorn muere. Lo único que importa pywebview |
| `operacion/lanzador.py` | `abrir` pasa a ser «presentar»: ventana o navegador; el bucle de vigilancia a un hilo; `--sin-ventana` |
| `operacion/config.py` | ajuste `interfaz = "ventana" \| "navegador"` en `silice.toml`, con aviso si trae otro valor |
| `instalador/silice.iss` | ícono propio (`silice.ico`) en accesos, desinstalación y ventana; mismo identificador de aplicación en el acceso y en la ventana para que la barra de tareas los agrupe como «Sílice» y no como Python |
| `instalador/humo.ps1`, `instalador/navegador.py` | el paso de la ventana (§7.5) |
| Textos | la bienvenida habla de «la ventana del servidor» (`frontend-desktop/src/bienvenida/Bienvenida.tsx`): se revisa; `docs/manual_instalacion.md` y `docs/manual_usuario.md` |

`core/`, `api/`, `aplicacion/` y `frontend-desktop/` (salvo ese texto) no cambian. **No toca el núcleo.**

### 6.3 Detección de WebView2 y respaldo

La guía de distribución de WebView2 de Microsoft indica comprobar la versión instalada del runtime en el registro (clave
de `EdgeUpdate\Clients` del runtime, en el equipo o en el usuario); la clave exacta se verifica en la tarea V0 contra la
documentación vigente. Si no está, o si pywebview no logra abrir la ventana (por ejemplo, porque `pythonnet` no carga), el
lanzador **abre el navegador** y lo dice. No se empaqueta el instalador de WebView2: no cabe en el margen de RNF-19 y
el respaldo hace innecesario enmendarlo.

### 6.4 Enmiendas que este diseño propone (al aprobarse)

- `docs/planes/RUTA_SESIONES.md`: RT-3 pasa de Tauri v2 a pywebview con respaldo al navegador; RT-5 deja el puerto fijo y
  retira la clave por IPC (la cubre RT-9); la sesión 5 se renombra y pierde el bloqueo B-5 (Rust).
- ERS: los números reservados para la sesión 5 (RF-137 a RF-140, RNF-26 y RNF-27) se usan para la ventana, por ejemplo:
  ventana propia que al cerrarse detiene Sílice; respaldo al navegador con su aviso; ninguna conexión fuera del bucle
  local, sin puente con Python ni herramientas de desarrollo; tope de lo que la capa de escritorio suma al instalador,
  fijado con la medición de V0. La redacción final se escribe con el plan.
- Diseño S5: DA-S5-5 (la consola minimizada como servidor) se mantiene en esta versión; ver la pregunta 2 de §9.

## 7. Plan de alto nivel

### 7.1 Tareas

| # | Tarea | Salida | Compuerta |
|---|---|---|---|
| V0 | Verificar sin código de producto: versión de pywebview y de `pythonnet` que funcionen con el Python del instalador (3.13.13, `instalador/manifiesto.toml`); medir la capa; licencias y `pip-audit`; probar en un Windows 10 22H2 limpio y en uno 11 que la ventana abre, entra con la cookie, sube un archivo y descarga un `blob:`; clave de registro de WebView2 | Bitácora con cifras y versiones fijadas | Si `pythonnet` no sirve con 3.13, se para y se decide (§8) |
| V1 | Extra `escritorio`, `uv.lock`, manifiesto y licencias | Instalador construye con la capa | Tamaño ≤ 150 MB en la CI |
| V2 | `operacion/ventana.py` y el lanzador (TDD con dobles, como ya se prueba `abrir`) | Pruebas en verde | Árbitro de seguridad |
| V3 | Ícono, identificador de aplicación y accesos en Inno Setup; textos de la bienvenida y de los manuales | Instalador nuevo | Árbitro de diseño |
| V4 | Paso de la ventana en la humo de la CI | Trabajo `instalador` en verde | — |
| V5 | Prueba de Eugenio en su equipo y, si se puede, en el de la empresa | Nota en la bitácora | Visto bueno de Eugenio |

### 7.2 Riesgos

| Riesgo | Efecto | Qué se hace |
|---|---|---|
| `pythonnet` sin soporte para el Python del instalador | La ventana no abre | V0 lo comprueba primero; el respaldo abre el navegador; si no hay versión compatible, se espera o se evalúa el otro motor de pywebview, sin cambiar el Python del instalador por esto |
| WebView2 ausente en Windows 10 22H2 | Sin ventana en ese equipo | Respaldo al navegador con aviso; el manual explica cómo instalar WebView2 si se quiere la ventana |
| Descargas o subidas que no funcionen en la ventana | Pantallas que exportan o suben quedan cojas | V0 y la humo prueban una descarga `blob:` y una subida; las descargas se encienden explícitamente |
| Antivirus que vigila `python.exe` abriendo componentes de .NET | Bloqueo o aviso | Respaldo al navegador; anotarlo en el manual |
| Proyecto pequeño, un solo mantenedor | Correcciones lentas | Versión fijada; el respaldo deja a Sílice usable aunque pywebview falle |
| El puerto de depuración de WebView2 que usa la humo se colara al producto | Cualquier proceso local podría manejar la ventana | Solo lo pone la humo por variable de entorno; una prueba comprueba que `entorno_hijos` y la ventana nunca lo ponen |

### 7.3 Pruebas unitarias (V2)

- Con WebView2 y `interfaz = "ventana"`: se llama a la ventana con la URL de `/app/`, sin `js_api` ni depuración; no se
  llama al navegador.
- Sin WebView2, con `interfaz = "navegador"` o con `--sin-ventana`: se abre el navegador y, en los dos primeros casos, sale
  el AVISO con el motivo.
- La ventana falla al abrir: navegador y AVISO; Sílice sigue en marcha.
- Cerrar la ventana termina Uvicorn y borra `servidor.json`; Uvicorn muere con la ventana abierta: mensaje y salida limpia.
- ~~Segunda ejecución: ventana no dueña; cerrarla no termina el servidor.~~ Enmienda 2026-11-06: segunda ejecución con
  la instancia viva: trae al frente su ventana y no lanza ni abre nada más; sin ventana viva, el navegador; con
  `--sin-navegador`, nada.
- El entorno de los hijos y de la ventana no contiene la variable del puerto de depuración.

### 7.4 Prueba manual (V5)

Instalar en una cuenta estándar sin internet; abrir «Sílice»; crear el primer administrador en la bienvenida; subir una
carpeta de trabajo y descargar un Excel; cerrar la ventana y comprobar en el Administrador de tareas que no quedó
`python.exe`; repetir con WebView2 ausente (o con `interfaz = "navegador"`) y comprobar el aviso.

### 7.5 Prueba de humo en la CI (V4)

En `windows-2025`, después del paso de hoy: arrancar sin `--sin-navegador`, con la variable de WebView2 que abre un puerto de
depuración **solo en este paso**; conectar Playwright por CDP (lo documenta Playwright para WebView2) desde
`instalador/navegador.py`; cargar `/app/`, anotar toda petición (la lista fuera de `127.0.0.1` debe quedar vacía, como
hoy), hacer una descarga; cerrar la ventana y afirmar que Uvicorn terminó y que `servidor.json` ya no existe. Si la imagen
del runner no trae WebView2, el trabajo lo instala antes del paso (la CI tiene internet; el producto no lo necesita).

## 8. Si V0 sale mal

- **`pythonnet` no carga con 3.13:** no se sube ni se baja el Python del instalador por la ventana. Se publica sin ventana
  (respaldo al navegador, que es lo de hoy) y se reabre cuando haya versión compatible. Tauri no se reconsidera por esto
  solo: su problema de WebView2 es el mismo.
- **La capa pasa del margen de RNF-19:** se mide qué pesa y se decide con Eugenio; no se enmienda RNF-19 sin su visto bueno.

## 9. Preguntas para Eugenio

1. ¿Aprueba pywebview con el navegador como respaldo, y enmendar RT-3 y RT-5 de la ruta (Tauri y la clave por IPC)?
2. La consola minimizada: ¿se queda (lo propuesto para esta versión: muestra el código de instalación y cerrarla también
   detiene Sílice) o se oculta, dejando la ventana como única forma de detener Sílice?
3. Una segunda ejecución con Sílice abierto: ¿abre otra ventana (lo propuesto) o solo trae al frente la que ya está?
4. ¿El ajuste `interfaz` debe poder cambiarse desde Administración, o basta con `silice.toml`?
5. ¿Quiere un ícono de Sílice dibujado para esto? Hoy no hay ninguno: los accesos usan el de Python y la interfaz no
   tiene favicon (`frontend-desktop/index.html` lo deja vacío).
6. ¿Puede probar V0 en un equipo de la empresa con Windows 10, para saber si allí WebView2 está?

## 10. Decisiones provisionales (2026-11-06)

Recomendaciones del orquestador a las preguntas de §9, con las que se construyó V0 a V3 en `feature/f5-ventana`.
**Pendientes de ratificar por Eugenio**; cada una es reversible sin tocar el núcleo.

| # | Pregunta de §9 | Decisión provisional | Dónde quedó |
|---|---|---|---|
| 1 | pywebview y enmendar RT-3 y RT-5 | pywebview con el navegador como respaldo; RT-3 y RT-5 enmendados con fecha | `docs/planes/RUTA_SESIONES.md` §2, `docs/ERS.md` (enmienda 2026-11-06) |
| 2 | La consola minimizada | Se queda en esta versión: muestra el código de instalación y cerrarla también detiene Sílice | `operacion/lanzador.py` (mensajes de la consola), RF-181 |
| 3 | Segunda ejecución | Trae al frente la ventana que ya está (estándar de las aplicaciones de escritorio), no abre otra | §6.1 punto 6 y §7.3 enmendados; `operacion/ventana.py` (`traer_al_frente`), RF-183 |
| 4 | Dónde se cambia `interfaz` | Solo en `silice.toml` (`[interfaz] abrir_en`), no en Administración por ahora | `operacion/config.py`, RF-182 |
| 5 | Ícono de Sílice | Sí: SVG propio, sobrio, con los colores del marco de Carbon; favicon de la interfaz, ícono de la ventana, de los accesos y del instalador | `frontend-desktop/public/silice.svg`, `operacion/silice.ico` (lo genera `instalador/icono.py`), `instalador/silice.iss` |
| 6 | V0 en un equipo de la empresa con Windows 10 | Queda para Eugenio (V5): este equipo es Windows 11 | `docs/bitacora/2026-11-06-ventana-v0.md` §1.5 |
| 7 | Perfil de WebView2 (lo levantó el árbitro único del 2026-11-07, V1: el modo privado borraba `localStorage` y el tamaño de letra y el zoom de la Hoja volvían a «Normal» en cada arranque) | **Ratificada por Eugenio el 2026-11-07, «Guardar perfil en datos»:** `private_mode=False` con `storage_path` en `<datos>\perfil_ventana` (en el producto, `%LOCALAPPDATA%\Silice\datos\perfil_ventana`). La cookie `silice_sesion` sigue sin `Max-Age` ni `Expires`: WebView2 no la escribe en el perfil y la sesión termina al cerrar la ventana (RNF-22). En el perfil quedan `localStorage` (solo esas dos preferencias: el resto de la interfaz no usa almacenamiento, RT-9) y la caché del navegador, en la misma carpeta y con los mismos permisos que las bases. Desinstalar no lo borra, como el resto de los datos | `operacion/config.py` (`carpeta_perfil_ventana`), `operacion/ventana.py`, `operacion/lanzador.py`, RF-180 y RF-184; `tests/unit/test_ventana.py`, `test_lanzador.py`, `test_operacion_config.py` |

Las decisiones 1 a 6 siguen **provisionales**; la 7 está ratificada. Además, el 2026-11-07 (MENOR del árbitro) `js_api`
pasó de `None` a `ventana.PuenteCerrado`, un objeto sin atributos: pywebview busca lo que pide la página con `getattr`
encadenado sobre `js_api`, y con `None` la cadena seguía por los atributos de `None` («__class__» llegaba a llamarse).
El riesgo que queda (los mensajes internos de pywebview) está escrito en RF-184.

Resultado de V0 (bitácora): pywebview 6.2.1 y pythonnet 3.2.1 funcionan con el Python 3.13.13 del instalador; la capa
suma unos 0,6 MB con LZMA; WebView2 está en este equipo. §8 no hizo falta.
