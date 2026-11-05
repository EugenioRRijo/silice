import { Button } from "@carbon/react";
import { useEffect, useState } from "react";
import type { JSX } from "react";
import { Link } from "react-router";
import { ErrorDeApi } from "../../api/cliente";
import { empresaDeAdministracion, publicarCalculo } from "../../api/produccionPlanta";
import type { CalculoDeCosto, EmpresaDeAdministracion } from "../../api/produccionPlanta";
import { AvisoError } from "../../comun/AvisoError";
import { rutaDeCuenta } from "../../marco/espacios";
import { MarcoDeDialogo } from "../../shell/carpetas/MarcoDeDialogo";
import { fuenteDelPrecio, mensajeAlPublicar, nombreDeLista, pideConfigurarEmpresa } from "./logicaPlanta";

interface Props {
  calculo: CalculoDeCosto;
  // Se publicó: la pantalla avisa con el nombre de la lista que creó el servidor.
  alPublicar: (nombreDeLaLista: string) => void;
  alExpirar: () => void;
  // El servidor dijo que ya estaba publicado (409): la pantalla muestra su texto y recarga lo que sabe.
  alConflicto: (razon: unknown) => void;
}

type Empresa = { estado: "cargando" } | { estado: "listo"; datos: EmpresaDeAdministracion } | { estado: "error" };

// Los datos de la empresa viven en la Cuenta, sección «Empresa y tema» (F6, T6).
const ADMINISTRACION = rutaDeCuenta("empresa");

// Publicar un cálculo como precio propio de la empresa. Solo se monta con la acción `publicar_costo_propio`; la ruta no
// lleva cuerpo (el servidor publica el cálculo tal como lo guardó). La empresa es la de Administración y se lee, no se
// escribe aquí. Cada publicación es otra lista de precios, así que se confirma antes.
export function PublicarCosto({ calculo, alPublicar, alExpirar, alConflicto }: Props): JSX.Element {
  const [empresa, setEmpresa] = useState<Empresa>({ estado: "cargando" });
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const control = new AbortController();
    empresaDeAdministracion(control.signal).then(
      (datos) => setEmpresa({ estado: "listo", datos }),
      (razon: unknown) => {
        if (control.signal.aborted) return;
        if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
        setEmpresa({ estado: "error" });
      },
    );
    return () => control.abort();
  }, [alExpirar]);

  const fuente = fuenteDelPrecio(calculo.periodo, calculo.id);
  const lista = nombreDeLista(calculo.periodo, calculo.id);
  const sinEmpresa = empresa.estado === "listo" && empresa.datos.empresa === null;

  async function publicar() {
    setError(null);
    setEnviando(true);
    try {
      const publicada = await publicarCalculo(calculo.id);
      setConfirmando(false);
      alPublicar(publicada.nombre);
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else if (razon instanceof ErrorDeApi && razon.estado === 409) {
        setConfirmando(false);
        alConflicto(razon);
      } else setError(razon);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <fieldset className="planta-publicar">
      <legend className="cds--type-heading-compact-02">Publicar como precio propio</legend>
      <p className="cds--type-body-compact-01">
        El precio de cada producto queda en una lista de precios nueva de la empresa, con esta fuente:{" "}
        <span className="silice-cifra">{fuente}</span>
      </p>
      {empresa.estado === "listo" && empresa.datos.empresa && (
        <p className="cds--type-body-compact-01">
          Empresa que publica (de Administración):{" "}
          <strong>
            {empresa.datos.empresa.nombre} ({empresa.datos.empresa.rif})
          </strong>
        </p>
      )}
      {empresa.estado === "error" && (
        <p className="planta-nota cds--type-body-compact-01">
          No se pudo leer la empresa de Administración; el servidor la comprobará al publicar.
        </p>
      )}
      {sinEmpresa && (
        <p className="cds--type-body-compact-01">
          Todavía no se configuró la empresa en Administración: sin ella no se puede publicar.{" "}
          <Link className="cds--link" to={ADMINISTRACION}>
            Ir a Administración
          </Link>
        </p>
      )}
      <Button kind="primary" size="md" onClick={() => setConfirmando(true)}>
        Publicar como precio propio
      </Button>
      {confirmando && (
        <MarcoDeDialogo
          titulo="Publicar el costo propio"
          alCerrar={() => {
            setConfirmando(false);
            setError(null);
          }}
          pie={
            <>
              <Button
                kind="secondary"
                onClick={() => {
                  setConfirmando(false);
                  setError(null);
                }}
              >
                Cancelar
              </Button>
              <Button kind="primary" disabled={enviando} onClick={() => void publicar()}>
                Publicar
              </Button>
            </>
          }
        >
          <div className="receta-formulario">
            <p className="cds--type-body-compact-01">
              Se creará la lista "{lista}" con un precio por producto, en {calculo.moneda}. Cada publicación es otra lista: las
              anteriores no cambian.
            </p>
            <p className="planta-nota cds--type-body-compact-01">Fuente de los precios: {fuente}</p>
            <AvisoError error={error === null ? null : mensajeAlPublicar(error)} titulo="No se pudo publicar" />
            {pideConfigurarEmpresa(error) && (
              <p className="cds--type-body-compact-01">
                <Link className="cds--link" to={ADMINISTRACION} onClick={() => setConfirmando(false)}>
                  Ir a Administración
                </Link>
              </p>
            )}
          </div>
        </MarcoDeDialogo>
      )}
    </fieldset>
  );
}
