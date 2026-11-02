import { Button, Select, SelectItem } from "@carbon/react";
import { useEffect, useId, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { LARGO_DE_CELDA, enteroDeDigitos, esBorradorAusente } from "./logica";
import type { DetalleApu, Resumen } from "./logica";
import { TIPOS_DE_LINEA, cuerpoDeInsumo, insumosVisibles, rutaDeInsumo, rutaDeInsumos } from "./logicaApu";
import type { InsumoCandidato, InsumosRespuesta } from "./logicaApu";
import type { Peticion } from "./useEdicionDeSeccion";
import { CampoTexto } from "../../comun/CampoTexto";

// Espera tras la última tecla antes de pedir los candidatos acotados al servidor.
const PAUSA_DE_BUSQUEDA_MS = 300;
export const TITULO_DEL_CAMBIO = "Cambiar el insumo de una línea (en la copia de esta versión)";

interface Props {
  id: string;
  detalle: DetalleApu;
  // Manda la petición después de lo que la persona escribió y espera la respuesta; devuelve el resumen si el servidor la aceptó.
  alCambiar: (peticion: (rev: number) => Peticion) => Promise<Resumen | null>;
  alAusente: () => void;
  alExpirar: () => void;
}

type Candidatos =
  | { estado: "cargando" }
  | { estado: "listo"; insumos: InsumoCandidato[]; hayMas: boolean }
  | { estado: "error"; error: unknown };

// «Cambiar el insumo de una línea (en la copia de esta versión)» (ui/paginas/hoja.py:1518-1584): tipo de línea, línea,
// candidatos de la lista de precios de la versión (con búsqueda) y «Usar este insumo». Cambia descripción, unidad y precio
// de la línea y conserva su cantidad; el servidor valida (el insumo debe estar en la lista) y recalcula.
export function CambioDeInsumo({ id, detalle, alCambiar, alAusente, alExpirar }: Props) {
  const idCuerpo = useId();
  const [abierto, setAbierto] = useState(false);
  const [tipo, setTipo] = useState<string>(TIPOS_DE_LINEA[0].valor);
  const [linea, setLinea] = useState("0");
  const [escrito, setEscrito] = useState("");
  const [buscar, setBuscar] = useState("");
  const [elegido, setElegido] = useState("");
  const [candidatos, setCandidatos] = useState<{ ruta: string; valor: Candidatos } | null>(null);
  const [mensaje, setMensaje] = useState("");
  const [enviando, setEnviando] = useState(false);

  const versionAbierta = !detalle.solo_lectura_insumos;
  const tipoActual = TIPOS_DE_LINEA.find((t) => t.valor === tipo) ?? TIPOS_DE_LINEA[0];
  const lineas = detalle.grupos.find((g) => g.clave === tipoActual.grupo)?.filas ?? [];
  const ruta = rutaDeInsumos(id, tipo, buscar);

  useEffect(() => {
    const espera = setTimeout(() => setBuscar(escrito.trim()), PAUSA_DE_BUSQUEDA_MS);
    return () => clearTimeout(espera);
  }, [escrito]);

  const hayLineas = lineas.length > 0;
  useEffect(() => {
    if (!abierto || !versionAbierta || !hayLineas) return;
    let vigente = true;
    pedir<InsumosRespuesta>(ruta).then(
      (r) => {
        if (vigente) setCandidatos({ ruta, valor: { estado: "listo", ...insumosVisibles(r) } });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        else if (esBorradorAusente(error)) alAusente();
        setCandidatos({ ruta, valor: { estado: "error", error } });
      },
    );
    return () => {
      vigente = false;
    };
  }, [abierto, versionAbierta, hayLineas, ruta, alAusente, alExpirar]);

  const actuales = candidatos !== null && candidatos.ruta === ruta ? candidatos.valor : ({ estado: "cargando" } as const);
  const indice = lineas.length > 0 ? Math.min(enteroDeDigitos(linea), lineas.length - 1) : 0;

  const usar = async () => {
    if (elegido === "" || enviando) return;
    const candidato = actuales.estado === "listo" ? actuales.insumos.find((c) => c.codigo === elegido) : undefined;
    setEnviando(true);
    setMensaje("");
    try {
      const aceptado = await alCambiar((rev) => ({
        ruta: rutaDeInsumo(id, detalle.codigo),
        metodo: "POST",
        cuerpo: cuerpoDeInsumo(rev, tipo, indice, elegido),
        frase: "", // la clásica muestra este rechazo solo (ui/paginas/hoja.py:1519)
      }));
      if (aceptado !== null) {
        setMensaje(`Insumo de la línea ${indice + 1} cambiado: ${candidato?.descripcion ?? elegido}.`);
        setElegido("");
      }
    } finally {
      setEnviando(false);
    }
  };

  return (
    <section className="silice-hoja__seccion silice-hoja__insumo">
      <Button
        kind="ghost"
        size="sm"
        aria-expanded={abierto}
        aria-controls={idCuerpo}
        onClick={() => setAbierto((a) => !a)}
      >
        {TITULO_DEL_CAMBIO}
      </Button>
      <div id={idCuerpo} hidden={!abierto} className="silice-hoja__insumo-cuerpo">
        {abierto && !versionAbierta && (
          <p className="cds--type-helper-text-01">Abra una versión guardada: los insumos se eligen de su lista de precios.</p>
        )}
        {abierto && versionAbierta && (
          <>
            <Select
              id={`${idCuerpo}-tipo`}
              labelText="Tipo de línea"
              size="sm"
              value={tipo}
              onChange={(e) => {
                setTipo(e.target.value);
                setLinea("0");
                setElegido("");
                setMensaje("");
              }}
            >
              {TIPOS_DE_LINEA.map((t) => (
                <SelectItem key={t.valor} value={t.valor} text={t.rotulo} />
              ))}
            </Select>
            {!hayLineas ? (
              <p className="cds--type-helper-text-01">Este APU no tiene líneas de ese tipo.</p>
            ) : (
              <>
                <Select id={`${idCuerpo}-linea`} labelText="Línea" size="sm" value={String(indice)} onChange={(e) => setLinea(e.target.value)}>
                  {lineas.map((l, i) => (
                    <SelectItem key={i} value={String(i)} text={`${i + 1}. ${l.descripcion ?? ""}`} />
                  ))}
                </Select>
                <CampoTexto
                  id={`${idCuerpo}-buscar`}
                  labelText="Buscar insumo (por descripción)"
                  size="sm"
                  value={escrito}
                  maxLength={LARGO_DE_CELDA}
                  autoComplete="off"
                  onChange={(e) => {
                    setEscrito(e.target.value);
                    setElegido("");
                  }}
                />
                {actuales.estado === "cargando" && <p className="cds--type-helper-text-01">Buscando insumos…</p>}
                {actuales.estado === "error" && <AvisoError error={actuales.error} titulo="No se pudieron leer los insumos" />}
                {actuales.estado === "listo" && actuales.hayMas && (
                  <p className="cds--type-helper-text-01">Hay más de 300 insumos: escriba parte de la descripción para acotar.</p>
                )}
                {actuales.estado === "listo" && actuales.insumos.length === 0 && (
                  <p className="cds--type-helper-text-01">Ningún insumo de la lista coincide: pruebe con otra palabra.</p>
                )}
                {actuales.estado === "listo" && actuales.insumos.length > 0 && (
                  <Select id={`${idCuerpo}-insumo`} labelText="Insumo" size="sm" value={elegido} onChange={(e) => setElegido(e.target.value)}>
                    <SelectItem value="" text="Elegir insumo de la lista de precios" />
                    {actuales.insumos.map((c) => (
                      <SelectItem
                        key={c.codigo}
                        value={c.codigo}
                        text={`${c.codigo} · ${c.descripcion} · ${c.unidad} · ${formatoEsVe(c.precio.texto)}`}
                      />
                    ))}
                  </Select>
                )}
                <div>
                  <Button kind="tertiary" size="sm" disabled={elegido === "" || enviando} onClick={() => void usar()}>
                    Usar este insumo
                  </Button>
                </div>
              </>
            )}
            <p className="cds--type-helper-text-01" role="status">
              {mensaje}
            </p>
          </>
        )}
      </div>
    </section>
  );
}
