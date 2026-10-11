"""Caso OF-001: oficina con baño, cocineta, recepción, cuarto técnico y dos zonas de puestos.

Caso construido para el proyecto (NORMAS.md §1), sobre la planta de TI-001 y simplificado para que
las cuentas se verifiquen a mano (`tests/fixtures/memorias/of001.md`): el espacio, los
rendimientos y los plazos son supuestos declarados; no es una obra ejecutada.

Precios: referencias publicadas MaPreX de julio de 2026 (materiales y equipos al 09/07/2026, mano
de obra al 01/07/2026), en Bs, convertidas a USD con la tasa que declara el propio listado
(633,3644 Bs/USD al 01/07/2026, la de `caso_ti001.TASA`). Cada insumo cita su Ref de MaPreX entre
corchetes; los insumos de TI-001 se importan, no se copian (DRY). **Dos insumos son proxies
declarados** (MaPreX no lista tubo ni codo de drenaje A.N. de 1 1/2 pulg: se usa el A.B. del mismo
diámetro, con su Ref) y se dicen en su descripción.

Flujo: `espacio_of001()` --derivar--> `ItemComputo` de agua, datos y electricidad;
`COMPOSICIONES` + `PARAMETROS` --`ui.hoja.elaborar_hoja`--> presupuesto e informe con R1 a R10.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.contracts import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
)
from tests.fixtures.caso_ti001 import INSUMOS as INSUMOS_TI001
from tests.fixtures.caso_ti001 import PARAMETROS, Insumo  # noqa: F401
from tests.fixtures.espacio_of001 import espacio_of001

FECHA = date(2026, 10, 5)
CODIGO = "OF-001"
MONEDA = "USD"


def _mat(descripcion: str, unidad: str, precio_bs: str, ref: str) -> Insumo:
    return Insumo("material", descripcion, unidad, precio_bs, ref)


def _mo(descripcion: str, jornal_bs: str, ref: str, bono_bs: str) -> Insumo:
    return Insumo("mano_obra", descripcion, "dia", jornal_bs, ref, bono_bs=bono_bs)


_DE_TI001 = (
    "utp",
    "emt34",
    "anillo34",
    "conector34",
    "curva34",
    "abraz34",
    "cajetin",
    "faceplate",
    "jack",
    "tirrap",
    "etiqueta",
    "pc05",
    "taladro",
    "dobladora",
    "escalera",
    "herramientas",
    "ponchadora",
    "certificador",
    "electricista",
    "ayudante",
    "tecnico",
)

INSUMOS: dict[str, Insumo] = {
    **{clave: INSUMOS_TI001[clave] for clave in _DE_TI001},
    # Agua fría (PVC A.B. a presión)
    "pvc12": _mat("Tubo PVC 1/2 pulg A.B. presion agua fria", "m", "1762.55", "MT2049"),
    "pvc34": _mat("Tubo PVC 3/4 pulg A.B. presion agua fria", "m", "3271.19", "MT2050"),
    "codo12": _mat("Codo PVC 90 grados 1/2 pulg presion agua fria", "pza", "906.00", "MT2079"),
    "codo34": _mat("Codo PVC 90 grados 3/4 pulg presion agua fria", "pza", "1510.00", "MT2080"),
    "tee34": _mat("Tee PVC 3/4 pulg presion agua fria", "pza", "1132.50", "MT2090"),
    "llave12": _mat("Llave de paso de bola PVC 1/2 pulg", "pza", "4907.50", "PLOG26"),
    "adaptador12": _mat("Adaptador macho PVC 1/2 pulg", "pza", "755.00", "PLOB97"),
    "pegamento": _mat("Pegamento para PVC 1/4 gl", "env", "21895.00", "MT539"),
    # Drenaje (PVC A.N.); el de 1 1/2 pulg es un proxy declarado
    "dr2": _mat("Tubo PVC A.N. 2 pulg norma e=1,8 mm", "m", "2604.75", "PLO210"),
    "dr112": _mat(
        "Tubo PVC 1 1/2 pulg A.B. ISO (proxy supuesto: MaPreX no lista A.N. de 1 1/2 pulg)",
        "m",
        "7026.22",
        "PLO557",
    ),
    "codo2": _mat("Codo PVC 90 grados A.N. 2 pulg", "pza", "2114.00", "PLO036"),
    "codo112": _mat(
        "Codo PVC 90 grados 1 1/2 pulg A.B. (proxy supuesto: MaPreX no lista A.N. de 1 1/2 pulg)",
        "pza",
        "3020.00",
        "PLO430",
    ),
    "sifon": _mat("Sifon PVC 1 1/2 pulg A.N. para fregadero", "pza", "4530.00", "SAN123"),
    "cemento": _mat("Cemento gris Portland saco 42,5 kg", "sco", "12080.00", "CEM019"),
    "arena": _mat("Arena lavada", "m3", "37750.00", "MZ0027"),
    # Canalización y electricidad
    "emt12": _mat("Tubo EMT 1/2 pulg acero galvanizado serie liviana", "m", "2014.16", "ELE308"),
    "anillo12": _mat("Anillo EMT 1/2 pulg", "pza", "755.00", "ELE029"),
    "conector12": _mat("Conector EMT 1/2 pulg", "pza", "755.00", "ELE185"),
    "curva12": _mat("Curva EMT 1/2 pulg", "pza", "2076.25", "ELE207"),
    "cable12": _mat("Cable THW 12 AWG cobre", "m", "1294.45", "ELE128"),
    "cable14": _mat("Cable THW 14 AWG cobre", "m", "932.00", "ELE450"),
    "toma": _mat("Tomacorriente doble 1 fase 20/30 A", "pza", "4303.50", "ELA190"),
    "tapatoma": _mat(
        "Tapa plastica soporte y puente para tomacorriente", "pza", "755.00", "ELE770"
    ),
    "aplique": _mat(
        "Aplique simple pared/techo con rosca para bombillo", "pza", "13590.00", "ELA084"
    ),
    "bombillo": _mat("Bombillo ahorrador fluorescente 11 W", "pza", "2642.50", "ELA252"),
    "breaker": _mat(
        "Breaker 1P x 20 A 120/240 residencial/industrial", "pza", "63420.00", "ELE987"
    ),
    # Mano de obra (jornal y bono de mano_de_obra.pdf)
    "plomero": _mo("Plomero de 1ra N5", "1385.63", "19-212", "3679.85"),
    "albanil": _mo("Albanil de 1ra N5", "1385.63", "19-2.2", "3679.85"),
}


def _m(clave: str, cantidad: str) -> LineaMaterial:
    insumo = INSUMOS[clave]
    return LineaMaterial(insumo.etiqueta, insumo.unidad, Decimal(cantidad), insumo.precio)


def _e(clave: str, cantidad: str = "1") -> LineaEquipo:
    insumo = INSUMOS[clave]
    return LineaEquipo(
        insumo.etiqueta, Decimal(cantidad), insumo.precio, Decimal(insumo.depreciacion)
    )


def _o(clave: str, cantidad: str) -> LineaManoObra:
    insumo = INSUMOS[clave]
    return LineaManoObra(insumo.etiqueta, Decimal(cantidad), insumo.precio)


_CUADRILLA_PLOMERIA = (_o("plomero", "1"), _o("ayudante", "1"))
_CUADRILLA_ALBANILERIA = (_o("albanil", "1"), _o("ayudante", "1"))
_CUADRILLA_ELECTRICA = (_o("electricista", "1"), _o("ayudante", "1"))
_HERRAMIENTAS = (_e("herramientas"),)


def _apu(
    codigo: str,
    descripcion: str,
    unidad: str,
    rendimiento: str,
    materiales: tuple[LineaMaterial, ...],
    mano_obra: tuple[LineaManoObra, ...],
    equipos: tuple[LineaEquipo, ...] = _HERRAMIENTAS,
) -> tuple[str, ComposicionAPU]:
    return codigo, ComposicionAPU(
        codigo,
        descripcion,
        unidad,
        Decimal(rendimiento),
        materiales=materiales,
        equipos=equipos,
        mano_obra=mano_obra,
    )


def _canalizacion(
    codigo: str, texto: str, diametro: str, tubo: str, accesorios: tuple[LineaMaterial, ...]
) -> tuple[str, ComposicionAPU]:
    return _apu(
        codigo,
        f"Suministro e instalacion de tuberia EMT {diametro} pulg a la vista con accesorios "
        f"({texto})",
        "m",
        "20",
        (_m(tubo, "1"), *accesorios),
        _CUADRILLA_ELECTRICA,
        (_e("dobladora"), _e("taladro"), _e("escalera"), _e("herramientas")),
    )


_ACCESORIOS_34 = (
    _m("anillo34", "0.3333"),
    _m("conector34", "0.35"),
    _m("curva34", "0.35"),
    _m("abraz34", "0.50"),
)
_ACCESORIOS_12 = (_m("anillo12", "0.3333"), _m("conector12", "0.35"), _m("curva12", "0.35"))

#: Una composición por cada partida que derivan agua, datos y electricidad (ver `PARTIDAS`).
COMPOSICIONES: dict[str, ComposicionAPU] = dict(
    [
        # --- agua fría ---
        _apu(
            "AF-TUB-PVC-1/2",
            "Suministro e instalacion de tuberia PVC 1/2 pulg de agua fria",
            "m",
            "30",
            (_m("pvc12", "1"), _m("pegamento", "0.01")),
            _CUADRILLA_PLOMERIA,
        ),
        _apu(
            "AF-TUB-PVC-3/4",
            "Suministro e instalacion de tuberia PVC 3/4 pulg de agua fria",
            "m",
            "30",
            (_m("pvc34", "1"), _m("pegamento", "0.015")),
            _CUADRILLA_PLOMERIA,
        ),
        _apu(
            "AF-CODO-1/2",
            "Codo PVC 90 grados 1/2 pulg de agua fria instalado",
            "u",
            "40",
            (_m("codo12", "1"), _m("pegamento", "0.005")),
            _CUADRILLA_PLOMERIA,
        ),
        _apu(
            "AF-CODO-3/4",
            "Codo PVC 90 grados 3/4 pulg de agua fria instalado",
            "u",
            "40",
            (_m("codo34", "1"), _m("pegamento", "0.005")),
            _CUADRILLA_PLOMERIA,
        ),
        _apu(
            "AF-TEE-3/4",
            "Tee PVC 3/4 pulg de agua fria instalada",
            "u",
            "30",
            (_m("tee34", "1"), _m("pegamento", "0.008")),
            _CUADRILLA_PLOMERIA,
        ),
        _apu(
            "AF-LLAVE",
            "Llave de paso de agua fria instalada",
            "u",
            "20",
            (_m("llave12", "1"),),
            _CUADRILLA_PLOMERIA,
        ),
        _apu(
            "AF-PICADO-PARED",
            "Picado y resane de pared para tuberia de agua fria",
            "m",
            "10",
            (_m("cemento", "0.02"), _m("arena", "0.01")),
            _CUADRILLA_ALBANILERIA,
        ),
        _apu(
            "AF-SALIDA",
            "Salida de agua fria terminada",
            "u",
            "12",
            (_m("adaptador12", "1"), _m("pegamento", "0.01")),
            _CUADRILLA_PLOMERIA,
        ),
        # --- drenaje ---
        _apu(
            "DR-TUB-PVC-2",
            "Suministro e instalacion de tuberia PVC 2 pulg de drenaje",
            "m",
            "25",
            (_m("dr2", "1"), _m("pegamento", "0.02")),
            _CUADRILLA_PLOMERIA,
        ),
        _apu(
            "DR-TUB-PVC-1-1/2",
            "Suministro e instalacion de tuberia PVC 1 1/2 pulg de drenaje",
            "m",
            "25",
            (_m("dr112", "1"), _m("pegamento", "0.02")),
            _CUADRILLA_PLOMERIA,
        ),
        _apu(
            "DR-CODO-2",
            "Codo PVC 90 grados 2 pulg de drenaje instalado",
            "u",
            "30",
            (_m("codo2", "1"), _m("pegamento", "0.01")),
            _CUADRILLA_PLOMERIA,
        ),
        _apu(
            "DR-CODO-1-1/2",
            "Codo PVC 90 grados 1 1/2 pulg de drenaje instalado",
            "u",
            "30",
            (_m("codo112", "1"), _m("pegamento", "0.01")),
            _CUADRILLA_PLOMERIA,
        ),
        _apu(
            "DR-PICADO-PISO",
            "Picado y resane de piso para tuberia de drenaje",
            "m",
            "8",
            (_m("cemento", "0.03"), _m("arena", "0.015")),
            _CUADRILLA_ALBANILERIA,
        ),
        _apu(
            "DR-PICADO-PARED",
            "Picado y resane de pared para tuberia de drenaje",
            "m",
            "10",
            (_m("cemento", "0.02"), _m("arena", "0.01")),
            _CUADRILLA_ALBANILERIA,
        ),
        _apu(
            "DR-SALIDA",
            "Salida de drenaje terminada con sifon",
            "u",
            "10",
            (_m("sifon", "1"), _m("pegamento", "0.01")),
            _CUADRILLA_PLOMERIA,
        ),
        # --- datos ---
        _apu(
            "DT-UTP-CAT-6",
            "Suministro y tendido de cable UTP cat 6 por tuberia",
            "m",
            "150",
            (_m("utp", "1"), _m("tirrap", "0.5")),
            _CUADRILLA_ELECTRICA,
            (_e("escalera"), _e("herramientas")),
        ),
        _canalizacion("DT-CAN-EMT-3/4", "datos", "3/4", "emt34", _ACCESORIOS_34),
        _canalizacion("DT-CAN-EMT-1/2", "datos", "1/2", "emt12", _ACCESORIOS_12),
        _apu(
            "DT-CAJA",
            "Caja cuadrada metalica 4x4 pulg para salida de datos instalada",
            "pieza",
            "20",
            (_m("cajetin", "1"),),
            _CUADRILLA_ELECTRICA,
            (_e("taladro"), _e("herramientas")),
        ),
        _apu(
            "DT-FACEPLATE",
            "Face plate para toma de red instalado",
            "pieza",
            "40",
            (_m("faceplate", "1"),),
            (_o("electricista", "1"),),
        ),
        _apu(
            "DT-JACK",
            "Jack RJ45 cat 6 conectorizado",
            "pieza",
            "40",
            (_m("jack", "1"),),
            (_o("electricista", "1"),),
            (_e("ponchadora"), _e("herramientas")),
        ),
        _apu(
            "DT-CERT",
            "Terminacion, etiquetado y certificacion de enlace permanente cat 6",
            "punto",
            "12",
            (_m("pc05", "1"), _m("etiqueta", "2")),
            (_o("tecnico", "1"), _o("ayudante", "1")),
            (_e("certificador"), _e("ponchadora"), _e("herramientas")),
        ),
        # --- electricidad ---
        _apu(
            "EL-COND-12-AWG",
            "Conductor 12 AWG de cobre THW en tuberia",
            "m",
            "120",
            (_m("cable12", "1"),),
            _CUADRILLA_ELECTRICA,
        ),
        _apu(
            "EL-COND-14-AWG",
            "Conductor 14 AWG de cobre THW en tuberia",
            "m",
            "120",
            (_m("cable14", "1"),),
            _CUADRILLA_ELECTRICA,
        ),
        _canalizacion("EL-TUB-EMT-3/4", "electrica", "3/4", "emt34", _ACCESORIOS_34),
        _canalizacion("EL-TUB-EMT-1/2", "electrica", "1/2", "emt12", _ACCESORIOS_12),
        _apu(
            "EL-CAJA",
            "Caja cuadrada metalica 4x4 pulg para salida electrica instalada",
            "pieza",
            "20",
            (_m("cajetin", "1"),),
            _CUADRILLA_ELECTRICA,
            (_e("taladro"), _e("herramientas")),
        ),
        _apu(
            "EL-SALIDA-TOMA",
            "Salida de tomacorriente doble terminada",
            "punto",
            "10",
            (_m("toma", "1"), _m("tapatoma", "1")),
            _CUADRILLA_ELECTRICA,
        ),
        _apu(
            "EL-SALIDA-ILUM",
            "Salida de iluminacion terminada con aplique y bombillo",
            "punto",
            "8",
            (_m("aplique", "1"), _m("bombillo", "1")),
            _CUADRILLA_ELECTRICA,
        ),
        _apu(
            "EL-PROT",
            "Breaker de 1 polo x 20 A instalado en el tablero",
            "pieza",
            "20",
            (_m("breaker", "1"),),
            _CUADRILLA_ELECTRICA,
        ),
    ]
)

#: Las partidas que deriva la oficina completa (de `of001.md`): una composición por cada una.
PARTIDAS: tuple[str, ...] = tuple(sorted(COMPOSICIONES))


def espacio():
    """La oficina completa como `Espacio` (datos de `of001.md`)."""
    return espacio_of001()
