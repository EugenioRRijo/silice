"""Caso OF-001 completo (tarea 2.5): derivar + elaborar contra la memoria `of001.md`.

OF-001 es una oficina construida para el proyecto (NORMAS.md §1) con las tres especialidades en el
mismo espacio y precios MaPreX de julio de 2026. Las cantidades salen de la memoria a mano (no de la
expresion de ninguna regla) y el informe da el CONJUNTO EXACTO de hallazgos esperado: no «cero
hallazgos», porque todas las filas citan un origen de medida que es un supuesto (R8 ADVERTENCIA).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from adapters.espacio import Coord, derivar
from core.contracts import Severidad
from tests.fixtures import caso_of001 as caso
from tests.fixtures.caso_ti001 import TASA
from ui import hoja

MEMORIAS = Path(__file__).resolve().parents[1] / "fixtures" / "memorias"
TOLERANCIA = Decimal("0.001")
D = Decimal

#: Clave de partida de la memoria -> codigo de partida del caso (el unico puente entre ambos).
CODIGO_DE_PARTIDA = {
    "agua": {
        "af_tuberia_3/4": "AF-TUB-PVC-3/4",
        "af_tuberia_1/2": "AF-TUB-PVC-1/2",
        "af_codo_3/4": "AF-CODO-3/4",
        "af_codo_1/2": "AF-CODO-1/2",
        "af_tee_3/4": "AF-TEE-3/4",
        "af_llave_de_paso": "AF-LLAVE",
        "af_picado_pared": "AF-PICADO-PARED",
        "af_salida": "AF-SALIDA",
        "dr_tuberia_2": "DR-TUB-PVC-2",
        "dr_tuberia_1 1/2": "DR-TUB-PVC-1-1/2",
        "dr_codo_2": "DR-CODO-2",
        "dr_codo_1 1/2": "DR-CODO-1-1/2",
        "dr_picado_piso": "DR-PICADO-PISO",
        "dr_picado_pared": "DR-PICADO-PARED",
        "dr_salida": "DR-SALIDA",
    },
    "datos": {
        "cable_cat_6": "DT-UTP-CAT-6",
        "canalizacion_3/4": "DT-CAN-EMT-3/4",
        "canalizacion_1/2": "DT-CAN-EMT-1/2",
        "caja": "DT-CAJA",
        "faceplate": "DT-FACEPLATE",
        "jack": "DT-JACK",
        "certificacion": "DT-CERT",
    },
    "electricidad": {
        "conductor_12 AWG": "EL-COND-12-AWG",
        "conductor_14 AWG": "EL-COND-14-AWG",
        "tuberia_3/4": "EL-TUB-EMT-3/4",
        "tuberia_1/2": "EL-TUB-EMT-1/2",
        "caja": "EL-CAJA",
        "salida_tomacorriente": "EL-SALIDA-TOMA",
        "salida_iluminacion": "EL-SALIDA-ILUM",
        "proteccion": "EL-PROT",
    },
}

#: Las filas del espacio que producen cantidad, escritas a mano desde la memoria (seccion 1).
AMBIENTES = ("BAN-01", "COC-01", "REC-01", "CT-01", "ZA", "ZB")
FUENTES = ("F1", "FD1", "FC1", "FDC1", "RK1", "T1")
PUNTOS = (
    ("P1", "P2", "D1", "D2", "PC1", "DC1")
    + ("PA1", "PA2", "PA3", "PB1", "PB2", "PB3", "PR1")
    + ("TA1", "TA2", "TB1", "TB2", "LZ1", "LZ2", "LZ3", "LZ4")
)
FILAS = (
    tuple(f"esp_ambientes:{i}" for i in AMBIENTES)
    + tuple(f"esp_fuentes:{i}" for i in FUENTES)
    + tuple(f"esp_puntos:{i}" for i in PUNTOS)
)


@pytest.fixture(scope="module")
def memoria() -> dict:
    texto = (MEMORIAS / "of001.md").read_text(encoding="utf-8")
    return json.loads(re.findall(r"```json\n(.*?)\n```", texto, flags=re.DOTALL)[0])


def _elaborar(espacio=None):
    return hoja.elaborar_hoja(
        espacio or caso.espacio(),
        caso.COMPOSICIONES,
        codigo=caso.CODIGO,
        fecha=caso.FECHA,
        especialidad=hoja.TODAS,
        parametros=caso.PARAMETROS,
        moneda=caso.MONEDA,
    )


@pytest.fixture(scope="module")
def resultado():
    return _elaborar()


def _claves(hallazgos) -> Counter:
    return Counter((h.regla, h.severidad, h.origen_ids) for h in hallazgos)


# --- cantidades -------------------------------------------------------------------------------


def test_derivar_las_tres_especialidades_da_las_cantidades_de_la_memoria(memoria: dict) -> None:
    derivadas = {
        i.codigo_partida: i
        for especialidad in ("agua", "datos", "electricidad")
        for i in derivar(caso.espacio(), especialidad)
    }
    esperadas = {}
    for especialidad, claves in CODIGO_DE_PARTIDA.items():
        for p in memoria[especialidad]["partidas"]:
            esperadas[claves[p["partida"]]] = D(p["cantidad"])
    assert set(derivadas) == set(esperadas) == set(caso.PARTIDAS)
    for codigo, cantidad in esperadas.items():
        assert abs(derivadas[codigo].cantidad - cantidad) <= TOLERANCIA, codigo


def test_el_presupuesto_tiene_esas_cantidades_y_ninguna_partida_pendiente(
    resultado, memoria: dict
) -> None:
    assert resultado.elaboracion.pendientes == ()
    en_presupuesto = {
        p.item.codigo_partida: p.item.cantidad for p in resultado.elaboracion.presupuesto.partidas
    }
    assert set(en_presupuesto) == set(caso.PARTIDAS)
    for especialidad, claves in CODIGO_DE_PARTIDA.items():
        for p in memoria[especialidad]["partidas"]:
            codigo = claves[p["partida"]]
            assert abs(en_presupuesto[codigo] - D(p["cantidad"])) <= TOLERANCIA, codigo


def test_hoja_deriva_las_tres_especialidades_juntas_y_ordenadas(resultado) -> None:
    codigos = [i.codigo_partida for i in resultado.items]
    assert set(codigos) == set(caso.PARTIDAS)
    prefijos = {c.split("-")[0] for c in codigos}
    assert prefijos == {"AF", "DR", "DT", "EL"}
    assert len(codigos) == len(set(codigos))


# --- el conjunto exacto de hallazgos -------------------------------------------------------------


def test_of001_limpia_da_el_conjunto_exacto_de_hallazgos(resultado) -> None:
    """Un hallazgo R8 ADVERTENCIA por cada fila con origen supuesto (33 filas) y nada mas: ni un
    ERROR, ni R9, ni R10, ni R1 a R7."""
    informe = resultado.elaboracion.informe
    esperado = Counter({("R8", Severidad.ADVERTENCIA, (fila,)): 1 for fila in FILAS})
    assert _claves(informe.hallazgos) == esperado
    assert len(FILAS) == 33
    assert informe.cumple  # advertencias, sin errores
    for h in informe.hallazgos:
        assert "supuesto declarado" in h.descripcion


def test_el_informe_declara_las_once_reglas(resultado) -> None:
    """R1 a R10 y, desde la 0.8.0, R15 (coherencia geométrica del plano; no da hallazgos)."""
    reglas = [codigo for codigo, _ in resultado.elaboracion.informe.reglas_evaluadas]
    assert reglas == [*(f"R{i}" for i in range(1, 11)), "R15"]


def test_el_estado_de_cada_fila_es_su_advertencia_de_origen(resultado) -> None:
    assert set(resultado.estado) == set(FILAS)
    for fila, estado in resultado.estado.items():
        assert estado.severidad is Severidad.ADVERTENCIA, fila
        assert estado.texto.startswith("ADVERTENCIA: "), fila
        assert "la medida es un supuesto declarado" in estado.texto, fila


# --- siembras ---------------------------------------------------------------------------------


def test_un_punto_fuera_de_su_ambiente_da_un_error_de_r9_en_su_fila() -> None:
    base = caso.espacio()
    fuera = replace(
        base,
        puntos=tuple(
            replace(p, posicion=Coord(D("7"), p.posicion.y, p.posicion.z)) if p.id == "PA1" else p
            for p in base.puntos
        ),
    )
    r = _elaborar(fuera)
    informe = r.elaboracion.informe
    nuevos = _claves(informe.hallazgos) - _claves(_elaborar().elaboracion.informe.hallazgos)
    assert nuevos == Counter({("R9", Severidad.ERROR, ("esp_puntos:PA1",)): 1})
    assert not informe.cumple
    assert r.estado["esp_puntos:PA1"].severidad is Severidad.ERROR
    assert r.estado["esp_puntos:PA2"].severidad is Severidad.ADVERTENCIA  # solo la fila sembrada


def test_un_circuito_con_mas_puntos_que_su_maximo_da_r10_advertencia() -> None:
    base = caso.espacio()
    estrecho = replace(
        base,
        circuitos=tuple(
            replace(c, puntos_maximos=3) if c.id == "C2" else c for c in base.circuitos
        ),
    )
    r = _elaborar(estrecho)
    nuevos = _claves(r.elaboracion.informe.hallazgos) - _claves(
        _elaborar().elaboracion.informe.hallazgos
    )
    assert nuevos == Counter(
        {
            (
                "R10",
                Severidad.ADVERTENCIA,
                (
                    "esp_circuitos:C2",
                    "esp_puntos:LZ1",
                    "esp_puntos:LZ2",
                    "esp_puntos:LZ3",
                    "esp_puntos:LZ4",
                ),
            ): 1
        }
    )
    assert r.elaboracion.informe.cumple  # una advertencia no impide cumplir
    for id_ in ("LZ1", "LZ2", "LZ3", "LZ4"):  # el Estado marca las filas de sus puntos
        assert "circuito C2" in r.estado[f"esp_puntos:{id_}"].texto
    assert "circuito C2" not in r.estado["esp_puntos:TA1"].texto


# --- precios ----------------------------------------------------------------------------------


def _usd(bolivares: str) -> Decimal:
    return (D(bolivares) / TASA).quantize(D("0.0001"), rounding=ROUND_HALF_UP)


def test_el_precio_unitario_de_dos_partidas_coincide_con_el_calculo_a_mano(resultado) -> None:
    """Calculo independiente de NORMAS.md §4 desde los Bs de MaPreX (sin el motor)."""
    fcas, bono = D("6.00"), _usd("3679.85")
    adm, util = D("0.15"), D("0.10")

    def pu(materiales: D, equipos: D, sueldos: list[str], rendimiento: str) -> Decimal:
        r = D(rendimiento)
        mano = (sum((_usd(s) for s in sueldos), D(0)) * (1 + fcas) + bono * len(sueldos)) / r
        directo = materiales + equipos / r + mano
        return directo * (1 + adm) * (1 + util)

    por_codigo = {p.item.codigo_partida: p for p in resultado.elaboracion.presupuesto.partidas}
    # DT-JACK: 1 jack [ELC065] 1 510,00 Bs; ponchadora [ELE047] 13 937,30 Bs x 0,007 y herramientas
    # menores [ALB213] 9 060,00 Bs x 1; 1 electricista de 1ra N5 [19-215] 1 385,63 Bs; rend. 40
    jack = pu(
        _usd("1510.00"),
        _usd("13937.30") * D("0.007") + _usd("9060.00"),
        ["1385.63"],
        "40",
    )
    assert abs(por_codigo["DT-JACK"].resultado.precio_unitario - jack) <= D("0.01")
    # EL-PROT: 1 breaker 1P x 20 A [ELE987] 63 420,00 Bs; herramientas menores; electricista y
    # ayudante N2 [1-1.2] 1 128,42 Bs; rend. 20
    prot = pu(
        _usd("63420.00"),
        _usd("9060.00"),
        ["1385.63", "1128.42"],
        "20",
    )
    assert abs(por_codigo["EL-PROT"].resultado.precio_unitario - prot) <= D("0.01")


def test_cada_insumo_cita_su_ref_de_maprex_y_los_proxies_estan_declarados() -> None:
    for clave, insumo in caso.INSUMOS.items():
        assert insumo.ref.strip(), clave
        assert insumo.precio > 0, clave
        assert f"[{insumo.ref}]" in insumo.etiqueta, clave
    proxies = [c for c, i in caso.INSUMOS.items() if "proxy supuesto" in i.descripcion]
    assert sorted(proxies) == ["codo112", "dr112"]


def _bs_por_etiqueta() -> dict[str, str]:
    """Etiqueta (con su Ref) -> precio en Bs tal como aparece en MaPreX."""
    return {i.etiqueta: i.precio_bs for i in caso.INSUMOS.values()}


def _pu_a_mano(comp, bs: dict[str, str]) -> Decimal:
    """PU de NORMAS.md §4 desde los Bs de MaPreX, linea por linea (sin el motor)."""
    fcas, adm, util = D("6.00"), D("0.15"), D("0.10")
    bono = _usd("3679.85")
    materiales = sum((m.cantidad * _usd(bs[m.descripcion]) for m in comp.materiales), D(0))
    equipos = sum(
        (e.cantidad * _usd(bs[e.descripcion]) * e.depreciacion for e in comp.equipos), D(0)
    )
    mano = sum(
        (o.cantidad * (_usd(bs[o.descripcion]) * (1 + fcas) + bono) for o in comp.mano_obra), D(0)
    )
    directo = materiales + (equipos + mano) / comp.rendimiento
    return directo * (1 + adm) * (1 + util)


def test_el_total_de_of001_se_calcula_a_mano_partida_por_partida(memoria: dict, resultado) -> None:
    """Total = suma de cantidad de la memoria x PU a mano, partida por partida (30 partidas)."""
    bs = _bs_por_etiqueta()
    por_codigo = {p.item.codigo_partida: p for p in resultado.elaboracion.presupuesto.partidas}
    total_a_mano = D(0)
    cantidades = 0
    for especialidad, claves in CODIGO_DE_PARTIDA.items():
        for p in memoria[especialidad]["partidas"]:
            codigo = claves[p["partida"]]
            cantidad = D(p["cantidad"])
            pu = _pu_a_mano(caso.COMPOSICIONES[codigo], bs)
            assert abs(por_codigo[codigo].resultado.precio_unitario - pu) <= D("0.01"), codigo
            total_a_mano += cantidad * pu
            cantidades += 1
    assert cantidades == len(caso.PARTIDAS) == 30
    total = resultado.elaboracion.presupuesto.total
    assert abs(total - total_a_mano) <= D("0.01"), (total, total_a_mano)
    # cifra fijada contra ese calculo a mano (no contra la salida del motor)
    assert abs(total_a_mano - D("2703.86")) <= D("0.01"), total_a_mano
