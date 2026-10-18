import { Button, Form, InlineNotification, PasswordInput, Select, SelectItem, TextInput } from "@carbon/react";
import { Download } from "@carbon/icons-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedirBinario } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { guardarBlob } from "../../comun/DescargaArchivo";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../inicio/useCarga";
import type { Carga } from "../inicio/useCarga";
import "./entregar.scss";

interface ProyectoDelCaso {
  codigo: string;
  nombre: string;
}

interface VersionEntregable {
  codigo: string;
  moneda: string;
}

interface ResumenEntrega {
  proyecto: string;
  version: string;
  moneda: string;
  total: string;
  total_texto: string;
  hallazgos_total: number;
  hallazgos_por_severidad: Record<string, number>;
  cadena_integra: boolean;
  mensaje_de_cadena: string;
  empresa: string | null;
  firma_disponible: boolean;
  viaja_con: string[];
}

interface PaqueteListo {
  blob: Blob;
  nombre: string;
  sha256: string;
  firmado: boolean;
}

// Los hallazgos como los escribe la pantalla clasica: «2 advertencia, 1 error» (la API ya los manda en orden).
function textoDeHallazgos(porSeveridad: Record<string, number>): string {
  return Object.entries(porSeveridad)
    .map(([severidad, n]) => `${n} ${severidad.toLowerCase()}`)
    .join(", ");
}

// UC-22 (spec S3 §8.2; RF-85): el rol «arma» elige proyecto y version, ve lo que va a viajar y descarga el .silice.
// La contraseña de la clave de firma vive solo en este formulario: se vacia al enviar, no se guarda en ningun sitio
// y la API ni la registra ni la devuelve. Firmar solo se puede desde el propio equipo (la API lo dice si no).
export default function PaginaEntregar() {
  const { alExpirar, proyecto: codigoAbierto } = useAplicacion();
  const proyectos = useCarga<ProyectoDelCaso[]>("/v1/proyectos", alExpirar);

  return (
    <div className="silice-entregar">
      <h1 className="cds--type-heading-04">Entregar paquete</h1>
      {proyectos.estado === "cargando" && <EsqueletoPagina etiqueta="Cargando los proyectos" />}
      {proyectos.estado === "listo" && proyectos.datos.length === 0 && (
        <EstadoVacio
          titulo="Este caso todavía no tiene proyectos."
          descripcion="Elabore un presupuesto para tener algo que entregar."
        />
      )}
      {proyectos.estado === "listo" && proyectos.datos.length > 0 && (
        <Seleccion proyectos={proyectos.datos} codigoAbierto={codigoAbierto} alExpirar={alExpirar} />
      )}
      <MensajeDeCarga carga={proyectos} />
    </div>
  );
}

function MensajeDeCarga({ carga }: { carga: Carga<unknown> }) {
  if (carga.estado === "error") return <AvisoError error={carga.error} titulo="No se pudo cargar" />;
  if (carga.estado === "sin_permiso") {
    return <AvisoError error="Su cuenta no tiene permiso para esta acción." titulo="Sin permiso" />;
  }
  if (carga.estado === "no_disponible") return <AvisoError error="No se encontró lo pedido." titulo="No disponible" />;
  return null;
}

function Seleccion({
  proyectos,
  codigoAbierto,
  alExpirar,
}: {
  proyectos: ProyectoDelCaso[];
  codigoAbierto: string | null;
  alExpirar: () => void;
}) {
  const inicial = proyectos.find((p) => p.codigo === codigoAbierto) ?? proyectos[0];
  const [nombre, setNombre] = useState(inicial.nombre);
  const [version, setVersion] = useState("");
  const versiones = useCarga<VersionEntregable[]>(
    `/v1/entregas/versiones?proyecto=${encodeURIComponent(nombre)}`,
    alExpirar,
  );
  const lista = versiones.estado === "listo" ? versiones.datos : [];
  // La version elegida si sigue en la lista; si no (otro proyecto), la mas nueva.
  const elegida = lista.some((v) => v.codigo === version) ? version : (lista[0]?.codigo ?? "");

  return (
    <>
      <div className="silice-entregar__selectores">
        <Select
          id="entregar-proyecto"
          labelText="Proyecto"
          value={nombre}
          onChange={(e) => {
            setNombre(e.target.value);
            setVersion("");
          }}
        >
          {proyectos.map((p) => (
            <SelectItem key={p.codigo} value={p.nombre} text={p.nombre} />
          ))}
        </Select>
        <Select
          id="entregar-version"
          labelText="Versión"
          value={elegida}
          disabled={lista.length === 0}
          onChange={(e) => setVersion(e.target.value)}
        >
          {lista.map((v) => (
            <SelectItem key={v.codigo} value={v.codigo} text={v.codigo} />
          ))}
        </Select>
      </div>
      {versiones.estado === "cargando" && <EsqueletoPagina etiqueta="Cargando las versiones" />}
      {versiones.estado === "listo" && lista.length === 0 && (
        <EstadoVacio titulo="Este proyecto todavía no tiene versiones." />
      )}
      <MensajeDeCarga carga={versiones} />
      {elegida && <Entrega key={`${nombre}|${elegida}`} proyecto={nombre} version={elegida} alExpirar={alExpirar} />}
    </>
  );
}

function Entrega({ proyecto, version, alExpirar }: { proyecto: string; version: string; alExpirar: () => void }) {
  const resumen = useCarga<ResumenEntrega>(
    `/v1/entregas/resumen?proyecto=${encodeURIComponent(proyecto)}&version=${encodeURIComponent(version)}`,
    alExpirar,
  );
  const [destinatario, setDestinatario] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [generando, setGenerando] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [listo, setListo] = useState<PaqueteListo | null>(null);

  if (resumen.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando el resumen" />;
  if (resumen.estado !== "listo") return <MensajeDeCarga carga={resumen} />;
  const datos = resumen.datos;

  async function generar(evento: FormEvent) {
    evento.preventDefault();
    const cuerpo: Record<string, string> = { proyecto, version };
    const para = destinatario.trim();
    if (para) cuerpo.destinatario = para;
    if (datos.firma_disponible) cuerpo.contrasena_clave = contrasena;
    // El formulario se vacia al enviar: la contraseña no se queda en pantalla ni en el estado.
    setDestinatario("");
    setContrasena("");
    setListo(null); // no dejar un paquete anterior a la vista
    setError(null);
    setGenerando(true);
    try {
      const { blob, nombre, cabeceras } = await pedirBinario("/v1/entregas", {
        metodo: "POST",
        cuerpo,
        respaldo: `${proyecto}-${version}.silice`,
      });
      setListo({
        blob,
        nombre,
        sha256: cabeceras.get("X-Silice-SHA256") ?? "",
        firmado: cabeceras.get("X-Silice-Firmado") === "1",
      });
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setError(e);
    } finally {
      setGenerando(false);
    }
  }

  return (
    <>
      <dl className="silice-entregar__datos">
        <div>
          <dt className="cds--type-label-01">Total</dt>
          <dd className="cds--type-heading-03">{`${datos.total_texto} ${datos.moneda}`}</dd>
        </div>
        <div>
          <dt className="cds--type-label-01">Hallazgos</dt>
          <dd className="cds--type-heading-03">{datos.hallazgos_total}</dd>
          {datos.hallazgos_total > 0 && (
            <dd className="cds--type-body-compact-01">{textoDeHallazgos(datos.hallazgos_por_severidad)}</dd>
          )}
        </div>
        <div>
          <dt className="cds--type-label-01">Cadena</dt>
          <dd className="cds--type-heading-03">{datos.cadena_integra ? "íntegra" : "ROTA"}</dd>
        </div>
      </dl>
      {!datos.cadena_integra && (
        <>
          <InlineNotification
            kind="error"
            role="alert"
            title="Cadena rota"
            subtitle={datos.mensaje_de_cadena}
            lowContrast
            hideCloseButton
          />
          <p className="silice-entregar__nota cds--type-body-compact-01">
            Un paquete con la cadena rota no se entrega: restaure la base desde un respaldo (Administración, pestaña
            Instalación) o avise a quien administra Sílice.
          </p>
        </>
      )}
      <p className="silice-entregar__nota cds--type-body-compact-01">{`Viaja con: ${datos.viaja_con.join(", ")}.`}</p>
      {datos.empresa === null && (
        <InlineNotification
          kind="warning"
          title="Sin empresa"
          subtitle="Todavía no hay empresa en Administración: el paquete no dirá quién lo emite."
          lowContrast
          hideCloseButton
        />
      )}
      {datos.empresa !== null && !datos.firma_disponible && (
        <InlineNotification
          kind="warning"
          title="Sin clave de firma"
          subtitle="No hay clave de firma: el paquete saldrá SIN FIRMA y quien lo reciba lo verá como «no verificado»."
          lowContrast
          hideCloseButton
        />
      )}

      <Form onSubmit={(e) => void generar(e)} className="silice-entregar__formulario">
        <TextInput
          id="entregar-destino"
          labelText="Para quién es (opcional)"
          value={destinatario}
          maxLength={200}
          onChange={(e) => setDestinatario(e.target.value)}
        />
        <PasswordInput
          id="entregar-clave"
          labelText="Contraseña de la clave de firma"
          value={contrasena}
          autoComplete="off"
          disabled={!datos.firma_disponible}
          onChange={(e) => setContrasena(e.target.value)}
        />
        <Button type="submit" kind="primary" size="md" disabled={!datos.cadena_integra || generando}>
          {generando ? "Generando…" : "Generar paquete"}
        </Button>
      </Form>

      <AvisoError error={error} titulo="No se pudo generar el paquete" alCerrar={() => setError(null)} />
      {listo && (
        <div className="silice-entregar__listo" role="status">
          <p className="cds--type-heading-compact-01">
            {listo.firmado ? "Paquete listo y firmado." : "Paquete listo (sin firma)."}
          </p>
          <p className="silice-entregar__sha cds--type-code-01">{`SHA-256: ${listo.sha256}`}</p>
          <Button kind="tertiary" size="md" renderIcon={Download} onClick={() => guardarBlob(listo.blob, listo.nombre)}>
            Descargar el paquete
          </Button>
        </div>
      )}
    </>
  );
}
