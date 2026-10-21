import { Button, InlineNotification, Select, SelectItem } from "@carbon/react";
import type { JSX } from "react";
import { useState } from "react";
import { CampoTexto } from "../../comun/CampoTexto";
import { useAplicacion } from "../../shell/contexto";
import { DialogoDeOperacion } from "./DialogoDeOperacion";
import type { CeldaPrecio } from "./logica";
import { usuarioDeSesion } from "./logicaGuardar";
import {
  RUTA_DE_COTIZAR,
  RUTA_DE_RETIRAR,
  avisoDeCambiosPendientes,
  cotizadasDePrecios,
  cuerpoDeCotizar,
  cuerpoDeRetirar,
  fechaDeHoy,
  insumosDePrecios,
  motivoParaNoCotizar,
  motivoParaNoRetirar,
  rotuloDeCotizada,
  rotuloDeInsumo,
  textoDeVersionCreada,
} from "./logicaVersiones";
import type { InsumoDePrecios, VersionCreada } from "./logicaVersiones";
import { useDialogoDeOperacion } from "./useDialogoDeOperacion";
import { useOperacion } from "./useOperacion";

// Los topes del contrato de S3 y S4 (proveedor y número son el ancho de las columnas; la evidencia, lo que cabe en la fuente).
const LARGO = { precio: 500, proveedor: 120, numero: 60, evidencia: 90, motivo: 300 };

export type AlCrearVersion = (codigo: string, texto: string) => Promise<void>;

interface PropsDeFormulario {
  proyecto: string;
  version: string;
  insumos: InsumoDePrecios[];
  anfitrion: HTMLElement;
  alCancelar: () => void;
  alCrearVersion: AlCrearVersion;
}

function FormularioDeCotizar({ proyecto, version, insumos, anfitrion, alCancelar, alCrearVersion }: PropsDeFormulario) {
  const { alExpirar, sesion } = useAplicacion();
  const [insumo, setInsumo] = useState(insumos[0]?.codigo ?? "");
  const [precio, setPrecio] = useState("");
  const [proveedor, setProveedor] = useState("");
  const [numero, setNumero] = useState("");
  const [fecha, setFecha] = useState(fechaDeHoy());
  const [evidencia, setEvidencia] = useState("");
  const operacion = useOperacion({
    ruta: RUTA_DE_COTIZAR,
    alExpirar,
    alCrear: (r: VersionCreada) =>
      alCrearVersion(r.codigo, textoDeVersionCreada(r, `Se guardó la versión ${r.codigo} con la cotización de ${insumo}.`)),
  });
  const motivo = motivoParaNoCotizar({ precio, proveedor, numero, fecha });
  return (
    <DialogoDeOperacion
      operacion="cotizar"
      titulo="Registrar una cotización"
      descripcion="Crea una versión nueva desde la guardada; la cotización vale solo para este proyecto."
      anfitrion={anfitrion}
      usuario={usuarioDeSesion(sesion)}
      motivo={motivo}
      textoConfirmar="Cotizar"
      enviando={operacion.enviando}
      error={operacion.error}
      alConfirmar={() =>
        void operacion.enviar(cuerpoDeCotizar(proyecto, version, { insumo, precio, proveedor, numero, fecha, evidencia }))
      }
      alCancelar={alCancelar}
    >
      <Select id="hoja-cotizar-insumo" labelText="Insumo" value={insumo} onChange={(e) => setInsumo(e.target.value)}>
        {insumos.map((i) => (
          <SelectItem key={i.codigo} value={i.codigo} text={rotuloDeInsumo(i)} />
        ))}
      </Select>
      <CampoTexto
        id="hoja-cotizar-precio"
        labelText="Precio cotizado"
        helperText="Decimales con punto, por ejemplo 2.5."
        inputMode="decimal"
        value={precio}
        maxLength={LARGO.precio}
        onChange={(e) => setPrecio(e.target.value)}
      />
      <CampoTexto
        id="hoja-cotizar-proveedor"
        labelText="Proveedor"
        value={proveedor}
        maxLength={LARGO.proveedor}
        onChange={(e) => setProveedor(e.target.value)}
      />
      <CampoTexto
        id="hoja-cotizar-numero"
        labelText="Número de la cotización"
        value={numero}
        maxLength={LARGO.numero}
        onChange={(e) => setNumero(e.target.value)}
      />
      <CampoTexto
        id="hoja-cotizar-fecha"
        type="date"
        labelText="Fecha de la cotización"
        value={fecha}
        onChange={(e) => setFecha(e.target.value)}
      />
      <CampoTexto
        id="hoja-cotizar-evidencia"
        labelText="Evidencia (opcional: archivo, enlace, nota)"
        value={evidencia}
        maxLength={LARGO.evidencia}
        onChange={(e) => setEvidencia(e.target.value)}
      />
    </DialogoDeOperacion>
  );
}

function FormularioDeRetirar({ proyecto, version, insumos, anfitrion, alCancelar, alCrearVersion }: PropsDeFormulario) {
  const { alExpirar, sesion } = useAplicacion();
  const [insumo, setInsumo] = useState(insumos[0]?.codigo ?? "");
  const [razon, setRazon] = useState("");
  const operacion = useOperacion({
    ruta: RUTA_DE_RETIRAR,
    alExpirar,
    alCrear: (r: VersionCreada) =>
      alCrearVersion(r.codigo, textoDeVersionCreada(r, `Se guardó la versión ${r.codigo} sin la cotización.`)),
  });
  return (
    <DialogoDeOperacion
      operacion="retirar"
      titulo="Retirar una cotización"
      descripcion="Crea una versión nueva que vuelve al precio de la lista para ese insumo; las demás cotizaciones se conservan."
      anfitrion={anfitrion}
      usuario={usuarioDeSesion(sesion)}
      motivo={motivoParaNoRetirar(razon)}
      textoConfirmar="Retirar cotización"
      enviando={operacion.enviando}
      error={operacion.error}
      alConfirmar={() => void operacion.enviar(cuerpoDeRetirar(proyecto, version, insumo, razon))}
      alCancelar={alCancelar}
    >
      <Select id="hoja-retirar-insumo" labelText="Insumo cotizado" value={insumo} onChange={(e) => setInsumo(e.target.value)}>
        {insumos.map((i) => (
          <SelectItem key={i.codigo} value={i.codigo} text={rotuloDeCotizada(i)} />
        ))}
      </Select>
      <CampoTexto
        id="hoja-retirar-motivo"
        labelText="Por qué se retira"
        value={razon}
        maxLength={LARGO.motivo}
        onChange={(e) => setRazon(e.target.value)}
      />
    </DialogoDeOperacion>
  );
}

function Accion({
  rotulo,
  Formulario,
  ...p
}: Omit<PropsDeFormulario, "anfitrion" | "alCancelar"> & {
  rotulo: string;
  Formulario: (props: PropsDeFormulario) => JSX.Element;
}) {
  const { abierto, anfitrion, abrir, cerrar, anclaDelBoton } = useDialogoDeOperacion();
  return (
    <>
      <Button ref={anclaDelBoton} kind="tertiary" size="md" onClick={abrir}>
        {rotulo}
      </Button>
      {abierto && anfitrion !== null && (
        <Formulario
          {...p}
          anfitrion={anfitrion}
          alCancelar={() => cerrar(true)}
          alCrearVersion={async (codigo, texto) => {
            cerrar(false);
            await p.alCrearVersion(codigo, texto);
          }}
        />
      )}
    </>
  );
}

interface Props {
  proyecto: string;
  // La versión guardada que está abierta: de ella sale la versión nueva.
  version: string;
  filas: Array<Record<string, CeldaPrecio | undefined>>;
  // Los cambios sin guardar del borrador: con alguno no se ofrece nada (P:1946).
  cambios: number;
  alCrearVersion: AlCrearVersion;
}

// «Registrar una cotización» y «Retirar una cotización» (S3 y S4) de la pestaña Precios. Cada una crea una versión nueva desde la
// guardada, así que con cambios sin guardar se dice por qué no se ofrecen (la regla es de pantalla, como en la clásica).
export function OperacionesDePrecios({ proyecto, version, filas, cambios, alCrearVersion }: Props) {
  const insumos = insumosDePrecios(filas);
  const cotizadas = cotizadasDePrecios(filas);
  if (cambios > 0) {
    return (
      <InlineNotification
        kind="warning"
        role="status"
        lowContrast
        hideCloseButton
        title="Hay cambios sin guardar"
        subtitle={avisoDeCambiosPendientes("cotizar", cambios)}
      />
    );
  }
  if (insumos.length === 0) return null;
  const comunes = { proyecto, version, alCrearVersion };
  return (
    <section className="silice-hoja__seccion" aria-label="Cotizaciones">
      <div className="silice-hoja__acciones">
        <Accion {...comunes} insumos={insumos} rotulo="Registrar una cotización…" Formulario={FormularioDeCotizar} />
        {cotizadas.length > 0 && (
          <Accion {...comunes} insumos={cotizadas} rotulo="Retirar una cotización…" Formulario={FormularioDeRetirar} />
        )}
      </div>
    </section>
  );
}
