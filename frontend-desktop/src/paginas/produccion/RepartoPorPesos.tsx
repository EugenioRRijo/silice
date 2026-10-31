import { Checkbox } from "@carbon/react";
import { useEffect, useState } from "react";
import type { JSX } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { recetaVigente } from "../../api/produccionPlanta";
import type { Producido } from "../../api/produccionPlanta";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { leerCifra } from "../../indicadores/cifraEscrita";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { porcentajeAFraccion, sumaDePorcentajes, ultimoDiaDelMes } from "./logicaMezcla";
import { mensajeDePlanta } from "./logicaPlanta";

// Lo que la pantalla de arriba necesita saber: si hay reparto por pesos, si está listo para mandarse y los pesos como
// fracciones con punto.
export interface Reparto {
  activo: boolean;
  valido: boolean;
  pesos: Record<string, string> | null;
}
export const SIN_REPARTO: Reparto = { activo: false, valido: true, pesos: null };

interface Props {
  periodo: string;
  producido: readonly Producido[];
  alCambiar: (reparto: Reparto) => void;
  alExpirar: () => void;
}

type Agregados = { estado: "cargando" } | { estado: "listo"; codigos: string[] } | { estado: "error"; error: unknown };
const CARGANDO: Agregados = { estado: "cargando" }; // una sola referencia: el efecto de abajo depende de ella

// Producir un agregado es producir lo que no tiene receta: se pregunta, para cada código producido en el mes, si tiene
// receta vigente al cierre (404 = es agregado). Solo se pregunta cuando la persona enciende el reparto.
function useAgregados(activo: boolean, periodo: string, producido: readonly Producido[], alExpirar: () => void): Agregados {
  const [resultado, setResultado] = useState<{ clave: string; agregados: Agregados } | null>(null);
  const clave = `${periodo}|${producido.map((p) => p.codigo).join(",")}`;
  useEffect(() => {
    if (!activo) return;
    const control = new AbortController();
    const dia = ultimoDiaDelMes(periodo);
    Promise.all(
      producido.map(async (p): Promise<string | null> => {
        try {
          await recetaVigente(p.codigo, dia, control.signal);
          return null;
        } catch (razon) {
          if (razon instanceof ErrorDeApi && razon.estado === 404) return p.codigo;
          throw razon;
        }
      }),
    ).then(
      (hallados) => setResultado({ clave, agregados: { estado: "listo", codigos: hallados.filter((c): c is string => c !== null) } }),
      (error: unknown) => {
        if (control.signal.aborted) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setResultado({ clave, agregados: { estado: "error", error } });
      },
    );
    return () => control.abort();
  }, [activo, clave, periodo, producido, alExpirar]);
  return resultado && resultado.clave === clave ? resultado.agregados : CARGANDO;
}

// «Repartir la cantera por pesos»: apagado, la cantera se reparte por tonelada entre los agregados (valor por defecto del
// servidor). Encendido, hay un porcentaje por cada agregado producido y Calcular exige que sumen 100 %. La pantalla solo
// manda cada porcentaje como fracción («75» -> «0.75»); el reparto lo hace el servidor.
export function RepartoPorPesos({ periodo, producido, alCambiar, alExpirar }: Props): JSX.Element {
  const [activo, setActivo] = useState(false);
  const [escritos, setEscritos] = useState<Record<string, string>>({});
  const agregados = useAgregados(activo, periodo, producido, alExpirar);
  const codigos = agregados.estado === "listo" ? agregados.codigos : [];

  const lecturas = codigos.map((c) => ({ codigo: c, texto: escritos[c] ?? "", lectura: leerCifra(escritos[c] ?? "") }));
  const mal = (l: (typeof lecturas)[number]) => l.texto.trim() !== "" && "error" in l.lectura;
  const completos = lecturas.length > 0 && lecturas.every((l) => l.texto.trim() !== "" && "valor" in l.lectura && !l.lectura.valor.startsWith("-"));
  const suma = completos ? sumaDePorcentajes(lecturas.map((l) => ("valor" in l.lectura ? l.lectura.valor : "0"))) : null;
  const valido = activo && suma === "100";

  useEffect(() => {
    if (!activo) alCambiar(SIN_REPARTO);
    else {
      const pesos = valido ? Object.fromEntries(lecturas.map((l) => [l.codigo, porcentajeAFraccion("valor" in l.lectura ? l.lectura.valor : "0")])) : null;
      alCambiar({ activo: true, valido, pesos });
    }
    // `lecturas` se rehace en cada vuelta: lo que cuenta es lo escrito y los agregados.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activo, valido, escritos, agregados]);

  return (
    <div className="planta-reparto">
      <Checkbox
        id="reparto-pesos"
        labelText="Repartir la cantera por pesos"
        helperText="Apagado, la cantera se reparte por tonelada producida: el mismo costo por tonelada para todos los agregados."
        checked={activo}
        onChange={(_, { checked }) => setActivo(checked)}
      />
      {activo && agregados.estado === "cargando" && <p className="planta-nota cds--type-body-compact-01">Buscando los agregados producidos…</p>}
      {activo && agregados.estado === "error" && <AvisoError error={mensajeDePlanta(agregados.error)} titulo="No se pudieron identificar los agregados" />}
      {activo && agregados.estado === "listo" && codigos.length === 0 && (
        <p className="planta-nota cds--type-body-compact-01">En este mes no se produjo ningún agregado: no hay nada que repartir.</p>
      )}
      {activo && codigos.length > 0 && (
        <div className="planta-barra">
          {lecturas.map((l) => (
            <CampoTexto
              key={l.codigo}
              id={`reparto-${l.codigo}`}
              labelText={`Porcentaje de ${l.codigo}`}
              autoComplete="off"
              inputMode="decimal"
              value={l.texto}
              invalid={mal(l) || (l.texto.trim() !== "" && "valor" in l.lectura && l.lectura.valor.startsWith("-"))}
              invalidText={"error" in l.lectura ? l.lectura.error : "El porcentaje no puede ser negativo."}
              onChange={(e) => setEscritos((antes) => ({ ...antes, [l.codigo]: e.target.value }))}
            />
          ))}
        </div>
      )}
      {activo && codigos.length > 0 && !completos && !lecturas.some(mal) && (
        <p className="planta-nota cds--type-body-compact-01">Escriba el porcentaje de cada agregado; deben sumar 100 %.</p>
      )}
      {activo && suma !== null && suma !== "100" && (
        <p className="planta-nota cds--type-body-compact-01" role="status">
          Los porcentajes suman {formatoEsVe(suma)} % y deben sumar 100 %.
        </p>
      )}
    </div>
  );
}
