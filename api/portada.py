"""Portada independiente de Sílice servida en `GET /` (HTML + CSS autocontenido, Carbon g10).

Cero guiones en línea (`script-src 'self'`), cero URLs externas (`http://` o `https://`, RNF-08) y
esquinas rectas (`border-radius: 0`) con divisores de `1px solid #e0e0e0`.
"""

from __future__ import annotations

PORTADA_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sílice — Ingeniería de Costos y Auditoría APU</title>
  <link rel="icon" href="/app/silice.svg" type="image/svg+xml">
  <style>
    :root {
      --cds-bg: #f4f4f4;
      --cds-layer-01: #ffffff;
      --cds-layer-lateral: #f7f3f2;
      --cds-marco: #393939;
      --cds-marco-deep: #262626;
      --cds-acento: #fddc69;
      --cds-text-primary: #161616;
      --cds-text-secondary: #525252;
      --cds-text-inverse: #ffffff;
      --cds-border-subtle: #e0e0e0;
      --cds-border-strong: #8d8d8d;
      --sev-critico: #da1e28;
      --sev-atipico: #8a3ffc;
      --sev-verificado: #24a148;
      --sev-aviso-bg: #fcf4d6;
      --sev-aviso-borde: #b28600;
      --font-sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
      --font-mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    *, *::before, *::after {
      box-sizing: border-box;
      border-radius: 0;
    }
    html {
      font-size: 100%;
      color-scheme: light;
    }
    body {
      margin: 0;
      background-color: var(--cds-bg);
      color: var(--cds-text-primary);
      font-family: var(--font-sans);
      line-height: 1.5;
    }
    .barra {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      min-block-size: 3rem;
      padding: 0 1.5rem;
      background-color: var(--cds-marco);
      color: var(--cds-text-inverse);
      border-block-end: 3px solid var(--cds-acento);
    }
    .barra__marca {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      color: inherit;
      text-decoration: none;
    }
    .barra__monograma {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      inline-size: 1.75rem;
      block-size: 1.75rem;
      background-color: var(--cds-acento);
      color: #161616;
      font-family: var(--font-mono);
      font-weight: 700;
      font-size: 0.9375rem;
    }
    .barra__nombre {
      font-weight: 600;
      font-size: 1rem;
      letter-spacing: 0.01em;
    }
    .barra__subtitulo {
      color: #c6c6c6;
      font-size: 0.8125rem;
      padding-inline-start: 0.75rem;
      border-inline-start: 1px solid #525252;
    }
    .cta {
      display: inline-flex;
      align-items: center;
      justify-content: space-between;
      gap: 1.5rem;
      padding: 0.75rem 1.25rem;
      background-color: var(--cds-marco);
      color: var(--cds-text-inverse);
      text-decoration: none;
      font-weight: 600;
      font-size: 0.875rem;
      border: 1px solid var(--cds-marco);
    }
    .cta:hover {
      background-color: var(--cds-marco-deep);
    }
    .cta:focus-visible {
      outline: 2px solid #0f62fe;
      outline-offset: 2px;
    }
    .cta--barra {
      padding: 0.5rem 1rem;
      background-color: var(--cds-acento);
      color: #161616;
      border-color: var(--cds-acento);
    }
    .cta--barra:hover {
      background-color: #f1c21b;
    }
    .cta--secundario {
      background-color: var(--cds-layer-01);
      color: var(--cds-text-primary);
      border-color: var(--cds-marco);
    }
    .cta--secundario:hover {
      background-color: #e5e5e5;
    }
    .hero__acciones {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
    }
    .descarga {
      background-color: var(--cds-layer-01);
      border: 1px solid var(--cds-border-subtle);
      border-inline-start: 4px solid var(--cds-acento);
      padding: 1.75rem 2rem;
      display: grid;
      gap: 1.25rem;
    }
    .descarga__rejilla {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
      gap: 1rem;
    }
    .descarga__caja {
      border: 1px solid var(--cds-border-subtle);
      background-color: var(--cds-bg);
      padding: 1.25rem;
      display: grid;
      align-content: start;
      gap: 0.75rem;
    }
    .descarga__caja--prueba {
      background-color: var(--cds-layer-lateral);
    }
    .descarga__titulo {
      margin: 0;
      font-size: 1rem;
      font-weight: 600;
    }
    .descarga__texto {
      margin: 0;
      font-size: 0.875rem;
      color: var(--cds-text-secondary);
    }
    .descarga__meta {
      margin: 0;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--cds-text-primary);
    }
    .contenedor {
      max-inline-size: 84rem;
      margin: 0 auto;
      padding: 2rem 1.5rem 3rem;
      display: grid;
      gap: 2rem;
    }
    .hero {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 26rem), 1fr));
      border: 1px solid var(--cds-border-subtle);
      background-color: var(--cds-bg);
    }
    .hero__izquierda {
      padding: 2.25rem 2rem;
      display: grid;
      align-content: start;
      gap: 1.25rem;
      border-inline-end: 1px solid var(--cds-border-subtle);
    }
    .etiqueta-tecnica {
      margin: 0;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--cds-text-secondary);
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .hero__titulo {
      margin: 0;
      font-size: 2.125rem;
      line-height: 1.2;
      font-weight: 600;
      color: var(--cds-text-primary);
    }
    .hero__resumen {
      margin: 0;
      color: var(--cds-text-secondary);
      font-size: 1rem;
      max-inline-size: 62ch;
    }
    .hero__acciones {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 1rem;
      padding-block-start: 0.25rem;
    }
    .garantias {
      margin: 0.5rem 0 0;
      padding: 1rem 0 0;
      list-style: none;
      border-block-start: 1px solid var(--cds-border-subtle);
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem 1.5rem;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--cds-text-secondary);
    }
    .garantias li::before {
      content: "▪ ";
      color: var(--cds-marco);
    }
    .hero__derecha {
      background-color: var(--cds-layer-01);
      padding: 1.75rem;
      display: grid;
      align-content: start;
      gap: 1rem;
    }
    .forense__cabecera {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      padding-block-end: 0.75rem;
      border-block-end: 1px solid var(--cds-border-subtle);
      font-family: var(--font-mono);
      font-size: 0.75rem;
      font-weight: 600;
    }
    .forense__comparacion {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
      border: 1px solid var(--cds-border-subtle);
    }
    .forense__kpi {
      padding: 0.875rem 1rem;
      border-inline-end: 1px solid var(--cds-border-subtle);
    }
    .forense__kpi:last-child {
      border-inline-end: 0;
    }
    .forense__kpi-rotulo {
      display: block;
      font-size: 0.75rem;
      color: var(--cds-text-secondary);
    }
    .forense__kpi-valor {
      display: block;
      margin-block-start: 0.25rem;
      font-family: var(--font-mono);
      font-size: 1.125rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }
    .forense__kpi-delta {
      display: block;
      margin-block-start: 0.25rem;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--sev-critico);
      font-weight: 600;
    }
    .forense__tabla {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8125rem;
      border: 1px solid var(--cds-border-subtle);
    }
    .forense__tabla th,
    .forense__tabla td {
      padding: 0.5rem 0.75rem;
      border-block-end: 1px solid var(--cds-border-subtle);
      text-align: left;
    }
    .forense__tabla th {
      background-color: var(--cds-bg);
      font-weight: 600;
      font-size: 0.75rem;
    }
    .celda-ref {
      font-family: var(--font-mono);
      font-weight: 600;
    }
    .etiqueta-sev {
      display: inline-block;
      padding: 0.125rem 0.375rem;
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      font-weight: 700;
      border: 1px solid currentColor;
    }
    .etiqueta-sev--critico {
      color: var(--sev-critico);
    }
    .etiqueta-sev--atipico {
      color: var(--sev-atipico);
    }
    .etiqueta-sev--verificado {
      color: var(--sev-verificado);
    }
    .seccion-titulo {
      margin: 0 0 0.75rem;
      font-size: 1.25rem;
      font-weight: 600;
    }
    .metodologias {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr));
      border-block-start: 1px solid var(--cds-border-subtle);
      border-inline-start: 1px solid var(--cds-border-subtle);
      background-color: var(--cds-layer-01);
    }
    .metodologia {
      padding: 1.25rem 1.5rem;
      border-inline-end: 1px solid var(--cds-border-subtle);
      border-block-end: 1px solid var(--cds-border-subtle);
      display: grid;
      align-content: start;
      gap: 0.5rem;
    }
    .metodologia__titulo {
      margin: 0;
      font-family: var(--font-mono);
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--cds-text-primary);
    }
    .metodologia__texto {
      margin: 0;
      font-size: 0.875rem;
      color: var(--cds-text-secondary);
    }
    .gobernanza {
      background-color: var(--cds-layer-lateral);
      border: 1px solid var(--cds-border-subtle);
      padding: 1.75rem 2rem;
      display: grid;
      gap: 1.25rem;
    }
    .gobernanza__roles {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
      gap: 1rem;
    }
    .rol-ficha {
      background-color: var(--cds-layer-01);
      border: 1px solid var(--cds-border-subtle);
      border-inline-start: 4px solid var(--cds-marco);
      padding: 1rem 1.25rem;
      display: grid;
      align-content: start;
      gap: 0.5rem;
    }
    .rol-ficha--master {
      border-inline-start-color: var(--sev-aviso-borde);
      background-color: var(--sev-aviso-bg);
    }
    .rol-ficha__titulo {
      margin: 0;
      font-size: 0.9375rem;
      font-weight: 600;
    }
    .rol-ficha__texto {
      margin: 0;
      font-size: 0.8125rem;
      color: var(--cds-text-secondary);
    }
    .pie {
      background-color: var(--cds-marco);
      color: var(--cds-text-inverse);
      border-block-start: 3px solid var(--cds-acento);
      padding: 1.5rem 2rem;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }
    .pie__texto {
      margin: 0;
      font-size: 0.875rem;
      color: #e0e0e0;
    }
  </style>
</head>
<body>
  <header class="barra" aria-label="Sílice">
    <a class="barra__marca" href="/">
      <span class="barra__monograma" aria-hidden="true">S</span>
      <span class="barra__nombre">Sílice</span>
      <span class="barra__subtitulo">Ingeniería de Costos y Auditoría APU</span>
    </a>
    <a class="cta cta--barra" href="/app/">Iniciar sesión en Sílice →</a>
  </header>

  <main class="contenedor">
    <section class="hero" aria-labelledby="portada-titulo">
      <div class="hero__izquierda">
        <p class="etiqueta-tecnica">
          SISTEMA LOCAL DE ANÁLISIS DE PRECIOS UNITARIOS · ARITMÉTICA EXACTA
        </p>
        <h1 id="portada-titulo" class="hero__titulo">
          Presupuestos de obra verificables, celda por celda.
        </h1>
        <p class="hero__resumen">
          Composición de partidas APU, control de valuaciones y auditoría forense de libros
          Excel sobre la misma aritmética decimal verificable, con coma decimal, punto de
          miles y trazabilidad criptográfica en su equipo.
        </p>
        <div class="hero__acciones">
          <a class="cta" href="#descargar">
            <span>Descargar el sistema Sílice</span>
            <span aria-hidden="true">↓</span>
          </a>
          <a class="cta cta--secundario" href="/app/">
            <span>Iniciar sesión en Sílice</span>
            <span aria-hidden="true">→</span>
          </a>
        </div>
        <ul class="garantias" aria-label="Garantías técnicas de la instalación">
          <li>Cálculo exacto en Decimal (sin float)</li>
          <li>Bases SQLite locales por carpeta</li>
          <li>Cero telemetría externa</li>
        </ul>
      </div>

      <div class="hero__derecha" aria-label="Vista esquemática de inspección forense">
        <div class="forense__cabecera">
          <span>HOJA: PLAN DE PAGOS · Inspección forense</span>
          <span>ES-VE · Decimal exacto</span>
        </div>
        <div class="forense__comparacion">
          <div class="forense__kpi">
            <span class="forense__kpi-rotulo">Total declarado en libro</span>
            <span class="forense__kpi-valor">1.740,89 USD</span>
            <span class="forense__kpi-delta">▲ +154,28 USD (+9,72 %) desfavorable</span>
          </div>
          <div class="forense__kpi">
            <span class="forense__kpi-rotulo">Total recalculado según Sílice</span>
            <span class="forense__kpi-valor">1.586,61 USD</span>
          </div>
        </div>
        <table class="forense__tabla" aria-label="Muestra de hallazgos forenses">
          <thead>
            <tr>
              <th>Celda</th>
              <th>Severidad</th>
              <th>Verificación libro contra Sílice</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="celda-ref">PRESUPUESTO!F12</td>
              <td><span class="etiqueta-sev etiqueta-sev--critico">[CRÍTICO]</span></td>
              <td>
                Fórmula truncada o cifra quemada distinta al APU recalculado (regla L3).
              </td>
            </tr>
            <tr>
              <td class="celda-ref">VALUACIONES!J48</td>
              <td><span class="etiqueta-sev etiqueta-sev--atipico">[ATÍPICO]</span></td>
              <td>
                Rendimiento o precio unitario fuera de banda histórica del catálogo.
              </td>
            </tr>
            <tr>
              <td class="celda-ref">COVENIN!C104</td>
              <td><span class="etiqueta-sev etiqueta-sev--verificado">[VERIFICADO]</span></td>
              <td>
                Rendimiento, FCAS y costo directo coinciden al céntimo con el núcleo.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section aria-labelledby="metodologias-titulo">
      <h2 id="metodologias-titulo" class="seccion-titulo">
        Arquitectura y metodologías de verificación
      </h2>
      <div class="metodologias">
        <article class="metodologia">
          <h3 class="metodologia__titulo">01 / Núcleo APU Multidominio</h3>
          <p class="metodologia__texto">
            Composición de materiales, equipos (COP/depreciación), mano de obra con FCAS,
            desperdicio y costos indirectos en edificación, vialidad, infraestructura e
            industria.
          </p>
        </article>
        <article class="metodologia">
          <h3 class="metodologia__titulo">02 / Auditoría Forense Excel L1–L7</h3>
          <p class="metodologia__texto">
            Inspección dual de fórmulas y valores almacenados en hojas .xlsx para detectar
            celdas quemadas, omisiones de costo directo y desviaciones aritméticas sin
            alterar la evidencia.
          </p>
        </article>
        <article class="metodologia">
          <h3 class="metodologia__titulo">03 / Control de Obra y Valor Ganado IBCS</h3>
          <p class="metodologia__texto">
            Seguimiento de línea base contractual, valuaciones, curvas PV/EV/AC y
            reproyección con semántica visual IBCS de variación favorable y desfavorable.
          </p>
        </article>
        <article class="metodologia">
          <h3 class="metodologia__titulo">04 / Moneda, Índices BCV y Riesgo ML</h3>
          <p class="metodologia__texto">
            Carteras separadas por moneda sin mezclar Bs con USD, fórmulas polinómicas de
            escalatoria con series del BCV y detección de precios atípicos.
          </p>
        </article>
        <article class="metodologia">
          <h3 class="metodologia__titulo">05 / Producción de Cantera y Áridos</h3>
          <p class="metodologia__texto">
            Costeo por período de planta y maquinaria pesada, balance de recetas de
            trituración, control de existencias y publicación trazable del costo por
            tonelada o metro cúbico.
          </p>
        </article>
        <article class="metodologia">
          <h3 class="metodologia__titulo">06 / Gobernanza Local SHA-256 y Respaldos</h3>
          <p class="metodologia__texto">
            Cadena de sellos criptográficos por versión de presupuesto, paquetes firmados
            entre empresas y copias de seguridad atómicas de las bases SQLite locales.
          </p>
        </article>
      </div>
    </section>

    <section class="gobernanza" aria-labelledby="gobernanza-titulo">
      <div>
        <p class="etiqueta-tecnica">CONTROL DE ACCESO LOCAL · SEPARACIÓN DE FUNCIONES</p>
        <h2 id="gobernanza-titulo" class="seccion-titulo">
          Gobernanza por roles y cuentas de la instalación
        </h2>
      </div>
      <div class="gobernanza__roles">
        <article class="rol-ficha rol-ficha--master">
          <h3 class="rol-ficha__titulo">Administrador Master</h3>
          <p class="rol-ficha__texto">
            Gobierna el nodo local: reclama la instalación con el código de 20 caracteres,
            crea las cuentas del equipo, asigna cualquier combinación de roles
            (<strong>Arma</strong>, <strong>Revisa</strong>, <strong>Administrador</strong>),
            gestiona carpetas de datos y restablece contraseñas temporales.
          </p>
        </article>
        <article class="rol-ficha">
          <h3 class="rol-ficha__titulo">Rol Arma</h3>
          <p class="rol-ficha__texto">
            Elabora presupuestos y análisis de precios unitarios, importa cómputos o planos,
            registra cotizaciones de estudio de mercado, sella versiones y lleva el control
            de valuaciones de la obra.
          </p>
        </article>
        <article class="rol-ficha">
          <h3 class="rol-ficha__titulo">Rol Revisa</h3>
          <p class="rol-ficha__texto">
            Ejecuta la auditoría forense de libros Excel y paquetes recibidos, inspecciona
            hallazgos celda por celda en solo lectura y emite dictámenes de aprobación o
            devolución con huella verificable.
          </p>
        </article>
      </div>
    </section>

    <section id="descargar" class="descarga" aria-labelledby="descargar-titulo">
      <div>
        <p class="etiqueta-tecnica">ENTREGA DEL PRODUCTO · ESCRITORIO PROPIO Y PRUEBA WEB</p>
        <h2 id="descargar-titulo" class="seccion-titulo">
          Descargar el sistema Sílice o probar el acceso web
        </h2>
      </div>
      <div class="descarga__rejilla">
        <article class="descarga__caja">
          <h3 class="descarga__titulo">Ambiente de escritorio propio</h3>
          <p class="descarga__texto">
            Ejecución nativa autocontenida en Windows sin navegador externo: servidor local
            aislado, base SQLite por carpeta y verificación SHA-256 en su equipo.
          </p>
          <p class="descarga__meta">Paquete: Sílice Desktop · Windows x64 · Enclave local</p>
          <div>
            <a class="cta" href="/app/">
              <span>Abrir instalador / consola local</span>
              <span aria-hidden="true">→</span>
            </a>
          </div>
        </article>
        <article class="descarga__caja descarga__caja--prueba">
          <h3 class="descarga__titulo">Ambiente de prueba web (/app/)</h3>
          <p class="descarga__texto">
            Entorno web de validación para probar el inicio de sesión jerárquico (Usuario
            Arma/Revisa y Administrador Master) antes del empaquetado final de escritorio.
          </p>
          <p class="descarga__meta">Ruta: /app/ · Acceso de prueba en servidor local</p>
          <div>
            <a class="cta cta--secundario" href="/app/">
              <span>Probar inicio de sesión web</span>
              <span aria-hidden="true">→</span>
            </a>
          </div>
        </article>
      </div>
    </section>

    <footer class="pie">
      <p class="pie__texto">
        Sílice · Ejecución local sin conexión externa obligatoria · Acceda con su cuenta de
        usuario o como Administrador Master.
      </p>
      <a class="cta cta--barra" href="/app/">Entrar a la aplicación (/app/) →</a>
    </footer>
  </main>
</body>
</html>
"""
