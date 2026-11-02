"""El comienzo del 409 «ya tiene lista para armar» que reconoce Componer es el del servidor (T4).

`POST /v1/carpeta/lista-para-armar {desde: "maprex"}` responde 409 con `MENSAJE_YA_TIENE_LISTA` de
`api/rutas/carpeta.py` cuando la carpeta ya tiene lista para armar. Componer
(`frontend-desktop/src/paginas/componer/AvisoSinLista.tsx`) reconoce ese 409 por el comienzo del
mensaje (`YA_TIENE_LISTA`) para decir «Sin cambios»: si uno cambia sin el otro, el aviso deja de
salir en silencio. Esta prueba ata los dos, como `test_front_razon_mercado.py` (T15).

Oráculo: la constante del servidor, no el código del front.
"""

from __future__ import annotations

import re
from pathlib import Path

from api.rutas.carpeta import MENSAJE_YA_TIENE_LISTA

RAIZ = Path(__file__).resolve().parents[2]
AVISO = RAIZ / "frontend-desktop" / "src" / "paginas" / "componer" / "AvisoSinLista.tsx"
#: `export const YA_TIENE_LISTA = "…";` (una cadena entre comillas dobles, sin comillas dentro).
CONSTANTE = re.compile(r'^export const YA_TIENE_LISTA = "([^"\n]*)";$', re.MULTILINE)


def comienzo_del_front(fuente: str) -> str:
    """El texto de `YA_TIENE_LISTA` en el fuente de `AvisoSinLista.tsx` (una sola definición)."""
    halladas = CONSTANTE.findall(fuente)
    assert len(halladas) == 1, f"se esperaba una sola YA_TIENE_LISTA; hay {len(halladas)}"
    return halladas[0]


def test_el_mensaje_del_servidor_empieza_por_lo_que_reconoce_el_front() -> None:
    comienzo = comienzo_del_front(AVISO.read_text(encoding="utf-8"))
    assert comienzo.strip() != ""
    assert MENSAJE_YA_TIENE_LISTA.format(nombre="Lista ficticia").startswith(comienzo)


def test_la_guardia_ve_un_comienzo_distinto() -> None:
    """Si el front esperara otro texto (o no lo definiera), la comparación lo nota."""
    otro = 'export const YA_TIENE_LISTA = "La carpeta ya tiene su lista";\n'
    assert not MENSAJE_YA_TIENE_LISTA.format(nombre="x").startswith(comienzo_del_front(otro))
    try:
        comienzo_del_front("const otra = 1;\n")
    except AssertionError:
        pass
    else:  # pragma: no cover - solo si la guardia dejara de exigir la definicion
        raise AssertionError("una fuente sin YA_TIENE_LISTA debe fallar")
