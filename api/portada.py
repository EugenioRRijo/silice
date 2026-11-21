"""Portada independiente de Sílice servida en `GET /` (HTML5 + CSS3 autocontenido).

Cero guiones en línea (`script-src 'self'`), cero URLs externas (`http://` o `https://`, RNF-08),
esquinas rectas (`border-radius: 0`) y retícula editorial limpia sobre IBM Carbon g10.
"""

from __future__ import annotations

PORTADA_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sílice · Ingeniería de costos y auditoría APU</title>
  <link rel="icon" href="/app/silice.svg" type="image/svg+xml">
  <style>
    :root {
      --bg: #f4f4f4;
      --surface: #ffffff;
      --surface-warm: #f7f3f2;
      --ink: #161616;
      --ink-muted: #525252;
      --marco: #393939;
      --marco-deep: #262626;
      --acento: #fddc69;
      --acento-hover: #f1c21b;
      --focus: #0f62fe;
      --line: #e0e0e0;
      --line-strong: #c6c6c6;
      --critico: #da1e28;
      --atipico: #8a3ffc;
      --verificado: #24a148;
      --font-sans: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --font-mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
    }
    *, *::before, *::after {
      box-sizing: border-box;
      border-radius: 0;
    }
    html {
      font-size: 100%;
      color-scheme: light;
      scroll-behavior: smooth;
    }
    body {
      margin: 0;
      background-color: var(--bg);
      color: var(--ink);
      font-family: var(--font-sans);
      line-height: 1.55;
      -webkit-font-smoothing: antialiased;
    }
    ::selection {
      background: var(--acento);
      color: var(--ink);
    }
    a, button {
      transition:
        background-color 150ms var(--ease-out),
        color 150ms var(--ease-out),
        border-color 150ms var(--ease-out),
        transform 120ms var(--ease-out);
    }
    a:focus-visible, button:focus-visible {
      outline: 2px solid var(--focus);
      outline-offset: 2px;
    }
    .barra {
      position: sticky;
      top: 0;
      z-index: 20;
      background-color: var(--marco);
      color: #ffffff;
      border-block-end: 3px solid var(--acento);
    }
    .barra__interior {
      max-inline-size: 80rem;
      margin: 0 auto;
      padding: 0 1.5rem;
      min-block-size: 3.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1.5rem;
    }
    .marca {
      display: inline-flex;
      align-items: center;
      gap: 0.75rem;
      color: #ffffff;
      text-decoration: none;
      font-weight: 600;
      font-size: 1rem;
      letter-spacing: -0.01em;
    }
    .marca__sello {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      inline-size: 1.875rem;
      block-size: 1.875rem;
      background-color: var(--acento);
      color: var(--ink);
      font-family: var(--font-mono);
      font-weight: 700;
      font-size: 0.9375rem;
    }
    .nav {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }
    .nav__enlace {
      color: #e0e0e0;
      text-decoration: none;
      font-size: 0.875rem;
      padding: 0.5rem 0;
    }
    .nav__enlace:hover {
      color: #ffffff;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.625rem;
      min-block-size: 2.75rem;
      padding: 0.625rem 1.25rem;
      font-size: 0.875rem;
      font-weight: 600;
      text-decoration: none;
      border: 1px solid transparent;
      cursor: pointer;
    }
    .btn:active {
      transform: scale(0.98);
    }
    .btn--acento {
      background-color: var(--acento);
      color: var(--ink);
      border-color: var(--acento);
      min-block-size: 2.25rem;
      padding: 0.375rem 1rem;
    }
    .btn--acento:hover {
      background-color: var(--acento-hover);
    }
    .btn--primario {
      background-color: var(--ink);
      color: #ffffff;
      border-color: var(--ink);
    }
    .btn--primario:hover {
      background-color: var(--marco);
    }
    .btn--secundario {
      background-color: var(--surface);
      color: var(--ink);
      border-color: var(--line-strong);
    }
    .btn--secundario:hover {
      background-color: #ebebeb;
      border-color: var(--ink);
    }
    .lienzo {
      max-inline-size: 80rem;
      margin: 0 auto;
      padding: clamp(2rem, 4vw, 3.5rem) 1.5rem 4rem;
      display: grid;
      gap: clamp(3rem, 5vw, 4.5rem);
    }
    .hero {
      background-color: var(--surface);
      border: 1px solid var(--line);
      box-shadow: 0 12px 32px rgba(22, 22, 22, 0.04);
      display: grid;
      grid-template-columns: minmax(0, 1.12fr) minmax(0, 0.88fr);
    }
    @media (max-width: 56rem) {
      .hero {
        grid-template-columns: 1fr;
      }
      .nav__enlace {
        display: none;
      }
    }
    .hero__principal {
      padding: clamp(2rem, 4vw, 3.5rem);
      display: grid;
      align-content: space-between;
      gap: 2rem;
      border-inline-end: 1px solid var(--line);
    }
    @media (max-width: 56rem) {
      .hero__principal {
        border-inline-end: 0;
        border-block-end: 1px solid var(--line);
      }
    }
    .hero__cabecera {
      display: grid;
      gap: 1.25rem;
    }
    .hero__titulo {
      margin: 0;
      font-size: clamp(2rem, 3.6vw, 3rem);
      font-weight: 600;
      line-height: 1.08;
      letter-spacing: -0.03em;
      max-inline-size: 18ch;
      text-wrap: balance;
    }
    .hero__resumen {
      margin: 0;
      font-size: 1rem;
      color: var(--ink-muted);
      max-inline-size: 56ch;
    }
    .hero__acciones {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
    }
    .hero__hechos {
      margin: 0;
      padding: 1.25rem 0 0;
      list-style: none;
      border-block-start: 1px solid var(--line);
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1rem;
    }
    @media (max-width: 36rem) {
      .hero__hechos {
        grid-template-columns: 1fr;
      }
    }
    .hecho__titulo {
      display: block;
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--ink);
    }
    .hecho__detalle {
      display: block;
      font-size: 0.75rem;
      color: var(--ink-muted);
    }
    .especimen {
      background-color: var(--surface-warm);
      padding: clamp(1.5rem, 3vw, 2.5rem);
      display: grid;
      align-content: center;
    }
    .especimen__marco {
      background-color: var(--surface);
      border: 1px solid var(--line-strong);
      box-shadow: 0 8px 24px rgba(22, 22, 22, 0.06);
    }
    .especimen__barra {
      background-color: var(--marco-deep);
      color: #ffffff;
      padding: 0.625rem 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-family: var(--font-mono);
      font-size: 0.75rem;
    }
    .especimen__cifras {
      display: grid;
      grid-template-columns: 1fr 1fr;
      border-block-end: 1px solid var(--line);
    }
    .cifra {
      padding: 1rem 1.25rem;
      display: grid;
      gap: 0.25rem;
    }
    .cifra:first-child {
      border-inline-end: 1px solid var(--line);
    }
    .cifra__rotulo {
      font-size: 0.75rem;
      color: var(--ink-muted);
    }
    .cifra__valor {
      font-size: 1.375rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      letter-spacing: -0.02em;
    }
    .cifra__delta {
      font-size: 0.75rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }
    .cifra__delta--mal {
      color: var(--critico);
    }
    .cifra__delta--bien {
      color: var(--verificado);
    }
    .hallazgos {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8125rem;
    }
    .hallazgos th {
      text-align: start;
      font-weight: 600;
      color: var(--ink-muted);
      padding: 0.625rem 1rem;
      border-block-end: 1px solid var(--line);
      background-color: var(--bg);
      font-size: 0.75rem;
    }
    .hallazgos td {
      padding: 0.75rem 1rem;
      border-block-end: 1px solid var(--line);
      vertical-align: middle;
    }
    .hallazgos tr:last-child td {
      border-block-end: 0;
    }
    .celda-ref {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--ink);
    }
    .estado-sev {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      font-weight: 600;
      font-size: 0.75rem;
    }
    .punto {
      inline-size: 0.5rem;
      block-size: 0.5rem;
      display: inline-block;
    }
    .punto--critico { background-color: var(--critico); }
    .punto--atipico { background-color: var(--atipico); }
    .punto--verificado { background-color: var(--verificado); }
    .bloque {
      display: grid;
      gap: 1.5rem;
    }
    .bloque__titulo {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 600;
      letter-spacing: -0.02em;
    }
    .bloque__bajada {
      margin: 0.375rem 0 0;
      color: var(--ink-muted);
      max-inline-size: 65ch;
      font-size: 0.9375rem;
    }
    .rejilla-especs {
      background-color: var(--surface);
      border: 1px solid var(--line);
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    @media (max-width: 44rem) {
      .rejilla-especs {
        grid-template-columns: 1fr;
      }
    }
    .espec {
      padding: 1.5rem 1.75rem;
      border-block-end: 1px solid var(--line);
      border-inline-end: 1px solid var(--line);
      display: grid;
      gap: 0.375rem;
    }
    .espec:nth-child(2n) {
      border-inline-end: 0;
    }
    .espec:nth-last-child(-n+2) {
      border-block-end: 0;
    }
    @media (max-width: 44rem) {
      .espec {
        border-inline-end: 0;
      }
      .espec:nth-last-child(-n+2) {
        border-block-end: 1px solid var(--line);
      }
      .espec:last-child {
        border-block-end: 0;
      }
    }
    .espec__titulo {
      margin: 0;
      font-size: 1rem;
      font-weight: 600;
    }
    .espec__texto {
      margin: 0;
      font-size: 0.875rem;
      color: var(--ink-muted);
    }
    .entrega {
      background-color: var(--surface);
      border: 1px solid var(--line);
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    @media (max-width: 48rem) {
      .entrega {
        grid-template-columns: 1fr;
      }
    }
    .entrega__columna {
      padding: 2rem;
      display: grid;
      align-content: space-between;
      gap: 1.5rem;
    }
    .entrega__columna--escritorio {
      border-inline-end: 1px solid var(--line);
    }
    .entrega__columna--web {
      background-color: var(--surface-warm);
    }
    @media (max-width: 48rem) {
      .entrega__columna--escritorio {
        border-inline-end: 0;
        border-block-end: 1px solid var(--line);
      }
    }
    .entrega__titulo {
      margin: 0;
      font-size: 1.125rem;
      font-weight: 600;
    }
    .entrega__texto {
      margin: 0.5rem 0 0;
      font-size: 0.875rem;
      color: var(--ink-muted);
    }
    .entrega__datos {
      margin: 1rem 0 0;
      padding: 0.75rem 0 0;
      border-block-start: 1px solid var(--line);
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--ink);
    }
    .roles {
      background-color: var(--surface);
      border: 1px solid var(--line);
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    @media (max-width: 52rem) {
      .roles {
        grid-template-columns: 1fr;
      }
    }
    .rol {
      padding: 1.5rem;
      border-inline-end: 1px solid var(--line);
      display: grid;
      align-content: start;
      gap: 0.5rem;
    }
    .rol:last-child {
      border-inline-end: 0;
    }
    @media (max-width: 52rem) {
      .rol {
        border-inline-end: 0;
        border-block-end: 1px solid var(--line);
      }
      .rol:last-child {
        border-block-end: 0;
      }
    }
    .rol__titulo {
      margin: 0;
      font-size: 0.9375rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .rol__texto {
      margin: 0;
      font-size: 0.875rem;
      color: var(--ink-muted);
    }
    .pie {
      background-color: var(--marco-deep);
      color: #c6c6c6;
      border-block-start: 3px solid var(--acento);
    }
    .pie__interior {
      max-inline-size: 80rem;
      margin: 0 auto;
      padding: 1.5rem;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      font-size: 0.875rem;
    }
    .pie__texto {
      margin: 0;
    }
    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; }
      a, button { transition: none; }
      .btn:active { transform: none; }
    }
  </style>
</head>
<body>
  <header class="barra" aria-label="Sílice">
    <div class="barra__interior">
      <a class="marca" href="/">
        <span class="marca__sello" aria-hidden="true">S</span>
        <span>Sílice</span>
      </a>
      <nav class="nav" aria-label="Navegación de portada">
        <a class="nav__enlace" href="#capacidades">Capacidades</a>
        <a class="nav__enlace" href="#roles">Roles</a>
        <a class="nav__enlace" href="#descargar">Escritorio</a>
        <a class="btn btn--acento" href="/app/">Iniciar sesión en Sílice</a>
      </nav>
    </div>
  </header>

  <main class="lienzo">
    <section class="hero" aria-labelledby="portada-titulo">
      <div class="hero__principal">
        <div class="hero__cabecera">
          <h1 id="portada-titulo" class="hero__titulo">
            Presupuestos de obra verificables, celda por celda.
          </h1>
          <p class="hero__resumen">
            Elabora análisis de precios unitarios, controla valuaciones y audita libros Excel con
            aritmética decimal exacta en tu equipo. Cada cifra conserva coma decimal, punto de
            miles y respaldo criptográfico local.
          </p>
          <div class="hero__acciones">
            <a class="btn btn--primario" href="#descargar">
              <span>Descargar el sistema Sílice</span>
              <span aria-hidden="true">↓</span>
            </a>
            <a class="btn btn--secundario" href="/app/">
              <span>Probar inicio de sesión web</span>
              <span aria-hidden="true">→</span>
            </a>
          </div>
        </div>
        <ul class="hero__hechos" aria-label="Propiedades técnicas de la instalación">
          <li>
            <span class="hecho__titulo">Decimal exacto</span>
            <span class="hecho__detalle">Sin errores de punto flotante</span>
          </li>
          <li>
            <span class="hecho__titulo">SQLite local</span>
            <span class="hecho__detalle">Aislamiento físico por carpeta</span>
          </li>
          <li>
            <span class="hecho__titulo">Sin telemetría</span>
            <span class="hecho__detalle">Operación 100 % en tu equipo</span>
          </li>
        </ul>
      </div>

      <div class="especimen" aria-label="Vista esquemática de inspección forense">
        <div class="especimen__marco">
          <div class="especimen__barra">
            <span>PLAN DE PAGOS · Inspección forense</span>
            <span>es-VE</span>
          </div>
          <div class="especimen__cifras">
            <div class="cifra">
              <span class="cifra__rotulo">Declarado en libro</span>
              <span class="cifra__valor">1.740,89 USD</span>
              <span class="cifra__delta cifra__delta--mal">+154,28 USD (+9,72 %)</span>
            </div>
            <div class="cifra">
              <span class="cifra__rotulo">Recalculado Sílice</span>
              <span class="cifra__valor">1.586,61 USD</span>
              <span class="cifra__delta cifra__delta--bien">Base verificada</span>
            </div>
          </div>
          <table class="hallazgos" aria-label="Muestra de hallazgos forenses">
            <thead>
              <tr>
                <th>Celda</th>
                <th>Diagnóstico</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="celda-ref">PRESUPUESTO!F12</td>
                <td>Valor fijo sobre fórmula de total</td>
                <td>
                  <span class="estado-sev"><span class="punto punto--critico"></span>Crítico</span>
                </td>
              </tr>
              <tr>
                <td class="celda-ref">VALUACIONES!J48</td>
                <td>Variación de precio atípica</td>
                <td>
                  <span class="estado-sev"><span class="punto punto--atipico"></span>Atípico</span>
                </td>
              </tr>
              <tr>
                <td class="celda-ref">COVENIN!C104</td>
                <td>Matriz APU consistente</td>
                <td>
                  <span class="estado-sev">
                    <span class="punto punto--verificado"></span>Verificado
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section id="capacidades" class="bloque" aria-labelledby="capacidades-titulo">
      <div>
        <h2 id="capacidades-titulo" class="bloque__titulo">Qué resuelve el sistema</h2>
        <p class="bloque__bajada">
          Seis módulos integrados sobre una sola base matemática y probatoria.
        </p>
      </div>
      <div class="rejilla-especs">
        <article class="espec">
          <h3 class="espec__titulo">Núcleo APU multidominio</h3>
          <p class="espec__texto">
            Composición de materiales, equipos y mano de obra con FCAS en aritmética decimal
            inmutable y redondeo oficial a dos decimales.
          </p>
        </article>
        <article class="espec">
          <h3 class="espec__titulo">Auditoría forense Excel</h3>
          <p class="espec__texto">
            Extracción dual de fórmulas y valores con inspección visual de libro original, detección
            de celdas quemadas y parches delta sin alterar el archivo fuente.
          </p>
        </article>
        <article class="espec">
          <h3 class="espec__titulo">Control de obra y valor ganado</h3>
          <p class="espec__texto">
            Seguimiento por frentes, valuaciones acumuladas, proyecciones de costo y punto de
            equilibrio con semántica tabular clara.
          </p>
        </article>
        <article class="espec">
          <h3 class="espec__titulo">Moneda, índices BCV y riesgo</h3>
          <p class="espec__texto">
            Estudios de mercado en USD y Bs con tasas diarias, series viales de asfalto y gasoil,
            y detección de variaciones atípicas en precios.
          </p>
        </article>
        <article class="espec">
          <h3 class="espec__titulo">Producción de cantera y áridos</h3>
          <p class="espec__texto">
            Costos horarios de maquinaria, balance de masa en planta de trituración, receta
            asfáltica y trazabilidad por tonelada o metro cúbico.
          </p>
        </article>
        <article class="espec">
          <h3 class="espec__titulo">Gobernanza local y respaldos</h3>
          <p class="espec__texto">
            Cadena de sellos SHA-256 por versión de presupuesto, paquetes firmados entre empresas y
            copias atómicas de las bases SQLite locales.
          </p>
        </article>
      </div>
    </section>

    <section id="descargar" class="bloque" aria-labelledby="descargar-titulo">
      <div>
        <h2 id="descargar-titulo" class="bloque__titulo">
          Descargar el sistema Sílice o probar la versión web
        </h2>
        <p class="bloque__bajada">
          El acceso web actual funciona como ambiente de prueba antes de cerrar el instalador de
          escritorio propio.
        </p>
      </div>
      <div class="entrega">
        <article class="entrega__columna entrega__columna--escritorio">
          <div>
            <h3 class="entrega__titulo">Ambiente de escritorio propio</h3>
            <p class="entrega__texto">
              Aplicación nativa autocontenida para Windows sin navegador externo: servidor local
              aislado, bases SQLite por carpeta y verificación criptográfica en tu equipo.
            </p>
            <p class="entrega__datos">Paquete: Sílice Desktop · Windows x64 · Instalación local</p>
          </div>
          <div>
            <a class="btn btn--primario" href="/app/">
              <span>Abrir instalador / consola local</span>
              <span aria-hidden="true">→</span>
            </a>
          </div>
        </article>
        <article class="entrega__columna entrega__columna--web">
          <div>
            <h3 class="entrega__titulo">Ambiente de prueba web (/app/)</h3>
            <p class="entrega__texto">
              Entorno web de validación para probar el inicio de sesión jerárquico entre Usuario
              (Arma / Revisa) y Administrador Master mientras cerramos el empaquetado de escritorio.
            </p>
            <p class="entrega__datos">Ruta: /app/ · Inicio de sesión de prueba</p>
          </div>
          <div>
            <a class="btn btn--secundario" href="/app/">
              <span>Probar inicio de sesión web</span>
              <span aria-hidden="true">→</span>
            </a>
          </div>
        </article>
      </div>
    </section>

    <section id="roles" class="bloque" aria-labelledby="roles-titulo">
      <div>
        <h2 id="roles-titulo" class="bloque__titulo">Separación de funciones en la instalación</h2>
      </div>
      <div class="roles">
        <article class="rol">
          <h3 class="rol__titulo">
            <span class="punto punto--atipico"></span>Administrador Master
          </h3>
          <p class="rol__texto">
            Reclama la instalación con la llave de 20 caracteres, administra cuentas y combina
            roles, gestiona carpetas y restaura respaldos.
          </p>
        </article>
        <article class="rol">
          <h3 class="rol__titulo"><span class="punto punto--verificado"></span>Rol Arma</h3>
          <p class="rol__texto">
            Elabora presupuestos y partidas APU, importa cómputos, registra cotizaciones de mercado,
            sella versiones y gestiona valuaciones.
          </p>
        </article>
        <article class="rol">
          <h3 class="rol__titulo"><span class="punto punto--critico"></span>Rol Revisa</h3>
          <p class="rol__texto">
            Ejecuta auditorías forenses sobre libros Excel y paquetes recibidos en solo lectura, y
            emite dictámenes aprobados o devueltos.
          </p>
        </article>
      </div>
    </section>
  </main>

  <footer class="pie">
    <div class="pie__interior">
      <p class="pie__texto">
        Sílice · Sistema local de análisis de precios unitarios y auditoría forense.
      </p>
      <a class="btn btn--acento" href="/app/">Entrar al ambiente web (/app/) →</a>
    </div>
  </footer>
</body>
</html>
"""
