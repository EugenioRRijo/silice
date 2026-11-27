import { describe, expect, test } from "vitest";

// jsdom no calcula CSS: las reglas se leen del fuente (como shell/AnilloDelTitulo.test.ts) y se midieron en el navegador.
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const leer = (ruta: string) => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/${ruta}`, "utf-8");

function reglaDe(fuente: string, selector: string): string | null {
  const i = fuente.indexOf(`${selector} {`);
  if (i < 0) return null;
  const abre = fuente.indexOf("{", i);
  return fuente.slice(i, fuente.indexOf("}", abre));
}

function bloqueDe(fuente: string, apertura: string): string | null {
  const i = fuente.indexOf(apertura);
  if (i < 0) return null;
  let nivel = 0;
  for (let j = fuente.indexOf("{", i); j < fuente.length; j++) {
    if (fuente[j] === "{") nivel++;
    if (fuente[j] === "}" && --nivel === 0) return fuente.slice(i, j + 1);
  }
  return null;
}

// Pasada en el navegador del cierre de F2: el cuerpo reserva 3 rem arriba para una cabecera fija (la de Carbon de las
// pantallas sin marco, visor.scss); la barra del marco iba en el flujo y quedaba una franja vacía encima. La barra del
// marco también es fija, a lo ancho, y el marco ocupa el alto que queda debajo.
describe("la barra superior del marco ocupa el hueco que reserva el cuerpo", () => {
  test("el cuerpo reserva 3 rem para una cabecera fija", () => {
    expect(reglaDe(leer("visor/visor.scss"), "body")).toMatch(/padding-block-start:\s*3rem/);
  });

  test("la barra del marco es fija arriba, a lo ancho, y el marco mide el alto que queda", () => {
    const marco = leer("marco/marco.scss");
    const barra = reglaDe(marco, "  > .silice-marco-barra");
    expect(barra).toMatch(/position:\s*fixed/);
    expect(barra).toMatch(/inset-block-start:\s*0/);
    expect(barra).toMatch(/inset-inline:\s*0/);
    expect(reglaDe(marco, ".silice-marco")).toMatch(/block-size:\s*calc\(100vh - 3rem\)/);
  });
});

// Recorrido funcional del 2026-11-27 (1366×768): la barra de estado era `sticky` al pie de la ventana y tapaba el final de la
// barra lateral y del contenido; la barra lateral (alto de la ventana, con la lista de obras en una caja que podía encogerse
// a 0) escondía todas las obras. El marco mide el alto de la ventana bajo la barra de arriba: el cuerpo ocupa lo que queda y
// se desplaza por dentro (la lateral y el contenido, cada uno con el suyo) y la barra de estado es su última fila, en el
// flujo, sin tapar nada.
describe("el marco mide el alto de la ventana: cuerpo con su desplazamiento y barra de estado como última fila", () => {
  const marco = () => leer("marco/marco.scss");

  test("el marco es una columna de alto fijo que no desplaza la página", () => {
    const regla = reglaDe(marco(), ".silice-marco") ?? "(no hay regla)";
    expect(regla).toMatch(/display:\s*flex/);
    expect(regla).toMatch(/flex-direction:\s*column/);
    expect(regla).toMatch(/(^|[\s;])block-size:\s*calc\(100vh - 3rem\)/);
    expect(regla).toMatch(/overflow:\s*clip/);
  });

  // Recorrido funcional del 2026-11-27 (reajuste, escenarios, revisar…): lo que Carbon coloca en `position: absolute` (el texto
  // `cds--visually-hidden`, p. ej.) tomaba el documento como bloque contenedor y se salía del contenido que se desplaza: el
  // documento crecía a 1123 px en una ventana de 768, el `focus()` lo desplazaba 56 px y la barra lateral y el contenido
  // quedaban corridos con una franja vacía abajo. El marco, la lateral y el contenido son su propio bloque contenedor, y el
  // marco recorta (`clip`, no `hidden`: `hidden` también se desplaza por programa).
  test("el marco, la barra lateral y el contenido contienen lo absoluto de su interior", () => {
    const fuente = marco();
    expect(reglaDe(fuente, ".silice-marco") ?? "").toMatch(/(^|[\s;])position:\s*relative/);
    expect(reglaDe(fuente, "  > .silice-marco-lateral") ?? "").toMatch(/position:\s*relative/);
    expect(reglaDe(fuente, "\n.silice-contenido") ?? "").toMatch(/position:\s*relative/);
  });

  test("el cuerpo toma el alto que queda y puede encogerse; la lateral y el contenido se desplazan por dentro", () => {
    const fuente = marco();
    const cuerpo = reglaDe(fuente, ".silice-marco__cuerpo") ?? "(no hay regla)";
    expect(cuerpo).toMatch(/flex:\s*1\s+1\s+0/);
    expect(cuerpo).toMatch(/min-block-size:\s*0/);
    const lateral = reglaDe(fuente, "  > .silice-marco-lateral") ?? "(no hay regla)";
    expect(lateral).toMatch(/overflow-y:\s*auto/);
    expect(lateral).not.toMatch(/position:\s*sticky|block-size:\s*calc/);
    const contenido = reglaDe(fuente, "\n.silice-contenido") ?? "(no hay regla)";
    expect(contenido).toMatch(/overflow-y:\s*auto/);
    expect(contenido).toMatch(/min-block-size:\s*0/);
  });

  test("la barra de estado no es sticky ni flota: es la última fila del marco y no se encoge", () => {
    const regla = reglaDe(leer("marco/BarraDeEstado.scss"), ".silice-barra-estado") ?? "(no hay regla)";
    expect(regla).not.toMatch(/position:\s*(sticky|fixed|absolute)/);
    expect(regla).toMatch(/flex:\s*none/);
  });

  test("la cabecera fija de la Hoja se pega al borde del contenido que se desplaza, no a 3 rem de él", () => {
    expect(reglaDe(marco(), "\n.silice-contenido") ?? "").toMatch(/--silice-alto-marco-fijo:\s*0/);
  });

  test("las pantallas de alto completo miden lo que queda sin la barra de estado", () => {
    expect(marco()).toMatch(/--silice-alto-util:\s*calc\(100vh - 3rem - var\(--silice-alto-estado\)\)/);
    for (const ruta of ["paginas/pendientes/Bandeja.scss", "visor/visor.scss"]) {
      expect(leer(ruta)).toMatch(/block-size:\s*var\(--silice-alto-util,\s*calc\(100vh - 3rem\)\)/);
      expect(leer(ruta)).not.toMatch(/block-size:\s*calc\(100vh - 3rem\)/);
    }
  });
});

// La lista de obras de la barra lateral nunca se encoge a cero: con poco alto, la barra se desplaza y la lista conserva un
// mínimo a la vista (en 1366×768 las ocho obras de la siembra desaparecían: `min-block-size: 0` + `overflow-y: auto`).
describe("la lista de obras de la barra lateral no se encoge a cero", () => {
  const lateral = () => leer("marco/BarraLateral.scss");

  test("el árbol de obras tiene un alto mínimo y la caja que lo contiene no lo comprime", () => {
    const arbol = reglaDe(lateral(), ".silice-marco-lateral__arbol") ?? "(no hay regla)";
    expect(arbol).toMatch(/min-block-size:\s*[1-9][\d.]*rem/);
    const obras = reglaDe(lateral(), ".silice-marco-lateral__obras") ?? "(no hay regla)";
    expect(arbol).toMatch(/overflow-y:\s*auto/);
    expect(obras).not.toMatch(/min-block-size:\s*0/);
  });

  test("ni la caja de obras ni la zona de navegación declaran un mínimo de 0 (el automático suma el del árbol)", () => {
    const nav = reglaDe(lateral(), ".silice-marco-lateral__nav") ?? "(no hay regla)";
    expect(nav).not.toMatch(/min-block-size:\s*0/);
  });
});

// Hallazgo 7 del recorrido (01-11-2026, 1366×768, letra Normal): en las pantallas de obra la cuenta se salía por el borde
// derecho (su envoltorio cedía ancho y el botón desbordaba). F6, T6: la barra ya no lleva migas ni tamaño de letra; el
// espacio flexible lo ocupa la carpeta activa. Orden de cesión: primero el buscador (hasta su ícono), luego la carpeta
// activa, que se recorta con puntos suspensivos; la marca y la persona no ceden. La medida real se hace en el navegador;
// aquí se vigilan las reglas.
describe("la barra superior cabe en 1366 px con letra Normal", () => {
  const barra = () => leer("marco/BarraSuperior.scss");
  const regla = (selector: string) => reglaDe(barra(), selector) ?? `(no hay regla ${selector})`;
  const encoger = (texto: string) => Number(/flex:\s*[\d.]+\s+([\d.]+)/.exec(texto)?.[1] ?? "NaN");

  test("la marca y la persona no ceden ancho, y el tamaño de letra ya no tiene reglas en la barra", () => {
    expect(regla(".silice-marco-barra .silice-cuenta")).toMatch(/flex:\s*none/);
    expect(regla(".silice-marco-barra__marca")).toMatch(/flex:\s*none/);
    expect(barra()).not.toMatch(/silice-letra/);
  });

  test("el buscador cede antes que nada y, encogido, deja ver su ícono sin desbordar", () => {
    const buscar = regla(".silice-marco-barra__buscar");
    expect(encoger(buscar)).toBeGreaterThanOrEqual(100);
    expect(buscar).toMatch(/overflow:\s*hidden/);
    expect(buscar).toMatch(/min-inline-size:\s*2\.5rem/);
  });

  test("el contexto ocupa el hueco flexible, cede después del buscador y se recorta con puntos suspensivos", () => {
    const contexto = regla(".silice-marco-barra__contexto");
    expect(contexto).toMatch(/flex:\s*1\s+\d+\s+auto/);
    expect(contexto).toMatch(/min-inline-size:\s*0/);
    expect(contexto).toMatch(/overflow:\s*hidden/);
    expect(contexto).toMatch(/text-overflow:\s*ellipsis/);
    expect(contexto).toMatch(/white-space:\s*nowrap/);
    expect(encoger(regla(".silice-marco-barra__buscar"))).toBeGreaterThan(encoger(contexto));
  });

  test("la carpeta activa cede después del buscador y se recorta con puntos suspensivos", () => {
    const carpeta = regla(".silice-marco-barra__carpeta");
    expect(carpeta).toMatch(/flex:\s*0\s+\d+\s+auto/);
    expect(carpeta).toMatch(/min-inline-size:\s*0/);
    expect(carpeta).toMatch(/overflow:\s*hidden/);
    expect(carpeta).toMatch(/text-overflow:\s*ellipsis/);
    expect(carpeta).toMatch(/white-space:\s*nowrap/);
    expect(encoger(regla(".silice-marco-barra__buscar"))).toBeGreaterThan(encoger(carpeta));
  });

  test("ya no hay reglas de migas", () => {
    expect(barra()).not.toMatch(/__migas|__miga-actual|__separador/);
  });

  test("el enlace de la persona marca la sección actual con el fondo y la raya del acento, no solo con color", () => {
    const actual = regla(".silice-marco-barra .silice-cuenta .silice-cuenta__boton[aria-current=\"page\"]");
    expect(actual).toMatch(/background-color:\s*var\(--cds-background-inverse-hover\)/);
    expect(actual).toMatch(/border-block-end:\s*2px solid var\(--silice-acento\)/);
  });

  test("sin colores nuevos: solo tokens", () => {
    expect(barra()).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(/);
  });
});

// Rediseño F3, Tarea 4c: el color que la empresa elige en Cuenta › Empresa y tema (`GET /v1/tema`, marco/tema.ts) pinta la
// barra superior y la lateral, y el servidor mide esos pares (aplicacion/tema.py, `_PARES`). Los hexadecimales fijos del
// rediseño editorial (--silice-charcoal*, --silice-gold*) no siguen al tema: la barra se quedaba carbón con cualquier marco.
describe("la barra superior y la lateral siguen el tema de la empresa", () => {
  const superior = () => leer("marco/BarraSuperior.scss");
  const lateral = () => leer("marco/BarraLateral.scss");

  test("la barra superior es del color del marco, con la raya de 3 px del acento y el texto sobre el marco", () => {
    const barra = reglaDe(superior(), ".silice-marco-barra") ?? "";
    expect(barra).toMatch(/background-color:\s*var\(--silice-marco\)/);
    expect(barra).toMatch(/border-block-end:\s*3px solid var\(--silice-acento\)/);
    expect(barra).toMatch(/(^|[\s;])color:\s*var\(--cds-text-inverse\)/);
  });

  test("el sello y el modo activo del selector van en el acento con el color del marco (par que mide el servidor)", () => {
    const sello = reglaDe(superior(), ".silice-marco-barra__sello") ?? "";
    expect(sello).toMatch(/background-color:\s*var\(--silice-acento\)/);
    expect(sello).toMatch(/(^|[\s;])color:\s*var\(--silice-marco\)/);
    const activo = superior().slice(superior().indexOf(".silice-marco-barra__modo {"));
    expect(/&\[aria-current="page"\]\s*\{([^}]*)\}/.exec(activo)?.[1]).toMatch(/background-color:\s*var\(--silice-acento\)/);
  });

  test("la lateral pinta su fondo, el hover y la fila activa con el lateral, el lateral activo y la raya del marco", () => {
    const fuente = lateral();
    expect(reglaDe(fuente, ".silice-marco-lateral") ?? "").toMatch(/background-color:\s*var\(--silice-lateral\)/);
    const fila = fuente.slice(fuente.indexOf(".silice-marco-lateral__fila {"));
    expect(/&:hover\s*\{([^}]*)\}/.exec(fila)?.[1]).toMatch(/background-color:\s*var\(--silice-lateral-activo\)/);
    const activa = /&\[aria-current="page"\]\s*\{([^}]*)\}/.exec(fila)?.[1] ?? "";
    expect(activa).toMatch(/background-color:\s*var\(--silice-lateral-activo\)/);
    expect(activa).toMatch(/border-color:\s*var\(--silice-marco\)/);
  });

  test.each(["marco/BarraSuperior.scss", "marco/BarraLateral.scss"])("%s no usa los colores fijos del rediseño editorial", (ruta) => {
    expect(leer(ruta)).not.toMatch(/--silice-(charcoal|gold|rail-hover|ink\b)/);
  });
});

// Plan F6, T3: la barra de espacio parte en renglones con cualquier cantidad de pestañas y cualquier letra, así que no
// puede declarar un ancho fijo (ni en px ni en rem) en ella ni en sus pestañas.
describe("la barra de espacio no declara anchos fijos", () => {
  test("ni width ni inline-size (ni sus mínimos y máximos) con un valor fijo", () => {
    const fuente = leer("marco/BarraDeEspacio.scss");
    expect(fuente.match(/(?:^|[\s;{])(?:min-|max-)?(?:width|inline-size)\s*:\s*[\d.]+(?:px|rem|em)\b/g)).toBeNull();
    expect(fuente).toMatch(/flex-wrap:\s*wrap/);
  });
});

// Recorrido responsive con letra Grande y Muy grande (2026-11-22): la carpeta activa cede el rótulo «Carpeta activa: »
// visualmente sin quitarlo al lector de pantalla; Recorridos guiados no desborda en horizontal; y las pestañas de la
// barra de espacio pueden partir línea solo con letra Grande o Muy grande.
describe("responsive con letra Grande y Muy grande", () => {
  test("en BarraSuperior.scss, por debajo del umbral de grande y muy-grande, el rótulo de carpeta se oculta solo visualmente", () => {
    const fuente = leer("marco/BarraSuperior.scss");
    const bloqueEscalas = bloqueDe(fuente, '@each $escala in ("grande", "muy-grande") {') ?? "";
    expect(bloqueEscalas).toMatch(/@include u\.por-debajo-del-umbral\(\$escala\)/);
    const rotulo = bloqueDe(bloqueEscalas, ".silice-marco-barra__carpeta-rotulo {") ?? "";
    expect(rotulo).toMatch(/position:\s*absolute/);
    expect(rotulo).toMatch(/inline-size:\s*1px/);
    expect(rotulo).toMatch(/block-size:\s*1px/);
    expect(rotulo).toMatch(/overflow:\s*hidden/);
    expect(rotulo).toMatch(/clip-path:\s*inset\(50%\)/);
    expect(rotulo).toMatch(/white-space:\s*nowrap/);
    expect(rotulo).not.toMatch(/display:\s*none/);
    // El rótulo oculto se ancla en la propia etiqueta: sin un contenedor posicionado, el `absolute` lo saca de su caja
    // y el texto de la etiqueta mide 122 px en una caja de 42 (segunda medición responsive, 2026-11-22).
    const carpeta = bloqueDe(fuente, ".silice-marco-barra__carpeta {") ?? "";
    expect(carpeta).toMatch(/position:\s*relative/);
  });

  test("en marco.scss, Recorridos guiados encoge sin desbordar y parte el texto del párrafo y los botones", () => {
    const recorridos = bloqueDe(leer("marco/marco.scss"), ".silice-cuenta-recorridos {") ?? "";
    expect(recorridos).toMatch(/grid-template-columns:\s*minmax\(0,\s*1fr\)/);
    expect(recorridos).toMatch(/max-inline-size:\s*100%/);
    expect(recorridos).toMatch(/min-inline-size:\s*0/);
    expect(recorridos.match(/(?:^|[\s;{])(?:min-|max-)?(?:width|inline-size)\s*:\s*[\d.]+(?:px|rem|em)\b/g)).toBeNull();

    const parrafo = bloqueDe(recorridos, "p {") ?? "";
    expect(parrafo).toMatch(/max-inline-size:\s*100%/);
    expect(parrafo).toMatch(/overflow-wrap:\s*anywhere/);

    const lista = bloqueDe(recorridos, "&__lista {") ?? "";
    expect(lista).toMatch(/display:\s*flex/);
    expect(lista).toMatch(/flex-wrap:\s*wrap/);
    expect(lista).toMatch(/max-inline-size:\s*100%/);
    expect(lista).toMatch(/min-inline-size:\s*0/);

    const boton = bloqueDe(lista, ".cds--btn {") ?? "";
    expect(boton).toMatch(/max-inline-size:\s*100%/);
    expect(boton).toMatch(/min-inline-size:\s*0/);
    expect(boton).toMatch(/white-space:\s*normal/);
    expect(boton).toMatch(/overflow-wrap:\s*anywhere/);
  });

  test("en BarraDeEspacio.scss, las pestañas parten línea solo con letra grande o muy grande (Normal conserva nowrap)", () => {
    const fuente = leer("marco/BarraDeEspacio.scss");
    const base = bloqueDe(fuente, ".silice-barra-espacio__pestana {") ?? "";
    expect(base).toMatch(/white-space:\s*nowrap/);

    const grande = bloqueDe(fuente, "@include u.con-letra-grande {") ?? "";
    const pestanaGrande = bloqueDe(grande, ".silice-barra-espacio__pestana {") ?? "";
    expect(pestanaGrande).toMatch(/white-space:\s*normal/);
    expect(pestanaGrande).toMatch(/max-inline-size:\s*100%/);
    expect(pestanaGrande).toMatch(/min-inline-size:\s*0/);
    expect(pestanaGrande).toMatch(/overflow-wrap:\s*anywhere/);
  });
});

// Tercera medición responsive (2026-11-22): a 768 px con letra Muy grande la barra lateral deja ~290 px al contenido. Las
// rejillas de Administración y de la Ayuda tenían la columna implícita `auto`, que no baja del ancho mínimo de su hijo
// más ancho (listas estructuradas y campos de Carbon), y el botón de la cabecera de la Cuenta quedaba en `max-content`.
describe("la Cuenta cabe a 768 px con letra Muy grande", () => {
  test.each([
    ["paginas/administracion/administracion.scss", ".silice-adm {"],
    ["paginas/administracion/administracion.scss", ".silice-adm__capa {"],
    ["paginas/administracion/administracion.scss", ".silice-adm__bloque {"],
    ["comun/ayuda/ayuda.scss", ".silice-ayuda {"],
    // La base de toda página: sin esto cualquier hijo ancho (una lista de Carbon, un campo) estira la página entera.
    ["comun/comun.scss", ".silice-pagina {"],
    ["paginas/administracion/administracion.scss", ".silice-adm__seccion {"],
  ])("%s %s: la columna de la rejilla puede encoger", (archivo, apertura) => {
    const regla = bloqueDe(leer(archivo), apertura) ?? "";
    expect(regla).toMatch(/grid-template-columns:\s*minmax\(0,\s*1fr\)/);
  });

  test("el botón de la cabecera de la Cuenta parte línea en vez de salirse", () => {
    const regla = bloqueDe(leer("marco/marco.scss"), ".silice-cuenta-cabecera .cds--btn {") ?? "";
    expect(regla).toMatch(/max-inline-size:\s*100%/);
    expect(regla).toMatch(/white-space:\s*normal/);
  });
});

// Cuarta medición (2026-11-22): con letra grande y la barra lateral abierta en una tablet, los componentes de Carbon con
// ancho propio (avisos de 18 rem, botones en `max-content`, tablas y listas estructuradas) se salían de la página.
describe("componentes de Carbon dentro de una página con letra grande", () => {
  const marco = leer("marco/marco.scss");
  const bloque = bloqueDe(marco, "@include u.con-letra-grande {") ?? "";

  test("marco.scss usa los umbrales y tiene un bloque para letra grande", () => {
    expect(marco).toMatch(/@use "umbrales" as u;/);
    expect(bloque).toContain(".silice-pagina");
  });

  test("avisos y botones no pasan del ancho de la página", () => {
    expect(bloque).toMatch(/\.cds--inline-notification[^{]*\{[^}]*min-inline-size:\s*0/);
    expect(bloque).toMatch(/\.cds--btn[^{]*\{[^}]*max-inline-size:\s*100%[^}]*white-space:\s*normal/);
  });

  test("las tablas se desplazan por dentro y las listas estructuradas reparten su ancho", () => {
    expect(bloque).toMatch(/\.cds--data-table-content[^{]*\{[^}]*overflow-x:\s*auto/);
    expect(bloque).toMatch(/\.cds--structured-list[^{-]*\{[^}]*table-layout:\s*fixed/);
  });

  test("los fieldset encogen y las palabras largas (rutas, nombres de archivo) parten línea", () => {
    expect(bloque).toMatch(/fieldset[^{]*\{[^}]*min-inline-size:\s*0/);
    expect(bloque).toMatch(/overflow-wrap:\s*anywhere/);
    // La declaración va en la propia página, antes de las reglas anidadas.
    const pagina = bloqueDe(bloque, ".silice-pagina {") ?? "";
    expect(pagina.slice(0, pagina.indexOf("fieldset"))).toMatch(/overflow-wrap:\s*anywhere/);
    // Las celdas de lista estructurada con `--nowrap` de Carbon también parten línea («Base de la carpeta abierta»).
    expect(bloque).toMatch(/\.cds--structured-list-content--nowrap[^{]*\{[^}]*white-space:\s*normal/);
  });
});

