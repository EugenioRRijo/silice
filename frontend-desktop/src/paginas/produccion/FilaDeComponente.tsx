import { Button, Select, SelectItem } from "@carbon/react";
import type { JSX } from "react";
import { CampoDeConsulta } from "../../comun/CampoDeConsulta";
import { CampoTexto } from "../../comun/CampoTexto";
import { AYUDA_CIFRAS } from "../../indicadores/cifraEscrita";
import { TIPOS, UNIDADES } from "./logicaPlanta";
import type { FilaDeComponente as Fila } from "./logicaPlanta";

interface Props {
  // Posición (desde 1) y el prefijo único de los campos.
  numero: number;
  base: string;
  fila: Fila;
  // Con una sola fila no hay nada que quitar.
  sePuedeQuitar: boolean;
  alCambiar: (cambio: Partial<Fila>) => void;
  alQuitar: () => void;
  alExpirar: () => void;
}

// Un componente de la receta. La unidad y el tipo no tienen valor por defecto: de ellos depende si el consumo sale del
// inventario o se compra a precio de lista, y de ahí el costo de la mezcla.
export function FilaDeComponente({ numero, base, fila, sePuedeQuitar, alCambiar, alQuitar, alExpirar }: Props): JSX.Element {
  const nombre = `Componente ${numero}`;
  return (
    <fieldset className="receta-componente">
      <legend className="cds--type-label-02">{nombre}</legend>
      <CampoDeConsulta
        id={`${base}-codigo`}
        etiqueta="Código"
        tabla="componentes_de_receta"
        tamano="md"
        texto={fila.codigo}
        alCambiarTexto={(codigo) => alCambiar({ codigo })}
        alExpirar={alExpirar}
      />
      <CampoTexto
        id={`${base}-cantidad`}
        labelText="Cantidad por t"
        inputMode="decimal"
        autoComplete="off"
        helperText={AYUDA_CIFRAS}
        value={fila.cantidad}
        onChange={(e) => alCambiar({ cantidad: e.target.value })}
      />
      <Select id={`${base}-unidad`} labelText="Unidad" value={fila.unidad} onChange={(e) => alCambiar({ unidad: e.target.value })}>
        <SelectItem value="" text="Elija la unidad" />
        {UNIDADES.map((u) => (
          <SelectItem key={u.valor} value={u.valor} text={u.texto} />
        ))}
      </Select>
      <Select id={`${base}-tipo`} labelText="Tipo" value={fila.tipo} onChange={(e) => alCambiar({ tipo: e.target.value })}>
        <SelectItem value="" text="Elija el tipo" />
        {TIPOS.map((t) => (
          <SelectItem key={t.valor} value={t.valor} text={t.texto} />
        ))}
      </Select>
      <Button
        className="receta-componente__quitar"
        kind="ghost"
        size="sm"
        disabled={!sePuedeQuitar}
        aria-label={`Quitar ${nombre.toLowerCase()}${fila.codigo.trim() ? ` (${fila.codigo.trim()})` : ""}`}
        onClick={alQuitar}
      >
        Quitar
      </Button>
    </fieldset>
  );
}
