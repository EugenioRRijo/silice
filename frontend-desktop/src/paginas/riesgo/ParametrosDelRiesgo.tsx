import { Select, SelectItem } from "@carbon/react";
import type { JSX } from "react";
import type { InsumosDeLaObra, MapaDeSeries } from "../../api/riesgo";
import { CampoTexto } from "../../comun/CampoTexto";
import { AYUDA_CIFRAS } from "../../indicadores/cifraEscrita";
import { ROTULOS, ayudaDelInicio } from "./logica";
import type { Campos } from "./logica";

interface Props {
  campos: Campos;
  errores: Partial<Record<keyof Campos, string>>;
  alCambiar: (clave: keyof Campos, valor: string) => void;
  insumos: InsumosDeLaObra;
  mapa: MapaDeSeries;
  alElegirSerie: (insumo: string, serie: string) => void;
}

const SIN_SERIE = "";

// Los parámetros de la proyección (D-V-3) y la serie que mueve cada insumo. Un insumo sin serie sigue a la tasa del BCV
// en un presupuesto en Bs y queda fijo en uno en USD (lo dice el servidor en los supuestos). Las cifras se escriben con
// punto de miles: «2.000».
export function ParametrosDelRiesgo({ campos, errores, alCambiar, insumos, mapa, alElegirSerie }: Props): JSX.Element {
  const numero = (clave: Exclude<keyof Campos, "inicio">) => (
    <CampoTexto
      id={`riesgo-${clave}`}
      labelText={ROTULOS[clave]}
      inputMode="numeric"
      value={campos[clave]}
      invalid={errores[clave] !== undefined}
      invalidText={errores[clave]}
      onChange={(e) => alCambiar(clave, e.target.value)}
    />
  );
  const conSerie = [...insumos.insumos, ...insumos.componentes];
  // Sin línea base de control no hay de dónde tomar el inicio: el campo es obligatorio y se dice en el rótulo.
  const obligatoria = insumos.inicio_linea_base === null;
  return (
    <>
      <fieldset className="riesgo-campos">
        <legend className="cds--type-heading-compact-01">Plazo y simulación</legend>
        <CampoTexto
          id="riesgo-inicio"
          type="date"
          labelText={obligatoria ? "Fecha de inicio (obligatoria)" : "Fecha de inicio"}
          required={obligatoria}
          helperText={ayudaDelInicio(insumos.inicio_linea_base)}
          value={campos.inicio}
          invalid={errores.inicio !== undefined}
          invalidText={errores.inicio}
          // Carbon no enlaza su texto de error al campo: se enlaza aquí para que la lectora lo diga con el foco.
          aria-describedby={errores.inicio !== undefined ? "riesgo-inicio-error-msg" : undefined}
          onChange={(e) => alCambiar("inicio", e.target.value)}
        />
        {numero("meses")}
        {numero("trayectorias")}
        {numero("semilla")}
        {numero("ventana")}
        <p className="riesgo-nota cds--type-helper-text-01">{AYUDA_CIFRAS}</p>
      </fieldset>
      <fieldset className="riesgo-series">
        <legend className="cds--type-heading-compact-01">Serie que mueve cada insumo</legend>
        {conSerie.length === 0 && <p className="riesgo-nota cds--type-body-compact-01">Esta versión no tiene insumos.</p>}
        {conSerie.map((insumo, i) => (
          <Select
            key={insumo}
            id={`riesgo-serie-${i}`}
            labelText={insumo}
            value={mapa[insumo] ?? SIN_SERIE}
            onChange={(e) => alElegirSerie(insumo, e.target.value)}
          >
            <SelectItem value={SIN_SERIE} text="Sin serie propia" />
            {insumos.series.map((s) => (
              <SelectItem key={s.codigo} value={s.codigo} text={s.nombre} />
            ))}
          </Select>
        ))}
        {insumos.mezclas.map((m) => (
          <p key={m.insumo} className="riesgo-nota cds--type-body-compact-01">
            {`${m.insumo}: se recalcula con su receta del cálculo n.º ${m.calculo}; sus componentes siguen su propia serie.`}
          </p>
        ))}
      </fieldset>
    </>
  );
}
