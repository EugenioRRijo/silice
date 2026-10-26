import { Button } from "@carbon/react";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { CampoConBusqueda } from "../../comun/CampoConBusqueda";
import { CampoTexto } from "../../comun/CampoTexto";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import { buscadorDePartidas } from "../../comun/logicaBusqueda";
import type { GrupoDeResultados, OpcionDeBusqueda } from "../../comun/logicaBusqueda";
import { useAplicacion } from "../../shell/contexto";
import { AnotarObservacion } from "./AnotarObservacion";
import { Cifras } from "./Cifras";
import { Observaciones } from "./Observaciones";
import { UsarPrecio } from "./UsarPrecio";
import { DIAS_POR_OMISION, buscadorDeInsumos, describirError, diasValidos, rutaDelEstudio } from "./logica";
import type { Estudio, Lado } from "./logica";

interface Elegido {
  codigo: string;
  descripcion: string;
}

// Lo que se elige en el buscador: un insumo (compra) o una partida (cobro); de los dos basta el codigo y el nombre.
type Buscar = (q: string, senal: AbortSignal, limite: number) => Promise<GrupoDeResultados<Elegido>[]>;

type Carga =
  | { estado: "cargando" }
  | { estado: "listo"; estudio: Estudio; recargando: boolean }
  | { estado: "error"; error: unknown };

const TEXTOS = {
  compra: {
    etiqueta: "Insumo",
    ayuda: "Escriba parte del nombre o el código del insumo; por ejemplo «cemento».",
    vacio: { titulo: "¿No lo encuentra?", pasos: "Pruebe con otra palabra del nombre o revise el Catálogo de partidas e insumos." },
    sinElegir: "Elija un insumo para ver sus precios en el mercado",
    comoElegir: "Escríbalo en «Insumo» y elíjalo de la lista: verá lo que cuesta en el mercado y podrá usar un precio.",
  },
  cobro: {
    etiqueta: "Partida",
    ayuda: "Escriba parte de la descripción o el código de la partida; por ejemplo «friso».",
    vacio: { titulo: "¿No la encuentra?", pasos: "Pruebe con otra palabra de la descripción o revise el Catálogo de partidas e insumos." },
    sinElegir: "Elija una partida para ver lo que cobra el mercado",
    comoElegir: "Escríbala en «Partida» y elíjala de la lista: verá lo que cobra la competencia frente a su costo.",
  },
} as const;

// Lo que se ve mientras llega el estudio: el esqueleto de la tabla de observaciones.
const COLUMNAS_DE_CARGA = ["Fecha", "De dónde sale", "Fuente", "Precio", "Nota"].map((titulo) => ({ clave: titulo, titulo }));

// Lee el estudio de `ruta` cada vez que cambia la ruta o `version` (tras anotar o anular). Mientras recarga la misma
// ruta deja a la vista lo que habia, para que la pantalla no parpadee ni pierda lo escrito.
function useEstudio(ruta: string | null, version: number, alExpirar: () => void): Carga | null {
  const [carga, setCarga] = useState<{ ruta: string; version: number; valor: Carga } | null>(null);

  useEffect(() => {
    if (ruta === null) return;
    let vigente = true;
    pedir<Estudio>(ruta).then(
      (estudio) => {
        if (vigente) setCarga({ ruta, version, valor: { estado: "listo", estudio, recargando: false } });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setCarga({ ruta, version, valor: { estado: "error", error } });
      },
    );
    return () => {
      vigente = false;
    };
  }, [ruta, version, alExpirar]);

  if (ruta === null) return null;
  if (carga && carga.ruta === ruta && carga.version === version) return carga.valor;
  if (carga && carga.ruta === ruta && carga.valor.estado === "listo") return { ...carga.valor, recargando: true };
  return { estado: "cargando" };
}

export function EstudioDelLado({ lado }: { lado: Lado }) {
  const { alExpirar, proyecto, nombreProyecto } = useAplicacion();
  const textos = TEXTOS[lado];
  const [texto, setTexto] = useState("");
  const [elegido, setElegido] = useState<Elegido | null>(null);
  const [diasEscritos, setDiasEscritos] = useState(DIAS_POR_OMISION);
  const [dias, setDias] = useState(DIAS_POR_OMISION);
  const [diasMalos, setDiasMalos] = useState(false);
  const [version, setVersion] = useState(0);
  // El piso de cobro sale con los parametros de la obra abierta; en compra no hay piso.
  const obra = lado === "cobro" ? proyecto : null;
  const ruta = elegido ? rutaDelEstudio(lado, elegido.codigo, dias, obra) : null;
  const carga = useEstudio(ruta, version, alExpirar);

  // Un buscador por pestana: el de insumos recuerda la lista del catalogo mientras la pagina este abierta.
  const buscar = useMemo<Buscar>(() => (lado === "cobro" ? buscadorDePartidas() : buscadorDeInsumos()), [lado]);

  function elegir(opcion: OpcionDeBusqueda<Elegido>) {
    setTexto(opcion.valor.descripcion);
    setElegido({ codigo: opcion.valor.codigo, descripcion: opcion.valor.descripcion });
  }

  function verDias(evento: FormEvent) {
    evento.preventDefault();
    const limpio = diasEscritos.trim();
    if (!diasValidos(limpio)) {
      setDiasMalos(true);
      return;
    }
    setDiasMalos(false);
    setDias(limpio);
    setVersion((v) => v + 1);
  }

  return (
    <div className="silice-mercado__lado">
      <div className="silice-mercado__eleccion">
        <div className="silice-mercado__buscador">
          <CampoConBusqueda<Elegido>
            id={`mercado-${lado}-buscar`}
            etiqueta={textos.etiqueta}
            ayuda={textos.ayuda}
            texto={texto}
            alCambiarTexto={setTexto}
            buscar={buscar}
            alElegir={elegir}
            vacio={textos.vacio}
            alExpirar={alExpirar}
            tamano="md"
          />
        </div>
        <form className="silice-mercado__dias" onSubmit={verDias} noValidate>
          <CampoTexto
            id={`mercado-${lado}-dias`}
            labelText="Días hacia atrás"
            helperText="De 1 a 3.650; por omisión, 90."
            size="md"
            inputMode="numeric"
            value={diasEscritos}
            invalid={diasMalos}
            invalidText="Escriba un número entero de días, de 1 a 3.650."
            {...describirError(`mercado-${lado}-dias`, diasMalos)}
            onChange={(e) => {
              setDiasEscritos(e.target.value);
              setDiasMalos(false);
            }}
          />
          <Button type="submit" kind="tertiary" size="md">
            Ver estos días
          </Button>
        </form>
      </div>

      {elegido === null && <EstadoVacio titulo={textos.sinElegir} descripcion={textos.comoElegir} />}
      {carga?.estado === "cargando" && (
        <TablaDensa etiqueta="estudio de mercado" columnas={COLUMNAS_DE_CARGA} filas={[]} cargando />
      )}
      {carga?.estado === "error" && <AvisoError error={carga.error} titulo="No se pudo leer el estudio de mercado" />}
      {carga?.estado === "listo" && elegido && (
        <div className="silice-mercado__estudio" aria-busy={carga.recargando || undefined} key={elegido.codigo}>
          <p className="silice-mercado__elegido cds--type-body-compact-01">
            <span className="silice-codigo">{carga.estudio.codigo}</span> {elegido.descripcion}
          </p>
          <Cifras estudio={carga.estudio} obra={obra === null ? null : (nombreProyecto ?? obra)} />
          <UsarPrecio estudio={carga.estudio} />
          <Observaciones estudio={carga.estudio} alCambiar={() => setVersion((v) => v + 1)} />
          <AnotarObservacion lado={lado} codigo={carga.estudio.codigo} moneda={carga.estudio.moneda} alCambiar={() => setVersion((v) => v + 1)} />
        </div>
      )}
    </div>
  );
}
