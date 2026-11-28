import { RadioButton, RadioButtonGroup } from "@carbon/react";
import { useModoDeColor } from "./modoDeColor";
import type { ModoDeColor as ModoDeColorValor } from "./modoDeColor";

function esModoDeColor(valor: unknown): valor is ModoDeColorValor {
  return valor === "claro" || valor === "oscuro" || valor === "sistema";
}

// Selector de apariencia en Cuenta › Configuración: tres estados explícitos (Claro, Oscuro y Como el sistema), donde el
// estado del sistema indica cuál rige en este momento.
export function SelectorDeModo() {
  const { modo, delSistema, elegir } = useModoDeColor();

  return (
    <RadioButtonGroup
      name="modo-de-color"
      legendText="Apariencia"
      orientation="vertical"
      valueSelected={modo}
      helperText="El modo oscuro cambia la pantalla; los PDF y el Excel que se entregan no cambian."
      onChange={(seleccion) => {
        if (esModoDeColor(seleccion)) elegir(seleccion);
      }}
    >
      <RadioButton value="claro" labelText="Claro" />
      <RadioButton value="oscuro" labelText="Oscuro" />
      <RadioButton value="sistema" labelText={`Como el sistema (ahora ${delSistema})`} />
    </RadioButtonGroup>
  );
}
