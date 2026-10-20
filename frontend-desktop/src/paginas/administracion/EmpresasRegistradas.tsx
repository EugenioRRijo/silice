import { Button, InlineNotification, Select, SelectItem } from "@carbon/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { CampoTexto } from "../../comun/CampoTexto";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { fechaDeHoy, filasDeRegistradas, MENSAJE_REVOCAR_SIN_MOTIVO, puedeRevocarRegistrada } from "./logica";
import type { ClaveLeida, RegistradasRespuesta } from "./logica";

const RUTA = "/v1/admin/empresas-registradas";

type Cambio = "retirar" | "revocar" | null;

// Pestaña «Empresas registradas» (UC-21; spec S3 §7): las claves públicas de las empresas cuyos paquetes se reciben.
// Paridad con `_pestana_registradas` y `_cambiar_registrada` de la clásica. El archivo de la clave se lee en la API
// (que calcula la huella) y solo se registra si la huella leída por otro canal coincide.
export default function EmpresasRegistradas() {
  const { alExpirar } = useAplicacion();
  const [datos, setDatos] = useState<RegistradasRespuesta | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupada, setOcupada] = useState(false);
  // registrar
  const [archivo, setArchivo] = useState<File | null>(null);
  const [leida, setLeida] = useState<ClaveLeida | null>(null);
  const [huella, setHuella] = useState("");
  const [conQuien, setConQuien] = useState("");
  const [metodo, setMetodo] = useState("");
  // retirar o revocar
  const [elegida, setElegida] = useState("");
  const [fecha, setFecha] = useState(() => fechaDeHoy());
  const [motivo, setMotivo] = useState("");
  const [avisoFirmado, setAvisoFirmado] = useState<File | null>(null);
  const [cambio, setCambio] = useState<Cambio>(null);
  // Foco de la confirmacion en linea (VB-12): al abrirla va a «Cancelar»; al cerrarla vuelve al boton que la abrio.
  const cancelarRef = useRef<HTMLButtonElement>(null);
  const retirarRef = useRef<HTMLButtonElement>(null);
  const revocarRef = useRef<HTMLButtonElement>(null);
  const abrio = useRef<Cambio>(null);
  useEffect(() => {
    if (cambio !== null) {
      abrio.current = cambio;
      cancelarRef.current?.focus();
    } else if (abrio.current !== null) {
      (abrio.current === "retirar" ? retirarRef : revocarRef).current?.focus();
      abrio.current = null;
    }
  }, [cambio]);

  const fallar = useCallback(
    (e: unknown) => {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setError(e);
    },
    [alExpirar],
  );

  const adoptar = useCallback((r: RegistradasRespuesta) => {
    setDatos(r);
    setMetodo((m) => m || (r.metodos[0]?.valor ?? ""));
    setElegida((e) => (r.registradas.some((f) => String(f.id) === e) ? e : String(r.registradas[0]?.id ?? "")));
  }, []);

  useEffect(() => {
    let vigente = true;
    pedir<RegistradasRespuesta>(RUTA).then(
      (r) => vigente && adoptar(r),
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

  function elegirClave(elegido: File) {
    setArchivo(elegido);
    setLeida(null);
    const cuerpo = new FormData();
    cuerpo.append("archivo", elegido);
    void enviar(() => pedir<ClaveLeida>(`${RUTA}/leer`, { metodo: "POST", cuerpo }), setLeida);
  }

  function registrar(e: FormEvent) {
    e.preventDefault();
    if (archivo === null) return;
    const cuerpo = new FormData();
    cuerpo.append("archivo", archivo);
    cuerpo.append("huella", huella);
    cuerpo.append("comprobada_con", conQuien);
    cuerpo.append("metodo", metodo);
    void enviar(
      () => pedir<RegistradasRespuesta>(RUTA, { metodo: "POST", cuerpo }),
      (r) => {
        adoptar(r);
        setArchivo(null);
        setLeida(null);
        setHuella("");
        setConQuien("");
        setAviso("Empresa registrada.");
      },
    );
  }

  function pedirConfirmacion(tipo: "retirar" | "revocar") {
    setAviso(null);
    if (tipo === "revocar" && !puedeRevocarRegistrada(motivo, avisoFirmado !== null)) {
      setError(MENSAJE_REVOCAR_SIN_MOTIVO);
      return;
    }
    setError(null);
    setCambio(tipo);
  }

  // Al confirmar, el boton de origen queda deshabilitado mientras se envia: el foco va a la lista de empresas.
  function alTerminarCambio() {
    document.getElementById("adm-ajena")?.focus();
  }

  function cambiar(tipo: "retirar" | "revocar") {
    abrio.current = null;
    setCambio(null);
    if (tipo === "retirar") {
      void enviar(
        () => pedir<RegistradasRespuesta>(`${RUTA}/${elegida}/retirar`, { metodo: "POST", cuerpo: { fecha } }),
        (r) => {
          adoptar(r);
          setAviso("Clave marcada como retirada.");
        },
      ).then(alTerminarCambio);
      return;
    }
    const cuerpo = new FormData();
    cuerpo.append("motivo", motivo);
    if (avisoFirmado !== null) cuerpo.append("aviso", avisoFirmado);
    void enviar(
      () => pedir<RegistradasRespuesta>(`${RUTA}/${elegida}/revocar`, { metodo: "POST", cuerpo }),
      (r) => {
        adoptar(r);
        setMotivo("");
        setAvisoFirmado(null);
        setAviso("Clave revocada: los paquetes con ella ya no verifican.");
      },
    ).then(alTerminarCambio);
  }

  if (datos === null) return error ? <AvisoError error={error} /> : <EsqueletoPagina />;
  const { registradas, metodos } = datos;
  // Sobre una clave ya revocada no hay nada que retirar ni que revocar (VB-22).
  const yaRevocada = registradas.find((f) => String(f.id) === elegida)?.estado === "revocada";

  return (
    <div className="silice-adm__secciones">
      <AvisoError error={error} alCerrar={() => setError(null)} />
      {aviso !== null && (
        <InlineNotification kind="success" role="status" title={aviso} lowContrast onClose={() => setAviso(null)} />
      )}
      <TablaDensa
        etiqueta="Empresas registradas"
        columnas={[
          { clave: "empresa", titulo: "Empresa" },
          { clave: "huella", titulo: "Huella" },
          { clave: "estado", titulo: "Estado" },
          { clave: "comprobada_con", titulo: "Comprobada con" },
          { clave: "metodo", titulo: "Método" },
        ]}
        filas={filasDeRegistradas(registradas, metodos)}
        vacio={{
          titulo: "Todavía no hay empresas registradas",
          descripcion: "Registre abajo la clave pública de la empresa cuyos paquetes va a recibir.",
        }}
      />

      {registradas.length > 0 && (
        <div className="silice-adm__seccion">
          <h2 className="cds--type-heading-compact-02">Retirar o revocar la clave de una empresa registrada</h2>
          <Select
            id="adm-ajena"
            labelText="Empresa"
            value={elegida}
            onChange={(e) => {
              setElegida(e.target.value);
              abrio.current = null; // cambiar de empresa no devuelve el foco a ningun boton
              setCambio(null);
            }}
          >
            {registradas.map((f) => (
              <SelectItem key={f.id} value={String(f.id)} text={f.empresa} />
            ))}
          </Select>
          <p className="silice-adm__nota cds--type-body-compact-01">
            Retirada: la empresa avisó que cambió de clave; sus paquetes anteriores a la fecha siguen valiendo.
            Revocada: ningún paquete con esa clave verifica.
          </p>
          <CampoTexto
            id="adm-ajena-fecha"
            type="date"
            labelText="Fecha del retiro"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
          />
          <CampoTexto
            id="adm-ajena-motivo"
            labelText="Motivo de la revocación"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          <SubidaArchivo
            id="adm-ajena-aviso"
            etiqueta="Aviso de revocación firmado (opcional): suéltelo aquí o haga clic para elegirlo"
            extensiones={[".silice-revocacion"]}
            alElegir={setAvisoFirmado}
            deshabilitada={ocupada}
          />
          {avisoFirmado !== null && (
            <div className="silice-adm__acciones">
              <p className="cds--type-body-compact-01">Aviso elegido: {avisoFirmado.name}</p>
              <Button kind="ghost" size="sm" onClick={() => setAvisoFirmado(null)}>
                Quitar el aviso
              </Button>
            </div>
          )}
          {yaRevocada && (
            <p id="adm-ajena-revocada" className="silice-adm__nota cds--type-body-compact-01">
              Esta clave ya está revocada: ningún paquete con ella verifica y no admite más cambios.
            </p>
          )}
          {cambio === null ? (
            <div className="silice-adm__acciones">
              <Button ref={retirarRef} kind="tertiary" size="md" disabled={ocupada || elegida === "" || yaRevocada} aria-describedby={yaRevocada ? "adm-ajena-revocada" : undefined} onClick={() => pedirConfirmacion("retirar")}>
                Marcar como retirada
              </Button>
              <Button ref={revocarRef} kind="danger--tertiary" size="md" disabled={ocupada || elegida === "" || yaRevocada} aria-describedby={yaRevocada ? "adm-ajena-revocada" : undefined} onClick={() => pedirConfirmacion("revocar")}>
                Revocar
              </Button>
            </div>
          ) : (
            <div role="group" aria-label="Confirmar" className="silice-adm__acciones">
              <p className="cds--type-body-compact-01">
                {cambio === "retirar"
                  ? "Solo los paquetes de esta empresa anteriores a la fecha del retiro seguirán valiendo. ¿Marcar la clave como retirada?"
                  : "Ningún paquete firmado con esta clave volverá a verificar. ¿Revocar la clave?"}
              </p>
              <Button kind={cambio === "revocar" ? "danger" : "primary"} size="md" onClick={() => cambiar(cambio)}>
                {cambio === "retirar" ? "Sí, marcar como retirada" : "Sí, revocar"}
              </Button>
              <Button ref={cancelarRef} kind="ghost" size="md" onClick={() => setCambio(null)}>
                Cancelar
              </Button>
            </div>
          )}
        </div>
      )}

      <div className="silice-adm__seccion">
        <h2 className="cds--type-heading-compact-02">Registrar la clave de otra empresa</h2>
        <SubidaArchivo
          id="adm-subir-clave"
          etiqueta="Archivo de la clave pública (.silice-clave): suéltelo aquí o haga clic para elegirlo"
          extensiones={[".silice-clave"]}
          alElegir={elegirClave}
          deshabilitada={ocupada}
        />
        {leida !== null && (
          <form className="silice-adm__seccion" onSubmit={registrar} autoComplete="off">
            <p className="cds--type-body-compact-01">
              Empresa declarada en el archivo: <strong>{leida.empresa}</strong>
            </p>
            <p className="cds--type-body-compact-01">
              Huella calculada del archivo: <strong>{leida.huella}</strong>
            </p>
            <p className="silice-adm__nota cds--type-label-01">
              Pida a la otra empresa que le lea su huella por teléfono (u otro canal distinto del que le mandó el
              archivo) y escríbala aquí.
            </p>
            <CampoTexto
              id="adm-huella-leida"
              labelText="Huella leída por otro canal"
              value={huella}
              onChange={(e) => setHuella(e.target.value)}
            />
            <CampoTexto
              id="adm-comprobada-con"
              labelText="Comprobada con (persona)"
              value={conQuien}
              onChange={(e) => setConQuien(e.target.value)}
            />
            <Select id="adm-metodo" labelText="Cómo se comprobó" value={metodo} onChange={(e) => setMetodo(e.target.value)}>
              {metodos.map((m) => (
                <SelectItem key={m.valor} value={m.valor} text={m.etiqueta} />
              ))}
            </Select>
            <Button type="submit" kind="primary" size="md" disabled={ocupada}>
              Registrar la empresa
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
