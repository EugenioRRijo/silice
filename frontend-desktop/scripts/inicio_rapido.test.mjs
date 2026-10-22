import { describe, expect, test } from "vitest";
import {
  armarEntorno,
  candidatasLan,
  cuentasDePrueba,
  elegirIp,
  elegirPuerto,
  esInterfazVirtual,
  esIpPrivada,
  mensajeInicio,
  necesitaCompilar,
  ordenServidor,
  parsearArgumentos,
  rutaPython,
} from "./inicio_rapido.mjs";

describe("esIpPrivada", () => {
  test.each(["10.0.0.5", "10.255.255.254", "172.16.0.1", "172.31.255.1", "192.168.1.20"])("%s es privada", (ip) => {
    expect(esIpPrivada(ip)).toBe(true);
  });
  test.each(["169.254.10.2", "127.0.0.1", "8.8.8.8", "172.15.0.1", "172.32.0.1", "192.169.0.1", "0.0.0.0", "", "abc", "10.0.0", "10.0.0.256", "::1"])(
    "%s no es privada",
    (ip) => {
      expect(esIpPrivada(ip)).toBe(false);
    },
  );
});

describe("esInterfazVirtual", () => {
  test.each([
    ["vEthernet (WSL)", "172.28.0.1"],
    ["VirtualBox Host-Only Network", "192.168.56.1"],
    ["VMware Network Adapter VMnet8", "192.168.100.1"],
    ["docker0", "172.17.0.1"],
    ["Tailscale", "10.0.0.9"],
    ["OpenVPN TAP-Windows Adapter", "10.8.0.2"],
    ["Ethernet 3", "192.168.56.1"],
    ["UrbanVPN", "10.7.0.241"],
  ])("%s %s es virtual", (nombre, ip) => {
    expect(esInterfazVirtual(nombre, ip)).toBe(true);
  });
  test.each([
    ["Wi-Fi", "192.168.1.20"],
    ["Ethernet", "10.1.2.3"],
    ["Ethernet 2", "172.20.5.5"],
  ])("%s %s es fisica", (nombre, ip) => {
    expect(esInterfazVirtual(nombre, ip)).toBe(false);
  });
});

const IFACES = {
  Loopback: [{ family: "IPv4", address: "127.0.0.1", internal: true }],
  "Wi-Fi": [
    { family: "IPv6", address: "fe80::1", internal: false },
    { family: "IPv4", address: "192.168.1.20", internal: false },
  ],
  "vEthernet (WSL)": [{ family: "IPv4", address: "172.28.0.1", internal: false }],
  Ethernet: [{ family: "IPv4", address: "169.254.3.3", internal: false }],
  "VirtualBox Host-Only": [{ family: "IPv4", address: "192.168.56.1", internal: false }],
  Publica: [{ family: "IPv4", address: "190.1.2.3", internal: false }],
};

describe("candidatasLan", () => {
  test("solo IPv4 privada, externa a loopback, no link-local y no virtual", () => {
    expect(candidatasLan(IFACES)).toEqual([{ nombre: "Wi-Fi", ip: "192.168.1.20" }]);
  });
  test("tolera interfaces sin direcciones", () => {
    expect(candidatasLan({ X: undefined })).toEqual([]);
  });
});

describe("elegirIp", () => {
  const dos = [
    { nombre: "Ethernet", ip: "10.0.0.7" },
    { nombre: "Wi-Fi", ip: "192.168.1.20" },
  ];
  const todas = ["127.0.0.1", "10.0.0.7", "192.168.1.20", "192.168.56.1"];
  test("usa la de la ruta por omision si es candidata", () => {
    expect(elegirIp({ candidatas: dos, rutaPorOmision: "192.168.1.20", todas }).ip).toBe("192.168.1.20");
  });
  test("sin ruta por omision toma la primera y avisa si hay varias", () => {
    const r = elegirIp({ candidatas: dos, rutaPorOmision: null, todas });
    expect(r.ip).toBe("10.0.0.7");
    expect(r.aviso).toMatch(/--ip/);
  });
  test("una sola candidata no avisa", () => {
    expect(elegirIp({ candidatas: [dos[0]], rutaPorOmision: null, todas }).aviso).toBeUndefined();
  });
  test("--ip debe existir en el equipo y ser privada", () => {
    expect(elegirIp({ candidatas: dos, rutaPorOmision: null, todas, ipPedida: "192.168.56.1" }).ip).toBe("192.168.56.1");
    expect(() => elegirIp({ candidatas: dos, rutaPorOmision: null, todas, ipPedida: "10.9.9.9" })).toThrow(/no existe/);
    expect(() => elegirIp({ candidatas: dos, rutaPorOmision: null, todas: [...todas, "8.8.8.8"], ipPedida: "8.8.8.8" })).toThrow(/privada/);
    expect(() => elegirIp({ candidatas: dos, rutaPorOmision: null, todas: [...todas, "0.0.0.0"], ipPedida: "0.0.0.0" })).toThrow(/privada/);
  });
  test("sin candidatas falla con un mensaje claro", () => {
    expect(() => elegirIp({ candidatas: [], rutaPorOmision: null, todas })).toThrow(/red local/);
  });
});

describe("elegirPuerto", () => {
  test("devuelve el primero libre y recuerda los ocupados", async () => {
    const r = await elegirPuerto(8000, async (p) => p >= 8002);
    expect(r).toEqual({ puerto: 8002, ocupados: [8000, 8001] });
  });
  test("se rinde tras el tope de intentos", async () => {
    await expect(elegirPuerto(8000, async () => false, 3)).rejects.toThrow(/8000.*8002/);
  });
  test("no pasa de 65535", async () => {
    await expect(elegirPuerto(65535, async () => false, 5)).rejects.toThrow();
  });
});

describe("armarEntorno", () => {
  const base = { PATH: "p", VIRTUAL_ENV: "v", PYTHON_KEYRING_BACKEND: "k", SILICE_DATOS: "d", SILICE_RED_LOCAL: "0", SILICE_DIRECCION: "9.9.9.9" };
  test("enciende la red local y fija la direccion con el mecanismo oficial", () => {
    const e = armarEntorno(base, "192.168.1.20");
    expect(e.SILICE_RED_LOCAL).toBe("1");
    expect(e.SILICE_DIRECCION).toBe("192.168.1.20");
  });
  test("no toca datos, keyring ni el resto, y no muta la base", () => {
    const e = armarEntorno(base, "192.168.1.20");
    expect(e.SILICE_DATOS).toBe("d");
    expect(e.PYTHON_KEYRING_BACKEND).toBe("k");
    expect(e.VIRTUAL_ENV).toBe("v");
    expect(base.SILICE_RED_LOCAL).toBe("0");
  });
  test("sin SILICE_DATOS en la base no lo inventa", () => {
    expect("SILICE_DATOS" in armarEntorno({ PATH: "p" }, "10.0.0.2")).toBe(false);
  });
});

describe("ordenServidor", () => {
  test("liga solo a la IP LAN y a 127.0.0.1, nunca a 0.0.0.0", () => {
    const orden = ordenServidor("192.168.1.20", 8020);
    expect(orden.slice(-2)).toEqual(["192.168.1.20", "8020"]);
    expect(orden[0]).toBe("-c");
    expect(orden[1]).toContain("api.main:app");
    expect(orden[1]).toContain("127.0.0.1");
    expect(orden[1]).not.toContain("0.0.0.0");
  });
});

describe("rutaPython", () => {
  test("sin entorno virtual activo falla claro", () => {
    expect(() => rutaPython("", "win32")).toThrow(/entorno virtual/);
    expect(() => rutaPython(undefined, "linux")).toThrow(/VIRTUAL_ENV/);
  });
  test("segun la plataforma", () => {
    expect(rutaPython("C:\\x\\.venv", "win32")).toMatch(/Scripts[\\/]python\.exe$/);
    expect(rutaPython("/x/.venv", "linux")).toMatch(/bin[\\/]python$/);
  });
});

describe("necesitaCompilar", () => {
  test("sin dist, compila", () => {
    expect(necesitaCompilar({ fuentes: 100, dist: null })).toBe(true);
  });
  test("fuentes mas nuevas que dist, compila", () => {
    expect(necesitaCompilar({ fuentes: 200, dist: 100 })).toBe(true);
  });
  test("dist al dia no compila (igual o posterior)", () => {
    expect(necesitaCompilar({ fuentes: 100, dist: 100 })).toBe(false);
    expect(necesitaCompilar({ fuentes: 100, dist: 300 })).toBe(false);
  });
  test("forzar compila siempre", () => {
    expect(necesitaCompilar({ fuentes: 1, dist: 300, forzar: true })).toBe(true);
  });
});

describe("cuentasDePrueba", () => {
  test("intersecta con los logins conocidos, ordenados y sin mayusculas", () => {
    expect(cuentasDePrueba(["Tomas", "maria", "admin", "ana"])).toEqual(["admin", "ana", "tomas"]);
  });
  test("sin coincidencias, vacio", () => {
    expect(cuentasDePrueba(["maria"])).toEqual([]);
    expect(cuentasDePrueba([])).toEqual([]);
  });
});

describe("parsearArgumentos", () => {
  test("por omision", () => {
    expect(parsearArgumentos([])).toEqual({ ip: undefined, puerto: 8000, abrir: false, compilar: false, ayuda: false });
  });
  test("opciones", () => {
    const a = parsearArgumentos(["--ip", "10.0.0.2", "--puerto", "8020", "--abrir", "--compilar"]);
    expect(a).toEqual({ ip: "10.0.0.2", puerto: 8020, abrir: true, compilar: true, ayuda: false });
  });
  test("puerto invalido", () => {
    expect(() => parsearArgumentos(["--puerto", "0"])).toThrow(/puerto/);
    expect(() => parsearArgumentos(["--puerto", "abc"])).toThrow(/puerto/);
    expect(() => parsearArgumentos(["--puerto", "70000"])).toThrow(/puerto/);
  });
  test("opcion desconocida", () => {
    expect(() => parsearArgumentos(["--host"])).toThrow();
  });
});

describe("mensajeInicio", () => {
  const base = { ip: "192.168.1.20", puerto: 8020, cuentas: [], plataforma: "win32", ocupados: [] };
  test("da las dos URLs, el puerto y como detener", () => {
    const m = mensajeInicio(base);
    expect(m).toContain("http://127.0.0.1:8020/app/");
    expect(m).toContain("http://192.168.1.20:8020/app/");
    expect(m).toMatch(/Ctrl\+C/);
    expect(m).toContain("8020");
  });
  test("aviso de seguridad siempre; cuentas de prueba solo si existen", () => {
    expect(mensajeInicio(base)).toMatch(/acepta conexiones de la red local/);
    expect(mensajeInicio(base)).not.toMatch(/contrasena conocida/);
    const m = mensajeInicio({ ...base, cuentas: ["admin", "ana"] });
    expect(m).toMatch(/cuentas de prueba/);
    expect(m).toContain("admin, ana");
    expect(m).toMatch(/contrasena conocida/);
  });
  test("lo sensible solo desde este equipo", () => {
    expect(mensajeInicio(base)).toMatch(/solo desde este equipo/i);
  });
  test("regla de firewall en Windows, con el puerto, limitada a la subred; no en otros", () => {
    const w = mensajeInicio(base);
    expect(w).toMatch(/netsh advfirewall firewall add rule/);
    expect(w).toContain("localport=8020");
    expect(w).toContain("remoteip=localsubnet");
    expect(mensajeInicio({ ...base, plataforma: "linux" })).not.toMatch(/netsh/);
  });
  test("avisa de los puertos ocupados", () => {
    expect(mensajeInicio({ ...base, puerto: 8001, ocupados: [8000] })).toMatch(/8000.*ocupado/);
  });
});
