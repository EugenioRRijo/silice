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

Haga doble clic en «Sílice». Se abre una ventana minimizada (es el servidor: **ciérrela para
detener Sílice**) y el navegador entra a `http://127.0.0.1:8501`.

Como todavía no hay usuarios, Sílice deja un **código de instalación de un solo uso** en la
ventana del servidor y en `%LOCALAPPDATA%\Silice\datos\codigo_instalacion.txt`. Úselo en la pantalla
de acceso para crear el primer administrador. El código nunca se guarda en el registro.

## Casos

Los casos viven en `%LOCALAPPDATA%\Silice\datos\casos\`. En **Inicio** se elige uno de la lista, se
crea uno nuevo o se sube un archivo `.db`. No se pueden abrir archivos de otras carpetas ni de
carpetas de red: se copian primero. El caso de demostración trae datos construidos para aprender.

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
- **No abre el navegador:** abra `http://127.0.0.1:8501` a mano.
