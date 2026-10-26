import { Button, InlineLoading } from "@carbon/react";
import { useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { useNavegarSeguro } from "../../shell/EnlaceSeguro";
import { BOTON_LLEVAR, partidasParaLlevar, textoLlevar, textoPendientesNoSeLlevan } from "./logica";
import type { ItemComputo, PendienteConPropuestas } from "./tipos";

interface Props {
  // El codigo de la obra con que se elaboro (el de la cabecera en ese momento).
  proyecto: string;
  obra: string | null;
  // Los items con que se elaboro y los pendientes de esa elaboracion.
  items: ItemComputo[];
  pendientes: PendienteConPropuestas[];
  alExpirar: () => void;
}

// Tarea 12 de montar un presupuesto: lleva los items elaborados al borrador de la Hoja de la obra, todo o nada y sin
// guardar version (POST /v1/hoja/llevar), y abre la Hoja, que ofrece retomar ese borrador. Solo se monta con una obra
// elegida: usa el enrutador, que la pagina sin obra no necesita.
export function LlevarALaHoja({ proyecto, obra, items, pendientes, alExpirar }: Props) {
  const navegar = useNavegarSeguro();
  const [llevando, setLlevando] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const partidas = partidasParaLlevar(items, pendientes);
  const sinLlevar = textoPendientesNoSeLlevan(pendientes.length);

  async function llevar() {
    setLlevando(true);
    setError(null);
    try {
      await pedir("/v1/hoja/llevar", { metodo: "POST", cuerpo: { proyecto, partidas } });
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setError(e);
      setLlevando(false);
      return;
    }
    setLlevando(false);
    await navegar("/hoja");
  }

  if (partidas.length === 0) return null;
  return (
    <div className="silice-elaborar__llevar">
      <p className="cds--type-body-compact-01">{textoLlevar(partidas.length, obra)}</p>
      {sinLlevar !== null && <p className="silice-elaborar__nota cds--type-label-01">{sinLlevar}</p>}
      <div className="silice-elaborar__fila-accion">
        <Button kind="secondary" size="md" disabled={llevando} onClick={() => void llevar()}>
          {BOTON_LLEVAR}
        </Button>
        {llevando && <InlineLoading description="Llevando a la Hoja..." />}
      </div>
      <AvisoError error={error} titulo="No se llevó nada a la Hoja" alCerrar={() => setError(null)} />
    </div>
  );
}
