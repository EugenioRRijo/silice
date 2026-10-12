"""SEG-3: el informe de auditoria no se interpreta como Markdown (RV-14).

Un nombre de insumo importado puede llegar dentro de la descripcion de un hallazgo (R11, R12...).
Si la pantalla pintara `informe.a_markdown()`, `![x](http://127.0.0.1:9/p)` seria una imagen que
el navegador pediria. El informe se muestra en celdas de tabla (texto plano) y lo que va en
Markdown pasa por `ui.texto_seguro`. Esta prueba mete ese nombre y mira lo que pinta la pantalla.
"""

import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.fixtures.arquitectura import RAIZ

IMAGEN = "![x](http://127.0.0.1:9/p)"


def _pantalla() -> None:
    from decimal import Decimal as D  # noqa: N817

    from core.contracts.verificacion import Hallazgo, Severidad
    from core.verification.informe import InformeAuditoria
    from ui.resultado import mostrar_informe

    hallazgo = Hallazgo(
        "R11",
        Severidad.ADVERTENCIA,
        "El precio de «![x](http://127.0.0.1:9/p) [enlace](http://127.0.0.1:9/q)» esta fuera "
        "de rango",
        D("12.5"),
        ("INS-1",),
    )
    informe = InformeAuditoria(
        "![x](http://127.0.0.1:9/p)",
        (hallazgo,),
        reglas_evaluadas=(("R11", "Precio fuera de rango"),),
    )
    mostrar_informe(informe)


def test_un_nombre_con_markdown_no_se_renderiza_como_imagen_ni_enlace() -> None:
    at = AppTest.from_function(_pantalla, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    # Lo que va como Markdown no trae la imagen ni el enlace sin escapar...
    for m in [*at.markdown, *at.subheader, *at.caption]:
        assert IMAGEN not in m.value
        assert not re.search(r"(?<!\\)\]\(http", m.value), m.value
    # ... y el texto ajeno esta, literal, en una celda de tabla.
    celdas = " ".join(str(v) for d in at.dataframe for v in d.value.to_numpy().ravel())
    assert IMAGEN in celdas
    assert "Precio fuera de rango" in celdas and "R11" in celdas


def test_ninguna_pantalla_pinta_a_markdown_del_informe() -> None:
    """Salvo la de actualizar precios (diferida: su `Presentacion.informe` es un `str`)."""
    infractores = sorted(
        archivo.relative_to(RAIZ).as_posix()
        for archivo in Path(RAIZ / "ui").rglob("*.py")
        if "a_markdown(" in archivo.read_text(encoding="utf-8")
    )
    assert infractores == ["ui/paginas/actualizacion.py"]
