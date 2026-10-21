import { Select, SelectItem } from "@carbon/react";
import { CampoTexto } from "../../comun/CampoTexto";
import { AreaTexto } from "./AreaTexto";
import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { useAplicacion } from "../../shell/contexto";
import { BuscadorReferencia } from "./BuscadorReferencia";
import { evaluar, guardar, opciones, partida, similares as pedirSimilares } from "./cliente";
import type { Cabecera, Evaluacion, Guardado, Opciones, Similar } from "./cliente";
import "./componer.scss";
import { Guardar } from "./Guardar";
import { PanelDesglose } from "./PanelDesglose";
import { Similares } from "./Similares";
import { agregarFila, borrarFila, editarCelda, hayFilas, normalizarTablas, TIPOS, tablasVacias } from "./tablas";
import type { Fila, Tablas, TipoTabla } from "./tablas";
import { TablaInsumos } from "./TablaInsumos";

// Retardo entre la ultima edicion y la peticion a la API (plan de la ola 3 B, RB-2).
const RETARDO_MS = 300;

const CABECERA_INICIAL: Cabecera = { codigo: "", descripcion: "", unidad: "", dominio: "civil", rendimiento: "" };

function hoy(): string {
  const d = new Date();
  const dos = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
}

// UC-10 (componer) y UC-11 (editar) una partida a mano. El navegador no calcula nada: el desglose, las advertencias
// y el guardado los hace la API. La cola de la pagina clasica (cantidades de obra, elaborar) vive en «Elaborar un
// presupuesto» (RB-1).
export default function PaginaComponer() {
  const { alExpirar } = useAplicacion();
  const ultimoExpirar = useRef(alExpirar);
  useEffect(() => {
    ultimoExpirar.current = alExpirar;
  });
  const expirar = useCallback(() => ultimoExpirar.current(), []);
  // Un 401 cierra la sesion; cualquier otro error se muestra. Devuelve true si el error ya se atendio.
  const atender = useCallback(
    (e: unknown): boolean => {
      if (e instanceof ErrorDeApi && e.estado === 401) {
        expirar();
        return true;
      }
      return false;
    },
    [expirar],
  );

  const [cabecera, setCabecera] = useState<Cabecera>(CABECERA_INICIAL);
  const [fecha, setFecha] = useState(hoy);
  const [condiciones, setCondiciones] = useState("");
  const [tablas, setTablas] = useState<Tablas>(tablasVacias);
  const [ops, setOps] = useState<Opciones | null>(null);
  const [errorOpciones, setErrorOpciones] = useState<unknown>(null);

  const [evaluacion, setEvaluacion] = useState<Evaluacion | null>(null);
  const [calculando, setCalculando] = useState(false);
  const [errorDesglose, setErrorDesglose] = useState<unknown>(null);

  const [sinHistorial, setSinHistorial] = useState(false);
  const [errorPrecarga, setErrorPrecarga] = useState<unknown>(null);
  const [parecidas, setParecidas] = useState<Similar[]>([]);
  const [errorParecidas, setErrorParecidas] = useState<unknown>(null);

  const [guardando, setGuardando] = useState(false);
  const [resultado, setResultado] = useState<Guardado | null>(null);
  const [errorGuardado, setErrorGuardado] = useState<unknown>(null);

  const limpiarGuardado = () => {
    setResultado(null);
    setErrorGuardado(null);
  };
  const cambiarCabecera = (parcial: Partial<Cabecera>) => {
    setCabecera((c) => ({ ...c, ...parcial }));
    limpiarGuardado();
  };
  const cambiarTablas = (cambio: (t: Tablas) => Tablas) => {
    setTablas(cambio);
    limpiarGuardado();
  };

  // Opciones de la lista de dominios y de modalidades.
  useEffect(() => {
    let vigente = true;
    opciones()
      .then((o) => {
        if (!vigente) return;
        setOps(o);
        setCabecera((c) => (o.dominios.length > 0 && !o.dominios.includes(c.dominio) ? { ...c, dominio: o.dominios[0] } : c));
      })
      .catch((e: unknown) => {
        if (vigente && !atender(e)) setErrorOpciones(e);
      });
    return () => {
      vigente = false;
    };
  }, [atender]);

  // UC-11, paso 1: al teclear un codigo que existe se precargan las tres tablas y el rendimiento propuesto, una sola
  // vez por codigo (lo editado despues no se pisa); teclear otro codigo vuelve a precargar.
  const precargado = useRef("");
  const turnoPartida = useRef(0);
  useEffect(() => {
    const codigo = cabecera.codigo.trim();
    if (!codigo || codigo === precargado.current) return;
    const espera = setTimeout(() => {
      precargado.current = codigo;
      const mio = ++turnoPartida.current;
      partida(codigo)
        .then((r) => {
          if (mio !== turnoPartida.current) return;
          setErrorPrecarga(null);
          setSinHistorial(!r.hay_historial);
          const precarga = normalizarTablas(r.tablas);
          if (r.existe && hayFilas(precarga)) setTablas(precarga);
          if (r.existe && r.rendimiento_propuesto !== null) {
            setCabecera((c) => ({ ...c, rendimiento: r.rendimiento_propuesto as string }));
          }
        })
        .catch((e: unknown) => {
          if (mio === turnoPartida.current && !atender(e)) setErrorPrecarga(e);
        });
    }, RETARDO_MS);
    return () => clearTimeout(espera);
  }, [cabecera.codigo, atender]);

  // Desglose en vivo: 300 ms despues de la ultima edicion; la respuesta de una peticion vieja se descarta.
  const turnoEvaluar = useRef(0);
  useEffect(() => {
    const mio = ++turnoEvaluar.current;
    const espera = setTimeout(() => {
      setCalculando(true);
      evaluar(cabecera, tablas)
        .then((r) => {
          if (mio !== turnoEvaluar.current) return;
          setEvaluacion(r);
          setErrorDesglose(null);
          setCalculando(false);
        })
        .catch((e: unknown) => {
          if (mio !== turnoEvaluar.current) return;
          setCalculando(false);
          if (!atender(e)) setErrorDesglose(e);
        });
    }, RETARDO_MS);
    return () => clearTimeout(espera);
  }, [cabecera, tablas, atender]);

  // Ayuda 1: partidas parecidas a la descripcion tecleada, del dominio elegido.
  const turnoParecidas = useRef(0);
  useEffect(() => {
    const descripcion = cabecera.descripcion.trim();
    const mio = ++turnoParecidas.current;
    if (!descripcion) return;
    const espera = setTimeout(() => {
      pedirSimilares(cabecera.dominio, descripcion)
        .then((lista) => {
          if (mio !== turnoParecidas.current) return;
          setErrorParecidas(null);
          setParecidas(lista);
        })
        .catch((e: unknown) => {
          if (mio === turnoParecidas.current && !atender(e)) setErrorParecidas(e);
        });
    }, RETARDO_MS);
    return () => clearTimeout(espera);
  }, [cabecera.descripcion, cabecera.dominio, atender]);

  const guardarComposicion = async (justificacion: string | null) => {
    setGuardando(true);
    limpiarGuardado();
    try {
      setResultado(await guardar(cabecera, tablas, { fecha, condiciones, justificacion }));
    } catch (e) {
      if (!atender(e)) setErrorGuardado(e);
    } finally {
      setGuardando(false);
    }
  };

  const usarFila = (tipo: TipoTabla) => (fila: Fila) => cambiarTablas((t) => agregarFila(t, tipo, fila));
  const dominios = ops?.dominios ?? [cabecera.dominio];

  return (
    <div className="silice-componer silice-pagina">
      <h1 className="cds--type-heading-04">Componer una partida</h1>
      <p className="silice-componer__nota cds--type-body-compact-01">
        Componga una partida a mano: declare su cabecera y sus tres tablas de insumos, vea el precio unitario
        desglosarse en vivo (sin necesidad de guardar) y guarde la composición. Si la partida ya existe, sus tablas se
        precargan al teclear su código y guardar reemplaza su composición vigente; si no existe, la crea.
      </p>
      <AvisoError error={errorOpciones} titulo="No se pudieron cargar las opciones" />

      <section className="silice-componer__bloque" aria-labelledby="componer-cabecera">
        <h2 id="componer-cabecera" className="cds--type-heading-compact-02">
          Cabecera de la partida
        </h2>
        <div className="silice-componer__rejilla">
          <CampoTexto
            id="componer-codigo"
            size="sm"
            labelText="Código"
            value={cabecera.codigo}
            onChange={(e) => cambiarCabecera({ codigo: e.target.value })}
          />
          <CampoTexto
            id="componer-descripcion"
            size="sm"
            labelText="Descripción"
            value={cabecera.descripcion}
            onChange={(e) => {
              cambiarCabecera({ descripcion: e.target.value });
              if (!e.target.value.trim()) setParecidas([]);
            }}
          />
          <CampoTexto
            id="componer-unidad"
            size="sm"
            labelText="Unidad"
            value={cabecera.unidad}
            onChange={(e) => cambiarCabecera({ unidad: e.target.value })}
          />
          <Select
            id="componer-dominio"
            size="sm"
            labelText="Dominio"
            value={cabecera.dominio}
            onChange={(e) => cambiarCabecera({ dominio: e.target.value })}
          >
            {dominios.map((d) => (
              <SelectItem key={d} value={d} text={d} />
            ))}
          </Select>
          <CampoTexto
            id="componer-fecha"
            size="sm"
            type="date"
            labelText="Fecha"
            value={fecha}
            onChange={(e) => {
              setFecha(e.target.value);
              limpiarGuardado();
            }}
          />
        </div>
      </section>

      <AvisoError error={errorParecidas} titulo="No se pudieron pedir las partidas similares" />
      <Similares similares={parecidas} />

      <section className="silice-componer__bloque" aria-labelledby="componer-rendimiento">
        <h2 id="componer-rendimiento" className="cds--type-heading-compact-02">
          Rendimiento
        </h2>
        <AvisoError error={errorPrecarga} titulo="No se pudo consultar la partida" />
        <div className="silice-componer__rejilla">
          <CampoTexto
            id="componer-rendimiento-valor"
            size="sm"
            labelText="Rendimiento: unidades por día"
            value={cabecera.rendimiento}
            onChange={(e) => cambiarCabecera({ rendimiento: e.target.value })}
          />
        </div>
        {sinHistorial && cabecera.codigo.trim() !== "" && (
          <p className="silice-componer__nota cds--type-body-compact-01">
            Todavía no hay historial de rendimientos registrado para esta partida: es el comportamiento correcto, no un
            error. Declare el rendimiento con sus condiciones.
          </p>
        )}
        <AreaTexto
          id="componer-condiciones"
          labelText="Condiciones del rendimiento"
          helperText="Obligatorio: el sistema no persiste una composición cuyo rendimiento no se declare junto con las condiciones en que se obtuvo."
          rows={2}
          value={condiciones}
          onChange={(e) => {
            setCondiciones(e.target.value);
            limpiarGuardado();
          }}
        />
      </section>

      <section className="silice-componer__bloque" aria-labelledby="componer-insumos">
        <h2 id="componer-insumos" className="cds--type-heading-compact-02">
          Insumos
        </h2>
        {TIPOS.map((tipo) => (
          <div key={tipo} className="silice-componer__insumo">
            <BuscadorReferencia tipo={tipo} alUsar={usarFila(tipo)} alExpirar={expirar} />
            <TablaInsumos
              tipo={tipo}
              filas={tablas[tipo]}
              modalidades={ops?.modalidades ?? []}
              alCambiar={(i, clave, valor) => cambiarTablas((t) => editarCelda(t, tipo, i, clave, valor))}
              alAgregar={() => cambiarTablas((t) => agregarFila(t, tipo))}
              alBorrar={(i) => cambiarTablas((t) => borrarFila(t, tipo, i))}
            />
          </div>
        ))}
      </section>

      <PanelDesglose evaluacion={evaluacion} cargando={calculando} error={errorDesglose} />

      <Guardar
        sinCondiciones={condiciones.trim() === ""}
        requiereJustificacion={evaluacion?.requiere_justificacion ?? false}
        guardando={guardando}
        resultado={resultado}
        error={errorGuardado}
        alGuardar={(j) => void guardarComposicion(j)}
      />
    </div>
  );
}
