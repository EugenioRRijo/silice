import { Button, Checkbox } from "@carbon/react";
import { InlineLoading, InlineNotification } from "../../comun/carbonEs";
import { useEffect, useRef, useState } from "react";
import type { FormEvent, JSX, Ref } from "react";
import { pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { textoParaEscribir } from "../../indicadores/cifraEscrita";
import {
  AYUDA_TRABAJADOS,
  AYUDA_VERSION,
  ETIQUETA_CALENDARIO,
  ETIQUETA_TRABAJADOS,
  ETIQUETA_VERSION,
  RUTA_CALCULAR,
  RUTA_COMPONENTES,
  armarPeticion,
  filasIniciales,
  multiplicadorEsVe,
  porcentajeEsVe,
  unidadDe,
} from "./logicaFcas";
import type { Escrito, FilaFcas, PorDefectoFcas, ResultadoFcas } from "./logicaFcas";

type Carga = { tipo: "cargando" } | { tipo: "listo"; datos: PorDefectoFcas } | { tipo: "error"; error: unknown };

const COLUMNAS: ColumnaDensa[] = [
  { clave: "nombre", titulo: "Renglón" },
  { clave: "aporte", titulo: "Parte del FCAS", numerica: true, presentar: formatoEsVe },
];

// «FCAS por componentes»: el factor de costos asociados al salario que sale de los días pagados y de los aportes
// patronales, con la fuente de cada componente. Se muestra al lado del FCAS de la versión y NO se aplica solo: el FCAS
// de una versión se cambia donde ya se cambia, en la pestaña Parámetros de la Hoja del proyecto. La pantalla no suma
// ni multiplica: solo escribe con coma lo que calcula el servidor.
export function CalculadoraFCAS({ alExpirar }: { alExpirar: (error: unknown) => void }): JSX.Element {
  const [carga, setCarga] = useState<Carga>({ tipo: "cargando" });
  const [escrito, setEscrito] = useState<Escrito>({ dias_calendario: "", dias_trabajados: "217,28", fcas_version: "" });
  const [filas, setFilas] = useState<Record<string, FilaFcas>>({});
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [resultado, setResultado] = useState<ResultadoFcas | null>(null);
  const [fallo, setFallo] = useState<unknown>(null);
  const [calculando, setCalculando] = useState(false);
  const [enfocar, setEnfocar] = useState(0);
  const cajaDelAviso = useRef<HTMLDivElement>(null);
  const cajaDelResultado = useRef<HTMLDivElement>(null);
  const cajaDelFallo = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let vigente = true;
    pedir<PorDefectoFcas>(RUTA_COMPONENTES).then(
      (datos) => {
        if (!vigente) return;
        setCarga({ tipo: "listo", datos });
        setEscrito((e) => ({
          ...e,
          dias_calendario: textoParaEscribir(datos.dias_calendario),
          fcas_version: textoParaEscribir(datos.fcas_version),
        }));
        setFilas(filasIniciales(datos.componentes));
      },
      (error: unknown) => {
        if (!vigente) return;
        alExpirar(error);
        setCarga({ tipo: "error", error });
      },
    );
    return () => {
      vigente = false;
    };
  }, [alExpirar]);

  // El botón se desactiva mientras se calcula: el foco pasa a lo que llegó (el aviso, el resultado o el error).
  useEffect(() => {
    if (enfocar === 0) return;
    (cajaDelFallo.current ?? cajaDelAviso.current ?? cajaDelResultado.current)?.focus();
  }, [enfocar]);

  if (carga.tipo === "cargando") return <InlineLoading description="Cargando los componentes del FCAS..." status="active" />;
  if (carga.tipo === "error") return <AvisoError error={carga.error} titulo="No se pudieron leer los componentes del FCAS" />;
  const { componentes } = carga.datos;

  const cambiarFila = (id: string, cambio: Partial<FilaFcas>) =>
    setFilas((actuales) => ({ ...actuales, [id]: { ...actuales[id]!, ...cambio } }));

  const calcular = (evento: FormEvent) => {
    evento.preventDefault();
    setFallo(null);
    const peticion = armarPeticion(escrito, componentes, filas);
    if ("errores" in peticion) {
      setErrores(peticion.errores);
      return;
    }
    setErrores({});
    setCalculando(true);
    pedir<ResultadoFcas>(RUTA_CALCULAR, { metodo: "POST", cuerpo: peticion.cuerpo }).then(
      (respuesta) => {
        setResultado(respuesta);
        setCalculando(false);
        setEnfocar((n) => n + 1);
      },
      (error: unknown) => {
        alExpirar(error);
        setResultado(null);
        setFallo(error);
        setCalculando(false);
        setEnfocar((n) => n + 1);
      },
    );
  };

  const campo = (clave: keyof Escrito, etiqueta: string, ayuda?: string) => (
    <CampoTexto
      id={`fcas-${clave}`}
      labelText={etiqueta}
      helperText={ayuda}
      size="sm"
      inputMode="decimal"
      value={escrito[clave]}
      invalid={errores[clave] !== undefined}
      invalidText={errores[clave]}
      onChange={(e) => setEscrito({ ...escrito, [clave]: e.target.value })}
    />
  );

  return (
    <div className="silice-fcas">
      <form className="silice-precios-empresa__formulario" onSubmit={calcular}>
        <div className="silice-precios-empresa__campos">
          {campo("dias_calendario", ETIQUETA_CALENDARIO)}
          {campo("dias_trabajados", ETIQUETA_TRABAJADOS, AYUDA_TRABAJADOS)}
          {campo("fcas_version", ETIQUETA_VERSION, AYUDA_VERSION)}
        </div>
        <ul className="silice-fcas__componentes" aria-label="Componentes del FCAS">
          {componentes.map((c) => (
            <li key={c.id} className="silice-fcas__componente">
              <Checkbox
                id={`fcas-activo-${c.id}`}
                labelText={c.nombre}
                checked={filas[c.id]?.activo ?? false}
                onChange={(_, { checked }) => cambiarFila(c.id, { activo: checked })}
              />
              <CampoTexto
                id={`fcas-valor-${c.id}`}
                labelText={`Valor de ${c.nombre} (${unidadDe(c.base)})`}
                size="sm"
                inputMode="decimal"
                disabled={!filas[c.id]?.activo}
                value={filas[c.id]?.valor ?? ""}
                invalid={errores[c.id] !== undefined}
                invalidText={errores[c.id]}
                onChange={(e) => cambiarFila(c.id, { valor: e.target.value })}
              />
              <p className="silice-precios-empresa__nota cds--type-label-01">
                {c.a_cotejar && <strong className="silice-fcas__cotejar">a cotejar</strong>} {c.fuente}
              </p>
            </li>
          ))}
        </ul>
        <div className="silice-precios-empresa__acciones">
          <Button type="submit" kind="primary" size="md" disabled={calculando}>
            Calcular el FCAS
          </Button>
          {calculando && <InlineLoading description="Calculando..." status="active" />}
        </div>
      </form>
      {fallo !== null && (
        <div ref={cajaDelFallo} tabIndex={-1}>
          <AvisoError error={fallo} titulo="No se calculó el FCAS" />
        </div>
      )}
      {resultado !== null && fallo === null && (
        <Resultado resultado={resultado} regionDelAviso={cajaDelAviso} regionDelResultado={cajaDelResultado} />
      )}
    </div>
  );
}

function Resultado({
  resultado: r,
  regionDelAviso,
  regionDelResultado,
}: {
  resultado: ResultadoFcas;
  regionDelAviso: Ref<HTMLDivElement>;
  regionDelResultado: Ref<HTMLDivElement>;
}): JSX.Element {
  const filas = r.desglose.map((d) => ({ id: d.id, nombre: d.nombre, aporte: d.aporte }));
  return (
    <div ref={regionDelResultado} tabIndex={-1} className="silice-fcas__resultado">
      {r.a_cotejar.length > 0 && (
        <div ref={regionDelAviso} tabIndex={-1}>
          <InlineNotification
            kind="warning"
            role="status"
            lowContrast
            hideCloseButton
            title="Hay cifras por cotejar"
            subtitle={`Antes de aplicar el FCAS, coteje con la norma vigente: ${r.a_cotejar.map((a) => a.nombre).join("; ")}.`}
          />
        </div>
      )}
      <div className="silice-fcas__lado-a-lado">
        <section aria-labelledby="fcas-calculado">
          <h3 id="fcas-calculado" className="cds--type-heading-compact-01">
            FCAS calculado
          </h3>
          <p className="cds--type-productive-heading-04">{porcentajeEsVe(r.porcentaje)}</p>
          <p className="cds--type-body-compact-01">{multiplicadorEsVe(r.multiplicador)}</p>
          <p className="silice-precios-empresa__nota cds--type-label-01">
            Días pagados: {formatoEsVe(r.dias_pagados)}. Solo por días: {formatoEsVe(r.fcas_por_dias)}.
          </p>
        </section>
        {r.version !== null && (
          <section aria-labelledby="fcas-version">
            <h3 id="fcas-version" className="cds--type-heading-compact-01">
              FCAS de la versión
            </h3>
            <p className="cds--type-productive-heading-04">{porcentajeEsVe(r.version.porcentaje)}</p>
            <p className="cds--type-body-compact-01">{multiplicadorEsVe(r.version.multiplicador)}</p>
          </section>
        )}
      </div>
      <TablaDensa etiqueta="Desglose del FCAS" columnas={COLUMNAS} filas={filas} />
      <p className="cds--type-body-compact-01">
        Esto no cambia ninguna versión. Para aplicarlo, escriba <strong>{textoParaEscribir(r.fcas)}</strong> en el
        FCAS de la pestaña Parámetros del presupuesto de la obra; es una fracción: 0,50 equivale a 50 % y a
        multiplicar el sueldo por 1,50.
      </p>
    </div>
  );
}
