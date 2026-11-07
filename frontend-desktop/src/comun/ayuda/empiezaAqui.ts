import { rutaDeCuenta, rutaOPendientes } from "../../marco/espacios";
import { rutaDeTema } from "./temas";

// «Empieza aquí» (F7, tarea A4; especificación 2026-10-21 de la bienvenida, §7.6): lo primero que hace cada papel en una
// instalación o una carpeta que se estrena. Se deriva de los datos (las acciones de la cuenta, cuántas obras ve y cuántas
// cuentas activas hay) y no guarda nada en el navegador (RT-9): desaparece solo cuando ya no hace falta. La Vista general
// muestra los pasos que le tocan a la cuenta; la Ayuda los muestra todos, con la primera vez delante.

export type PasoId = "cuentas" | "empresa" | "obra" | "presupuesto" | "aprobacion" | "auditar" | "dictamen";
export type Papel = "administra" | "arma" | "revisa";

export interface PasoDeEmpiezaAqui {
  papel: Papel;
  titulo: string;
  texto: string;
  // `accion`: el enlace solo se ofrece a quien puede usar su destino (no se promete lo que no se puede hacer).
  enlace?: { texto: string; ruta: string; accion?: string };
}

export const PASOS_DE_EMPIEZA_AQUI: Readonly<Record<PasoId, PasoDeEmpiezaAqui>> = {
  cuentas: {
    papel: "administra",
    titulo: "Cree las cuentas de las personas",
    texto:
      "En «Crear una cuenta», escriba el «Usuario», el «Nombre de la persona», lo que puede hacer y una «Contraseña temporal», y pulse «Crear la cuenta». La persona la cambia al entrar. La cuenta del administrador solo arma presupuestos si al crearla marcó «Usaré esta cuenta también para armar presupuestos»; si no, créele la cuenta a quien arma.",
    enlace: { texto: "Ir a Cuentas y permisos", ruta: rutaDeCuenta("cuentas"), accion: "administrar_cuentas" },
  },
  empresa: {
    papel: "administra",
    titulo: "Ponga los datos de la empresa",
    texto:
      "En «La empresa», escriba el «Nombre de la empresa», el «RIF» y la «Ciudad» y pulse «Guardar la empresa». Con «Generar la clave de firma», los paquetes que se entreguen salen firmados.",
    enlace: { texto: "Ir a Empresa y tema", ruta: rutaDeCuenta("empresa"), accion: "administrar_empresa" },
  },
  obra: {
    papel: "arma",
    titulo: "Cree la obra",
    texto: "Pulse «Nueva obra» (en la barra de la izquierda o en «Cartera por moneda»), escriba el «Nombre de la obra», revise la «Moneda» y pulse «Crear obra».",
  },
  presupuesto: {
    papel: "arma",
    titulo: "Arme el presupuesto",
    texto: "En la sección «Presupuesto» de la obra, agregue las partidas con «Agregar partida» y guarde la primera versión con «Guardar primera versión…».",
    enlace: { texto: "Guía «Montar un presupuesto»", ruta: rutaDeTema("guia-presupuesto") },
  },
  aprobacion: {
    papel: "arma",
    titulo: "Envíelo a aprobación",
    texto: "Cuando la versión esté lista, la franja del Presupuesto ofrece «Enviar a aprobación…»; quien revisa da su dictamen en «Aprobaciones».",
    enlace: { texto: "Guía «Enviarlo a aprobación»", ruta: rutaDeTema("guia-aprobacion") },
  },
  auditar: {
    papel: "revisa",
    titulo: "Audite un libro",
    texto: "En «Auditar un presupuesto», suelte el Excel de un presupuesto: Sílice recalcula cada partida y le dice lo que no cuadra.",
    enlace: { texto: "Ir a Auditar un presupuesto", ruta: rutaOPendientes("auditoria"), accion: "leer_proyecto" },
  },
  dictamen: {
    papel: "revisa",
    titulo: "Dé su dictamen",
    texto: "Cuando alguien envíe una versión a aprobación, ábrala en la sección «Aprobaciones» de su obra y registre su dictamen.",
    enlace: { texto: "Guía «Enviarlo a aprobación»", ruta: rutaDeTema("guia-aprobacion") },
  },
};

// El orden de la tabla: primero lo de quien administra, después lo de quien arma y, al final, lo de quien solo revisa.
const ORDEN: readonly PasoId[] = ["cuentas", "empresa", "obra", "presupuesto", "aprobacion", "auditar", "dictamen"];

export interface DatosDeEmpiezaAqui {
  acciones: readonly string[];
  // Cuántas obras ve la cuenta (null: no se sabe, porque no las lee o la lectura falló).
  obras: number | null;
  // Cuántas cuentas activas tiene la instalación (null: no se sabe).
  cuentasActivas: number | null;
}

// Quien administra estrena la instalación mientras su cuenta sea la única activa y no haya ninguna obra (con obras, la
// instalación ya se usa y el bloque sobra aunque nadie más tenga cuenta); quien arma o revisa estrena mientras no
// vea ninguna obra. Lo que no se sabe (null) no abre ningún paso: no se inventa una primera vez. Quien arma y revisa a la
// vez ve los pasos de quien arma (los de quien revisa son para quien no arma).
export function pasosDeEmpiezaAqui({ acciones, obras, cuentasActivas }: DatosDeEmpiezaAqui): PasoId[] {
  const papeles = new Set<Papel>();
  if (acciones.includes("administrar_cuentas") && cuentasActivas === 1 && !(obras !== null && obras > 0)) papeles.add("administra");
  const arma = acciones.includes("editar_hoja");
  if (arma && obras === 0) papeles.add("arma");
  if (!arma && acciones.includes("leer_proyecto") && obras === 0) papeles.add("revisa");
  return ORDEN.filter((id) => papeles.has(PASOS_DE_EMPIEZA_AQUI[id].papel));
}

// La primera vez de una instalación (diseño de la bienvenida, §3): antes de que exista ninguna cuenta. La bienvenida ya
// lo hace en la interfaz; aquí se cuenta para quien vuelva a leerlo o se lo explique a otra persona.
export const PRIMERA_VEZ = {
  titulo: "La primera vez",
  parrafos: [
    "Una instalación nueva no tiene cuentas: en lugar de «Entrar», Sílice abre «Bienvenida a Sílice». Busque el código de instalación (20 caracteres en grupos de cuatro) en el archivo codigo_instalacion.txt de la carpeta de datos de Sílice o en la ventana del servidor.",
    "Escriba el «Código de instalación», «Su nombre», el «Usuario» y la «Contraseña» dos veces, y pulse «Crear la cuenta y entrar». Esa es la cuenta del administrador, y el código se borra al usarse. Si esa cuenta también va a armar presupuestos, marque «Usaré esta cuenta también para armar presupuestos».",
    "Si más adelante se pierde el acceso del administrador, en «Entrar» pulse «Perdí el acceso de administrador» y siga los pasos con un código de restablecimiento.",
  ],
} as const;

export const TITULO_DEL_PAPEL: Readonly<Record<Papel, string>> = {
  administra: "Si administra Sílice",
  arma: "Si arma presupuestos",
  revisa: "Si revisa",
};
