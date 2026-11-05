import { Button, Select, SelectItem, Table, TableBody, TableCell, TableHead, TableRow } from "@carbon/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { TableHeader } from "../../comun/carbonEs";
import { CampoConBusqueda } from "../../comun/CampoConBusqueda";
import { CampoTexto } from "../../comun/CampoTexto";
import { buscadorDeConsulta } from "../../comun/consulta";
import type { SugerenciaDeConsulta } from "../../comun/consulta";
import { LARGO_MAXIMO } from "../../comun/logicaBusqueda";
import type { OpcionDeBusqueda } from "../../comun/logicaBusqueda";
import { TABLA_DE_CONSULTA, valoresAlElegir } from "./autocompletado";
import { insumosDelCatalogo } from "./cliente";
import type { InsumoCatalogo } from "./cliente";
import { COLUMNAS, TITULOS } from "./tablas";
import type { Fila, TipoTabla } from "./tablas";

interface Props {
  tipo: TipoTabla;
  filas: Fila[];
  // Opciones de modalidad que manda la API (solo mano de obra).
  modalidades: string[];
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
}

// Una tabla de insumos editable (UC-10, pasos 2 a 4). Carbon `sm`: celdas de texto; los montos se teclean y se
// muestran como texto, alineados a la derecha, y nunca se convierten en el navegador.
//
// La descripcion es un campo con sugerencias del catalogo (AC1, pedido de Eugenio del 2026-10-21): materiales y equipos
// piden «insumos» y la mano de obra «salarios_cct». Al elegir se llenan tambien la unidad y el precio que el catalogo
// trae; escribir una descripcion propia sigue siendo posible y queda avisado.
export function TablaInsumos({ tipo, filas, modalidades, alCambiar, alAgregar, alBorrar, alCompletar, alExpirar, nivel = 3 }: Props) {
  const Titulo = `h${nivel}` as const;
  const titulo = TITULOS[tipo];
  const columnas = COLUMNAS[tipo];
  const buscador = useMemo(() => buscadorDeConsulta(TABLA_DE_CONSULTA[tipo]), [tipo]);
  const [marcas, setMarcas] = useState<Record<number, Marca>>({});
  // Las filas de ahora, para que una eleccion que tarda en volver (la lista del catalogo) no pise lo que se escribio despues.
  const filasAhora = useRef(filas);
  useEffect(() => {
    filasAhora.current = filas;
  });

  const marcar = (indice: number, cambio: Marca) => setMarcas((m) => ({ ...m, [indice]: { ...m[indice], ...cambio } }));

  const escribir = (indice: number, texto: string) => {
    marcar(indice, { escrita: texto });
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

  const elegir = async (indice: number, opcion: OpcionDeBusqueda<SugerenciaDeConsulta>) => {
    const alElegir = filasAhora.current[indice]?.descripcion;
    const codigo = opcion.valor.valor;
    let insumo: InsumoCatalogo | null = null;
    try {
      insumo = (await insumosDelCatalogo()).find((i) => i.codigo === codigo) ?? null;
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) {
        alExpirar();
        return;
      }
      // Sin la lista completa se elige igual: queda la descripcion y la persona escribe el resto.
    }
    if (filasAhora.current[indice]?.descripcion !== alElegir) return; // siguio escribiendo o borro la fila
    const valores = valoresAlElegir(tipo, insumo, opcion.principal, codigo);
    marcar(indice, { catalogo: valores.descripcion, escrita: undefined });
    alCompletar(indice, valores);
  };

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
                          alElegir={(opcion) => void elegir(i, opcion)}
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
