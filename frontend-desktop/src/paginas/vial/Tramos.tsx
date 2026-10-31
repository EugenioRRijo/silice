import { InlineNotification, Select, SelectItem } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { importarTramos } from "../../api/vial";
import { AvisoError } from "../../comun/AvisoError";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { rutaDeVersiones, versionesOfrecidas } from "../hoja/logica";
import type { VersionesRespuesta } from "../hoja/logica";
import { useCarga } from "../inicio/useCarga";
import { AvisoConFoco } from "../produccion/AvisoConFoco";
import { TramoConCantidades } from "./TramoConCantidades";
import { useTramos } from "./useTramos";
import "./vial.scss";

const SIN_OBRA = "Abra una obra para ver o importar sus tramos.";
const SIN_VERSIONES = "Esta obra aún no tiene versiones guardadas. Guarde una en la Hoja para cargar sus tramos.";
const SIN_TRAMOS = "Esta versión aún no tiene tramos. Importe el archivo de la vía.";

// «Tramos de la vía»: los tramos de una versión con sus cantidades de obra (m2, m3, l, t, t·km y m) y la importación del
// archivo CSV de la vía. La importación es todo o nada: si una fila está mal, el servidor dice cuál y no se guarda nada.
// La pantalla no calcula: lee lo que manda el servidor con coma decimal y punto de miles.
export default function Tramos() {
  const { nombreProyecto, alExpirar } = useAplicacion();
  const nombre = nombreProyecto ?? null;
  const versiones = useCarga<VersionesRespuesta>(nombre === null ? null : rutaDeVersiones(nombre), alExpirar);
  const ofrecidas = versiones.estado === "listo" ? versionesOfrecidas(versiones.datos.versiones) : [];
  const [elegida, setElegida] = useState<string | null>(null);
  const porOmision = versiones.estado === "listo" ? (versiones.datos.por_omision ?? ofrecidas.at(-1)?.codigo ?? null) : null;
  const version = elegida !== null && ofrecidas.some((v) => v.codigo === elegida) ? elegida : porOmision;
  const { carga, reemplazar } = useTramos(nombre, version, alExpirar);

  const [importando, setImportando] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const cajaDelError = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (error !== null) cajaDelError.current?.focus();
  }, [error]);

  async function importar(archivo: File) {
    if (nombre === null || version === null) return;
    setError(null);
    setAviso(null);
    setImportando(true);
    try {
      const datos = await importarTramos(nombre, version, archivo);
      reemplazar(datos);
      const n = datos.tramos.length;
      setAviso(`Tramos importados: ${n} ${n === 1 ? "tramo" : "tramos"} de ${archivo.name}.`);
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setError(razon);
    } finally {
      setImportando(false);
    }
  }

  return (
    <div className="vial silice-pagina">
      <h1 className="cds--type-heading-04">Tramos de la vía</h1>
      <p className="vial-nota cds--type-body-compact-01">
        Los tramos de la vía de cada versión, con las cantidades de obra que salen de ellos. Se cargan desde un archivo CSV.
      </p>
      {nombre === null && <EstadoVacio titulo={SIN_OBRA} />}
      {versiones.estado === "error" && <AvisoError error={versiones.error} titulo="No se pudieron leer las versiones" />}
      {versiones.estado === "listo" && ofrecidas.length === 0 && <EstadoVacio titulo={SIN_VERSIONES} />}
      {version !== null && (
        <>
          <Select id="tramos-version" labelText="Versión" value={version} onChange={(e) => setElegida(e.target.value)}>
            {ofrecidas.map((v) => (
              <SelectItem key={v.codigo} value={v.codigo} text={v.codigo} />
            ))}
          </Select>
          {carga.estado === "error" && <AvisoError error={carga.error} titulo="No se pudieron leer los tramos" />}
          {carga.estado === "listo" && (
            <>
              {carga.datos.bloqueo !== null && (
                <InlineNotification kind="info" role="status" lowContrast hideCloseButton title={carga.datos.bloqueo} />
              )}
              {carga.datos.editable && (
                <SubidaArchivo
                  id="tramos-archivo"
                  etiqueta="Suelte aquí el archivo .csv de la vía, o haga clic para elegirlo"
                  extensiones={[".csv"]}
                  alElegir={(a) => void importar(a)}
                  deshabilitada={importando}
                />
              )}
              <AvisoConFoco aviso={aviso} alCerrar={() => setAviso(null)} />
              {error !== null && (
                <div ref={cajaDelError} tabIndex={-1}>
                  <AvisoError error={error} titulo="No se importó ningún tramo" />
                </div>
              )}
              {carga.datos.heredados_de !== null && (
                <p className="vial-nota cds--type-body-compact-01">{`Tramos heredados de la versión ${carga.datos.heredados_de}`}</p>
              )}
              {carga.datos.guardado !== null && (
                <p className="vial-nota cds--type-body-compact-01">
                  {`Guardado por ${carga.datos.guardado.usuario} el ${fechaEsVe(carga.datos.guardado.fecha_hora)} · ${carga.datos.guardado.fuente}`}
                </p>
              )}
              {carga.datos.tramos.length === 0 && carga.datos.editable && <EstadoVacio titulo={SIN_TRAMOS} />}
              {carga.datos.tramos.map((t) => (
                <TramoConCantidades key={t.id} tramo={t} cantidades={carga.datos.cantidades} />
              ))}
            </>
          )}
        </>
      )}
    </div>
  );
}
