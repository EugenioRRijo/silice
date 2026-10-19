import { Button, Checkbox, InlineNotification } from "@carbon/react";
import { useCallback, useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { useAplicacion } from "../../shell/contexto";
import { textoDeApi, textoDeRed } from "./sensibles";
import type { InstalacionEstado, Pendiente } from "./sensibles";

// Pestaña «Instalación» (RF-98; spec S5 §5.2 y §6.5): red y API en lectura (los cambios de red no se hacen desde el
// navegador), respaldos y eventos de seguridad perdidos.
export default function Instalacion() {
  const { alExpirar } = useAplicacion();
  const [estado, setEstado] = useState<InstalacionEstado | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [confirmados, setConfirmados] = useState<Record<string, boolean>>({});
  const [ocupada, setOcupada] = useState(false);

  const fallar = useCallback(
    (e: unknown) => {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setError(e);
    },
    [alExpirar],
  );

  const cargar = useCallback(() => pedir<InstalacionEstado>("/v1/admin/instalacion").then(setEstado, fallar), [fallar]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function respaldar() {
    setOcupada(true);
    setError(null);
    try {
      const { nombre } = await pedir<{ nombre: string }>("/v1/admin/instalacion/respaldos", { metodo: "POST" });
      setAviso(`Respaldo creado: ${nombre}`);
      await cargar();
    } catch (e) {
      fallar(e);
    } finally {
      setOcupada(false);
    }
  }

  async function marcar(p: Pendiente) {
    setOcupada(true);
    setError(null);
    try {
      await pedir(`/v1/admin/instalacion/eventos/${encodeURIComponent(p.nombre)}/revisar`, { metodo: "POST" });
      await cargar();
    } catch (e) {
      fallar(e);
    } finally {
      setOcupada(false);
    }
  }

  if (estado === null) return error ? <AvisoError error={error} /> : <EsqueletoPagina />;

  return (
    <div className="silice-adm__secciones">
      <AvisoError error={error} alCerrar={() => setError(null)} />
      {estado.avisos.map((a) => (
        <InlineNotification key={a} kind="warning" role="status" title={a} lowContrast hideCloseButton />
      ))}
      <section className="silice-adm__seccion">
        <p className="cds--type-body-compact-01">{textoDeRed(estado)}</p>
        <p className="cds--type-body-compact-01">{textoDeApi(estado)}</p>
        <p className="silice-adm__nota cds--type-label-01">
          Para cambiar la red local use, en el equipo servidor, el acceso «Sílice: red local (administrador)». La API
          se activa en silice.toml y entra en vigor al reiniciar.
        </p>
      </section>

      {estado.pendientes.length > 0 && (
        <section className="silice-adm__seccion" aria-label="Eventos de seguridad perdidos">
          <InlineNotification
            kind="error"
            role="alert"
            title="Las operaciones sensibles están bloqueadas"
            subtitle="Se restauró un respaldo y hay eventos de seguridad perdidos sin revisar."
            lowContrast
            hideCloseButton
          />
          {estado.pendientes.map((p) => (
            <div key={p.nombre} className="silice-adm__seccion">
              <h3 className="cds--type-heading-compact-01">{p.nombre}</h3>
              <ul>
                {p.diferencias.map((d, i) => (
                  <li key={`${i}-${d}`} className="cds--type-body-compact-01">
                    {d}
                  </li>
                ))}
              </ul>
              <p className="cds--type-body-compact-01">Eventos de acceso posteriores al respaldo: {p.eventos}</p>
              <p className="silice-adm__nota cds--type-label-01">
                Vuelva a aplicar lo que corresponda (revocar, desactivar) y luego marque.
              </p>
              <Checkbox
                id={`adm-revise-${p.nombre}`}
                labelText="Ya revisé esto"
                checked={confirmados[p.nombre] === true}
                onChange={(_, { checked }) => setConfirmados({ ...confirmados, [p.nombre]: checked })}
              />
              <Button
                kind="tertiary"
                size="md"
                disabled={ocupada || confirmados[p.nombre] !== true}
                onClick={() => void marcar(p)}
              >
                Marcar como revisado
              </Button>
            </div>
          ))}
        </section>
      )}

      <section className="silice-adm__seccion">
        <h2 className="cds--type-heading-compact-02">Respaldos</h2>
        <Button kind="primary" size="md" disabled={ocupada} onClick={() => void respaldar()}>
          Crear respaldo ahora
        </Button>
        {aviso !== null && (
          <InlineNotification kind="success" role="status" title={aviso} lowContrast onClose={() => setAviso(null)} />
        )}
        {estado.respaldos.length === 0 ? (
          <p className="silice-adm__nota cds--type-body-compact-01">Todavía no hay respaldos.</p>
        ) : (
          <>
            <ul>
              {estado.respaldos.map((j) => (
                <li key={j.nombre} className="cds--type-body-compact-01">
                  {j.nombre} ({j.motivo}, {j.bases} bases)
                </li>
              ))}
            </ul>
            {estado.sensible.permitida ? (
              <>
                <InlineNotification
                  kind="warning"
                  role="status"
                  title="El respaldo trae huellas de contraseñas y la clave de firma cifrada: guárdelo bien."
                  lowContrast
                  hideCloseButton
                />
                <div className="silice-adm__acciones">
                  {estado.respaldos.map((j) => (
                    <DescargaArchivo
                      key={j.nombre}
                      ruta={`/v1/admin/instalacion/respaldos/${encodeURIComponent(j.nombre)}`}
                      etiqueta={`Descargar ${j.nombre} (.zip)`}
                      nombrePorOmision={`${j.nombre}.zip`}
                      alExpirar={alExpirar}
                    />
                  ))}
                </div>
              </>
            ) : (
              <InlineNotification kind="error" role="status" title={estado.sensible.motivo} lowContrast hideCloseButton />
            )}
          </>
        )}
      </section>
    </div>
  );
}
