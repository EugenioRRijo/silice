import { Button, Checkbox, InlineNotification, PasswordInput, Select, SelectItem } from "@carbon/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { CampoTexto } from "../../comun/CampoTexto";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { useAplicacion } from "../../shell/contexto";
import { textoDeLaClaveDeIA, topeParaEditar } from "./logica";
import type { AsistenteEstado, ResultadoAsistente } from "./logica";

const RUTA = "/v1/admin/asistente";

// Lo que se le dice a quien administra cuando falta el componente de IA (VB-18). La API manda un texto con el comando
// de instalacion para desarrolladores; esta pantalla no lo muestra.
const AVISO_FALTA_EL_COMPONENTE =
  "Falta un componente opcional del asistente de IA en este equipo. Pídalo a quien instaló Sílice y vuelva a abrir Sílice.";

// Pestaña «Asistente de IA» (S4 §3.1, §8.3): configurar el asistente y registrar, reactivar u olvidar la clave de
// IA de la empresa. Paridad con `pestana_asistente` de la clásica. La clave y las contraseñas viven solo en el estado
// de este componente y se vacían al enviarlas, pase lo que pase; la API no las devuelve nunca (solo los 4 últimos
// caracteres de la clave). El panel de chat del asistente no es de esta pestaña.
export default function Asistente() {
  const { alExpirar } = useAplicacion();
  const [estado, setEstado] = useState<AsistenteEstado | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupada, setOcupada] = useState(false);
  // configuración
  const [activo, setActivo] = useState(false);
  const [proveedor, setProveedor] = useState("");
  const [modeloClaude, setModeloClaude] = useState("");
  const [modeloLocal, setModeloLocal] = useState("");
  const [anfitrion, setAnfitrion] = useState("");
  const [tope, setTope] = useState("");
  // clave (secretos: solo aquí y solo hasta enviarlos)
  const [clave, setClave] = useState("");
  const [respaldo, setRespaldo] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [confirmarOlvido, setConfirmarOlvido] = useState(false);
  // Foco de la confirmacion en linea (VD-2, igual que VB-12): al abrirla va a «Cancelar»; al cancelarla vuelve a
  // «Olvidar la clave».
  const cancelarOlvidoRef = useRef<HTMLButtonElement>(null);
  const olvidarRef = useRef<HTMLButtonElement>(null);
  const abrioOlvido = useRef(false);
  useEffect(() => {
    if (confirmarOlvido) {
      abrioOlvido.current = true;
      cancelarOlvidoRef.current?.focus();
    } else if (abrioOlvido.current) {
      abrioOlvido.current = false;
      olvidarRef.current?.focus();
    }
  }, [confirmarOlvido]);

  const adoptar = useCallback((e: AsistenteEstado) => {
    setEstado(e);
    setActivo(e.activo);
    setProveedor(e.proveedor);
    setModeloClaude(e.modelo_claude);
    setModeloLocal(e.modelo_local);
    setAnfitrion(e.anfitrion_ollama);
    setTope(topeParaEditar(e.tope_usd));
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
    pedir<AsistenteEstado>(RUTA).then(
      (e) => vigente && adoptar(e),
      (e: unknown) => vigente && fallar(e),
    );
    return () => {
      vigente = false;
    };
  }, [adoptar, fallar]);

  async function enviar(ruta: string, cuerpo?: object) {
    setOcupada(true);
    setError(null);
    setAviso(null);
    try {
      const r = await pedir<ResultadoAsistente>(ruta, { metodo: "POST", cuerpo });
      adoptar(r.estado);
      setAviso(r.mensaje);
    } catch (e) {
      fallar(e);
    } finally {
      setOcupada(false);
    }
  }

  function guardar(e: FormEvent) {
    e.preventDefault();
    void enviar(`${RUTA}/configuracion`, {
      activo,
      proveedor,
      modelo_claude: modeloClaude,
      modelo_local: modeloLocal,
      anfitrion_ollama: anfitrion,
      tope_usd: tope,
    });
  }

  function registrar(e: FormEvent) {
    e.preventDefault();
    const cuerpo = respaldo ? { clave, contrasena_respaldo: respaldo } : { clave };
    setClave("");
    setRespaldo("");
    setContrasena("");
    void enviar(`${RUTA}/clave`, cuerpo);
  }

  function reactivar(e: FormEvent) {
    e.preventDefault();
    const cuerpo = { contrasena };
    setClave("");
    setRespaldo("");
    setContrasena("");
    void enviar(`${RUTA}/clave/reactivar`, cuerpo);
  }

  // Al confirmar, el boton de origen queda deshabilitado mientras se envia: el foco va al campo para registrar otra
  // clave (o, si la cuenta no puede, queda donde estaba).
  async function olvidar() {
    abrioOlvido.current = false;
    setConfirmarOlvido(false);
    await enviar(`${RUTA}/clave/olvidar`);
    document.getElementById("ia-clave-nueva")?.focus();
  }

  if (estado === null) return error ? <AvisoError error={error} /> : <EsqueletoPagina />;
  const { sensible } = estado;
  const permitida = sensible.permitida;

  return (
    <div className="silice-adm__secciones">
      <InlineNotification kind="warning" role="status" title="Asistente en la nube" subtitle={estado.aviso_de_nube} lowContrast hideCloseButton />
      <AvisoError error={error} alCerrar={() => setError(null)} />
      {aviso !== null && (
        <InlineNotification kind="success" role="status" title={aviso} lowContrast onClose={() => setAviso(null)} />
      )}

      <form className="silice-adm__seccion" onSubmit={guardar}>
        <h2 className="cds--type-heading-compact-02">Configuración del asistente</h2>
        <Checkbox
          id="ia-activo"
          labelText="Activar el asistente de IA (viene apagado)"
          checked={activo}
          onChange={(_e, { checked }) => setActivo(checked)}
        />
        <Select id="ia-proveedor" labelText="Proveedor por defecto" value={proveedor} onChange={(e) => setProveedor(e.target.value)}>
          {estado.proveedores.map((p) => (
            <SelectItem key={p.valor} value={p.valor} text={p.etiqueta} />
          ))}
        </Select>
        <CampoTexto id="ia-modelo-claude" labelText="Modelo de Claude" value={modeloClaude} onChange={(e) => setModeloClaude(e.target.value)} />
        <CampoTexto
          id="ia-modelo-local"
          labelText="Modelo local (Ollama)"
          helperText="El nombre exacto de un modelo ya instalado en Ollama (el que muestra «ollama list»). Vacío: el modo local no se ofrece."
          value={modeloLocal}
          onChange={(e) => setModeloLocal(e.target.value)}
        />
        <CampoTexto id="ia-anfitrion" labelText="Dirección de Ollama" value={anfitrion} onChange={(e) => setAnfitrion(e.target.value)} />
        <p className="silice-adm__nota cds--type-label-01">
          Si la dirección de Ollama no es de este equipo, el asistente la trata como un servicio en la nube y lo avisa
          antes de enviar nada.
        </p>
        <CampoTexto
          id="ia-tope"
          labelText="Tope de costo por sesión (USD)"
          helperText="Mayor que cero; puede escribir coma o punto decimal."
          inputMode="decimal"
          value={tope}
          onChange={(e) => setTope(e.target.value)}
        />
        <Button type="submit" kind="primary" size="md" disabled={ocupada}>
          Guardar la configuración
        </Button>
      </form>

      {estado.falta_el_componente !== null ? (
        <InlineNotification kind="error" role="alert" title="Asistente de IA" subtitle={AVISO_FALTA_EL_COMPONENTE} lowContrast hideCloseButton />
      ) : (
        <div className="silice-adm__seccion">
          <h2 className="cds--type-heading-compact-02">Clave de IA de la empresa</h2>
          <p className="silice-adm__nota cds--type-body-compact-01">
            Se registra solo desde el equipo donde está instalado Sílice y se guarda en el almacén de credenciales de
            este usuario de Windows; no viaja en los respaldos.
          </p>
          {!permitida && (
            <InlineNotification kind="info" role="status" title="Clave de IA" subtitle={sensible.motivo} lowContrast hideCloseButton />
          )}
          <p className="cds--type-body-compact-01">{textoDeLaClaveDeIA(estado)}</p>
          {estado.clave_registrada === null && estado.pide_contrasena && permitida && (
            <form className="silice-adm__seccion" onSubmit={reactivar} autoComplete="off">
              <PasswordInput
                id="ia-contrasena-reactivar"
                labelText="Contraseña del respaldo cifrado de la clave"
                value={contrasena}
                autoComplete="off"
                onChange={(e) => setContrasena(e.target.value)}
              />
              <Button type="submit" kind="primary" size="md" disabled={ocupada}>
                Reactivar la clave
              </Button>
            </form>
          )}
          <form className="silice-adm__seccion" onSubmit={registrar} autoComplete="off">
            <PasswordInput
              id="ia-clave-nueva"
              labelText="Clave de IA de la empresa"
              value={clave}
              autoComplete="off"
              disabled={!permitida}
              onChange={(e) => setClave(e.target.value)}
            />
            <PasswordInput
              id="ia-contrasena-respaldo"
              labelText="Contraseña del respaldo cifrado (solo si el almacén de credenciales no está)"
              value={respaldo}
              autoComplete="new-password"
              disabled={!permitida}
              onChange={(e) => setRespaldo(e.target.value)}
            />
            <Button type="submit" kind="primary" size="md" disabled={ocupada || !permitida}>
              Registrar la clave
            </Button>
          </form>
          {!confirmarOlvido ? (
            <div className="silice-adm__acciones">
              <Button ref={olvidarRef} kind="danger--tertiary" size="md" disabled={ocupada || !permitida} onClick={() => setConfirmarOlvido(true)}>
                Olvidar la clave
              </Button>
            </div>
          ) : (
            <div role="group" aria-label="Confirmar" className="silice-adm__acciones">
              <p className="cds--type-body-compact-01">
                La clave de IA se borrará de este equipo (del almacén de credenciales y del respaldo cifrado). ¿Olvidarla?
              </p>
              <Button kind="danger" size="md" onClick={() => void olvidar()}>
                Sí, olvidar la clave
              </Button>
              <Button ref={cancelarOlvidoRef} kind="ghost" size="md" onClick={() => setConfirmarOlvido(false)}>
                Cancelar
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
