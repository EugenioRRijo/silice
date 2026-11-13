import { Button, Checkbox } from "@carbon/react";
import { InlineNotification } from "../../comun/carbonEs";
import { useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { useAplicacion } from "../../shell/contexto";
import { enumeradas } from "../auditoria/AuditarApuPorHoja";
import type { PerfilDisponible } from "../auditoria/AuditarApuPorHoja";

const RUTA = "/v1/admin/empresa/perfiles-libros";

// Libro por frentes (ola 2, línea 3, 2026-11-13): el perfil del libro con un APU por hoja de un libro de la empresa vive en
// la carpeta de datos de la instalación, nunca en el repositorio; antes había que copiar el JSON a mano. Aquí quien
// administra lo sube: el servidor lo valida entero (las mismas reglas que al auditar) y no pisa uno que ya está sin
// «Reemplazar». La pantalla no lee ni interpreta el JSON: solo lo manda y dice lo que respondió el servidor.
export default function PerfilesDeLibros() {
  const { alExpirar } = useAplicacion();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [reemplazar, setReemplazar] = useState(false);
  const [ocupada, setOcupada] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [puesto, setPuesto] = useState<PerfilDisponible | null>(null);

  async function poner() {
    if (archivo === null) return;
    setError(null);
    setPuesto(null);
    setOcupada(true);
    const cuerpo = new FormData();
    cuerpo.append("perfil", archivo);
    cuerpo.append("reemplazar", reemplazar ? "true" : "false");
    try {
      setPuesto(await pedir<PerfilDisponible>(RUTA, { metodo: "POST", cuerpo }));
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setError(razon);
    } finally {
      setOcupada(false);
    }
  }

  const hojas = puesto ? (puesto.hojas_presupuesto?.length ? puesto.hojas_presupuesto : [puesto.hoja_presupuesto ?? ""]) : [];
  return (
    <section aria-labelledby="adm-perfiles-libros-titulo" className="silice-adm__bloque">
      <h2 id="adm-perfiles-libros-titulo" className="cds--type-heading-compact-02">
        Perfiles de los libros de la empresa
      </h2>
      <p className="cds--type-body-compact-01">
        Un perfil dice cómo leer el libro con un APU por hoja que exporta el programa de la empresa (los rótulos de cada hoja
        y las hojas del presupuesto, una por frente). Se guarda solo en esta instalación y se elige al auditar el libro.
      </p>
      <SubidaArchivo
        id="adm-perfil-libro"
        etiqueta="Suelte aquí el perfil .json, o haga clic para elegirlo"
        extensiones={[".json"]}
        alElegir={setArchivo}
        deshabilitada={ocupada}
      />
      {archivo && <p className="cds--type-body-compact-01">{`Perfil elegido: ${archivo.name}`}</p>}
      <Checkbox
        id="adm-perfil-reemplazar"
        labelText="Reemplazar el que ya está con ese nombre"
        checked={reemplazar}
        disabled={ocupada}
        onChange={(_e, { checked }) => setReemplazar(checked)}
      />
      <Button kind="primary" size="md" disabled={archivo === null || ocupada} onClick={() => void poner()}>
        Poner el perfil
      </Button>
      <AvisoError error={error} titulo="No se puso el perfil" />
      {puesto && (
        <InlineNotification
          kind="success"
          role="status"
          title={`Perfil «${puesto.nombre}» puesto en esta instalación: lee ${hojas.length === 1 ? "la hoja" : "las hojas"} ${enumeradas(hojas)}.`}
          lowContrast
          hideCloseButton
        />
      )}
    </section>
  );
}
