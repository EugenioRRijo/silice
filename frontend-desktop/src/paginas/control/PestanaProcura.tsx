import { Button, Checkbox, InlineNotification } from "@carbon/react";
import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { createPortal } from "react-dom";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { mensajeDeError } from "../../comun/errores";
import { Severidad } from "../../comun/Severidad";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { AYUDA_CIFRAS } from "../../indicadores/cifraEscrita";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { useFormularioSucio } from "../../shell/sucio";
import { useAtraparFoco } from "../../shell/useAtraparFoco";
import { describirError, hoyIso } from "../mercado/logica";
import { fechaDeRanura } from "./fechas";
import { errorDeCarga, errorDeCifra, rutaDe, useCargaSuave } from "./logica";
import {
  COLUMNAS_ALERTAS_DE_COMPRA,
  COLUMNAS_PROCURA,
  campoDelError,
  delMaterial,
  diasHabiles,
  severidadDeCompra,
} from "./procura";
import type { CampoDeRecepcion, NecesidadDeMaterial, Procura } from "./procura";

interface Props {
  proyecto: string;
  // Cambia cuando otra pestaña (o esta) escribio algo: vuelve a pedir la procura.
  clave: number;
  alCambiar: () => void;
}

const ID_ESTADO = "procura-estado";
const PANTALLA = "control";

// --- dialogo -------------------------------------------------------------------------------------------------------

interface PropsDialogo {
  titulo: string;
  // El campo que recibe el foco al abrir.
  idPrimero: string;
  textoEnviar: string;
  enviando: boolean;
  // Un error que no es de ningun campo (se dice dentro del dialogo).
  error: string | null;
  alEnviar: () => void;
  alCancelar: () => void;
  children: ReactNode;
}

// Dialogo propio (como los de la Hoja): foco atrapado, Esc cierra (salvo mientras va la peticion, para no perder la
// respuesta) y el pie con Cancelar y la accion siempre a la vista. Quien lo abre decide adonde vuelve el foco.
function DialogoDeProcura({ titulo, idPrimero, textoEnviar, enviando, error, alEnviar, alCancelar, children }: PropsDialogo) {
  const caja = useRef<HTMLDivElement>(null);
  const atrapar = useAtraparFoco(caja);
  const idTitulo = useId();
  const idFormulario = useId();

  useEffect(() => {
    document.getElementById(idPrimero)?.focus();
  }, [idPrimero]);

  const alTeclear = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      if (!enviando) alCancelar();
      return;
    }
    atrapar(e);
  };

  return createPortal(
    <div className="silice-control__dialogo-fondo">
      <div
        ref={caja}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
        onKeyDown={alTeclear}
        className="silice-control__dialogo"
      >
        <h2 id={idTitulo} className="cds--type-heading-compact-02">
          {titulo}
        </h2>
        <form
          id={idFormulario}
          className="silice-control__dialogo-campos"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            if (!enviando) alEnviar();
          }}
        >
          {children}
        </form>
        <p className="cds--type-helper-text-01" aria-live="polite">
          {enviando ? "Guardando…" : ""}
        </p>
        {error !== null && (
          <InlineNotification kind="error" role="alert" lowContrast hideCloseButton title="No se guardó" subtitle={error} />
        )}
        <div className="silice-control__dialogo-acciones">
          <Button kind="secondary" size="md" disabled={enviando} onClick={alCancelar}>
            Cancelar
          </Button>
          <Button kind="primary" size="md" type="submit" form={idFormulario} disabled={enviando}>
            {textoEnviar}
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

// Lleva el foco a un campo cuando ya se puede enfocar (mientras va la peticion los campos estan deshabilitados).
function useFocoPendiente(enviando: boolean, cambio: unknown): (id: string) => void {
  const pendiente = useRef<string | null>(null);
  useEffect(() => {
    if (enviando || pendiente.current === null) return;
    const id = pendiente.current;
    pendiente.current = null;
    document.getElementById(id)?.focus();
  }, [enviando, cambio]);
  return (id: string) => {
    pendiente.current = id;
  };
}

interface PropsAccion {
  proyecto: string;
  necesidad: NecesidadDeMaterial;
  alCancelar: () => void;
  // Lo hecho, en una frase neutra para la linea de estado de la pestaña.
  alHecho: (texto: string) => void;
}

// --- «Recibida…» ---------------------------------------------------------------------------------------------------

type ErroresDeRecepcion = Record<CampoDeRecepcion, string | null>;
const SIN_ERRORES: ErroresDeRecepcion = { fecha: null, cantidad: null, precio: null };
const ORDEN: CampoDeRecepcion[] = ["fecha", "cantidad", "precio"];
// La casilla «Declararlo precio del corte» (Tarea 25) sin precio: el mismo texto que el 422 de la API.
const PRECIO_PARA_EL_CORTE = "El precio unitario hace falta para declararlo precio del corte.";

function DialogoRecibida({ proyecto, necesidad, alCancelar, alHecho }: PropsAccion) {
  const { alExpirar } = useAplicacion();
  const [hoy] = useState(hoyIso);
  const [fecha, setFecha] = useState(hoy);
  const [cantidad, setCantidad] = useState("");
  const [precio, setPrecio] = useState("");
  const [declarar, setDeclarar] = useState(false);
  const [errores, setErrores] = useState<ErroresDeRecepcion>(SIN_ERRORES);
  const [general, setGeneral] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const enfocar = useFocoPendiente(enviando, errores);
  const base = useId();
  const id = (campo: CampoDeRecepcion) => `${base}-${campo}`;
  const { descripcion, unidad } = necesidad;
  // Con la casilla marcada el precio es obligatorio: ya no se llama «opcional».
  const detallesDelPrecio = [unidad ? `por ${unidad}` : null, declarar ? null : "opcional"].filter((d) => d !== null);
  const etiquetaDelPrecio = detallesDelPrecio.length > 0 ? `Precio unitario (${detallesDelPrecio.join(", ")})` : "Precio unitario";

  useFormularioSucio(PANTALLA, fecha !== hoy || cantidad.trim() !== "" || precio.trim() !== "" || declarar);

  async function anotar() {
    const nuevos: ErroresDeRecepcion = {
      fecha: fecha ? null : "Escriba la fecha en que llegó el material.",
      cantidad: errorDeCifra(cantidad),
      precio: declarar && !precio.trim() ? PRECIO_PARA_EL_CORTE : errorDeCifra(precio),
    };
    setErrores(nuevos);
    setGeneral(null);
    const conError = ORDEN.find((c) => nuevos[c] !== null);
    if (conError) {
      enfocar(id(conError));
      return;
    }
    setEnviando(true);
    try {
      const cuerpo = { proyecto, descripcion, unidad, evento: "recibida", fecha, cantidad, precio };
      await pedir("/v1/procura/compras", {
        metodo: "POST",
        cuerpo: declarar ? { ...cuerpo, declarar_corte: true } : cuerpo,
      });
      const anotada = `Recepción de ${descripcion} anotada con fecha ${fechaDeRanura(fecha)}.`;
      alHecho(declarar ? `${anotada} Su precio queda como precio del corte desde esa fecha.` : anotada);
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      const campo = e instanceof ErrorDeApi && e.estado === 422 ? campoDelError(e.detalle) : null;
      if (campo !== null && e instanceof ErrorDeApi) {
        setErrores({ ...SIN_ERRORES, [campo]: e.detalle });
        enfocar(id(campo));
      } else {
        setGeneral(mensajeDeError(e));
      }
    } finally {
      setEnviando(false);
    }
  }

  const campo = (c: CampoDeRecepcion) => ({
    id: id(c),
    size: "md" as const,
    autoComplete: "off",
    disabled: enviando,
    invalid: errores[c] !== null,
    invalidText: errores[c] ?? "",
    ...describirError(id(c), errores[c] !== null),
  });

  return (
    <DialogoDeProcura
      titulo={`Recepción de ${descripcion}`}
      idPrimero={id("fecha")}
      textoEnviar="Anotar recepción"
      enviando={enviando}
      error={general}
      alEnviar={() => void anotar()}
      alCancelar={alCancelar}
    >
      <p className="silice-control__nota cds--type-helper-text-01">{AYUDA_CIFRAS}</p>
      <CampoTexto
        {...campo("fecha")}
        type="date"
        max={hoy}
        labelText="Fecha de llegada"
        helperText="El día en que llegó a la obra; no puede ser posterior a hoy."
        value={fecha}
        onChange={(e) => {
          setFecha(e.target.value);
          setErrores((previos) => ({ ...previos, fecha: null }));
        }}
      />
      <CampoTexto
        {...campo("cantidad")}
        inputMode="decimal"
        labelText={`Cantidad recibida (${unidad ? `${unidad}, ` : ""}opcional)`}
        value={cantidad}
        onChange={(e) => {
          setCantidad(e.target.value);
          setErrores((previos) => ({ ...previos, cantidad: null }));
        }}
      />
      <CampoTexto
        {...campo("precio")}
        inputMode="decimal"
        labelText={etiquetaDelPrecio}
        helperText="En la moneda de la carpeta. Si el material está en el catálogo, el precio se anota también en el estudio de mercado."
        value={precio}
        onChange={(e) => {
          setPrecio(e.target.value);
          setErrores((previos) => ({ ...previos, precio: null }));
        }}
      />
      <Checkbox
        id={`${base}-declarar`}
        labelText="Declararlo precio del corte"
        helperText="Desde la fecha de llegada, Control de obra lo usará para separar el desvío de precio («Precios declarados de insumos»)."
        checked={declarar}
        disabled={enviando}
        onChange={(_e, { checked }) => {
          setDeclarar(checked);
          setErrores((previos) => ({ ...previos, precio: null }));
        }}
      />
    </DialogoDeProcura>
  );
}

// --- plazo de entrega ----------------------------------------------------------------------------------------------

function DialogoPlazo({ proyecto, necesidad, alCancelar, alHecho }: PropsAccion) {
  const { alExpirar } = useAplicacion();
  const inicial = String(necesidad.plazo);
  const [dias, setDias] = useState(inicial);
  const [error, setError] = useState<string | null>(null);
  const [general, setGeneral] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const enfocar = useFocoPendiente(enviando, error);
  const idDias = `${useId()}-dias`;
  const { descripcion, unidad } = necesidad;

  useFormularioSucio(PANTALLA, dias !== inicial);

  async function guardar() {
    setGeneral(null);
    const escrito = dias.trim();
    if (escrito === "") {
      setError("Escriba el plazo: un número entero de días hábiles, de 0 a 365.");
      enfocar(idDias);
      return;
    }
    setError(null);
    setEnviando(true);
    try {
      await pedir("/v1/procura/plazos", { metodo: "PUT", cuerpo: { proyecto, descripcion, unidad, dias } });
      alHecho(`Plazo de ${descripcion}: ${diasHabiles(escrito)}.`);
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      if (e instanceof ErrorDeApi && e.estado === 422) {
        setError(e.detalle);
        enfocar(idDias);
      } else {
        setGeneral(mensajeDeError(e));
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <DialogoDeProcura
      titulo={`Plazo de entrega de ${descripcion}`}
      idPrimero={idDias}
      textoEnviar="Guardar plazo"
      enviando={enviando}
      error={general}
      alEnviar={() => void guardar()}
      alCancelar={alCancelar}
    >
      <CampoTexto
        id={idDias}
        size="md"
        inputMode="numeric"
        autoComplete="off"
        labelText="Días hábiles de entrega"
        helperText="Cuánto tarda el proveedor desde el pedido hasta la obra, sin contar fines de semana ni feriados. Un número entero de 0 a 365."
        value={dias}
        disabled={enviando}
        invalid={error !== null}
        invalidText={error ?? ""}
        {...describirError(idDias, error !== null)}
        onChange={(e) => {
          setDias(e.target.value);
          setError(null);
        }}
      />
    </DialogoDeProcura>
  );
}

// --- la pestaña ----------------------------------------------------------------------------------------------------

type Abierto = { tipo: "recibida" | "plazo"; fila: number } | null;

function fechaOSin(iso: string | null): string {
  return iso ? fechaDeRanura(iso) : "Sin fecha";
}

// Las filas de la tabla: el valor de cada columna como texto (las fechas en ISO y la cantidad exacta, para ordenar);
// lo que se ve lo pinta cada columna.
function filasDe(necesidades: NecesidadDeMaterial[]): FilaDensa[] {
  return necesidades.map((n, i) => ({
    id: String(i),
    Insumo: n.descripcion,
    Cantidad: n.cantidad,
    Partidas: n.partidas.join(", "),
    "Se necesita": n.se_necesita ?? "",
    "Pedir a más tardar": n.pedir_a_mas_tardar ?? "",
    "Plazo (días hábiles)": String(n.plazo),
    Pedida: n.pedida ?? "",
    Recibida: n.recibida ?? "",
  }));
}

// MP-7, Tarea 24 (diseño de montar un presupuesto §11, meta 3): los materiales de la obra con sus fechas de compra y las
// alertas al dia de hoy (`GET /v1/procura`); anotar un pedido o una recepcion (`POST /v1/procura/compras`) y cambiar el
// plazo de entrega de un material (`PUT /v1/procura/plazos`). Lo hecho se dice en una linea de estado neutra.
export function PestanaProcura({ proyecto, clave, alCambiar }: Props) {
  const { alExpirar } = useAplicacion();
  const carga = useCargaSuave<Procura>(rutaDe("/v1/procura", proyecto, { n: String(clave) }), alExpirar);
  const [abierto, setAbierto] = useState<Abierto>(null);
  const [hecho, setHecho] = useState("");
  const [pidiendo, setPidiendo] = useState<number | null>(null);
  const [errorPedido, setErrorPedido] = useState<unknown>(null);
  // Adonde vuelve el foco cuando no hay dialogo: el boton que lo abrio (al cancelar) o la linea de estado.
  const foco = useRef<string | null>(null);

  useEffect(() => {
    if (abierto !== null || foco.current === null) return;
    const destino = foco.current;
    foco.current = null;
    document.getElementById(destino)?.focus();
  });

  if (carga.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando la procura" />;
  if (carga.estado !== "listo") return <AvisoError error={errorDeCarga(carga)} titulo="No se pudo cargar la procura" />;
  const datos = carga.datos;
  const necesidades = datos.necesidades;
  const idBoton = (tipo: "pedida" | "recibida" | "plazo", fila: number) => `procura-${tipo}-${fila}`;

  const terminar = (texto: string) => {
    setAbierto(null);
    setHecho(texto);
    foco.current = ID_ESTADO;
    alCambiar();
  };
  const cancelar = () => {
    if (abierto !== null) foco.current = idBoton(abierto.tipo, abierto.fila);
    setAbierto(null);
  };

  async function pedidaHoy(fila: number) {
    const n = necesidades[fila]!;
    const fecha = hoyIso();
    setPidiendo(fila);
    setErrorPedido(null);
    try {
      await pedir("/v1/procura/compras", {
        metodo: "POST",
        cuerpo: { proyecto, descripcion: n.descripcion, unidad: n.unidad, evento: "pedida", fecha },
      });
      terminar(`Pedido de ${n.descripcion} anotado con fecha ${fechaDeRanura(fecha)}.`);
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setErrorPedido(e);
    } finally {
      setPidiendo(null);
    }
  }

  const deFila = (fila: FilaDensa) => necesidades[Number(fila.id)]!;
  const pintores: Partial<Record<(typeof COLUMNAS_PROCURA)[number], (fila: FilaDensa) => ReactNode>> = {
    // La cantidad exacta en es-VE, una sola vez y sin `title` (el texto ya es el exacto).
    Cantidad: (fila) => {
      const n = deFila(fila);
      return n.unidad ? `${formatoEsVe(n.cantidad)} ${n.unidad}` : formatoEsVe(n.cantidad);
    },
    "Se necesita": (fila) => fechaOSin(deFila(fila).se_necesita),
    "Pedir a más tardar": (fila) => fechaOSin(deFila(fila).pedir_a_mas_tardar),
    "Plazo (días hábiles)": (fila) => {
      const i = Number(fila.id);
      const n = deFila(fila);
      return (
        <span className="silice-control__plazo">
          <span className="silice-cifra">{n.plazo}</span>
          <Button
            id={idBoton("plazo", i)}
            kind="ghost"
            size="sm"
            aria-label={`Cambiar el plazo de ${delMaterial(n)}`}
            onClick={() => setAbierto({ tipo: "plazo", fila: i })}
          >
            Cambiar
          </Button>
        </span>
      );
    },
    Pedida: (fila) => {
      const i = Number(fila.id);
      const n = deFila(fila);
      if (n.pedida) return fechaDeRanura(n.pedida);
      // Una recepcion cuenta tambien como pedido (bitacora T23, 2): ya no se ofrece pedirlo.
      if (n.recibida) return "No consta";
      return (
        <Button
          id={idBoton("pedida", i)}
          kind="ghost"
          size="sm"
          aria-label={`Pedida hoy: ${delMaterial(n)}`}
          disabled={pidiendo !== null}
          onClick={() => void pedidaHoy(i)}
        >
          Pedida hoy
        </Button>
      );
    },
    Recibida: (fila) => {
      const i = Number(fila.id);
      const n = deFila(fila);
      if (n.recibida) return fechaDeRanura(n.recibida);
      return (
        <Button
          id={idBoton("recibida", i)}
          kind="ghost"
          size="sm"
          aria-label={`Recibida…: ${delMaterial(n)}`}
          onClick={() => setAbierto({ tipo: "recibida", fila: i })}
        >
          Recibida…
        </Button>
      );
    },
  };
  const columnas: ColumnaDensa[] = COLUMNAS_PROCURA.map((titulo) => ({
    clave: titulo,
    titulo,
    numerica: titulo === "Cantidad",
    ordenable: false,
    celda: pintores[titulo],
  }));
  const columnasAlertas: ColumnaDensa[] = COLUMNAS_ALERTAS_DE_COMPRA.map((titulo) => ({
    clave: titulo,
    titulo,
    ordenable: false,
    celda: titulo === "Severidad" ? (fila: FilaDensa) => <Severidad valor={severidadDeCompra(fila.Severidad ?? "")} /> : undefined,
  }));
  const filasAlertas: FilaDensa[] = datos.alertas.map((a, i) => ({ id: String(i), Severidad: a.severidad, "Qué pasa": a.texto }));
  const elegida = abierto === null ? undefined : necesidades[abierto.fila];

  return (
    <>
      <section className="silice-control__bloque" aria-labelledby="procura-alertas">
        <h2 id="procura-alertas" className="cds--type-heading-compact-02">
          Alertas de compra
        </h2>
        <p className="silice-control__nota cds--type-helper-text-01">
          Al día de hoy: lo que hay que pedir ya (desde dos días hábiles antes de la fecha límite) y lo que llegó después
          de que se necesitaba.
        </p>
        {filasAlertas.length === 0 ? (
          <p className="cds--type-body-compact-01">No hay compras por pedir ni compras tardías.</p>
        ) : (
          <TablaDensa etiqueta="Alertas de compra" columnas={columnasAlertas} filas={filasAlertas} />
        )}
      </section>
      <section className="silice-control__bloque" aria-labelledby="procura-materiales">
        <h2 id="procura-materiales" className="cds--type-heading-compact-02">
          Materiales de la obra
        </h2>
        <p className="silice-control__nota cds--type-helper-text-01">
          Los materiales de los análisis de precios de la versión de la línea base. Se necesitan el primer día de la
          primera partida que los usa y hay que pedirlos a más tardar el plazo de entrega antes. Anote aquí cuándo los
          pidió y cuándo llegaron.
        </p>
        {datos.aviso && <InlineNotification kind="warning" lowContrast hideCloseButton role="status" title={datos.aviso} />}
        <AvisoError error={errorPedido} titulo="No se anotó el pedido" />
        <p id={ID_ESTADO} role="status" tabIndex={-1} className="silice-control__estado cds--type-body-compact-01">
          {hecho}
        </p>
        <TablaDensa
          etiqueta="Materiales de la obra"
          columnas={columnas}
          filas={filasDe(necesidades)}
          vacio={{
            titulo: "Esta obra no tiene materiales que comprar",
            descripcion: "Los análisis de precios de su versión no tienen líneas de material.",
          }}
        />
      </section>
      {abierto !== null && elegida !== undefined && abierto.tipo === "recibida" && (
        <DialogoRecibida proyecto={proyecto} necesidad={elegida} alCancelar={cancelar} alHecho={terminar} />
      )}
      {abierto !== null && elegida !== undefined && abierto.tipo === "plazo" && (
        <DialogoPlazo proyecto={proyecto} necesidad={elegida} alCancelar={cancelar} alHecho={terminar} />
      )}
    </>
  );
}
