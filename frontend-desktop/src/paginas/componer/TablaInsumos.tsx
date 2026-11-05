import { Button, Select, SelectItem, Table, TableBody, TableCell, TableHead, TableRow } from "@carbon/react";
import { useMemo, useState } from "react";
import { TableHeader } from "../../comun/carbonEs";
import { CampoConBusqueda } from "../../comun/CampoConBusqueda";
import { CampoTexto } from "../../comun/CampoTexto";
import { buscadorDeConsulta } from "../../comun/consulta";
import type { SugerenciaDeConsulta } from "../../comun/consulta";
import { LARGO_MAXIMO } from "../../comun/logicaBusqueda";
import type { OpcionDeBusqueda } from "../../comun/logicaBusqueda";
import { COLUMNA_DEL_PRECIO, TABLA_DE_CONSULTA, valoresAlElegir } from "./autocompletado";
import { COLUMNAS, TITULOS } from "./tablas";
import type { Fila, TipoTabla } from "./tablas";

interface Props {
  tipo: TipoTabla;
  filas: Fila[];
  // Opciones de modalidad que manda la API (solo mano de obra).
  modalidades: string[];
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
  // El nivel de su titulo: h3 en la pantalla, h4 en el panel de «Agregar partida» (plan F4, Tarea 9).
  nivel?: 3 | 4;
}

const AVISO_PROPIA = "Descripción propia: no viene del catálogo.";

// Que se sabe del origen de la descripcion de una fila: lo ultimo que se tecleo y la ultima que se eligio del catalogo.
// La descripcion es «propia» (se avisa) si es lo tecleado y no coincide con lo elegido; una fila precargada o llenada
// desde la referencia no tiene marca y no se avisa nada.
interface Marca {
  catalogo?: string;
  escrita?: string;
  // Por que no se lleno el precio de lo elegido (otra moneda): lo dice la celda del precio o del sueldo.
  avisoPrecio?: string;
}

// Una tabla de insumos editable (UC-10, pasos 2 a 4). Carbon `sm`: celdas de texto; los montos se teclean y se
// muestran como texto, alineados a la derecha, y nunca se convierten en el navegador.
//
// La descripcion es un campo con sugerencias del catalogo (AC1, pedido de Eugenio del 2026-10-21): materiales y equipos
// piden «insumos» y la mano de obra «salarios_cct». Al elegir se llenan tambien la unidad y el precio, que vienen en la
// misma respuesta: el precio es el de la lista para armar a la fecha de la composicion y solo se copia en la moneda de la
// carpeta; si no, la celda del precio dice por que quedo vacia (AC1b). Escribir una descripcion propia sigue siendo
// posible y queda avisado.
export function TablaInsumos({
  tipo,
  filas,
  modalidades,
  paraArmarAl = "",
  moneda = null,
  alCambiar,
  alAgregar,
  alBorrar,
  alCompletar,
  alExpirar,
  nivel = 3,
}: Props) {
  const Titulo = `h${nivel}` as const;
  const titulo = TITULOS[tipo];
  const columnas = COLUMNAS[tipo];
  const buscador = useMemo(
    () => buscadorDeConsulta(TABLA_DE_CONSULTA[tipo], { detalle: true, paraArmarAl }),
    [tipo, paraArmarAl],
  );
  const [marcas, setMarcas] = useState<Record<number, Marca>>({});

  const marcar = (indice: number, cambio: Marca) => setMarcas((m) => ({ ...m, [indice]: { ...m[indice], ...cambio } }));

  const escribir = (indice: number, texto: string) => {
    marcar(indice, { escrita: texto, avisoPrecio: undefined });
    alCambiar(indice, "descripcion", texto);
  };

  const borrar = (indice: number) => {
    setMarcas((m) =>
      Object.fromEntries(
        Object.entries(m)
          .filter(([clave]) => Number(clave) !== indice)
          .map(([clave, marca]) => [Number(clave) > indice ? Number(clave) - 1 : Number(clave), marca]),
      ),
    );
    alBorrar(indice);
  };

  const elegir = (indice: number, opcion: OpcionDeBusqueda<SugerenciaDeConsulta>) => {
    const { valores, aviso } = valoresAlElegir(tipo, opcion.valor, moneda);
    marcar(indice, { catalogo: valores.descripcion, escrita: undefined, avisoPrecio: aviso ?? undefined });
    alCompletar(indice, valores);
  };
  const columnaDelPrecio = COLUMNA_DEL_PRECIO[tipo];

  const esPropia = (indice: number, descripcion: string) =>
    descripcion.trim() !== "" && marcas[indice]?.escrita === descripcion && marcas[indice]?.catalogo !== descripcion;
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
                          id={`${tipo}-${i}-${c.clave}`}
                          etiqueta={nombre}
                          etiquetaOculta
                          ayuda={esPropia(i, fila.descripcion ?? "") ? AVISO_PROPIA : undefined}
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
                          largoMaximo={null}
                          conBorrar={false}
                          tamano="sm"
                        />
                      ) : (
                        <CampoTexto
                          id={`${tipo}-${i}-${c.clave}`}
                          size="sm"
                          labelText={nombre}
                          hideLabel
                          helperText={c.clave === columnaDelPrecio ? marcas[i]?.avisoPrecio : undefined}
                          value={fila[c.clave] ?? ""}
                          onChange={(e) => alCambiar(i, c.clave, e.target.value)}
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
