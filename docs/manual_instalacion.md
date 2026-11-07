# Manual de instalación de Sílice

Para quien instala y administra Sílice en un equipo de la empresa. No hace falta saber programar.
La operación diaria está en el [manual de usuario](manual_usuario.md); cómo se construye el
instalador, en el [manual técnico](manual_tecnico.md).

## Requisitos

- Windows 10 22H2 u 11, de 64 bits. **No hace falta ser administrador** ni tener internet.
- Espacio libre: unos 700 MB para el instalador básico y unos 1,8 GB para el completo (con la
  similitud de partidas).
- Una cuenta de Windows por persona: cada cuenta tiene su propia copia del programa y sus propios
  datos.

## Comprobar la huella y la firma

Nunca ejecute un instalador que le llegó por correo, WhatsApp o memoria USB sin comprobarlo.
Junto al instalador vienen tres archivos: `SHA256SUMS`, `SHA256SUMS.ed25519` y `verificar_sumas.py`.

1. **Huella del archivo.** En PowerShell: `Get-FileHash .\Silice-1.0.0.exe -Algorithm SHA256`. El
   resultado debe ser el que aparece en `SHA256SUMS` para ese archivo.
2. **Firma de `SHA256SUMS`.** La firma demuestra que `SHA256SUMS` lo emitió el proyecto. Con `uv`
   instalado: `uv run --with cryptography verificar_sumas.py Silice-1.0.0.exe SHA256SUMS
   SHA256SUMS.ed25519 --publica <clave pública>`. Debe decir **VERIFICADO**.
3. **Huella de la clave.** El script imprime la huella SHA-256 de la clave pública que usó; debe ser
   exactamente esta (también está en la tesis):

   Huella de la clave: `07513b7c432cea1ad6a86ce3771ed08d3a4e9d7dbdce1d678830f45ab5068057`
   (`07513b7c 432cea1a d6a86ce3 771ed08d 3a4e9d7d bdce1d67 8830f45a b5068057`)

   Si no coincide, **no instale** y avise a quien le entregó el instalador.

Si ya tiene Sílice instalado, el mismo control se hace sin `uv`:
`python -m operacion verificar-instalador Silice-1.0.1.exe SHA256SUMS SHA256SUMS.ed25519`.
Nunca abra `SHA256SUMS` con un editor y lo guarde: cualquier cambio (incluso los saltos de línea)
invalida la firma.

## Instalar

1. Haga doble clic en `Silice-<versión>.exe` (o en `Silice-<versión>-completo.exe` si necesita la
   similitud de partidas).
2. Windows puede mostrar «Windows protegió su PC» (ver SmartScreen más abajo).
3. Elija los componentes: el programa (obligatorio), el caso de demostración (datos construidos,
   ficticios) y, en el completo, la similitud de partidas.
4. Termine el asistente. Se crean los accesos «Sílice» y «Detener Sílice» en el menú Inicio.

El programa queda en `%LOCALAPPDATA%\Programs\Silice` y sus datos en `%LOCALAPPDATA%\Silice`. Si
alguien usa otra carpeta de datos por una razón especial, la variable es `SILICE_DATOS`.

## Primer arranque

Haga doble clic en «Sílice». Se abren la **ventana de Sílice**, con su ícono en la barra de tareas,
y una consola minimizada: es el servidor y muestra el código de instalación la primera vez.
**Para terminar, basta cerrar la ventana:** eso detiene Sílice, igual que cerrar la consola o usar
el acceso «Detener Sílice». La ventana usa WebView2 de Microsoft, que ya viene en Windows 11 y en
casi todos los Windows 10. Si el equipo no puede mostrarla, Sílice se abre en el navegador en
`http://127.0.0.1:8501/app/` y la consola lo avisa en una línea que empieza con «AVISO»; Sílice
funciona igual en el navegador (ver «Si falta WebView2» más abajo).

Como todavía no hay cuentas, Sílice crea al arrancar un **código de instalación de un solo uso**:
20 caracteres en grupos de cuatro (letras de la A a la Z y cifras del 2 al 7). Lo deja en tres
sitios: en el Bloc de notas, que se abre solo esa primera vez; en la consola minimizada de Sílice
(búsquela en la barra de tareas y busque «Código de instalación»); y en el archivo
`%LOCALAPPDATA%\Silice\datos\codigo_instalacion.txt`. El código nunca se guarda en el registro.

La ventana de Sílice (o el navegador) muestra la pantalla **Bienvenida a Sílice**. Pegue el código
tal cual, escriba su nombre, el usuario y la contraseña (dos veces) y pulse «Crear la cuenta y
entrar». Si esa misma cuenta va a armar presupuestos, marque «Usaré esta cuenta también para armar
presupuestos». Es la cuenta del administrador: con ella se crean las demás cuentas en
Administración. El código se borra al usarse y no sirve otra vez.

- La bienvenida solo funciona en el propio equipo donde está instalado Sílice, no desde otro
  equipo de la red local.
- Si la bienvenida dice que no encuentra el archivo, use «Detener Sílice» y abra «Sílice» otra vez:
  al arrancar sin cuentas se crea un código nuevo si falta el archivo o si el que tiene ya no vale.
- Si ya hay cuentas y se perdió el acceso de administrador, use el acceso «Sílice: recuperar
  acceso de administrador» del menú Inicio de Windows. Su ventana muestra un **código de
  restablecimiento** (sirve una sola vez y vence a las 24 horas). En la pantalla de acceso pulse
  «Perdí el acceso de administrador» y úselo allí.

### Abrir Sílice otra vez

Si Sílice ya está abierto, hacer doble clic en «Sílice» otra vez no abre un segundo Sílice:
trae al frente la ventana que ya está. Si el Sílice abierto se abrió en el navegador, abre otra
pestaña del navegador en la misma dirección.

La ventana recuerda el tamaño de letra y el zoom de la Hoja de una vez para otra: los guarda en
`%LOCALAPPDATA%\Silice\datos\perfil_ventana`, junto a los datos. La sesión no se guarda: al volver
a abrir Sílice hay que entrar otra vez con su cuenta.

### Si falta WebView2

La ventana de Sílice necesita **Microsoft Edge WebView2 Runtime**, un componente gratuito de
Microsoft. Si falta, Sílice se abre en el navegador y la consola dice, en la línea «AVISO», que
WebView2 no está instalado. Para tener la ventana:

1. En un equipo con internet, abra la página de Microsoft
   `https://developer.microsoft.com/microsoft-edge/webview2/`, sección «Download the WebView2
   Runtime», y baje el **Evergreen Standalone Installer** de **x64** (es el instalador completo,
   que no necesita internet en el equipo donde se instala).
2. Lleve ese archivo al equipo de Sílice (por ejemplo, en una memoria USB) y ejecútelo. Si Windows
   pide permiso de administrador y su cuenta no lo tiene, pídaselo a quien administra el equipo.
3. Cierre Sílice (la consola o «Detener Sílice») y vuelva a abrirlo: ahora se abre la ventana.

Si después de instalarlo Sílice sigue abriendo el navegador, la línea «AVISO» de la consola dice el
motivo (por ejemplo, un antivirus que bloquea el componente de la ventana).

## Casos

Lo que este manual llama caso, la interfaz lo llama **carpeta de trabajo**: un archivo `.db` con su
catálogo, sus precios y sus obras. Viven en `%LOCALAPPDATA%\Silice\datos\casos\`. El administrador
las maneja en **Administración › Carpetas de trabajo**: ve la lista y abre una, crea una nueva (con
su moneda de trabajo), sube el `.db` de una carpeta copiada de otro equipo (hasta 20 MiB; nunca
reemplaza una que ya exista y, si es de una versión anterior, se migra con respaldo) y, si su
cuenta también arma, estrena la demostración, que trae datos construidos para aprender. Quien
arma cambia de carpeta al abrir una obra de otra carpeta desde la barra lateral o el buscador. No
se pueden abrir archivos de otras carpetas ni de carpetas de red: se suben primero.

## Red local

Por defecto Sílice **solo atiende a este equipo**. Para que otros equipos de la oficina entren:

1. Use, en el equipo servidor, el acceso «Sílice: red local (administrador)» y acepte el aviso de
   Windows. Elija la interfaz de su red de confianza.
2. Reinicie Sílice. Los demás equipos abren `http://<IP del servidor>:8501`.
3. Para apagarla: `python -m operacion red-local desactivar` desde el mismo acceso.

**Red de confianza** es la red propia de la oficina, con WPA2 o WPA3 o cableada, y equipos
conocidos. **No** lo es la Wi‑Fi de la obra, una red pública ni la conexión compartida de un
teléfono. En Windows, la red debe estar marcada como **Privada**.

Sílice **no cifra** la conexión en la red local: las contraseñas viajan sin cifrar. La pantalla de
acceso lo avisa a quien entra desde otro equipo. Firmar, tocar las claves y crear claves de API
solo se puede desde el propio servidor.

**Nunca** use un túnel (`cloudflared`, `ngrok`, un proxy inverso) para publicar Sílice en internet:
anula las protecciones por IP y expone el sistema. Si Sílice detecta uno en ejecución, lo avisa al
arrancar. Si la IP del servidor cambia (DHCP), Sílice arranca solo en `127.0.0.1` y lo dice;
conviene reservar la IP en el enrutador.

## API y claves

La API está apagada. Para usarla (por ejemplo, desde un plugin) el administrador pone
`activa = true` en `%LOCALAPPDATA%\Silice\config\silice.toml`, reinicia y crea una clave en
Administración, desde el propio servidor; se muestra **una sola vez**. Toda ruta pide la clave
(cabecera `X-Silice-Clave`) salvo `/salud`.

## Actualizar

Ejecute el instalador de la versión nueva (después de comprobarlo). Sílice se detiene, se reemplaza
el programa, se respaldan las bases y se migran. Sus datos y sus presupuestos quedan. Si la
versión nueva no puede migrar una base, la base **no se toca** y el arranque explica qué hacer.

## Respaldos

Antes de cada migración Sílice guarda un juego de respaldo (la instalación y los casos juntos, con
una ficha) en `%LOCALAPPDATA%\Silice\respaldos\`; se conservan los cinco últimos. En
Administración → Instalación se puede crear uno a mano y descargarlo. **Un respaldo contiene todo**:
huellas de contraseñas, la clave de firma cifrada y huellas de claves de API. Guárdelo como guarda
las llaves. La clave de IA de la empresa se guarda con el almacén de claves de Windows (`keyring`)
y **no viaja en los respaldos**: en otro equipo hay que registrarla de nuevo.

## Restaurar

Con Sílice detenido: `python -m operacion restaurar <carpeta del juego>`. Restaurar la instalación
puede **deshacer en silencio** revocaciones, cuentas desactivadas y cambios de roles. Por eso
Sílice escribe `eventos_perdidos_<fecha>.json` y **bloquea las operaciones sensibles** hasta que el
administrador revise la lista (Administración → Instalación) y la marque como revisada.

## Desinstalar

«Configuración → Aplicaciones → Sílice → Desinstalar». Se borra el programa; **los datos y los
respaldos quedan** en `%LOCALAPPDATA%\Silice`. Bórrelos a mano si ya no los necesita.

## SmartScreen

Este instalador no lleva firma de código (cuesta una suscripción anual). Windows puede mostrar
**«Windows protegió su PC»**: pulse «Más información» y «Ejecutar de todas formas» **solo después**
de comprobar la huella y la firma como se explicó arriba.

## Problemas frecuentes

- **Puerto ocupado:** otro programa usa el 8501. Cierre ese programa o cambie `puerto` en
  `silice.toml`.
- **Base no adoptable:** una base muy antigua (anterior a la 0.4) no se puede migrar sola. Sílice
  no la toca; vuelva a sembrar el caso o pida ayuda con el juego de respaldo.
- **Esta base es de una versión más nueva:** instale esa versión o restaure el respaldo previo.
- **La IP de la red local ya no existe:** Sílice arrancó solo en este equipo. Vuelva a activar la
  red local y elija la IP nueva.
- **Prefiero el navegador:** en `%LOCALAPPDATA%\Silice\config\silice.toml`, en la tabla
  `[interfaz]`, ponga `abrir_en = "navegador"` (o `abrir_en = "ventana"` para volver) y vuelva a
  abrir Sílice. La consola lo recuerda con un «AVISO» en cada arranque.
- **Se abre el navegador en vez de la ventana:** lea la línea «AVISO» de la consola; dice por qué
  (falta WebView2, un antivirus bloquea el componente de la ventana, la ventana no cargó en 30
  segundos o el ajuste anterior). Para WebView2, vea «Si falta WebView2».
- **«Sílice se detuvo» en la ventana:** el servidor terminó con la ventana abierta. Cierre la ventana
  y abra «Sílice» otra vez; si se repite, mire el registro en `%LOCALAPPDATA%\Silice
egistros`.
- **No abre la ventana ni el navegador:** abra `http://127.0.0.1:8501/app/` a mano.
