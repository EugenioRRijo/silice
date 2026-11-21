import "./portada.scss";

interface FilaModulo {
  ref: string;
  concepto: string;
  monto: string;
  estado: string;
  clase: "critico" | "atipico" | "verificado";
}

interface VistaModulo {
  titulo: string;
  resumen: string;
  kpiIzqRotulo: string;
  kpiIzqValor: string;
  kpiDerRotulo: string;
  kpiDerValor: string;
  filas: FilaModulo[];
}

const MODULOS: Record<string, VistaModulo> = {
  forense: {
    titulo: "PLAN DE PAGOS · Inspección forense de libro",
    resumen: "Comparación celda por celda entre el libro entregado y el recálculo oficial.",
    kpiIzqRotulo: "Declarado en libro",
    kpiIzqValor: "1.740,89 USD",
    kpiDerRotulo: "Recalculado Sílice",
    kpiDerValor: "1.586,61 USD",
    filas: [
      { ref: "PRESUPUESTO!F12", concepto: "Valor quemado sobre fórmula de total", monto: "+154,28 USD", estado: "Crítico", clase: "critico" },
      { ref: "VALUACIONES!J48", concepto: "Desviación atípica de precio unitario", monto: "0,39 %", estado: "Atípico", clase: "atipico" },
      { ref: "COVENIN!C104", concepto: "Matriz APU y FCAS consistentes", monto: "242,64 USD", estado: "Verificado", clase: "verificado" },
    ],
  },
  apu: {
    titulo: "HOJA APU · Concreto R28 = 250 kg/cm² (m³)",
    resumen: "Composición exacta en Decimal sin redondeo intermedio de punto flotante.",
    kpiIzqRotulo: "Costo directo",
    kpiIzqValor: "205,40 USD",
    kpiDerRotulo: "Precio unitario",
    kpiDerValor: "242,64 USD",
    filas: [
      { ref: "MAT-014", concepto: "Cemento Portland gris + agregados", monto: "148,20 USD", estado: "Verificado", clase: "verificado" },
      { ref: "EQP-008", concepto: "Mezcladora + vibrador (COPAC)", monto: "31,90 USD", estado: "Verificado", clase: "verificado" },
      { ref: "MDO-FCAS", concepto: "Mano de obra directa + factor 182,40 %", monto: "25,30 USD", estado: "Verificado", clase: "verificado" },
    ],
  },
  control: {
    titulo: "CONTROL DE OBRA · Avance y proyecciones EVM",
    resumen: "Frentes de trabajo, valuaciones acumuladas y costo estimado al cierre.",
    kpiIzqRotulo: "EAC proyectado",
    kpiIzqValor: "48.910,25 USD",
    kpiDerRotulo: "Punto de equilibrio",
    kpiDerValor: "64,20 %",
    filas: [
      { ref: "FRENTE-01", concepto: "Obras preliminares y drenaje", monto: "18.420,00 USD", estado: "Verificado", clase: "verificado" },
      { ref: "VAL-03", concepto: "Valuación en revisión de obra", monto: "12.140,50 USD", estado: "Atípico", clase: "atipico" },
      { ref: "REAJ-BCV", concepto: "Índice de asfalto e insumos BCV", monto: "+3,18 %", estado: "Verificado", clase: "verificado" },
    ],
  },
  cantera: {
    titulo: "CANTERA Y ÁRIDOS · Balance de masa y costo horario",
    resumen: "Rendimiento de trituración primaria/secundaria y derivación exacta por m³.",
    kpiIzqRotulo: "Costo horario flota",
    kpiIzqValor: "164,80 USD/h",
    kpiDerRotulo: "Costo agregado",
    kpiDerValor: "14,35 USD/m³",
    filas: [
      { ref: "TRIT-01", concepto: "Trituradora primaria quijada 180 t/h", monto: "78,40 USD/h", estado: "Verificado", clase: "verificado" },
      { ref: "CARG-04", concepto: "Cargador frontal 3,5 m³", monto: "86,40 USD/h", estado: "Verificado", clase: "verificado" },
      { ref: "PROD-M3", concepto: "Piedra picada 3/4\" en patio", monto: "14,35 USD/m³", estado: "Verificado", clase: "verificado" },
    ],
  },
};

function renderizarModulo(clave: string): void {
  const panel = document.getElementById("panel-modulo");
  const datos = MODULOS[clave];
  if (!panel || !datos) return;

  panel.replaceChildren();

  const cabecera = document.createElement("div");
  cabecera.className = "lienzo__cabecera";
  const h = document.createElement("h3");
  h.textContent = datos.titulo;
  const p = document.createElement("p");
  p.textContent = datos.resumen;
  cabecera.append(h, p);

  const kpis = document.createElement("div");
  kpis.className = "lienzo__kpis";
  for (const [rotulo, valor] of [
    [datos.kpiIzqRotulo, datos.kpiIzqValor],
    [datos.kpiDerRotulo, datos.kpiDerValor],
  ]) {
    const caja = document.createElement("div");
    caja.className = "lienzo__kpi";
    const spanR = document.createElement("span");
    spanR.textContent = rotulo;
    const strongV = document.createElement("strong");
    strongV.textContent = valor;
    caja.append(spanR, strongV);
    kpis.append(caja);
  }

  const tabla = document.createElement("table");
  tabla.className = "lienzo__tabla";
  const tbody = document.createElement("tbody");
  for (const fila of datos.filas) {
    const tr = document.createElement("tr");
    const tdRef = document.createElement("td");
    tdRef.className = "mono";
    tdRef.textContent = fila.ref;
    const tdCon = document.createElement("td");
    tdCon.textContent = fila.concepto;
    const tdMon = document.createElement("td");
    tdMon.className = "mono derecha";
    tdMon.textContent = fila.monto;
    const tdEst = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `sev sev--${fila.clase}`;
    badge.textContent = fila.estado;
    tdEst.append(badge);
    tr.append(tdRef, tdCon, tdMon, tdEst);
    tbody.append(tr);
  }
  tabla.append(tbody);

  panel.append(cabecera, kpis, tabla);
}

const botones = document.querySelectorAll<HTMLButtonElement>(".modulo[data-modulo]");
for (const boton of botones) {
  boton.addEventListener("click", () => {
    for (const otro of botones) {
      otro.classList.remove("activo");
      otro.setAttribute("aria-selected", "false");
    }
    boton.classList.add("activo");
    boton.setAttribute("aria-selected", "true");
    const clave = boton.dataset.modulo ?? "forense";
    renderizarModulo(clave);
  });
}

renderizarModulo("forense");
