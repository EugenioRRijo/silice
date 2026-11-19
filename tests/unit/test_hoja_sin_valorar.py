"""El mensaje de una partida que la Hoja no puede valorar (`aplicacion.hoja_sin_valorar`).

Árbitro de la rama `feature/vivo-presupuesto` (2026-11-18): el paso «Qué hacer» dice solo lo que
falta. Con un motivo del catálogo que no es ni precio ni rendimiento no habla de ninguno de los dos
(antes redactaba «Qué hacer: . Luego…»), y Componer solo agrega los precios que le faltan a la
lista (`core/catalog/repositorio.py`, `_resolver_insumo`: un precio distinto crea una variante, no
reescribe el que ya está). Datos ficticios; los textos esperados, escritos a mano.
"""

from __future__ import annotations

from datetime import date

from aplicacion.hoja_sin_valorar import DE_NUEVO, SinValorar, mensaje_sin_valorar
from core import models

LISTA = models.ListaPrecios(nombre="Lista ficticia", moneda="Bs", fecha_vigencia=date(2026, 10, 1))
FECHA = date(2026, 10, 25)
TEXTOS = {
    "inicio": "La partida «X-1» queda pendiente en el Presupuesto",
    "se_valora": "se puede valorar",
    "esas": "esa partida",
    "cierre": "Fin.",
}


def _mensaje(falta: SinValorar, componer_con: date | None) -> str:
    return mensaje_sin_valorar(
        [falta], LISTA, "V-001", FECHA, [], componer_con=componer_con, **TEXTOS
    )


def test_un_motivo_del_catalogo_no_habla_de_precios_ni_de_rendimiento() -> None:
    otro = SinValorar("X-1", False, (), (), "su APU no tiene líneas")
    for componer_con in (None, date(2026, 10, 1)):
        assert _mensaje(otro, componer_con) == (
            "La partida «X-1» queda pendiente en el Presupuesto porque el Presupuesto arma cada "
            "APU con la lista «Lista ficticia» de la versión V-001, al 25/10/2026, y con ella no "
            "se puede valorar. «X-1»: su APU no tiene líneas. Qué hacer: revise esa partida en "
            "Componer y vuelva a guardarla. Fin."
        )


def test_sin_precio_y_sin_rendimiento_dice_las_dos_cosas() -> None:
    ambas = SinValorar("X-1", True, ("Bloque",), (7,), None)
    assert _mensaje(ambas, date(2026, 10, 1)).endswith(
        "Qué hacer: en Componer, guarde esa partida con fecha 01/10/2026: solo se agregan a "
        "«Lista ficticia» los precios que le faltan (los que ya tiene no cambian) y su "
        f"rendimiento queda a esa fecha ({DE_NUEVO}). Fin."
    )
