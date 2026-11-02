import { useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { filasDeAccesos, notaAccesos } from "./logica";
import type { AccesosRespuesta } from "./logica";

// Pestana «Accesos»: los ultimos eventos de acceso. Solo lectura (la API no ofrece otro metodo).
export default function Accesos() {
  const { alExpirar } = useAplicacion();
  const [datos, setDatos] = useState<AccesosRespuesta | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let vigente = true;
    pedir<AccesosRespuesta>("/v1/accesos").then(
      (r) => {
        if (vigente) setDatos(r);
      },
      (e: unknown) => {
        if (!vigente) return;
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
        setError(e);
      },
    );
    return () => {
      vigente = false;
    };
  }, [alExpirar]);

  return (
    <section className="silice-adm__tabla" aria-labelledby="adm-accesos">
      <h2 id="adm-accesos" className="cds--type-heading-compact-02">
        Accesos
      </h2>
      <p className="silice-adm__nota cds--type-body-compact-01">{notaAccesos(datos?.maximo ?? null)}</p>
      <AvisoError error={error} titulo="No se pudo leer el registro de accesos" />
      {error === null && (
        <TablaDensa
          etiqueta="Eventos de acceso"
          cargando={datos === null}
          columnas={[
            // Ya llegan del mas nuevo al mas viejo: la fecha legible no se ordena como texto.
            { clave: "fecha", titulo: "Fecha", ordenable: false },
            { clave: "evento", titulo: "Evento" },
            { clave: "usuario", titulo: "Usuario" },
            { clave: "ip", titulo: "IP" },
            { clave: "detalle", titulo: "Detalle" },
          ]}
          filas={filasDeAccesos(datos?.eventos ?? [])}
          vacio={{ titulo: "Todavía no hay eventos de acceso." }}
        />
      )}
    </section>
  );
}
