// Cómo se nombra, en español llano, la clave de fila que guarda el servidor («esp_puntos:P1», «AF-LLAVE|esp_fuentes:F1#2»).
// Lo comparten la Hoja, Versiones y Revisar (por eso vive en `comun/`).

const NOMBRE_DE_PREFIJO: Record<string, string> = {
  esp_origenes: "Origen",
  esp_ambientes: "Ambiente",
  esp_fuentes: "Fuente",
  esp_puntos: "Punto",
  esp_tramos: "Tramo",
  esp_segmentos: "Segmento",
  esp_circuitos: "Circuito",
  esp_recorridos: "Recorrido",
  esp_sobrescrituras: "Sobrescritura",
};

// Un origen suelto («esp_puntos:P1»; el de un segmento lleva además «|coordenadas», que no se muestran).
function rotuloDeFila(texto: string): string {
  const m = /^(esp_[a-z_]+):([^|]+)/.exec(texto);
  // Un prefijo esp_* sin nombre nunca llega a pantalla como código: cae a «Origen X».
  return m ? `${NOMBRE_DE_PREFIJO[m[1]!] ?? "Origen"} ${m[2]}` : texto;
}

// La clave de un renglón o de un registro: «partida|origen;origen;…#2». Los orígenes van unidos por «;»; los segmentos
// llevan «|» con sus coordenadas y un «;+n» final con los que no caben.
export function partirClave(clave: string): { partida: string | null; origenes: string[]; mas: string; repetido: string } {
  const rep = /^(.*)#(\d+)$/.exec(clave);
  const base = rep ? rep[1]! : clave;
  // Una clave sin partida que empieza por un origen de segmento («esp_segmentos:F1|coordenadas») no tiene partida.
  const barra = /^esp_[a-z_]+:/.test(base) ? -1 : base.indexOf("|");
  const resto = barra < 0 ? base : base.slice(barra + 1);
  const origenes: string[] = [];
  let mas = "";
  for (const trozo of resto.split(";")) {
    const m = /^\+(\d+)$/.exec(trozo);
    if (m) mas = m[1]!;
    else if (trozo !== "") origenes.push(trozo);
  }
  return { partida: barra < 0 ? null : base.slice(0, barra), origenes, mas, repetido: rep ? rep[2]! : "" };
}

// La clave de fila del servidor («esp_puntos:P1», «AF-LLAVE|esp_fuentes:F1;esp_puntos:P1#2») como la nombra la persona.
export function rotuloDeOrigen(origen: string): string {
  const { partida, origenes, mas, repetido } = partirClave(origen);
  const nombres = origenes.map(rotuloDeFila);
  if (partida !== null && partida !== "") nombres.unshift(partida);
  let texto = nombres.join(", ");
  if (mas !== "") texto += ` y ${mas} más`;
  return repetido ? `${texto} (${repetido})` : texto;
}
