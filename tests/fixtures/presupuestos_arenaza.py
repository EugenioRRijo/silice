"""Los dos presupuestos didacticos de ARENAZA (telecom), transcritos renglon a renglon.

Fuente primaria: `data/samples/telecom/Presupuesto_1_ARENAZA.pdf` (14 renglones, 1 109,29 USD)
y `Presupuesto_2_ARENAZA.pdf` (26 renglones, 5 410,73 USD), ambos con fecha 18/05/2026. Es la
segunda linea base didactica de la tesis, en otro dominio (CLAUDE.md seccion 1): la primera es
`tests/fixtures/apu_linea_base.py` (civil).

Direccion CSV <-> fixture (decision de esta sesion, brief Sesion M1.1 paso 4): el CSV NO se
genera desde este fixture ni este fixture lee el CSV en tiempo de prueba. `scripts/
extraer_arenaza.py` lee los dos PDF con PyMuPDF y escribe `data/telecom/fuentes/
presupuesto_1_arenaza.csv` y `presupuesto_2_arenaza.csv` de forma independiente (mismo
contrato que `scripts/extraer_maprex.py`, Sesion M0.2). Este fixture es una segunda
transcripcion, tambien hecha a mano contra el mismo PDF, de la MISMA fuente primaria -- no una
lectura del CSV. `tests/unit/test_fuentes_arenaza.py::test_fixture_coincide_con_csv` es el
mecanismo de reconciliacion: si el fixture y el CSV alguna vez se transcriben distinto, la
prueba falla (comparando la suma de `total`, no cada campo, porque son dos formas -- Python y
CSV -- de la misma informacion, no una derivada de la otra). Se elige esta direccion (dos
transcripciones independientes verificadas por una prueba) en vez de generar una desde la otra
en tiempo de ejecucion porque sigue el mismo patron que `tests/fixtures/apu_linea_base.py`
(valores `Decimal` literales, sin E/S en tiempo de prueba) y porque una prueba que reconcilia
dos transcripciones independientes es mas sensible a un error de transcripcion que una que
compara un dato contra si mismo.

Forma del fixture: dataclass `RenglonPresupuesto` (no dict), por eso
`tests/unit/test_fuentes_arenaza.py::test_fixture_coincide_con_csv` usa `r.total` (atributo),
no `r["total"]` -- la alternativa que documenta el brief para un fixture de dicts. Mismo patron
que `LineaPresupuestoAuditado` en `tests/fixtures/apu_linea_base.py`.

`cantidad` y `precio_unitario` son `Decimal | None`: son `None` unicamente en el renglon 14 de
`PRESUPUESTO_1` ("Micelaneos"), una partida global de contingencia que el PDF no descompone en
cantidad x precio unitario (solo trae un `total` de 100,00 USD). No se inventa una cantidad de
"1" ni un precio "100.00" que la fuente no declara (CLAUDE.md seccion 2, principio de
trazabilidad total: un dato que la fuente no tiene no se rellena por conveniencia).

Cuando la tabla "Presupuesto" del PDF omite el precio unitario por ser igual al total
(renglones con `cantidad = 1`), este fixture SI completa `precio_unitario` con ese mismo
importe (division exacta entre 1): no es un precio inventado, es el mismo dato ya impreso en la
columna `total`, solo copiado a la columna que el PDF deja vacia por redundancia. Ver
`scripts/extraer_arenaza.py` para el mismo criterio aplicado al CSV.

La inconsistencia del tubo corrugado (`TUBO_CORRUGADO`): el renglon 5 de
`Presupuesto_2_ARENAZA.pdf` ("Tubo Corrugado Flexible 1 Pulgada") trae `cantidad = 80` en la
tabla "Computos metricos" (pagina 1) y `cantidad = 90` en la tabla "Presupuesto" (pagina 2) del
MISMO PDF. Es la segunda inconsistencia de fuente primaria que la tesis registra tal cual, sin
corregir (la primera son las siete de `apu_linea_base.py`, caso civil). `PRESUPUESTO_2` usa 90
(el valor de la tabla "Presupuesto", que es la que trae precio y total); `TUBO_CORRUGADO` deja
ambos valores explicitos para que una regla de verificacion futura (Sesion M1.3, hallazgo
80/90) los compare.

Hallazgos adicionales (no forman parte de la inconsistencia 80/90 exigida por esta sesion, pero
se documentan aqui y en `data/telecom/fuentes/README.md` con el mismo criterio de no ocultar
nada de la fuente primaria):

- Presupuesto 2, renglon 14 ("Camara Bullet Ip 4mp Intemperie"): `total` impreso 1 446,65 no
  coincide con `cantidad x precio_unitario` = 5 x 289,00 = 1 445,00 (diferencia de 1,65).
- Presupuesto 2, renglon 18 ("Conector Jack Coupler Ubiquiti Rj45"): `total` impreso 303,93 no
  coincide con `cantidad x precio_unitario` = 7 x 42,99 = 300,93 (diferencia de 3,00).

Ninguno de los dos se corrige: `total` es el valor que declara el PDF y el que entra en la
suma verificada por `test_totales_exactos` (1 109,29 y 5 410,73 exactos).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RenglonPresupuesto:
    renglon: int
    descripcion: str
    unidad: str
    cantidad: Decimal | None
    precio_unitario: Decimal | None
    total: Decimal
    origen: str


def _r(
    renglon: int,
    descripcion: str,
    unidad: str,
    cantidad: str | None,
    precio_unitario: str | None,
    total: str,
    origen: str,
) -> RenglonPresupuesto:
    return RenglonPresupuesto(
        renglon=renglon,
        descripcion=descripcion,
        unidad=unidad,
        cantidad=None if cantidad is None else Decimal(cantidad),
        precio_unitario=None if precio_unitario is None else Decimal(precio_unitario),
        total=Decimal(total),
        origen=origen,
    )


# ---------------------------------------------------------------------------------------------
# Presupuesto 1: Presupuesto_1_ARENAZA.pdf, 001, 18/05/2026, 14 renglones, 1 109,29 USD
# ---------------------------------------------------------------------------------------------

PRESUPUESTO_1: tuple[RenglonPresupuesto, ...] = (
    _r(1, "BOBINA CABLE UTP CAT 6 (300 M)", "Pieza", "1", "82.68", "82.68",
       "Presupuesto_1_ARENAZA.pdf:2:1"),
    _r(2, "Switch Escritorio Gigabit De 10 Puertos Con Poe De", "Pieza", "1", "157.99", "157.99",
       "Presupuesto_1_ARENAZA.pdf:2:2"),
    # Tubo corrugado del presupuesto 1: 90 m en computos metricos y 90 m en presupuesto -- sin
    # inconsistencia (la inconsistencia 80/90 es exclusiva del presupuesto 2, ver TUBO_CORRUGADO).
    # Precio cotizado por tubo de 30 m: 3*99.75 = 299.25 (99.75 es el precio de UN tubo, no de un
    # metro; se preserva el precio_unitario tal como lo imprime el PDF).
    _r(3, "Tubo Corrugado Flexible 1 Pulgada", "Metros", "90", "99.75", "299.25",
       "Presupuesto_1_ARENAZA.pdf:2:3"),
    _r(4, "Conectores Rj45 Cat6 Utp Bolsa (100 unidades)", "Pieza", "1", "5.00", "5.00",
       "Presupuesto_1_ARENAZA.pdf:2:4"),
    _r(5, "Bosla Tirrap (100 unidades)", "Pieza", "5", "2.00", "10.00",
       "Presupuesto_1_ARENAZA.pdf:2:5"),
    _r(6, "Organizador De Cables Individuales 20cm 100 Und", "Pieza", "5", "18.00", "90.00",
       "Presupuesto_1_ARENAZA.pdf:2:6"),
    _r(7, "Bobina Cable Utp Cat6 305 m Int", "Pieza", "1", "211.21", "211.21",
       "Presupuesto_1_ARENAZA.pdf:2:7"),
    _r(8, "Teipe Eléctrico Negro Cobra", "Pieza", "1", "9.99", "9.99",
       "Presupuesto_1_ARENAZA.pdf:2:8"),
    _r(9, "Teipe Aislante Para Cableado Eléctrico", "Pieza", "1", "10.00", "10.00",
       "Presupuesto_1_ARENAZA.pdf:2:9"),
    _r(10, "Toma Doble Con Tierra 270 20a Con Placa Blanca", "Pieza", "5", "5.05", "25.25",
       "Presupuesto_1_ARENAZA.pdf:2:10"),
    _r(11, "Anillo E.m.t. 2", "Pieza", "2", "3.96", "7.92", "Presupuesto_1_ARENAZA.pdf:2:11"),
    _r(12, "Guaya Guia Pasa Cable De Acero", "Pieza", "1", "90.00", "90.00",
       "Presupuesto_1_ARENAZA.pdf:2:12"),
    _r(13, "Cajetin Plástico 4x2 Pvc Con Grapa Metálica.", "Pieza", "5", "2.00", "10.00",
       "Presupuesto_1_ARENAZA.pdf:2:13"),
    # Partida global de contingencia sin cantidad ni precio unitario en ninguna de las dos tablas
    # del PDF (ver docstring del modulo): cantidad y precio_unitario quedan en None.
    _r(14, "Micelaneos", "", None, None, "100.00", "Presupuesto_1_ARENAZA.pdf:2:14"),
)
TOTAL_1 = Decimal("1109.29")

# ---------------------------------------------------------------------------------------------
# Presupuesto 2: Presupuesto_2_ARENAZA.pdf, 002, 18/05/2026, 26 renglones, 5 410,73 USD
# ---------------------------------------------------------------------------------------------

PRESUPUESTO_2: tuple[RenglonPresupuesto, ...] = (
    _r(1, "BOBINA CABLE UTP CAT 6 (300 M) Ext", "Pieza", "1", "96.99", "96.99",
       "Presupuesto_2_ARENAZA.pdf:2:1"),
    _r(2, "Bobina Cable Utp Cat6 305 m Int", "Pieza", "1", "211.21", "211.21",
       "Presupuesto_2_ARENAZA.pdf:2:2"),
    _r(3, "Punto De Acceso Rap Ruijie", "Pieza", "4", "208.92", "835.68",
       "Presupuesto_2_ARENAZA.pdf:2:3"),
    _r(4, "Switch Tp-link Tl-sg108 8 Puertos", "Pieza", "1", "278.56", "278.56",
       "Presupuesto_2_ARENAZA.pdf:2:4"),
    # Renglon del hallazgo 80/90 (ver TUBO_CORRUGADO): cantidad 90 en la tabla "Presupuesto"
    # (la que usa este fixture), 80 en "Computos metricos" del mismo PDF. Precio cotizado por
    # tubo de 30 m (3*99.75=299.25), igual que en el presupuesto 1.
    _r(5, "Tubo Corrugado Flexible 1 Pulgada 30 MTS", "Metros", "90", "99.75", "299.25",
       "Presupuesto_2_ARENAZA.pdf:2:5"),
    _r(6, "Conectores Rj45 Cat6 Utp Bolsa (100 unidades)", "Pieza", "1", "5.00", "5.00",
       "Presupuesto_2_ARENAZA.pdf:2:6"),
    _r(7, "Amarre Tiewrap Negro Plástico 20 Cm", "Pieza", "5", "2.84", "14.20",
       "Presupuesto_2_ARENAZA.pdf:2:7"),
    _r(8, "Organizador De Cables Individuales 20cm 100 Und", "Pieza", "5", "19.00", "95.00",
       "Presupuesto_2_ARENAZA.pdf:2:8"),
    _r(9, "Protector De Voltaje Exceline", "Pieza", "4", "33.00", "132.00",
       "Presupuesto_2_ARENAZA.pdf:2:9"),
    _r(10, "Rack Fijo Onlink 12u", "Pieza", "1", "202.00", "202.00",
       "Presupuesto_2_ARENAZA.pdf:2:10"),
    _r(11, "Switch Tp-link 16 Puertos", "Pieza", "1", "160.00", "160.00",
       "Presupuesto_2_ARENAZA.pdf:2:11"),
    _r(12, "Mini Ups Spidertec 17600mah", "Pieza", "1", "120.00", "120.00",
       "Presupuesto_2_ARENAZA.pdf:2:12"),
    _r(13, "Nvr Hikvision 7600 Ds-7616ni-q2 16 Canales", "Pieza", "1", "118.75", "118.75",
       "Presupuesto_2_ARENAZA.pdf:2:13"),
    # Hallazgo adicional (no es el 80/90 exigido, pero tampoco se oculta): total impreso 1446.65
    # no coincide con cantidad x precio_unitario = 5*289.00 = 1445.00. Se transcribe tal cual.
    _r(14, "Camara Bullet Ip 4mp Intemperie", "Pieza", "5", "289.00", "1446.65",
       "Presupuesto_2_ARENAZA.pdf:2:14"),
    _r(15, "Cámara Domo Ip Hikvision 4mp", "Pieza", "5", "127.35", "636.75",
       "Presupuesto_2_ARENAZA.pdf:2:15"),
    _r(16, "Cajetin Superficial 4x2 Hembra", "Pieza", "5", "50.00", "250.00",
       "Presupuesto_2_ARENAZA.pdf:2:16"),
    _r(17, "Conector Rj-45 Ftp Cat6 Blindado 50 U", "Pieza", "2", "8.80", "17.60",
       "Presupuesto_2_ARENAZA.pdf:2:17"),
    # Segundo hallazgo adicional: total impreso 303.93 no coincide con 7*42.99=300.93.
    _r(18, "Conector Jack Coupler Ubiquiti Rj45", "Pieza", "7", "42.99", "303.93",
       "Presupuesto_2_ARENAZA.pdf:2:18"),
    _r(19, "Teipe Eléctrico Negro Cobra", "Pieza", "1", "9.99", "9.99",
       "Presupuesto_2_ARENAZA.pdf:2:19"),
    _r(20, "Teipe Aislante Para Cableado Eléctrico", "Pieza", "1", "10.00", "10.00",
       "Presupuesto_2_ARENAZA.pdf:2:20"),
    _r(21, "Canaleta Plastica 40x40x2mts", "Pieza", "2", "12.00", "24.00",
       "Presupuesto_2_ARENAZA.pdf:2:21"),
    _r(22, "Base Para Tirrap Tirraje 10 u", "Pieza", "2", "5.00", "10.00",
       "Presupuesto_2_ARENAZA.pdf:2:22"),
    _r(23, "Toma Doble Con Tierra 270 20a Con Placa Blanca", "Pieza", "5", "5.05", "25.25",
       "Presupuesto_2_ARENAZA.pdf:2:23"),
    _r(24, "Anillo E.m.t. 2", "Pieza", "2", "3.96", "7.92", "Presupuesto_2_ARENAZA.pdf:2:24"),
    _r(25, "Cajetin Plástico 4x2 Pvc Con Grapa Metálica.", "Pieza", "5", "2.00", "10.00",
       "Presupuesto_2_ARENAZA.pdf:2:25"),
    _r(26, "Guaya Guia Pasa Cable De Acero", "Pieza", "1", "90.00", "90.00",
       "Presupuesto_2_ARENAZA.pdf:2:26"),
)
TOTAL_2 = Decimal("5410.73")

# ---------------------------------------------------------------------------------------------
# La inconsistencia registrada: tubo corrugado del presupuesto 2, 80 m (computos metricos) vs
# 90 m (presupuesto), misma fuente primaria. No corregida (ver docstring del modulo).
# ---------------------------------------------------------------------------------------------

TUBO_CORRUGADO = {
    "descripcion": "Tubo Corrugado Flexible 1 Pulgada",
    "cantidad_computos": Decimal("80"),
    "cantidad_presupuesto": Decimal("90"),
    "origen_computos": "Presupuesto_2_ARENAZA.pdf:1:5",
    "origen_presupuesto": "Presupuesto_2_ARENAZA.pdf:2:5",
}
