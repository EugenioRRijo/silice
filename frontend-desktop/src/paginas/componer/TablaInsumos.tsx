import { Button, Select, SelectItem, Table, TableBody, TableCell, TableHead, TableRow } from "@carbon/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { TableHeader } from "../../comun/carbonEs";
import { CampoConBusqueda } from "../../comun/CampoConBusqueda";
import { CampoTexto } from "../../comun/CampoTexto";
import { buscadorDeConsulta } from "../../comun/consulta";
import type { SugerenciaDeConsulta } from "../../comun/consulta";
import { LARGO_MAXIMO } from "../../comun/logicaBusqueda";
import { ErrorDeApi } from "../../api/cliente";
import type { OpcionDeBusqueda } from "../../comun/logicaBusqueda";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import { COLUMNA_DEL_PRECIO, TABLA_DE_CONSULTA, aplicarEleccion, columnasDelCatalogo } from "./autocompletado";
import type { Conflicto, Llenado } from "./autocompletado";
import { CampoDeUnidad } from "./CampoDeUnidad";
import { COLUMNAS, TITULOS } from "./tablas";
import type { Fila, TipoTabla } from "./tablas";

interface Props {
  tipo: TipoTabla;
  filas: Fila[];
  // Opciones de modalidad que manda la API (solo mano de obra).
  modalidades: string[];
  // Cuantas veces una precarga reemplazo las tres tablas: al cambiar, se reinicia el estado interno de origen de
  // datos (marcas, tecleadas, deFuera) sin volver a montar la tabla, para preservar el foco (WCAG 2.4.3).
  vuelta?: number;
  // La fecha de la composicion (ISO): el precio que se llena es el de la lista para armar a esa fecha (AC1b). Vacia, no se
  // pide ningun precio y solo se llenan la descripcion y la unidad.
  paraArmarAl?: string;
  // La moneda de trabajo de la carpeta (`GET /v1/carpeta`): un precio en otra moneda no se copia.
  moneda?: string | null;
  alCambiar: (indice: number, clave: string, valor: string) => void;
  alAgregar: () => void;
  alBorrar: (indice: number) => void;
  // Al elegir una sugerencia del catalogo: varias celdas de la fila a la vez (descripcion, unidad y precio).
  alCompletar: (indice: number, valores: Record<string, string>) => void;
  // La sesion vencio mientras se buscaba (401).
  alExpirar: () => void;
  // Cuantos precios llenados desde el catalogo quedaron con otra lista que la de la «Fecha» actual (`otras`) o no se pudo
  // comprobar (`quiza`): la pantalla lo anuncia una vez junto al campo «Fecha». Se avisa solo cuando cambia.
  alMedirListas?: (tipo: TipoTabla, otras: number, quiza: number) => void;
  // El nivel de su titulo: h3 en la pantalla, h4 en el panel de «Agregar partida» (plan F4, Tarea 9).
  nivel?: 3 | 4;
}

const AVISO_PROPIA = "Descripción propia: no viene del catálogo.";

// Que se sabe del origen de una fila: lo ultimo que se tecleo en la descripcion, la ultima que se eligio del catalogo y que
// celdas lleno el catalogo y con que valor. La descripcion es «propia» (se avisa) si es lo tecleado y no coincide con lo
// elegido; una fila precargada o llenada desde la referencia no tiene marca y no se avisa nada.
interface Marca {
  catalogo?: string;
  escrita?: string;
  // Por que no se lleno el precio de lo elegido (otra moneda): lo dice la celda del precio o del sueldo mientras siga vacia.
  avisoPrecio?: string;
  // Las celdas (unidad, precio o sueldo) que puso el catalogo y todavia son suyas: al elegir otro insumo se reemplazan o se
  // vacian; las que la persona escribio no estan aqui y no se pisan (dictamen del autocompletado, BLOQUEANTE).
  llenado?: Llenado;
  // Lo que el catalogo tiene y no se escribio porque la persona ya habia puesto otra cosa en esa celda.
  conflictos?: Record<string, Conflicto>;
  // El codigo del insumo elegido, la fecha de la composicion con que se pidio el precio y la de su lista: si la «Fecha» cambia y
  // el precio sigue siendo el del catalogo, se comprueba si rige otra lista y, solo entonces, la celda lo dice (el precio no se
  // toca).
  codigo?: string;
  fecha?: string;
  fechaPrecio?: string;
  // Lo que vino de fuera y se reemplazo o se quito al elegir (con lo que quedo en la celda): la celda lo dice mientras siga asi.
  cambios?: Record<string, Conflicto>;
}

// Que lista rige para la «Fecha» actual respecto de la del precio llenado.
type EstadoDeLista = { tipo: "misma" } | { tipo: "pendiente" } | { tipo: "nose" } | { tipo: "otra"; motivo: string };

// Lo que se aprendio de la API sobre la lista de un insumo a una fecha: la fecha de su lista, o null si no tiene precio a esa
// fecha. Clave: «codigo@fecha». Un fallo de la consulta no se guarda aqui sino en `sinSaber`.
type ListasPorFecha = Record<string, { fechaPrecio: string | null }>;

// Una tabla de insumos editable (UC-10, pasos 2 a 4). Carbon `sm`: celdas de texto; los montos se teclean y se
// muestran como texto, alineados a la derecha, y nunca se convierten en el navegador.
//
// La descripcion es un campo con sugerencias del catalogo (AC1, pedido de Eugenio del 2026-10-21): materiales y equipos
// piden «insumos» y la mano de obra «salarios_cct». Al elegir se llenan tambien la unidad y el precio, que vienen en la
// misma respuesta: el precio es el de la lista para armar a la fecha de la composicion y solo se copia en la moneda de la
// carpeta; si no, la celda del precio dice por que quedo vacia (AC1b). Escribir una descripcion propia sigue siendo
// posible y queda avisado. La unidad de un material sugiere las que ya usa el catalogo y admite una propia (AC4).
export function TablaInsumos({
  tipo,
  filas,
  modalidades,
  vuelta = 0,
  paraArmarAl = "",
  moneda = null,
  alCambiar,
  alAgregar,
  alBorrar,
  alCompletar,
  alExpirar,
  alMedirListas,
  nivel = 3,
}: Props) {
  const Titulo = `h${nivel}` as const;
  const titulo = TITULOS[tipo];
  const columnas = COLUMNAS[tipo];
  const buscador = useMemo(
    () => buscadorDeConsulta(TABLA_DE_CONSULTA[tipo], { detalle: true, paraArmarAl, mostrarPrecio: paraArmarAl !== "" }),
    [tipo, paraArmarAl],
  );
  const [marcas, setMarcas] = useState<Record<number, Marca>>({});
  // Lo que la persona tecleo en la unidad y el precio (o sueldo) de cada fila: solo eso es suyo; lo demas vino de fuera.
  const [tecleadas, setTecleadas] = useState<Record<number, Llenado>>({});
  // Lo que habia en la celda la primera vez que la persona la toco y no era ni suyo ni del catalogo: lo que vino de fuera (la
  // precarga de una partida, «Usar esta fila» de MaPreX). Si la persona vuelve a escribir ese mismo valor, no es un tecleo.
  const [deFuera, setDeFuera] = useState<Record<number, Llenado>>({});
  const [listas, setListas] = useState<ListasPorFecha>({});
  // Las consultas de lista que fallaron: se dice con prudencia, pero el fallo no se guarda para siempre. Se olvida al cambiar la
  // «Fecha» y entonces se vuelve a preguntar (dictamen de la ronda 3, MENOR 3).
  const [sinSaber, setSinSaber] = useState<Record<string, true>>({});
  // Con otra «Fecha» se olvida lo que no se supo (se ajusta el estado al renderizar, como pide React): se vuelve a preguntar.
  const [fechaVista, setFechaVista] = useState(paraArmarAl);
  if (fechaVista !== paraArmarAl) {
    setFechaVista(paraArmarAl);
    setSinSaber({});
  }
  // Con otra vuelta de precarga se reinicia el origen de cada fila (se ajusta el estado al renderizar, como pide React).
  const [vueltaVista, setVueltaVista] = useState(vuelta);
  if (vueltaVista !== vuelta) {
    setVueltaVista(vuelta);
    setMarcas({});
    setTecleadas({});
    setDeFuera({});
  }
  const pedidas = useRef(new Set<string>());
  const vivo = useRef(true);
  useEffect(() => {
    vivo.current = true;
    return () => {
      vivo.current = false;
    };
  }, []);
  const columnaDelPrecio = COLUMNA_DEL_PRECIO[tipo];
  const delCatalogo = columnasDelCatalogo(tipo);

  // Las marcas van por indice, pero las filas tambien cambian desde fuera (la precarga de una partida, la referencia): una
  // marca solo vale mientras la descripcion de la fila siga siendo la que ella recuerda (dictamen, sospecha de TablaInsumos).
  const marcaDe = (indice: number, fila: Fila | undefined): Marca | undefined => {
    const marca = marcas[indice];
    const descripcion = fila?.descripcion ?? "";
    return marca !== undefined && (descripcion === marca.catalogo || descripcion === marca.escrita) ? marca : undefined;
  };

  const marcar = (indice: number, cambio: Marca) => setMarcas((m) => ({ ...m, [indice]: { ...m[indice], ...cambio } }));

  const escribir = (indice: number, texto: string) => {
    marcar(indice, { escrita: texto, avisoPrecio: undefined, conflictos: undefined, cambios: undefined });
    alCambiar(indice, "descripcion", texto);
  };

  // Lo que la persona escribe en la unidad o en el precio es suyo desde ese momento (y solo eso): el catalogo no lo vuelve a
  // pisar. Lo que vino de fuera (precarga, MaPreX) no se teclea y por eso se reemplaza.
  //
  // El origen de una celda se decide por su VALOR, no por el evento (dictamen de la ronda 3, MAYOR 1): Esc en el panel devuelve
  // un campo a su valor con un evento `input` que llega aqui como cualquier cambio. Si el valor nuevo es el que puso el catalogo
  // (la marca lo recuerda hasta la siguiente eleccion) o el que vino de fuera, la celda vuelve a ser de quien lo puso y deja de
  // contar como tecleada.
  const editar = (indice: number, clave: string, valor: string) => {
    if (delCatalogo.includes(clave)) {
      const previo = filas[indice]?.[clave] ?? "";
      const delCatalogoAhora = marcaDe(indice, filas[indice])?.llenado?.[clave];
      const tecleadoAntes = tecleadas[indice]?.[clave];
      const fueraAntes = deFuera[indice]?.[clave];
      // Lo que habia antes de tocarla y no era ni del catalogo ni tecleado vino de fuera: se recuerda la primera vez.
      const fuera = fueraAntes ?? (previo !== delCatalogoAhora && previo !== tecleadoAntes ? previo : undefined);
      setMarcas((m) => {
        const marca = m[indice];
        if (marca === undefined) return m;
        const conflictos = { ...marca.conflictos };
        const cambios = { ...marca.cambios };
        delete conflictos[clave];
        delete cambios[clave];
        return { ...m, [indice]: { ...marca, conflictos, cambios } };
      });
      if (fueraAntes === undefined && fuera !== undefined) {
        setDeFuera((f) => ({ ...f, [indice]: { ...f[indice], [clave]: fuera } }));
      }
      const esDeLaPersona = valor.trim() !== "" && valor !== delCatalogoAhora && valor !== fuera;
      setTecleadas((t) => {
        const propias = { ...t[indice] };
        if (esDeLaPersona) propias[clave] = valor;
        else delete propias[clave];
        return { ...t, [indice]: propias };
      });
    }
    alCambiar(indice, clave, valor);
  };

  const sinLaFila = <T,>(previo: Record<number, T>, indice: number): Record<number, T> =>
    Object.fromEntries(
      Object.entries(previo)
        .filter(([clave]) => Number(clave) !== indice)
        .map(([clave, valor]) => [Number(clave) > indice ? Number(clave) - 1 : Number(clave), valor]),
    );

  const borrar = (indice: number) => {
    setMarcas((m) => sinLaFila(m, indice));
    setTecleadas((t) => sinLaFila(t, indice));
    setDeFuera((f) => sinLaFila(f, indice));
    alBorrar(indice);
  };

  // Devuelve lo que hay que decir en voz alta (region viva del campo): la ayuda de la celda del precio o de la unidad no se
  // anuncia sola.
  const elegir = (indice: number, opcion: OpcionDeBusqueda<SugerenciaDeConsulta>): string | undefined => {
    const fila = filas[indice] ?? {};
    const eleccion = aplicarEleccion(tipo, opcion.valor, moneda, fila, {
      llenado: marcaDe(indice, fila)?.llenado ?? {},
      tecleado: tecleadas[indice] ?? {},
    });
    setMarcas((m) => ({
      ...m,
      [indice]: {
        catalogo: eleccion.valores.descripcion,
        avisoPrecio: eleccion.aviso ?? undefined,
        llenado: eleccion.llenado,
        conflictos: eleccion.conflictos,
        cambios: eleccion.cambios,
        codigo: opcion.valor.valor,
        fecha: paraArmarAl,
        fechaPrecio: opcion.valor.fecha_precio ?? undefined,
      },
    }));
    // Lo que vino de fuera en esas celdas ya se reemplazo o se quito.
    setDeFuera((f) => ({ ...f, [indice]: {} }));
    alCompletar(indice, eleccion.valores);
    const dicho = [
      ...Object.values(eleccion.cambios).map((c) => c.aviso),
      eleccion.aviso,
      ...Object.values(eleccion.conflictos).map((c) => c.aviso),
    ]
      .filter(Boolean)
      .join(" ");
    return dicho === "" ? undefined : dicho;
  };

  // Que lista rige para la «Fecha» de ahora respecto de la del precio llenado (dictamen de la ronda 2, MENOR 2). Sin pedir
  // nada se sabe en dos casos: la lista que rige a una fecha es la ultima que empezo antes, asi que si la fecha nueva esta entre
  // el inicio de la lista del precio y la fecha con que se pidio, es la misma lista; y si es anterior al inicio, esa lista aun
  // no regia. Una fecha posterior puede tener una lista nueva: se le pregunta a la API por el mismo insumo (una vez por insumo
  // y fecha) y se compara la fecha de su lista; mientras responde no se dice nada, y si no responde se avisa con prudencia.
  const estadoDeLista = (marca: Marca): EstadoDeLista => {
    if (paraArmarAl === "" || marca.fecha === undefined || marca.fecha === paraArmarAl) return { tipo: "misma" };
    const inicio = marca.fechaPrecio;
    if (inicio !== undefined && paraArmarAl >= inicio && paraArmarAl <= marca.fecha) return { tipo: "misma" };
    if (inicio !== undefined && paraArmarAl < inicio) return { tipo: "otra", motivo: "esa lista todavía no regía" };
    if (marca.codigo === undefined) return { tipo: "nose" };
    const clave = `${marca.codigo}@${paraArmarAl}`;
    const sabido = listas[clave];
    if (sabido === undefined) return sinSaber[clave] ? { tipo: "nose" } : { tipo: "pendiente" };
    if (inicio === undefined) return { tipo: "nose" };
    if (sabido.fechaPrecio === null) return { tipo: "otra", motivo: "este insumo no tiene precio en la lista" };
    return sabido.fechaPrecio === inicio
      ? { tipo: "misma" }
      : { tipo: "otra", motivo: `rige la del ${fechaEsVe(sabido.fechaPrecio)}` };
  };

  // El estado de la lista de una fila cuyo precio sigue siendo el que puso el catalogo (si no, no hay nada que decir).
  const listaDe = (indice: number, fila: Fila): EstadoDeLista => {
    const marca = marcaDe(indice, fila);
    const llenado = marca?.llenado?.[columnaDelPrecio];
    if (marca === undefined || llenado === undefined || (fila[columnaDelPrecio] ?? "") !== llenado) return { tipo: "misma" };
    return estadoDeLista(marca);
  };
  const estados = filas.map((fila, i) => listaDe(i, fila));
  const otras = estados.filter((e) => e.tipo === "otra").length;
  const quiza = estados.filter((e) => e.tipo === "nose").length;
  useEffect(() => {
    alMedirListas?.(tipo, otras, quiza);
  }, [alMedirListas, tipo, otras, quiza]);

  // Pregunta a la API la lista de la fecha nueva de cada insumo que lo necesita (el mismo buscador de la descripcion).
  useEffect(() => {
    filas.forEach((fila, i) => {
      const marca = marcaDe(i, fila);
      if (marca?.codigo === undefined || marca.catalogo === undefined || listaDe(i, fila).tipo !== "pendiente") return;
      const clave = `${marca.codigo}@${paraArmarAl}`;
      if (pedidas.current.has(clave)) return;
      pedidas.current.add(clave);
      const codigo = marca.codigo;
      // Un fallo (la API no respondio o no hallo el insumo) se dice con prudencia, pero no se guarda: `pedidas` lo suelta y
      // `sinSaber` solo vive hasta que la «Fecha» cambie.
      const noSupe = () => {
        pedidas.current.delete(clave);
        if (vivo.current) setSinSaber((s) => ({ ...s, [clave]: true }));
      };
      // El codigo exacto es lo primero que ordena la API (`aplicacion/busqueda.py`, rango 0): no depende del tope de 20 ni de
      // cuantas descripciones se parezcan.
      buscador(codigo.slice(0, LARGO_MAXIMO).trim(), new AbortController().signal, 20)
        .then((grupos) => {
          const hallada = grupos.flatMap((g) => g.opciones).find((o) => o.valor.valor === codigo);
          if (hallada === undefined) noSupe();
          else if (vivo.current) setListas((l) => ({ ...l, [clave]: { fechaPrecio: hallada.valor.fecha_precio ?? null } }));
        })
        .catch((e: unknown) => {
          if (e instanceof ErrorDeApi && e.estado === 401 && vivo.current) alExpirar();
          noSupe();
        });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filas, marcas, listas, sinSaber, paraArmarAl, buscador]);

  // Lo que dice la celda del precio (o del sueldo): por que quedo vacia, lo que el catalogo tiene y no se escribio, o que el
  // precio es de la lista de otra fecha de composicion. Cada aviso vale mientras su motivo siga vigente en la celda.
  const avisoDelPrecio = (indice: number, fila: Fila): string | undefined => {
    const marca = marcaDe(indice, fila);
    if (marca === undefined) return undefined;
    const valor = fila[columnaDelPrecio] ?? "";
    const conflicto = marca.conflictos?.[columnaDelPrecio];
    const cambio = marca.cambios?.[columnaDelPrecio];
    const lista = listaDe(indice, fila);
    const origen = marca.fechaPrecio
      ? `de la lista del ${fechaEsVe(marca.fechaPrecio)}`
      : `tomado con la fecha ${marca.fecha ? fechaEsVe(marca.fecha) : "vacía"}`;
    const dichoDeLaLista =
      lista.tipo === "otra"
        ? `Precio ${origen}; con la fecha ${fechaEsVe(paraArmarAl)} ${lista.motivo}; revise.`
        : lista.tipo === "nose"
          ? `Precio ${origen}; con la fecha ${fechaEsVe(paraArmarAl)} puede regir otra lista; revise.`
          : undefined;
    const partes = [
      cambio !== undefined && valor === cambio.valor ? cambio.aviso : undefined,
      valor.trim() === "" ? marca.avisoPrecio : undefined,
      conflicto !== undefined && valor.trim() !== "" && valor !== conflicto.valor ? conflicto.aviso : undefined,
      dichoDeLaLista,
    ];
    const texto = partes.filter(Boolean).join(" ");
    return texto === "" ? undefined : texto;
  };

  const avisoDeLaUnidad = (indice: number, fila: Fila): string | undefined => {
    const marca = marcaDe(indice, fila);
    const conflicto = marca?.conflictos?.unidad;
    const cambio = marca?.cambios?.unidad;
    const valor = fila.unidad ?? "";
    const texto = [
      cambio !== undefined && valor === cambio.valor ? cambio.aviso : undefined,
      conflicto !== undefined && valor.trim() !== "" && valor !== conflicto.valor ? conflicto.aviso : undefined,
    ]
      .filter(Boolean)
      .join(" ");
    return texto === "" ? undefined : texto;
  };

  const esPropia = (indice: number, fila: Fila) => {
    const descripcion = fila.descripcion ?? "";
    const marca = marcaDe(indice, fila);
    return descripcion.trim() !== "" && marca?.escrita === descripcion && marca.catalogo !== descripcion;
  };
  return (
    <section className="silice-componer__tabla" aria-label={titulo}>
      <Titulo className="cds--type-heading-compact-02">{titulo}</Titulo>
      <div className="silice-tabla">
        <Table size="sm" aria-label={`Insumos: ${titulo}`}>
          <TableHead>
            <TableRow>
              {columnas.map((c) => (
                <TableHeader key={c.clave} className={c.numerica ? "silice-cifra" : undefined}>
                  {c.titulo}
                </TableHeader>
              ))}
              <TableHeader aria-label="Acciones" />
            </TableRow>
          </TableHead>
          <TableBody>
            {filas.map((fila, i) => (
              <TableRow key={i}>
                {columnas.map((c) => {
                  const nombre = `${c.titulo}, fila ${i + 1}`;
                  return (
                    <TableCell key={c.clave} className={c.numerica ? "silice-cifra" : undefined}>
                      {c.clave === "modalidad" ? (
                        <Select
                          id={`${tipo}-${i}-${c.clave}`}
                          size="sm"
                          labelText={nombre}
                          hideLabel
                          value={fila[c.clave] ?? ""}
                          onChange={(e) => alCambiar(i, c.clave, e.target.value)}
                        >
                          <SelectItem value="" text="" />
                          {modalidades.map((m) => (
                            <SelectItem key={m} value={m} text={m} />
                          ))}
                        </Select>
                      ) : c.clave === "descripcion" ? (
                        <CampoConBusqueda<SugerenciaDeConsulta>
                          // Con otra «Fecha» el campo se vuelve a montar: lo que habia buscado y guardado era de otra lista de
                          // precios y no se puede elegir (dictamen, BLOQUEANTE). Montar de nuevo tambien aborta lo que iba en vuelo.
                          key={paraArmarAl}
                          id={`${tipo}-${i}-${c.clave}`}
                          etiqueta={nombre}
                          etiquetaOculta
                          ayuda={esPropia(i, fila) ? AVISO_PROPIA : undefined}
                          texto={fila.descripcion ?? ""}
                          alCambiarTexto={(texto) => escribir(i, texto)}
                          buscar={(q, senal, limite) => buscador(q.slice(0, LARGO_MAXIMO).trim(), senal, limite)}
                          alElegir={(opcion) => elegir(i, opcion)}
                          valorPropio={{
                            rotulo: (t) => `Usar «${t.trim()}» tal cual (no viene del catálogo)`,
                            alUsar: (t) => escribir(i, t.trim()),
                          }}
                          vacio={{
                            titulo: "¿No lo encuentra?",
                            pasos: "Pruebe con otra palabra o con el código. Si no está en la lista, puede escribirlo tal cual.",
                          }}
                          alExpirar={alExpirar}
                          enCelda
                          escLimpia={false}
                          llenaOtrasCeldas
                          largoMaximo={null}
                          conBorrar={false}
                          tamano="sm"
                        />
                      ) : c.clave === "unidad" ? (
                        <CampoDeUnidad
                          id={`${tipo}-${i}-${c.clave}`}
                          etiqueta={nombre}
                          etiquetaOculta
                          texto={fila.unidad ?? ""}
                          ayuda={avisoDeLaUnidad(i, fila)}
                          alCambiar={(texto) => editar(i, c.clave, texto)}
                          alExpirar={alExpirar}
                          enCelda
                        />
                      ) : (
                        <CampoTexto
                          id={`${tipo}-${i}-${c.clave}`}
                          size="sm"
                          labelText={nombre}
                          hideLabel
                          helperText={c.clave === columnaDelPrecio ? avisoDelPrecio(i, fila) : undefined}
                          value={fila[c.clave] ?? ""}
                          onChange={(e) => editar(i, c.clave, e.target.value)}
                        />
                      )}
                    </TableCell>
                  );
                })}
                <TableCell>
                  <Button
                    kind="ghost"
                    size="sm"
                    aria-label={`Borrar fila ${i + 1} de ${titulo}`}
                    onClick={() => borrar(i)}
                  >
                    Borrar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Button kind="tertiary" size="sm" aria-label={`Agregar fila a ${titulo}`} onClick={alAgregar}>
        Agregar fila
      </Button>
    </section>
  );
}
