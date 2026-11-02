// El responsable que guarda la API es «Nombre <login>» (RF-82, `seguridad/cuentas.py::texto_responsable`), a veces con
// « (tras restablecimiento)» al final. En la interfaz se dice solo el nombre; sin login, el texto tal cual.
export function nombreDeResponsable(responsable: string): string {
  const corte = responsable.indexOf(" <");
  return corte > 0 ? responsable.slice(0, corte) : responsable;
}
