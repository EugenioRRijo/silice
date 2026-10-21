import { Button, InlineNotification, Select, SelectItem } from "@carbon/react";
import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import { AvisoDeEdicion } from "./AvisoDeEdicion";
import { LARGO_DE_CELDA } from "./logica";
import type { Resumen } from "./logica";
import {
  AYUDA_ALTURAS,
  AYUDA_CIRCUITOS,
  AYUDA_PLANO,
  CAMPOS_DE_CIRCUITO,
  COLUMNAS_DEL_INFORME,
  ETIQUETA_DE_SUBIDA,
  EXTENSIONES_DE_PLANO,
  ROTULO_CARGAR_ALTURAS,
  ROTULO_CONTINUAR_UNIDAD,
  ROTULO_DECLARAR_CIRCUITOS,
  ROTULO_DESCARTAR_PLANO,
  ROTULO_FUSIONAR,
  ROTULO_IMPORTAR,
  ROTULO_LEER_PLANO,
  etiquetaDeAltura,
  etiquetaDeCampoDeCircuito,
  filasDelInforme,
  lineaDeFilasPorTabla,
  lineaDeOrigenes,
  valoresDeCircuitos,
} from "./logicaPlano";
import type { AlturaPendiente, CircuitoSupuesto, ConteoDePlano, FilaDeInforme, ValoresDeCircuito } from "./logicaPlano";
import { useImportacion } from "./useImportacion";
import "./plano.scss";

interface Props {
  id: string;
  // El `rev` del borrador según la página.
  rev: number;
  // Hay una edición del espacio esperando su pausa o en vuelo: no se manda nada hasta que termine (el `rev` cambiaría).
  ocupadoPorEdicion?: boolean;
  alAusente: () => void;
  alAceptar: (resumen: Resumen) => void;
  // Vuelve a leer el borrador y las tablas del espacio.
  alRecargar: () => Promise<void>;
  // Descarta lo que se ve y abre otro borrador de la versión.
  alReabrir: () => void;
  alExpirar: () => void;
  // El flujo ocupa el espacio mientras fusiona y vuelve a leerlo: la página no deja editar las tablas.
  alOcuparse?: (ocupada: boolean) => void;
}

function Conteos({ conteos }: { conteos: ConteoDePlano[] }) {
  return (
    <dl className="silice-plano__conteos">
      {conteos.map((c) => (
        <div key={c.rotulo} className="silice-plano__conteo">
          <dt className="cds--type-label-01">{c.rotulo}</dt>
          <dd className="cds--type-heading-03">{c.cantidad}</dd>
        </div>
      ))}
    </dl>
  );
}

function TablaDelInforme({ etiqueta, informe }: { etiqueta: string; informe: FilaDeInforme[] }) {
  return (
    <TablaDensa
      etiqueta={etiqueta}
      columnas={COLUMNAS_DEL_INFORME.map((c) => ({ ...c, ordenable: false }))}
      filas={filasDelInforme(informe)}
      vacio={{ titulo: "El informe no trae líneas" }}
    />
  );
}

interface PropsDeAlturas {
  pendientes: AlturaPendiente[];
  deshabilitado: boolean;
  alCargar: (textos: Record<string, string>) => void;
}

// «Alturas pendientes» (ui/paginas/hoja.py:1368-1381): un campo por ambiente, en metros. Todo viaja como texto, tal cual.
function FormularioDeAlturas({ pendientes, deshabilitado, alCargar }: PropsDeAlturas) {
  const base = useId();
  const [textos, setTextos] = useState<Record<string, string>>({});
  return (
    <section className="silice-hoja__seccion">
      <h3 className="cds--type-heading-compact-01">Alturas pendientes</h3>
      <p className="cds--type-helper-text-01">{AYUDA_ALTURAS}</p>
      <form
        className="silice-plano__formulario"
        onSubmit={(e) => {
          e.preventDefault();
          alCargar(textos);
        }}
      >
        <div className="silice-plano__campos">
          {pendientes.map((p, i) => (
            <CampoTexto
              key={p.id}
              id={`${base}-${i}`}
              size="sm"
              labelText={etiquetaDeAltura(p)}
              inputMode="decimal"
              autoComplete="off"
              maxLength={LARGO_DE_CELDA}
              value={textos[p.id] ?? ""}
              onChange={(e) => setTextos((previo) => ({ ...previo, [p.id]: e.target.value }))}
            />
          ))}
        </div>
        <div>
          <Button type="submit" kind="secondary" size="sm" disabled={deshabilitado}>
            {ROTULO_CARGAR_ALTURAS}
          </Button>
        </div>
      </form>
    </section>
  );
}

interface PropsDeCircuitos {
  supuestos: CircuitoSupuesto[];
  deshabilitado: boolean;
  alDeclarar: (valores: Record<string, ValoresDeCircuito>) => void;
}

// «Circuitos por declarar» (ui/paginas/hoja.py:1384-1400): cuatro campos por circuito, con lo que supuso el plano.
function FormularioDeCircuitos({ supuestos, deshabilitado, alDeclarar }: PropsDeCircuitos) {
  const base = useId();
  const [valores, setValores] = useState<Record<string, ValoresDeCircuito>>(() => valoresDeCircuitos(supuestos));
  const cambiar = (id: string, lugar: number, texto: string) =>
    setValores((previo) => {
      const actuales = [...(previo[id] ?? ["", "", "", ""])] as ValoresDeCircuito;
      actuales[lugar] = texto;
      return { ...previo, [id]: actuales };
    });
  return (
    <section className="silice-hoja__seccion">
      <h3 className="cds--type-heading-compact-01">Circuitos por declarar</h3>
      <p className="cds--type-helper-text-01">{AYUDA_CIRCUITOS}</p>
      <form
        className="silice-plano__formulario"
        onSubmit={(e) => {
          e.preventDefault();
          alDeclarar(valores);
        }}
      >
        {supuestos.map((c, i) => (
          <fieldset key={c.id} className="silice-plano__circuito">
            <legend className="cds--type-label-01">{`Circuito ${c.id}`}</legend>
            <div className="silice-plano__campos silice-plano__campos--circuito">
              {CAMPOS_DE_CIRCUITO.map((campo, lugar) => (
                <CampoTexto
                  key={campo.clave}
                  id={`${base}-${i}-${campo.clave}`}
                  size="sm"
                  labelText={campo.rotulo}
                  aria-label={etiquetaDeCampoDeCircuito(campo.rotulo, c.id)}
                  inputMode="numeric"
                  autoComplete="off"
                  maxLength={LARGO_DE_CELDA}
                  value={valores[c.id]?.[lugar] ?? ""}
                  onChange={(e) => cambiar(c.id, lugar, e.target.value)}
                />
              ))}
            </div>
          </fieldset>
        ))}
        <div>
          <Button type="submit" kind="secondary" size="sm" disabled={deshabilitado}>
            {ROTULO_DECLARAR_CIRCUITOS}
          </Button>
        </div>
      </form>
    </section>
  );
}

interface PropsDeUnidad {
  unidades: string[];
  deshabilitado: boolean;
  alContinuar: (unidad: string) => void;
}

// El plano no dice su unidad: el servidor manda las que acepta y la persona elige (ui/paginas/hoja.py:1319-1325).
function UnidadDelDibujo({ unidades, deshabilitado, alContinuar }: PropsDeUnidad) {
  const idSelector = useId();
  const [unidad, setUnidad] = useState(unidades[0] ?? "");
  return (
    <div className="silice-plano__unidad">
      <Select id={idSelector} labelText="Unidad del dibujo" size="sm" value={unidad} onChange={(e) => setUnidad(e.target.value)}>
        {unidades.map((u) => (
          <SelectItem key={u} value={u} text={u} />
        ))}
      </Select>
      <div>
        <Button kind="primary" size="sm" disabled={deshabilitado || unidad === ""} onClick={() => alContinuar(unidad)}>
          {ROTULO_CONTINUAR_UNIDAD}
        </Button>
      </div>
    </div>
  );
}

// Lo que puede recibir el foco tras una acción: si es el resultado vigente lleva `data-resultado` (ver el efecto de
// `ImportarPlano`). Con `tabIndex=-1` se enfoca por programa, sin entrar en el orden del Tab.
function Resultado({ activo, children }: { activo: boolean; children: ReactNode }) {
  return (
    <div {...(activo ? { "data-resultado": "" } : {})} tabIndex={-1} className="silice-plano__resultado">
      {children}
    </div>
  );
}

// «Importar plano (DXF o IFC)» de la pestaña Espacio y metrajes (RF-50, RF-51; ui/paginas/hoja.py:1225-1485): subir un .dxf o
// .ifc, leerlo (P1), pedir la unidad si falta (P2), cargar las alturas (P3) y declarar los circuitos (P4), fusionar con el
// borrador (P5) o descartar (P6). La importación vive en el servidor, aparte del borrador, hasta fusionarla.
export function ImportarPlano({ id, rev, ocupadoPorEdicion = false, alAusente, alAceptar, alRecargar, alReabrir, alExpirar, alOcuparse }: Props) {
  const imp = useImportacion({ id, rev, alAusente, alAceptar, alRecargar, alExpirar, alOcuparse });
  const idCuerpo = useId();
  const cuerpo = useRef<HTMLDivElement>(null);
  const { importacion, fusion, lectura } = imp.datos;
  const [abierto, setAbierto] = useState(importacion !== null || fusion !== null);
  const [archivo, setArchivo] = useState<File | null>(null);
  const bloqueado = imp.ocupado !== null || ocupadoPorEdicion || imp.detenido;

  // Tras leer, cargar alturas, declarar circuitos, fusionar o descartar (o fallar), el foco va al resultado: el botón que lo
  // tenía puede haber desaparecido y no debe quedar en `body`.
  useEffect(() => {
    if (imp.foco === 0) return;
    // Sin resultado a la vista (por ejemplo tras recargar con la primera lectura fallida) el foco va a «Leer plano».
    (cuerpo.current?.querySelector<HTMLElement>("[data-resultado]") ?? cuerpo.current?.querySelector<HTMLElement>("[data-leer]"))?.focus();
  }, [imp.foco]);

  // El primero de estos que exista es el que recibe el foco: el error, el aviso de la acción, o la importación vigente.
  const marca = (destino: "error" | "aviso" | "importacion" | "fusion") => {
    const actual = imp.error !== null ? "error" : imp.aviso !== null ? "aviso" : importacion !== null ? "importacion" : "fusion";
    return actual === destino;
  };

  const alturas = importacion?.alturas_pendientes ?? [];
  const circuitos = importacion?.circuitos_supuestos ?? [];

  return (
    <section className="silice-hoja__seccion silice-plano">
      <h2 className="cds--type-heading-compact-02">
        <Button kind="ghost" size="sm" aria-expanded={abierto} aria-controls={idCuerpo} onClick={() => setAbierto((a) => !a)}>
          {ROTULO_IMPORTAR}
        </Button>
      </h2>
      {/* Fuera del cuerpo ocupado (aria-busy): algunos lectores retienen lo que se anuncia dentro de una región ocupada. */}
      <p className="cds--type-helper-text-01" role="status">
        {imp.ocupado ?? ""}
      </p>
      {abierto && (
        <div id={idCuerpo} ref={cuerpo} className="silice-plano__cuerpo" aria-busy={imp.ocupado !== null}>
          <p className="cds--type-body-compact-01">{AYUDA_PLANO}</p>
          <SubidaArchivo etiqueta={ETIQUETA_DE_SUBIDA} extensiones={EXTENSIONES_DE_PLANO} alElegir={setArchivo} deshabilitada={bloqueado} />
          {archivo !== null && <p className="cds--type-body-compact-01">Archivo elegido: {archivo.name}</p>}
          <div>
            <Button
              kind="primary"
              size="sm"
              disabled={bloqueado}
              data-leer=""
              onClick={() => {
                if (archivo === null) imp.faltaArchivo();
                else void imp.leer(archivo);
              }}
            >
              {ROTULO_LEER_PLANO}
            </Button>
          </div>
          {imp.error !== null && (
            <Resultado activo={marca("error")}>
              {imp.error.tipo === "otro" ? (
                <AvisoError error={imp.error.mensaje} titulo={imp.error.titulo} />
              ) : (
                <AvisoDeEdicion error={imp.error} id={`${idCuerpo}-error`} alRecargar={() => void imp.recargar()} alReabrir={alReabrir} />
              )}
            </Resultado>
          )}

          {imp.aviso !== null && (
            <Resultado activo={marca("aviso")}>
              <InlineNotification kind="success" role="status" lowContrast hideCloseButton title={imp.aviso} />
            </Resultado>
          )}

          {importacion !== null && importacion.estado === "rechazada" && (
            <>
              <Resultado activo={marca("importacion")}>
                <AvisoError error={`No se pudo importar «${importacion.archivo}»: ${importacion.mensaje}`} titulo="Plano no importado" />
              </Resultado>
              <div>
                <Button kind="tertiary" size="sm" disabled={bloqueado} onClick={() => void imp.descartar()}>
                  {ROTULO_DESCARTAR_PLANO}
                </Button>
              </div>
            </>
          )}

          {importacion !== null && importacion.estado === "detenida" && (
            <>
              <Resultado activo={marca("importacion")}>
                <InlineNotification kind="warning" role="status" lowContrast hideCloseButton title="Falta la unidad del dibujo" subtitle={importacion.mensaje} />
              </Resultado>
              <UnidadDelDibujo
                key={lectura}
                unidades={importacion.unidades}
                deshabilitado={bloqueado}
                alContinuar={(unidad) => void imp.reanudar(unidad)}
              />
              <div>
                <Button kind="tertiary" size="sm" disabled={bloqueado} onClick={() => void imp.descartar()}>
                  {ROTULO_DESCARTAR_PLANO}
                </Button>
              </div>
            </>
          )}

          {importacion !== null && importacion.estado === "importada" && (
            <>
              <h3
                {...(marca("importacion") ? { "data-resultado": "" } : {})}
                tabIndex={-1}
                className="cds--type-heading-compact-02 silice-plano__resultado"
              >
                {`Informe de la importación de ${importacion.archivo}`}
              </h3>
              <Conteos conteos={importacion.conteos} />
              <TablaDelInforme etiqueta="Informe de la importación" informe={importacion.informe} />
              {alturas.length > 0 && (
                <FormularioDeAlturas
                  key={`${lectura}-${alturas.map((a) => a.id).join("|")}`}
                  pendientes={alturas}
                  deshabilitado={bloqueado}
                  alCargar={(textos) => void imp.cargarAlturas(textos)}
                />
              )}
              {circuitos.length > 0 && (
                <FormularioDeCircuitos
                  key={`${lectura}-${circuitos.map((c) => c.id).join("|")}`}
                  supuestos={circuitos}
                  deshabilitado={bloqueado}
                  alDeclarar={(valores) => void imp.declarar(valores)}
                />
              )}
              {importacion.aviso_pendientes !== null && (
                <InlineNotification kind="info" role="status" lowContrast hideCloseButton title="Antes de fusionar" subtitle={importacion.aviso_pendientes} />
              )}
              <div className="silice-plano__acciones">
                <Button kind="primary" size="sm" disabled={bloqueado} onClick={() => void imp.fusionar()}>
                  {ROTULO_FUSIONAR}
                </Button>
                <Button kind="tertiary" size="sm" disabled={bloqueado} onClick={() => void imp.descartar()}>
                  {ROTULO_DESCARTAR_PLANO}
                </Button>
              </div>
            </>
          )}

          {importacion === null && fusion !== null && (
            <section className="silice-hoja__seccion">
              <Resultado activo={marca("fusion")}>
                <InlineNotification kind="success" role="status" lowContrast hideCloseButton title="Importación fusionada" subtitle={fusion.mensaje} />
              </Resultado>
              <h3 className="cds--type-heading-compact-02">Informe de la última fusión</h3>
              <Conteos conteos={fusion.fusion.por_tipo} />
              <p className="cds--type-helper-text-01">{lineaDeFilasPorTabla(fusion.fusion.filas_por_tabla)}</p>
              <p className="cds--type-helper-text-01">{lineaDeOrigenes(fusion.fusion.origenes)}</p>
              <TablaDelInforme etiqueta="Informe de la fusión" informe={fusion.informe} />
            </section>
          )}
        </div>
      )}
    </section>
  );
}
