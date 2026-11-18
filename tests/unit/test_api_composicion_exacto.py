"""Las cifras exactas de la composicion salen por `api.presentacion.exacto` (anexo A.7).

`f"{v:f}"` y `exacto(v)` son el mismo texto: sin redondear, sin recortar ceros y sin notacion
cientifica. Estas pruebas fijan esa salida para que el paso a `api/presentacion.py` no la cambie.
Casos construidos a mano.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from api.rutas.composicion import _evaluacion, _prevision
from aplicacion.composicion import AvisoVariante, ContrasteEvaluado, Evaluacion, Prevision
from aplicacion.listas_para_armar import ListaParaArmar

#: (valor, texto esperado): con ceros de relleno, con exponente positivo y con exponente negativo.
CASOS = [
    (Decimal("9.50"), "9.50"),
    (Decimal("1E+2"), "100"),
    (Decimal("5E-7"), "0.0000005"),
]


@pytest.mark.parametrize(("valor", "texto"), CASOS)
def test_el_pu_estimado_del_contraste_sale_exacto(valor: Decimal, texto: str) -> None:
    evaluacion = Evaluacion(
        estado="valido",
        contraste=ContrasteEvaluado(
            tecnica="reglas", registros=3, pu_estimado=valor, dentro_de_rango=True
        ),
    )

    assert _evaluacion(evaluacion).contraste.pu_estimado == texto


@pytest.mark.parametrize(("valor", "texto"), CASOS)
def test_los_precios_de_la_variante_salen_exactos(valor: Decimal, texto: str) -> None:
    prevision = Prevision(
        lista=ListaParaArmar(
            lista_id=1, nombre="Lista de prueba", moneda="Bs", fecha=date(2026, 11, 18), origen="x"
        ),
        lista_nueva=False,
        variantes=[
            AvisoVariante(
                descripcion="Cemento de prueba",
                unidad="saco",
                precio_en_lista=valor,
                precio_tecleado=valor + 1,
                codigo_variante="MAT-001-B",
            )
        ],
    )

    variante = _prevision(prevision).variantes[0]

    assert variante.precio_en_lista == texto
    assert variante.precio_tecleado == format(valor + 1, "f")
