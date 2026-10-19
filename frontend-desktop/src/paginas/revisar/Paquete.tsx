import {
  Button,
  Form,
  InlineLoading,
  InlineNotification,
  RadioButton,
  RadioButtonGroup,
  Select,
  SelectItem,
  TextArea,
} from "@carbon/react";
import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import {
  COLUMNAS_CAMBIOS,
  COLUMNAS_HALLAZGOS,
  SIN_ARCHIVO,
  filasDeCambios,
  formularioDictamen,
  formularioExcel,
  formularioPaquete,
  presentador,
  tipoDeBanner,
  tituloDeLote,
} from "./logica";
import { Dato, Diferencia } from "./piezas";
import type { ContraLista, DictamenAnterior, DictamenGuardado, ReauditoriaRevision, Revision } from "./tipos";

type Estado =
  | { tipo: "ninguno" }
  | { tipo: "analizando" }
  | { tipo: "error"; error: unknown }
  | { tipo: "listo"; archivo: File; revision: Revision };

// Pestaña «Paquete .silice» (UC-23; ui/paginas/revisar.py `_paquete`). La API verifica, registra lo recibido y
// reaudita en memoria; esta pantalla no guarda nada entre peticiones: el contraste con otra lista, el dictamen y los
// Excel vuelven a mandar el mismo archivo, que la API verifica otra vez.
export function PestanaPaquete({ alExpirar }: { alExpirar: () => void }) {
  const [estado, setEstado] = useState<Estado>({ tipo: "ninguno" });
  const consulta = useRef(0);

  async function analizar(archivo: File) {
    const numero = ++consulta.current;
    setEstado({ tipo: "analizando" });
    try {
      const revision = await pedir<Revision>("/v1/revision/paquete", {
        metodo: "POST",
        cuerpo: formularioPaquete(archivo),
      });
      if (numero === consulta.current) setEstado({ tipo: "listo", archivo, revision });
    } catch (error) {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
      if (numero === consulta.current) setEstado({ tipo: "error", error });
    }
  }

  return (
    <div className="silice-revisar__pestana">
      <SubidaArchivo
        id="revisar-paquete"
        etiqueta="Suelte aquí el paquete .silice, o haga clic para elegirlo"
        extensiones={[".silice"]}
        deshabilitada={estado.tipo === "analizando"}
        alElegir={(archivo) => void analizar(archivo)}
      />
      {estado.tipo === "ninguno" && <EstadoVacio titulo={SIN_ARCHIVO} />}
      {estado.tipo === "analizando" && <InlineLoading description="Verificando y reauditando el paquete…" />}
      {estado.tipo === "error" && <AvisoError error={estado.error} titulo="No se pudo revisar el paquete" />}
      {estado.tipo === "listo" && (
        <Resultado key={estado.revision.sha256} archivo={estado.archivo} r={estado.revision} alExpirar={alExpirar} />
      )}
    </div>
  );
}

function Resultado({ archivo, r, alExpirar }: { archivo: File; r: Revision; alExpirar: () => void }) {
  const tipo = tipoDeBanner(r.color);
  const re = r.reauditoria;
  return (
    <div className="silice-revisar__resultado">
      <InlineNotification
        kind={tipo}
        role={tipo === "error" ? "alert" : "status"}
        title=""
        subtitle={r.banner}
        lowContrast
        hideCloseButton
      />
      {r.banner_version && <p className="silice-revisar__nota cds--type-body-compact-01">{r.banner_version}</p>}
      {r.ayuda_registro && <p className="silice-revisar__nota cds--type-body-compact-01">{r.ayuda_registro}</p>}
      {r.avisos.map((aviso) => (
        <InlineNotification key={aviso} kind="warning" title="" subtitle={aviso} lowContrast hideCloseButton />
      ))}
      {r.retroactiva && <p className="silice-revisar__nota cds--type-body-compact-01">{r.retroactiva}</p>}
      {r.aviso_armo && (
        <InlineNotification kind="warning" title="" subtitle={r.aviso_armo} lowContrast hideCloseButton />
      )}
      {r.legible && re && <Reauditoria archivo={archivo} r={r} re={re} alExpirar={alExpirar} />}
    </div>
  );
}

function Reauditoria({
  archivo,
  r,
  re,
  alExpirar,
}: {
  archivo: File;
  r: Revision;
  re: ReauditoriaRevision;
  alExpirar: () => void;
}) {
  return (
    <>
      {re.avisos.map((aviso) => (
        <InlineNotification key={aviso} kind="warning" title="" subtitle={aviso} lowContrast hideCloseButton />
      ))}
      {re.termino && re.total_recalculado && re.total_recalculado_texto && (
        <>
          <dl className="silice-revisar__datos">
            <Dato rotulo="Total recalculado" texto={re.total_recalculado_texto} exacto={re.total_recalculado} />
          </dl>
          {re.reglas && <p className="silice-revisar__nota cds--type-body-compact-01">{re.reglas}</p>}
          <DiferenciasDePrecio re={re} />
          {re.hallazgos.map((lote, i) => (
            <section key={lote.titulo} className="silice-revisar__seccion" aria-labelledby={`revisar-lote-${i}`}>
              <h2 id={`revisar-lote-${i}`} className="cds--type-heading-compact-02">
                {tituloDeLote(lote.titulo, lote.hallazgos.length)}
              </h2>
              <TablaDensa
                etiqueta={lote.titulo}
                columnas={COLUMNAS_HALLAZGOS}
                filas={lote.hallazgos.map((h, j) => ({ id: String(j), ...h }))}
                vacio={{ titulo: "Ninguno." }}
              />
            </section>
          ))}
          {r.entrega_anterior ? (
            <Diferencia d={r.entrega_anterior} idTitulo="revisar-anterior" />
          ) : (
            r.sin_entrega_anterior && (
              <p className="silice-revisar__nota cds--type-body-compact-01">{r.sin_entrega_anterior}</p>
            )
          )}
          <ContraMiLista archivo={archivo} r={r} alExpirar={alExpirar} />
          <section className="silice-revisar__seccion" aria-labelledby="revisar-cambios">
            <h2 id="revisar-cambios" className="cds--type-heading-compact-02">
              {r.cambios_titulo}
            </h2>
            <TablaDensa
              etiqueta={r.cambios_titulo}
              columnas={COLUMNAS_CAMBIOS}
              filas={filasDeCambios(r.cambios)}
              vacio={{ titulo: "Ningún cambio nuevo." }}
            />
          </section>
          <section className="silice-revisar__seccion" aria-labelledby="revisar-excel">
            <h2 id="revisar-excel" className="cds--type-heading-compact-02">
              Excel
            </h2>
            <div className="silice-revisar__acciones">
              <DescargaArchivo
                ruta="/v1/revision/excel"
                metodo="POST"
                cuerpo={formularioExcel(archivo, "presupuesto")}
                etiqueta="Descargar el Excel del presupuesto"
                nombrePorOmision="presupuesto.xlsx"
                alExpirar={alExpirar}
                size="sm"
              />
              <DescargaArchivo
                ruta="/v1/revision/excel"
                metodo="POST"
                cuerpo={formularioExcel(archivo, "revision")}
                etiqueta="Descargar el Excel de la revisión"
                nombrePorOmision="revision.xlsx"
                alExpirar={alExpirar}
                size="sm"
              />
            </div>
            <p className="silice-revisar__nota cds--type-body-compact-01">{r.nota_excel}</p>
          </section>
          <Dictamen archivo={archivo} resultados={r.resultados} iniciales={r.dictamenes} alExpirar={alExpirar} />
        </>
      )}
    </>
  );
}

function DiferenciasDePrecio({ re }: { re: ReauditoriaRevision }) {
  if (!re.mensaje_precios) return null;
  if (re.precios_coinciden) {
    return <InlineNotification kind="success" title="" subtitle={re.mensaje_precios} lowContrast hideCloseButton />;
  }
  const ver = presentador(
    re.diferencias.flatMap((d) => [
      [d.declarado, d.declarado_texto],
      [d.recalculado, d.recalculado_texto],
      [d.monto, d.monto_texto],
    ]) as [string, string][],
  );
  const columnas: ColumnaDensa[] = [
    { clave: "codigo_partida", titulo: "Partida" },
    { clave: "campo", titulo: "Campo" },
    { clave: "declarado", titulo: "Declarado", numerica: true, presentar: ver },
    { clave: "recalculado", titulo: "Recalculado", numerica: true, presentar: ver },
    { clave: "monto", titulo: "Diferencia", numerica: true, presentar: ver },
  ];
  return (
    <>
      <InlineNotification kind="error" role="alert" title="" subtitle={re.mensaje_precios} lowContrast hideCloseButton />
      <TablaDensa
        etiqueta="Precios y totales que no coinciden"
        columnas={columnas}
        filas={re.diferencias.map((d, i) => ({
          id: String(i),
          codigo_partida: d.codigo_partida,
          campo: d.campo,
          declarado: d.declarado,
          recalculado: d.recalculado,
          monto: d.monto,
        }))}
      />
    </>
  );
}

function ContraMiLista({ archivo, r, alExpirar }: { archivo: File; r: Revision; alExpirar: () => void }) {
  const [contra, setContra] = useState<ContraLista | null>(r.contra_lista);
  const [pidiendo, setPidiendo] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const consulta = useRef(0);

  if (r.sin_listas) return <p className="silice-revisar__nota cds--type-body-compact-01">{r.sin_listas}</p>;
  if (!contra) return null;

  async function elegir(lista: number) {
    const numero = ++consulta.current;
    setPidiendo(true);
    setError(null);
    try {
      const nueva = await pedir<ContraLista>("/v1/revision/contra-lista", {
        metodo: "POST",
        cuerpo: formularioPaquete(archivo, lista),
      });
      if (numero === consulta.current) setContra(nueva);
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      if (numero === consulta.current) setError(e);
    } finally {
      if (numero === consulta.current) setPidiendo(false);
    }
  }

  return (
    <Diferencia d={contra.diferencia} idTitulo="revisar-mi-lista">
      <Select
        id="revisar-lista"
        labelText="Contrastar con mi lista"
        size="sm"
        value={String(contra.lista_id)}
        disabled={pidiendo}
        onChange={(e) => void elegir(Number.parseInt(e.target.value, 10))}
      >
        {r.listas.map((l) => (
          <SelectItem key={l.id} value={String(l.id)} text={l.nombre} />
        ))}
      </Select>
      {pidiendo && <InlineLoading description="Contrastando con la lista…" />}
      <AvisoError error={error} titulo="No se pudo contrastar" alCerrar={() => setError(null)} />
      {contra.no_contrastables && (
        <p className="silice-revisar__nota cds--type-body-compact-01">{contra.no_contrastables}</p>
      )}
    </Diferencia>
  );
}

function Dictamen({
  archivo,
  resultados,
  iniciales,
  alExpirar,
}: {
  archivo: File;
  resultados: string[];
  iniciales: DictamenAnterior[];
  alExpirar: () => void;
}) {
  const [anteriores, setAnteriores] = useState(iniciales);
  const [resultado, setResultado] = useState(resultados[0] ?? "");
  const [notas, setNotas] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);

  async function guardar(evento: FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      const guardado = await pedir<DictamenGuardado>("/v1/revision/dictamen", {
        metodo: "POST",
        cuerpo: formularioDictamen(archivo, resultado, notas),
      });
      setAnteriores(guardado.dictamenes);
      setMensaje(guardado.mensaje);
      setResultado(resultados[0] ?? ""); // como la clasica (clear_on_submit): el formulario se vacia
      setNotas("");
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setError(e);
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section className="silice-revisar__seccion" aria-labelledby="revisar-dictamen">
      <h2 id="revisar-dictamen" className="cds--type-heading-compact-02">
        Dictamen
      </h2>
      {anteriores.map((d) => (
        <p key={`${d.fecha}|${d.usuario}|${d.resultado}`} className="silice-revisar__nota cds--type-body-compact-01">
          {d.texto}
        </p>
      ))}
      <Form onSubmit={(e) => void guardar(e)} className="silice-revisar__formulario">
        <RadioButtonGroup
          legendText="Dictamen"
          name="revisar-resultado"
          valueSelected={resultado}
          onChange={(valor) => setResultado(String(valor))}
        >
          {resultados.map((x) => (
            <RadioButton key={x} id={`revisar-resultado-${x.replace(/\s+/g, "-")}`} labelText={x} value={x} />
          ))}
        </RadioButtonGroup>
        <TextArea id="revisar-notas" labelText="Notas" value={notas} rows={3} onChange={(e) => setNotas(e.target.value)} />
        <Button type="submit" kind="primary" size="md" disabled={guardando}>
          {guardando ? "Guardando…" : "Guardar dictamen"}
        </Button>
      </Form>
      <AvisoError error={error} titulo="No se pudo guardar el dictamen" alCerrar={() => setError(null)} />
      {mensaje && <InlineNotification kind="success" title="" subtitle={mensaje} lowContrast hideCloseButton />}
    </section>
  );
}
