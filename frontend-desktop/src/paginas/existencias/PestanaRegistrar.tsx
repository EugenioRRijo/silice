import { Button, InlineNotification, Select, SelectItem, SkeletonText, Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useState } from "react";
import type { FormEvent } from "react";
import { pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { reaccionar } from "./fallos";
import type { Reacciones } from "./fallos";
import { fechaIsoDe, hoyISO, leerCantidad, mostrarCantidad, rotuloUnidad } from "./formato";
import type { MaterialRespuesta, MovimientoRespuesta, TipoDeMovimiento } from "./tipos";
import type { Recurso } from "./useRecurso";
import { CampoTexto } from "../../comun/CampoTexto";

interface Props {
  materiales: Recurso<MaterialRespuesta[]>;
  // Se registro un movimiento: hay que volver a leer el tablero.
  alRegistrar: () => void;
  // Se creo un material: hay que volver a leer la lista y el tablero.
  alCrearMaterial: () => void;
  reacciones: Reacciones;
}

const RUTA_MOVIMIENTOS = "/v1/produccion/movimientos";
const RUTA_MATERIALES = "/v1/produccion/materiales";

interface Descripcion {
  deQue: string; // sigue a «la cantidad»
  rotuloCantidad: (unidad: string) => string;
  boton: string;
  permiteCero: boolean;
}

const DESCRIPCIONES: Record<TipoDeMovimiento, Descripcion> = {
  entrada: {
    deQue: "de la entrada",
    rotuloCantidad: (u) => `Cantidad (${u})`,
    boton: "Registrar entrada",
    permiteCero: false,
  },
  despacho: {
    deQue: "del despacho",
    rotuloCantidad: (u) => `Cantidad (${u})`,
    boton: "Registrar despacho",
    permiteCero: false,
  },
  ajuste: {
    deQue: "del conteo",
    rotuloCantidad: (u) => `Lo contado (${u})`,
    boton: "Registrar conteo",
    permiteCero: true,
  },
};

function SinMateriales() {
  return (
    <p className="existencias-nota cds--type-body-compact-01">
      No hay materiales registrados. Créelos en «Material nuevo».
    </p>
  );
}

interface PropsFormulario {
  tipo: TipoDeMovimiento;
  materiales: MaterialRespuesta[];
  alRegistrar: () => void;
  reacciones: Reacciones;
}

function FormularioMovimiento({ tipo, materiales, alRegistrar, reacciones }: PropsFormulario) {
  const descripcion = DESCRIPCIONES[tipo];
  const [codigo, setCodigo] = useState(materiales[0].codigo);
  const [cantidad, setCantidad] = useState("");
  const [fecha, setFecha] = useState(() => hoyISO());
  const [nota, setNota] = useState("");
  const [errorCantidad, setErrorCantidad] = useState<string | null>(null);
  const [errorFecha, setErrorFecha] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const material = materiales.find((m) => m.codigo === codigo) ?? materiales[0];
  const unidad = rotuloUnidad(material.unidad_venta);

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault();
    setError(null);
    setAviso(null);
    const lectura = leerCantidad(cantidad, descripcion.deQue, { permiteCero: descripcion.permiteCero });
    const fechaValida = fechaIsoDe(fecha) !== "";
    setErrorCantidad("error" in lectura ? lectura.error : null);
    setErrorFecha(fechaValida ? null : "Escriba la fecha.");
    if ("error" in lectura || !fechaValida) return;

    setEnviando(true);
    try {
      const respuesta = await pedir<MovimientoRespuesta | null>(RUTA_MOVIMIENTOS, {
        metodo: "POST",
        cuerpo: {
          material_codigo: material.codigo,
          tipo,
          fecha,
          cantidad: lectura.valor,
          nota: nota.trim(),
        },
      });
      const dicha = `${mostrarCantidad(lectura.valor)} ${unidad} de ${material.codigo}`;
      if (tipo === "entrada") setAviso(`Entrada registrada: ${dicha}.`);
      else if (tipo === "despacho") setAviso(`Despacho registrado: ${dicha}.`);
      else setAviso(respuesta === null ? "El conteo coincide con la existencia: no hizo falta ajustar." : "Conteo registrado.");
      setCantidad("");
      setNota("");
      alRegistrar();
    } catch (razon) {
      setError(reaccionar(razon, reacciones));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="existencias-formulario" onSubmit={(e) => void enviar(e)} noValidate>
      {tipo === "ajuste" && (
        <p className="existencias-nota cds--type-body-compact-01">
          Escriba lo que contó en el patio. Sílice guarda la diferencia con la existencia que tenía registrada.
        </p>
      )}
      <Select id={`mov-${tipo}-material`} labelText="Material" value={material.codigo} onChange={(e) => setCodigo(e.target.value)}>
        {materiales.map((m) => (
          <SelectItem key={m.codigo} value={m.codigo} text={`${m.codigo} · ${m.nombre}`} />
        ))}
      </Select>
      <CampoTexto
        id={`mov-${tipo}-cantidad`}
        labelText={descripcion.rotuloCantidad(unidad)}
        inputMode="decimal"
        autoComplete="off"
        value={cantidad}
        onChange={(e) => setCantidad(e.target.value)}
        invalid={errorCantidad !== null}
        invalidText={errorCantidad ?? ""}
      />
      <CampoTexto
        id={`mov-${tipo}-fecha`}
        type="date"
        labelText="Fecha"
        value={fecha}
        onChange={(e) => setFecha(e.target.value)}
        invalid={errorFecha !== null}
        invalidText={errorFecha ?? ""}
      />
      <CampoTexto
        id={`mov-${tipo}-nota`}
        labelText="Nota (opcional)"
        autoComplete="off"
        value={nota}
        onChange={(e) => setNota(e.target.value)}
      />
      <AvisoError error={error} titulo="No se pudo registrar" />
      {aviso && <InlineNotification kind="success" role="status" lowContrast hideCloseButton title={aviso} />}
      <div>
        <Button type="submit" kind="primary" size="md" disabled={enviando}>
          {descripcion.boton}
        </Button>
      </div>
    </form>
  );
}

interface PropsMaterialNuevo {
  alCrear: () => void;
  reacciones: Reacciones;
}

interface ErroresMaterial {
  codigo?: string;
  nombre?: string;
  minima?: string;
  densidad?: string;
}

function FormularioMaterial({ alCrear, reacciones }: PropsMaterialNuevo) {
  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [unidad, setUnidad] = useState("m3");
  const [minima, setMinima] = useState("");
  const [densidad, setDensidad] = useState("");
  const [errores, setErrores] = useState<ErroresMaterial>({});
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault();
    setError(null);
    setAviso(null);
    const nuevos: ErroresMaterial = {};
    const codigoLimpio = codigo.trim();
    if (!codigoLimpio) nuevos.codigo = "Escriba el código del material.";
    if (!nombre.trim()) nuevos.nombre = "Escriba el nombre del material.";
    let valorMinima = "";
    if (!minima.trim()) {
      nuevos.minima = "Escriba la existencia mínima.";
    } else {
      const lectura = leerCantidad(minima, "de la existencia mínima", { permiteCero: true });
      if ("error" in lectura) nuevos.minima = lectura.error;
      else valorMinima = lectura.valor;
    }
    let valorDensidad: string | null = null;
    if (densidad.trim()) {
      const lectura = leerCantidad(densidad, "de la densidad");
      if ("error" in lectura) nuevos.densidad = lectura.error;
      else valorDensidad = lectura.valor;
    }
    setErrores(nuevos);
    if (Object.keys(nuevos).length > 0) return;

    setEnviando(true);
    try {
      await pedir<MaterialRespuesta>(RUTA_MATERIALES, {
        metodo: "POST",
        cuerpo: {
          codigo: codigoLimpio,
          nombre: nombre.trim(),
          unidad_venta: unidad,
          existencia_minima: valorMinima,
          ...(valorDensidad !== null ? { densidad_t_m3: valorDensidad } : {}),
        },
      });
      setAviso(`Material creado: ${codigoLimpio}.`);
      setCodigo("");
      setNombre("");
      setMinima("");
      setDensidad("");
      alCrear();
    } catch (razon) {
      setError(reaccionar(razon, reacciones));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="existencias-formulario" onSubmit={(e) => void enviar(e)} noValidate>
      <p className="existencias-nota cds--type-body-compact-01">
        La existencia mínima y la densidad son datos de la empresa: Sílice no pone ningún valor por defecto. La
        densidad solo hace falta para convertir pesos de la báscula a metros cúbicos.
      </p>
      <CampoTexto
        id="material-codigo"
        labelText="Código"
        autoComplete="off"
        value={codigo}
        onChange={(e) => setCodigo(e.target.value)}
        invalid={errores.codigo !== undefined}
        invalidText={errores.codigo ?? ""}
      />
      <CampoTexto
        id="material-nombre"
        labelText="Nombre"
        autoComplete="off"
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
        invalid={errores.nombre !== undefined}
        invalidText={errores.nombre ?? ""}
      />
      <Select id="material-unidad" labelText="Unidad de venta" value={unidad} onChange={(e) => setUnidad(e.target.value)}>
        <SelectItem value="m3" text="m³" />
        <SelectItem value="t" text="t" />
      </Select>
      <CampoTexto
        id="material-minima"
        labelText="Existencia mínima"
        inputMode="decimal"
        autoComplete="off"
        helperText={`En ${rotuloUnidad(unidad)}.`}
        value={minima}
        onChange={(e) => setMinima(e.target.value)}
        invalid={errores.minima !== undefined}
        invalidText={errores.minima ?? ""}
      />
      <CampoTexto
        id="material-densidad"
        labelText="Densidad (t/m³, opcional)"
        inputMode="decimal"
        autoComplete="off"
        value={densidad}
        onChange={(e) => setDensidad(e.target.value)}
        invalid={errores.densidad !== undefined}
        invalidText={errores.densidad ?? ""}
      />
      <AvisoError error={error} titulo="No se pudo crear el material" />
      {aviso && <InlineNotification kind="success" role="status" lowContrast hideCloseButton title={aviso} />}
      <div>
        <Button type="submit" kind="primary" size="md" disabled={enviando}>
          Crear material
        </Button>
      </div>
    </form>
  );
}

// Entrada (produccion), despacho, conteo fisico y material nuevo (RF-127, RF-128). Cada formulario valida lo que
// escribe la persona antes de llamar a la API y muestra el `detalle` de la API tal cual si esta rechaza.
export function PestanaRegistrar({ materiales, alRegistrar, alCrearMaterial, reacciones }: Props) {
  const [seccion, setSeccion] = useState(0);

  const movimiento = (tipo: TipoDeMovimiento) => {
    if (materiales.estado === "cargando") {
      return (
        <div role="status" aria-busy="true" aria-label="Cargando materiales">
          <SkeletonText paragraph lineCount={3} />
        </div>
      );
    }
    if (materiales.estado === "error") return <AvisoError error={materiales.error} titulo="No se pudo leer los materiales" />;
    const activos = materiales.datos.filter((m) => m.activo);
    if (activos.length === 0) return <SinMateriales />;
    return <FormularioMovimiento tipo={tipo} materiales={activos} alRegistrar={alRegistrar} reacciones={reacciones} />;
  };

  return (
    <div className="existencias-bloque">
      <p className="existencias-nota cds--type-body-compact-01">
        Un despacho nunca se bloquea: si deja la existencia en negativo se registra igual y el tablero lo marca. Para
        corregirla, registre la producción (entrada) o un conteo físico.
      </p>
      <Tabs selectedIndex={seccion} onChange={({ selectedIndex }) => setSeccion(selectedIndex)}>
        <TabList aria-label="Qué desea registrar" contained>
          <Tab>Entrada</Tab>
          <Tab>Despacho</Tab>
          <Tab>Conteo físico</Tab>
          <Tab>Material nuevo</Tab>
        </TabList>
        <TabPanels>
          <TabPanel>{seccion === 0 && movimiento("entrada")}</TabPanel>
          <TabPanel>{seccion === 1 && movimiento("despacho")}</TabPanel>
          <TabPanel>{seccion === 2 && movimiento("ajuste")}</TabPanel>
          <TabPanel>{seccion === 3 && <FormularioMaterial alCrear={alCrearMaterial} reacciones={reacciones} />}</TabPanel>
        </TabPanels>
      </Tabs>
    </div>
  );
}
