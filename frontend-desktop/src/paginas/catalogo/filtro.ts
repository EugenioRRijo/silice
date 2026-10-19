// Busqueda del catalogo en el navegador: ignora tildes y mayusculas, y exige que aparezca cada palabra.

export function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

export function coincide(campos: ReadonlyArray<string | null>, busqueda: string): boolean {
  const palabras = normalizar(busqueda).split(/\s+/).filter(Boolean);
  if (palabras.length === 0) return true;
  const pajar = campos.map((c) => normalizar(c ?? "")).join(" ");
  return palabras.every((p) => pajar.includes(p));
}
