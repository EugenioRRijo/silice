// Una cifra con su rotulo (resumen del tablero, resultado de una importacion). El rotulo y la cifra van juntos en el
// mismo bloque para que un lector de pantalla los diga seguidos.
export function Dato({ rotulo, valor }: { rotulo: string; valor: number }) {
  return (
    <div className="existencias-dato">
      <span className="existencias-dato__rotulo cds--type-label-01">{rotulo}</span>
      <span className="existencias-dato__valor cds--type-heading-03 silice-cifra">{valor}</span>
    </div>
  );
}
