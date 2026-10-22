import { Button, Select, SelectItem } from "@carbon/react";
import { CampoTexto } from "../../comun/CampoTexto";
import { useEffect, useRef, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { referencia } from "./cliente";
import type { FilaReferencia } from "./cliente";
import { TITULOS } from "./tablas";
import type { Fila, TipoTabla } from "./tablas";

interface Props {
  tipo: TipoTabla;
  alUsar: (fila: Fila) => void;
  alExpirar: () => void;
}

const RETARDO_MS = 300;

// Busca en la referencia MaPreX y entrega una fila ya completada. La `ref_maprex` de la fila elegida queda visible:
// es la procedencia del precio, y sin ella el numero deja de ser trazable.
export function BuscadorReferencia({ tipo, alUsar, alExpirar }: Props) {
  const [texto, setTexto] = useState("");
  const [resultados, setResultados] = useState<FilaReferencia[] | null>(null);
  const [elegido, setElegido] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const turno = useRef(0);

  useEffect(() => {
    const q = texto.trim();
    const mio = ++turno.current;
    if (!q) return;
    const espera = setTimeout(() => {
      referencia(tipo, q)
        .then((filas) => {
          if (mio !== turno.current) return; // respuesta de una busqueda vieja
          setError(null);
          setResultados(filas);
          setElegido(0);
        })
        .catch((e: unknown) => {
          if (mio !== turno.current) return;
          if (e instanceof ErrorDeApi && e.estado === 401) {
            alExpirar();
            return;
          }
          setError(e);
        });
    }, RETARDO_MS);
    return () => clearTimeout(espera);
  }, [texto, tipo, alExpirar]);

  const cambiarTexto = (valor: string) => {
    setTexto(valor);
    if (!valor.trim()) {
      setResultados(null);
      setError(null);
    }
  };

  const actual = resultados?.[elegido];
  return (
    <div className="silice-componer__buscador">
      <CampoTexto
        id={`buscar-${tipo}`}
        size="sm"
        labelText={`Buscar en la referencia MaPreX (${TITULOS[tipo].toLowerCase()})`}
        value={texto}
        onChange={(e) => cambiarTexto(e.target.value)}
      />
      <div className="silice-componer__resultado">
        <AvisoError error={error} titulo="No se pudo buscar en la referencia" />
        {resultados && resultados.length === 0 && (
          <p className="cds--type-body-compact-01">Sin coincidencias en la referencia MaPreX.</p>
        )}
        {resultados && resultados.length > 0 && actual && (
          <>
            <Select
              id={`resultado-${tipo}`}
              size="sm"
              labelText="Resultado"
              value={String(elegido)}
              onChange={(e) => setElegido(Number(e.target.value))}
            >
              {resultados.map((r, i) => (
                <SelectItem key={`${r.ref_maprex}-${i}`} value={String(i)} text={r.etiqueta} />
              ))}
            </Select>
            <p className="cds--type-label-01">Referencia MaPreX: {actual.ref_maprex}</p>
            <Button kind="tertiary" size="sm" onClick={() => alUsar(actual.fila)}>
              Usar esta fila
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
