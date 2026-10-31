import { Button } from "@carbon/react";
import { useEffect, useState } from "react";
import type { JSX } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { calculoGuardado, calculosDelPeriodo } from "../../api/produccionPlanta";
import type { CalculoDeCosto, ResumenDeCalculo } from "../../api/produccionPlanta";
import { AvisoError } from "../../comun/AvisoError";
import { fechaEsVe, nombreDelMes } from "./logica";
import { mensajeDePlanta } from "./logicaPlanta";

interface Props {
  periodo: string;
  // Cambia cuando algo pudo cambiar la lista (se calculó, se publicó, hubo un 409): vuelve a leerla.
  version: number;
  alAbrir: (calculo: CalculoDeCosto) => void;
  alExpirar: () => void;
}

type Lista = { periodo: string; version: number; ok: true; datos: ResumenDeCalculo[] } | { periodo: string; version: number; ok: false; error: unknown };

// Los cálculos que ya se guardaron del mes, del más reciente al más viejo, con su fecha y si se publicaron. Abrir uno trae
// el cálculo tal como se guardó (con su huella verificada por el servidor); nada se recalcula aquí.
export function CalculosAnteriores({ periodo, version, alAbrir, alExpirar }: Props): JSX.Element {
  const [lista, setLista] = useState<Lista | null>(null);
  const [errorAlAbrir, setErrorAlAbrir] = useState<unknown>(null);
  const [abriendo, setAbriendo] = useState<number | null>(null);

  useEffect(() => {
    const control = new AbortController();
    calculosDelPeriodo(periodo, control.signal).then(
      (datos) => setLista({ periodo, version, ok: true, datos }),
      (error: unknown) => {
        if (control.signal.aborted) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setLista({ periodo, version, ok: false, error });
      },
    );
    return () => control.abort();
  }, [periodo, version, alExpirar]);

  async function abrir(id: number) {
    setErrorAlAbrir(null);
    setAbriendo(id);
    try {
      alAbrir(await calculoGuardado(id));
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setErrorAlAbrir(razon);
    } finally {
      setAbriendo(null);
    }
  }

  const actual = lista && lista.periodo === periodo ? lista : null;
  return (
    <section aria-label="Cálculos anteriores" className="planta-anteriores">
      <h2 className="cds--type-heading-compact-02">Cálculos de {nombreDelMes(periodo)}</h2>
      {actual && !actual.ok && <AvisoError error={mensajeDePlanta(actual.error)} titulo="No se pudieron leer los cálculos anteriores" />}
      {actual?.ok && actual.datos.length === 0 && <p className="planta-nota cds--type-body-compact-01">Todavía no se calculó este mes.</p>}
      {actual?.ok && actual.datos.length > 0 && (
        <ul className="planta-anteriores__lista cds--type-body-compact-01" aria-label={`Cálculos anteriores de ${nombreDelMes(periodo)}`}>
          {actual.datos.map((c) => (
            <li key={c.id}>
              <span>
                Cálculo n.º {c.id} · {fechaEsVe(c.registrado.slice(0, 10))} · {c.moneda} · por {c.usuario} ·{" "}
                {c.publicado ? `Publicado en la lista n.º ${c.publicado.lista_id}` : "Sin publicar"}
              </span>
              <Button kind="tertiary" size="sm" disabled={abriendo !== null} onClick={() => void abrir(c.id)}>
                {`Abrir el cálculo n.º ${c.id}`}
              </Button>
            </li>
          ))}
        </ul>
      )}
      <AvisoError error={errorAlAbrir === null ? null : mensajeDePlanta(errorAlAbrir)} titulo="No se pudo abrir el cálculo" />
    </section>
  );
}
