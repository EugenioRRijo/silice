"""Búsqueda de partidas del catálogo (`aplicacion/busqueda.py`; Tarea 10 del plan de montar un
presupuesto; diseño de autocompletado 2026-10-21 §5.1, §5.2 y §5.4).

Contrato: `buscar_partidas(catalogo, q, dominio, limite) -> (halladas, hay_mas)`. Una partida
coincide si **todas** las palabras de `q` (normalizadas: minúsculas, sin tildes) están en su código
o su descripción; el rango (menor primero) es 0 = código igual al texto, 1 = código que empieza por
el texto, 2 = descripción que empieza por la primera palabra, 3 = alguna palabra de la descripción
empieza por ella, 4 = cualquier otra coincidencia; desempate por descripción normalizada y luego
por código. Menos de 2 letras → nada. `hay_mas` dice si quedaron coincidencias fuera del límite.

Oráculos escritos a mano: las partidas de abajo son ficticias y su rango se calculó leyendo cada
descripción, no corriendo el código. Para «bloq»:

| código   | descripción                         | por qué                                   | rango |
|----------|-------------------------------------|-------------------------------------------|-------|
| BLOQ     | Zanja de prueba                     | el código es «bloq»                        | 0     |
| BLOQ-01  | Pared de arcilla                    | el código empieza por «bloq»               | 1     |
| BLOQ-T   | Bloque de telecom (dominio telecom) | el código empieza por «bloq»               | 1     |
| PAR-06   | Bloques de arcilla                  | la descripción empieza por «bloq»          | 2     |
| PAR-02   | Bloques de concreto de 15 cm        | la descripción empieza por «bloq»          | 2     |
| PAR-03   | Pared de bloques de arcilla         | la palabra «bloques» empieza por «bloq»    | 3     |
| PAR-04   | Pared con sobrebloque decorativo    | «sobrebloque» contiene «bloq», no empieza  | 4     |
| PAR-05   | Friso liso                          | no coincide                                | —     |
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from aplicacion.busqueda import PartidaHallada, buscar_partidas
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts.dominio import Dominio
from core.models import Partida
from operacion.base_datos import preparar_base
from scripts.seed import sembrar

#: (código, descripción, unidad, dominio): ficticias, escritas para esta prueba.
PARTIDAS = (
    ("BLOQ", "Zanja de prueba", "m3", "civil"),
    ("BLOQ-01", "Pared de arcilla", "m2", "civil"),
    ("BLOQ-T", "Bloque de telecom", "pza", "telecom"),
    ("PAR-06", "Bloques de arcilla", "m2", "civil"),
    ("PAR-02", "Bloques de concreto de 15 cm", "m2", "civil"),
    ("PAR-03", "Pared de bloques de arcilla", "m2", "civil"),
    ("PAR-04", "Pared con sobrebloque decorativo", "m2", "civil"),
    ("PAR-05", "Friso liso", "m2", "civil"),
)


def _codigos(halladas: list[PartidaHallada]) -> list[str]:
    return [h.codigo for h in halladas]


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator[Session]:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as abierta:
            for codigo, descripcion, unidad, dominio in PARTIDAS:
                abierta.add(
                    Partida(codigo=codigo, descripcion=descripcion, unidad=unidad, dominio=dominio)
                )
            abierta.commit()
            yield abierta
    finally:
        motor.dispose()


@pytest.fixture
def catalogo(sesion: Session) -> Catalogo:
    return Catalogo(sesion)


def test_el_orden_sigue_los_cinco_rangos_y_el_desempate(catalogo: Catalogo) -> None:
    halladas, hay_mas = buscar_partidas(catalogo, "bloq", Dominio.CIVIL, 20)
    assert _codigos(halladas) == ["BLOQ", "BLOQ-01", "PAR-06", "PAR-02", "PAR-03", "PAR-04"]
    assert hay_mas is False


def test_sin_dominio_entran_todas_y_con_otro_solo_las_suyas(catalogo: Catalogo) -> None:
    todas, _ = buscar_partidas(catalogo, "bloq", None, 20)
    # BLOQ-T (rango 1) va antes que BLOQ-01 (rango 1): «bloque de telecom» < «pared de arcilla».
    assert _codigos(todas) == [
        "BLOQ",
        "BLOQ-T",
        "BLOQ-01",
        "PAR-06",
        "PAR-02",
        "PAR-03",
        "PAR-04",
    ]
    telecom, _ = buscar_partidas(catalogo, "bloq", Dominio.TELECOM, 20)
    assert _codigos(telecom) == ["BLOQ-T"]


def test_la_partida_hallada_trae_su_cabecera(catalogo: Catalogo) -> None:
    halladas, _ = buscar_partidas(catalogo, "BLOQ-01", None, 20)
    assert halladas[0] == PartidaHallada(
        codigo="BLOQ-01",
        descripcion="Pared de arcilla",
        unidad="m2",
        dominio="civil",
        tiene_composicion=False,
    )


def test_todas_las_palabras_en_cualquier_orden(catalogo: Catalogo) -> None:
    # «arcilla pared»: solo BLOQ-01 y PAR-03 tienen las dos palabras (PAR-06 dice «par-06», no «pared»).
    # Las dos tienen rango 3 por «arcilla»; «pared de arcilla» < «pared de bloques de arcilla».
    halladas, _ = buscar_partidas(catalogo, "arcilla pared", None, 20)
    assert _codigos(halladas) == ["BLOQ-01", "PAR-03"]
    al_reves, _ = buscar_partidas(catalogo, "pared arcilla", None, 20)
    assert {h.codigo for h in al_reves} == {"BLOQ-01", "PAR-03"}


def test_ignora_tildes_mayusculas_y_espacios_sobrantes(catalogo: Catalogo) -> None:
    # «bloques» está en PAR-06 y PAR-02 (rango 2) y en PAR-03 (rango 3); no en «sobrebloque».
    esperado = ["PAR-06", "PAR-02", "PAR-03"]
    assert _codigos(buscar_partidas(catalogo, "BLÓQUES", None, 20)[0]) == esperado
    assert _codigos(buscar_partidas(catalogo, "   bloques  ", None, 20)[0]) == esperado


def test_menos_de_dos_letras_no_busca(catalogo: Catalogo) -> None:
    assert buscar_partidas(catalogo, "b", None, 20) == ([], False)
    assert buscar_partidas(catalogo, "", None, 20) == ([], False)
    assert buscar_partidas(catalogo, "  p  ", None, 20) == ([], False)
    # dos letras ya buscan: «bl» está en los códigos BLOQ, BLOQ-01 y BLOQ-T y en «bloques»/«sobrebloque»
    assert len(buscar_partidas(catalogo, "bl", None, 20)[0]) == 7


def test_sin_coincidencias_es_una_lista_vacia(catalogo: Catalogo) -> None:
    assert buscar_partidas(catalogo, "tuberia", None, 20) == ([], False)


def test_el_limite_corta_y_avisa_que_hay_mas(catalogo: Catalogo) -> None:
    halladas, hay_mas = buscar_partidas(catalogo, "bloq", Dominio.CIVIL, 2)
    assert _codigos(halladas) == ["BLOQ", "BLOQ-01"]
    assert hay_mas is True
    # seis coincidencias en civil: con límite 6 caben todas y no hay más
    halladas, hay_mas = buscar_partidas(catalogo, "bloq", Dominio.CIVIL, 6)
    assert len(halladas) == 6
    assert hay_mas is False


@pytest.mark.parametrize("limite", [0, 51, -1])
def test_un_limite_fuera_de_rango_es_un_error(catalogo: Catalogo, limite: int) -> None:
    with pytest.raises(ValueError, match="límite"):
        buscar_partidas(catalogo, "bloq", None, limite)


def test_tiene_composicion_dice_si_la_partida_tiene_lineas(tmp_path: Path) -> None:
    """La línea base (`scripts.seed.sembrar`) trae la tubería con su APU; una partida agregada a
    mano sin líneas dice que no tiene composición."""
    ruta = tmp_path / "linea_base.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.add(
                Partida(
                    codigo="LB-06-PIN",
                    descripcion="Pintura de tanquillas",
                    unidad="m2",
                    dominio="civil",
                )
            )
            sesion.commit()
            catalogo = Catalogo(sesion)
            tuberia, _ = buscar_partidas(catalogo, "LB-02-TUB", None, 20)
            assert tuberia[0].codigo == "LB-02-TUB"
            assert tuberia[0].tiene_composicion is True
            pintura, _ = buscar_partidas(catalogo, "pintura", None, 20)
            assert [(p.codigo, p.tiene_composicion) for p in pintura] == [("LB-06-PIN", False)]
    finally:
        motor.dispose()
