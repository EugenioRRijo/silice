import { Button, InlineNotification, Select, SelectItem } from "@carbon/react";
import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { reaccionar } from "./fallos";
import type { Reacciones } from "./fallos";
import { ahoraLocalISO, fechaIsoDe, leerCantidad } from "./formato";
import type { MaterialRespuesta, MovimientoRespuesta, SospechosoRespuesta } from "./tipos";
import { useRecurso } from "./useRecurso";
import type { Recurso } from "./useRecurso";
import { CampoTexto } from "../../comun/CampoTexto";

interface Props {
  materiales: Recurso<MaterialRespuesta[]>;
  // Se resolvio un pesaje: nace un despacho, hay que volver a leer el tablero.
  alResolver: () => void;
  reacciones: Reacciones;
}

const RUTA_SOSPECHOSOS = "/v1/produccion/pesajes-sospechosos";

const SIN_DATO = "—";
const dato = (texto: string) => (texto.trim() === "" ? SIN_DATO : texto);

// «Arena  Lavada» y «arena lavada» son lo mismo; las tildes tampoco cuentan.
function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

// El material que el archivo nombra, si coincide con el codigo o el nombre de uno registrado; si no, vacio: elegir un
// material a ciegas registraria un despacho en el lugar equivocado.
function materialDelArchivo(texto: string, materiales: MaterialRespuesta[]): string {
  const buscado = normalizar(texto);
  if (buscado === "") return "";
  const coincide = materiales.find((m) => normalizar(m.codigo) === buscado || normalizar(m.nombre) === buscado);
  return coincide?.codigo ?? "";
}

function aFila(s: SospechosoRespuesta): FilaDensa {
  return {
    id: String(s.id),
    fila: String(s.fila),
    ticket: dato(s.ticket),
    fecha: dato(s.fecha_texto),
    placa: dato(s.placa),
    material: dato(s.material_texto),
    bruto: dato(s.bruto_texto),
    tara: dato(s.tara_texto),
    neto: dato(s.neto_texto),
    motivo: s.motivo,
    accion: "",
  };
}

interface PropsFormulario {
  sospechoso: SospechosoRespuesta;
  materiales: MaterialRespuesta[];
  ocupado: boolean;
  alResolver: (id: number, cuerpo: ResolverCuerpo, material: string) => void;
  alDescartar: (id: number) => void;
  alCerrar: () => void;
}

interface ResolverCuerpo {
  material_codigo: string;
  fecha: string;
  neto_t: string;
  ticket: string;
}

interface ErroresResolver {
  material?: string;
  fecha?: string;
  ticket?: string;
  neto?: string;
}

function FormularioPesaje({ sospechoso, materiales, ocupado, alResolver, alDescartar, alCerrar }: PropsFormulario) {
  // Se parte de lo que dice el archivo, solo cuando es claro; el neto nunca: es justo lo que no se pudo confiar.
  const [material, setMaterial] = useState(() => materialDelArchivo(sospechoso.material_texto, materiales));
  const [fecha, setFecha] = useState(() => fechaIsoDe(sospechoso.fecha_texto));
  const [ticket, setTicket] = useState(sospechoso.ticket);
  const [neto, setNeto] = useState("");
  const [errores, setErrores] = useState<ErroresResolver>({});

  const resolver = (evento: FormEvent) => {
    evento.preventDefault();
    const nuevos: ErroresResolver = {};
    if (material === "") nuevos.material = "Elija el material correcto.";
    if (fechaIsoDe(fecha) === "") nuevos.fecha = "Escriba la fecha del despacho.";
    if (ticket.trim() === "") nuevos.ticket = "Escriba el ticket del despacho.";
    let valorNeto = "";
    if (neto.trim() === "") {
      nuevos.neto = "Escriba el peso neto en toneladas.";
    } else {
      const lectura = leerCantidad(neto, "del peso neto");
      if ("error" in lectura) nuevos.neto = lectura.error;
      else valorNeto = lectura.valor;
    }
    setErrores(nuevos);
    if (Object.keys(nuevos).length > 0) return;
    alResolver(sospechoso.id, { material_codigo: material, fecha, neto_t: valorNeto, ticket: ticket.trim() }, material);
  };

  return (
    <form className="existencias-formulario existencias-pesaje" onSubmit={resolver} noValidate>
      <h3 className="cds--type-heading-compact-02">{`Pesaje de la fila ${sospechoso.fila}`}</h3>
      <p className="existencias-nota cds--type-body-compact-01">{`Motivo: ${sospechoso.motivo}. Corrija lo que haga falta y resuélvalo como despacho, o descártelo si no corresponde.`}</p>
      <Select
        id={`pesaje-${sospechoso.id}-material`}
        labelText="Material correcto"
        value={material}
        onChange={(e) => setMaterial(e.target.value)}
        invalid={errores.material !== undefined}
        invalidText={errores.material ?? ""}
      >
        <SelectItem value="" text="Elija un material" />
        {materiales.map((m) => (
          <SelectItem key={m.codigo} value={m.codigo} text={`${m.codigo} · ${m.nombre}`} />
        ))}
      </Select>
      <CampoTexto
        id={`pesaje-${sospechoso.id}-fecha`}
        type="date"
        labelText="Fecha"
        value={fecha}
        onChange={(e) => setFecha(e.target.value)}
        invalid={errores.fecha !== undefined}
        invalidText={errores.fecha ?? ""}
      />
      <CampoTexto
        id={`pesaje-${sospechoso.id}-ticket`}
        labelText="Ticket"
        autoComplete="off"
        value={ticket}
        onChange={(e) => setTicket(e.target.value)}
        invalid={errores.ticket !== undefined}
        invalidText={errores.ticket ?? ""}
      />
      <CampoTexto
        id={`pesaje-${sospechoso.id}-neto`}
        labelText="Peso neto (t)"
        inputMode="decimal"
        autoComplete="off"
        value={neto}
        onChange={(e) => setNeto(e.target.value)}
        invalid={errores.neto !== undefined}
        invalidText={errores.neto ?? ""}
      />
      <div className="existencias-acciones">
        <Button type="submit" kind="primary" size="md" disabled={ocupado}>
          Resolver como despacho
        </Button>
        <Button type="button" kind="danger--tertiary" size="md" disabled={ocupado} onClick={() => alDescartar(sospechoso.id)}>
          Descartar
        </Button>
        <Button type="button" kind="ghost" size="md" onClick={alCerrar}>
          Cerrar
        </Button>
      </div>
    </form>
  );
}

function pesajesPorResolver(n: number): string {
  return n === 1 ? "1 pesaje por resolver" : `${n} pesajes por resolver`;
}

// Bandeja «Pesajes sospechosos» (RF-131, RF-133): lo dudoso de la bascula no entra solo al inventario; una persona
// lo corrige y lo resuelve como despacho, o lo descarta. Queda quien y cuando.
export function PestanaBandeja({ materiales, alResolver, reacciones }: Props) {
  const [version, setVersion] = useState(0);
  const [abierto, setAbierto] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const lista = useRecurso<SospechosoRespuesta[]>(RUTA_SOSPECHOSOS, version, reacciones.alExpirar, reacciones.alDenegar);
  const recargar = useCallback(() => setVersion((n) => n + 1), []);

  const columnas: ColumnaDensa[] = [
    // Sin orden: la bandeja se lee en el orden del archivo (fila), y asi cada encabezado se anuncia con su nombre.
    { clave: "fila", titulo: "Fila", numerica: true, ordenable: false },
    { clave: "ticket", titulo: "Ticket", ordenable: false },
    { clave: "fecha", titulo: "Fecha", ordenable: false },
    { clave: "placa", titulo: "Placa", ordenable: false },
    { clave: "material", titulo: "Material", ordenable: false },
    { clave: "bruto", titulo: "Bruto", ordenable: false },
    { clave: "tara", titulo: "Tara", ordenable: false },
    { clave: "neto", titulo: "Neto", ordenable: false },
    { clave: "motivo", titulo: "Motivo", ordenable: false },
    {
      clave: "accion",
      titulo: "Acción",
      ordenable: false,
      celda: (f) => (
        <Button
          kind="ghost"
          size="sm"
          aria-label={`Revisar el pesaje de la fila ${f.fila}`}
          onClick={() => {
            setAviso(null);
            setError(null);
            setAbierto(Number(f.id));
          }}
        >
          Revisar
        </Button>
      ),
    },
  ];

  const resolver = async (id: number, cuerpo: ResolverCuerpo, codigo: string) => {
    setOcupado(true);
    setError(null);
    setAviso(null);
    try {
      await pedir<MovimientoRespuesta>(`${RUTA_SOSPECHOSOS}/${id}/resolver`, {
        metodo: "POST",
        cuerpo: { ...cuerpo, ahora: ahoraLocalISO() },
      });
      setAviso(`Pesaje resuelto: despacho de ${codigo} registrado.`);
      setAbierto(null);
      recargar();
      alResolver();
    } catch (razon) {
      setError(reaccionar(razon, reacciones));
    } finally {
      setOcupado(false);
    }
  };

  const descartar = async (id: number) => {
    setOcupado(true);
    setError(null);
    setAviso(null);
    try {
      await pedir<undefined>(`${RUTA_SOSPECHOSOS}/${id}/descartar`, { metodo: "POST", cuerpo: { ahora: ahoraLocalISO() } });
      setAviso("Pesaje descartado: no se registró ningún despacho.");
      setAbierto(null);
      recargar();
    } catch (razon) {
      setError(reaccionar(razon, reacciones));
      // Otra sesion pudo haberlo cerrado ya: se vuelve a leer la bandeja para que la lista diga la verdad.
      recargar();
    } finally {
      setOcupado(false);
    }
  };

  const avisos = (
    <>
      <AvisoError error={error} titulo="No se pudo completar la acción" />
      {aviso && <InlineNotification kind="success" role="status" lowContrast hideCloseButton title={aviso} />}
    </>
  );

  if (lista.estado === "cargando") {
    return (
      <div className="existencias-bloque">
        <TablaDensa etiqueta="Pesajes sospechosos" columnas={columnas} filas={[]} cargando />
      </div>
    );
  }
  if (lista.estado === "error") {
    return (
      <div className="existencias-bloque">
        <AvisoError error={lista.error} titulo="No se pudo leer la bandeja" />
        <div>
          <Button kind="tertiary" size="md" onClick={recargar}>
            Reintentar
          </Button>
        </div>
      </div>
    );
  }

  const pendientes = lista.datos;
  const abiertoSospechoso = pendientes.find((s) => s.id === abierto);
  const activos = materiales.estado === "listo" ? materiales.datos.filter((m) => m.activo) : [];

  if (pendientes.length === 0) {
    return (
      <div className="existencias-bloque">
        {avisos}
        <EstadoVacio
          titulo="No hay pesajes sospechosos por resolver"
          descripcion="Lo dudoso de los reportes de báscula aparece aquí al importarlos."
        />
      </div>
    );
  }

  return (
    <div className="existencias-bloque">
      {avisos}
      <p className="existencias-nota cds--type-body-compact-01">{pesajesPorResolver(pendientes.length)}</p>
      <TablaDensa etiqueta="Pesajes sospechosos" columnas={columnas} filas={pendientes.map(aFila)} />
      {abiertoSospechoso && (
        <FormularioPesaje
          key={abiertoSospechoso.id}
          sospechoso={abiertoSospechoso}
          materiales={activos}
          ocupado={ocupado}
          alResolver={(id, cuerpo, codigo) => void resolver(id, cuerpo, codigo)}
          alDescartar={(id) => void descartar(id)}
          alCerrar={() => setAbierto(null)}
        />
      )}
    </div>
  );
}
