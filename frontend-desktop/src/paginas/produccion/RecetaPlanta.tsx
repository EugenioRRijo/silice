import { Button } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { recetaVigente } from "../../api/produccionPlanta";
import type { RecetaRespuesta } from "../../api/produccionPlanta";
import { AvisoError } from "../../comun/AvisoError";
import { CampoDeConsulta } from "../../comun/CampoDeConsulta";
import { CampoTexto } from "../../comun/CampoTexto";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { hoyISO } from "../existencias/formato";
import { AvisoConFoco } from "./AvisoConFoco";
import { FormularioDeReceta } from "./FormularioDeReceta";
import { fechaEsVe, mostrarMonto, rotulo } from "./logica";
import { TIPOS, UNIDADES, mensajeDePlanta, sumaDeMasa } from "./logicaPlanta";
import "./planta.scss";

type Vista = { estado: "ninguna" } | { estado: "listo"; receta: RecetaRespuesta } | { estado: "error"; error: unknown };

const COLUMNAS: ColumnaDensa[] = [
  { clave: "codigo", titulo: "Código" },
  { clave: "cantidad", titulo: "Cantidad por t", numerica: true, presentar: mostrarMonto },
  { clave: "unidad", titulo: "Unidad" },
  { clave: "tipo", titulo: "Tipo" },
];

// «Receta de la planta»: lo que lleva una tonelada de cada mezcla. Se consulta la receta que rige para un producto en una
// fecha y se registra una nueva (la anterior no se toca). La suma de masa es un aviso: el servidor la comprueba al
// guardar y es quien decide. Nada aquí calcula costos.
export default function RecetaPlanta() {
  const { alExpirar } = useAplicacion();
  const [producto, setProducto] = useState("");
  const [fecha, setFecha] = useState(() => hoyISO());
  const [vista, setVista] = useState<Vista>({ estado: "ninguna" });
  const [registrando, setRegistrando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const region = useRef<HTMLElement>(null);
  const enfocarReceta = useRef(false);

  // El foco pasa a la receta cuando llega, no se queda en un botón que cambió de lugar.
  useEffect(() => {
    if (vista.estado === "listo" && enfocarReceta.current) region.current?.focus();
  }, [vista]);

  async function consultar(conFoco: boolean) {
    enfocarReceta.current = conFoco;
    try {
      setVista({ estado: "listo", receta: await recetaVigente(producto.trim(), fecha) });
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setVista({ estado: "error", error: razon });
    }
  }

  const receta = vista.estado === "listo" ? vista.receta : null;
  const filas: FilaDensa[] = (receta?.componentes ?? []).map((c) => ({
    id: c.codigo,
    codigo: c.codigo,
    cantidad: c.cantidad_por_t,
    unidad: rotulo(UNIDADES, c.unidad),
    tipo: rotulo(TIPOS, c.tipo),
  }));
  const masa = receta ? sumaDeMasa(receta.componentes.map((c) => ({ cantidad: mostrarComa(c.cantidad_por_t), unidad: c.unidad }))) : null;

  return (
    <div className="planta silice-pagina">
      <h1 className="cds--type-heading-04">Receta de la planta</h1>
      <p className="planta-nota cds--type-body-compact-01">
        Lo que lleva una tonelada de cada mezcla. Una receta nueva no cambia las anteriores: la producción usa la que rige en su fecha.
      </p>
      <div className="planta-barra">
        <CampoDeConsulta id="receta-producto" etiqueta="Producto (código)" tabla="materiales_produccion" texto={producto} alCambiarTexto={setProducto} alExpirar={alExpirar} />
        <CampoTexto id="receta-fecha" type="date" labelText="Fecha" value={fecha} onChange={(e) => setFecha(e.target.value)} />
        <Button kind="secondary" size="md" disabled={producto.trim() === "" || fecha === ""} onClick={() => void consultar(true)}>
          Ver la receta vigente
        </Button>
        <Button kind="primary" size="md" onClick={() => setRegistrando(true)}>
          Registrar una receta nueva
        </Button>
      </div>
      <AvisoConFoco aviso={aviso} alCerrar={() => setAviso(null)} />
      {vista.estado === "error" && <AvisoError error={mensajeDePlanta(vista.error)} titulo="No se encontró la receta" />}
      {receta && masa && (
        <section ref={region} tabIndex={-1} aria-label="Receta vigente" className="planta-resultado">
          <h2 className="cds--type-heading-compact-02">Receta vigente</h2>
          <p className="cds--type-body-compact-01">
            Receta n.º {receta.id} de {receta.producto}, vigente desde {fechaEsVe(receta.vigente_desde)}. Fuente: {receta.fuente}.
          </p>
          <TablaDensa etiqueta={`Componentes de la receta de ${receta.producto}`} columnas={COLUMNAS} filas={filas} />
          <p className="cds--type-body-compact-01">Suma de masa: {masa.texto} t por t de mezcla</p>
        </section>
      )}
      {registrando && (
        <FormularioDeReceta
          alCerrar={() => setRegistrando(false)}
          alRegistrar={() => {
            setRegistrando(false);
            setAviso("Receta registrada.");
            if (producto.trim() !== "") void consultar(false);
          }}
          alExpirar={alExpirar}
        />
      )}
    </div>
  );
}

// «0.94» -> «0,94»: sumaDeMasa lee lo que escribe la persona, con coma.
function mostrarComa(decimal: string): string {
  return decimal.replace(".", ",");
}
