"""Medición de controles y carga visual por pantalla en el recorrido con Playwright.

Reúne el detector de controles sin nombre accesible (`CONTROLES_JS`, `sin_nombre`) y la capa
medida de la guardia de interfaz (`docs/especificaciones/2026-11-23-norma-de-interfaz.md`,
«Lo que revisa una persona»): lo que la guardia estática no ve porque solo existe en el
navegador.

R-8 cuenta cuántos controles ve la persona al entrar a la pantalla, sin abrir pliegues ni
diálogos (8 decisiones a la vista por paso, una pregunta de revisión y no un cupo), y comprueba
la primera pantalla: el `h1` y el botón principal dentro de la primera vista a 1366 × 768 con
letra normal. Se cuentan los controles de `main#contenido` (el marco es el mismo en todas las
pantallas), aparte los de tablas y hojas. Un botón propio de un campo de Carbon (abrir una
lista, subir o bajar un número) no es otra decisión, y la entrada de archivo va siempre con su
botón visible. Es un informe para una persona (`carga_<rol>.md`): no bloquea la CI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ALTO = 768
UMBRAL_DE_DECISIONES = 8
ANCHO_DE_CARGA = 1366
LETRA_DE_CARGA = "normal"

# Los controles de la pantalla (botones, enlaces y lo que hace de botón) con su nombre accesible
# aproximado (aria-label, aria-labelledby, el texto, el `alt` de una imagen, `title` o el valor de
# un botón de formulario), si están a la vista y si cuelgan de un `aria-hidden="true"`: axe no
# revisa lo que el árbol de accesibilidad no expone, y este detector tampoco (`sin_nombre`).
CONTROLES_JS = """() => {
  const limpio = t => (t || '').replace(/\\s+/g, ' ').trim();
  const nombre = el => {
    const etiqueta = el.getAttribute('aria-label');
    if (limpio(etiqueta)) return limpio(etiqueta);
    const ids = (el.getAttribute('aria-labelledby') || '').split(/\\s+/).filter(Boolean);
    const de = ids.map(i => {
      const r = document.getElementById(i); return r ? r.textContent : ''; });
    if (limpio(de.join(' '))) return limpio(de.join(' '));
    if (limpio(el.textContent)) return limpio(el.textContent);
    const img = el.querySelector('img[alt], [role="img"][aria-label]');
    if (img && limpio(img.getAttribute('alt') || img.getAttribute('aria-label')))
      return limpio(img.getAttribute('alt') || img.getAttribute('aria-label'));
    if (limpio(el.getAttribute('title'))) return limpio(el.getAttribute('title'));
    if (el.tagName === 'INPUT') return limpio(el.value);
    return '';
  };
  const selector = 'button, a[href], [role="button"], [role="link"], input[type="button"],'
    + ' input[type="submit"]';
  return [...document.querySelectorAll(selector)].map(el => {
    const r = el.getBoundingClientRect();
    return {
      rol: el.getAttribute('role') || (el.tagName === 'A' ? 'link' : 'button'),
      nombre: nombre(el),
      oculto: el.closest('[aria-hidden="true"]') !== null,
      visible: r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden',
      html: el.outerHTML.slice(0, 120),
    };
  });
}"""

CARGA_JS = """() => {
  const raiz = document.querySelector('main#contenido') || document.body;
  const alto = window.innerHeight, ancho = document.documentElement.clientWidth;
  const cerrado = 'details:not([open]), dialog:not([open]), [aria-hidden="true"],'
    + ' .cds--modal:not(.is-visible)';
  const visible = el => { const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'
      && !el.closest(cerrado); };
  const enLaVista = el => { if (!el || !visible(el)) return false;
    const r = el.getBoundingClientRect();
    return r.top >= 0 && r.bottom <= alto + 1 && r.left >= 0 && r.right <= ancho + 1; };
  const controles = [...raiz.querySelectorAll('input, select, textarea, button, [role=combobox]')]
    .filter(el => !(el.tagName === 'INPUT' && ['hidden', 'file'].includes(el.type)))
    .filter(el => !(el.parentElement && el.parentElement.closest('[role=combobox]')))
    .filter(el => !(el.tagName === 'BUTTON' && el.getAttribute('role') !== 'combobox'
      && el.closest('.cds--list-box, .cds--number__controls')))
    .filter(visible);
  const enTablas = controles.filter(el => el.closest('table, [role=grid]')).length;
  const h1 = raiz.querySelector('h1') || document.querySelector('h1');
  const principales = [...raiz.querySelectorAll('.cds--btn--primary')].filter(visible);
  return {
    fuera_de_tablas: controles.length - enTablas, en_tablas: enTablas,
    h1_a_la_vista: enLaVista(h1),
    principal_a_la_vista: principales.length ? enLaVista(principales[0]) : null,
    principales: principales.length,
    principal_texto: principales.length ? principales[0].textContent.trim().slice(0, 40) : null,
  };
}"""


def sin_nombre(controles: list[dict[str, Any]]) -> list[str]:
    """Los botones y enlaces a la vista sin nombre accesible. Lo que cuelga de un
    `aria-hidden="true"` (un portal cerrado de Carbon, un icono decorativo) se salta, como axe."""
    return [
        f"{c['rol']} {c['html']}"
        for c in controles
        if c.get("visible") and not c.get("oculto") and not str(c.get("nombre", "")).strip()
    ]


def toca_medir_carga(medir: bool, ancho: int, letra: str) -> bool:
    """La carga se mide una vez por pantalla: a 1366 × 768 y con letra normal, si se pidió."""
    return medir and ancho == ANCHO_DE_CARGA and letra == LETRA_DE_CARGA


def anotar_carga(pagina: Any, fila: dict[str, Any]) -> None:
    """Mide la carga antes de la captura y de axe: lo que ve la persona al entrar."""
    if "carga" in fila and fila["ms_hasta_h1"] is not None:
        fila["carga"] = pagina.evaluate(CARGA_JS)


def veredicto_de_carga(medida: dict[str, Any]) -> str:
    """«falla» si el h1 no se ve o el principal que existe queda fuera de la primera vista;
    «revisar» si los controles fuera de tablas y hojas pasan de 8 (una pregunta para la persona
    que revisa, no un cupo); «bien» en otro caso. La primera pantalla pesa más que la revisión."""
    if not medida.get("h1_a_la_vista") or medida.get("principal_a_la_vista") is False:
        return "falla"
    if int(medida.get("fuera_de_tablas", 0)) > UMBRAL_DE_DECISIONES:
        return "revisar"
    return "bien"


def _si_no(valor: Any) -> str:
    return "no hay" if valor is None else ("sí" if valor else "no")


def informe_de_carga(filas: list[dict[str, Any]]) -> str:
    """Tabla Markdown por pantalla con su veredicto. Entran las filas con la clave «carga»; una
    `None` es una medida pedida que no se pudo tomar y queda como «sin medida». Una pantalla que
    el marco no ofrece al rol lo lleva a otra («Pendientes», «Sin permiso»): lo contado ahí no es
    esa pantalla y no lleva veredicto."""
    cuenta = {"bien": 0, "revisar": 0, "falla": 0, "sin medida": 0, "no ofrecida al rol": 0}
    lineas = [
        "| Pantalla | Controles fuera de tablas | Controles en tablas | h1 a la vista "
        "| Principal a la vista | Veredicto |",
        "|---|---:|---:|---|---|---|",
    ]
    for fila in filas:
        if "carga" not in fila:
            continue
        nombre = f"{fila.get('titulo', fila['id'])} (`{fila['id']}`)"
        medida = fila["carga"]
        sin_veredicto = "no ofrecida al rol" if fila.get("ofrecida") is False else "sin medida"
        if medida is None or sin_veredicto == "no ofrecida al rol":
            cuenta[sin_veredicto] += 1
            lineas.append(f"| {nombre} | — | — | — | — | {sin_veredicto} |")
            continue
        veredicto = veredicto_de_carga(medida)
        cuenta[veredicto] += 1
        lineas.append(
            f"| {nombre} | {medida['fuera_de_tablas']} | {medida['en_tablas']} "
            f"| {_si_no(medida['h1_a_la_vista'])} | {_si_no(medida['principal_a_la_vista'])} "
            f"| {veredicto} |"
        )
    resumen = " · ".join(f"{k}: {v}" for k, v in cuenta.items())
    return "\n".join(
        [
            "# Carga de cada pantalla (capa medida de la guardia de interfaz)",
            "",
            f"Ventana de {ANCHO_DE_CARGA} × {ALTO} con letra {LETRA_DE_CARGA}, al entrar y sin "
            "abrir pliegues ni diálogos. Se cuentan input, select, textarea, button y "
            "`[role=combobox]` visibles en `main#contenido`; los de `table` y `[role=grid]` van "
            f"aparte. «revisar» (más de {UMBRAL_DE_DECISIONES} controles fuera de tablas) es una "
            "pregunta de revisión, no un cupo; «falla» es que el h1 o el botón principal "
            "(`.cds--btn--primary`) quedan fuera de la primera vista. Este informe no bloquea "
            "la CI.",
            "",
            resumen,
            "",
            *lineas,
            "",
        ]
    )


def escribir_informes_de_carga(
    salida: Path, roles: list[str], pantallas: list[dict[str, Any]]
) -> None:
    """Escribe `carga_<rol>.md` por cada rol pedido con las pantallas medidas."""
    for rol in roles:
        informe = informe_de_carga([f for f in pantallas if f["rol"] == rol])
        ruta_informe = salida / f"carga_{rol}.md"
        ruta_informe.write_text(informe, encoding="utf-8")
        print(f"informe de carga: {ruta_informe}")
