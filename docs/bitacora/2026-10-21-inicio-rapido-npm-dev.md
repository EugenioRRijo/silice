# Inicio rápido: `npm run dev` para el equipo de desarrollo (2026-10-21)

Pedido de Eugenio: «el inicio rápido de este sistema solamente con `npm run dev` para que las demás máquinas puedan
probar en mi equipo de desarrollo».

## Decisión

`npm run dev` (en `frontend-desktop/`) ejecuta `scripts/inicio_rapido.mjs`, que:

1. Compila `dist` si falta o si `src/`, `index.html`, `vite.config.ts`, `package*.json` o `tsconfig*.json` son más nuevos.
2. Levanta **un** proceso de uvicorn (`api.main:app`) con el Python del entorno virtual activo (`VIRTUAL_ENV`; nunca
   crea uno, y sin él falla con un mensaje claro). API y `/app` salen por el mismo puerto.
3. Enciende la red local con el mecanismo del producto: `SILICE_RED_LOCAL=1` y `SILICE_DIRECCION=<IP LAN>`
   (`seguridad/red.py`, `api/proteccion.py`). `SILICE_DATOS` y `PYTHON_KEYRING_BACKEND` no se tocan.
4. Escucha **solo** en la IP LAN y en `127.0.0.1` (dos sockets en el mismo proceso, pasados a `uvicorn.Server.run`;
   uvicorn por línea de comandos admite un solo `--host`). Nunca `0.0.0.0`.
5. Imprime las dos URLs, el puerto, cómo detener (Ctrl+C), el aviso de seguridad y, en Windows, la regla de Firewall
   (limitada a `profile=private remoteip=localsubnet`; el script no la crea).

**Por qué no el servidor de Vite con `--host`:** su proxy reenvía las peticiones desde `127.0.0.1`, así que la API vería a
todos como el propio equipo y `es_local` dejaría de proteger firma, claves de API y de IA y carpeta de datos (RM-4,
comentario de `vite.config.ts`). Aquí la API ve la IP real del cliente.

**Qué IP:** IPv4 privada (10/8, 172.16/12, 192.168/16), no link-local ni loopback, y se descartan las interfaces
virtuales conocidas por nombre (vEthernet, WSL, VirtualBox, VMware, Docker, Hyper-V, Tailscale, ZeroTier, cualquier
nombre con «vpn», TAP/TUN, etc.) y las redes 192.168.56/99 y 172.17. Entre las que queden gana la de la ruta por omisión
(un socket UDP "conectado" que no envía nada); `--ip` fuerza otra, que debe existir en el equipo y ser privada.
En esta máquina la ruta por omisión es la de una VPN (UrbanVPN, 10.7.0.241); sin el filtro por nombre «vpn» el script la
eligió: hallazgo de la prueba real, corregido con prueba (rojo visto) antes de seguir.

**Puerto:** 8000 por omisión (el que espera el proxy de `dev:vite`); si está ocupado en cualquiera de las dos
direcciones, prueba hasta 10 y lo dice. `--puerto N` cambia el inicial.

**Cuentas de prueba:** consulta de solo lectura (`sqlite3` en modo `ro`, desde el Python del entorno) de los `login`
de `instalacion.db` (o de `SILICE_INSTALACION`/`SILICE_DATOS`); si hay `admin`, `ana`, `rita` o `tomas`, el aviso de
seguridad lo dice. No mira contraseñas ni escribe.

**Navegador:** no se abre solo salvo `--abrir`.

`npm run dev:vite` conserva el comportamiento anterior (Vite con recarga en caliente, solo 127.0.0.1, proxy al 8000).

## Verificación real (datos temporales, puerto 8020)

`SILICE_DATOS` temporal con una cuenta `admin` creada por la migración real y `tests/fixtures/instalacion.py`;
desde la propia IP LAN (192.168.0.198):

- `GET /app/` por LAN y por 127.0.0.1: 200. `GET /salud`: 200.
- `POST /v1/sesion` con credenciales falsas y `Origin: http://192.168.0.198:8020`: 401.
- `Host: evil.example.com`: 400.
- Login como `admin` por LAN: 200; `GET /v1/admin/asistente` (solo administrador): 200.
- `POST /v1/admin/asistente/clave` (sensible) con sesión y CSRF válidos desde la LAN: 403 «solo puede hacerse desde el
  propio equipo»; con `Origin` ajeno: 403.
- Sockets en escucha: solo `192.168.0.198:8020` y `127.0.0.1:8020`.
- Con el 8020 ocupado, un segundo arranque usó el 8021 y lo avisó. Sin `VIRTUAL_ENV`: sale con código 1 y el mensaje.
- El servidor de Eugenio en el 8000 no se tocó; todos los procesos de la prueba se cerraron por PID.

## Para revisar con lupa

- Exponer la red local en desarrollo: tráfico sin cifrar; el aviso lo dice. Con cuentas de prueba (contraseña
  conocida) cualquier equipo de la red puede entrar a todo lo que no sea «solo desde el propio equipo».
- El Python en línea (`python -c`) del servidor y de la consulta de cuentas: sin entrada del usuario más allá de IP
  validada (`esIpPrivada`/existe en el equipo), puerto entero y la ruta de la base.
- Firewall de Windows: la regla es manual y limitada a la subred local y al perfil Privado.
