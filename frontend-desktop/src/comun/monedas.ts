// Las monedas que maneja Silice (el nucleo valora en bolivares y en dolares): una sola definicion para toda la interfaz.
// Solo codigos y rotulos; ningun monto se calcula aqui.
export const MONEDAS = ["Bs", "USD"] as const;

export type Moneda = (typeof MONEDAS)[number];

// La moneda destino de una conversion no puede ser la actual (MONEDAS de la clasica).
export function monedasDestino(actual: string | null): string[] {
  return MONEDAS.filter((m) => m !== actual);
}

const NOMBRE: Record<Moneda, { corto: string; completo: string }> = {
  Bs: { corto: "Bolívares", completo: "Bolívares" },
  USD: { corto: "Dólares", completo: "Dólares estadounidenses" },
};

// «Bolívares (Bs)» y «Dólares (USD)»; con `completo`, «Dólares estadounidenses (USD)» (el diálogo de «Nueva obra»).
export function rotuloDeMoneda(moneda: Moneda, completo = false): string {
  return `${completo ? NOMBRE[moneda].completo : NOMBRE[moneda].corto} (${moneda})`;
}
