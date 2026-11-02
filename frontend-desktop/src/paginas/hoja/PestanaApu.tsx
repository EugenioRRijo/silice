import { RadioButton, RadioButtonGroup } from "@carbon/react";
import { Search } from "../../comun/carbonEs";
import { useCallback, useEffect, useState } from "react";
import { AyudaDePestana } from "./AyudaDePestana";
import { EditorDelDetalle } from "./EditorDeApu";
import { VistaCarga } from "./VistaCarga";
import { rutaDeVista } from "./logica";
import type { BaseAbierta, Resumen, VistaApu } from "./logica";
import { useHojaDeLaObra } from "./ProveedorDeLaHoja";
import { usePuedeEditarLaHoja } from "./puedeEditar";

interface Props {
  id: string;
  // El `rev` del borrador según la página.
  rev: number;
  moneda: string;
  alAusente: () => void;
  // El servidor aceptó una edición: su resumen pasa a la barra de estado de la página.
  alAceptar: (resumen: Resumen) => void;
  alRecargarBorrador: () => Promise<void>;
  // Descarta lo que se ve y abre otro borrador de la versión (cuando recargar no sirve).
  alReabrir: () => void;
  // La base del borrador: con `solo_lectura` (o sin permiso de edición) no se pinta nada que escriba (F4 2b).
  base?: Pick<BaseAbierta, "solo_lectura">;
}

// Espera tras la última tecla antes de pedir la lista filtrada al servidor.
const PAUSA_DE_BUSQUEDA_MS = 300;

// Pestaña «APU»: lista con buscador (lo filtra el servidor) y el editor de la partida elegida (`EditorDeApu.tsx`, rebanada
// 3c-3). Cada edición recalcula en el servidor; la pestaña vuelve a leer su vista. La partida elegida es la del proveedor
// (Tarea 7 del plan F4): la comparte con el panel del APU que se abre desde «Partidas».
export function PestanaApu(props: Props) {
  const puedeEditar = usePuedeEditarLaHoja(props.base ?? null);
  const [escrito, setEscrito] = useState("");
  const [buscar, setBuscar] = useState("");
  const { partidaElegida, elegirPartida } = useHojaDeLaObra();
  const partida = partidaElegida ?? undefined;
  // Sube cada vez que hay que volver a leer la vista tras una edición: la anterior sigue a la vista mientras llega.
  const [lecturas, setLecturas] = useState(0);
  const alRelectura = useCallback(() => setLecturas((n) => n + 1), []);

  useEffect(() => {
    const espera = setTimeout(() => setBuscar(escrito.trim()), PAUSA_DE_BUSQUEDA_MS);
    return () => clearTimeout(espera);
  }, [escrito]);

  return (
    <VistaCarga<VistaApu>
      ruta={rutaDeVista(props.id, "apu", { partida, buscar })}
      etiqueta="APU"
      alAusente={props.alAusente}
      recarga={lecturas}
    >
      {(vista, actualizando) => (
        <>
          <AyudaDePestana id="apu" puedeEditar={puedeEditar} />
          {vista.vacio_mensaje !== null ? (
          <p className="cds--type-body-compact-01">{vista.vacio_mensaje}</p>
        ) : (
          <div className="silice-hoja__apu" aria-busy={actualizando}>
            <div className="silice-hoja__apu-lista">
              <Search
                size="sm"
                labelText="Buscar partida"
                placeholder="Código o descripción"
                value={escrito}
                onChange={(e: { target: { value: string } }) => setEscrito(e.target.value)}
              />
              {vista.sin_coincidencias && (
                <p className="cds--type-helper-text-01">Ninguna partida coincide; se muestran todas.</p>
              )}
              <RadioButtonGroup
                legendText="Partidas"
                name="partida-apu"
                orientation="vertical"
                valueSelected={vista.seleccionada ?? undefined}
                onChange={(valor) => elegirPartida(String(valor))}
              >
                {vista.partidas.map((p) => (
                  <RadioButton key={p.codigo} id={`apu-${p.codigo}`} value={p.codigo} labelText={`${p.codigo} · ${p.descripcion}`} />
                ))}
              </RadioButtonGroup>
            </div>
            {vista.detalle !== null && (
              <EditorDelDetalle key={vista.detalle.codigo} {...props} detalle={vista.detalle} alRelectura={alRelectura} />
            )}
          </div>
        )}
        </>
      )}
    </VistaCarga>
  );
}
