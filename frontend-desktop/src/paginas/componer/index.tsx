import { Select, SelectItem } from "@carbon/react";
import { CampoTexto } from "../../comun/CampoTexto";
import { AreaTexto } from "../../comun/AreaTexto";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { ErrorDeApi } from "../../api/cliente";
import type { CarpetaRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { useAplicacion } from "../../shell/contexto";
import { useNavegarSeguro } from "../../shell/navegarSeguro";
import { useFormularioSucio } from "../../shell/sucio";
import { BuscadorReferencia } from "./BuscadorReferencia";
import { AvisoSinLista } from "./AvisoSinLista";
import type { Desde } from "./AvisoSinLista";
import {
  carpeta as pedirCarpeta,
  crearListaParaArmar,
  evaluar,
  guardar,
  opciones,
  partida,
  prever,
  similares as pedirSimilares,
} from "./cliente";
import type { Cabecera, DatosDeGuardado, Desglose, Evaluacion, Guardado, Opciones, Prevision, Similar } from "./cliente";
import "./componer.scss";
import { DialogoVariantes } from "./DialogoVariantes";
import { Guardar } from "./Guardar";
import { PanelDesglose } from "./PanelDesglose";
import { Similares } from "./Similares";
import { AYUDA_CIFRAS } from "../../indicadores/cifraEscrita";
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

// Lo que la persona escribio y se perderia: algun campo de la cabecera o de las condiciones, o alguna fila con algo
// escrito (una fila agregada y vacia no cuenta). La fecha y el dominio traen su valor y no cuentan solos.
function hayDatos(cabecera: Cabecera, condiciones: string, tablas: Tablas): boolean {
  const escrito = (v: string | undefined) => (v ?? "").trim() !== "";
  return (
    [cabecera.codigo, cabecera.descripcion, cabecera.unidad, cabecera.rendimiento, condiciones].some(escrito) ||
    TIPOS.some((t) => tablas[t].some((fila) => Object.values(fila).some(escrito)))
  );
}

// UC-10 (componer) y UC-11 (editar) una partida a mano. El navegador no calcula nada: el desglose, las advertencias
// y el guardado los hace la API. La cola de la pagina clasica (cantidades de obra, elaborar) vive en Archivos y planos ›
// «Cargar cómputo» (F4, Tarea 12, baja 19; antes, «Elaborar un presupuesto», RB-1).
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

  // Desde la Hoja (plan de montar, T4 y T11): `?codigo=X&volver=hoja` trae el codigo y, guardada, ofrece volver.
  const [parametros] = useSearchParams();
  const volverAHoja = parametros.get("volver") === "hoja";
  const navegarSeguro = useNavegarSeguro();
  const [cabecera, setCabecera] = useState<Cabecera>(() => ({
    ...CABECERA_INICIAL,
    codigo: parametros.get("codigo")?.trim() ?? "",
  }));
  const [fecha, setFecha] = useState(hoy);
  const [condiciones, setCondiciones] = useState("");
  const [tablas, setTablas] = useState<Tablas>(tablasVacias);
  const [ops, setOps] = useState<Opciones | null>(null);
  const [carpeta, setCarpeta] = useState<CarpetaRespuesta | null>(null);
  const [listaCreada, setListaCreada] = useState<CarpetaRespuesta["lista"]>(null);
  const [creandoLista, setCreandoLista] = useState(false);
  const [errorLista, setErrorLista] = useState<unknown>(null);
  const [errorOpciones, setErrorOpciones] = useState<unknown>(null);

  const [evaluacion, setEvaluacion] = useState<Evaluacion | null>(null);
  // El ultimo desglose valido; con el formulario vacio se olvida.
  const [ultimoDesglose, setUltimoDesglose] = useState<Desglose | null>(null);
  const [calculando, setCalculando] = useState(false);
  const [errorDesglose, setErrorDesglose] = useState<unknown>(null);

  const [sinHistorial, setSinHistorial] = useState(false);
  const [errorPrecarga, setErrorPrecarga] = useState<unknown>(null);
  const [parecidas, setParecidas] = useState<Similar[]>([]);
  const [errorParecidas, setErrorParecidas] = useState<unknown>(null);

  const [guardando, setGuardando] = useState(false);
  const [resultado, setResultado] = useState<Guardado | null>(null);
  const [errorGuardado, setErrorGuardado] = useState<unknown>(null);
  // Lo que dijo `prever` cuando algun precio quedaria como variante, con lo que se iba a guardar: abre el dialogo.
  const [porConfirmar, setPorConfirmar] = useState<{ prevision: Prevision; datos: DatosDeGuardado } | null>(null);
  const botonGuardar = useRef<HTMLButtonElement>(null);
  // La persona cambio algo (lo que trae la URL o la precarga no cuenta). Con algo escrito y sin guardar, salir de la
  // pantalla por un control de Silice pregunta antes (foco 2 del plan de montar; MOD-2).
  const [tocado, setTocado] = useState(false);
  useFormularioSucio("componer", tocado && hayDatos(cabecera, condiciones, tablas) && resultado === null);

  const limpiarGuardado = () => {
    setResultado(null);
    setErrorGuardado(null);
  };
  const cambiarCabecera = (parcial: Partial<Cabecera>) => {
    setCabecera((c) => ({ ...c, ...parcial }));
    setTocado(true);
    limpiarGuardado();
  };
  const cambiarTablas = (cambio: (t: Tablas) => Tablas) => {
    setTablas(cambio);
    setTocado(true);
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

  // La moneda de trabajo y la lista para armar de la carpeta (D-MP1). Se pregunta al abrir (al cambiar de carpeta el
  // Shell vuelve a montar la pagina) y otra vez si guardar responde 409. Si la API no la da (otra base que SQLite) no se
  // avisa nada ni se inventa la moneda: guardar lo dira si hace falta.
  const [lecturaCarpeta, setLecturaCarpeta] = useState(0);
  useEffect(() => {
    let vigente = true;
    pedirCarpeta()
      .then((r) => {
        if (vigente) setCarpeta(r);
      })
      .catch((e: unknown) => {
        if (vigente) atender(e);
      });
    return () => {
      vigente = false;
    };
  }, [atender, lecturaCarpeta]);

  const crearLista = async (desde: Desde) => {
    setCreandoLista(true);
    setErrorLista(null);
    try {
      const nueva = await crearListaParaArmar(desde);
      setCarpeta(nueva);
      setListaCreada(nueva.aviso === null ? nueva.lista : null);
    } catch (e) {
      if (atender(e)) return;
      setErrorLista(e);
      // 409: la carpeta pudo cambiar en otra pestana (ya tiene lista, o sigue sin tasa): se relee y el aviso se ajusta.
      if (e instanceof ErrorDeApi && e.estado === 409) setLecturaCarpeta((n) => n + 1);
    } finally {
      setCreandoLista(false);
    }
  };

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
          if (r.desglose) setUltimoDesglose(r.desglose);
          else if (r.estado === "vacio") setUltimoDesglose(null);
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

  const fallarGuardado = (e: unknown) => {
    if (atender(e)) return;
    setErrorGuardado(e);
    // 409: la carpeta no tiene lista para armar en su moneda (pudo cambiar en otra pestana): se relee y el aviso de
    // arriba ofrece sus salidas.
    if (e instanceof ErrorDeApi && e.estado === 409) setLecturaCarpeta((n) => n + 1);
  };

  const confirmarGuardado = async (datos: DatosDeGuardado) => {
    setGuardando(true);
    try {
      setResultado(await guardar(cabecera, tablas, datos));
    } catch (e) {
      fallarGuardado(e);
    } finally {
      setGuardando(false);
    }
  };

  // D-MP2: antes de guardar se pregunta a `prever` (no escribe); si algun precio tecleado quedaria como variante solo
  // para este APU, se dice y la persona decide. Sin variantes se guarda de una vez, con el mismo cuerpo.
  const guardarComposicion = async (justificacion: string | null) => {
    const datos: DatosDeGuardado = { fecha, condiciones, justificacion };
    setGuardando(true);
    limpiarGuardado();
    let previsto: Prevision;
    try {
      previsto = await prever(cabecera, tablas, datos);
    } catch (e) {
      fallarGuardado(e);
      setGuardando(false);
      return;
    }
    if (previsto.variantes.length > 0) {
      setGuardando(false);
      setPorConfirmar({ prevision: previsto, datos });
      return;
    }
    await confirmarGuardado(datos);
  };

  // Al cerrar el dialogo el foco vuelve a «Guardar composición» (mientras se preveia estuvo deshabilitado).
  const cerrarDialogo = () => {
    setPorConfirmar(null);
    botonGuardar.current?.focus();
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
      <AvisoSinLista
        carpeta={carpeta}
        creada={listaCreada}
        creando={creandoLista}
        error={errorLista}
        alCrear={(desde) => void crearLista(desde)}
      />
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
            Todavía no hay historial de rendimientos para esta partida: declare el rendimiento y las condiciones en que
            se obtuvo.
          </p>
        )}
        <AreaTexto
          id="componer-condiciones"
          labelText="Condiciones del rendimiento"
          helperText="Obligatorio: Sílice no guarda una composición sin las condiciones en que se obtuvo su rendimiento."
          rows={2}
          value={condiciones}
          onChange={(e) => {
            setCondiciones(e.target.value);
            setTocado(true);
            limpiarGuardado();
          }}
        />
      </section>

      <section className="silice-componer__bloque" aria-labelledby="componer-insumos">
        <h2 id="componer-insumos" className="cds--type-heading-compact-02">
          Insumos
        </h2>
        {carpeta?.moneda && (
          <p className="silice-componer__moneda cds--type-body-compact-01">{`Precios en ${carpeta.moneda}`}</p>
        )}
        <p className="silice-componer__nota cds--type-body-compact-01">
          {AYUDA_CIFRAS}
        </p>
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

      <PanelDesglose
        evaluacion={evaluacion}
        cargando={calculando}
        error={errorDesglose}
        anterior={ultimoDesglose}
        moneda={carpeta?.moneda ?? null}
      />

      <Guardar
        sinCondiciones={condiciones.trim() === ""}
        requiereJustificacion={evaluacion?.requiere_justificacion ?? false}
        guardando={guardando}
        resultado={resultado}
        error={errorGuardado}
        alGuardar={(j) => void guardarComposicion(j)}
        sinLista={Boolean(carpeta?.aviso)}
        alVolverAHoja={volverAHoja ? () => void navegarSeguro("/hoja") : undefined}
        refBoton={botonGuardar}
      />
      {porConfirmar && (
        <DialogoVariantes
          prevision={porConfirmar.prevision}
          alVolver={cerrarDialogo}
          alGuardar={() => {
            const { datos } = porConfirmar;
            cerrarDialogo();
            void confirmarGuardado(datos);
          }}
        />
      )}
    </div>
  );
}
