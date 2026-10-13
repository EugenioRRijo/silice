# Sílice S3 (versión 0.8.0): cuentas, registro encadenado, firma, paquete auditado y auditoría de planos

| Campo | Valor |
|---|---|
| Estado | **APROBADA por Eugenio el 2026‑10‑11** (revisión 2). Incorpora los rulings RV‑1 … RV‑26 de la revisión por encargo (requisitos, arquitectura, pruebas y calidad, verificador de hechos y **seguridad**; maestro §10). Eugenio ratificó P1 y P2 y decidió P3 y P5 el 2026‑10‑11 (maestro §10.3). Los expedientes SL‑E7, SL‑E8, SL‑E9 y SL‑E12 necesitan además el visto bueno del tutor |
| Fecha | 2026‑10‑11 |
| Rama del spec | `inc/silice` (worktree `.worktrees/silice`) |
| Ramas de construcción | ramas cortas **por fase**, desde el `main` del momento, con PR contra `main` y fusión al cruzar la compuerta de esa fase (RV‑2, §14). S3‑2 es el único carril de núcleo y se abre después de cerrar S2‑3; S3‑1 y S3‑5 son carriles sin núcleo |
| Versión que entrega | **0.8.0** (maestro §5). Se construye **sobre la 0.7.0** (S1 y S2), porque el paquete lleva sus anexos (RV‑1). Los carriles sin núcleo S3‑1 (`seguridad` y `ui/acceso`) y S3‑5 (planos) pueden adelantarse desde `main` y se fusionan al cruzar su propia compuerta |
| Se apoya en | [spec maestro](2026-10-11-silice-1.0.0-design.md) (S‑D3, S‑D4, S‑D5, §3.2, §3.3, §4, §6.3, §7, §10); [S1](2026-10-11-silice-s1-moneda-reajuste-design.md) y [S2](2026-10-11-silice-s2-presupuesto-vivo-design.md) (anexos del paquete, campos `responsable`); [horizonte, revisión 2](2026-10-08-horizonte-reorientacion-design.md) (§2.4, §5.1, §6.1, H‑D7 a H‑D10); [spec SF](2026-10-04-sprint-final-prototipo-design.md) (formato, SF‑E2, SF‑E6, §6.6) |
| Naturaleza de los datos | igual que [NORMAS.md §1](../../NORMAS.md): casos construidos; las empresas, personas y claves de las pruebas son ficticias |

Este documento es la **fuente única** del diseño de S3. No repite el horizonte ni el maestro: los enlaza. Donde el
maestro fija algo transversal (empresa, roles, dos bases, abrir un caso, secretos, formato del paquete, reglas por
contexto, red local, meta y regresión), este spec lo cita y agrega solo el detalle propio de S3; si difieren, manda
el maestro.

---

## 1. Qué se quiere y por qué

### 1.1 El pedido

El horizonte une a **quien arma** y **quien revisa** con un **paquete auditado** (§2.4, H‑D7, H‑D10); el maestro fija
cómo: cuentas locales con tres roles (S‑D4), firma por empresa Ed25519 (S‑D5), sin internet (S‑D3). S3 suma el APU de
otras herramientas y la auditoría de planos (horizonte §5.1, fase R3). Como S3 llega después de S1 y S2, el paquete
también lleva lo que ellos producen: el origen de cada precio y el reajuste (S1), y las valuaciones, los costos reales
y las decisiones de recuperación (S2), para que quien revisa pueda reauditarlo todo (horizonte §2.4: «durante la
obra: valuaciones, reajuste en Bs, alertas»).

### 1.2 Lo que se encontró en el código (2026‑10‑11, rama `inc/silice`)

- **El responsable es un texto que escribe el usuario.** `_exigir_respaldo` (`core/budget/edicion.py:76`) solo
  exige que no venga vacío; `RegistroCambio.responsable` es `String(120)` (`core/models/entidades.py:552`). La hoja
  lo pide en un campo (`ui/paginas/hoja.py:505`) y dos caminos ponen `"sistema"` por defecto (`ui/hoja.py:1594`,
  `core/budget/instantanea.py:450`).
- **UC‑02 no registra responsable.** `CambioPrecio` (`core/models/entidades.py:227`) no tiene esa columna.
- **No hay cuentas, control de acceso, huellas de versión ni firmas.** `ui/caso.py` fija el caso por sesión de
  Streamlit; `api/main.py` no exige clave en ninguna ruta. En el producto no hay **ninguna** huella SHA‑256; en las
  pruebas, las de RNF‑04 y dos comprobaciones de archivo intacto (`tests/unit/test_probar_precios_maprex.py:80`,
  `tests/unit/test_reinicio_seguro.py:44`).
- **Toda versión pasa por un solo embudo.** `core/budget/persistencia.guardar_presupuesto` crea cada versión y
  **deja la transacción abierta** (no confirma). Lo llaman, en `core/`, `actualizacion.py:225`, `cotizacion.py:151`,
  `edicion.py:127` y `:186` e `importacion.py:239`; fuera de `core/`, `ui/hoja.py:1883` (primera versión de la hoja),
  `api/rutas/presupuestos.py:172` y cuatro scripts (`seed_demo.py:445`, `generar_resultados_ml.py:164`,
  `medir_rnf03.py:125`, `probar_precios_maprex.py:461`). `MOTIVOS_VERSION` tiene hoy cuatro valores
  (`entidades.py:505`: edición, restauración, cotización, revaloración); S1 agrega `conversion` y S2 `recuperacion`.
  Los `RegistroCambio` se crean **después** de llamar al embudo (p. ej. `edicion.py:141`).
- **Las pruebas de regresión llaman al embudo sin confirmar.** `tests/integration/test_presupuesto_linea_base.py:65`
  llama a `guardar_presupuesto` sin usuario y no hace `commit`. El diseño del sellado (§6.2) lo respeta, porque esas
  pruebas no se editan (maestro §6.3).
- **SQLite sin espera ni diario WAL.** `core/catalog/sesion.crear_motor` solo activa `PRAGMA foreign_keys`: no fija
  `busy_timeout` ni el diario WAL, y las transacciones son diferidas. Sellar lee el último eslabón y después escribe:
  con dos usuarios a la vez eso da `database is locked` (ARQ‑H2). Por eso SL‑E12 pasa de S5 a S3 (RV‑7).
- **La ruta del caso es libre.** `ui/paginas/inicio.py:50` tiene un `st.text_input` con la ruta del caso, `fijar_caso`
  la usa sin restricción, y `estado_caso` (`ui/caso.py:128`) ejecuta `crear_esquema`, que es DDL, con solo mirar el
  estado. Con la red local encendida, cualquier usuario con sesión haría que el servidor abra o cree un SQLite en
  cualquier ruta, incluidas rutas UNC (SEG‑5). Lo cierra S5‑1 en la 0.6.0 (maestro §4.3, RV‑5); S3 agrega el permiso
  «cambiar de caso» a la matriz de roles (§5.1).
- **`UC‑05` no sirve tal cual para un paquete.** `importar_presupuesto` rechaza un archivo cuyas partidas ya estén en
  el catálogo (`core/budget/importacion.py:208`); un paquete de una contratista que usa los mismos códigos MaPreX
  chocaría. `leer_presupuesto_tabular` sí reconstruye en memoria sin tocar la base (`importacion.py:132`).
- **La auditoría de archivo de `ezdxf` no se invoca.** `adapters/espacio/planos/dxf.py:171` abre el plano con
  `ezdxf.readfile` y ninguna línea de `adapters/` llama a una auditoría. El horizonte §5.1 la daba como «ya en el
  sistema»; se corrigió el 2026‑10‑11 (commit 6674c83). Se construye aquí (RF‑89).
- **`shapely` ya está instalado** como dependencia de `ifcopenshell` 0.8.5 (`uv.lock`), versión 2.1.2; S3 la
  declara como dependencia directa en el extra `planos`. `ifctester` no aparece en `uv.lock`; depende de
  `ifcopenshell` (mismo proyecto, LGPL‑3, versiones atadas), así que va al extra `civil` (o a uno nuevo `ifc`) con
  importación diferida (RV‑24).
- **`.gitignore` solo excluye `*.db`.** `codigo_instalacion.txt`, `paquetes/` y `casos/` quedarían versionables
  dentro de `data/` (ARQ‑H9).
- **Subidas:** las nuevas de S3 (paquete, clave pública, plano de contraste) pasan por `ui/subidas.py` y
  `api/archivos.py`, las funciones únicas de guardado seguro (A‑1).

### 1.3 Criterio de éxito de la versión

Una contratista arma un presupuesto, lo entrega como **paquete firmado**; un administrador de otra instalación lo
recibe, ve **«Verificado: emitido por Contratista Demo, C.A.»**, lo **reaudita sin confiar en el informe ajeno**
(incluidos los precios, el reajuste y las valuaciones que viajan en los anexos), ve en qué difiere de la entrega
anterior y **cuánto dinero representa**. Un byte cambiado en el paquete se detecta. Un APU de otra herramienta se
audita por Excel y por la API. En los planos de OF‑001 con errores sembrados se mide la **tasa de detección** y las
**falsas alarmas** con un protocolo escrito antes de medir.

---

## 2. Alcance

**Incluye:** cuentas, roles y sesión (§5); reglas de la red local que tocan a S3 (§5.6); registro encadenado y su
concurrencia (§6); claves y firma por empresa (§7); paquete auditado con anexos (§8); vista de revisión y diferencia
entre versiones con su costo (§9); APU de otras herramientas (§10); auditoría de planos y errores sembrados (§11);
amenazas (§12); los dos protocolos de medición de quien revisa y de planos (§13.5); y, como **deseable (D)**, la
detección de anomalías en variaciones de precio (RF‑100, fase opcional S3‑6, §3.2), lo primero que cae si falta
tiempo.

**No incluye:** TLS en la red local y activar la API (S5); abrir casos de una lista y Alembic (S5‑1, adelantado a la
0.6.0; S3 solo agrega sus tablas y sus revisiones); servidor en internet (2.x); sellado de tiempo por un tercero
(RFC 3161, exige internet); cifrar el contenido del paquete (se firma, no se oculta); inicio de sesión con un proveedor
externo (`st.login` usa OpenID Connect, contrario a S‑D3); recuperar una clave cuya contraseña se perdió; respuesta
firmada del revisor (pregunta 9). Las anomalías en variaciones de precio ya **no** quedan fuera: entran **dentro como
D (RF‑100), decidido por Eugenio el 2026‑10‑11** (pregunta P5 del maestro §10.3; deja sin efecto, para S3, el valor
por defecto de RV‑21).

---

## 3. Requisitos (enmienda a la ERS, IEEE 830)

**Numeración asignada:** UC‑21 a UC‑23; RF‑80 a RF‑89; RNF‑16 y RNF‑17; expedientes SL‑E7 a SL‑E9 y **SL‑E12**
(pasa de S5 a S3, RV‑7); reglas R15 y R16, según la numeración del spec maestro (§9). **Se usan todos; no queda
ninguno vacante**, y no se usa ningún otro. Los dos casos con personas se llaman aquí **CP‑R1** y **CP‑R2**: su número
definitivo lo asigna el líder en el guion (S4 propone CP‑12 para el suyo).

**Enmienda única de RNF‑08 (RV‑23), en S3‑0.** Texto propuesto: «El sistema no requiere servicios externos ni
credenciales de terceros. Las únicas credenciales son **locales**: las cuentas de la instalación (S3), guardadas en el
propio equipo.» La redacción final con todas sus excepciones (la IA en la nube de S4, el retiro de three.js de S5) se
consolida en S5‑0; ningún otro spec enmienda RNF‑08.

### 3.0 Actores

La ERS §2.3 se enmienda con los tres roles de S‑D4 y el mapa del maestro §4.1 (ratificado por Eugenio el
2026‑10‑11, pregunta P2 del maestro §10.3):

| Actor de la ERS §2.3 o nuevo | Rol en Sílice |
|---|---|
| proyectista / estimador | *arma* |
| residente de obra (UC‑19, S2) | *arma* |
| administrador del catálogo (UC‑17, S1) | *administrador* |
| auditor | *revisa* |
| gerente | *revisa* (si además decide recuperaciones, UC‑20, su cuenta lleva también *arma*) |
| **administrador de la instalación** (nuevo) | *administrador*: cuentas, clave de firma, empresa propia, empresas registradas, red y API |
| **herramienta externa** (nuevo) | ningún rol: un plugin que llama a la API con su **clave de API** |

*Quien revisa* agrupa al administrador del contrato, al cliente o al ente contratante (horizonte §2.4).

### 3.1 Casos de uso

#### UC‑21 — Iniciar sesión y administrar cuentas y claves

- **Actor principal:** cualquier usuario (entrar); administrador de la instalación (administrar).
- **Precondiciones:** instalación con al menos un administrador, o código de instalación vigente (21a).
- **Flujo principal**
  1. El usuario abre Sílice; la pantalla de acceso pide usuario y contraseña. Si el cliente no es el propio equipo,
     muestra el aviso «Conexión sin cifrar» (§5.6).
  2. El sistema verifica la contraseña (Argon2), crea una **ficha de sesión nueva**, lee los roles de la base y
     muestra el menú que esos roles permiten.
  3. El administrador abre Administración: da de alta una persona con sus roles y una contraseña temporal, o cambia
     roles, desactiva, desbloquea o restablece una cuenta.
  4. El sistema registra cada acción en `evento_acceso` (sin secretos) y, al cambiar roles, desactivar o restablecer
     una cuenta, **cierra todas sus sesiones abiertas**.
  5. El usuario cierra sesión; la ficha queda cerrada.
- **Flujos alternativos**
  - *21a. Primera vez:* no hay usuarios; se crea el primer administrador con el código de instalación (§5.5).
  - *21b. Contraseña errónea o usuario inexistente:* «Usuario o contraseña incorrectos», el mismo mensaje y el mismo
    contador en los dos casos.
  - *21c. Cuenta bloqueada por intentos:* mensaje de §5.4; el mismo para un usuario inexistente.
  - *21d. Sesión expirada:* vuelve al acceso **conservando el borrador** para el mismo usuario.
  - *21e. Contraseña temporal:* obliga a cambiarla; al cambiarla se emite una ficha nueva.
  - *21f. El administrador desactiva, desbloquea o restablece una cuenta.*
  - *21g. El administrador genera, retira o revoca la clave de firma de la empresa* (solo desde el propio equipo).
  - *21h. Registra o revoca la clave pública de otra empresa,* con su huella comprobada (§7.3).
  - *21i. Muchos fallos seguidos desde cualquier pestaña:* freno global con espera progresiva (§5.4).
  - *21j. Operación sensible pedida desde otro equipo de la red* (firmar, generar o exportar la clave de firma,
    crear claves de API): se rechaza con «Esta operación solo se hace en el equipo donde está instalado Sílice».
- **Postcondiciones:** sesión vigente con usuario y roles leídos de la base; todo intento y toda acción de
  administración en `evento_acceso`; ningún secreto en claro en la base, en el registro ni en los mensajes.

#### UC‑22 — Entregar el paquete auditado

- **Actor principal:** quien arma. Para firmar hace falta la contraseña de la clave, que conoce **solo** el
  administrador (maestro §4.1, P1, ratificada por Eugenio el 2026‑10‑11): en una empresa pequeña es la misma
  persona con los dos roles, o el administrador la teclea.
- **Precondiciones:** versión guardada y sellada; clave de firma de la empresa activa (si no, 22a); cliente en el
  propio equipo para firmar (22e).
- **Flujo principal**
  1. Quien arma abre la versión y pulsa **Entregar paquete** en la barra.
  2. El sistema verifica la cadena del proyecto (22c) y muestra el resumen: total, hallazgos por severidad, cadena,
     empresa emisora y anexos que viajarán (espacio, reajuste, control, IA).
  3. El usuario elige, si quiere, el **destinatario** (una empresa registrada o un nombre) y escribe la contraseña
     de la clave.
  4. El sistema genera en memoria `presupuesto.json`, `informe.json`, `cadena.json` y los anexos, el manifiesto con
     su `paquete_id` y su `huella_anexos`, y la firma con separación de dominio (§8.1).
  5. El usuario descarga el `.silice`; el sistema guarda su SHA‑256, su `paquete_id`, la versión y el usuario en
     `evento_acceso`.
- **Flujos alternativos**
  - *22a. Sin clave de empresa:* se ofrece exportar **sin firma**, declarado en el paquete.
  - *22b. Contraseña de la clave errónea:* mensaje, no se escribe nada.
  - *22c. La cadena del proyecto está rota:* se rechaza la entrega y se dice en qué versión.
  - *22d. La versión tiene hallazgos ERROR:* se avisa y se entrega igual (el informe viaja).
  - *22e. Firma pedida desde otro equipo de la red:* se rechaza con el mensaje de 21j; se puede exportar sin firma.
  - *22f. El paquete excedería los límites de §8.4:* se rechaza con el motivo; no se genera un paquete que el
    revisor rechazaría.
- **Postcondiciones:** un `.silice` descargado; su SHA‑256 y su `paquete_id` en `evento_acceso`; la base del caso no
  cambia.

#### UC‑23 — Revisar un paquete o un presupuesto externo

- **Actor principal:** quien revisa. **Secundario:** herramienta externa (23e).
- **Precondiciones:** sesión con rol *revisa*, o clave de API vigente (23e).
- **Flujo principal**
  1. Quien revisa sube el `.silice` (o un Excel con el formato UC‑05, 23d).
  2. El sistema lo abre con límites (§8.4), verifica formato, integridad, autenticidad, cadena y anterioridad, y
     muestra el estado con el banner de versión (§8.3).
  3. El sistema reaudita en memoria con sus propias reglas y los anexos (§9, paso 3).
  4. Muestra la **diferencia entre versiones** y su costo frente a la entrega anterior o frente a su base de precios
     (§9, paso 4).
  5. Muestra quién cambió qué y, si quien revisa es también quien armó (usuario emisor o responsable de algún
     eslabón de la cadena del paquete), lo indica (§9, paso 5).
  6. Quien revisa registra su dictamen; el sistema lo guarda atado al SHA‑256 del archivo y con el estado de
     verificación de ese momento.
- **Flujos alternativos**
  - *23a. Sin firma o empresa no registrada:* **no verificado**, se audita igual.
  - *23b. Alterado (huella o firma no cuadran):* banner rojo, se audita igual para mostrar qué cambió.
  - *23c. El paquete es anterior a uno ya recibido o reescribe su historia* (§6.4).
  - *23d. Presupuesto externo en Excel (formato UC‑05):* solo se reaudita; «no contrastable» lo que no se puede
    verificar.
  - *23e. La herramienta externa manda el presupuesto por la API* y recibe el informe.
  - *23f. Formato o versión del paquete desconocidos:* se rechaza con mensaje.
  - *23g. El destinatario es otra empresa:* aviso ámbar «Este paquete se emitió para *X*».
  - *23h. El mismo archivo ya se recibió (mismo SHA‑256):* se abre el registro existente, no se duplica.
- **Postcondiciones:** `paq_recibido` con el SHA‑256 del archivo, su `paquete_id`, su estado y su cadena;
  `paq_dictamen` si se dictaminó, con quién revisó y si coincide con quien armó; nada escrito en el catálogo ni en las versiones del caso.

#### UC existentes que se enmiendan

**UC‑05** (el auditor puede auditar en memoria, sin persistir, desde la vista de revisión; la importación
persistente sigue igual); **UC‑14** (la importación del plano corre la auditoría de archivo DXF, el IDS del IFC y las
reglas R15 y R16); **UC‑15** (el responsable es el usuario de la sesión, no una caja de texto); **UC‑12** (los
recorridos se filtran por rol).

### 3.2 Requisitos funcionales

Prioridad: E = esencial, D = deseable. Fases de §14.

| RF | Requisito | UC | Pri. | Fase | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑80 | Cuentas locales con roles *arma*, *revisa* y *administrador de la instalación* (uno o varios por cuenta) y la matriz de §5.1; contraseñas con Argon2; el primer administrador se crea solo con el **código de instalación** de un solo uso, de al menos 100 bits | UC‑21 | E | S3‑1 | sin código o con código usado se rechaza; el código tiene 20 caracteres base32; ninguna contraseña aparece en la base, en el registro de accesos ni en los mensajes; cada página y cada acción de la matriz rechaza un rol que no le corresponde aunque se llegue por URL |
| RF‑81 | Sesión propia en Streamlit: expira por inactividad (30 min) y por antigüedad (12 h); ficha nueva al entrar y al cambiar la contraseña; todas las sesiones de una cuenta se cierran al restablecerla, desactivarla o cambiar sus roles; roles leídos de la base en cada ejecución; bloqueo tras 5 intentos fallidos seguidos durante 15 min, con el mismo contador y mensaje para usuarios inexistentes; freno global con espera progresiva; cierre de sesión; varios usuarios a la vez sin mezclar estado | UC‑21 | E | S3‑1 | reloj inyectado: 29:59 sigue, 30:00 expira; 4 fallos no bloquean, el 5.º sí, con un login existente y con uno inexistente; cambiar los roles en la base cambia el menú en la ejecución siguiente; dos sesiones AppTest con usuarios distintos no comparten borrador ni caso; prueba de concurrencia de §13.4 |
| RF‑82 | El responsable de todo `RegistroCambio`, de todo eslabón y de **todo campo `responsable`** de las tablas de S1 y S2 (`importacion_indice`, `moneda_proyecto`, `estudio_reajuste`, `linea_base_control`, `valuacion`, `anulacion_valuacion`, `costo_real`, `decision_recuperacion`) es el **usuario autenticado**, congelado como `Nombre <login>` en el momento del cambio; la caja «Responsable» desaparece de la hoja y de las pantallas de S1 y S2 | UC‑15, UC‑21 | E | S3‑1 (S3‑3 para las pantallas de S1 y S2 si S3‑1 se adelanta) | guardar, restaurar, cotizar, convertir, decidir una recuperación, crear la primera versión, asegurar la instantánea, importar índices, registrar valuaciones, anulaciones y costos reales registran al usuario de la sesión; una prueba recorre los metadatos y lista **toda** columna `responsable`: cada una tiene su prueba, y una columna nueva sin prueba hace fallar la lista; ningún camino de `ui/` pasa `"sistema"`; desactivar una cuenta no cambia sus registros |
| RF‑83 | Registro encadenado: cada versión nueva, que nace en el embudo `guardar_presupuesto`, se sella **al confirmar la transacción que la crea** (evento `before_commit`, §6.2) y en esa misma transacción, con un eslabón SHA‑256 que encadena su contenido, sus `RegistroCambio`, sus anexos y el eslabón anterior (§6); el sellado es una invariante de **todo** `MOTIVOS_VERSION` (incluidos `conversion` de S1 y `recuperacion` de S2) y del motivo vacío (versión sin origen); las versiones anteriores se sellan una vez de forma **retroactiva** y declarada; el sistema verifica la cadena | UC‑15, UC‑22 | E | S3‑2 | una prueba recorre la tupla `MOTIVOS_VERSION` y el motivo vacío, y crea una versión de cada uno; otra enumera a **todos** los llamadores del embudo (§1.2) y falla si aparece uno nuevo sin prueba; cambiar un byte de una partida, de un registro, de un anexo o de un eslabón en la base rompe la cadena **en esa versión** y lo dice; una versión posterior al génesis sin eslabón es un error de cadena; confirmar una versión sin usuario se rechaza; guardar y recargar no cambia ninguna huella |
| RF‑84 | Clave de firma de la empresa Ed25519 generada en el equipo, con la privada **cifrada con su propia contraseña** por `seguridad/secretos.py` (Argon2id → AES‑GCM, maestro §4.4); huella corta legible (§7.2); registro de claves públicas de otras empresas con la comprobación de su huella; retiro (se destruye la privada) y revocación; separación de dominio en todo lo que se firma | UC‑21 | E | S3‑3 | la privada nunca aparece sin cifrar en disco ni en el paquete; contraseña de clave errónea da `InvalidTag` y un mensaje sin traza; una contraseña de la lista corta de comunes se rechaza; la huella es la misma en las dos instalaciones; al retirar, la privada deja de existir en la base; una clave revocada deja de verificar |
| RF‑85 | Exportar el paquete auditado (§8): documento canónico (con moneda del proyecto y `precio_origen`), informe, cadena, anexos (`espacio`, `reajuste`, `control`, `ia`), manifiesto con `paquete_id`, `destinatario` opcional y `huella_anexos`, y firma; **sin Excel**; el emisor guarda el SHA‑256 de cada paquete exportado; firmar solo desde el propio equipo | UC‑22 | E | S3‑3 | el paquete exportado se verifica como «Verificado» en otra base con la clave registrada; sin clave se exporta «sin firma» y así se declara; la cadena rota impide exportar; el SHA‑256 del archivo descargado está en `evento_acceso`; una firma pedida desde una IP que no es de bucle local se rechaza |
| RF‑86 | Importar y verificar un paquete: límites leídos con tope (§8.4), integridad (huellas del manifiesto), autenticidad (firma de una empresa registrada y no revocada, con separación de dominio), cadena, posición respecto de paquetes ya recibidos y banner de versión; **siempre** se reaudita con las reglas propias | UC‑23 | E | S3‑4 | cada caso de §13.3 da su estado declarado, con las fronteras exactas de §8.4; un paquete no verificado se audita igual; ninguna entrada del ZIP sale de su carpeta ni excede los límites; el banner dice la versión y la última recibida |
| RF‑87 | Vista de revisión: estado de verificación, reauditoría con los anexos (R11–R14 recomputadas, R12 a la fecha de emisión), **diferencia entre versiones** y su costo (desvío por cantidad y por precio) frente a la entrega anterior y frente a la base de precios del revisor, Excel regenerado desde `presupuesto.json`, dictamen atado al SHA‑256 del archivo y aviso cuando quien revisa es quien armó (maestro §4.1, P2) | UC‑23 | E | S3‑4 | con el par de presupuestos de la memoria de diferencias (§13.1) la vista da los montos de la memoria; R11–R14 del paquete de prueba dan el conjunto exacto de su memoria; el dictamen queda con usuario, fecha, SHA‑256 del archivo, estado de verificación y `revisor_armo`; con un paquete de la empresa propia, un revisor que es el usuario emisor o el `usuario` de un eslabón ve el aviso y su dictamen queda con `revisor_armo` = sí; otro revisor de la misma empresa, o un paquete de una empresa ajena, no lo ve |
| RF‑88 | APU de otras herramientas: Excel con el formato UC‑05 (plantilla descargable) auditado en memoria desde la vista de revisión, y ruta `POST /v1/auditorias` con **clave de API** que recibe el documento canónico (§6.1) y devuelve el informe; cuerpo limitado por un middleware; `TrustedHostMiddleware` | UC‑23, UC‑05 | E | S3‑4 | Excel con partidas del catálogo se audita sin el rechazo de `importacion.py:208`; sin clave o con clave revocada, 401 sin auditar; cuerpo de 20 MiB pasa y de 20 MiB + 1 B da 413 sin leerlo entero; con clave, el informe coincide con el de la vista |
| RF‑89 | Auditoría de planos: auditoría de archivo DXF, requisitos IDS del IFC con `ifctester`, R15 (coherencia geométrica, `shapely`, severidad por condición), R16 (contraste entre dos fuentes, con el costo de la diferencia) y evaluación por **errores sembrados** con el protocolo de §13.5 | UC‑14 | E | S3‑5 | cada error del catálogo sembrado se detecta con la regla o el ítem de informe declarados; cada fila de R15 y R16 cumple sus fronteras (§11.3, §11.4); OF‑001 limpio da el conjunto exacto escrito en S3‑0; la tasa de detección y las falsas alarmas cumplen la meta del protocolo: 100 % de lo detectable y 0 falsas alarmas (ratificada por Eugenio el 2026‑10‑11, pregunta P8 del maestro §10.3) |
| RF‑100 | Anomalías en variaciones de precio: sobre la serie fechada de precios de un insumo (listas de la empresa de S1, RF‑67, y listas MaPreX, cada precio con su fecha), llevada a USD con la tasa de cada precio (RF‑65) y reducida a variaciones entre puntos consecutivos, el sistema marca las variaciones atípicas como **ADVERTENCIA** (`CODIGO_ATIPICO`), **nunca ERROR**, reutilizando el detector existente `ml.anomaly.precios_atipicos` (Isolation Forest, `SEMILLA` = 42, `UMBRAL_ATIPICO` = −0,05, se abstiene con menos de `MINIMO_OBSERVACIONES` = 8 variaciones) | UC‑17, UC‑23 | **D** | S3‑6 | serie sembrada de 10 precios (9 variaciones) con **un** atípico sembrado → el conjunto exacto de hallazgos es ese único punto, con severidad ADVERTENCIA; serie de 10 precios **sin** atípico → conjunto vacío; serie de 8 precios (7 variaciones) → abstención (vacío); ningún hallazgo de RF‑100 es ERROR ni bloquea guardar, exportar o firmar; sin el extra `ml` no hay hallazgo ni traza |

**RF‑100 (D) cae primero** (decisión de Eugenio del 2026‑10‑11, P5): no tiene número de RNF, no toca `core/` y no
entra en el criterio de éxito de §1.3. **No se inventa un método nuevo:** se reutiliza `ml/anomaly/detector.py`
(I6.1, RF‑29) y el código `CODIGO_ATIPICO` de `core/budget/presupuesto.py`, con severidad ADVERTENCIA, como ya hacen
`core/budget/actualizacion.py` (UC‑07, paso 5) y `ui/composicion.py:advertencia_precio_atipico`; lo nuevo es solo
armar la serie fechada en USD de un insumo (en `ml/anomaly/` o en `ui/composicion.py`, sin importar la base desde
`ml/`). Los umbrales del detector son los ya declarados en ese módulo (SUPUESTO_DECLARADO, RS3‑6); no se ajustan para
S3. **Amenaza declarada:** con datos ficticios no se valida la tasa real de detección ni de falsas alarmas; RF‑100 se
prueba solo con **series sembradas** cuyo oráculo se escribe a mano antes del código (qué punto es el atípico y cuál
es el conjunto exacto de hallazgos), y la tesis lo presenta como apoyo al revisor, no como medición.

**IfcClash queda fuera de RF‑89** (REQ‑21): es una mejora deseable (D) sin número propio (§11.6). Si se construye, se
agrega como criterio D de UC‑14 en la enmienda de la ERS, sin cambiar el criterio esencial de RF‑89.

### 3.3 Requisitos no funcionales (ISO/IEC 25010)

| RNF | Característica | Requisito | Medición |
|---|---|---|---|
| RNF‑16 | Seguridad (confidencialidad, integridad, no repudio, responsabilidad, autenticidad) | Contraseñas de cuenta solo como Argon2 (parámetros por defecto de `argon2-cffi`, con semáforo); clave privada solo cifrada con `seguridad/secretos.py`; ningún secreto en registros, mensajes ni paquete; el 100 % de las alteraciones de §13.3 detectadas; ninguna página, acción ni ruta nueva accesible sin sesión, rol o clave; operaciones sensibles solo desde el propio equipo; límites del ZIP, del JSON y de la API (§8.4); texto ajeno siempre por `texto_seguro()`; mensajes sin traza | pruebas de §13.3 y §13.4; revisión por el encargo de seguridad con la tabla de amenazas (§12) |
| RNF‑17 | Usabilidad (reconocimiento, prevención de errores, ISO 9241‑110) | En las condiciones de CP‑07, con personas que no son el autor: (a) quien revisa abre un paquete y dice su estado de verificación y quién lo emitió, sin ayuda, en ≤ 5 min; (b) encuentra las diferencias sembradas de CP‑R1 en ≤ 20 min; (c) quien administra registra la clave de otra empresa comprobando su huella por teléfono en ≤ 10 min; bloque B ≥ 4,0, ningún ítem < 3 | guion en Med, con consigna, paradas y criterio fijados antes de medir. El **indicador del administrador** (horizonte §6.1) no se reduce a RNF‑17: se mide con su propio protocolo de dos condiciones (§13.5 a) |

### 3.4 Reglas externas en los contextos de S3

La tabla única de qué regla corre en cada contexto está en el maestro §3.3 (RV‑9); aquí solo lo que toca a S3:

- **Hoja en vivo:** R15 si la versión tiene espacio; R16 a pedido, con una segunda fuente.
- **Reauditoría del paquete (§9):** R8–R10 y R15 si viene `anexos/espacio.json`; R11–R12 recomputadas con el
  `precio_origen` de `presupuesto.json` y `anexos/reajuste.json`, contra la referencia MaPreX **de la instalación que
  revisa**; R13–R14 recomputadas si viene `anexos/control.json`. R16 no corre: las diferencias entre entregas las da
  SL‑E9. **R12 se evalúa a la fecha de emisión del paquete** (la del manifiesto), no a la de hoy, y R13–R14 al corte
  que traiga el anexo.
- **API `POST /v1/auditorias`:** R8–R10 y R15 si viene el anexo de espacio; R11–R12 con lo que traiga el documento;
  R13–R14 no. La fecha de evaluación de R12 viaja en el cuerpo (`fecha_evaluacion`, obligatoria; valor por defecto,
  a confirmar en S3‑0) y la respuesta la declara, para que la misma petición dé siempre el mismo informe.
- **Hoja y lista de precios (RF‑100, D):** la advertencia de variación atípica corre al ver la pestaña Precios de la
  hoja y al importar o revisar la lista de la empresa de S1; no corre en la reauditoría del paquete (§9) ni en la
  API, y nunca es ERROR.
- **Toda reevaluación es en memoria:** nunca reescribe filas ni hallazgos guardados, así que no cambia
  `huella_contenido` ni rompe la cadena.

---

## 4. Arquitectura (vistas 4+1)

### 4.1 Principio que se conserva

NORMAS §2: núcleo cerrado, adaptadores abiertos. Lo **genérico de cualquier presupuesto** (documento canónico de
una versión, eslabón de la cadena, diferencia entre dos versiones y revaloración en memoria, concurrencia de SQLite)
va en `core/` con expediente. Las cuentas, la criptografía y el formato del paquete **no** son del presupuesto: van en
paquetes nuevos fuera de `core/`. Lo propio de un formato de plano va en `adapters/espacio/planos`. Nada de S3 hace
que `core/` conozca `ui/`, `api/` ni `adapters/`.

### 4.2 Vista lógica

| Paquete | Qué contiene | Importa | Toca `core/` |
|---|---|---|---|
| `core/budget/canonico.py` (nuevo) | documento canónico de una versión desde las filas guardadas, y su lectura inversa a `Presupuesto` + composiciones + parámetros + plan | — | **SL‑E8** |
| `core/budget/cadena.py` (nuevo) y `core/models/cadena.py` (nuevo, reexportado) | tabla aditiva `eslabon_version`; `sellar_version`, `sellar_historial`, `verificar_cadena`; el sellado de lo pendiente al confirmar (§6.2) | — | **SL‑E7** |
| `core/budget/persistencia.py` | `guardar_presupuesto` recibe `usuario` y `anexos_de` y marca la versión por sellar (único punto de cambio de SL‑E7) | — | **SL‑E7** |
| `core/budget/comparacion.py` (nuevo) | `diferencia_entre_versiones(a, b)`: diferencia por partida separada en cantidad y precio, función pura; `revalorar(documento, lista)`: el presupuesto revalorado en memoria con otra lista, emparejando insumos por referencia de precio o por código (o reutilizando `core/budget/actualizacion` si expone esa función pura; se decide en S3‑2) | — | **SL‑E9** |
| `core/catalog/sesion.py` | `busy_timeout`, diario WAL y `BEGIN IMMEDIATE` en las transacciones que crean versión | — | **SL‑E12** |
| `seguridad/` (nuevo, raíz) | `cuentas.py` (Argon2 con semáforo, roles, bloqueo, freno global), `sesiones.py` (fichas de sesión, expiración, invalidación), `secretos.py` (Argon2id → AES‑GCM, maestro §4.4; lo usa también la clave de IA de S4), `firma.py` (Ed25519, separación de dominio, huella corta), `empresas.py` (empresa propia y empresas registradas, retiro y revocación), `claves_api.py`, `red.py` (¿el cliente es de bucle local?), `modelo.py` (tablas de **`instalacion.db`**) | biblioteca estándar, `sqlalchemy`, `argon2`, `cryptography` | no; **no importa** `core`, `ui`, `api` ni `adapters` |
| `paquete/` (nuevo, raíz) | `formato.py` (manifiesto, versión del formato, nombres admitidos, límites, lector JSON estricto), `exportar.py`, `verificar.py`, `anexos.py` (arma y lee `anexos/*.json`), `modelo.py` (tablas `paq_*` en la base del caso, sin clave foránea a `core/models`, como `esp_*`) | `core` (funciones públicas de `core.budget` y `core.verification`), `seguridad.firma`, `seguridad.empresas` | no; **no importa** `ui`, `api` ni `adapters` |
| `adapters/espacio/planos/` | `auditoria_archivo.py` (DXF), `ids.py` (IFC con `ifctester`, **importación diferida**), `geometria_plano.py` (R15, `shapely`), `contraste.py` (R16); `data/ids/silice_instalaciones.ids` | `core.contracts`, `ezdxf`, `ifcopenshell`, `ifctester`, `shapely` | no |
| `ui/acceso.py` (nuevo, Streamlit) | pantalla de acceso, primer administrador, cambio de contraseña, aviso de conexión sin cifrar; **solo lo importa `ui/app.py`** (como `ui/barra.py`) | `seguridad`, `streamlit` | no |
| `ui/texto_seguro.py` (nuevo, **sin Streamlit**) | `texto_seguro(texto)`: escapa Markdown; única vía para mostrar texto ajeno (maestro §4.6, RV‑14) | biblioteca estándar | no |
| `ui/entrega.py` y `ui/revision.py` (nuevos, **sin Streamlit**) | orquestan: anexos (`adapters.espacio` y los de S1 y S2), reglas externas por contexto, exportar e importar paquete, reauditoría, diferencia entre versiones, Excel regenerado, dictamen | `paquete`, `core`, `adapters.espacio`, `seguridad` | no |
| `ui/paginas/revisar.py`, `ui/paginas/administracion.py` (nuevas) | Revisar un paquete; Administración (Personas, Empresa y clave de firma, Empresas registradas, Claves de API, Registro de accesos; S5 agrega Instalación y S4 la clave de IA) | `ui.*` (nunca `ui.app`, `ui.barra` ni `ui.acceso`); `administracion` además `asistente` (maestro §3.1) | no |
| `api/seguridad.py` (nuevo) y `api/rutas/auditorias.py` (nueva) | dependencia que exige la clave de API; middleware de tamaño de cuerpo; `TrustedHostMiddleware`; `POST /v1/auditorias` | `seguridad.claves_api`, `core`, `adapters.espacio` (reglas del anexo, si viene) | no |

**Dos bases (maestro §4.2, RV‑4).** Todo vive en la carpeta de datos (`%LOCALAPPDATA%\Silice\datos\` en el producto;
en desarrollo, `SILICE_DATOS`, por defecto `data/`):

- **`instalacion.db`** (`SILICE_INSTALACION`, que fija el lanzador): cuentas, sesiones, intentos de acceso, código de
  instalación, empresa propia, clave de firma, empresas registradas, claves de API y `evento_acceso`. Metadatos del
  paquete `seguridad`. Son de la instalación, no de un caso: el caso se cambia por sesión.
- **`casos\*.db`**: el presupuesto y todo lo del caso, con `eslabon_version` (`core.models`) y `paq_*` (`paquete`),
  junto a lo que sellan. `silice.db` es el caso por defecto.

Dos entornos de Alembic (o dos `version_locations`), cada uno con su `alembic_version` y su `METADATAS` explícita
(S5‑1, adelantado a la 0.6.0, RV‑3). S3 agrega la primera revisión del entorno de la instalación (tablas de
`seguridad`) y una revisión del caso (`eslabon_version`, `paq_*`). Las dos bases se respaldan y adoptan juntas; la
prueba de deriva de RNF‑20 recorre también `seguridad` y `paquete`. Paquetes recibidos en `datos\paquetes\`, con el
nombre de `nombre_seguro` y su huella. Abrir un caso: solo de la lista de `datos\casos\` y con
`operacion.base_datos.preparar_base` (maestro §4.3, S5‑1).

**Empresa (maestro §4.1, RV‑6; ratificada por Eugenio el 2026‑10‑11, pregunta P1).** Una sola **empresa propia**
por instalación (tabla `empresa_propia` en `instalacion.db`: nombre, RIF, ciudad opcional) y las **empresas ajenas**
registradas (`empresa_registrada`). Desde S3, los campos `empresa_nombre` y `empresa_rif` de la lista de precios de S1
se rellenan desde la empresa propia (instantánea de texto, sin clave foránea entre bases). La contraseña de la clave
de firma la conoce **solo** el administrador; no hay no repudio individual: el paquete declara el usuario emisor
(SEG‑6). Las empresas de los paquetes recibidos se registran como ajenas (`empresa_registrada`), nunca como propia.

`tests/unit/test_arquitectura_s3.py` (archivo propio, con los ayudantes compartidos de `test_arquitectura.py`,
RV‑2): `seguridad` solo con biblioteca estándar, `sqlalchemy`, `argon2` y `cryptography`; `paquete` sin `ui`, `api`,
`adapters`, `streamlit`; `ui/acceso.py` solo desde `ui/app.py`; `ui/entrega.py`, `ui/revision.py` y
`ui/texto_seguro.py` en `PROHIBIDOS_EN_UI` (`streamlit`, `pandas`, `ui.caso`); **ningún** `unsafe_allow_html` en
`ui/`; `TERCEROS_POR_ADAPTADOR["espacio"]` agrega `shapely` e `ifctester`. `PAQUETES_FUERA_DEL_NUCLEO` suma
`seguridad` y `paquete` (la lista completa, con `asistente`, `operacion` y `migraciones`, la fija el maestro §3.1),
como exige `test_la_guardia_cubre_todo_paquete_de_primer_nivel_fuera_del_nucleo`. NORMAS §6 se enmienda con los dos
paquetes de la raíz.

### 4.3 Vista de procesos

```
app.py -> ui.acceso.exigir_sesion(): ¿ficha vigente? ¿roles (leídos de la base)?
          no -> acceso (aviso si el cliente es remoto) y st.stop(); sí -> menú según roles
guardar versión -> una Session con BEGIN IMMEDIATE (SL-E12):
                   guardar_presupuesto(..., usuario=usuario de la sesión, anexos_de=...) -> versión por sellar
                   -> RegistroCambio -> gancho de la hoja (copia esp_*)
                   -> commit: antes de confirmar, cadena.sella lo pendiente (anexos_de corre aquí)
entregar paquete -> ¿cliente de bucle local? -> ui.entrega: verificar_cadena -> paquete.exportar(anexos)
                   -> contraseña -> secretos.descifrar -> firma(b"silice-paquete-v1\0" + manifiesto)
                   -> descarga -> SHA-256 del archivo a evento_acceso
revisar paquete -> guardar_subida -> paquete.verificar (lectura con tope) -> canonico.leer -> motor
                   -> auditar(REGLAS + externas del contexto «reauditoría», R12 a la fecha de emisión)
                   -> comparacion.diferencia_entre_versiones(entrega anterior | revalorar(base del revisor))
                   -> pantalla (todo texto ajeno por texto_seguro)
```

### 4.4 Vista física y de desarrollo

- **Dependencias nuevas** (en el PR temprano «dependencias Sílice», maestro §3, RV‑2): `argon2-cffi` y
  `cryptography` en el grupo principal (las usan la interfaz y la API); `shapely` declarada en el extra `planos`
  (hoy transitiva; R15 la usa también con los DXF); `ifctester` en el extra `civil` (o en uno nuevo `ifc`), con
  importación diferida en `adapters/espacio/planos/ids.py`, para no arrastrar `ifcopenshell` al instalador básico
  (RV‑24); `qrcode` opcional (D, a confirmar). Licencias verificadas en S3‑0 y anotadas en la bitácora (IfcOpenShell
  e `ifctester` son LGPL‑3).
- **Streamlit:** cada pestaña del navegador es una sesión con su `st.session_state`; las sesiones comparten el
  proceso, así que **nada por usuario** va en variables de módulo ni en `st.cache_resource`/`st.cache_data` (hoy
  `ui/` no usa caché; la regla queda escrita y una prueba de arquitectura busca usos nuevos). Excepciones declaradas:
  el semáforo de Argon2 y el freno global (estado del proceso, no de un usuario) y la clave de IA descifrada, que es
  de la instalación (S4, maestro §4.4).
- **SQLite (SL‑E12):** diario WAL, `busy_timeout` fijo (5 s, `SUPUESTO_DECLARADO`) y `BEGIN IMMEDIATE` en las
  transacciones que crean versión, para tomar el bloqueo de escritura **antes** de leer el último eslabón. La receta
  exacta con SQLAlchemy y `pysqlite` (evento `begin` con `isolation_level=None`) se confirma en S3‑0. Se prueba con
  §13.4.
- **Red local:** §5.6.
- **`.gitignore`** (ARQ‑H9): agrega `codigo_instalacion.txt`, `paquetes/` y `casos/` (`instalacion.db` ya queda
  cubierto por `*.db`).

### 4.5 Decisiones de diseño

| # | Decisión | Alternativa descartada | Costo si es errónea |
|---|---|---|---|
| DA‑S3‑1 | Sesión propia en `st.session_state` con ficha aleatoria validada contra la base de la instalación; recargar la página (F5) pide entrar de nuevo; cada pestaña exige entrar | cookie con un componente de terceros; `st.login` (proveedor externo) | si F5 molesta en Med, agregar un componente de cookies con su revisión de seguridad |
| DA‑S3‑2 | Base de la instalación separada de la del caso | tablas de usuario en cada caso | migrar cuentas a cada caso y decidir qué pasa al abrir el caso de otra instalación |
| DA‑S3‑3 | La cadena se ancla con los paquetes: la firma se pone **al exportar**, no en cada guardado | firmar cada eslabón (pide la contraseña de la clave en cada guardado) | la cadena dentro de la base se puede reescribir entera por quien tenga el archivo (§12); se detecta solo entre entregas |
| DA‑S3‑4 | El paquete lleva el contenido de la **versión entregada** y solo las huellas de las anteriores | paquete con todas las versiones | paquetes más grandes; el revisor no puede reauditar versiones intermedias |
| DA‑S3‑5 | Un paquete es un ZIP con nombres fijos; la firma cubre el manifiesto (con separación de dominio) y el manifiesto cubre cada archivo | firmar el ZIP entero (el orden y la compresión cambian los bytes) | rehacer formato y verificador; la versión del formato lo permite |
| DA‑S3‑6 | `shapely` (coma flotante) solo **detecta**; toda cantidad o distancia informada sale de las coordenadas `Decimal` | calcular con `shapely` | R15 podría informar distancias con error de redondeo |
| DA‑S3‑7 | El revisor reaudita **en memoria** (no carga el APU ajeno al catálogo) y guarda el paquete, el resultado y el dictamen en `paq_*` | persistir con UC‑05 | conflicto de códigos con el catálogo (`importacion.py:208`) |
| DA‑S3‑8 | Una ficha de sesión o el secreto de una clave de API se guardan como SHA‑256 (son aleatorios de 256 bits); las contraseñas, con Argon2 | Argon2 para todo | ninguno práctico; Argon2 en cada petición de la API sería lento |
| DA‑S3‑9 | Se sella **en el embudo** `guardar_presupuesto`: marca la versión y la sella justo antes de confirmar, cuando ya existen sus `RegistroCambio` y sus anexos | sellar en cada camino que crea versión | un camino nuevo podría crear versiones sin eslabón; las pruebas de §13.2 RF‑83 lo atrapan |
| DA‑S3‑10 | El Excel **no viaja** en el paquete: el revisor lo regenera desde `presupuesto.json` (SEG‑2) | llevar `presupuesto.xlsx` del emisor | un Excel con cifras distintas de las auditadas, o con vínculos y fórmulas ajenas, ganaría credibilidad con el banner verde |
| DA‑S3‑11 | La privada se cifra con Argon2id → AES‑GCM (composición de primitivas de las bibliotecas, maestro §4.4) | PKCS8 con el cifrado «mejor disponible» de `cryptography` | si su derivación fuera débil (p. ej. PBKDF2 con pocas iteraciones), un robo de la base o de un respaldo permitiría probar contraseñas sin límite |

---

## 5. Cuentas, roles y sesión

### 5.1 Roles y permisos

Matriz del maestro §4.1 (ratificada por Eugenio el 2026‑10‑11, pregunta P2 del maestro §10.3), con las acciones de
S1, S2 y S3:

| Acción | arma | revisa | administrador |
|---|---|---|---|
| Crear proyecto, editar la hoja, guardar versión, importar plano, contrastar planos (R16), exportar el Excel de la hoja | sí | solo lectura | no |
| Convertir la moneda del proyecto y hacer estudios de reajuste (S1) | sí | solo lectura | no |
| Línea base de control, valuaciones (registrar y anular), costos reales (S2) | sí | solo lectura | no |
| Decidir una recuperación (S2) | sí | solo lectura | no |
| Entregar paquete (firmar exige además la contraseña de la clave y el propio equipo) | sí | no | no |
| Cambiar de caso (elegirlo de la lista de `datos\casos\`) | sí | no | sí |
| Abrir paquetes o presupuestos externos, reauditar, dictamen | no | sí | no |
| Cuentas, desbloqueo, cierre de sesiones, registro de accesos | no | no | sí |
| Empresa propia; clave de firma (generar, exportar, retirar, revocar; solo desde el propio equipo); empresas registradas | no | no | sí |
| Lista de precios de la empresa e importar los datos del BCV (S1) | no | no | sí |
| Red local y API; claves de API (crear solo desde el propio equipo) | no | no | sí |
| Cambiar la carpeta de datos (S5) | no | no | sí, solo desde el propio equipo |

Una cuenta puede tener varios roles (en una empresa pequeña una persona es las tres cosas); una misma persona
**puede** tener *arma* y *revisa* (P2, ratificada). La pantalla de cuentas lo **informa** sin impedirlo («esta cuenta
podrá revisar paquetes que ella misma armó; la vista de revisión lo indicará»); el paquete y la cadena registran
quién armó, y el dictamen quién revisó y si coincide (§9, paso 5). El rol se
comprueba en la navegación **y** dentro de `render()` de cada página o de la función de `ui/` que ejecuta la acción,
con los roles leídos de la base en cada ejecución.

### 5.2 Contraseñas

- `argon2-cffi`: el objeto que calcula y verifica la huella con los parámetros por defecto de la biblioteca;
  verificar lanza una excepción propia si no coincide; la biblioteca dice cuándo una huella vieja necesita
  recalcularse (se recalcula al entrar). **Nombres exactos de clase y métodos: a confirmar en S3‑0.** Un semáforo
  limita las verificaciones simultáneas (4, `SUPUESTO_DECLARADO`): cada una usa unos 64 MiB.
- Política: 10 a 128 caracteres, distinta del usuario, sin reglas de composición (en la línea de NIST SP 800‑63B;
  **la cita se verifica en S3‑0** antes de usarla en la tesis), y fuera de una lista corta de contraseñas comunes.
  Se acepta cualquier carácter Unicode.
- **Usuario inexistente:** se verifica igual contra una huella de relleno, para que el tiempo de respuesta no delate
  qué cuentas existen; el mensaje es siempre «Usuario o contraseña incorrectos», y el contador y el mensaje de
  bloqueo (§5.4) son los mismos.
- **Contraseña temporal** (alta o restablecimiento por el administrador): obliga a cambiarla al entrar (21e). Los
  cambios hechos por una cuenta después de un restablecimiento del administrador y antes de que la persona cambie su
  contraseña se marcan en la trazabilidad («hecho tras un restablecimiento del administrador», SEG‑6).
- Las cuentas **no se borran**: se desactivan, para que los registros con su nombre sigan teniendo dueño.

### 5.3 Sesión en Streamlit (sin servicios externos)

1. Al entrar (y al cambiar la contraseña), `seguridad.sesiones` crea una ficha **nueva** aleatoria de 256 bits
   (`secrets`), guarda en la base de la instalación **su SHA‑256**, el usuario, la creación y la última actividad, y
   devuelve la ficha. La ficha nunca sale del servidor.
2. `ui.acceso` la guarda en `st.session_state["silice_sesion"]` (clave que no es de widget).
3. En cada ejecución del guion, `exigir_sesion()` busca la huella, comprueba que no esté cerrada, que la última
   actividad tenga menos de **30 min** y la creación menos de **12 h**, que la cuenta siga activa, y **lee sus roles
   de la base**; renueva la última actividad (como mucho una escritura por minuto, para no cargar SQLite).
4. Si expiró: se borra la ficha, se conserva el borrador en `st.session_state` **marcado con el usuario dueño**, y
   se muestra el acceso con «Su sesión se cerró por inactividad. Entre de nuevo: su borrador sigue aquí.» Si entra
   otro usuario en esa pestaña, el borrador se descarta con aviso.
5. «Cerrar sesión» marca la ficha como cerrada y limpia la pestaña. Restablecer, desactivar o cambiar los roles de una
   cuenta cierra **todas** sus fichas. El reloj se inyecta (`ahora`) en las pruebas.
6. **A confirmar en S3‑0:** si Streamlit permite reanudar una sesión del servidor presentando su identificador al
   reconectar. Si lo permite, quien escucha la red local podría tomar la sesión; se declara en §12 y pesa en la
   decisión de TLS (RS3‑8).

### 5.4 Bloqueo por intentos y freno global

- **Por login:** cinco fallos **seguidos** con el mismo login lo bloquean **15 min** («Demasiados intentos fallidos.
  Espere 15 minutos o pida al administrador que desbloquee la cuenta.»); un acierto pone el contador en cero. El
  contador vive en la tabla `intento_acceso` (por login normalizado) y se aplica igual a logins **inexistentes**, con
  el mismo mensaje, para no delatar qué cuentas existen. Las filas de logins inexistentes se purgan a las 24 h.
- **Global:** recargar la pestaña no reinicia nada. Tras 20 fallos en 10 min en todo el proceso (o por IP del
  cliente, si `st.context.ip_address` la da; API a confirmar en S3‑0), cada intento nuevo espera 1, 2, 4… s, hasta 60
  s (cifras `SUPUESTO_DECLARADO`).
- Todo intento queda en `evento_acceso`. Si el único administrador queda bloqueado o pierde su contraseña,
  `scripts/restablecer_administrador.py` (exige acceso al equipo) emite un código de instalación nuevo y **cierra las
  sesiones de los administradores**.

### 5.5 Primer administrador

Al crear la base de la instalación se genera un **código de instalación** de un solo uso con al menos **100 bits**
(20 caracteres base32 de `secrets`), se guarda su SHA‑256 y se escribe el código en
`datos\codigo_instalacion.txt` (y en la consola). El código se acepta **solo** mientras no haya usuarios o haya un
restablecimiento pendiente, con el mismo freno de §5.4. Al usarlo, el archivo se borra y la huella se invalida. Así
nadie que llegue por la red antes que el dueño del equipo puede quedarse con la instalación. El instalador de S5 hará
este paso por el usuario.

### 5.6 Red local (maestro §4.7, RV‑15)

- **Dónde escucha:** Streamlit y Uvicorn escuchan en la **IP explícita de la interfaz elegida** al activar la red
  local (S5), por defecto `127.0.0.1`; nunca en todas las interfaces. `browser.serverAddress` fijo, CORS y XSRF
  explícitos, `TrustedHostMiddleware` en la API, y ningún `.streamlit/config.toml` dentro de `{app}\codigo` distinto
  del oficial.
- **Solo desde el propio equipo:** firmar; generar, exportar, retirar o revocar la clave de firma de la empresa;
  registrar la clave de IA (S4); crear claves de API. `seguridad.red.es_local(ip)` acepta solo IP de bucle local;
  la IP la da `st.context.ip_address` (API exacta a confirmar en S3‑0; si no está disponible, esas operaciones se
  permiten solo con la red local apagada).
- **Aviso en la pantalla de acceso:** cuando el cliente no es el propio equipo y no hay TLS, la pantalla de acceso
  (no solo Administración) dice «Conexión sin cifrar: su contraseña viaja legible por la red. Úsela solo en una red de
  confianza».
- **Red de confianza:** la red propia con WPA2 o WPA3; no la Wi‑Fi de la obra ni un punto de acceso compartido. Se
  escribe en el manual y en el aviso de activación (S5).
- **El filtro de IP privadas no es un control:** cualquier túnel o proxy local hace llegar todo como `127.0.0.1`. El
  control real es la sesión (interfaz) y la clave (API); se declara en §12.

### 5.7 Interfaz

- Acceso: dos campos y «Entrar»; el rechazo en lenguaje llano, sin traza. Barra: «Sesión: Ana Pérez (arma) · Cerrar
  sesión»; la hoja muestra «Responsable: Ana Pérez» en lugar del campo.
- Administración (`ui/paginas/administracion.py`), pestañas con `st.segmented_control`: **Personas** (alta, roles,
  desactivar, desbloquear, contraseña temporal), **Empresa y clave de firma**, **Empresas registradas**, **Claves de
  API**, **Registro de accesos** (S5 agrega **Instalación**; S4, la clave de IA de la empresa).
- Menú: Trabajo (según rol), **Revisión** (nueva, rol *revisa*), Investigación, **Administración** (nueva, rol
  administrador). Se enmienda RF‑42 (de dos a cuatro secciones, visibles según rol) y RF‑43 («ninguna pantalla de
  Trabajo **que el rol permita**»); el modo entrega sigue ocultando Investigación; los recorridos de UC‑12 se filtran
  por rol y ningún paso apunta a una pantalla que el rol no ve (RF‑37).
- **Texto ajeno** (nombres de empresa, descripciones de partidas de un paquete o de un Excel externo, notas, nombres
  de capas o de `IfcSpace` de planos ajenos, `anexos/ia.json`): siempre por `texto_seguro()`, o con `st.text`,
  `st.code` o celdas de tabla. Nunca interpolado en `st.markdown`, `st.info`, `st.error` ni en rótulos.

---

## 6. Registro encadenado (SL‑E7, SL‑E8, SL‑E12)

### 6.1 Documento canónico de una versión (SL‑E8)

`core.budget.canonico.documento(session, version) -> bytes`: JSON UTF‑8, claves ordenadas, sin espacios, con
`"formato": "silice-presupuesto"` y `"version_formato": 1`. Contiene, **desde las filas guardadas** (no
recalculadas): código, fecha, moneda de la versión, **moneda del proyecto** (S1, la vigente a la fecha de la
versión), proyecto; parámetros; renglones con su ítem completo (código, descripción, unidad, cantidad, precio
unitario, total, `origen_id`, `origen_tipo`, regla, parámetros, especificaciones); pendientes; instantánea de
composiciones con sus líneas (precio, `insumo_id` lógico como código de insumo, referencia de precio si la hay, y su
**`precio_origen`** de S1: moneda original, precio original, fecha, tasa con su fecha y su fuente, propio o heredado)
y rendimiento; plan; curva; hallazgos guardados; lista de precios (nombre, moneda, tasa y fecha de la tasa de SF‑E7,
empresa). Todo `Decimal` se escribe como el **texto exacto** que guarda `DecimalExacto`; no hay `id` de filas
(cambian entre instalaciones). `leer(bytes)` hace lo inverso y valida el formato con el lector estricto de §8.4. El
mismo documento es `presupuesto.json` del paquete y el cuerpo de `POST /v1/auditorias` (DRY).

### 6.2 Qué se encadena y dónde se sella (SL‑E7)

Tabla aditiva `eslabon_version` (§7.4), en un módulo nuevo `core/models/cadena.py` reexportado, con su revisión de
Alembic (RV‑3). Por versión:

```
huella_contenido = SHA-256(documento canónico)
huella_cambios   = SHA-256(JSON canónico de sus RegistroCambio en orden: objeto, clave, campo,
                           valor_anterior, valor_nuevo, fuente, responsable, fecha_hora ISO)
huella_anexos    = SHA-256(JSON canónico de [(nombre, SHA-256(bytes del anexo))] ordenado)
huella_eslabon   = SHA-256(JSON canónico de {anterior, codigo, contenido, cambios, anexos,
                           usuario, fecha_hora, tipo, version_formato})
```

`anterior` es la `huella_eslabon` del eslabón previo **del mismo proyecto** (el génesis usa 64 ceros). Los anexos de
la versión son los que dependen de ella (hoy, `espacio`, que aporta quien tiene las tablas `esp_*`); `core` no los
interpreta.

**Sellado en el embudo (RV‑7, DA‑S3‑9).** El sellado no depende de una lista de caminos: es una invariante de
`core/budget/persistencia.guardar_presupuesto`, el único embudo (§1.2).

1. `guardar_presupuesto` recibe `usuario` y `anexos_de` (una función inyectada que devuelve los anexos de la
   versión; por defecto, ninguno) y registra la versión nueva como **por sellar** en la sesión.
2. Quien llama agrega sus `RegistroCambio` y corre su gancho (la hoja copia `esp_*`), como hoy.
3. Justo **antes de confirmar** (evento `before_commit` de la sesión, registrado por `core.budget.cadena`; API exacta
   a confirmar en S3‑2), se sella cada versión pendiente: `anexos_de` corre en ese momento, después del gancho, y se
   escribe el eslabón en la **misma transacción**. Una versión pendiente sin `usuario` impide confirmar
   (`ValueError`, nada se escribe).
4. Así quedan cubiertos todos los motivos de `MOTIVOS_VERSION` (edición, restauración, cotización, revaloración,
   `conversion` de S1, `recuperacion` de S2) y el motivo vacío (primera versión de la hoja, importación UC‑05, la API
   y los sembradores). El eslabón también da responsable a las versiones de UC‑02, que hoy no lo tienen.
5. **Todo llamador fuera de `tests/` pasa `usuario=`** (la interfaz, el de la sesión; la API, `api:<identificador de
   la clave>` o `api (sin clave)` en las rutas antiguas hasta que S5 decida; los scripts, `script:<nombre>`); una
   prueba lo comprueba recorriendo el código. Las pruebas de regresión que llaman al embudo **sin confirmar**
   (`test_presupuesto_linea_base.py:65`) no cambian (maestro §6.3).

### 6.3 Concurrencia (SL‑E12)

Las transacciones que crean versión empiezan con `BEGIN IMMEDIATE` sobre una base en diario WAL con `busy_timeout`
(§4.4): quien guarda toma el bloqueo de escritura antes de leer el último eslabón, y el otro espera. El índice único
(`proyecto_id`, `anterior`) queda como salvaguarda: si salta, se rechaza con mensaje y nada se pierde (el borrador
sigue en la pestaña). Antes de guardar, la interfaz avisa si la versión vigente ya no es la que el usuario abrió
(«Luis guardó la 006 después de que usted abrió la 005; su versión saldrá de la 005 y no incluye esos cambios»).

### 6.4 Verificación

`verificar_cadena(session, proyecto, anexos_de)` **recalcula** cada huella desde la base y devuelve el primer fallo
(contenido, registro, anexo o eslabón cambiado; versión sin sellar; bifurcación). La pestaña Trazabilidad muestra
«Cadena íntegra: 7 versiones» o «Cadena rota en la versión 005: su contenido no coincide con su huella; alguien
cambió la base fuera del sistema. Revíselo con el administrador antes de entregar un paquete.»

### 6.5 Versiones anteriores sin huella y anterioridad entre paquetes

La primera vez que se abre un caso con S3, `sellar_historial` sella **todas** las versiones existentes, por proyecto y
en orden de `id`, con `tipo = "retroactivo"`, el usuario y la fecha (el documento sale de las filas, así que se puede
sellar aun una versión que ya no recarga). Hoja, paquete y revisión lo declaran: «Versiones 001 a 004 selladas el
2026‑11‑03: prueban que no cambiaron **desde** esa fecha; antes no hay garantía.»

**Anterioridad entre paquetes.** El revisor guarda la cadena y los anexos de cada paquete recibido. Un paquete nuevo
del mismo proyecto y emisor debe **contener como prefijo** la cadena del último recibido; si no, es 23c: «Este
paquete reescribe la historia: la versión 004 que recibió el 2026‑11‑10 tenía otra huella.» Un paquete cuya cadena es
prefijo de uno ya recibido es **anterior** y se avisa. Una entrada de un anexo de S1 o S2 que estaba en un paquete
anterior y falta en el nuevo también se avisa («la valuación 3 que recibió el 2026‑11‑10 ya no viene»). Esta defensa
es **parcial**: un revisor que nunca recibió un paquete más nuevo, otro revisor o una base restaurada no la tienen; por
eso el banner de §8.3 dice siempre la versión y la última recibida.

---

## 7. Firma por empresa (S‑D5)

### 7.1 Clave de firma de la empresa

- Generación en el equipo con `cryptography`: clave privada Ed25519, su pública, firmar bytes y verificar (la
  verificación lanza una excepción de firma inválida). **Nombres exactos: a confirmar en S3‑0.**
- **Cifrado de la privada** (maestro §4.4, RV‑13): `seguridad/secretos.py` deriva una clave con Argon2id
  (`argon2.low_level.hash_secret_raw`, sal aleatoria de 16 B, m ≥ 64 MiB, t ≥ 3) y cifra los 32 B de la privada con
  AES‑GCM (o ChaCha20‑Poly1305), con dato asociado `"silice-clave-v1"` + huella pública; se guardan parámetros, sal y
  nonce. Una contraseña errónea da `InvalidTag`. Es combinar primitivas de las bibliotecas, no criptografía propia.
  El mismo módulo cifra la clave de IA de la empresa (S4).
- La contraseña de la clave es **distinta** de las contraseñas de cuenta (mínimo 12 caracteres, fuera de la lista
  corta de comunes), nunca se guarda y se pide en cada firma. Quien la conoce puede firmar en nombre de la empresa: por
  defecto, el administrador (maestro §4.1).
- Se guarda cifrada en la base de la instalación y se **exporta cifrada** para respaldo (solo desde el propio
  equipo). Contraseña perdida = clave perdida: se genera otra y se avisa a los receptores.
- Estados: **activa** (una por empresa propia), **retirada** (sustituida sin compromiso: **se destruye la privada** en
  la base y se advierte que los respaldos anteriores aún la contienen cifrada) y **revocada** (comprometida o perdida;
  deja de verificar).
- **Separación de dominio** (RV‑16): se firma `b"silice-paquete-v1\0" + bytes(manifiesto.json)` y
  `b"silice-revocacion-v1\0" + bytes(aviso)`; una firma de un tipo nunca vale como la del otro, y una respuesta
  firmada futura (pregunta 9) tendrá su propio prefijo.

### 7.2 Huella corta legible

`huella = SHA-256(clave pública en bytes crudos)`; se muestran sus primeros **100 bits** en base32 sin caracteres
ambiguos, en cinco grupos de cuatro (`K7QF‑M9XR‑A2PT‑W4HN‑C8DV`), legibles por teléfono. Falsificarla cuesta del orden
de 2^100. La huella corta **solo** sirve para comparar por teléfono: toda búsqueda y comparación interna usa la clave
pública completa o el SHA‑256 completo. Opcional (D): un QR con la huella para compararla con la cámara del teléfono.

### 7.3 Registro de claves de otras empresas, retiro y revocación

1. La contratista exporta su **archivo de clave pública** (`.silice-clave`: JSON con nombre, RIF opcional, clave
   pública en base64, huella, fecha) y lo manda por cualquier medio.
2. El administrador lo sube; el sistema calcula la huella **él mismo** (no confía en la escrita).
3. Pantalla: «Llame a la contratista por un número que **ya conocía** (no el que viene en el correo) y pídale que lea
   la huella que muestra su Sílice. ¿Coincide con esta?» y la huella grande. El administrador marca «Coincide»,
   indica con quién habló, cómo (teléfono, en persona, QR) y la fecha. Sin esa marca la clave no se registra.
4. **Retiro ajeno:** si la contratista avisa que retiró su clave, el administrador lo registra con la fecha.
   «Verificado (retirada)» vale solo para paquetes cuyo SHA‑256 se recibió **antes** de registrar el retiro; los que
   lleguen después quedan «No verificado».
5. **Revocación propia:** el administrador revoca su clave y el sistema genera un **aviso de revocación** firmado con
   esa misma clave (con el prefijo de revocación) si todavía la tiene (si se perdió, se avisa por teléfono).
   **Revocación ajena:** importar el aviso firmado (se verifica con la clave registrada) o marcarla a mano con el
   motivo. Como la fecha de firma la declara el emisor, tras la revocación **ningún** paquete de esa clave verifica;
   los dictámenes ya emitidos conservan el estado que tenían al recibirse.

Todo JSON firmado o con huella (`manifiesto.json`, el aviso de revocación, `.silice-clave`) se lee con un
`object_pairs_hook` que **rechaza claves duplicadas**.

### 7.4 Modelo de datos

**Base de la instalación** (`seguridad/modelo.py`, Base propia, en `instalacion.db`):

| Tabla | Columnas |
|---|---|
| `usuario` | id, login (único, inmutable), nombre, huella_clave (Argon2), roles, activo, debe_cambiar_clave, restablecida_por_admin, creado, creado_por |
| `intento_acceso` | login_normalizado (PK), fallos_seguidos, bloqueado_hasta, ultimo_fallo (sirve igual para logins existentes e inexistentes) |
| `sesion` | huella_ficha (PK), usuario_id, creada, ultima_actividad, cerrada, motivo_cierre |
| `evento_acceso` | id, fecha_hora, login_intentado, usuario_id (nulo si no existe), ip_cliente, tipo (entrada, fallo, bloqueo, salida, expiración, cambio de clave, alta, baja, cambio de roles, desbloqueo, restablecimiento, firma, paquete exportado, clave de API, retiro, revocación), detalle (sin secretos; para un paquete exportado: `paquete_id`, versión y SHA‑256 del archivo) |
| `codigo_instalacion` | huella, creado, usado, motivo (primera vez o restablecimiento) |
| `empresa_propia` | id (una sola fila), nombre, rif, ciudad (opcional), actualizada, actualizada_por |
| `clave_empresa` | id, publica (bytes crudos), huella, privada_cifrada (nula al retirar o revocar), kdf (algoritmo y parámetros), sal, nonce, estado, creada, creada_por, fecha_estado, motivo |
| `empresa_registrada` | id, empresa, rif, publica, huella, estado (activa, retirada, revocada), comprobada_con, metodo, fecha_comprobacion, registrada_por, fecha_estado, motivo |
| `clave_api` | id, nombre (p. ej. «plugin de AutoCAD de la oficina técnica»), identificador público (8 caracteres, aparte del secreto), huella_secreto (SHA‑256 de un secreto de 256 bits), creada, creada_por, ultimo_uso, revocada |

**Base del caso:** `eslabon_version` (core, SL‑E7): presupuesto_id (PK, FK), proyecto_id, anterior, huella_contenido,
huella_cambios, huella_anexos, huella_eslabon, usuario, fecha_hora, tipo (`normal`, `retroactivo`), version_formato;
índice único (proyecto_id, anterior). Tablas `paq_*` (`paquete/modelo.py`, sin FK a `core/models`):
`paq_recibido` (id, archivo, huella del archivo (SHA‑256), `paquete_id`, destinatario, ruta, empresa declarada,
empresa verificada, estado, proyecto, código, fecha de emisión, cadena en JSON, huellas de las entradas de los
anexos en JSON, recibido_por, fecha) y `paq_dictamen` (paquete, huella del archivo, resultado: conforme, con
observaciones o rechazado; notas, usuario, fecha, estado de verificación al dictaminar, `revisor_armo` (sí o no,
§9 paso 5)).

---

## 8. Paquete auditado

### 8.1 Formato (`.silice`, `version_formato = 1`)

ZIP con estos nombres y ningún otro (maestro §4.5, RV‑8). La carpeta `anexos/` admite solo los nombres fijos de la
tabla, todos opcionales:

| Archivo | Contenido | Para qué | Obligatorio |
|---|---|---|---|
| `manifiesto.json` | `formato: "silice-paquete"`, `version_formato`, versión de Sílice, **`paquete_id`** (UUID4), fecha y hora de emisión, empresa y huella de su clave (o `null`), usuario emisor, **`destinatario`** (empresa o huella; opcional), proyecto, código de la versión, moneda, total declarado, **lista de archivos con SHA‑256 y tamaño**, **`huella_anexos`** (SHA‑256 del JSON canónico de [(nombre, SHA‑256)] de todo `anexos/`), última `huella_eslabon`, algoritmo `Ed25519` | lo que se firma | sí |
| `firma.ed25519` | firma de `b"silice-paquete-v1\0"` + los bytes exactos de `manifiesto.json` (ausente si se exporta sin firma) | autenticidad | no |
| `presupuesto.json` | documento canónico (§6.1), con la moneda del proyecto y el `precio_origen` de cada precio | reauditoría; el revisor regenera el Excel desde aquí | sí |
| `informe.json` | informe del emisor (hallazgos con regla, severidad, mensaje, `origen_id`) | comparar con la reauditoría | sí |
| `cadena.json` | todos los eslabones del proyecto hasta la versión entregada y los `RegistroCambio` de cada una | verificar la cadena y ver quién cambió qué | sí |
| `anexos/espacio.json` | espacio de la versión, si tiene | reauditar R8–R10 y R15 | no |
| `anexos/reajuste.json` | S1: índices usados con su fuente y la huella del archivo del BCV; estudios de reajuste | reauditar R11–R12 y el reajuste | no |
| `anexos/control.json` | S2: línea base de control y calendario, valuaciones (con su fecha de registro; sin conformación, maestro P3), anulaciones, costos reales, decisiones de recuperación | reauditar R13–R14 y el valor ganado | no |
| `anexos/ia.json` | S4: pasos y citas del asistente, sin uso de fichas, sin costo y nunca con la clave (ratificada por Eugenio el 2026‑10‑11, pregunta P4) | ver qué propuso la IA y con qué fuente | no |

- Cada entrada de `reajuste.json` y `control.json` lleva su propia huella SHA‑256; **no tienen cadena propia** (S2 ya
  es solo‑agregar en `core`): borrar una fila en la base antes de exportar no se detecta, salvo entre entregas (§6.5).
  Es un límite declarado.
- **El Excel no viaja** (DA‑S3‑10). Quien quiera el Excel del presupuesto lo genera el revisor desde `presupuesto.json`
  con `exportar_hoja` en su propia instalación.

### 8.2 Exportar (UC‑22)

Herramienta **Entregar paquete** de la barra (rol *arma*), sobre la versión abierta: verifica la cadena (22c),
muestra el resumen (total, hallazgos por severidad, cadena, empresa, anexos), pide destinatario opcional y la
contraseña de la clave (solo desde el propio equipo, §5.6) y genera el archivo en memoria; lo descarga con
`st.download_button` y registra en `evento_acceso` la firma y el SHA‑256 del archivo, para poder responder a un
revisor que alegue «Alterado». El paquete se genera **solo al pulsar**.

### 8.3 Verificar (UC‑23)

1. **Abrir con cuidado** (§8.4). 2. **Formato:** `formato` y `version_formato` conocidos (23f). 3. **Integridad:**
cada archivo que el manifiesto lista existe, su tamaño y su SHA‑256 coinciden, `huella_anexos` cuadra y no hay en el
ZIP ningún archivo admitido que el manifiesto no liste. 4. **Autenticidad:** si hay firma y la huella del manifiesto
es de una empresa registrada, se verifica con **la clave pública registrada** (nunca con una que venga en el
paquete) y con el prefijo de dominio. 5. **Cadena** de `cadena.json` y su último eslabón igual al del manifiesto y a
la `huella_contenido` de `presupuesto.json`. 6. **Anterioridad** (§6.5) y **destinatario** (23g). 7. **Banner de
versión**, siempre: «Versión 005 del 2026‑11‑10; la última que usted recibió de este proyecto: 004 del 2026‑11‑03» (o
«es la primera que recibe»; o «ya recibió este mismo paquete el …», por `paquete_id` o SHA‑256).

| Estado | Cuándo | Banner |
|---|---|---|
| **Verificado** | 1–6 bien, firma válida de empresa registrada activa; o retirada, solo si el SHA‑256 del archivo se recibió antes de registrar el retiro (con aviso) | verde: «Verificado: emitido por *Contratista Demo, C.A.* el 2026‑11‑10. No se alteró desde que se firmó.» |
| **No verificado** | sin firma, o empresa no registrada, o clave revocada, o clave retirada y paquete recibido después del retiro | ámbar: «No verificado: dice venir de *X*, pero no se pudo comprobar. Se audita igual.» Con la empresa no registrada, botón «Registrar su clave» (lleva a Administración) |
| **Alterado** | una huella no coincide, falta un archivo que el manifiesto lista, hay un archivo admitido que no lista, la firma está vacía, truncada o no es válida con la clave registrada, o la cadena no cuadra | rojo: «Alterado: *presupuesto.json* cambió después de firmarse. No confíe en este paquete; pida uno nuevo.» Se audita igual para mostrar qué contiene |
| **Rechazado** | ZIP dañado, inseguro, fuera de límites o de formato desconocido | mensaje con el motivo y qué hacer; no se audita (no hay qué leer) |

Sin firma, las huellas solo prueban que el archivo no se dañó por accidente: cualquiera que lo cambie puede
recalcularlas. El banner ámbar lo dice con esas palabras. El nombre que «dice venir de» se muestra con
`texto_seguro()`.

### 8.4 Abrir un ZIP y un JSON ajenos sin riesgo

Se lee con `zipfile` en memoria, sin extraer al disco, y **sin confiar en los tamaños de las cabeceras**: cada
entrada se lee con tope (`read(limite + 1)`) contando los bytes reales. Límites como constantes con
`SUPUESTO_DECLARADO` hasta medir paquetes reales; cada uno con su frontera exacta (pasa / se rechaza):

| Límite | Pasa | Se rechaza |
|---|---|---|
| tamaño del archivo `.silice` | 20 MiB (20 971 520 B) | 20 971 521 B |
| contenido descomprimido por entrada | 50 MiB (52 428 800 B) | 52 428 801 B |
| contenido descomprimido en total | 100 MiB (104 857 600 B) | 104 857 601 B |
| relación de compresión por entrada (descomprimido ≤ 100 × comprimido, en enteros) | 100:1 | 101:1 |
| renglones del presupuesto más líneas de composición en `presupuesto.json` | 200 000 | 200 001 |
| anidamiento de cualquier JSON | 64 niveles | 65 (o `RecursionError`, capturado) |
| ambientes, puntos y vértices de `anexos/espacio.json` (antes de R15 con `shapely`) | 5 000 ambientes, 50 000 puntos, 1 000 vértices por polígono | uno más en cualquiera |
| tiempo de la reauditoría | 60 s | se corta y se informa «no terminó» |

Se rechaza además: entrada con nombre fuera de la lista de §8.1; nombre repetido (un ZIP admite dos entradas con el
mismo nombre); ruta absoluta, con `..` o con barra invertida; entrada cifrada; método de compresión que no sea
almacenado o *deflate*. El **lector JSON estricto** (`paquete/formato.py`, también para la API) rechaza `NaN`,
`Infinity` y `-Infinity` (`parse_constant`), claves duplicadas (`object_pairs_hook`) y toda cifra que no cumpla el
patrón estricto **antes** de pasarla a `Decimal` (p. ej. `1E+999999999`; patrón exacto fijado en S3‑0, del estilo
`^-?\d{1,15}(\.\d{1,12})?$`).

---

## 9. Vista del administrador que revisa (UC‑23)

**Pantalla «Revisar un paquete»** (`ui/paginas/revisar.py`, sección Revisión). Pasos en el orden del trabajo:

1. **Subir** el `.silice` o un Excel UC‑05 (23d), con `ui.subidas.guardar_subida`. Del Excel ajeno se leen
   **valores**, nunca fórmulas ni vínculos externos.
2. **Estado de verificación** (§8.3), siempre visible arriba, con el banner de versión, la huella del emisor y la
   cadena.
3. **Reauditoría propia.** `core.budget.canonico.leer` → el motor recalcula cada precio unitario desde las
   composiciones y parámetros del paquete (no se confía en los precios ni en los totales escritos) → `auditar` con
   `REGLAS` y las reglas externas del contexto «reauditoría» (§3.4, maestro §3.3): R8–R10 y R15 con el anexo de
   espacio; R11–R12 con el `precio_origen` y el anexo de reajuste, contra la referencia MaPreX del revisor y **a la
   fecha de emisión del paquete**; R13–R14 con el anexo de control. Todo en memoria. Tres listas: hallazgos **que el
   emisor no declaró**, **que declaró y ya no aparecen**, y comunes. Un precio unitario o total declarado que no
   cuadra con el recálculo es una diferencia con su monto.
4. **Diferencia entre versiones y su costo** (`core.budget.comparacion`, SL‑E9), con un control para elegir contra
   qué:
   - **la entrega anterior** del mismo proyecto (paquete ya recibido);
   - **la base de precios del revisor** (lista de su empresa, S1): el presupuesto del paquete revalorado **en
     memoria** con sus precios por `comparacion.revalorar` (en `core`, SL‑E9, ARQ‑H4), emparejando insumos por
     **referencia de precio** (Ref MaPreX) o por código; lo que no empareja es **«no contrastable»**, se lista y no
     suma.

   Por partida: Δ total = **(q₂ − q₁) × PU₁** (desvío por cantidad) **+ (PU₂ − PU₁) × q₂** (desvío por precio): el
   término cruzado queda en el precio. Las dos columnas suman exacto el Δ total (`Decimal`). Una partida que solo
   está en una versión es desvío por cantidad entero (nueva: q₁ = 0 y PU₁ := PU₂; eliminada: q₂ = 0). Ordenado por
   |Δ|, con la suma arriba (ejemplo: «La entrega 005 cuesta 1 240,50 USD más que la 004: 980,00 por cantidades y
   260,50 por precios»). Esta **diferencia entre versiones** es distinta de la **separación del desvío de control**
   de S2 (término cruzado en el consumo, precio = (PU_real − PU_base) · Q_base; RV‑10): cada una tiene su nombre y su
   memoria, y S2 no reutiliza SL‑E9.
5. **Quién cambió qué**: los `RegistroCambio` entre la entrega anterior y esta, con responsable y fuente (los
   hechos tras un restablecimiento del administrador, marcados). **Quien revisa es quien armó** (maestro §4.1, P2):
   si el paquete es de la empresa propia (firmado con su clave, o sin firma y con la empresa propia declarada) y
   el login de quien revisa es el del usuario emisor o el del `usuario` de algún eslabón de `cadena.json`, un aviso
   ámbar fijo arriba dice «Usted armó o cambió este presupuesto: lo está revisando la misma persona que lo armó»,
   con las versiones en que aparece; no impide el dictamen.
6. **Dictamen**: conforme, con observaciones o rechazado, con notas obligatorias salvo «conforme»; se guarda en
   `paq_dictamen` atado al **SHA‑256 del archivo**, con el estado de verificación de ese momento, quién revisó y
   `revisor_armo`. **Exportar la
   revisión** a Excel (hojas Verificación, Hallazgos, Diferencias, Cambios) y **Descargar el presupuesto en Excel**
   (regenerado desde `presupuesto.json` con `exportar_hoja`), los dos con el escape de M‑1.

Pasos con `st.segmented_control`; la verificación en `st.session_state` con clave propia (no se repite en cada
interacción); los Excel solo al pulsar. Todo texto que viene del paquete pasa por `texto_seguro()`.

---

## 10. APU de otras herramientas

- **Excel (UC‑05):** el formato de `core/budget/importacion.py`, con **plantilla descargable** (cinco hojas y una fila
  de ejemplo); se lee con `leer_presupuesto_tabular` (solo valores) y se audita en memoria (DA‑S3‑7); errores con
  archivo, hoja y fila, como hoy. Sin cadena ni firma: siempre «no verificado».
- **API para plugins:** `POST /v1/auditorias`, cuerpo = documento canónico (§6.1), `fecha_evaluacion` y, opcional, el
  anexo de espacio; se lee con el lector JSON estricto de §8.4. Cabecera con la clave de API (nombre a fijar en S3‑0,
  p. ej. `X-Silice-Clave: <identificador>.<secreto>`): el identificador público de 8 caracteres es aparte y el
  secreto conserva sus 256 bits (SEG‑15). No guarda nada. Respuesta: informe, totales recalculados, diferencias entre
  lo declarado y lo recalculado y la fecha de evaluación usada; montos como texto (convención de la API). Sin clave,
  clave desconocida o revocada: **401** con `{"detalle": ...}` y `evento_acceso`. Las claves las crea el
  administrador, solo desde el propio equipo; se muestran **una sola vez** y se guarda el SHA‑256 del secreto.
- **Defensas de la API:** un middleware corta el cuerpo en 20 MiB (413) sin leerlo entero (FastAPI y Uvicorn no lo
  limitan); `TrustedHostMiddleware` contra el *DNS rebinding*; la reauditoría tiene el tope de tiempo de §8.4. La API
  sigue apagada por defecto y, si se activa, escucha en la IP explícita de la red local (S5, §5.6); en 0.8.0 la clave
  se exige en las rutas `/v1/`, y S5 decide extenderla a las rutas antiguas. Esquema publicado en `docs/api.json`.

---

## 11. Auditoría de planos (horizonte §5.1)

### 11.1 Archivo DXF dañado

La importación pasa de `ezdxf.readfile` a la **lectura con recuperación** de `ezdxf` (módulo de recuperación, que
devuelve el documento y un auditor con errores y arreglos) y, sobre el documento, a su **auditoría**. **API exacta: a
confirmar en S3‑0.** Errores que la biblioteca arregla → ítems ADVERTENCIA del informe de importación («el plano
tenía 3 errores de estructura que se repararon: …»); irrecuperables → rechazo con mensaje (UC‑14d). Los nombres de
capas y bloques de un plano ajeno se muestran con `texto_seguro()`.

### 11.2 IFC con requisitos mínimos (IDS)

`data/ids/silice_instalaciones.ids` declara, en el estándar IDS de buildingSMART, lo mínimo que la hoja necesita:
espacio con altura, aparato sanitario con diámetro, tomacorriente con circuito, tablero con nombre. Las clases y
propiedades exactas salen de las clases IFC fijadas en SF0 y se versionan **antes** del código. `ifctester` (extra
`civil` o `ifc`, importación diferida) abre el IDS, valida el modelo y entrega por requisito los elementos que fallan
(**API a confirmar en S3‑0**). Cada fallo es un ítem del informe de importación con su `GlobalId`; lo que falte sigue
pendiente y R8 lo marca. Sin el extra instalado, la importación del IFC sigue funcionando y el informe dice «IDS no
comprobado: falta el módulo IFC».

### 11.3 R15 Coherencia geométrica del plano (`shapely`)

`ReglaVerificacion` de `adapters/espacio`, construida con la instantánea del espacio como R8–R10 (DA‑SF‑8).
Detecta, con índice espacial; toda medida informada sale de las coordenadas `Decimal` (DA‑S3‑6). **La severidad es
la de la tabla, por condición, y no cambia:** las dos primeras filas usan tolerancias geométricas del sistema (no
supuestos sobre la obra) y son ERROR; las dos últimas dependen de umbrales supuestos y por eso son ADVERTENCIA desde
el diseño, como R10 (RS‑11).

| Condición | Severidad | Pasa (sin hallazgo) | Falla |
|---|---|---|---|
| dos ambientes se superponen en más de 0,01 m² | ERROR | 0,0100 m² | 0,0101 m² |
| dos puntos de la misma especialidad y tipo a menos de 0,001 m (duplicados) | ERROR | 0,0010 m | 0,0009 m |
| escala imposible: lado de ambiente < 0,30 m o > 200 m | ADVERTENCIA | 0,300 m y 200,000 m | 0,299 m y 200,001 m |
| escala imposible: altura < 2,00 m o > 12 m | ADVERTENCIA | 2,000 m y 12,000 m | 1,999 m y 12,001 m |
| punto a más de 100 m de su fuente | ADVERTENCIA | 100,000 m | 100,001 m |

Los umbrales de escala y distancia son `SUPUESTO_DECLARADO` (fuentes candidatas a verificar en S3‑0). R15 no repite
R9 (punto fuera de su ambiente, recorridos imposibles): una prueba comprueba que ningún error sembrado da hallazgos
de R9 y R15 a la vez.

### 11.4 R16 Contraste entre dos fuentes

`ReglaContraste(espacio_referencia)`: compara el espacio de la versión con otro (plano contra levantamiento, plano
nuevo contra anterior). Empareja ambientes, fuentes y puntos por especialidad, tipo y posición (vecino más cercano),
con dos distancias `SUPUESTO_DECLARADO`:

| Distancia al vecino más cercano de la otra fuente | Resultado | Frontera |
|---|---|---|
| ≤ 0,10 m (tolerancia) | emparejado, sin hallazgo | 0,10 m emparejado / 0,11 m desplazado |
| > 0,10 m y ≤ 1,00 m (radio de búsqueda) | **desplazado** | 1,00 m desplazado / 1,01 m faltante y sobrante |
| > 1,00 m o sin vecino | **faltante** en una fuente y **sobrante** en la otra | — |

El costo: la interfaz deriva los ítems de las dos fuentes, los valora con las mismas composiciones y llama a
`core.budget.comparacion` (SL‑E9), por ejemplo «el plano tiene 2 puntos de datos menos que el levantamiento: −186,40
USD». El costo de faltantes, sobrantes y desplazados tiene su oráculo a mano en `diferencias_s3.md` (§13.1). Es la
única forma de ver un plano «coherente pero equivocado» (H‑D9). La segunda fuente se carga desde la hoja («Contrastar
con otro plano o levantamiento»): otro DXF/IFC u otra versión.

### 11.5 Evaluación por errores sembrados

- **Catálogo de errores** (`tests/fixtures/errores_planos/catalogo.md`), escrito **antes** de R15 y R16 y por
  categoría: sin `$INSUNITS`; entidad dañada; bloque en capa equivocada; `ALTURA` faltante; escala ×1000; ambiente
  superpuesto; punto duplicado; punto fuera de todo ambiente; punto sin fuente; `IfcSpace` sin altura; aparato sin
  diámetro; tomacorriente sin circuito; elemento borrado entre dos fuentes; punto desplazado 0,50 m entre dos
  fuentes. Cada uno con la detección esperada (regla o ítem del informe, severidad, fila) y **controles no
  detectables** (un plano coherente pero equivocado sin segunda fuente), que deben dar «no detectado» y miden el
  límite declarado. **Una parte del catálogo la escribe alguien que no programa las reglas** (el ingeniero de pruebas
  o el tutor), sin ver la implementación (§13.5 b).
- **Sembrador determinista** (`scripts/sembrar_errores_planos.py`, semilla fija) sobre el DXF y el IFC de OF‑001,
  uno y varios errores por archivo, con su lista. **Medición** (`scripts/medir_deteccion_planos.py`): tasa de
  detección = detectados / sembrados detectables, por categoría; falsas alarmas = hallazgos fuera del conjunto exacto
  esperado. Protocolo en §13.5 b, versionado antes de medir; meta 100 % en lo detectable y cero falsas alarmas sobre
  OF‑001 limpio (ratificada por Eugenio el 2026‑10‑11, pregunta P8 del maestro §10.3).
- **Conjunto exacto de OF‑001 limpio.** No se pudo fijar leyendo el código en esta revisión: R15 y R16 todavía no
  existen. Lo que se sabe: las **33 ADVERTENCIAS de R8** por constantes supuestas (las que cita S4) y, sin segunda
  fuente, R16 no corre. **S3‑0 escribe el conjunto como literal** (regla, severidad y `origen_ids` de cada hallazgo de
  R8, R9, R10 y R15), recontando las de R8 con el código de la 0.7.0 y antes del código de R15. La expectativa de
  diseño es que R15 no agregue nada sobre OF‑001 limpio; si agrega, S3‑0 decide si es un error del plano o un umbral
  mal puesto y registra el ruling.

### 11.6 IfcClash (D, fuera de RF‑89)

Solo si el IFC trae estructura; detecta choques tubo‑elemento. No tiene número propio ni entra en la meta de §11.5. Es
lo primero en caer (§14).

---

## 12. Amenazas: qué protege y qué no

| Amenaza | ¿Protege? | Cómo, o por qué no |
|---|---|---|
| Alguien cambia el paquete en el camino (correo, WhatsApp, USB) | **sí** | huellas del manifiesto + `huella_anexos` + firma: «Alterado» |
| Alguien fabrica un paquete a nombre de una contratista registrada | **sí**, salvo que tenga su clave privada y su contraseña | la firma se verifica con la clave **registrada**, no con la que trae el paquete |
| Alguien sustituye la clave de la contratista al registrarla (correo falso) | **sí, si** se comprueba la huella por un canal ya conocido | paso 3 de §7.3; si el administrador marca «coincide» sin llamar, no |
| Alguien con la **clave privada y su contraseña** | **no** | firma lo que quiera como esa empresa. Mitigación: contraseña propia, revocación, aviso a receptores |
| Alguien con el archivo de la clave cifrada (base o respaldo) y una contraseña débil | **parcial** | Argon2id con m ≥ 64 MiB frena el ataque por diccionario sin conexión, no lo impide; mínimo de 12 caracteres y lista de comunes |
| Una clave **retirada** usada para firmar después del retiro | **sí**, del lado del receptor | la privada se destruye al retirar (los respaldos viejos la conservan cifrada: se advierte); «Verificado (retirada)» solo para paquetes recibidos antes del retiro |
| Reescribir la historia **dentro** de la base (con acceso al archivo SQLite) | **no** dentro de la base; **sí** entre entregas | la cadena no lleva secreto: quien tiene el archivo puede recalcularla entera. El revisor lo detecta si ya recibió un paquete anterior (§6.5) |
| Borrar una valuación, un costo real o un estudio antes de exportar | **no** dentro de la base; **parcial** entre entregas | las entradas de S1 y S2 viajan con huella sin cadena propia; el revisor avisa si falta una que ya recibió |
| Reenviar un paquete viejo como si fuera nuevo | **parcial** | solo se detecta si ese revisor ya recibió uno más nuevo del mismo proyecto y emisor; un revisor nuevo, otro revisor o una base restaurada lo aceptan. Mitigación: `paquete_id`, `destinatario` y el banner «versión N del …; la última que usted recibió: …» |
| Usar la firma de un aviso de revocación como firma de un paquete (o al revés) | **sí** | separación de dominio (§7.1) |
| JSON firmado con claves duplicadas que dos lectores interpretan distinto | **sí** | lector estricto que las rechaza (§8.4) |
| Fecha de emisión falsa | **no** | la fecha la declara el emisor; no hay sellado de tiempo de un tercero (exige internet). Por eso la revocación invalida todos los paquetes de esa clave |
| Un presupuesto firmado pero **equivocado o engañoso** | **no** | la firma prueba quién y que no cambió, no que sea verdad; para eso está la reauditoría, que solo encuentra inconsistencias |
| **Revisor malicioso** | **no** | el dictamen no va firmado y el revisor puede editar sus `paq_*`. Mitigación: el emisor guarda el SHA‑256 de cada paquete exportado y puede mostrar qué entregó; la respuesta firmada queda fuera (pregunta 9) |
| **Empleado deshonesto** que conoce la contraseña compartida de la clave | **no** | no hay no repudio individual: «usuario emisor» es solo lo que declara el emisor (maestro §4.1). Mitigación: pocas personas con la contraseña; registro de cada firma en `evento_acceso` |
| **Administrador** que restablece la contraseña de otro y actúa en su nombre | **parcial** | el restablecimiento queda en `evento_acceso` y los cambios hechos antes de que la persona cambie su contraseña se marcan en la trazabilidad (§5.2) |
| **Archivo malicioso** más allá del ZIP: Excel externo, Markdown, analizadores en C++ de DXF e IFC | **parcial** | el Excel no viaja en el paquete; del Excel UC‑05 se leen solo valores; todo texto ajeno por `texto_seguro()` (una imagen Markdown no hace peticiones); límites de tamaño y tiempo. Un fallo de memoria en los analizadores en C++ de `ezdxf`/`ifcopenshell` queda fuera: se declara |
| ZIP malicioso (rutas `..`, bomba de compresión, nombres repetidos, entradas cifradas, tamaños de cabecera falsos) | **sí** | §8.4, lectura con tope, sin extraer al disco |
| Robo de la base de la instalación | **parcial** | contraseñas con Argon2 (costosas de romper), fichas y secretos de API como huellas; la privada sigue cifrada con Argon2id |
| Adivinar contraseñas por la pantalla de acceso | **sí** | bloqueo por login (también inexistentes), freno global con espera progresiva, tiempo constante con usuarios inexistentes |
| Bloquear a propósito las cuentas de otros | **no** (es el precio del bloqueo) | el administrador desbloquea; el script de restablecimiento si es el administrador |
| **Atacante en la red local**: escuchar contraseñas, la contraseña de la clave, contraseñas temporales o claves de API | **parcial** en 0.8.0 | sin TLS (S5 decide) las contraseñas de cuenta viajan legibles; las operaciones con secretos de la empresa solo se hacen desde el propio equipo; aviso en la pantalla de acceso; solo en una red de confianza (§5.6). Si Streamlit permite reanudar una sesión por su identificador, también podría tomarla (§5.3, 6) |
| Atacante en la red local: *DNS rebinding*, websockets entre sitios | **sí**, a confirmar | `TrustedHostMiddleware`, `browser.serverAddress` fijo, CORS y XSRF explícitos (§5.6); se prueba en S3‑4 |
| Túnel o proxy local que publica Sílice | **no** | todo llega como `127.0.0.1` y anula el filtro de IP; el control real es la sesión y la clave (§5.6) |
| **IA manipulada** (texto inyectado en planos, listas o respuestas del modelo) | **parcial** | lo trata S4; en S3, la salida del modelo y `anexos/ia.json` son texto ajeno (`texto_seguro()`) y la IA no tiene campos de precio ni de total |
| Quien administra el equipo (Windows) o un programa malicioso en él | **no** | puede cambiar la base de la instalación y las claves registradas, o capturar contraseñas: el sistema confía en el equipo local |
| Plugin con una clave de API robada | **parcial** | la ruta no escribe nada; revocación inmediata; `ultimo_uso` a la vista |
| Sesión abierta en un equipo ajeno | **parcial** | expiración por inactividad y por antigüedad; «Cerrar sesión» |

Nada de esto programa criptografía propia: todo es de `cryptography`, `argon2-cffi`, `hashlib` y `secrets` (maestro
§4.4). Restaurar un respaldo que revive claves o cuentas ya revocadas lo trata S5 (lista de eventos de seguridad
perdidos, RV‑16), con su propia tabla de amenazas.

---

## 13. Pruebas y calidad (IEEE 829, ISO/IEC 25010)

Pruebas antes que código con **el rojo observado** (commit de prueba antes que el de implementación) en SL‑E7,
SL‑E8, SL‑E9, SL‑E12, `seguridad`, `paquete`, R15 y R16. Cero omitidas; `-W error`; Linux y Windows. Una sola guardia
de red en `tests/conftest.py` (maestro §6.3).

### 13.1 Oráculos independientes

- **Memoria de diferencias** (`tests/fixtures/memorias/diferencias_s3.md`), **antes** de SL‑E9: dos versiones de un
  presupuesto pequeño, con Δ cantidad, Δ precio y Δ total por partida **hechos a mano**, incluida la frontera de una
  partida que solo está en una de las dos versiones (nueva y eliminada); la revaloración con una lista del revisor
  con un insumo «no contrastable»; y el **costo de R16** (un faltante, un sobrante y un desplazado de un espacio
  pequeño, valorados a mano con las composiciones de la memoria).
- **Vector de huella:** el documento canónico de ejemplo (`tests/fixtures/canonico/ejemplo_v1.json`) se **escribe a
  mano**, con claves ordenadas y `Decimal` como texto, no se genera con `documento()` para congelarlo después; su
  SHA‑256 se calcula aparte (`sha256sum` sobre el archivo versionado) y se escribe como literal. La prueba comprueba
  que `documento()` de la versión sembrada da esos bytes y que su huella es ese literal.
- **Firma:** los vectores de prueba de Ed25519 del RFC 8032 (sección 7.1) comprueban que se usa la biblioteca bien.
- **Planos:** el catálogo de §11.5 con la detección esperada y el conjunto exacto de OF‑001 limpio, antes del código
  de R15 y R16.
- **Reauditoría con anexos:** una memoria del paquete de prueba con el conjunto exacto de R11–R14 recomputadas a la
  fecha de emisión, reutilizando los oráculos de S1 y S2.

### 13.2 Matriz

| RF / RNF | Prueba |
|---|---|
| RF‑80 | código de instalación válido, usado, ausente y aceptado solo sin usuarios o con restablecimiento pendiente; su longitud (20 caracteres base32); alta con roles; cada fila de la matriz de §5.1 con un rol ajeno, por URL y por la función de `ui/` → rechazo; ninguna contraseña en la base (búsqueda del texto plano en el archivo SQLite) ni en `evento_acceso` |
| RF‑81 | expiración 29:59 / 30:00 y 11:59:59 / 12:00:00 con reloj inyectado; 4 y 5 fallos con un login existente y con uno inexistente (mismo mensaje); desbloqueo tras 15 min; freno global (20 fallos, espera 1, 2, 4… s); ficha distinta tras entrar y tras cambiar la contraseña; restablecer, desactivar y cambiar roles cierran las sesiones; roles cambiados en la base cambian el menú; un **espía** comprueba que con un usuario inexistente se verifica contra la huella de relleno (no se miden tiempos); semáforo de Argon2; cerrar sesión; **sesión expirada** en AppTest muestra el acceso y conserva el borrador del mismo usuario; usuario distinto lo descarta |
| RF‑82 | la lista de toda columna `responsable` de los metadatos, cada una con su prueba de que la escribe el usuario de la sesión; búsqueda de `"sistema"` en `ui/` |
| RF‑83 | recorrido de **todo** `MOTIVOS_VERSION` y del motivo vacío; enumeración de **todos** los llamadores del embudo, con `usuario=` fuera de `tests/`; confirmar sin usuario se rechaza; un byte cambiado en partida, registro, anexo y eslabón → fallo en esa versión; versión sin sellar; sellado retroactivo declarado; guardar y recargar no cambia la huella; vector de huella |
| SL‑E12 | concurrencia de §13.4 |
| RF‑84 | generar, cifrar, cargar con contraseña buena y **errónea** (`InvalidTag`, mensaje sin traza); contraseña de la lista de comunes rechazada; huella igual en dos bases; búsqueda interna por clave completa (dos claves con los mismos 100 bits iniciales, construidas en la prueba, no se confunden); retirar destruye la privada; revocar; aviso de revocación firmado, uno con firma falsa y uno firmado con el prefijo de paquete (no vale) |
| RF‑85, RF‑86 | ida y vuelta entre dos bases temporales con los cuatro anexos; SHA‑256 del exportado en `evento_acceso`; firma pedida con una IP que no es de bucle local → rechazo; todos los casos de §13.3 |
| RF‑87 | memoria de diferencias; «no contrastable»; reauditoría que encuentra un hallazgo no declarado; R11–R14 recomputadas = conjunto exacto; R12 a la fecha de emisión (el mismo paquete reauditado otro día da lo mismo); `revalorar` en `core` con su prueba; Excel regenerado sin el Excel del emisor; dictamen con SHA‑256 y estado; **quien revisa es quien armó**: con un paquete de la empresa propia, revisor = usuario emisor → aviso y `revisor_armo` = sí; revisor = `usuario` de un eslabón anterior → aviso; otro revisor → sin aviso; paquete de una empresa ajena con un login igual → sin aviso |
| RF‑88 | plantilla descargada → auditada; Excel con partidas del catálogo sin rechazo; Excel con una fórmula `HYPERLINK` → se lee su valor, nunca la fórmula; API sin clave, con clave revocada y con clave válida (`TestClient`); toda ruta `/v1/` exige la clave (recorriendo `app.routes`); cuerpo de 20 MiB y de 20 MiB + 1 B; `Host` ajeno → rechazo; `NaN` y cifra `1E+999999999` → 422 |
| RF‑89 | auditoría DXF de un archivo dañado a propósito; IDS con un fallo por requisito; cada fila de R15 con sus fronteras (§11.3); R16 con 0,10 / 0,11 m y 1,00 / 1,01 m, faltante, sobrante y desplazado con su costo de la memoria; ningún error sembrado da R9 y R15 a la vez; OF‑001 limpio = conjunto exacto literal; IFC sin el extra instalado |
| RF‑100 (D) | oráculo a mano en `tests/fixtures/memorias/atipicos_s3.md`: serie de 10 precios fechados con un atípico sembrado → conjunto exacto `{ese punto}` en ADVERTENCIA; serie de 10 sin atípico → vacío; 8 precios → abstención; conversión a USD con la tasa de cada precio (dos precios en Bs con tasas distintas dan la variación en USD de la memoria); ningún hallazgo ERROR; sin el extra `ml` → sin hallazgo |
| RNF‑16 | §13.3 y §13.4; ningún secreto en registros (prueba que captura la salida y el registro de accesos) |
| Arquitectura | `test_arquitectura_s3.py`: importaciones de `seguridad`, `paquete`, `ui/acceso.py`, `ui/entrega.py`, `ui/revision.py`, `ui/texto_seguro.py`; `PAQUETES_FUERA_DEL_NUCLEO`; caché por usuario; ningún `unsafe_allow_html` |
| Interfaz | AppTest de arranque con y sin sesión; acceso (con el aviso de conexión sin cifrar cuando el cliente es remoto), primer administrador, cambio de contraseña; navegación por rol y modo entrega (RF‑43); recorridos de UC‑12 por rol; Administración; Revisar con un paquete de prueba en `st.file_uploader` (a confirmar que AppTest lo admite; si no, se prueba `ui.revision` sin Streamlit y la subida a mano); un nombre de empresa con una imagen Markdown hacia `127.0.0.1:9` deja el proxy testigo en 0 peticiones |

### 13.3 Pruebas de seguridad del paquete (estado esperado)

| Caso | Estado |
|---|---|
| paquete íntegro, firmado, empresa registrada, con los cuatro anexos | Verificado |
| firmado con una clave **retirada**, recibido antes de registrar el retiro | Verificado (retirada), con aviso |
| firmado con una clave retirada, recibido después del retiro | No verificado |
| un byte cambiado en `presupuesto.json` sin tocar el manifiesto | Alterado (huella) |
| un byte cambiado en `anexos/control.json` | Alterado (huella y `huella_anexos`) |
| `presupuesto.json` cambiado y manifiesto con la huella nueva, firma vieja | Alterado (firma) |
| `firma.ed25519` vacía (0 bytes) o truncada (63 bytes) | Alterado (firma no válida) |
| firma de un aviso de revocación puesta como firma del paquete | Alterado (firma no válida: otro dominio) |
| manifiesto que lista un archivo ausente | Alterado (integridad) |
| archivo admitido presente en el ZIP que el manifiesto no lista | Alterado (integridad) |
| manifiesto con una clave JSON duplicada | Rechazado |
| todo re‑firmado con otra clave que dice ser de la empresa registrada | Alterado (firma no válida con la clave registrada) |
| todo re‑firmado con una clave no registrada y otro nombre | No verificado; el nombre se muestra «dice venir de» con `texto_seguro()` |
| sin `firma.ed25519` | No verificado |
| clave revocada | No verificado (revocada) |
| nombre fuera de la lista; nombre repetido; `../x`; ruta absoluta; entrada cifrada; método de compresión no admitido; formato 2 | Rechazado |
| cada límite de §8.4 en su frontera (pasa) y una unidad más (Rechazado), con tamaños de cabecera falsos que mienten por debajo | según la tabla de §8.4 |
| `NaN`, `Infinity`, cifra fuera del patrón, anidamiento de 65 niveles | Rechazado |
| cadena del paquete que no extiende la del último recibido | aviso 23c |
| paquete anterior a uno ya recibido; el mismo paquete otra vez | aviso de anterioridad; «ya recibió este paquete» |
| destinatario de otra empresa | aviso 23g |
| contraseña de la clave errónea al exportar | mensaje, ningún archivo |

### 13.4 Varios usuarios a la vez

- **Automática (SL‑E12, PRU‑H20):** tres hilos, sincronizados con `threading.Barrier`, con sesiones de la base de la
  instalación y de un caso temporal, hacen cada uno **N guardados fijos** (N = 10) del mismo proyecto. Lo esperado:
  exactamente 3 × N versiones y sus `RegistroCambio`, ninguno perdido; la cadena queda lineal y verificable; ningún
  `database is locked`. Sin tiempos de espera fijos en la prueba. Dos `AppTest` con usuarios distintos en el mismo
  proceso no comparten estado.
- **Manual, en la red local** (procedimiento fijado antes, en la bitácora): un servidor y dos clientes; tres personas
  (arma, arma, revisa), 15 min: entran, editan, guardan, una deja expirar la sesión, se entrega y se revisa un
  paquete. Metas: 0 ediciones perdidas, 0 trazas; el número de usuarios probados se declara como límite (maestro §8).

### 13.5 Protocolos de medición de quien revisa y de planos (dueño: S3‑0, RV‑20)

Los dos se escriben en S3‑0 y se versionan con su huella SHA‑256 **antes de Med** (maestro §7):

- **(a) Indicador del administrador** (horizonte §6.1). Dos condiciones con el mismo presupuesto y una lista
  **congelada** (con huella) de diferencias sembradas: revisarlo **a mano** (con el Excel) y **con el sistema**. Dos
  métricas: tasa de detección y falsas alarmas, más el tiempo. Fija el número de participantes y su criterio de
  selección, el orden contrabalanceado de las condiciones, el sesgo del autor como facilitador y las amenazas a la
  validez. CP‑R1 es la condición «con el sistema»; RNF‑17 (b) se mide en esa misma sesión.
- **(b) Tasa de detección en planos** (§11.5). Fija n por categoría, la semilla, las combinaciones de errores (cuáles
  se siembran juntos y cómo se tratan los que se enmascaran), la parte del catálogo escrita por quien no programa las
  reglas sin ver la implementación, los «no detectables» informados con su número, y las amenazas: validez de
  constructo (errores sintéticos) y externa (un solo caso, OF‑001). Meta: 100 % de lo detectable y 0 falsas alarmas
  (ratificada por Eugenio el 2026‑10‑11, pregunta P8 del maestro §10.3).

**Casos con personas (Med):** CP‑R1 (revisar un paquete con diferencias sembradas, dentro del protocolo a) y CP‑R2
(registrar una clave comprobando su huella), casos IEEE 829 del guion; RNF‑17 fija consigna, paradas y criterio antes
de medir.

### 13.6 Meta y regresión

- **Meta:** `scripts/meta_silice.py --version 0.8.0 --hasta S3‑n` (maestro §6.3), con las siete comprobaciones
  comunes (presencia de los números de la ERS de S3, cero omitidas, prueba antes que implementación, `git diff` vacío
  en `core/contracts/`, `git diff v0.5.0..HEAD` vacío sobre las pruebas de regresión, pruebas de tiempo con su cifra,
  guardia de red activa) y las propias de S3: huella de los dos protocolos de §13.5 presente antes de Med; conjunto
  exacto de OF‑001 limpio presente; ningún `unsafe_allow_html`; las ramas de S3‑5 y S3‑6 no tocan `core/`. RF‑100 solo
  se exige con `--hasta S3‑6` (si la fase cae, la meta de la 0.8.0 se cierra en S3‑5 y RF‑100 se declara no
  construido).
- **Regresión en cada compuerta (no se editan):** cinco APU a ± 0,01; 7 de 7; R4 de 3/4 pulg
  (`test_r4_marca_3_4_pulg_y_no_marca_pvc`); TI‑001 total, PU y punto de equilibrio 28 586,76 USD en el Día 6; las
  dos huellas de RNF‑04; las cuatro hojas de `exportar_excel`. Además, todo AppTest de UC‑12. Si un cambio de S3
  moviera alguna, se registra un ruling de reanclaje; nunca se edita la prueba.
- Cobertura ≥ 80 % en `seguridad/` y `paquete/`, en la CI.

---

## 14. Tareas por fase

Ramas cortas por fase desde el `main` del momento, PR contra `main`, fusión al cruzar la compuerta de la fase (RV‑2).
Lo inconcluso queda fuera de la navegación o detrás de una opción de configuración, así `main` siempre se puede
publicar.

| Fase | Contenido | Rol | Compuerta | Base de la rama |
|---|---|---|---|---|
| **S3‑0** | ERS (UC‑21 a UC‑23 con flujo principal y postcondiciones, RF‑80 a RF‑89 y RF‑100 (D), RNF‑16, RNF‑17, actores y su mapa a los roles, **enmienda única de RNF‑08**), arquitectura, modelo de datos y plan de pruebas enmendados; licencias (en el PR «dependencias Sílice»); API exacta de `argon2-cffi`, `cryptography`, `ezdxf` (recuperación), `ifctester`, `st.context.ip_address`, reanudación de sesiones de Streamlit y `BEGIN IMMEDIATE` con SQLAlchemy; patrón de cifras del lector JSON; nombre de la cabecera de la API y `fecha_evaluacion`; IDS; catálogo de errores (con la parte de quien no programa las reglas); memorias (`diferencias_s3.md` con el costo de R16, vector de huella a mano, reauditoría con anexos); **conjunto exacto de OF‑001 limpio como literal**; los dos protocolos de §13.5 con su huella; comprobaciones de S3 en `meta_silice.py` | líder, interfaz, adaptadores, pruebas | GS3‑0 | `main` (0.7.0) |
| **S3‑1** | `seguridad` (cuentas, sesiones, bloqueo y freno global, código de instalación, registro de accesos, `secretos.py`, `red.py`, empresa propia); `ui/acceso.py`; `ui/texto_seguro.py` (y su aplicación a lo existente); reglas de red local de §5.6; navegación y matriz por rol; RF‑82 en la hoja | interfaz | GS3‑1 | sin núcleo: puede adelantarse desde `main`; si se fusiona antes de la 0.7.0, queda detrás de una opción apagada hasta la 0.8.0 y la parte de RF‑82 y de la matriz que toca pantallas de S1 y S2 se cierra en S3‑3 |
| **S3‑2** | Núcleo, **único carril de núcleo abierto**, después de cerrar S2‑3: SL‑E8, SL‑E7 (en el embudo), SL‑E9 (diferencia entre versiones y `revalorar`), SL‑E12, con expediente y rojo observado | núcleo | GS3‑2 | `main` con S2 fusionada |
| **S3‑3** | `seguridad.firma`, `seguridad.empresas` (retiro, revocación); `paquete` (formato v1 con anexos, lector estricto, exportar, verificar); Entregar paquete; Administración; RF‑82 en las pantallas de S1 y S2 si faltaba | interfaz | GS3‑3 | `main` con S3‑2 |
| **S3‑4** | `ui/revision.py`, Revisar, reauditoría con anexos, diferencia entre versiones, Excel regenerado, dictamen, plantilla Excel, `POST /v1/auditorias`, claves de API, middleware y `TrustedHostMiddleware` | interfaz | GS3‑4 | `main` con S3‑3 |
| **S3‑5** | auditoría DXF, IDS, R15, R16, sembrador y medición; IfcClash si sobra tiempo; guion CP‑R1 y CP‑R2 | adaptadores, pruebas | GS3‑5 | sin núcleo: sale de `main` **sin núcleo pendiente** (agrega archivos bajo `adapters/`, `scripts/meta_alpha.py:_ramas_adaptador`); va en secuencia, no a la vez, con la parte de S4 que toca `adapters/espacio` |
| **S3‑6 (D)** | RF‑100: serie fechada en USD de un insumo, `ml.anomaly.precios_atipicos` reutilizado, advertencia en la pestaña Precios y en la lista de la empresa; memoria `atipicos_s3.md` antes del código | interfaz, pruebas | GS3‑6 | sin núcleo: `main` con S1‑3 (lista de la empresa); toca solo `ml/` y `ui/` |

S3‑1 y S3‑5 son independientes y pueden adelantarse en paralelo; S3‑3 necesita S3‑2. Cada compuerta: `meta_silice.py
--version 0.8.0 --hasta S3‑n` en OK, CI verde en Linux y Windows, los encargos y, en GS3‑1, GS3‑3 y GS3‑4, **el de
seguridad**; en GS3‑1 y GS3‑4 el de usabilidad (Nielsen e ISO 9241‑110). GS3‑5 comprueba que el rango de la rama de
S3‑5 no toca `core/` (la auditoría de planos no toca el núcleo). La etiqueta `v0.8.0` se pone en `main` después de
`v0.7.0` (orden numérico, RV‑1).

**Orden de caída:** **S3‑6 (RF‑100) primero**; IfcClash; el QR; la ruta de la API (queda solo el Excel); la comparación contra la base del
revisor (queda la entrega anterior). Cuentas, cadena, firma, paquete con anexos y reauditoría no se recortan.

### 14.1 Expedientes en `core/`

| # | Qué | Por qué es genérico | Prueba |
|---|---|---|---|
| SL‑E7 | `eslabon_version` (tabla aditiva en `core/models/cadena.py`) y `core/budget/cadena.py`; un solo punto de cambio: `guardar_presupuesto` recibe `usuario` y `anexos_de` y la versión se sella antes de confirmar | cualquier presupuesto versionado, de cualquier dominio | §13.2 RF‑83 |
| SL‑E8 | `core/budget/canonico.py`: documento canónico (con moneda del proyecto y `precio_origen`) y su lectura | describe cualquier versión; lo usan la cadena, el paquete y la API (DRY) | ida y vuelta; vector de huella escrito a mano |
| SL‑E9 | `core/budget/comparacion.py`: **diferencia entre versiones** por cantidad y por precio (término cruzado en el precio), pura, y `revalorar` en memoria con otra lista | compara dos presupuestos cualesquiera; distinta de la separación del desvío de control de S2, que no la reutiliza (RV‑10) | memoria de diferencias |
| SL‑E12 | `core/catalog/sesion.py`: `busy_timeout`, diario WAL y `BEGIN IMMEDIATE` en las transacciones que crean versión (pasa de S5 a S3, RV‑7) | cualquier base SQLite con varios usuarios | §13.4 con `threading.Barrier` |

---

## 15. Rulings para ratificar

| # | Decisión | Costo si es errónea | Estado |
|---|---|---|---|
| RS3‑1 | DA‑S3‑1 a DA‑S3‑11 (§4.5) | el costo de cada una, en su fila | DA‑S3‑9 a DA‑S3‑11 los fijan RV‑7, RV‑8 y RV‑13; el resto, Eugenio |
| RS3‑2 | 30 min de inactividad, 12 h de antigüedad, 5 intentos y 15 min de bloqueo; freno global de 20 fallos en 10 min | cambiar constantes y sus pruebas de frontera | Eugenio |
| RS3‑3 | Primer administrador con código de instalación de 100 bits en un archivo local | si el instalador de S5 lo resuelve de otro modo, se retira la pantalla | entropía fijada por RV‑16; el mecanismo, Eugenio |
| RS3‑4 | Una cuenta puede armar y revisar; la vista de revisión lo indica cuando coinciden y el dictamen lo registra | prohibirlo exige dos personas en empresas de una | **ratificada por Eugenio el 2026‑10‑11** (pregunta P2 del maestro §10.3) |
| RS3‑5 | Sellado retroactivo automático al abrir el caso, declarado | un botón del administrador; versiones sin sellar mientras tanto | Eugenio |
| RS3‑6 | Umbrales de R15, distancias de R16 y límites del ZIP, del JSON y de la API como supuestos declarados, con sus fronteras exactas | cifras discutibles hasta medir o verificar fuente | fronteras fijadas por RV‑16 y PRU‑H4; las cifras, Eugenio |
| RS3‑7 | Revocar invalida todos los paquetes de esa clave (no hay fecha confiable) | un paquete legítimo antiguo deja de verificar; su dictamen se conserva | Eugenio |
| RS3‑8 | Red local sin TLS en 0.8.0, con las condiciones de §5.6 | adelantar a S3 la configuración de TLS de S5 | condiciones fijadas por RV‑15; aceptar sin TLS, Eugenio |
| RS3‑9 | Matriz de roles de §5.1 y mapa de actores de §3.0 | reasignar acciones y ajustar las pruebas de la matriz | **ratificada por Eugenio el 2026‑10‑11** (pregunta P2 del maestro §10.3) |
| RS3‑10 | Una empresa propia por instalación; la contraseña de la clave la conoce solo el administrador; las empresas de los paquetes recibidos, ajenas | rehacer `empresa_propia` y la pantalla | **ratificada por Eugenio el 2026‑10‑11** (pregunta P1 del maestro §10.3) |
| RS3‑11 | Meta de planos: 100 % de lo detectable y 0 falsas alarmas sobre OF‑001 limpio | fijar otro umbral en el protocolo de §13.5 b antes de medir | pregunta P8 del maestro §10.3 |

---

## 16. Riesgos

| Riesgo | Mitigación |
|---|---|
| Streamlit no aguanta varios usuarios en la red local | §13.4 con límite declarado (maestro §8) |
| Streamlit permite reanudar una sesión por su identificador | se confirma en S3‑0; si lo permite, se declara en §12 y pesa en adelantar TLS (RS3‑8) |
| Criptografía mal usada | solo bibliotecas; esquema de secretos fijado en el maestro §4.4; vectores del RFC 8032; revisión del encargo de seguridad en tres compuertas |
| Desacuerdo entre el documento canónico y la base (un `Decimal` reescrito) | prueba de ida y vuelta; el texto exacto de `DecimalExacto`; vector escrito a mano |
| Un camino nuevo crea versiones sin eslabón | sellado en el embudo; pruebas que recorren `MOTIVOS_VERSION` y enumeran a los llamadores |
| `usuario` obligatorio obliga a editar pruebas de regresión | se exige al confirmar, no al llamar al embudo: las pruebas que no confirman no cambian (§6.2) |
| Cambios en `core/` sin aval | expedientes; si el tutor rechaza SL‑E7, el paquete viaja sin cadena (solo firma) y se declara |
| `ifctester` con licencia o dependencias incompatibles | se confirma en S3‑0; extra aparte con importación diferida; si no, el IDS se reemplaza por comprobaciones propias con `ifcopenshell` y se declara |
| La medición de planos se cumple por construcción | parte del catálogo escrita por quien no programa las reglas; protocolo con huella antes de medir (§13.5 b) |
| Los instrumentos de Med cambian (acceso al inicio de CP‑07) | el guion agrega «entrar con la cuenta de prueba» una sola vez, al cerrar S3, como en SF §2 |

---

## 17. Preguntas abiertas

Las que dependen de Eugenio remiten al maestro §10.3; las que cerró la revisión se marcan.

1. ¿Eugenio acepta que recargar la página pida entrar de nuevo (DA‑S3‑1, RS3‑1)? — Eugenio.
2. ~~¿La misma persona puede armar y revisar en la misma instalación (RS3‑4)?~~ **Ratificada por Eugenio el
   2026‑10‑11** (pregunta P2 del maestro §10.3): sí; la vista de revisión lo indica y el dictamen lo registra (§9,
   paso 5).
3. ¿Se acepta la red local sin TLS en 0.8.0, o se adelanta TLS desde S5 (RS3‑8)? — Las condiciones las fijó RV‑15
   (§5.6); la decisión sigue siendo de Eugenio.
4. Tiempos de sesión y bloqueo (RS3‑2): ¿son razonables para una oficina de obra? — Eugenio.
5. ¿Qué datos de la empresa van en la clave pública y quién en la empresa conoce la contraseña de la clave? —
   **Cerrada por RV‑6** (nombre, RIF y ciudad opcional; la conoce solo el administrador); ratificada por Eugenio el
   2026‑10‑11 (pregunta P1).
6. ¿El tutor acepta SL‑E7, SL‑E8, SL‑E9 y SL‑E12 en `core/`? — Tutor.
7. ¿La meta de §11.5 (100 % en lo detectable y cero falsas alarmas sobre OF‑001 limpio) es la correcta? — **Valor
   por defecto fijado por RV‑20**; ratificada por Eugenio el 2026‑10‑11 en la pregunta P8 del maestro §10.3.
8. ¿CP‑R1 y CP‑R2 entran en Med o en una medición propia del indicador del administrador? — **Cerrada en parte por
   RV‑20:** S3‑0 es dueño del protocolo del indicador, con dos condiciones (§13.5 a), y CP‑R1 es su condición «con el
   sistema». Si se mide en la misma sesión de Med o en otra lo fija ese protocolo.
9. ¿El revisor debe poder **devolver** el paquete con observaciones firmadas por su propia empresa (respuesta
   firmada)? — Fuera de este spec (candidata a 1.x o 2.x); la separación de dominio de §7.1 ya le reserva su prefijo.
10. ~~¿Qué rol hace cada acción de S1 y S2?~~ **La matriz de §5.1** (REQ‑4, maestro §4.1), ratificada por Eugenio el
    2026‑10‑11 (pregunta P2 del maestro §10.3).
11. ~~¿Entran a la 1.0.0 las anomalías en variaciones de precio (RV‑21)?~~ **Decidida por Eugenio el 2026‑10‑11**
    (pregunta P5 del maestro §10.3): entran como deseable, RF‑100 (D), en la fase opcional S3‑6, reutilizando
    `ml.anomaly.precios_atipicos`; es lo primero que cae si falta tiempo.

## Enmienda 1.5 (2026-10-13)

Decidida por Eugenio el 2026-10-13 ([spec 1.5](2026-10-13-silice-1.5-fusion-design.md), W3 y W4).

- **RF-88 / UC-05:** además del formato neutro UC-05, Silice lee el libro de la empresa **tal como es**, mediante
  un perfil de plantilla (`adapters/hoja_empresa/perfiles/`).
- **DA-S3-10:** sigue valiendo para el `.silice` v1 (el Excel del emisor no viaja). El libro calcado que produce
  Silice es una entrega aparte, con su SHA-256 de origen en TRAZABILIDAD y en las propiedades del documento.
- **Amenaza declarada «con datos ficticios no se valida la tasa real de detección»:** queda atenuada. Los 17
  hallazgos reales de [causas raíz](../auditoria/2026-10-13-causas-raiz-libros-arenaza.md) son la primera medida
  sobre presupuestos entregados de verdad.
