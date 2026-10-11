# Sílice S3 (versión 0.8.0): cuentas, registro encadenado, firma, paquete auditado y auditoría de planos

| Campo | Valor |
|---|---|
| Estado | **propuesta**, pendiente de la aprobación de Eugenio y de la revisión por encargo (requisitos, arquitectura, pruebas y calidad, verificador de hechos, usabilidad y **seguridad**, spec maestro §6). Los expedientes SL‑E7 a SL‑E9 necesitan además el visto bueno del tutor |
| Fecha | 2026‑10‑11 |
| Rama del spec | `inc/silice` (worktree `.worktrees/silice`) |
| Ramas de construcción | `inc/silice-s3-nucleo` (solo `core/`, se fusiona primero) e `inc/silice-s3` (lo demás), según la guardia M9 |
| Versión que entrega | **0.8.0** (spec maestro §5); depende de 0.5.0 y puede ir en paralelo a 0.7.0 |
| Se apoya en | [spec maestro](2026-10-11-silice-1.0.0-design.md) (S‑D3, S‑D4, S‑D5, §4); [horizonte, revisión 2](2026-10-08-horizonte-reorientacion-design.md) (§2.4, §5.1, H‑D7 a H‑D10); [spec SF](2026-10-04-sprint-final-prototipo-design.md) (formato, SF‑E2, SF‑E6, §6.6) |
| Naturaleza de los datos | igual que [NORMAS.md §1](../../NORMAS.md): casos construidos; las empresas, personas y claves de las pruebas son ficticias |

Este documento es la **fuente única** del diseño de S3. No repite el horizonte ni el maestro: los enlaza.

---

## 1. Qué se quiere y por qué

### 1.1 El pedido

El horizonte une a **quien arma** y **quien revisa** con un **paquete auditado** (§2.4, H‑D7, H‑D10); el maestro fija
cómo: cuentas locales con tres roles (S‑D4), firma por empresa Ed25519 (S‑D5), sin internet (S‑D3). S3 suma el APU de
otras herramientas y la auditoría de planos (horizonte §5.1, fase R3).

### 1.2 Lo que se encontró en el código (2026‑10‑11, rama `inc/silice`)

- **El responsable es un texto que escribe el usuario.** `_exigir_respaldo` (`core/budget/edicion.py:76`) solo
  exige que no venga vacío; `RegistroCambio.responsable` es `String(120)` (`core/models/entidades.py:552`). La hoja
  lo pide en un campo (`ui/paginas/hoja.py:505`) y dos caminos ponen `"sistema"` por defecto (`ui/hoja.py:1594`,
  `core/budget/instantanea.py:450`).
- **UC‑02 no registra responsable.** `CambioPrecio` (`core/models/entidades.py:227`) no tiene esa columna.
- **No hay cuentas, control de acceso, huellas de versión ni firmas.** `ui/caso.py` fija el caso por sesión de
  Streamlit; `api/main.py` no exige clave en ninguna ruta; las únicas huellas SHA‑256 son las de RNF‑04 (pruebas).
- **UC‑05 no sirve tal cual para un paquete.** `importar_presupuesto` rechaza un archivo cuyas partidas ya estén en el
  catálogo (`core/budget/importacion.py:208`); un paquete de una contratista que usa los mismos códigos MaPreX
  chocaría. `leer_presupuesto_tabular` sí reconstruye en memoria sin tocar la base (`importacion.py:132`).
- **La auditoría de archivo de `ezdxf` no se invoca.** El horizonte §5.1 la da como «ya en el sistema», pero
  `adapters/espacio/planos/dxf.py:171` abre el plano con `ezdxf.readfile` y ninguna línea de `adapters/` llama a una
  auditoría. **Se corrige aquí** (RF‑89) y se enmienda el horizonte.
- **`shapely` ya está instalado** como dependencia de `ifcopenshell` 0.8.5 (`uv.lock`), versión 2.1.2; S3 la
  declara como dependencia directa. `ifctester` no aparece en `uv.lock`.
- **Subidas:** las nuevas de S3 (paquete, clave pública, plano de contraste) pasan por `ui/subidas.py` y
  `api/archivos.py`, las funciones únicas de guardado seguro (A‑1).

### 1.3 Criterio de éxito de la versión

Una contratista arma un presupuesto, lo entrega como **paquete firmado**; un administrador de otra instalación lo
recibe, ve **«Verificado: emitido por Contratista Demo, C.A.»**, lo **reaudita sin confiar en el informe ajeno**, ve
en qué difiere de la entrega anterior y **cuánto dinero representa**. Un byte cambiado en el paquete se detecta. Un
APU de otra herramienta se audita por Excel y por la API. En los planos de OF‑001 con errores sembrados se mide la
**tasa de detección** y las **falsas alarmas**.

---

## 2. Alcance

**Incluye:** cuentas, roles y sesión (§5); registro encadenado (§6); claves y firma por empresa (§7); paquete
auditado (§8); vista de revisión y diferencias con su costo (§9); APU de otras herramientas (§10); auditoría de planos
y errores sembrados (§11); amenazas (§12).

**No incluye:** TLS en la red local y activar la API (S5); servidor en internet (2.x); sellado de tiempo por un tercero
(RFC 3161, exige internet); cifrar el contenido del paquete (se firma, no se oculta); inicio de sesión con un proveedor
externo (`st.login` usa OpenID Connect, contrario a S‑D3); recuperar una clave cuya contraseña se perdió; anomalías en
variaciones de precio (las primeras en caer, horizonte §6).

---

## 3. Requisitos (enmienda a la ERS, IEEE 830)

**Numeración asignada:** UC‑21 a UC‑23; RF‑80 a RF‑89; RNF‑16 y RNF‑17; expedientes SL‑E7 a SL‑E9; reglas R15 y
R16, según la numeración del spec maestro (§3). **Se usan todos; no queda ninguno vacante**, y no se usa ningún otro.
Los dos casos con personas se llaman aquí **CP‑R1** y **CP‑R2**: su número definitivo lo asigna el líder en el guion
(S4 propone CP‑12 para el suyo).

**Actores.** La ERS §2.3 se enmienda: *proyectista / estimador* = **quien arma**; *gerente* y *auditor* se agrupan
como **quien revisa** (administrador, cliente o ente contratante, horizonte §2.4); actor nuevo **administrador de la
instalación** (cuentas y claves); actor nuevo **herramienta externa** (un plugin que llama a la API con su clave).

### 3.1 Casos de uso

| UC | Nombre | Actor | Precondición | Flujos alternos conocidos |
|---|---|---|---|---|
| UC‑21 | Iniciar sesión y administrar cuentas y claves | todos; administrador de la instalación | instalación con al menos un administrador (o código de instalación vigente, 21a) | 21a primera vez: no hay usuarios, se crea el primer administrador con el código de instalación; 21b contraseña errónea: mensaje genérico, cuenta el intento; 21c cuenta bloqueada por intentos; 21d sesión expirada: vuelve al acceso **conservando el borrador** para el mismo usuario; 21e contraseña temporal: obliga a cambiarla; 21f el administrador desactiva, desbloquea o restablece una cuenta; 21g el administrador genera, retira o revoca la clave de la empresa; 21h registra o revoca la clave pública de otra empresa, con su huella comprobada |
| UC‑22 | Entregar el paquete auditado | quien arma | versión guardada; clave de la empresa activa (si no, 22a) | 22a sin clave de empresa: se ofrece exportar **sin firma**, declarado en el paquete; 22b contraseña de la clave errónea: mensaje, no se escribe nada; 22c la cadena del proyecto está rota: se rechaza la entrega y se dice en qué versión; 22d la versión tiene hallazgos ERROR: se avisa y se entrega igual (el informe viaja) |
| UC‑23 | Revisar un paquete o un presupuesto externo | quien revisa; herramienta externa (23e) | sesión con rol *revisa* | 23a sin firma o empresa no registrada: **no verificado**, se audita igual; 23b alterado (huella o firma no cuadran): banner rojo, se audita igual para mostrar qué cambió; 23c el paquete es anterior a uno ya recibido o reescribe su historia (§6.4); 23d presupuesto externo en Excel (formato UC‑05): solo se reaudita, «no contrastable» lo que no se puede verificar; 23e la herramienta externa manda el presupuesto por la API y recibe el informe; 23f formato o versión del paquete desconocidos: se rechaza con mensaje |

UC existentes que se enmiendan: **UC‑05** (el auditor puede auditar en memoria, sin persistir, desde la vista de
revisión; la importación persistente sigue igual); **UC‑14** (la importación del plano corre la auditoría de archivo
DXF, el IDS del IFC y las reglas R15 y R16); **UC‑15** (el responsable es el usuario de la sesión, no una caja de
texto); **UC‑12** (los recorridos se filtran por rol).

### 3.2 Requisitos funcionales

Prioridad: E = esencial, D = deseable. Fases de §14.

| RF | Requisito | UC | Pri. | Fase | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑80 | Cuentas locales con roles *arma*, *revisa* y *administrador de la instalación* (uno o varios por cuenta); contraseñas con Argon2; el primer administrador se crea solo con el **código de instalación** de un solo uso | UC‑21 | E | S3‑1 | sin código o con código usado se rechaza; ninguna contraseña aparece en la base, en el registro de accesos ni en los mensajes; cada página rechaza un rol que no le corresponde aunque se llegue por URL |
| RF‑81 | Sesión propia en Streamlit: expira por inactividad (30 min) y por antigüedad (12 h); bloqueo de la cuenta tras 5 intentos fallidos seguidos durante 15 min; cierre de sesión; varios usuarios a la vez sin mezclar estado | UC‑21 | E | S3‑1 | reloj inyectado: 29:59 sigue, 30:00 expira; 4 fallos no bloquean, el 5.º sí; dos sesiones AppTest con usuarios distintos no comparten borrador ni caso; prueba de concurrencia de §13.4 |
| RF‑82 | El responsable de todo `RegistroCambio` y de todo eslabón es el **usuario autenticado**, congelado como `Nombre <login>` en el momento del cambio; la caja «Responsable» desaparece de la hoja | UC‑15, UC‑21 | E | S3‑1 | guardar, restaurar, cotizar, crear la primera versión y asegurar la instantánea registran al usuario de la sesión; ningún camino de `ui/` pasa `"sistema"`; desactivar una cuenta no cambia sus registros |
| RF‑83 | Registro encadenado: cada versión nueva se sella con un eslabón SHA‑256 que encadena su contenido, sus `RegistroCambio` y el eslabón anterior (§6); las versiones anteriores se sellan una vez de forma **retroactiva** y declarada; el sistema verifica la cadena | UC‑15, UC‑22 | E | S3‑2 | cambiar un byte de una partida, de un registro o de un eslabón en la base rompe la cadena **en esa versión** y lo dice; una versión posterior al génesis sin eslabón es un error de cadena; guardar y recargar no cambia ninguna huella |
| RF‑84 | Clave de la empresa Ed25519 generada en el equipo, con la privada **cifrada con su propia contraseña**; huella corta legible (§7.2); registro de claves públicas de otras empresas con la comprobación de su huella; retiro y revocación | UC‑21 | E | S3‑3 | la privada nunca aparece sin cifrar en disco ni en el paquete; contraseña de clave errónea se rechaza sin traza; la huella es la misma en las dos instalaciones; una clave revocada deja de verificar |
| RF‑85 | Exportar el paquete auditado (§8): presupuesto canónico, informe, registro con su cadena, Excel de la hoja, anexos, manifiesto y firma | UC‑22 | E | S3‑3 | el paquete exportado se verifica como «Verificado» en otra base con la clave registrada; sin clave se exporta «sin firma» y así se declara; la cadena rota impide exportar |
| RF‑86 | Importar y verificar un paquete: integridad (huellas del manifiesto), autenticidad (firma de una empresa registrada y no revocada), cadena y posición respecto de paquetes ya recibidos; **siempre** se reaudita con las reglas propias | UC‑23 | E | S3‑4 | cada caso de §13.3 da su estado declarado; un paquete no verificado se audita igual; ninguna entrada del ZIP sale de su carpeta ni excede los límites |
| RF‑87 | Vista de revisión: estado de verificación, reauditoría, **diferencias y su costo** frente a la entrega anterior (desvío por cantidad y por precio) y frente a la base de precios del revisor, y dictamen registrado | UC‑23 | E | S3‑4 | con el par de presupuestos de la memoria de diferencias (§13.1) la vista da los montos de la memoria; el dictamen queda con usuario, fecha y estado de verificación |
| RF‑88 | APU de otras herramientas: Excel con el formato UC‑05 (plantilla descargable) auditado en memoria desde la vista de revisión, y ruta `POST /v1/auditorias` con **clave de API** que recibe el documento canónico (§8.2) y devuelve el informe | UC‑23, UC‑05 | E | S3‑4 | Excel con partidas del catálogo se audita sin el rechazo de `importacion.py:208`; sin clave o con clave revocada, 401 sin auditar; con clave, el informe coincide con el de la vista |
| RF‑89 | Auditoría de planos: auditoría de archivo DXF, requisitos IDS del IFC con `ifctester`, R15 (coherencia geométrica, `shapely`), R16 (contraste entre dos fuentes, con el costo de la diferencia), evaluación por **errores sembrados**; IfcClash opcional (D) | UC‑14 | E | S3‑5 | cada error del catálogo sembrado se detecta con la regla o el ítem de informe declarados; OF‑001 limpio da el conjunto exacto esperado; la tasa de detección y las falsas alarmas se publican con el protocolo de §11.5 |

### 3.3 Requisitos no funcionales (ISO/IEC 25010)

| RNF | Característica | Requisito | Medición |
|---|---|---|---|
| RNF‑16 | Seguridad (confidencialidad, integridad, no repudio, responsabilidad, autenticidad) | Contraseñas solo como Argon2 (parámetros por defecto de `argon2-cffi`); privada solo cifrada; ningún secreto en registros, mensajes, paquete ni Excel; el 100 % de las alteraciones de §13.3 detectadas; ninguna página ni ruta nueva accesible sin sesión o clave; límites del ZIP (§8.4); mensajes sin traza | pruebas de §13.3 y §13.4; revisión por el encargo de seguridad con la tabla de amenazas (§12) |
| RNF‑17 | Usabilidad (reconocimiento, prevención de errores, ISO 9241‑110) | En las condiciones de CP‑07, con personas que no son el autor: (a) quien revisa abre un paquete y dice su estado de verificación y quién lo emitió, sin ayuda, en ≤ 5 min; (b) encuentra las diferencias sembradas de CP‑R1 (§13.4) en ≤ 20 min; (c) quien administra registra la clave de otra empresa comprobando su huella por teléfono en ≤ 10 min; bloque B ≥ 4,0, ningún ítem < 3 | guion en Med, con consigna, paradas y criterio fijados antes de medir; alimenta el indicador del administrador (horizonte §6.1) |

---

## 4. Arquitectura (vistas 4+1)

### 4.1 Principio que se conserva

NORMAS §2: núcleo cerrado, adaptadores abiertos. Lo **genérico de cualquier presupuesto** (documento canónico de
una versión, eslabón de la cadena, comparación de dos presupuestos) va en `core/` con expediente. Las cuentas, la
criptografía y el formato del paquete **no** son del presupuesto: van en paquetes nuevos fuera de `core/`. Lo propio
de un formato de plano va en `adapters/espacio/planos`. Nada de S3 hace que `core/` conozca `ui/`, `api/` ni
`adapters/`.

### 4.2 Vista lógica

| Paquete | Qué contiene | Importa | Toca `core/` |
|---|---|---|---|
| `core/budget/canonico.py` (nuevo) | documento canónico de una versión desde las filas guardadas, y su lectura inversa a `Presupuesto` + composiciones + parámetros + plan | — | **SL‑E8** |
| `core/budget/cadena.py` (nuevo) y `core/models` | tabla aditiva `eslabon_version`; `sellar_version`, `sellar_historial`, `verificar_cadena` | — | **SL‑E7** |
| `core/budget/comparacion.py` (nuevo) | `comparar(a, b)`: diferencia por partida separada en cantidad y precio, función pura | — | **SL‑E9** |
| `seguridad/` (nuevo, raíz) | `cuentas.py` (Argon2, roles, bloqueo), `sesiones.py` (fichas de sesión, expiración), `firma.py` (Ed25519, cifrado de la privada, huella corta), `empresas.py` (claves registradas, revocación), `claves_api.py`, `modelo.py` (tablas de la **base de la instalación**) | biblioteca estándar, `sqlalchemy`, `argon2`, `cryptography` | no; **no importa** `core`, `ui`, `api` ni `adapters` |
| `paquete/` (nuevo, raíz) | `formato.py` (manifiesto, versión del formato, límites), `exportar.py`, `verificar.py`, `modelo.py` (tablas `paq_*` en la base del caso, sin clave foránea a `core/models`, como `esp_*`) | `core` (funciones públicas de `core.budget` y `core.verification`), `seguridad.firma`, `seguridad.empresas` | no; **no importa** `ui`, `api` ni `adapters` |
| `adapters/espacio/planos/` | `auditoria_archivo.py` (DXF), `ids.py` (IFC con `ifctester`), `geometria_plano.py` (R15, `shapely`), `contraste.py` (R16); `data/ids/silice_instalaciones.ids` | `core.contracts`, `ezdxf`, `ifcopenshell`, `ifctester`, `shapely` | no |
| `ui/acceso.py` (nuevo, Streamlit) | pantalla de acceso, primer administrador, cambio de contraseña; **solo lo importa `ui/app.py`** (como `ui/barra.py`) | `seguridad`, `streamlit` | no |
| `ui/entrega.py` y `ui/revision.py` (nuevos, **sin Streamlit**) | orquestan: anexo del espacio (`adapters.espacio`), reglas extra, exportar e importar paquete, reauditoría, diferencias, dictamen | `paquete`, `core`, `adapters.espacio`, `seguridad` | no |
| `ui/paginas/revisar.py`, `ui/paginas/administracion.py` (nuevas) | Revisar un paquete; Cuentas y claves | `ui.*` (nunca `ui.app`, `ui.barra` ni `ui.acceso`) | no |
| `api/seguridad.py` (nuevo) y `api/rutas/auditorias.py` (nueva) | dependencia que exige la clave de API; `POST /v1/auditorias` | `seguridad.claves_api`, `core`, `adapters.espacio` (reglas del anexo, si viene) | no |

**Dos bases.** Las cuentas, sesiones, claves y el registro de accesos viven en la **base de la instalación**
(`SILICE_INSTALACION`, por defecto `data/instalacion.db`), no en la base del caso: hoy el caso se cambia por sesión
(`ui/caso.py`) y las cuentas son de la instalación, no de un caso. La cadena (`eslabon_version`) y los paquetes
recibidos (`paq_*`) viven en la base del caso, junto a lo que sellan.

`tests/unit/test_arquitectura.py` se amplía: `seguridad` solo con biblioteca estándar, `sqlalchemy`, `argon2` y
`cryptography`; `paquete` sin `ui`, `api`, `adapters`, `streamlit`; `ui/acceso.py` solo desde `ui/app.py`;
`ui/entrega.py` y `ui/revision.py` en `PROHIBIDOS_EN_UI` (`streamlit`, `pandas`, `ui.caso`);
`TERCEROS_POR_ADAPTADOR["espacio"]` agrega `shapely` e `ifctester`. NORMAS §6 se enmienda con los dos paquetes de la
raíz.

### 4.3 Vista de procesos

```
app.py -> ui.acceso.exigir_sesion(): ficha vigente? no -> acceso y st.stop(); sí -> menú según roles
guardar versión -> una Session: guardar_edicion(..., responsable=usuario de la sesión)
                   -> gancho de la hoja: copia esp_* y cadena.sellar_version(..., anexos={"espacio": ...})
entregar paquete -> ui.entrega: verificar_cadena -> paquete.exportar -> contraseña -> firma -> descarga
revisar paquete -> guardar_subida -> paquete.verificar -> canonico.leer -> motor -> auditar(propias)
                   -> comparacion.comparar(entrega anterior | base del revisor, actual) -> pantalla
```

### 4.4 Vista física y de desarrollo

- **Dependencias nuevas:** `argon2-cffi` y `cryptography` en el grupo principal (las usan la interfaz y la API);
  `shapely` declarada en el extra `planos` (hoy transitiva); `ifctester` en el extra `planos` (paquete y licencia **a
  confirmar en S3‑0**: IfcOpenShell es LGPL); `qrcode` opcional (D, a confirmar). Licencias de las cuatro primeras
  verificadas en S3‑0 y anotadas en la bitácora.
- **Streamlit:** cada pestaña del navegador es una sesión con su `st.session_state`; las sesiones comparten el
  proceso, así que **nada por usuario** va en variables de módulo ni en `st.cache_resource`/`st.cache_data` (hoy
  `ui/` no usa caché; la regla queda escrita y una prueba de arquitectura busca usos nuevos).
- **SQLite:** un escritor a la vez; el tiempo de espera de bloqueo se fija y se prueba (§13.4). Paquetes recibidos
  en `data/paquetes/`, con el nombre de `nombre_seguro` y su huella.

### 4.5 Decisiones de diseño

| # | Decisión | Alternativa descartada | Costo si es errónea |
|---|---|---|---|
| DA‑S3‑1 | Sesión propia en `st.session_state` con ficha aleatoria validada contra la base de la instalación; recargar la página (F5) pide entrar de nuevo | cookie con un componente de terceros; `st.login` (proveedor externo) | si F5 molesta en Med, agregar un componente de cookies con su revisión de seguridad |
| DA‑S3‑2 | Base de la instalación separada de la del caso | tablas de usuario en cada caso | migrar cuentas a cada caso y decidir qué pasa al abrir el caso de otra instalación |
| DA‑S3‑3 | La cadena se ancla con los paquetes: la firma se pone **al exportar**, no en cada guardado | firmar cada eslabón (pide la contraseña de la clave en cada guardado) | la cadena dentro de la base se puede reescribir entera por quien tenga el archivo (§12); se detecta solo entre entregas |
| DA‑S3‑4 | El paquete lleva el contenido de la **versión entregada** y solo las huellas de las anteriores | paquete con todas las versiones | paquetes más grandes; el revisor no puede reauditar versiones intermedias |
| DA‑S3‑5 | Un paquete es un ZIP con nombres fijos; la firma cubre el manifiesto y el manifiesto cubre cada archivo | firmar el ZIP entero (el orden y la compresión cambian los bytes) | rehacer formato y verificador; la versión del formato lo permite |
| DA‑S3‑6 | `shapely` (coma flotante) solo **detecta**; toda cantidad o distancia informada sale de las coordenadas `Decimal` | calcular con `shapely` | R15 podría informar distancias con error de redondeo |
| DA‑S3‑7 | El revisor reaudita **en memoria** (no carga el APU ajeno al catálogo) y guarda el paquete, el resultado y el dictamen en `paq_*` | persistir con UC‑05 | conflicto de códigos con el catálogo (`importacion.py:208`) |
| DA‑S3‑8 | Una huella o una clave de API se guardan como SHA‑256 (son aleatorias de 256 bits); las contraseñas, con Argon2 | Argon2 para todo | ninguno práctico; Argon2 en cada petición de la API sería lento |

---

## 5. Cuentas, roles y sesión

### 5.1 Roles y permisos

| Acción | arma | revisa | administrador |
|---|---|---|---|
| Crear proyecto, editar la hoja, guardar versión, importar plano, exportar Excel | sí | no (solo lectura) | no |
| Entregar paquete (firmar exige además la contraseña de la clave) | sí | no | no |
| Revisar paquete o presupuesto externo, dictamen | no | sí | no |
| Cuentas, desbloqueo, claves de la empresa, empresas registradas, claves de API, registro de accesos | no | no | sí |

Una cuenta puede tener varios roles (en una empresa pequeña una persona es las tres cosas); la pantalla de cuentas
**avisa** cuando una cuenta arma y revisa a la vez («la misma persona no debería revisar lo que armó»). El rol se
comprueba en la navegación **y** dentro de `render()` de cada página.

### 5.2 Contraseñas

- `argon2-cffi`: el objeto que calcula y verifica la huella con los parámetros por defecto de la biblioteca;
  verificar lanza una excepción propia si no coincide; la biblioteca dice cuándo una huella vieja necesita
  recalcularse (se recalcula al entrar). **Nombres exactos de clase y métodos: a confirmar en la implementación.**
- Política: 10 a 128 caracteres, distinta del usuario, sin reglas de composición (en la línea de NIST SP 800‑63B;
  **la cita se verifica en S3‑0** antes de usarla en la tesis). Se acepta cualquier carácter Unicode.
- **Usuario inexistente:** se verifica igual contra una huella de relleno, para que el tiempo de respuesta no delate
  qué cuentas existen; el mensaje es siempre «Usuario o contraseña incorrectos».
- **Contraseña temporal** (alta o restablecimiento por el administrador): obliga a cambiarla al entrar (21e).
- Las cuentas **no se borran**: se desactivan, para que los registros firmados con su nombre sigan teniendo dueño.

### 5.3 Sesión en Streamlit (sin servicios externos)

1. Al entrar, `seguridad.sesiones` crea una ficha aleatoria de 256 bits (`secrets`), guarda en la base de la
   instalación **su SHA‑256**, el usuario, la creación y la última actividad, y devuelve la ficha.
2. `ui.acceso` la guarda en `st.session_state["silice_sesion"]` (clave que no es de widget).
3. En cada ejecución del guion, `exigir_sesion()` busca la huella, comprueba que no esté cerrada, que la última
   actividad tenga menos de **30 min** y la creación menos de **12 h**, y que la cuenta siga activa; renueva la
   última actividad (como mucho una escritura por minuto, para no cargar SQLite).
4. Si expiró: se borra la ficha, se conserva el borrador en `st.session_state` **marcado con el usuario dueño**, y
   se muestra el acceso con «Su sesión se cerró por inactividad. Entre de nuevo: su borrador sigue aquí.» Si entra
   otro usuario en esa pestaña, el borrador se descarta con aviso.
5. «Cerrar sesión» marca la ficha como cerrada y limpia la pestaña. El reloj se inyecta (`ahora`) en las pruebas.

### 5.4 Bloqueo por intentos

Cinco fallos **seguidos** de una cuenta la bloquean **15 min** («Demasiados intentos fallidos. Espere 15 minutos o
pida al administrador que desbloquee la cuenta.»); un acierto pone el contador en cero. Además, una pestaña que acumula
10 fallos (con cualquier usuario) deja de aceptar intentos hasta recargarse, para frenar a quien prueba muchas
cuentas. Todo intento queda en `evento_acceso`. Si el único administrador queda bloqueado o pierde su contraseña,
`scripts/restablecer_administrador.py` (exige acceso al equipo) emite un código de instalación nuevo.

### 5.5 Primer administrador

Al crear la base de la instalación se genera un **código de instalación** de un solo uso, se guarda su SHA‑256 y se
escribe el código en `data/codigo_instalacion.txt` (y en la consola). Mientras no haya usuarios, la pantalla de
acceso pide ese código para crear el primer administrador; al usarlo, el archivo se borra y la huella se invalida.
Así nadie que llegue por la red antes que el dueño del equipo puede quedarse con la instalación (con la red local
encendida, Streamlit escucha en todas las interfaces). El instalador de S5 hará este paso por el usuario.

### 5.6 Interfaz

- Acceso: dos campos y «Entrar»; el rechazo en lenguaje llano, sin traza. Barra: «Sesión: Ana Pérez (arma) · Cerrar
  sesión»; la hoja muestra «Responsable: Ana Pérez» en lugar del campo.
- Administración (`ui/paginas/administracion.py`), pestañas con `st.segmented_control`: **Personas** (alta, roles,
  desactivar, desbloquear, contraseña temporal), **Clave de la empresa**, **Empresas registradas**, **Claves de
  API**, **Registro de accesos**.
- Menú: Trabajo (según rol), **Revisión** (nueva, rol *revisa*), Investigación, **Administración** (nueva, rol
  administrador). Se enmienda RF‑42 (de dos a cuatro secciones, visibles según rol) y RF‑43 («ninguna pantalla de
  Trabajo **que el rol permita**»); el modo entrega sigue ocultando Investigación; los recorridos de UC‑12 se filtran
  por rol y ningún paso apunta a una pantalla que el rol no ve (RF‑37).

---

## 6. Registro encadenado (SL‑E7, SL‑E8)

### 6.1 Documento canónico de una versión (SL‑E8)

`core.budget.canonico.documento(session, version) -> bytes`: JSON UTF‑8, claves ordenadas, sin espacios, con
`"formato": "silice-presupuesto"` y `"version_formato": 1`. Contiene, **desde las filas guardadas** (no
recalculadas): código, fecha, moneda, proyecto; parámetros; renglones con su ítem completo (código, descripción,
unidad, cantidad, precio unitario, total, `origen_id`, `origen_tipo`, regla, parámetros, especificaciones); pendientes;
instantánea de composiciones con sus líneas (precio, `insumo_id` lógico como código de insumo, referencia de precio
si la hay) y rendimiento; plan; curva; hallazgos guardados; lista de precios (nombre, moneda, tasa y fecha de la tasa
de SF‑E7). Todo `Decimal` se escribe como el **texto exacto** que guarda `DecimalExacto`; no hay `id` de filas (cambian
entre instalaciones). `leer(bytes)` hace lo inverso y valida el formato. El mismo documento es `presupuesto.json` del
paquete y el cuerpo de `POST /v1/auditorias` (DRY).

### 6.2 Qué se encadena (SL‑E7)

Tabla aditiva `eslabon_version` (§7.4, sin migración, como en SF3). Por versión:

```
huella_contenido = SHA-256(documento canónico)
huella_cambios   = SHA-256(JSON canónico de sus RegistroCambio en orden: objeto, clave, campo,
                           valor_anterior, valor_nuevo, fuente, responsable, fecha_hora ISO)
huella_anexos    = SHA-256(JSON canónico de [(nombre, SHA-256(bytes del anexo))] ordenado)
huella_eslabon   = SHA-256(JSON canónico de {anterior, codigo, contenido, cambios, anexos,
                           usuario, fecha_hora, tipo, version_formato})
```

`anterior` es la `huella_eslabon` del eslabón previo **del mismo proyecto** (el génesis usa 64 ceros). El anexo
`espacio` lo aporta quien tiene las tablas `esp_*` (la hoja, por el gancho que ya existe en `guardar_edicion`); `core`
no lo interpreta. Cada camino que crea una versión (edición, restauración, cotización, revaloración por UC‑02,
importación UC‑05, primera versión de la hoja) la sella en la **misma transacción**. El eslabón también da
responsable a las versiones de UC‑02, que hoy no lo tienen.

**Dos usuarios a la vez:** índice único (`proyecto_id`, `anterior`). Si dos guardados leen el mismo último eslabón,
el segundo falla al confirmar; la interfaz reintenta una vez sobre el eslabón nuevo y, antes de guardar, avisa si la
versión vigente ya no es la que el usuario abrió («Luis guardó la 006 después de que usted abrió la 005; su versión
saldrá de la 005 y no incluye esos cambios»).

### 6.3 Verificación

`verificar_cadena(session, proyecto, anexos_de)` **recalcula** cada huella desde la base y devuelve el primer fallo
(contenido, registro, anexo o eslabón cambiado; versión sin sellar; bifurcación). La pestaña Trazabilidad muestra
«Cadena íntegra: 7 versiones» o «Cadena rota en la versión 005: su contenido no coincide con su huella; alguien
cambió la base fuera del sistema. Revíselo con el administrador antes de entregar un paquete.»

### 6.4 Versiones anteriores sin huella

La primera vez que se abre un caso con S3, `sellar_historial` sella **todas** las versiones existentes, por proyecto y
en orden de `id`, con `tipo = "retroactivo"`, el usuario y la fecha (el documento sale de las filas, así que se puede
sellar aun una versión que ya no recarga). Hoja, paquete y revisión lo declaran: «Versiones 001 a 004 selladas el
2026‑11‑03: prueban que no cambiaron **desde** esa fecha; antes no hay garantía.»

**Anterioridad entre paquetes.** El revisor guarda la cadena de cada paquete recibido. Un paquete nuevo del mismo
proyecto y emisor debe **contener como prefijo** la cadena del último recibido; si no, es 23c: «Este paquete
reescribe la historia: la versión 004 que recibió el 2026‑11‑10 tenía otra huella.» Un paquete cuya cadena es prefijo
de uno ya recibido es **anterior** y se avisa.

---

## 7. Firma por empresa (S‑D5)

### 7.1 Clave de la empresa

- Generación en el equipo con `cryptography`: clave privada Ed25519, su pública, firmar bytes y verificar (la
  verificación lanza una excepción de firma inválida). Serialización de la privada en PKCS8 cifrada con la contraseña
  mediante el cifrado «mejor disponible» de la biblioteca, y carga con contraseña. **Nombres exactos y el algoritmo
  de derivación que usa ese cifrado: a confirmar en la implementación**; si la derivación no es robusta, se declara y
  se evalúa en la revisión de seguridad antes de construir.
- La contraseña de la clave es **distinta** de las contraseñas de cuenta (mínimo 12 caracteres), nunca se guarda y
  se pide en cada firma. Quien la conoce puede firmar en nombre de la empresa: la empresa decide a quién se la da.
- Se guarda cifrada en la base de la instalación y se **exporta cifrada** para respaldo. Contraseña perdida = clave
  perdida: se genera otra y se avisa a los receptores.
- Estados: **activa** (una por empresa), **retirada** (sustituida sin compromiso; los paquetes firmados con ella
  siguen verificando, con aviso) y **revocada** (comprometida o perdida; deja de verificar).

### 7.2 Huella corta legible

`huella = SHA-256(clave pública en bytes crudos)`; se muestran sus primeros **100 bits** en base32 sin caracteres
ambiguos, en cinco grupos de cuatro (`K7QF‑M9XR‑A2PT‑W4HN‑C8DV`), legibles por teléfono. Opcional (D): un QR con la
huella para compararla con la cámara del teléfono; no hace falta leerlo con el sistema.

### 7.3 Registro de claves de otras empresas y revocación

1. La contratista exporta su **archivo de clave pública** (`.silice-clave`: JSON con nombre, RIF opcional, clave
   pública en base64, huella, fecha) y lo manda por cualquier medio.
2. El administrador lo sube; el sistema calcula la huella **él mismo** (no confía en la escrita).
3. Pantalla: «Llame a la contratista por un número que **ya conocía** (no el que viene en el correo) y pídale que lea
   la huella que muestra su Sílice. ¿Coincide con esta?» y la huella grande. El administrador marca «Coincide»,
   indica con quién habló, cómo (teléfono, en persona, QR) y la fecha. Sin esa marca la clave no se registra.
4. **Revocación propia:** el administrador revoca su clave y el sistema genera un **aviso de revocación** firmado
   con esa misma clave si todavía la tiene (si se perdió, se avisa por teléfono). **Revocación ajena:** importar el
   aviso firmado (se verifica con la clave registrada) o marcarla a mano con el motivo. Como la fecha de firma la
   declara el emisor, tras la revocación **ningún** paquete de esa clave verifica; los dictámenes ya emitidos
   conservan el estado que tenían al recibirse.

### 7.4 Modelo de datos

**Base de la instalación** (`seguridad/modelo.py`, Base propia):

| Tabla | Columnas |
|---|---|
| `usuario` | id, login (único, inmutable), nombre, huella_clave (Argon2), roles, activo, debe_cambiar_clave, fallos_seguidos, bloqueado_hasta, creado, creado_por |
| `sesion` | huella_ficha (PK), usuario_id, creada, ultima_actividad, cerrada, motivo_cierre |
| `evento_acceso` | id, fecha_hora, login_intentado, usuario_id (nulo si no existe), tipo (entrada, fallo, bloqueo, salida, expiración, cambio de clave, alta, baja, desbloqueo, firma, clave de API), detalle (sin secretos) |
| `codigo_instalacion` | huella, creado, usado |
| `clave_empresa` | id, empresa, rif, publica (bytes crudos), privada_cifrada (PEM), huella, estado, creada, creada_por, fecha_estado, motivo |
| `empresa_registrada` | id, empresa, rif, publica, huella, estado, comprobada_con, metodo, fecha_comprobacion, registrada_por, fecha_estado, motivo |
| `clave_api` | id, nombre (p. ej. «plugin de AutoCAD de la oficina técnica»), huella_ficha, prefijo visible (8 caracteres), creada, creada_por, ultimo_uso, revocada |

**Base del caso:** `eslabon_version` (core, SL‑E7): presupuesto_id (PK, FK), proyecto_id, anterior, huella_contenido,
huella_cambios, huella_anexos, huella_eslabon, usuario, fecha_hora, tipo (`normal`, `retroactivo`), version_formato;
índice único (proyecto_id, anterior). Tablas `paq_*` (`paquete/modelo.py`, sin FK a `core/models`):
`paq_recibido` (id, archivo, huella del archivo, ruta, empresa declarada, empresa verificada, estado, proyecto,
código, cadena en JSON, recibido_por, fecha) y `paq_dictamen` (paquete, resultado: conforme, con observaciones o
rechazado; notas, usuario, fecha, estado de verificación al dictaminar).

---

## 8. Paquete auditado

### 8.1 Formato (`.silice`, `version_formato = 1`)

ZIP con estos nombres y ningún otro:

| Archivo | Contenido | Para qué |
|---|---|---|
| `manifiesto.json` | `formato: "silice-paquete"`, `version_formato`, versión de Sílice, fecha y hora de emisión, empresa y huella de su clave (o `null`), usuario emisor, proyecto, código de la versión, moneda, total declarado, **lista de archivos con SHA‑256 y tamaño**, última `huella_eslabon`, algoritmo `Ed25519` | lo que se firma |
| `presupuesto.json` | documento canónico (§6.1) | reauditoría |
| `informe.json` | informe del emisor (hallazgos con regla, severidad, mensaje, `origen_id`) | comparar con la reauditoría |
| `registro.json` | todos los eslabones del proyecto hasta la versión entregada y los `RegistroCambio` de cada una | verificar la cadena y ver quién cambió qué |
| `presupuesto.xlsx` | Excel de la hoja (`exportar_hoja`) | lectura humana; **no** se reimporta (DA‑SF‑4) |
| `anexos/espacio.json` | espacio de la versión, si tiene | reauditar R8–R10, R15 |
| `firma.ed25519` | firma de los bytes exactos de `manifiesto.json` (ausente si se exporta sin firma) | autenticidad |

### 8.2 Exportar (UC‑22)

Herramienta **Entregar paquete** de la barra (rol *arma*), sobre la versión abierta: verifica la cadena (22c),
muestra el resumen (total, hallazgos por severidad, cadena, empresa), pide la contraseña de la clave y genera el
archivo en memoria; lo descarga con `st.download_button` y registra la firma en `evento_acceso`. El paquete se
genera **solo al pulsar**.

### 8.3 Verificar (UC‑23)

1. **Abrir con cuidado** (§8.4). 2. **Formato:** `formato` y `version_formato` conocidos (23f). 3. **Integridad:**
cada archivo existe, su tamaño y su SHA‑256 coinciden con el manifiesto, no sobra ni falta ninguno. 4.
**Autenticidad:** si hay firma y la huella del manifiesto es de una empresa registrada, se verifica con **la clave
pública registrada** (nunca con una que venga en el paquete). 5. **Cadena** de `registro.json` y su último eslabón
igual al del manifiesto y a la `huella_contenido` de `presupuesto.json`. 6. **Anterioridad** (§6.4).

| Estado | Cuándo | Banner |
|---|---|---|
| **Verificado** | 1–6 bien, firma válida de empresa registrada activa (o retirada, con aviso) | verde: «Verificado: emitido por *Contratista Demo, C.A.* el 2026‑11‑10. No se alteró desde que se firmó.» |
| **No verificado** | sin firma, o empresa no registrada, o clave revocada | ámbar: «No verificado: dice venir de *X*, pero no se pudo comprobar. Se audita igual.» Con la empresa no registrada, botón «Registrar su clave» (lleva a Administración) |
| **Alterado** | una huella no coincide, o la firma no es válida con la clave registrada, o la cadena no cuadra | rojo: «Alterado: *presupuesto.json* cambió después de firmarse. No confíe en este paquete; pida uno nuevo.» Se audita igual para mostrar qué contiene |
| **Rechazado** | ZIP dañado, inseguro o de formato desconocido | mensaje con el motivo y qué hacer; no se audita (no hay qué leer) |

Sin firma, las huellas solo prueban que el archivo no se dañó por accidente: cualquiera que lo cambie puede
recalcularlas. El banner ámbar lo dice con esas palabras.

### 8.4 Abrir un ZIP ajeno sin riesgo

Se lee con `zipfile` en memoria, sin extraer al disco. Se rechaza: entrada con nombre fuera de la lista de §8.1,
nombre repetido (un ZIP admite dos entradas con el mismo nombre), ruta absoluta o con `..`; archivo de más de 20 MB;
contenido descomprimido de más de 100 MB en total o por archivo de más de 50 MB; relación de compresión mayor de 100
a 1; JSON de más de 200 000 renglones. Límites como constantes con `SUPUESTO_DECLARADO` hasta medir paquetes reales.

---

## 9. Vista del administrador que revisa (UC‑23)

**Pantalla «Revisar un paquete»** (`ui/paginas/revisar.py`, sección Revisión). Pasos en el orden del trabajo:

1. **Subir** el `.silice` o un Excel UC‑05 (23d), con `ui.subidas.guardar_subida`.
2. **Estado de verificación** (§8.3), siempre visible arriba, con la huella del emisor y la cadena.
3. **Reauditoría propia.** `core.budget.canonico.leer` → el motor recalcula cada precio unitario desde las
   composiciones y parámetros del paquete (no se confía en los precios ni en los totales escritos) → `auditar` con
   `REGLAS` y, si hay anexo de espacio, las reglas del espacio y R15. Tres listas: hallazgos **que el emisor no
   declaró**, **que declaró y ya no aparecen**, y comunes. Un precio unitario o total declarado que no cuadra con el
   recálculo es una diferencia con su monto.
4. **Diferencias y su costo** (`core.budget.comparacion`, SL‑E9), con un control para elegir contra qué:
   - **la entrega anterior** del mismo proyecto (paquete ya recibido);
   - **la base de precios del revisor** (lista de su empresa, S1): el presupuesto del paquete revalorado en memoria
     con sus precios, emparejando insumos por **referencia de precio** (Ref MaPreX) o por código; lo que no empareja es
     **«no contrastable»**, se lista y no suma.
   Por partida: Δ total = **(q₂ − q₁) × PU₁** (desvío por cantidad) **+ (PU₂ − PU₁) × q₂** (desvío por precio); las dos
   columnas suman exacto el Δ total (`Decimal`); partidas que solo están en una versión son desvío por cantidad
   entero. Ordenado por |Δ|, con la suma arriba (ejemplo: «La entrega 005 cuesta 1 240,50 USD más que la 004: 980,00 por
   cantidades y 260,50 por precios»).
5. **Quién cambió qué**: los `RegistroCambio` entre la entrega anterior y esta, con responsable y fuente.
6. **Dictamen**: conforme, con observaciones o rechazado, con notas obligatorias salvo «conforme»; se guarda en
   `paq_dictamen` con el estado de verificación de ese momento. **Exportar la revisión** a Excel (hojas Verificación,
   Hallazgos, Diferencias, Cambios) con el escape de M‑1.

Pasos con `st.segmented_control`; la verificación en `st.session_state` con clave propia (no se repite en cada
interacción); el Excel solo al pulsar Exportar.

---

## 10. APU de otras herramientas

- **Excel (UC‑05):** el formato de `core/budget/importacion.py`, con **plantilla descargable** (cinco hojas y una fila
  de ejemplo); se lee con `leer_presupuesto_tabular` y se audita en memoria (DA‑S3‑7); errores con archivo, hoja y
  fila, como hoy. Sin cadena ni firma: siempre «no verificado».
- **API para plugins:** `POST /v1/auditorias`, cuerpo = documento canónico (§6.1) y, opcional, el anexo de espacio;
  cabecera con la clave de API (nombre a fijar en S3‑0, p. ej. `X-Silice-Clave`). No guarda nada. Respuesta:
  informe, totales recalculados y diferencias entre lo declarado y lo recalculado; montos como texto (convención
  de la API). Sin clave, clave desconocida o revocada: **401** con `{"detalle": ...}` y
  `evento_acceso`. Las claves las crea el administrador; se muestran **una sola vez** y se guardan como SHA‑256.
  Esquema publicado en `docs/api.json`. La API sigue apagada por defecto y escuchando solo en la red local (S5); en
  0.8.0 la clave se exige en las rutas `/v1/`, y S5 decide extenderla a las rutas antiguas.

---

## 11. Auditoría de planos (horizonte §5.1)

### 11.1 Archivo DXF dañado

La importación pasa de `ezdxf.readfile` a la **lectura con recuperación** de `ezdxf` (módulo de recuperación, que
devuelve el documento y un auditor con errores y arreglos) y, sobre el documento, a su **auditoría**. **API exacta: a
confirmar en la implementación.** Errores que la biblioteca arregla → ítems ADVERTENCIA del informe de importación
(«el plano tenía 3 errores de estructura que se repararon: …»); irrecuperables → rechazo con mensaje (UC‑14d).

### 11.2 IFC con requisitos mínimos (IDS)

`data/ids/silice_instalaciones.ids` declara, en el estándar IDS de buildingSMART, lo mínimo que la hoja necesita:
espacio con altura, aparato sanitario con diámetro, tomacorriente con circuito, tablero con nombre. Las clases y
propiedades exactas salen de las clases IFC fijadas en SF0 y se versionan **antes** del código. `ifctester` abre el
IDS, valida el modelo y entrega por requisito los elementos que fallan (**API a confirmar en la implementación**).
Cada fallo es un ítem del informe de importación con su `GlobalId`; lo que falte sigue pendiente y R8 lo marca.

### 11.3 R15 Coherencia geométrica del plano (`shapely`)

`ReglaVerificacion` de `adapters/espacio`, construida con la instantánea del espacio como R8–R10 (DA‑SF‑8).
Detecta, con índice espacial y tolerancia 0,001 m:

| Condición | Severidad |
|---|---|
| dos ambientes se superponen en más de 0,01 m² | ERROR |
| dos puntos de la misma especialidad y tipo a menos de 0,001 m (duplicados) | ERROR |
| escala imposible: lado de ambiente < 0,30 m o > 200 m; altura < 2,00 m o > 12 m | ADVERTENCIA |
| punto a más de 100 m de su fuente | ADVERTENCIA |

Los umbrales son `SUPUESTO_DECLARADO` (fuentes candidatas a verificar en S3‑0); R15 baja a ADVERTENCIA lo que dependa
de un umbral supuesto, como R10 (RS‑11). No repite R9 (punto fuera de su ambiente, recorridos imposibles): una
prueba comprueba que ningún error sembrado da hallazgos de R9 y R15 a la vez.

### 11.4 R16 Contraste entre dos fuentes

`ReglaContraste(espacio_referencia)`: compara el espacio de la versión con otro (plano contra levantamiento, plano
nuevo contra anterior). Empareja ambientes, fuentes y puntos por especialidad, tipo y posición (vecino más cercano
dentro de una tolerancia declarada, 0,10 m `SUPUESTO_DECLARADO`), y marca **faltantes**, **sobrantes** y
**desplazados**. El costo: la interfaz deriva los ítems de las dos fuentes, los valora con las mismas composiciones y
llama a `core.budget.comparacion` (SL‑E9), por ejemplo «el plano tiene 2 puntos de datos menos que el
levantamiento: −186,40 USD». Es la única forma de ver un plano «coherente pero equivocado» (H‑D9). La segunda
fuente se carga desde la hoja («Contrastar con otro plano o levantamiento»): otro DXF/IFC u otra versión.

### 11.5 Evaluación por errores sembrados

- **Catálogo de errores** (`tests/fixtures/errores_planos/catalogo.md`), escrito **antes** de R15 y R16 y por
  categoría: sin `$INSUNITS`; entidad dañada; bloque en capa equivocada; `ALTURA` faltante; escala ×1000; ambiente
  superpuesto; punto duplicado; punto fuera de todo ambiente; punto sin fuente; `IfcSpace` sin altura; aparato sin
  diámetro; tomacorriente sin circuito; elemento borrado entre dos fuentes; punto desplazado 0,50 m entre dos
  fuentes. Cada uno con la detección esperada (regla o ítem del informe, severidad, fila) y **controles no
  detectables** (un plano coherente pero equivocado sin segunda fuente), que deben dar «no detectado» y miden el
  límite declarado.
- **Sembrador determinista** (`scripts/sembrar_errores_planos.py`, semilla fija) sobre el DXF y el IFC de OF‑001,
  uno y varios errores por archivo, con su lista. **Medición** (`scripts/medir_deteccion_planos.py`): tasa de
  detección = detectados / sembrados detectables, por categoría; falsas alarmas = hallazgos fuera del conjunto exacto
  esperado. Protocolo escrito antes de medir; meta propuesta (a ratificar): 100 % en lo detectable y cero falsas
  alarmas sobre OF‑001 limpio.
- **IfcClash (D):** solo si el IFC trae estructura; detecta choques tubo‑elemento. Es lo segundo en caer (horizonte
  §6).

---

## 12. Amenazas: qué protege y qué no

| Amenaza | ¿Protege? | Cómo, o por qué no |
|---|---|---|
| Alguien cambia el paquete en el camino (correo, WhatsApp, USB) | **sí** | huellas del manifiesto + firma: «Alterado» |
| Alguien fabrica un paquete a nombre de una contratista registrada | **sí**, salvo que tenga su clave privada y su contraseña | la firma se verifica con la clave **registrada**, no con la que trae el paquete |
| Alguien sustituye la clave de la contratista al registrarla (correo falso) | **sí, si** se comprueba la huella por un canal ya conocido | paso 3 de §7.3; si el administrador marca «coincide» sin llamar, no |
| Alguien con la **clave privada y su contraseña** | **no** | firma lo que quiera como esa empresa. Mitigación: contraseña propia, revocación, aviso a receptores |
| Alguien con el archivo de la clave cifrada y una contraseña débil | **parcial** | la derivación de la contraseña frena el ataque por diccionario, no lo impide; mínimo de 12 caracteres |
| Reescribir la historia **dentro** de la base (con acceso al archivo SQLite) | **no** dentro de la base; **sí** entre entregas | la cadena no lleva secreto: quien tiene el archivo puede recalcularla entera. El revisor lo detecta si ya recibió un paquete anterior (§6.4) |
| Reenviar un paquete viejo como si fuera nuevo | **sí** | anterioridad entre paquetes (§6.4) |
| Fecha de emisión falsa | **no** | la fecha la declara el emisor; no hay sellado de tiempo de un tercero (exige internet). Por eso la revocación invalida todos los paquetes de esa clave |
| Un presupuesto firmado pero **equivocado o engañoso** | **no** | la firma prueba quién y que no cambió, no que sea verdad; para eso está la reauditoría, que solo encuentra inconsistencias |
| Robo de la base de la instalación | **parcial** | contraseñas con Argon2 (costosas de romper), fichas y claves de API como huellas; la privada sigue cifrada |
| Adivinar contraseñas por la pantalla de acceso | **sí** | bloqueo por cuenta y por pestaña; tiempo constante con usuarios inexistentes |
| Bloquear a propósito las cuentas de otros | **no** (es el precio del bloqueo) | el administrador desbloquea; el script de restablecimiento si es el administrador |
| Ver las contraseñas en la red local | **no** en 0.8.0 | Streamlit sirve por HTTP; con la red local encendida las contraseñas viajan sin cifrar. S5 decide TLS; mientras tanto, solo en una red de confianza, y la pantalla de Administración lo advierte |
| Quien administra el equipo (Windows) o un programa malicioso en él | **no** | puede cambiar la base de la instalación y las claves registradas, o capturar contraseñas: el sistema confía en el equipo local |
| ZIP malicioso (rutas `..`, bomba de compresión, nombres repetidos) | **sí** | §8.4, sin extraer al disco |
| Plugin con una clave de API robada | **parcial** | la ruta no escribe nada; revocación inmediata; `ultimo_uso` a la vista |
| Sesión abierta en un equipo ajeno | **parcial** | expiración por inactividad y por antigüedad; «Cerrar sesión» |

Nada de esto programa criptografía propia: todo es de `cryptography`, `argon2-cffi`, `hashlib` y `secrets` (maestro
§8).

---

## 13. Pruebas y calidad (IEEE 829, ISO/IEC 25010)

Pruebas antes que código con **el rojo observado** (commit de prueba antes que el de implementación) en SL‑E7 a SL‑E9,
`seguridad`, `paquete`, R15 y R16. Cero omitidas; `-W error`; Linux y Windows.

### 13.1 Oráculos independientes

- **Memoria de diferencias** (`tests/fixtures/memorias/diferencias_s3.md`): dos versiones de un presupuesto pequeño,
  con Δ cantidad, Δ precio y Δ total por partida **hechos a mano**, antes de SL‑E9.
- **Vectores de huella:** el SHA‑256 de un documento canónico de ejemplo calculado aparte (`sha256sum` sobre el
  archivo versionado), no con la función que se prueba.
- **Firma:** los vectores de prueba de Ed25519 del RFC 8032 (sección 7.1) comprueban que se usa la biblioteca bien.
- **Planos:** el catálogo de §11.5 con la detección esperada, antes del código de R15 y R16.

### 13.2 Matriz

| RF / RNF | Prueba |
|---|---|
| RF‑80 | código de instalación válido, usado y ausente; alta con roles; página con rol ajeno por URL → rechazo; ninguna contraseña en la base (búsqueda del texto plano en el archivo SQLite) ni en `evento_acceso` |
| RF‑81 | expiración 29:59 / 30:00 y 11:59:59 / 12:00:00 con reloj inyectado; 4 y 5 fallos; desbloqueo tras 15 min; 10 fallos por pestaña; cerrar sesión; **sesión expirada** en AppTest muestra el acceso y conserva el borrador del mismo usuario; usuario distinto lo descarta |
| RF‑82 | cada camino que escribe `RegistroCambio` o eslabón lleva el usuario de la sesión; búsqueda de `"sistema"` en `ui/` |
| RF‑83 | un byte cambiado en partida, registro, anexo y eslabón → fallo en esa versión; versión sin sellar; dos guardados concurrentes → un solo eslabón por `anterior`; sellado retroactivo declarado; guardar y recargar no cambia la huella |
| RF‑84 | generar, cifrar, cargar con contraseña buena y **errónea** (mensaje, sin traza); huella igual en dos bases; retirar; revocar; aviso de revocación firmado y uno con firma falsa |
| RF‑85, RF‑86 | ida y vuelta entre dos bases temporales; todos los casos de §13.3 |
| RF‑87 | memoria de diferencias; «no contrastable»; reauditoría que encuentra un hallazgo no declarado; dictamen con estado |
| RF‑88 | plantilla descargada → auditada; Excel con partidas del catálogo sin rechazo; API sin clave, con clave revocada y con clave válida (`TestClient`) |
| RF‑89 | auditoría DXF de un archivo dañado a propósito; IDS con un fallo por requisito; cada fila de R15 con su frontera (0,01 m² y una más; 0,001 m); R16 faltante, sobrante y desplazado con su costo; OF‑001 limpio = conjunto exacto |
| RNF‑16 | §13.3 y §13.4; ningún secreto en registros (prueba que captura la salida y el registro de accesos) |
| Arquitectura | importaciones de `seguridad`, `paquete`, `ui/acceso.py`, `ui/entrega.py`, `ui/revision.py`; caché por usuario |
| Interfaz | AppTest de arranque con y sin sesión; acceso, primer administrador, cambio de contraseña; navegación por rol y modo entrega (RF‑43); recorridos de UC‑12 por rol; Administración; Revisar con un paquete de prueba en `st.file_uploader` (a confirmar que AppTest lo admite; si no, se prueba `ui.revision` sin Streamlit y la subida a mano) |

### 13.3 Pruebas de seguridad del paquete (estado esperado)

| Caso | Estado |
|---|---|
| paquete íntegro, firmado, empresa registrada | Verificado |
| un byte cambiado en `presupuesto.json` sin tocar el manifiesto | Alterado (huella) |
| `presupuesto.json` cambiado y manifiesto con la huella nueva, firma vieja | Alterado (firma) |
| todo re‑firmado con otra clave que dice ser de la empresa registrada | Alterado (firma no válida con la clave registrada) |
| todo re‑firmado con una clave no registrada y otro nombre | No verificado; el nombre se muestra «dice venir de» |
| sin `firma.ed25519` | No verificado |
| clave revocada | No verificado (revocada) |
| archivo de más o de menos; nombre repetido; `../x`; ruta absoluta; bomba de compresión; formato 2 | Rechazado |
| cadena del paquete que no extiende la del último recibido | aviso 23c |
| paquete anterior a uno ya recibido | aviso de anterioridad |
| contraseña de la clave errónea al exportar | mensaje, ningún archivo |

### 13.4 Varios usuarios a la vez

- **Automática:** tres hilos con sesiones de la base de la instalación y de un caso temporal guardan versiones a la
  vez durante 20 s; ningún `RegistroCambio` se pierde, la cadena queda lineal y verificable, y cada conflicto da su
  mensaje. Dos `AppTest` con usuarios distintos en el mismo proceso no comparten estado.
- **Manual, en la red local** (procedimiento fijado antes, en la bitácora): un servidor y dos clientes; tres personas
  (arma, arma, revisa), 15 min: entran, editan, guardan, una deja expirar la sesión, se entrega y se revisa un
  paquete. Metas: 0 ediciones perdidas, 0 trazas; el número de usuarios probados se declara como límite (maestro §8).

**Casos con personas (Med):** CP‑R1 (revisar un paquete con diferencias sembradas) y CP‑R2 (registrar una clave
comprobando su huella), casos IEEE 829 del guion; RNF‑17 fija consigna, paradas y criterio antes de medir.

**Regresión en cada compuerta:** las de SF (línea base ± 0,01, 7 de 7, R4 de 3/4 pulg, TI‑001, huellas de RNF‑04,
cuatro hojas) y todo AppTest de UC‑12. Cobertura ≥ 80 % en `seguridad/` y `paquete/`, en la CI.

---

## 14. Tareas por fase

| Fase | Contenido | Rol | Compuerta |
|---|---|---|---|
| **S3‑0** | ERS (UC‑21 a UC‑23, RF‑80 a RF‑89, RNF‑16, RNF‑17, actores), arquitectura, modelo de datos y plan de pruebas enmendados; licencias; API exacta de `argon2-cffi`, `cryptography`, `ezdxf` (recuperación), `ifctester`; IDS; catálogo de errores; memorias; protocolos de RNF‑17 y de §11.5; `scripts/meta_s3.py` | líder, interfaz, adaptadores | GS3‑0 |
| **S3‑1** | `seguridad` (cuentas, sesiones, bloqueo, código de instalación, registro de accesos); `ui/acceso.py`; navegación por rol; RF‑82 en la hoja | interfaz | GS3‑1 |
| **S3‑2** | Núcleo en `inc/silice-s3-nucleo`: SL‑E8, SL‑E7, SL‑E9, con expediente y rojo observado | núcleo | GS3‑2 |
| **S3‑3** | `seguridad.firma`, `seguridad.empresas`; `paquete` (formato, exportar, verificar); Entregar paquete; Administración | interfaz | GS3‑3 |
| **S3‑4** | `ui/revision.py`, Revisar, diferencias, dictamen, plantilla Excel, `POST /v1/auditorias` y claves de API | interfaz | GS3‑4 |
| **S3‑5** | auditoría DXF, IDS, R15, R16, sembrador y medición; IfcClash si sobra tiempo; guion CP‑R1 y CP‑R2 | adaptadores, pruebas | GS3‑5 |

S3‑1 y S3‑5 son independientes y corren en paralelo; S3‑3 necesita S3‑2. Cada compuerta: `meta_s3.py --hasta`
en OK, CI verde en Linux y Windows, los encargos y, en GS3‑1, GS3‑3 y GS3‑4, **el de seguridad**; en GS3‑1 y GS3‑4
el de usabilidad (Nielsen e ISO 9241‑110). GS3‑5 comprueba `git diff gs3-2..HEAD -- core/` vacío (la auditoría de
planos no toca el núcleo).

**Orden de caída:** IfcClash; el QR; la ruta de la API (queda solo el Excel); la comparación contra la base del
revisor (queda la entrega anterior). Cuentas, cadena, firma, paquete y reauditoría no se recortan.

### 14.1 Expedientes en `core/`

| # | Qué | Por qué es genérico | Prueba |
|---|---|---|---|
| SL‑E7 | `eslabon_version` (tabla aditiva) y `core/budget/cadena.py`; todo camino que crea versión la sella | cualquier presupuesto versionado, de cualquier dominio | §13.2 RF‑83 |
| SL‑E8 | `core/budget/canonico.py`: documento canónico y su lectura | describe cualquier versión; lo usan la cadena, el paquete y la API (DRY) | ida y vuelta; vector de huella |
| SL‑E9 | `core/budget/comparacion.py`: diferencia por cantidad y por precio, pura | compara dos presupuestos cualesquiera; S2 (valor ganado) puede reutilizarla | memoria de diferencias |

---

## 15. Rulings para ratificar

| # | Decisión | Costo si es errónea |
|---|---|---|
| RS3‑1 | DA‑S3‑1 a DA‑S3‑8 (§4.5) | el costo de cada una, en su fila |
| RS3‑2 | 30 min de inactividad, 12 h de antigüedad, 5 intentos y 15 min de bloqueo | cambiar cuatro constantes y sus pruebas de frontera |
| RS3‑3 | Primer administrador con código de instalación en un archivo local | si el instalador de S5 lo resuelve de otro modo, se retira la pantalla |
| RS3‑4 | Una cuenta puede armar y revisar, con aviso | prohibirlo exige dos personas en empresas de una |
| RS3‑5 | Sellado retroactivo automático al abrir el caso, declarado | un botón del administrador; versiones sin sellar mientras tanto |
| RS3‑6 | Umbrales de R15, tolerancia de R16 y límites del ZIP como supuestos declarados | cifras discutibles hasta medir o verificar fuente |
| RS3‑7 | Revocar invalida todos los paquetes de esa clave (no hay fecha confiable) | un paquete legítimo antiguo deja de verificar; su dictamen se conserva |
| RS3‑8 | Red local sin TLS en 0.8.0, con aviso | adelantar a S3 la configuración de TLS de S5 |

---

## 16. Riesgos

| Riesgo | Mitigación |
|---|---|
| Streamlit no aguanta varios usuarios en la red local | §13.4 con límite declarado (maestro §8) |
| Criptografía mal usada | solo bibliotecas; vectores del RFC 8032; revisión del encargo de seguridad en tres compuertas |
| Desacuerdo entre el documento canónico y la base (un `Decimal` reescrito) | prueba de ida y vuelta; el texto exacto de `DecimalExacto` |
| Cambios en `core/` sin aval | expedientes; si el tutor rechaza SL‑E7, el paquete viaja sin cadena (solo firma) y se declara |
| `ifctester` con licencia o dependencias incompatibles | se confirma en S3‑0; si no, el IDS se reemplaza por comprobaciones propias con `ifcopenshell` y se declara |
| Los instrumentos de Med cambian (acceso al inicio de CP‑07) | el guion agrega «entrar con la cuenta de prueba» una sola vez, al cerrar S3, como en SF §2 |

---

## 17. Preguntas abiertas

1. ¿Eugenio acepta que recargar la página pida entrar de nuevo (DA‑S3‑1, ratificada en RS3‑1)?
2. ¿La misma persona puede armar y revisar en la misma instalación (RS3‑4)?
3. ¿Se acepta la red local sin TLS en 0.8.0 con aviso, o se adelanta TLS desde S5 (RS3‑8)?
4. Tiempos de sesión y bloqueo (RS3‑2): ¿son razonables para una oficina de obra?
5. ¿Qué datos de la empresa van en la clave pública (nombre, RIF, ciudad) y quién en la empresa conoce la contraseña
   de la clave?
6. ¿El tutor acepta SL‑E7 a SL‑E9 en `core/`?
7. ¿La meta de §11.5 (100 % en lo detectable y cero falsas alarmas sobre OF‑001 limpio) es la correcta para la tesis?
8. ¿CP‑R1 y CP‑R2 entran en Med o en una medición propia del indicador del administrador?
9. ¿El revisor debe poder **devolver** el paquete con observaciones firmadas por su propia empresa (respuesta
   firmada)? No está en este spec.
