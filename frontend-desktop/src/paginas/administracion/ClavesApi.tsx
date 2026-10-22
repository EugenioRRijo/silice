import { Button, InlineNotification, Select, SelectItem } from "@carbon/react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { CampoTexto } from "../../comun/CampoTexto";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import type { ClaveApi } from "./sensibles";

// Pestaña «Claves de API» (UC-21; RF-98). El secreto de una clave nueva se muestra UNA vez: vive solo en el estado
// de este componente (nunca en el almacenamiento del navegador) y desaparece al cerrarlo, al crear otra o al salir.
export default function ClavesApi() {
  const { alExpirar } = useAplicacion();
  const [claves, setClaves] = useState<ClaveApi[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [nombre, setNombre] = useState("");
  const [secreto, setSecreto] = useState<string | null>(null);
  const [aRevocar, setARevocar] = useState("");
  const [confirmando, setConfirmando] = useState(false);
  const [ocupada, setOcupada] = useState(false);

  const fallar = useCallback(
    (e: unknown) => {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setError(e);
    },
    [alExpirar],
  );

  const cargar = useCallback(() => pedir<ClaveApi[]>("/v1/admin/claves-api").then(setClaves, fallar), [fallar]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setOcupada(true);
    setError(null);
    setSecreto(null);
    try {
      const creada = await pedir<{ secreto: string }>("/v1/admin/claves-api", { metodo: "POST", cuerpo: { nombre } });
      setSecreto(creada.secreto);
      setNombre("");
      await cargar();
    } catch (err) {
      fallar(err);
    } finally {
      setOcupada(false);
    }
  }

  async function revocar() {
    setConfirmando(false);
    setOcupada(true);
    setError(null);
    try {
      await pedir(`/v1/admin/claves-api/${aRevocar}/revocar`, { metodo: "POST" });
      setARevocar("");
      setSecreto(null);
      await cargar();
    } catch (err) {
      fallar(err);
    } finally {
      setOcupada(false);
    }
  }

  if (claves === null) return error ? <AvisoError error={error} /> : <EsqueletoPagina />;
  const vigentes = claves.filter((c) => c.estado === "vigente");

  return (
    <div className="silice-adm__secciones">
      <AvisoError error={error} alCerrar={() => setError(null)} />
      <TablaDensa
        etiqueta="Claves de API"
        columnas={[
          { clave: "etiqueta", titulo: "Clave" },
          { clave: "nombre", titulo: "Para qué" },
          { clave: "estado", titulo: "Estado" },
          { clave: "ultimo_uso", titulo: "Último uso" },
        ]}
        filas={claves.map((c) => ({
          id: String(c.id),
          etiqueta: c.etiqueta,
          nombre: c.nombre,
          estado: c.estado,
          ultimo_uso: c.ultimo_uso ?? "nunca",
        }))}
        vacio={{ titulo: "Todavía no hay claves de API" }}
      />
      <form className="silice-adm__seccion" onSubmit={(e) => void crear(e)}>
        <CampoTexto
          id="adm-api-nombre"
          labelText="Para qué es esta clave (por ejemplo, el plugin que la usa)"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
        <Button type="submit" kind="primary" size="md" disabled={ocupada}>
          Crear la clave de API
        </Button>
      </form>
      {secreto !== null && (
        <InlineNotification
          kind="warning"
          role="alert"
          title="Clave creada. Cópiela ahora: no se vuelve a mostrar."
          lowContrast
          onClose={() => {
            setSecreto(null);
            return false;
          }}
        >
          <code className="silice-cifra" data-testid="secreto-de-api">
            {secreto}
          </code>
        </InlineNotification>
      )}
      {vigentes.length > 0 && (
        <div className="silice-adm__seccion">
          <Select
            id="adm-api-revocar"
            labelText="Clave a revocar"
            value={aRevocar}
            onChange={(e) => {
              setARevocar(e.target.value);
              setConfirmando(false);
            }}
          >
            <SelectItem value="" text="Elija una clave" />
            {vigentes.map((c) => (
              <SelectItem key={c.id} value={String(c.id)} text={`${c.etiqueta} — ${c.nombre}`} />
            ))}
          </Select>
          {!confirmando ? (
            <Button kind="danger--tertiary" size="md" disabled={ocupada || aRevocar === ""} onClick={() => setConfirmando(true)}>
              Revocar la clave
            </Button>
          ) : (
            <div role="group" aria-label="Confirmar" className="silice-adm__acciones">
              <p className="cds--type-body-compact-01">Quien use esta clave dejará de entrar a la API. ¿Revocarla?</p>
              <Button kind="danger" size="md" onClick={() => void revocar()}>
                Sí, revocar
              </Button>
              <Button kind="ghost" size="md" onClick={() => setConfirmando(false)}>
                Cancelar
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
