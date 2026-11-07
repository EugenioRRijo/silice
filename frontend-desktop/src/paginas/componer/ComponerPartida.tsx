import { Select, SelectItem } from "@carbon/react";
import { CampoTexto } from "../../comun/CampoTexto";
import { AreaTexto } from "../../comun/AreaTexto";
import { useCallback, useEffect, useRef, useState } from "react";
import type { JSX } from "react";
import { ErrorDeApi } from "../../api/cliente";
import type { CarpetaRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import type { PartidaHallada } from "../../comun/logicaBusqueda";
import { useAplicacion } from "../../shell/contexto";
import { useFormularioSucio } from "../../shell/sucio";
import { mismoDatoDeCabecera } from "./cabecera";
import { BuscadorReferencia } from "./BuscadorReferencia";
import { CampoDelCodigo } from "./CampoDelCodigo";
import { CampoDeUnidad } from "../../comun/CampoDeUnidad";
import { esCodigoValido } from "./codigo";
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
import { agregarFila, borrarFila, completarFila, editarCelda, hayFilas, normalizarTablas, TIPOS, tablasVacias } from "./tablas";
import type { Fila, Tablas, TipoTabla } from "./tablas";
import { TablaInsumos } from "./TablaInsumos";

// Lo que se anuncia junto a «Fecha»: cuantos precios del catalogo son de otra lista y cuantos no se pudieron comprobar. Nada
// si no hay ninguno.
function avisoDeListas(listas: Record<TipoTabla, { otras: number; quiza: number }>): string {
  const otras = TIPOS.reduce((n, t) => n + listas[t].otras, 0);
  const quiza = TIPOS.reduce((n, t) => n + listas[t].quiza, 0);
  const partes = [
    otras === 0 ? "" : otras === 1 ? "1 precio es de otra lista; revíselo." : `${otras} precios son de otra lista; revíselos.`,
    quiza === 0 ? "" : quiza === 1 ? "1 precio puede ser de otra lista; revíselo." : `${quiza} precios pueden ser de otra lista; revíselos.`,
  ];
  return partes.filter(Boolean).join(" ");
}

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

// La partida que se acaba de guardar en el catalogo: el dialogo «Agregar partida» la deja elegida (codigo, descripcion y
// unidad, para que la cantidad diga en que se mide).
export interface PartidaCompuesta {
  codigo: string;
  descripcion: string;
  unidad: string;
}

interface Props {
  codigoInicial: string;
  // La descripción con que se pidió componer (pulido F5, Tarea 1): en «Agregar partida», lo escrito que no es un código.
  descripcionInicial?: string;
  // El nivel del titulo que la encabeza (el h1 de la pantalla o el h2 del panel): sus bloques van un nivel por debajo.
  nivelDelTitulo: 1 | 2;
  alGuardar: (partida: PartidaCompuesta) => void;
}

// Por que existe (plan F4, Tarea 9): la composicion de una partida sin h1 ni navegacion, para la pantalla «Componer una
// partida» (que sigue en Ctrl+K hasta F5) y para el panel de «Agregar partida» (`paginas/hoja/ComponerEnPanel.tsx`), que
// compone sin salir de la obra (baja 21). Pasa de 250 lineas porque es el cuerpo entero de la pantalla de antes, con sus
// cinco lecturas en vivo (opciones, carpeta, precarga, desglose y parecidas) y el guardado en dos pasos; partirlo
// repartiria ese estado entre piezas que no se usan solas.
//
// UC-10 (componer) y UC-11 (editar) una partida a mano. El navegador no calcula nada: el desglose, las advertencias
// y el guardado los hace la API. La cola de la pagina clasica (cantidades de obra, elaborar) vive en Archivos y planos ›
// «Cargar cómputo» (F4, Tarea 12, baja 19; antes, «Elaborar un presupuesto», RB-1).
export function ComponerPartida({ codigoInicial, descripcionInicial = "", nivelDelTitulo, alGuardar }: Props): JSX.Element {
  const nivel = nivelDelTitulo === 1 ? 2 : 3;
  const Titulo = `h${nivel}` as const;
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

  const [cabecera, setCabecera] = useState<Cabecera>(() => ({
    ...CABECERA_INICIAL,
    codigo: codigoInicial.trim(),
    descripcion: descripcionInicial.trim(),
  }));
  const [fecha, setFecha] = useState(hoy);
  // Cuantos precios llenados desde el catalogo tienen otra lista que la de la «Fecha» (o no se pudo comprobar), por tabla: se
  // anuncia una vez, junto al campo «Fecha», en una region viva (dictamen de la ronda 2, MENOR 2; WCAG 4.1.3).
  const [listas, setListas] = useState<Record<TipoTabla, { otras: number; quiza: number }>>({
    materiales: { otras: 0, quiza: 0 },
    equipos: { otras: 0, quiza: 0 },
    mano_obra: { otras: 0, quiza: 0 },
  });
  const medirListas = useCallback((tipo: TipoTabla, otras: number, quiza: number) => {
    setListas((l) => (l[tipo].otras === otras && l[tipo].quiza === quiza ? l : { ...l, [tipo]: { otras, quiza } }));
  }, []);
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
  // D17 y ronda 3 (B, C): lo que puso la ultima partida elegida del catalogo en la descripcion y la unidad, y su codigo. Al elegir
  // una partida del catalogo siempre se ponen su descripcion y su unidad (el servidor no deja guardar una partida existente con
  // otra, `motivo_para_no_reemplazar`); si se reemplaza algo que no era del catalogo (lo tecleado, o la descripcion con que llega
  // la pantalla) se dice. Al cambiar el codigo por otro, lo que puso el catalogo se vacia (se guarda en `retirado` para devolverlo
  // si el codigo vuelve al elegido, p. ej. con Esc en el panel); lo tecleado se queda.
  const delCatalogo = useRef<{ codigo?: string; descripcion?: string; unidad?: string }>({});
  const retirado = useRef<{ descripcion?: string; unidad?: string }>({});
  const [avisoDeCabecera, setAvisoDeCabecera] = useState("");
  const elegirDelCatalogo = (p: PartidaHallada) => {
    const parcial: Partial<Cabecera> = { codigo: p.codigo };
    const avisos: string[] = [];
    for (const [campo, nuevo, rotulo] of [
      ["descripcion", p.descripcion, "la descripción"],
      ["unidad", p.unidad, "la unidad"],
    ] as const) {
      const actual = cabecera[campo];
      // N4: sin los bordes y por la grafía escrita, como compara el servidor (`cabecera.ts`).
      if (actual.trim() !== "" && !mismoDatoDeCabecera(campo, actual, nuevo) && actual !== delCatalogo.current[campo]) {
        avisos.push(`Se cambió ${rotulo} «${actual}» por la del catálogo, «${nuevo}».`);
      }
      parcial[campo] = nuevo;
      delCatalogo.current[campo] = nuevo;
    }
    delCatalogo.current.codigo = p.codigo;
    retirado.current = {};
    cambiarCabecera(parcial);
    setAvisoDeCabecera(avisos.join(" "));
  };
  // Cualquier cambio del codigo que no sea elegir una partida del catalogo (teclear, «Usar … como codigo», una partida vial).
  const cambiarCodigo = (codigo: string) => {
    const parcial: Partial<Cabecera> = { codigo };
    for (const campo of ["descripcion", "unidad"] as const) {
      if (codigo === delCatalogo.current.codigo) {
        const devuelto = retirado.current[campo];
        if (devuelto !== undefined && cabecera[campo] === "") parcial[campo] = devuelto;
        delete retirado.current[campo];
      } else if (delCatalogo.current[campo] !== undefined && cabecera[campo] === delCatalogo.current[campo]) {
        retirado.current[campo] = cabecera[campo];
        parcial[campo] = "";
      }
    }
    if (parcial.descripcion === "") setParecidas([]);
    cambiarCabecera(parcial);
    setAvisoDeCabecera("");
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
  // Cuantas veces una precarga reemplazo las tres tablas. Las tablas de insumos recuerdan por indice de fila lo que se tecleo y
  // lo que puso el catalogo; una precarga trae filas nuevas y nada de eso es suyo, asi que reciben la vuelta como prop para
  // reiniciar ese estado sin volver a montarse (dictamen de la ronda 3, MENOR 2 y WCAG 2.4.3).
  const [vueltaDePrecarga, setVueltaDePrecarga] = useState(0);
  const turnoPartida = useRef(0);
  // N6 (ronda 4): lo que puso la ultima precarga (las tablas y el rendimiento) y lo que hay ahora en pantalla. Al pasar a otra
  // partida que existe pero no trae composicion, lo que todavia es la precarga anterior se vacia; lo que la persona edito se
  // conserva y se avisa. Es el mismo criterio de origen de las tablas de insumos: lo que no es de la persona se reemplaza.
  const dePrecarga = useRef<{ tablas: Tablas | null; rendimiento: string | null }>({ tablas: null, rendimiento: null });
  const vivo = useRef({ tablas, rendimiento: cabecera.rendimiento });
  useEffect(() => {
    vivo.current = { tablas, rendimiento: cabecera.rendimiento };
  });
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
          if (r.existe) {
            const previa = dePrecarga.current;
            if (hayFilas(precarga)) {
              setTablas(precarga);
              setVueltaDePrecarga((n) => n + 1);
              dePrecarga.current.tablas = precarga;
            } else if (previa.tablas !== null) {
              if (JSON.stringify(vivo.current.tablas) === JSON.stringify(previa.tablas)) {
                setTablas(tablasVacias());
                setVueltaDePrecarga((n) => n + 1);
              } else {
                const dicho = `La partida «${codigo}» no tiene composición en el catálogo; se conservan las líneas que escribió.`;
                setAvisoDeCabecera((a) => (a === "" ? dicho : `${a} ${dicho}`));
              }
              dePrecarga.current.tablas = null;
            }
            if (r.rendimiento_propuesto !== null) {
              setCabecera((c) => ({ ...c, rendimiento: r.rendimiento_propuesto as string }));
              dePrecarga.current.rendimiento = r.rendimiento_propuesto;
            } else if (previa.rendimiento !== null) {
              if (vivo.current.rendimiento === previa.rendimiento) setCabecera((c) => ({ ...c, rendimiento: "" }));
              dePrecarga.current.rendimiento = null;
            }
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
      alGuardar({ codigo: cabecera.codigo.trim(), descripcion: cabecera.descripcion.trim(), unidad: cabecera.unidad.trim() });
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
    <div className="silice-componer__cuerpo">
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
        <Titulo id="componer-cabecera" className="cds--type-heading-compact-02">
          Cabecera de la partida
        </Titulo>
        <div className="silice-componer__rejilla">
          <CampoDelCodigo
            texto={cabecera.codigo}
            alCambiar={cambiarCodigo}
            alElegirDelCatalogo={elegirDelCatalogo}
            alExpirar={expirar}
          />
          <CampoTexto
            id="componer-descripcion"
            size="sm"
            labelText="Descripción"
            value={cabecera.descripcion}
            onChange={(e) => {
              cambiarCabecera({ descripcion: e.target.value });
              setAvisoDeCabecera("");
              if (!e.target.value.trim()) setParecidas([]);
            }}
          />
          <CampoDeUnidad
            id="componer-unidad"
            etiqueta="Unidad"
            texto={cabecera.unidad}
            alCambiar={(unidad) => {
              cambiarCabecera({ unidad });
              setAvisoDeCabecera("");
            }}
            alExpirar={expirar}
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
          <div>
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
            <p id="componer-fecha-estado" role="status" aria-live="polite" className="cds--form__helper-text">
              {avisoDeListas(listas)}
            </p>
          </div>
        </div>
        <p id="componer-cabecera-aviso" role="status" aria-live="polite" className="cds--form__helper-text">
          {avisoDeCabecera}
        </p>
      </section>

      <AvisoError error={errorParecidas} titulo="No se pudieron pedir las partidas similares" />
      <Similares similares={parecidas} nivel={nivel} />

      <section className="silice-componer__bloque" aria-labelledby="componer-rendimiento">
        <Titulo id="componer-rendimiento" className="cds--type-heading-compact-02">
          Rendimiento
        </Titulo>
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
        <Titulo id="componer-insumos" className="cds--type-heading-compact-02">
          Insumos
        </Titulo>
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
              vuelta={vueltaDePrecarga}
              paraArmarAl={fecha}
              moneda={carpeta?.moneda ?? null}
              alCambiar={(i, clave, valor) => cambiarTablas((t) => editarCelda(t, tipo, i, clave, valor))}
              alAgregar={() => cambiarTablas((t) => agregarFila(t, tipo))}
              alBorrar={(i) => cambiarTablas((t) => borrarFila(t, tipo, i))}
              alCompletar={(i, valores) => cambiarTablas((t) => completarFila(t, tipo, i, valores))}
              alExpirar={expirar}
              alMedirListas={medirListas}
              nivel={nivel === 2 ? 3 : 4}
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
        nivel={nivel}
      />

      <Guardar
        sinCondiciones={condiciones.trim() === ""}
        requiereJustificacion={evaluacion?.requiere_justificacion ?? false}
        guardando={guardando}
        resultado={resultado}
        error={errorGuardado}
        alGuardar={(j) => void guardarComposicion(j)}
        sinLista={Boolean(carpeta?.aviso)}
        codigoInvalido={cabecera.codigo.trim() !== "" && !esCodigoValido(cabecera.codigo)}
        refBoton={botonGuardar}
        nivel={nivel}
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
