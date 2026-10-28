import { WarningAltFilled } from "@carbon/icons-react";
import { Button, Checkbox, Select, SelectItem } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { textoDeEquivalenciaExacta } from "../../comun/LineaDeEquivalencia";
import type { Equivalencia } from "../../comun/LineaDeEquivalencia";
import { AYUDA_CIFRAS, leerCifra, textoParaEscribir } from "../../indicadores/cifraEscrita";
import { fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { useFormularioSucio } from "../../shell/sucio";
import { Monto } from "./Cifras";
import { RAZON_POR_DEBAJO, describirError, rutaDeAfectados, rutaDeUsar, textoDeAfectados } from "./logica";
import type { Estudio } from "./logica";

type Paso =
  | { fase: "editando" }
  | { fase: "consultando" }
  | { fase: "confirmando"; apus: string[] }
  | { fase: "guardando" };

// La propuesta y «Usar este precio». El campo llega prellenado con la propuesta, escrita como se teclea («2.010,50»);
// lo que la persona escribe se envia tal cual y lo interpreta el servidor. Antes se revisa con la misma regla
// (`leerCifra`) para decir el error en el campo sin ir a la API; el valor leido no se usa. En compra, antes de guardar
// se dice que partidas cambiaran de precio y se pide confirmar (D-MP2); en cobro se guarda el precio objetivo citando
// las observaciones de las cifras. En compra, con una obra abierta, la casilla «Declararlo precio del corte» deja
// ademas el precio como precio del corte de esa obra (Tarea 25): `declarar_en` solo viaja si se marco, y la API
// confirma con su frase (`corte`) o, si la obra no lo admite, no guarda nada. Si la obra trabaja en la otra moneda, la
// API convierte el precio con la tasa del BCV y trae su `equivalencia`: se dice en una linea (Tarea D2).
interface Props {
  estudio: Estudio;
  // Avisa al lado si el campo tiene algo escrito sin usar (para preguntar antes de cambiar de insumo o partida).
  alCambiarSucio?: (sucio: boolean) => void;
}

export function UsarPrecio({ estudio, alCambiarSucio }: Props) {
  const { alExpirar, proyecto, nombreProyecto } = useAplicacion();
  const { lado, codigo, moneda, propuesta, estadisticas } = estudio;
  const propuesto = propuesta.precio === null ? "" : textoParaEscribir(propuesta.precio);
  // La ultima propuesta vista (para seguir sus cambios) y el texto que cuenta como «sin cambios»: la propuesta mientras
  // nadie escriba, o el ultimo precio usado. Son dos cosas: tras usar un precio propio, ese queda en el campo.
  const [vista, setVista] = useState(propuesto);
  const [limpio, setLimpio] = useState(propuesto);
  const [precio, setPrecio] = useState(propuesto);
  const [respaldo, setRespaldo] = useState("");
  const [errorDelCampo, setErrorDelCampo] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [hecho, setHecho] = useState<string | null>(null);
  const [paso, setPaso] = useState<Paso>({ fase: "editando" });
  const [declarar, setDeclarar] = useState(false);
  const campo = useRef<HTMLInputElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const pregunta = useRef<HTMLDivElement>(null);
  const aviso = useRef<HTMLDivElement>(null);
  // Adonde va el foco al volver a editar: a «Usar este precio» (que se vuelve a montar tras la pregunta) o al aviso de
  // error; un error del campo lo enfoca en el acto.
  const devolverFoco = useRef<"boton" | "aviso" | null>(null);
  const idTitulo = `mercado-${lado}-precio-titulo`;

  // Si la propuesta cambia (otra ventana de dias, una observacion nueva) y el campo no tiene nada propio sin usar, toma
  // la nueva; lo escrito y no usado no se pisa.
  if (propuesto !== vista) {
    setVista(propuesto);
    if (precio === limpio) {
      setPrecio(propuesto);
      setLimpio(propuesto);
    }
  }

  const sucio = precio !== limpio;
  useFormularioSucio("mercado", sucio);
  useEffect(() => {
    alCambiarSucio?.(sucio);
  }, [sucio, alCambiarSucio]);

  useEffect(() => {
    if (paso.fase === "confirmando") pregunta.current?.focus();
    if (paso.fase === "editando" && devolverFoco.current) {
      const destino = devolverFoco.current === "aviso" ? aviso.current : boton.current;
      devolverFoco.current = null;
      destino?.focus();
    }
  }, [paso.fase]);

  // El aviso lo decide la razon que manda la API (compara los montos exactos); la pagina no vuelve a comparar.
  const debajoDelPiso = lado === "cobro" && propuesta.razon === RAZON_POR_DEBAJO;
  const citables = estudio.observaciones.filter((o) => o.cuenta);
  const ocupado = paso.fase === "consultando" || paso.fase === "guardando";
  // La casilla solo existe en compra y con una obra abierta; sin ella nunca se declara.
  const obra = lado === "compra" && proyecto ? { codigo: proyecto, nombre: nombreProyecto ?? proyecto } : null;
  const declarando = obra !== null && declarar;

  function fallo(e: unknown) {
    if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
    if (e instanceof ErrorDeApi && e.estado === 422) {
      setErrorDelCampo(e.detalle);
      setPaso({ fase: "editando" });
      campo.current?.focus();
      return;
    }
    setError(e);
    devolverFoco.current = "aviso";
    setPaso({ fase: "editando" });
  }

  async function guardar() {
    setPaso({ fase: "guardando" });
    try {
      if (lado === "compra") {
        const cita = citables.find((o) => String(o.id) === respaldo);
        const cuerpo = { precio, observacion_id: cita ? cita.id : null };
        const r = await pedir<{ lista: string; corte?: string | null; equivalencia?: Equivalencia | null }>(
          rutaDeUsar("compra", codigo),
          {
            metodo: "POST",
            cuerpo: declarando ? { ...cuerpo, declarar_en: obra.codigo } : cuerpo,
          },
        );
        const guardado = r.corte ? `Precio guardado en «${r.lista}». ${r.corte}` : `Precio guardado en «${r.lista}».`;
        setHecho(
          r.equivalencia ? `${guardado} Se convirtió con la tasa del BCV: ${textoDeEquivalenciaExacta(r.equivalencia)}` : guardado,
        );
        setDeclarar(false);
      } else {
        const r = await pedir<{ codigo: string; precio: string; moneda: string }>(rutaDeUsar("cobro", codigo), {
          metodo: "POST",
          cuerpo: { precio, observaciones: estadisticas.ids },
        });
        setHecho(
          `Precio objetivo guardado: ${formatoEsVe(r.precio)} ${r.moneda}. La Hoja lo mostrará junto al precio del APU.`,
        );
      }
      setLimpio(precio);
      devolverFoco.current = "boton";
      setPaso({ fase: "editando" });
    } catch (e) {
      fallo(e);
    }
  }

  async function usar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setHecho(null);
    const lectura = leerCifra(precio);
    if ("error" in lectura) {
      setErrorDelCampo(lectura.error);
      campo.current?.focus();
      return;
    }
    if (lado === "cobro") {
      await guardar();
      return;
    }
    setPaso({ fase: "consultando" });
    try {
      const r = await pedir<{ apus: string[] }>(rutaDeAfectados(codigo));
      setPaso({ fase: "confirmando", apus: r.apus });
    } catch (e) {
      fallo(e);
    }
  }

  function cancelar() {
    devolverFoco.current = "boton";
    setPaso({ fase: "editando" });
  }

  return (
    <section className="silice-mercado__bloque" aria-labelledby={idTitulo}>
      <h2 id={idTitulo} className="cds--type-heading-compact-02">
        Su precio
      </h2>
      {propuesta.precio !== null ? (
        <>
          <p className="cds--type-body-compact-01">
            Propuesta de Sílice:{" "}
            <strong>
              <Monto valor={propuesta.precio} moneda={moneda} />
            </strong>
          </p>
          <p className="silice-mercado__razon cds--type-body-compact-01">
            {debajoDelPiso && (
              <WarningAltFilled aria-label="Aviso" className="silice-mercado__icono-aviso" />
            )}
            <span>{propuesta.razon}</span>
          </p>
        </>
      ) : (
        <p className="silice-mercado__nota cds--type-body-compact-01">
          Sin propuesta: no hay observaciones con qué compararla. Si ya sabe su precio, escríbalo.
        </p>
      )}

      <form className="silice-mercado__usar" onSubmit={(e) => void usar(e)} noValidate>
        <CampoTexto
          ref={campo}
          id={`mercado-${lado}-precio`}
          labelText="Su precio"
          helperText={`En ${moneda}. ${AYUDA_CIFRAS}`}
          size="md"
          inputMode="decimal"
          autoComplete="off"
          value={precio}
          invalid={errorDelCampo !== null}
          invalidText={errorDelCampo ?? ""}
          {...describirError(`mercado-${lado}-precio`, errorDelCampo !== null)}
          readOnly={paso.fase !== "editando"}
          onChange={(e) => {
            setPrecio(e.target.value);
            setErrorDelCampo(null);
            setHecho(null);
          }}
        />
        {lado === "compra" ? (
          <Select
            id={`mercado-${lado}-respaldo`}
            labelText="Observación que respalda el precio"
            helperText="Opcional: queda como fuente del precio en la lista."
            size="md"
            value={respaldo}
            disabled={paso.fase !== "editando"}
            onChange={(e) => setRespaldo(e.target.value)}
          >
            <SelectItem value="" text="Ninguna: es un precio propio" />
            {citables.map((o) => (
              <SelectItem
                key={o.id}
                value={String(o.id)}
                text={`n.º ${o.id} · ${o.fuente} · ${fechaEsVe(o.fecha)} · ${formatoEsVe(o.precio)} ${o.moneda}`}
              />
            ))}
          </Select>
        ) : null}
        {/* Mientras se confirma, la pregunta ya dice si se declara (como «Usar este precio», la casilla se oculta). */}
        {obra !== null && paso.fase !== "confirmando" && (
          <div className="silice-mercado__ancho">
            <Checkbox
              id={`mercado-${lado}-declarar`}
              labelText={`Declararlo precio del corte de la obra ${obra.nombre}`}
              helperText="Control de obra lo usará para separar el desvío de precio («Precios declarados de insumos»)."
              checked={declarar}
              disabled={paso.fase !== "editando"}
              onChange={(_e, { checked }) => setDeclarar(checked)}
            />
          </div>
        )}
        <p className="silice-mercado__nota silice-mercado__ancho cds--type-helper-text-01">
          {lado === "compra"
            ? "Entra en la lista para armar de la carpeta con la fecha de hoy. Las versiones ya guardadas no cambian."
            : `Se guarda como su precio de venta objetivo de ${codigo}, citando las observaciones de las cifras.`}
        </p>
        {paso.fase !== "confirmando" && (
          <div className="silice-mercado__ancho">
            <Button ref={boton} type="submit" kind="primary" size="md" disabled={ocupado}>
              {ocupado ? "Un momento…" : "Usar este precio"}
            </Button>
          </div>
        )}
      </form>

      {paso.fase === "confirmando" && (
        <div ref={pregunta} tabIndex={-1} className="silice-mercado__pregunta" role="group" aria-label="Confirmar el precio">
          <p className="cds--type-body-compact-01">{textoDeAfectados(paso.apus)}</p>
          {declarando && (
            <p className="cds--type-body-compact-01">{`También quedará como precio del corte de la obra ${obra.nombre} desde hoy.`}</p>
          )}
          <p className="cds--type-body-compact-01">{`¿Usar ${precio} ${moneda} para ${codigo}?`}</p>
          <div className="silice-mercado__botones">
            <Button kind="primary" size="md" onClick={() => void guardar()}>
              Confirmar
            </Button>
            <Button kind="secondary" size="md" onClick={cancelar}>
              Cancelar
            </Button>
          </div>
        </div>
      )}

      {error !== null && (
        <div ref={aviso} tabIndex={-1} className="silice-mercado__aviso">
          <AvisoError error={error} titulo="No se usó el precio" />
        </div>
      )}
      <p role="status" className="silice-mercado__estado cds--type-body-compact-01">
        {hecho ?? ""}
      </p>
    </section>
  );
}
