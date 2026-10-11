"""OF-001 completa como `Espacio` (datos de `tests/fixtures/memorias/of001.md`, secciones 1 a 4).

Baño, cocineta, recepción, cuarto técnico y las zonas A y B, con las tres especialidades en el mismo
espacio. Coordenadas supuestas y declaradas como tales (NORMAS.md §1): no provienen de un plano.
Todos los recorridos son propuestos (la geometría los calcula); `C1` declara el orden de su cadena y
`C2` lo deja vacío para que lo proponga el vecino más cercano.
"""

from __future__ import annotations

from decimal import Decimal

from adapters.espacio import (
    Ambiente,
    Circuito,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    OrigenMedida,
    Punto,
    SuperficiePunto,
    TipoFuente,
    TipoOrigen,
    TipoPunto,
)

D = Decimal
ALTO = D("2.5")
ORIGEN = "O1"


def _c(x: str, y: str, z: str) -> Coord:
    return Coord(D(x), D(y), D(z))


def _ambiente(id_: str, nombre: str, x0: str, y0: str, largo: str, ancho: str) -> Ambiente:
    return Ambiente(
        id=id_,
        nombre=nombre,
        x0=D(x0),
        y0=D(y0),
        largo=D(largo),
        ancho=D(ancho),
        alto=ALTO,
        origen_id=ORIGEN,
    )


def _fuente(id_: str, esp: Especialidad, tipo: TipoFuente, ambiente: str, pos: Coord) -> Fuente:
    return Fuente(
        id=id_, especialidad=esp, tipo=tipo, ambiente_id=ambiente, posicion=pos, origen_id=ORIGEN
    )


def _punto(
    id_: str,
    nombre: str,
    esp: Especialidad,
    tipo: TipoPunto,
    ambiente: str,
    superficie: SuperficiePunto,
    pos: Coord,
    fuente: str | None = None,
    circuito: str | None = None,
    **especificaciones: str,
) -> Punto:
    return Punto(
        id=id_,
        nombre=nombre,
        especialidad=esp,
        tipo=tipo,
        ambiente_id=ambiente,
        superficie=superficie,
        posicion=pos,
        fuente_id=fuente,
        circuito_id=circuito,
        especificaciones=especificaciones,
        origen_id=ORIGEN,
    )


AGUA, DATOS, ELEC = Especialidad.AGUA, Especialidad.DATOS, Especialidad.ELECTRICIDAD
PARED, TECHO, PISO = SuperficiePunto.PARED, SuperficiePunto.TECHO, SuperficiePunto.PISO


def _puntos_agua() -> tuple[Punto, ...]:
    return (
        _punto("P1", "lavamanos", AGUA, TipoPunto.AGUA_FRIA, "BAN-01", PARED, _c("1.5", "0", "0.6"),
               "F1", diametro='1/2"', llave_de_paso="si"),
        _punto("P2", "ducha", AGUA, TipoPunto.AGUA_FRIA, "BAN-01", PARED, _c("1", "1.5", "1.2"),
               "F1", diametro='3/4"', llave_de_paso="si"),
        _punto("D1", "desague de la ducha", AGUA, TipoPunto.DRENAJE, "BAN-01", PISO,
               _c("1", "1.5", "0"), "FD1", diametro='2"'),
        _punto("D2", "desague del lavamanos", AGUA, TipoPunto.DRENAJE, "BAN-01", PARED,
               _c("1.5", "0", "0.5"), "FD1", diametro='1 1/2"'),
        _punto("PC1", "fregadero", AGUA, TipoPunto.AGUA_FRIA, "COC-01", PARED,
               _c("1", "1.5", "0.9"), "FC1", diametro='1/2"', llave_de_paso="si"),
        _punto("DC1", "desague del fregadero", AGUA, TipoPunto.DRENAJE, "COC-01", PARED,
               _c("1", "1.5", "0.45"), "FDC1", diametro='2"'),
    )  # fmt: skip


def _puntos_datos() -> tuple[Punto, ...]:
    def dato(id_: str, ambiente: str, y: str, diametro: str, **extra: str) -> Punto:
        x = "0" if id_ == "PR1" else "6"
        return _punto(id_, f"puesto {id_}", DATOS, TipoPunto.DATOS, ambiente, PARED,
                      _c(x, y, "0.3"), "RK1", diametro=diametro, **extra)  # fmt: skip

    return (
        dato("PA1", "ZA", "2.5", '3/4"'),  # no declara categoria: la de por defecto (D-11)
        dato("PA2", "ZA", "3", '3/4"', categoria="cat 6"),
        dato("PA3", "ZA", "3.5", '3/4"', categoria="cat 6"),
        dato("PB1", "ZB", "4.5", '3/4"', categoria="cat 6"),
        dato("PB2", "ZB", "5", '3/4"', categoria="cat 6"),
        dato("PB3", "ZB", "5.5", '3/4"', categoria="cat 6"),
        dato("PR1", "REC-01", "4", '1/2"', categoria="cat 6"),
    )


def _puntos_electricos() -> tuple[Punto, ...]:
    def toma(id_: str, ambiente: str, y: str) -> Punto:
        return _punto(id_, f"tomacorriente {id_}", ELEC, TipoPunto.TOMACORRIENTE, ambiente, PARED,
                      _c("6", y, "0.3"), circuito="C1", diametro='3/4"')  # fmt: skip

    def luz(id_: str, ambiente: str, x: str, y: str) -> Punto:
        return _punto(id_, f"luminaria {id_}", ELEC, TipoPunto.ILUMINACION, ambiente, TECHO,
                      _c(x, y, "2.5"), circuito="C2", diametro='1/2"')  # fmt: skip

    return (
        toma("TA1", "ZA", "2.5"),
        toma("TA2", "ZA", "3.5"),
        toma("TB1", "ZB", "4.5"),
        toma("TB2", "ZB", "5.5"),
        luz("LZ1", "ZA", "3", "3"),
        luz("LZ2", "ZA", "5", "3"),
        luz("LZ3", "ZB", "5", "5"),
        luz("LZ4", "ZB", "3", "5"),
    )


def espacio_of001() -> Espacio:
    """La oficina completa de la memoria `of001.md`."""
    return Espacio(
        origenes=(
            OrigenMedida(
                id=ORIGEN,
                tipo=TipoOrigen.SUPUESTO,
                referencia={"motivo": "ejemplo de memoria de cálculo"},
            ),
        ),
        ambientes=(
            _ambiente("BAN-01", "Baño", "0", "0", "2", "1.5"),
            _ambiente("COC-01", "Cocineta", "0", "1.5", "2", "1.5"),
            _ambiente("REC-01", "Recepción", "0", "3", "2", "3"),
            _ambiente("CT-01", "Cuarto técnico", "2", "0", "2", "2"),
            _ambiente("ZA", "Zona A", "2", "2", "4", "2"),
            _ambiente("ZB", "Zona B", "2", "4", "4", "2"),
        ),
        fuentes=(
            _fuente("F1", AGUA, TipoFuente.MONTANTE_AGUA, "BAN-01", _c("0", "0", "0")),
            _fuente("FD1", AGUA, TipoFuente.COLECTOR_DRENAJE, "BAN-01", _c("2", "0.75", "0")),
            _fuente("FC1", AGUA, TipoFuente.MONTANTE_AGUA, "COC-01", _c("0", "1.5", "0")),
            _fuente("FDC1", AGUA, TipoFuente.COLECTOR_DRENAJE, "COC-01", _c("2", "2.25", "0")),
            _fuente("RK1", DATOS, TipoFuente.RACK, "CT-01", _c("3", "1", "0")),
            _fuente("T1", ELEC, TipoFuente.TABLERO, "CT-01", _c("4", "1", "1.5")),
        ),
        circuitos=(
            Circuito(
                id="C1",
                tablero="T1",
                numero=1,
                conductores=(1, 1, 1),
                calibre="12 AWG",
                puntos_maximos=6,
                orden=("TA1", "TA2", "TB1", "TB2"),
            ),
            Circuito(
                id="C2",
                tablero="T1",
                numero=2,
                conductores=(1, 1, 1),
                calibre="14 AWG",
                puntos_maximos=6,
            ),
        ),
        puntos=_puntos_agua() + _puntos_datos() + _puntos_electricos(),
    )
