import { Button } from "@carbon/react";
import { useState } from "react";
import { InlineNotification } from "../../comun/carbonEs";
import { AvisoError } from "../../comun/AvisoError";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import { Dato } from "./Dato";
import { DialogoAnularConteo } from "./DialogoAnularConteo";
import type { ConConteo } from "./DialogoAnularConteo";
import { EstadoExistencia, ROTULOS_DE_ESTADO, estadoDe } from "./EstadoExistencia";
import type { Estado } from "./EstadoExistencia";
import type { Reacciones } from "./fallos";
import { mostrarCantidad, rotuloUnidad } from "./formato";
import type { ExistenciaRespuesta } from "./tipos";
import type { Recurso } from "./useRecurso";
import { CampoTexto } from "../../comun/CampoTexto";

interface Props {
  existencias: Recurso<ExistenciaRespuesta[]>;
  fecha: string;
  alCambiarFecha: (fecha: string) => void;
  alReintentar: () => void;
  alCrearMaterial: () => void;
  // Se anulo un conteo: hay que volver a leer la existencia.
  alAnularConteo: () => void;
  reacciones: Reacciones;
}

const COLUMNAS: ColumnaDensa[] = [
  { clave: "codigo", titulo: "Código" },
  { clave: "nombre", titulo: "Material" },
  { clave: "unidad", titulo: "Unidad" },
  { clave: "existencia", titulo: "Existencia", numerica: true, celda: (f) => mostrarCantidad(f.existencia) },
  { clave: "minima", titulo: "Mínima", numerica: true, celda: (f) => mostrarCantidad(f.minima) },
  { clave: "estado", titulo: "Estado", celda: (f) => <EstadoExistencia estado={f.estado as Estado} /> },
  // El conteo que cerro el pasado del material (prueba en vivo 2026-11-18); se ordena por la fecha ISO.
  { clave: "conteo", titulo: "Último conteo", celda: (f) => (f.conteo ? fechaEsVe(String(f.conteo)) : "Sin conteo") },
];

function aFila(f: ExistenciaRespuesta): FilaDensa {
  return {
    id: f.codigo,
    codigo: f.codigo,
    nombre: f.nombre,
    unidad: rotuloUnidad(f.unidad_venta),
    existencia: f.existencia,
    minima: f.minima,
    // Para ordenar por estado: negativa, luego queda poco, luego normal (el texto de la fila, no el icono).
    estado: estadoDe(f),
    conteo: f.ultimo_conteo?.fecha ?? "",
  };
}

// «Cuanto hay y cuanto queda» de cada material a una fecha (UC-28, RF-129). Las cantidades son texto de la API: aqui
// solo se escriben con coma decimal, punto de miles y sin ceros de relleno; nada se calcula.
export function PestanaExistencias({
  existencias,
  fecha,
  alCambiarFecha,
  alReintentar,
  alCrearMaterial,
  alAnularConteo,
  reacciones,
}: Props) {
  // Un conteo mal hecho se anula aqui con su motivo (tanda 2026-11-19): solo el ultimo vigente de cada material.
  const [anulando, setAnulando] = useState<ConConteo | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const filtro = (
    <>
      <div className="existencias-filtro">
        <CampoTexto
          id="existencias-al"
          type="date"
          labelText="Existencia al"
          value={fecha}
          onChange={(e) => alCambiarFecha(e.target.value)}
        />
      </div>
      {aviso && <InlineNotification kind="success" role="status" lowContrast hideCloseButton title={aviso} />}
    </>
  );

  if (existencias.estado === "error") {
    return (
      <div className="existencias-bloque">
        {filtro}
        <AvisoError error={existencias.error} titulo="No se pudo leer la existencia" />
        <div>
          <Button kind="tertiary" size="md" onClick={alReintentar}>
            Reintentar
          </Button>
        </div>
      </div>
    );
  }

  if (existencias.estado === "cargando") {
    return (
      <div className="existencias-bloque">
        {filtro}
        <TablaDensa etiqueta="Existencias por material" columnas={COLUMNAS} filas={[]} cargando />
      </div>
    );
  }

  const filas = existencias.datos;
  if (filas.length === 0) {
    return (
      <div className="existencias-bloque">
        {filtro}
        <EstadoVacio
          titulo="Todavía no hay materiales"
          descripcion="Cree el primer material de la arenera, con su existencia mínima, para ver aquí cuánto hay y cuánto queda."
        >
          <Button kind="primary" size="md" onClick={alCrearMaterial}>
            Crear un material
          </Button>
        </EstadoVacio>
      </div>
    );
  }

  const columnas: ColumnaDensa[] = [
    ...COLUMNAS,
    {
      clave: "accion",
      titulo: "Acción",
      ordenable: false,
      celda: (fila) => {
        const material = filas.find((f) => f.codigo === fila.id);
        const conteo = material?.ultimo_conteo;
        if (!material || !conteo) return null;
        return (
          <Button
            kind="ghost"
            size="sm"
            aria-label={`Anular el conteo de ${material.nombre} del ${fechaEsVe(conteo.fecha)}`}
            onClick={() => {
              setAviso(null);
              setAnulando({ ...material, ultimo_conteo: conteo });
            }}
          >
            Anular conteo
          </Button>
        );
      },
    },
  ];
  const estados = filas.map(estadoDe);
  const pocos = estados.filter((e) => e === "queda_poco").length;
  const negativas = estados.filter((e) => e === "negativa").length;

  return (
    <div className="existencias-bloque">
      {filtro}
      <section className="existencias-resumen" aria-label="Resumen de existencias">
        <Dato rotulo="Materiales" valor={filas.length} />
        <Dato rotulo="Queda poco" valor={pocos} />
        <Dato rotulo="Existencia negativa" valor={negativas} />
      </section>
      {negativas > 0 && (
        <InlineNotification
          kind="warning"
          role="status"
          lowContrast
          hideCloseButton
          title="Hay materiales con existencia negativa"
          subtitle="Registre la producción (entrada) o un conteo físico para corregirla: un despacho nunca se bloquea, y la báscula pesa lo que sale de verdad."
        />
      )}
      <TablaDensa etiqueta="Existencias por material" columnas={columnas} filas={filas.map(aFila)} />
      <ul className="existencias-leyenda cds--type-body-compact-01">
        <li>{`${ROTULOS_DE_ESTADO.normal}: la existencia está por encima de la mínima.`}</li>
        <li>Queda poco: existencia menor o igual que la mínima.</li>
        <li>Existencia negativa: se despachó más de lo que hay registrado.</li>
        <li>Último conteo: el conteo físico que cerró la existencia hasta su fecha. Si estaba mal, anúlelo con su motivo.</li>
      </ul>
      {anulando && (
        <DialogoAnularConteo
          material={anulando}
          alCerrar={() => setAnulando(null)}
          alAnular={() => {
            setAnulando(null);
            setAviso(`Conteo anulado: ${anulando.codigo} vuelve a la existencia de antes del conteo.`);
            alAnularConteo();
          }}
          reacciones={reacciones}
        />
      )}
    </div>
  );
}
