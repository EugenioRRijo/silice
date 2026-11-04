import { Button, Select, SelectItem } from "@carbon/react";
import { useContext, useEffect, useId, useState } from "react";
import { Link, useInRouterContext } from "react-router";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { CarpetaRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { InlineLoading } from "../../comun/carbonEs";
import { FranjaDelPaso } from "../../comun/FranjaDelPaso";
import { TablaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { rutaDeObra } from "../../marco/secciones";
import { useAplicacion } from "../../shell/contexto";
import { useHojaDeLaObra } from "../hoja/ProveedorDeLaHoja";
import { useCarga } from "../inicio/useCarga";
import { CodigosCiviles, Pendientes, Rendimientos, SIN_CODIGOS, codigosCompletos, seleccionCivil } from "./BloquesDelComputo";
import type { CodigosElegidos } from "./BloquesDelComputo";
import {
  AYUDA_DEL_CSV,
  DOMINIOS,
  ERROR_COMPUTO_CAMBIO,
  FALTA_LA_LISTA,
  NOMBRE_DEL_DOMINIO,
  SIN_NADA_QUE_LLEVAR,
  aceptarPropuesta,
  calcular,
  cuerpoDeValoracion,
  filasDeItems,
  listaParaValorar,
  mapeoCodigos,
  partidasParaLlevar,
  textoLlevadas,
  OTRO_BORRADOR,
} from "./logicaComputo";
import type { Dominio, ItemComputo, PartidaCatalogo, PartidaParaLlevar, PendienteConPropuestas, RendimientoPorDeclarar, TipoRendimiento } from "./tipos";
import "./computo.scss";

interface Props {
  // El .csv que se eligió en «Subir plano o cómputo».
  archivo: File;
  // Mientras hay una petición en vuelo el diálogo no se cierra.
  alOcuparse: (ocupado: boolean) => void;
  // Lo llevado ya está en el borrador: la sección vuelve a leer su registro de importaciones.
  alLlevar: () => void;
  // Con «edificación» apagada el diálogo ya se titula «Cargar cómputo» (h2): el flujo no repite ese título en un h3.
  conTitulo?: boolean;
}

// Lo que sigue tras pulsar «Llevar al presupuesto»: nada todavía, rendimientos o pendientes que resolver, o ya llevado.
type Paso =
  | { tipo: "nada" }
  | { tipo: "rendimientos"; lista: RendimientoPorDeclarar[] }
  | { tipo: "pendientes"; lista: PendienteConPropuestas[] }
  // `otroBorrador`: la API las llevó a otro borrador de la obra (el más reciente de la ficha), no al abierto aquí.
  | { tipo: "llevadas"; cuantas: number; otroBorrador: boolean };
const NADA: Paso = { tipo: "nada" };
type Ocupacion = "extrayendo" | "llevando" | "registrando" | null;

// Por qué existe (Tarea 12 del plan F4): «Cargar cómputo», el flujo de un .csv dentro del diálogo «Subir plano o cómputo»
// de Archivos y planos, absorbe la pantalla Elaborar (bajas 13 a 19). Tipo de obra del archivo → «Extraer cómputo» → la
// tabla → «Llevar al presupuesto», un solo paso que valora (`POST /presupuestos/calcular`, con la obra, la moneda de la
// carpeta y la fecha de su lista) y, si quedan rendimientos por declarar o pendientes, los muestra antes de llevar nada.
// Sin ellos lleva los ítems al MISMO borrador que el Presupuesto (`POST /v1/hoja/llevar` con el nombre del archivo, que
// queda en el registro, Tarea 10) y lo vuelve a leer (`refrescar`). No muestra el presupuesto elaborado: va directo a
// Partidas. Solo lo monta `paginas/archivos/index.tsx`, y solo para quien puede editar la Hoja.
export function CargarComputo({ archivo, alOcuparse, alLlevar, conTitulo = true }: Props) {
  const { sesion, alExpirar } = useAplicacion();
  const hoja = useHojaDeLaObra();
  const obra = useContext(ContextoDeLaObra);
  const enRuta = useInRouterContext();
  const idTitulo = useId();
  const carpeta = useCarga<CarpetaRespuesta>("/v1/carpeta", alExpirar);
  const [dominio, setDominio] = useState<Dominio>("civil");
  const esCivil = dominio === "civil";
  const catalogo = useCarga<PartidaCatalogo[]>(esCivil ? "/partidas?dominio=civil" : null, alExpirar);
  const partidas = catalogo.estado === "listo" ? catalogo.datos.filter((p) => p.dominio === "civil") : [];
  const [elegidos, setElegidos] = useState<CodigosElegidos>(SIN_CODIGOS);
  const [items, setItems] = useState<ItemComputo[] | null>(null);
  const [paso, setPaso] = useState<Paso>(NADA);
  const [ocupado, setOcupado] = useState<Ocupacion>(null);
  const [fallo, setFallo] = useState<{ titulo: string; error: unknown } | null>(null);

  useEffect(() => {
    alOcuparse(ocupado !== null);
    return () => alOcuparse(false);
  }, [ocupado, alOcuparse]);

  const valorar = carpeta.estado === "listo" ? listaParaValorar(carpeta.datos) : null;
  const sinLista = carpeta.estado === "listo" && valorar === null;
  const hayItems = items !== null && items.length > 0;
  const puedeExtraer = ocupado === null && (!esCivil || codigosCompletos(elegidos, partidas));
  const puedeLlevar = ocupado === null && hayItems && valorar !== null;

  // Corre `trabajo` con la ocupación puesta; un error queda a la vista con `titulo` (y un 401 cierra la sesión).
  async function ocupar(que: Exclude<Ocupacion, null>, titulo: string, trabajo: () => Promise<void>) {
    setOcupado(que);
    setFallo(null);
    try {
      await trabajo();
    } catch (error) {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
      setFallo({ titulo, error });
    } finally {
      setOcupado(null);
    }
  }

  const extraer = () =>
    ocupar("extrayendo", "No se pudo extraer el cómputo", async () => {
      setItems(null);
      setPaso(NADA);
      const datos = new FormData();
      datos.append("archivo", archivo);
      if (esCivil) datos.append("codigos", JSON.stringify(mapeoCodigos(seleccionCivil(elegidos))));
      setItems(await pedir<ItemComputo[]>(`/computos/${dominio}`, { metodo: "POST", cuerpo: datos }));
    });

  async function enviar(lista: PartidaParaLlevar[]) {
    if (lista.length === 0) {
      setFallo({ titulo: "No se llevó nada al presupuesto", error: SIN_NADA_QUE_LLEVAR });
      return;
    }
    const abierto = hoja.estado.estado === "listo" ? hoja.estado.borrador.id : null;
    const r = await pedir<{ borrador_id: string }>("/v1/hoja/llevar", {
      metodo: "POST",
      cuerpo: { proyecto: hoja.proyecto, partidas: lista, archivo: archivo.name },
    });
    setPaso({ tipo: "llevadas", cuantas: lista.length, otroBorrador: r.borrador_id !== abierto });
    alLlevar();
    await hoja.refrescar();
  }

  // «Llevar al presupuesto» valora y, sin nada que resolver, lleva. «Llevar sin los pendientes» (`sinPendientes`) también
  // vuelve a valorar antes, como Elaborar: una propuesta aplicada cambió el código de un ítem que aún no se valoró (menor 4
  // de la Tarea 12); deja fuera los pendientes que dé esta valoración. Si pide rendimientos, se muestran y no se lleva nada.
  const valorarYLlevar = (sinPendientes: boolean) =>
    ocupar("llevando", "No se llevó nada al presupuesto", async () => {
      if (items === null || valorar === null) return;
      const r = await calcular(cuerpoDeValoracion({ proyecto: hoja.proyecto, ...valorar, items }), sesion.csrf);
      if (r.tipo === "rendimientos") setPaso({ tipo: "rendimientos", lista: r.lista });
      else if (!sinPendientes && r.respuesta.pendientes.length > 0) setPaso({ tipo: "pendientes", lista: r.respuesta.pendientes });
      else await enviar(partidasParaLlevar(items, sinPendientes ? r.respuesta.pendientes : []));
    });
  const llevar = () => valorarYLlevar(false);
  const llevarSinPendientes = () => valorarYLlevar(true);

  const registrar = (entrada: RendimientoPorDeclarar, tipo: TipoRendimiento) =>
    ocupar("registrando", "No se pudo registrar el rendimiento", async () => {
      if (valorar === null) return;
      const cuerpo = { codigo_partida: entrada.codigo_partida, tipo, fecha: valorar.fecha };
      await pedir("/presupuestos/calcular/declarar-rendimiento", { metodo: "POST", cuerpo });
      setPaso((p) => {
        if (p.tipo !== "rendimientos") return p;
        const quedan = p.lista.filter((e) => e.codigo_partida !== entrada.codigo_partida);
        return quedan.length > 0 ? { ...p, lista: quedan } : NADA;
      });
    });

  function aplicar(pendiente: PendienteConPropuestas, elegido: string) {
    const nuevos = items === null ? null : aceptarPropuesta(items, pendiente, elegido);
    if (nuevos === null) {
      setFallo({ titulo: "No se aplicó la propuesta", error: ERROR_COMPUTO_CAMBIO });
      return;
    }
    setItems(nuevos);
    setPaso((p) => {
      if (p.tipo !== "pendientes") return p;
      const quedan = p.lista.filter((x) => x !== pendiente);
      return quedan.length > 0 ? { ...p, lista: quedan } : NADA;
    });
  }

  const cambiarDominio = (nuevo: Dominio) => {
    setDominio(nuevo);
    setItems(null);
    setPaso(NADA);
  };

  return (
    <section aria-labelledby={conTitulo ? idTitulo : undefined} aria-label={conTitulo ? undefined : "Cómputo"} className="silice-computo">
      {conTitulo && (
        <h3 id={idTitulo} className="cds--type-heading-compact-01">
          Cargar cómputo
        </h3>
      )}
      {sinLista && <FranjaDelPaso tipo="falta" texto={FALTA_LA_LISTA} />}
      {carpeta.estado !== "listo" && carpeta.estado !== "cargando" && <AvisoError error={carpeta.error} titulo="No se pudo leer la carpeta" />}
      <Select id="computo-dominio" labelText="Tipo de obra del archivo" size="sm" value={dominio} onChange={(e) => cambiarDominio(e.target.value as Dominio)}>
        {DOMINIOS.map((d) => (
          <SelectItem key={d} value={d} text={NOMBRE_DEL_DOMINIO[d]} />
        ))}
      </Select>
      <p className="cds--type-helper-text-01">{AYUDA_DEL_CSV}</p>
      {esCivil && <CodigosCiviles carga={catalogo} partidas={partidas} elegidos={elegidos} alCambiar={setElegidos} />}
      <div className="silice-computo__acciones">
        <Button kind={hayItems ? "secondary" : "primary"} size="md" disabled={!puedeExtraer} onClick={() => void extraer()}>
          Extraer cómputo
        </Button>
        {ocupado === "extrayendo" && <InlineLoading description="Extrayendo..." />}
      </div>
      {hayItems && (
        <section aria-label="Cómputo extraído" className="silice-computo__bloque">
          <h4 className="cds--type-heading-compact-01">Cómputo extraído</h4>
          <TablaDensa
            etiqueta="Cómputo extraído"
            columnas={[
              { clave: "codigo_partida", titulo: "Partida" },
              { clave: "descripcion", titulo: "Descripción" },
              { clave: "unidad", titulo: "Unidad" },
              { clave: "cantidad", titulo: "Cantidad", numerica: true, presentar: formatoEsVe },
              { clave: "origen_id", titulo: "Origen" },
              { clave: "origen_tipo", titulo: "Tipo de origen" },
              { clave: "regla", titulo: "Regla" },
            ]}
            filas={filasDeItems(items)}
          />
        </section>
      )}
      {paso.tipo === "rendimientos" && <Rendimientos lista={paso.lista} ocupado={ocupado !== null} alRegistrar={(e, t) => void registrar(e, t)} />}
      {paso.tipo === "pendientes" && (
        <Pendientes
          lista={paso.lista}
          ocupado={ocupado !== null}
          alAplicar={aplicar}
          alLlevarSinEllos={partidasParaLlevar(items ?? [], paso.lista).length > 0 ? () => void llevarSinPendientes() : undefined}
        />
      )}
      {hayItems && paso.tipo !== "llevadas" && (
        <div className="silice-computo__acciones">
          <Button kind="primary" size="md" disabled={!puedeLlevar} onClick={() => void llevar()}>
            Llevar al presupuesto
          </Button>
          {ocupado === "llevando" && <InlineLoading description="Llevando al presupuesto..." />}
        </div>
      )}
      {fallo !== null && <AvisoError error={fallo.error} titulo={fallo.titulo} alCerrar={() => setFallo(null)} />}
      {paso.tipo === "llevadas" && (
        <div role="status" className="silice-computo__exito">
          <p className="cds--type-body-compact-01">{textoLlevadas(paso.cuantas)}</p>
          {paso.otroBorrador && <p className="cds--type-body-compact-01">{OTRO_BORRADOR}</p>}
          {obra !== null && enRuta && (
            <Link className="cds--link" to={rutaDeObra(obra.carpeta, obra.obraId, "presupuesto")} onClick={() => hoja.irAPestana("partidas")}>
              Ver en Partidas
            </Link>
          )}
        </div>
      )}
    </section>
  );
}
