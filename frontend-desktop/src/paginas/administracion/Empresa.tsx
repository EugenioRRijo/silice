import { Button, InlineNotification, PasswordInput } from "@carbon/react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { CampoTexto } from "../../comun/CampoTexto";
import { AvisoError } from "../../comun/AvisoError";
import { DescargaArchivo, guardarBlob } from "../../comun/DescargaArchivo";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { useAplicacion } from "../../shell/contexto";
import { avisoDeRevocacion, bytesDeBase64, contrasenasCoinciden, MENSAJE_NO_COINCIDEN } from "./sensibles";
import type { EmpresaEstado } from "./sensibles";

type Baja = { tipo: "retirar" | "revocar" } | null;

// Pestaña «Empresa y clave de firma» (UC-21; RF-80, RF-84). La contraseña de la clave vive solo en el estado de
// este componente y se vacía al enviarla; la API no la guarda, no la registra y no la devuelve.
export default function Empresa() {
  const { alExpirar } = useAplicacion();
  const [estado, setEstado] = useState<EmpresaEstado | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [nombre, setNombre] = useState("");
  const [rif, setRif] = useState("");
  const [ciudad, setCiudad] = useState("");
  const [uno, setUno] = useState("");
  const [dos, setDos] = useState("");
  const [motivo, setMotivo] = useState("");
  const [contrasenaBaja, setContrasenaBaja] = useState("");
  const [baja, setBaja] = useState<Baja>(null);
  const [ocupada, setOcupada] = useState(false);

  const adoptar = useCallback((e: EmpresaEstado) => {
    setEstado(e);
    setNombre(e.empresa?.nombre ?? "");
    setRif(e.empresa?.rif ?? "");
    setCiudad(e.empresa?.ciudad ?? "");
  }, []);

  const fallar = useCallback(
    (e: unknown) => {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setError(e);
    },
    [alExpirar],
  );

  useEffect(() => {
    let vigente = true;
    pedir<EmpresaEstado>("/v1/admin/empresa").then(
      (e) => vigente && adoptar(e),
      (e: unknown) => vigente && fallar(e),
    );
    return () => {
      vigente = false;
    };
  }, [adoptar, fallar]);

  async function enviar<T>(accion: () => Promise<T>, alTerminar: (r: T) => void) {
    setOcupada(true);
    setError(null);
    setAviso(null);
    try {
      alTerminar(await accion());
    } catch (e) {
      fallar(e);
    } finally {
      setOcupada(false);
    }
  }

  function guardarEmpresa(e: FormEvent) {
    e.preventDefault();
    void enviar(
      () => pedir<EmpresaEstado>("/v1/admin/empresa", { metodo: "POST", cuerpo: { nombre, rif, ciudad } }),
      (r) => {
        adoptar(r);
        setAviso("Empresa guardada.");
      },
    );
  }

  function generar(e: FormEvent) {
    e.preventDefault();
    if (!contrasenasCoinciden(uno, dos)) {
      setError(MENSAJE_NO_COINCIDEN);
      return;
    }
    const contrasena = uno;
    setUno("");
    setDos("");
    void enviar(
      () => pedir<EmpresaEstado>("/v1/admin/empresa/clave", { metodo: "POST", cuerpo: { contrasena } }),
      (r) => {
        adoptar(r);
        setAviso("Clave generada. Guarde la contraseña: sin ella no se puede firmar.");
      },
    );
  }

  function darDeBaja(tipo: "retirar" | "revocar") {
    const contrasena = contrasenaBaja;
    setContrasenaBaja("");
    setBaja(null);
    if (tipo === "retirar") {
      void enviar(
        () => pedir<EmpresaEstado>("/v1/admin/empresa/clave/retirar", { metodo: "POST", cuerpo: { motivo } }),
        (r) => {
          adoptar(r);
          setMotivo("");
          setAviso("Clave retirada. Genere una nueva para volver a firmar.");
        },
      );
      return;
    }
    void enviar(
      () =>
        pedir<{ aviso: string | null }>("/v1/admin/empresa/clave/revocar", {
          metodo: "POST",
          cuerpo: contrasena ? { motivo, contrasena } : { motivo },
        }),
      (r) => {
        setMotivo("");
        setAviso(avisoDeRevocacion(r.aviso !== null));
        if (r.aviso !== null) {
          guardarBlob(new Blob([bytesDeBase64(r.aviso)]), "revocacion.silice-revocacion");
        }
        void pedir<EmpresaEstado>("/v1/admin/empresa").then(adoptar, fallar);
      },
    );
  }

  if (estado === null) return error ? <AvisoError error={error} /> : <EsqueletoPagina />;
  const { clave, sensible } = estado;
  const hayEmpresa = estado.empresa !== null;

  return (
    <div className="silice-adm__secciones">
      <AvisoError error={error} alCerrar={() => setError(null)} />
      {aviso !== null && (
        <InlineNotification kind="success" role="status" title={aviso} lowContrast onClose={() => setAviso(null)} />
      )}
      <form className="silice-adm__seccion" onSubmit={guardarEmpresa}>
        <h2 className="cds--type-heading-compact-02">La empresa</h2>
        <CampoTexto id="adm-empresa-nombre" labelText="Nombre de la empresa" value={nombre} onChange={(e) => setNombre(e.target.value)} />
        <CampoTexto id="adm-empresa-rif" labelText="RIF" value={rif} onChange={(e) => setRif(e.target.value)} />
        <CampoTexto id="adm-empresa-ciudad" labelText="Ciudad" value={ciudad} onChange={(e) => setCiudad(e.target.value)} />
        <Button type="submit" kind="primary" size="md" disabled={ocupada}>
          Guardar la empresa
        </Button>
      </form>

      {!sensible.permitida && (
        <InlineNotification kind="info" role="status" title="Clave de firma" subtitle={sensible.motivo} lowContrast hideCloseButton />
      )}

      {clave === null ? (
        !hayEmpresa ? (
          <p className="silice-adm__nota cds--type-body-compact-01">
            Primero guarde el nombre y el RIF de la empresa; después se genera la clave.
          </p>
        ) : (
          <form className="silice-adm__seccion" onSubmit={generar} autoComplete="off">
            <h2 className="cds--type-heading-compact-02">Generar la clave de firma</h2>
            <PasswordInput
              id="adm-clave-uno"
              labelText="Contraseña de la clave (12 a 128 caracteres)"
              value={uno}
              autoComplete="new-password"
              onChange={(e) => setUno(e.target.value)}
            />
            <PasswordInput
              id="adm-clave-dos"
              labelText="Repítala"
              value={dos}
              autoComplete="new-password"
              onChange={(e) => setDos(e.target.value)}
            />
            <Button type="submit" kind="primary" size="md" disabled={ocupada || !sensible.permitida}>
              Generar la clave
            </Button>
          </form>
        )
      ) : (
        <div className="silice-adm__seccion">
          <h2 className="cds--type-heading-compact-02">Clave de firma</h2>
          <p className="cds--type-body-compact-01">
            Huella de la clave de firma: <strong>{clave.huella}</strong>
          </p>
          <p className="silice-adm__nota cds--type-label-01">
            Léala por teléfono a quien reciba sus paquetes: es lo que comprueba su clave.
          </p>
          <div className="silice-adm__acciones">
            <DescargaArchivo
              ruta="/v1/admin/empresa/clave-publica"
              etiqueta="Descargar la clave pública"
              nombrePorOmision="clave-publica.silice-clave"
              alExpirar={alExpirar}
            />
            {sensible.permitida ? (
              <DescargaArchivo
                ruta="/v1/admin/empresa/respaldo-clave"
                etiqueta="Descargar el respaldo cifrado de la clave"
                nombrePorOmision="respaldo-clave.silice-respaldo"
                alExpirar={alExpirar}
              />
            ) : (
              <p className="silice-adm__nota cds--type-label-01">Respaldo de la clave: {sensible.motivo}</p>
            )}
          </div>
          <h3 className="cds--type-heading-compact-01">Retirar o revocar la clave</h3>
          <p className="silice-adm__nota cds--type-body-compact-01">
            Retirar es cambiar de clave sin que se haya comprometido; revocar es para una clave perdida o expuesta:
            los paquetes firmados con ella dejan de verificar. En ambos casos se destruye la clave privada de este
            equipo.
          </p>
          <CampoTexto id="adm-motivo-clave" labelText="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          <PasswordInput
            id="adm-clave-revocar"
            labelText="Contraseña de la clave (para firmar el aviso de revocación; opcional)"
            value={contrasenaBaja}
            autoComplete="off"
            onChange={(e) => setContrasenaBaja(e.target.value)}
          />
          {baja === null ? (
            <div className="silice-adm__acciones">
              <Button kind="tertiary" size="md" disabled={ocupada || !sensible.permitida} onClick={() => setBaja({ tipo: "retirar" })}>
                Retirar
              </Button>
              <Button kind="danger--tertiary" size="md" disabled={ocupada || !sensible.permitida} onClick={() => setBaja({ tipo: "revocar" })}>
                Revocar
              </Button>
            </div>
          ) : (
            <div role="group" aria-label="Confirmar" className="silice-adm__acciones">
              <p className="cds--type-body-compact-01">
                {baja.tipo === "retirar"
                  ? "Se destruirá la clave privada de este equipo. ¿Retirar la clave?"
                  : "Los paquetes firmados con la clave dejarán de verificar. ¿Revocar la clave?"}
              </p>
              <Button kind={baja.tipo === "revocar" ? "danger" : "primary"} size="md" onClick={() => darDeBaja(baja.tipo)}>
                {baja.tipo === "retirar" ? "Sí, retirar" : "Sí, revocar"}
              </Button>
              <Button kind="ghost" size="md" onClick={() => setBaja(null)}>
                Cancelar
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
