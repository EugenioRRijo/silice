// Inicio rapido para el equipo de desarrollo: `npm run dev` levanta Silice completo en UN solo puerto
// (API + interfaz en /app) y lo deja accesible a las demas maquinas de la red local.
//
// Usa el mecanismo OFICIAL del producto (SILICE_RED_LOCAL=1 y SILICE_DIRECCION=<ip>), no el servidor de Vite con
// `--host`: con el proxy de Vite la API veria siempre 127.0.0.1 y anularia «solo desde el propio equipo» (RM-4;
// firma, claves de API y de IA, carpeta de datos). Aqui la API ve la IP real de cada cliente.
//
// La logica pura (IP, puerto, entorno, mensaje, recompilacion) esta exportada y probada en inicio_rapido.test.mjs;
// la parte con efectos vive al final y solo corre cuando se ejecuta el archivo.
import { spawn, spawnSync } from "node:child_process";
import dgram from "node:dgram";
import { existsSync, readdirSync, statSync } from "node:fs";
import net from "node:net";
import { networkInterfaces } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

export const PUERTO_INICIAL = 8000;
export const INTENTOS_DE_PUERTO = 10;
export const LOOPBACK = "127.0.0.1";
// Cuentas de prueba del repositorio de desarrollo: su contrasena es conocida (aviso al arrancar).
export const CUENTAS_DE_PRUEBA = ["admin", "ana", "rita", "tomas"];

const VIRTUALES = /vethernet|wsl|virtualbox|vbox|vmware|vmnet|hyper-?v|docker|veth|br-|virbr|podman|tailscale|zerotier|hamachi|wireguard|nordlynx|openvpn|\btap\b|tap-|\btun\d*\b|vpn|ppp|anyconnect|fortinet|globalprotect|host-only|bluetooth|loopback|pseudo/i;
// Redes que VirtualBox (host-only) y Docker Machine reparten por omision.
const REDES_VIRTUALES = [/^192\.168\.56\./, /^192\.168\.99\./, /^172\.17\./];

function octetos(ip) {
  if (typeof ip !== "string" || !/^\d{1,3}(\.\d{1,3}){3}$/.test(ip)) return null;
  const o = ip.split(".").map(Number);
  return o.every((n) => n >= 0 && n <= 255) ? o : null;
}

export function esIpPrivada(ip) {
  const o = octetos(ip);
  if (!o) return false;
  return o[0] === 10 || (o[0] === 172 && o[1] >= 16 && o[1] <= 31) || (o[0] === 192 && o[1] === 168);
}

export function esInterfazVirtual(nombre, ip) {
  return VIRTUALES.test(nombre ?? "") || REDES_VIRTUALES.some((r) => r.test(ip ?? ""));
}

/** De `os.networkInterfaces()`: IPv4 privadas, externas, no link-local y no virtuales. */
export function candidatasLan(interfaces) {
  const salida = [];
  for (const [nombre, direcciones] of Object.entries(interfaces ?? {})) {
    for (const d of direcciones ?? []) {
      if (d.family !== "IPv4" && d.family !== 4) continue;
      if (d.internal || !esIpPrivada(d.address) || esInterfazVirtual(nombre, d.address)) continue;
      salida.push({ nombre, ip: d.address });
    }
  }
  return salida;
}

export function elegirIp({ candidatas, rutaPorOmision, todas, ipPedida }) {
  if (ipPedida) {
    if (!esIpPrivada(ipPedida)) throw new Error(`--ip ${ipPedida} no es una IP privada (10.x, 172.16-31.x, 192.168.x).`);
    if (!todas.includes(ipPedida)) throw new Error(`--ip ${ipPedida} no existe en este equipo (IP de sus interfaces: ${todas.join(", ")}).`);
    return { ip: ipPedida };
  }
  if (candidatas.length === 0) {
    throw new Error(
      "No encontre una IP privada de red local en este equipo (¿sin Wi-Fi ni cable?). Conectese a la red o indique una con --ip.",
    );
  }
  const porRuta = candidatas.find((c) => c.ip === rutaPorOmision);
  const elegida = porRuta ?? candidatas[0];
  if (candidatas.length > 1) {
    const otras = candidatas.filter((c) => c !== elegida).map((c) => `${c.ip} (${c.nombre})`).join(", ");
    return { ip: elegida.ip, aviso: `Hay varias redes: uso ${elegida.ip} (${elegida.nombre}). Otras: ${otras}. Para otra, use --ip <direccion>.` };
  }
  return { ip: elegida.ip };
}

export async function elegirPuerto(inicio, libre, intentos = INTENTOS_DE_PUERTO) {
  const ocupados = [];
  for (let p = inicio; p < inicio + intentos && p <= 65535; p++) {
    if (await libre(p)) return { puerto: p, ocupados };
    ocupados.push(p);
  }
  throw new Error(`No hay un puerto libre entre ${inicio} y ${ocupados[ocupados.length - 1]}. Use --puerto <otro>.`);
}

/** Entorno del servidor: red local encendida y direccion fijada (mecanismo oficial); lo demas, intacto. */
export function armarEntorno(base, ip) {
  return { ...base, SILICE_RED_LOCAL: "1", SILICE_DIRECCION: ip };
}

// Un solo proceso de uvicorn con DOS sockets (IP LAN y 127.0.0.1), nunca 0.0.0.0: el propio equipo entra por
// 127.0.0.1 y la API lo reconoce como local; los demas, por la IP LAN y quedan fuera de lo sensible.
const CODIGO_SERVIDOR = [
  "import socket, sys, uvicorn",
  "ip, puerto = sys.argv[1], int(sys.argv[2])",
  "zocalos = []",
  `for host in (ip, "${LOOPBACK}"):`,
  "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)",
  "    s.bind((host, puerto))",
  "    s.listen(2048)",
  "    zocalos.append(s)",
  'uvicorn.Server(uvicorn.Config("api.main:app", host=ip, port=puerto, access_log=False)).run(sockets=zocalos)',
].join("\n");

export function ordenServidor(ip, puerto) {
  return ["-c", CODIGO_SERVIDOR, ip, String(puerto)];
}

export function rutaPython(virtualEnv, plataforma) {
  if (!virtualEnv) {
    throw new Error(
      "No hay un entorno virtual activo (VIRTUAL_ENV vacio). Active el de siempre antes de `npm run dev` " +
        "(por ejemplo .venv\\Scripts\\Activate.ps1); este comando no crea ninguno.",
    );
  }
  return plataforma === "win32" ? join(virtualEnv, "Scripts", "python.exe") : join(virtualEnv, "bin", "python");
}

export function necesitaCompilar({ fuentes, dist, forzar = false }) {
  return forzar || dist === null || dist === undefined || fuentes > dist;
}

export function cuentasDePrueba(logins) {
  const conocidas = new Set(CUENTAS_DE_PRUEBA);
  return [...new Set((logins ?? []).map((l) => String(l).toLowerCase()))].filter((l) => conocidas.has(l)).sort();
}

export function rutaInstalacion(entorno, raiz) {
  if (entorno.SILICE_INSTALACION) return resolve(entorno.SILICE_INSTALACION);
  return join(entorno.SILICE_DATOS ? resolve(entorno.SILICE_DATOS) : join(raiz, "data"), "instalacion.db");
}

export function parsearArgumentos(argv) {
  const { values } = parseArgs({
    args: argv,
    options: {
      ip: { type: "string" },
      puerto: { type: "string" },
      abrir: { type: "boolean", default: false },
      compilar: { type: "boolean", default: false },
      ayuda: { type: "boolean", short: "h", default: false },
    },
    strict: true,
  });
  let puerto = PUERTO_INICIAL;
  if (values.puerto !== undefined) {
    puerto = Number(values.puerto);
    if (!Number.isInteger(puerto) || puerto < 1 || puerto > 65535) throw new Error(`--puerto ${values.puerto} no es un puerto valido (1-65535).`);
  }
  return { ip: values.ip, puerto, abrir: values.abrir, compilar: values.compilar, ayuda: values.ayuda };
}

export const AYUDA = `Uso: npm run dev [-- opciones]
  Compila la interfaz si hace falta y levanta Silice (API + /app) en un solo puerto, visible en la red local.
  --ip <direccion>   IP privada de este equipo (por omision, la de la ruta por omision)
  --puerto <n>       puerto inicial (8000; si esta ocupado prueba los 9 siguientes)
  --compilar         fuerza \`npm run build\`
  --abrir            abre el navegador en esta maquina
  -h, --ayuda        esta ayuda
Desarrollo con recarga en caliente (solo este equipo): npm run dev:vite`;

export function mensajeInicio({ ip, puerto, cuentas, plataforma, ocupados = [] }) {
  const l = [];
  const barra = "=".repeat(74);
  l.push("", barra, "  Silice listo (modo desarrollo, red local ENCENDIDA)", barra);
  if (ocupados.length) l.push(`  El puerto ${ocupados.join(", ")} estaba ocupado; uso el ${puerto}.`);
  l.push(
    "",
    `  En ESTA maquina:      http://${LOOPBACK}:${puerto}/app/`,
    `  En las OTRAS maquinas: http://${ip}:${puerto}/app/`,
    `  Puerto: ${puerto}   (la API y la interfaz salen por el mismo puerto)`,
    "  Para detener: Ctrl+C en esta ventana.",
    "",
    "  AVISO DE SEGURIDAD",
    "  - Esta maquina acepta conexiones de la red local: entre con una cuenta.",
    "  - Firmar, claves de API, clave de IA y carpeta de datos: solo desde este equipo.",
    "  - La conexion no va cifrada: use solo una red de confianza (WPA2/WPA3 o cable), nunca una publica.",
  );
  if (cuentas.length) {
    l.push(
      `  - ATENCION: existen cuentas de prueba (${cuentas.join(", ")}) con contrasena conocida.`,
      "    Cualquiera de la red puede entrar con ellas: desactivelas o cambie su contrasena si la red no es solo suya.",
    );
  }
  if (plataforma === "win32") {
    l.push(
      "",
      "  Si las otras maquinas no conectan, el Firewall de Windows puede estar bloqueando el puerto",
      "  (y la red debe estar marcada como Privada). Regla, en PowerShell como administrador (no la creo yo):",
      `    netsh advfirewall firewall add rule name="Silice dev ${puerto}" dir=in action=allow protocol=TCP localport=${puerto} profile=private remoteip=localsubnet`,
      `  Para quitarla: netsh advfirewall firewall delete rule name="Silice dev ${puerto}"`,
    );
  }
  l.push(barra, "");
  return l.join("\n");
}

// ---------------------------------------------------------------- efectos (solo al ejecutar el archivo)

function mtimeMaximo(ruta) {
  if (!existsSync(ruta)) return 0;
  const st = statSync(ruta);
  if (!st.isDirectory()) return st.mtimeMs;
  let max = st.mtimeMs;
  for (const e of readdirSync(ruta)) max = Math.max(max, mtimeMaximo(join(ruta, e)));
  return max;
}

function mtimeDeFuentes(front) {
  const sueltos = ["index.html", "vite.config.ts", "package.json", "package-lock.json", "tsconfig.json", "tsconfig.app.json", "tsconfig.node.json"];
  return Math.max(mtimeMaximo(join(front, "src")), ...sueltos.map((f) => mtimeMaximo(join(front, f))));
}

function ipDeLaRutaPorOmision() {
  // Conectar un socket UDP no envia nada: solo le hace elegir la interfaz de la ruta por omision.
  return new Promise((ok) => {
    const s = dgram.createSocket("udp4");
    const fin = (v) => {
      try {
        s.close();
      } catch {
        /* ya cerrado */
      }
      ok(v);
    };
    s.on("error", () => fin(null));
    s.connect(9, "203.0.113.1", () => fin(s.address().address));
  });
}

function escucha(host, puerto) {
  return new Promise((ok) => {
    const srv = net.createServer();
    srv.once("error", () => ok(false));
    srv.listen({ host, port: puerto, exclusive: true }, () => srv.close(() => ok(true)));
  });
}

function leerLogins(python, raiz, entorno) {
  const ruta = rutaInstalacion(entorno, raiz);
  if (!existsSync(ruta)) return [];
  const codigo = [
    "import json, pathlib, sqlite3, sys",
    "try:",
    '    c = sqlite3.connect(pathlib.Path(sys.argv[1]).resolve().as_uri() + "?mode=ro", uri=True)',
    '    print(json.dumps([r[0] for r in c.execute("select login from usuario")]))',
    "except Exception:",
    "    print('[]')",
  ].join("\n");
  const r = spawnSync(python, ["-c", codigo, ruta], { cwd: raiz, encoding: "utf8", timeout: 15000 });
  try {
    return JSON.parse(r.stdout || "[]");
  } catch {
    return [];
  }
}

async function esperarSalud(url, hijo, plazoMs = 90000) {
  const fin = Date.now() + plazoMs;
  while (Date.now() < fin) {
    if (hijo.exitCode !== null) return false;
    try {
      const r = await fetch(url);
      if (r.ok) return true;
    } catch {
      /* aun no arranca */
    }
    await new Promise((ok) => setTimeout(ok, 500));
  }
  return false;
}

function compilar(front) {
  const npmJs = process.env.npm_execpath;
  const usaNode = npmJs && npmJs.endsWith(".js");
  const r = usaNode
    ? spawnSync(process.execPath, [npmJs, "run", "build"], { cwd: front, stdio: "inherit" })
    : spawnSync("npm run build", { cwd: front, stdio: "inherit", shell: true });
  return r.status === 0;
}

function abrirNavegador(url) {
  const [cmd, args] =
    process.platform === "win32" ? ["cmd", ["/c", "start", "", url]] : process.platform === "darwin" ? ["open", [url]] : ["xdg-open", [url]];
  spawn(cmd, args, { stdio: "ignore", detached: true }).unref();
}

async function principal() {
  const aqui = dirname(fileURLToPath(import.meta.url));
  const front = resolve(aqui, "..");
  const raiz = resolve(front, "..");
  const args = parsearArgumentos(process.argv.slice(2));
  if (args.ayuda) {
    console.log(AYUDA);
    return 0;
  }
  const python = rutaPython(process.env.VIRTUAL_ENV, process.platform);
  const prueba = spawnSync(python, ["-c", "import fastapi, uvicorn"], { cwd: raiz, encoding: "utf8" });
  if (prueba.error || prueba.status !== 0) {
    throw new Error(`El entorno virtual ${process.env.VIRTUAL_ENV} no tiene fastapi y uvicorn (uv sync --all-extras en el entorno de siempre).`);
  }

  const todas = Object.values(networkInterfaces()).flatMap((ds) => (ds ?? []).filter((d) => d.family === "IPv4").map((d) => d.address));
  const { ip, aviso } = elegirIp({
    candidatas: candidatasLan(networkInterfaces()),
    rutaPorOmision: await ipDeLaRutaPorOmision(),
    todas,
    ipPedida: args.ip,
  });
  if (aviso) console.log(aviso);

  const { puerto, ocupados } = await elegirPuerto(args.puerto, async (p) => (await escucha(ip, p)) && (await escucha(LOOPBACK, p)));

  const dist = join(front, "dist", "index.html");
  const distMtime = existsSync(dist) ? statSync(dist).mtimeMs : null;
  if (necesitaCompilar({ fuentes: mtimeDeFuentes(front), dist: distMtime, forzar: args.compilar })) {
    console.log("Compilando la interfaz (npm run build)...");
    if (!compilar(front)) throw new Error("La compilacion de la interfaz fallo; corrija y vuelva a intentar.");
  } else {
    console.log("La interfaz compilada (dist) esta al dia.");
  }

  const entorno = armarEntorno(process.env, ip);
  const cuentas = cuentasDePrueba(leerLogins(python, raiz, entorno));
  console.log(`Arrancando el servidor en ${ip}:${puerto} y ${LOOPBACK}:${puerto}...`);
  const hijo = spawn(python, ordenServidor(ip, puerto), { cwd: raiz, env: entorno, stdio: "inherit" });
  const detener = () => {
    if (hijo.exitCode === null) hijo.kill();
  };
  process.on("SIGINT", detener);
  process.on("SIGTERM", detener);
  process.on("exit", detener);

  const salida = new Promise((ok) => hijo.on("exit", (codigo) => ok(codigo ?? 0)));
  if (!(await esperarSalud(`http://${LOOPBACK}:${puerto}/salud`, hijo))) {
    detener();
    throw new Error("El servidor no respondio en /salud; revise el mensaje de arriba.");
  }
  console.log(mensajeInicio({ ip, puerto, cuentas, plataforma: process.platform, ocupados }));
  if (args.abrir) abrirNavegador(`http://${LOOPBACK}:${puerto}/app/`);
  return salida;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  principal().then(
    (codigo) => process.exit(codigo),
    (e) => {
      console.error(`\nNo se pudo iniciar: ${e.message}`);
      process.exit(1);
    },
  );
}
