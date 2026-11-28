// El responsable que guarda la API es «Nombre <login>» (RF-82, `seguridad/cuentas.py::texto_responsable`), a veces con
// « (tras restablecimiento)» al final. En la interfaz se dice solo el nombre; sin login, el texto tal cual.
export function nombreDeResponsable(responsable: string): string {
  const corte = responsable.indexOf(" <");
  return corte > 0 ? responsable.slice(0, corte) : responsable;
}

// Nombre y usuario de un responsable («Ana Pérez <ana>»), para filtrar por persona y enlazar a su actividad (C10b).
export interface PersonaExtraida {
  clave: string;
  nombre: string;
  usuario: string | null;
}

const LOGIN = /<([^<>]+)>/;

// Extrae el nombre visible y el usuario (login) de un texto «Nombre <login>» o de campos separados.
// Si no trae usuario (p. ej. «api (clave de API)» o nulo), `usuario` es null.
export function extraerPersona(dato: string | null | undefined, usuarioExplicito?: string | null): PersonaExtraida | null {
  const texto = (dato ?? "").trim();
  const explicito = (usuarioExplicito ?? "").trim();
  if (texto === "") {
    return explicito === "" ? null : extraerPersona(explicito);
  }
  const hallado = LOGIN.exec(texto);
  if (hallado !== null) {
    const usuario = hallado[1]!.trim();
    const nombre = texto.startsWith("<") ? usuario : nombreDeResponsable(texto).trim() || usuario;
    if (usuario !== "") {
      return { clave: `u:${usuario.toLowerCase()}`, nombre, usuario };
    }
    return { clave: `t:${nombre.toLowerCase()}`, nombre, usuario: null };
  }
  if (explicito !== "") {
    return { clave: `u:${explicito.toLowerCase()}`, nombre: texto, usuario: explicito };
  }
  return { clave: `t:${texto.toLowerCase()}`, nombre: texto, usuario: null };
}
