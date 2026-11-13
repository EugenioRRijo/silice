"""Libro por frentes (ola 2, línea 3, 2026-11-13): el perfil y el lector del libro con un APU por
hoja después de la prueba local del libro vial real (`docs/bitacora/2026-11-13-libro-vial-real-
local.md` §3). Decisiones simuladas en `docs/bitacora/2026-11-13-ola2-libro-por-frentes.md`.

1. Un perfil con **varias hojas de presupuesto** (`presupuesto.hojas`, una por frente): cada
   renglón se enlaza con su APU por el número en cada hoja; el precio se compara hoja por hoja y la
   cantidad del APU con la **suma** de las hojas (D1).
2. Una **segunda fila de impuesto** (`porcentajes.otros_impuestos`) se suma al impuesto (D2).
3. Las hojas del libro de APU que **no siguen el prefijo** del perfil se dicen en un AH12 (INFO),
   sin leerlas (D3).
4. La **hoja del presupuesto se elige aparte del perfil** (`hojas=`), y una que no está se rechaza
   diciendo las que hay (D4).
5. **Poner un perfil local** (`instalar_perfil_apu_por_hoja`): se valida antes de escribirlo y no
   pisa uno que ya está sin `reemplazar` (D5).

Libros FICTICIOS de `tests/fixtures/libro_apu_por_hoja.py`; los oráculos salen de su memoria de
cálculo (a mano): FRENTE A lleva el 60 % de cada cantidad y FRENTE B el 40 %, así que la suma es la
del presupuesto de siempre (el renglón 3 suma 450 y su APU dice 500).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.hoja_empresa import perfil_apu_por_hoja as modulo_perfil
from adapters.hoja_empresa.guardia import ArchivoRechazado
from adapters.hoja_empresa.lector_apu_por_hoja import leer_libro_apu_por_hoja
from adapters.hoja_empresa.perfil import PerfilInvalido
from adapters.hoja_empresa.perfil_apu_por_hoja import (
    VARIABLE_PERFILES,
    cargar_perfil_apu_por_hoja,
    perfiles_apu_por_hoja,
)
from fusion.apu_por_hoja import auditar_apu_por_hoja
from tests.fixtures.libro_apu_por_hoja import (
    APUS,
    RENGLONES,
    libro_apu,
    libro_presupuesto,
    libro_presupuesto_por_hojas,
)

D = Decimal
PAQUETE = Path(__file__).resolve().parents[2] / "adapters/hoja_empresa/perfiles/apu_por_hoja.json"


@pytest.fixture(autouse=True)
def _sin_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VARIABLE_PERFILES, raising=False)


def _crudo(**cambios) -> dict:
    crudo = json.loads(PAQUETE.read_text(encoding="utf-8"))
    crudo.update(cambios)
    return crudo


def _escribir(carpeta: Path, crudo: dict) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / f"{crudo['nombre']}.json").write_text(json.dumps(crudo), encoding="utf-8")


def _por_frentes(carpeta: Path, nombre: str = "por_frentes") -> str:
    crudo = _crudo(nombre=nombre)
    crudo["presupuesto"] = {
        "hojas": ["FRENTE A", "FRENTE B"],
        "encabezado": crudo["presupuesto"]["encabezado"],
    }
    _escribir(carpeta, crudo)
    return nombre


def _resumen(resultado) -> list[tuple[str, str, str]]:
    return [(h.codigo, h.severidad, h.celda) for h in resultado.hallazgos]


# --- 1. Varias hojas de presupuesto ---------------------------------------------------------------


def test_el_perfil_admite_varias_hojas_de_presupuesto(tmp_path: Path):
    nombre = _por_frentes(tmp_path)
    perfil = cargar_perfil_apu_por_hoja(nombre, (tmp_path,))
    assert perfil.hojas_presupuesto == ("FRENTE A", "FRENTE B")
    assert perfil.hoja_presupuesto == "FRENTE A"  # la primera, para quien solo mira una


def test_el_perfil_de_una_hoja_sigue_igual():
    perfil = cargar_perfil_apu_por_hoja("apu_por_hoja", ())
    assert perfil.hojas_presupuesto == ("PRESUPUESTO",)
    assert perfil.hoja_presupuesto == "PRESUPUESTO"


@pytest.mark.parametrize(
    ("presupuesto", "dice"),
    [
        ({"hoja": "A", "hojas": ["A"]}, "presupuesto: declare «hoja» o «hojas», no las dos"),
        ({"hojas": []}, "presupuesto.hojas debe ser una lista no vacía de textos"),
        ({"hojas": ["A", "a"]}, "presupuesto.hojas: la hoja «a» está repetida"),
        ({}, "presupuesto: falta «hoja» u «hojas»"),
    ],
)
def test_las_hojas_mal_declaradas_rechazan_el_perfil(tmp_path: Path, presupuesto, dice):
    crudo = _crudo(nombre="malo")
    crudo["presupuesto"] = {**presupuesto, "encabezado": crudo["presupuesto"]["encabezado"]}
    _escribir(tmp_path, crudo)
    with pytest.raises(PerfilInvalido) as error:
        cargar_perfil_apu_por_hoja("malo", (tmp_path,))
    assert str(error.value) == f"perfil 'malo': {dice}"


def test_la_lista_de_perfiles_dice_todas_las_hojas(tmp_path: Path):
    _por_frentes(tmp_path)
    disponibles = {p.nombre: p for p in perfiles_apu_por_hoja((tmp_path,))}
    assert disponibles["por_frentes"].hojas_presupuesto == ("FRENTE A", "FRENTE B")
    assert disponibles["apu_por_hoja"].hojas_presupuesto == ("PRESUPUESTO",)


def _auditar_por_frentes(carpeta: Path, presupuesto: bytes | None = None, **extra):
    return auditar_apu_por_hoja(
        libro_apu(),
        "obra_a.xlsx",
        presupuesto=libro_presupuesto_por_hojas() if presupuesto is None else presupuesto,
        presupuesto_nombre="presupuesto_frentes.xlsx",
        perfil=extra.pop("perfil", None) or _por_frentes(carpeta),
        carpeta_perfiles=carpeta,
        **extra,
    )


def test_con_dos_frentes_el_precio_se_compara_por_hoja_y_la_cantidad_con_la_suma(tmp_path: Path):
    """D1: 60 % + 40 % suman la cantidad de cada APU, salvo el renglón 3 (450 frente a 500): un
    solo AH6, en la primera hoja; el P.U. del renglón 5 y el renglón 6 sin APU, en cada hoja."""
    resultado = _auditar_por_frentes(tmp_path)
    assert resultado.hojas_presupuesto == ("FRENTE A", "FRENTE B")
    assert resultado.hoja_presupuesto == "FRENTE A"
    del_presupuesto = [r for r in _resumen(resultado) if r[2].startswith("FRENTE ")]
    assert del_presupuesto == [
        ("AH6", "ADVERTENCIA", "FRENTE A!E6"),
        ("AH5", "ERROR", "FRENTE A!F8"),
        ("AH7", "ADVERTENCIA", "FRENTE A!A9"),
        ("AH5", "ERROR", "FRENTE B!F8"),
        ("AH7", "ADVERTENCIA", "FRENTE B!A9"),
    ]
    ah6 = next(h for h in resultado.hallazgos if h.codigo == "AH6")
    assert ah6.descripcion == (
        "Renglón 3 (VF-003): las hojas FRENTE A y FRENTE B del presupuesto suman una cantidad de "
        "450 y su APU (APU 3!D5) dice 500."
    )
    ah5_b = next(h for h in resultado.hallazgos if h.celda == "FRENTE B!F8")
    assert ah5_b.descripcion == (
        "Renglón 5 (VF-005), hoja FRENTE B: el presupuesto dice un precio unitario de 0,25 y su "
        "APU (APU 5!G28) imprime 0,20."
    )


def test_los_renglones_de_cada_frente_quedan_en_el_resultado(tmp_path: Path):
    """Lo que necesita llevar el libro a la Hoja: cada renglón con su hoja, su número y su
    cantidad (FRENTE A, renglón 1: 60 % de 1.000 = 600)."""
    resultado = _auditar_por_frentes(tmp_path)
    primeros = [(r.hoja, r.numero, r.cantidad) for r in resultado.renglones[:2]]
    assert primeros == [("FRENTE A", 1, D(600)), ("FRENTE A", 2, D(72))]
    assert len(resultado.renglones) == 12  # 6 renglones por hoja
    assert resultado.renglones[6].hoja == "FRENTE B"
    assert resultado.renglones[0].celda_cantidad == "FRENTE A!E4"


def test_dos_frentes_de_otra_obra_se_avisan_con_la_suma(tmp_path: Path):
    """AH11 con varias hojas juzga la suma: aquí FRENTE B repite las cantidades de A y la suma es
    el 120 % de cada APU (ninguno casa)."""
    mitad = tuple(
        (n, c, d, u, str((D(q) * D("0.6")).normalize()), p) for n, c, d, u, q, p in RENGLONES
    )
    resultado = _auditar_por_frentes(
        tmp_path, libro_presupuesto_por_hojas({"FRENTE A": mitad, "FRENTE B": mitad})
    )
    ah11 = [h for h in resultado.hallazgos if h.codigo == "AH11"]
    assert [h.celda for h in ah11] == ["FRENTE A!E3"]
    assert ah11[0].descripcion == (
        "Las hojas FRENTE A y FRENTE B del presupuesto parecen de otra obra: de 5 renglones "
        "enlazados con su APU, ninguno suma la misma cantidad. Revise el perfil o las hojas "
        "elegidas: se leyeron FRENTE A y FRENTE B."
    )


# --- 4. La hoja del presupuesto se elige aparte del perfil ----------------------------------------


def test_la_hoja_elegida_manda_sobre_la_del_perfil(tmp_path: Path):
    """El perfil del paquete lee PRESUPUESTO; aquí se elige FRENTE B y el informe lo dice."""
    resultado = _auditar_por_frentes(tmp_path, perfil="apu_por_hoja", hojas=("FRENTE B",))
    assert resultado.hojas_presupuesto == ("FRENTE B",)
    assert {r.hoja for r in resultado.renglones} == {"FRENTE B"}


def test_una_hoja_elegida_que_no_esta_dice_las_que_hay(tmp_path: Path):
    with pytest.raises(ArchivoRechazado) as error:
        _auditar_por_frentes(tmp_path, perfil="apu_por_hoja", hojas=("FRENTE C",))
    assert str(error.value) == (
        "El libro «presupuesto_frentes.xlsx» no tiene la hoja FRENTE C: sus hojas son FRENTE A y "
        "FRENTE B."
    )


def test_la_hoja_se_busca_sin_mayusculas_ni_espacios_de_mas(tmp_path: Path):
    resultado = _auditar_por_frentes(tmp_path, perfil="apu_por_hoja", hojas=("frente  b",))
    assert resultado.hojas_presupuesto == ("FRENTE B",)


def test_sin_presupuesto_las_hojas_elegidas_no_importan():
    resultado = auditar_apu_por_hoja(libro_apu(), "obra.xlsx", hojas=("NO ESTA",))
    assert resultado.hojas_presupuesto == ()
    assert resultado.renglones == ()


def test_con_una_hoja_los_mensajes_no_cambian():
    resultado = auditar_apu_por_hoja(
        libro_apu(), "f.xlsx", presupuesto=libro_presupuesto(), presupuesto_nombre="p.xlsx"
    )
    assert resultado.hojas_presupuesto == ("PRESUPUESTO",)
    ah5 = next(h for h in resultado.hallazgos if h.codigo == "AH5")
    assert ah5.descripcion == (
        "Renglón 5 (VF-005): el presupuesto dice un precio unitario de 0,25 y su APU (APU 5!G28) "
        "imprime 0,20."
    )


# --- 2. La segunda fila de impuesto ---------------------------------------------------------------


def _con_otros_impuestos(carpeta: Path) -> str:
    crudo = _crudo(nombre="con_otros")
    crudo["porcentajes"] = {**crudo["porcentajes"], "otros_impuestos": ["Otros impuestos"]}
    _escribir(carpeta, crudo)
    return "con_otros"


def _libro_con_otros() -> bytes:
    from dataclasses import replace

    quinto = replace(APUS[4], otros_impuestos="2")
    return libro_apu((*APUS[:4], quinto))


def test_la_segunda_fila_de_impuesto_se_suma(tmp_path: Path):
    """APU 5: impuesto 16 % y otros impuestos 2 %: 18 % (0,18 como fracción), con la celda de
    cada uno."""
    perfil = cargar_perfil_apu_por_hoja(_con_otros_impuestos(tmp_path), (tmp_path,))
    quinto = leer_libro_apu_por_hoja(_libro_con_otros(), "f.xlsx", perfil).apus[4]
    assert quinto.impuesto == D("0.18")
    assert (quinto.celdas["impuesto"].ref, quinto.celdas["otros_impuestos"].ref) == ("F27", "F28")


def test_sin_declararla_la_segunda_fila_no_se_lee(tmp_path: Path):
    quinto = leer_libro_apu_por_hoja(
        _libro_con_otros(), "f.xlsx", cargar_perfil_apu_por_hoja("apu_por_hoja", ())
    ).apus[4]
    assert quinto.impuesto == D("0.16")


def test_el_ah4_dice_los_dos_impuestos(tmp_path: Path):
    resultado = auditar_apu_por_hoja(
        _libro_con_otros(),
        "f.xlsx",
        perfil=_con_otros_impuestos(tmp_path),
        carpeta_perfiles=tmp_path,
    )
    ah4 = next(h for h in resultado.hallazgos if h.codigo == "AH4")
    assert ah4.descripcion == (
        "APU 5 (VF-005): el APU suma un impuesto del 18 % (16 % y otros impuestos del 2 %); el IVA "
        "va sobre el total del presupuesto y contarlo también aquí lo cobraría dos veces."
    )


def test_otra_clave_de_porcentaje_sigue_rechazada(tmp_path: Path):
    crudo = _crudo(nombre="raro")
    crudo["porcentajes"] = {**crudo["porcentajes"], "propina": ["Propina"]}
    _escribir(tmp_path, crudo)
    with pytest.raises(PerfilInvalido, match="no se conocen \\['propina'\\]"):
        cargar_perfil_apu_por_hoja("raro", (tmp_path,))


# --- 3. Las hojas que no siguen el prefijo --------------------------------------------------------


def test_las_hojas_sin_el_prefijo_se_dicen_en_un_ah12():
    resultado = auditar_apu_por_hoja(libro_apu(otras=("Portada", "Partida 6")), "f.xlsx")
    ah12 = [h for h in resultado.hallazgos if h.codigo == "AH12"]
    assert [(h.severidad, h.celda) for h in ah12] == [("INFO", "Portada!A1")]
    assert ah12[0].descripcion == (
        "2 hojas del libro no empiezan por «APU» y no se leyeron como APU: Portada y Partida 6. "
        "Si alguna es un APU, revise el prefijo del perfil."
    )


def test_una_sola_hoja_sin_el_prefijo():
    resultado = auditar_apu_por_hoja(libro_apu(otras=("Resumen",)), "f.xlsx")
    ah12 = next(h for h in resultado.hallazgos if h.codigo == "AH12")
    assert ah12.descripcion == (
        "La hoja Resumen del libro no empieza por «APU» y no se leyó como APU. Si es un APU, "
        "revise el prefijo del perfil."
    )


def test_muchas_hojas_sin_el_prefijo_se_cortan_a_diez():
    otras = tuple(f"Nota {n}" for n in range(1, 13))
    resultado = auditar_apu_por_hoja(libro_apu(otras=otras), "f.xlsx")
    ah12 = next(h for h in resultado.hallazgos if h.codigo == "AH12")
    assert ah12.descripcion == (
        "12 hojas del libro no empiezan por «APU» y no se leyeron como APU: Nota 1, Nota 2, "
        "Nota 3, Nota 4, Nota 5, Nota 6, Nota 7, Nota 8, Nota 9, Nota 10 y 2 más. Si alguna es un "
        "APU, revise el prefijo del perfil."
    )


def test_un_libro_con_todas_sus_hojas_de_apu_no_tiene_ah12():
    assert "AH12" not in {h.codigo for h in auditar_apu_por_hoja(libro_apu(), "f.xlsx").hallazgos}


# --- 5. Poner un perfil local ---------------------------------------------------------------------


def instalar_perfil_apu_por_hoja(*args, **kwargs):
    return modulo_perfil.instalar_perfil_apu_por_hoja(*args, **kwargs)


def _ya_instalado():
    return modulo_perfil.PerfilYaInstalado


def _bytes(crudo: dict) -> bytes:
    return json.dumps(crudo, ensure_ascii=False).encode("utf-8")


def test_instalar_un_perfil_lo_escribe_y_se_puede_elegir(tmp_path: Path):
    carpeta = tmp_path / "perfiles_libros"  # aún no existe: la crea quien instala
    crudo = _crudo(nombre="obra_local")
    instalado = instalar_perfil_apu_por_hoja(_bytes(crudo), carpeta)
    assert (instalado.nombre, instalado.origen, instalado.hojas_presupuesto) == (
        "obra_local",
        "local",
        ("PRESUPUESTO",),
    )
    assert json.loads((carpeta / "obra_local.json").read_text(encoding="utf-8")) == crudo
    assert cargar_perfil_apu_por_hoja("obra_local", (carpeta,)).origen == "local"


def test_instalar_no_pisa_uno_que_ya_esta(tmp_path: Path):
    crudo = _crudo(nombre="obra_local")
    instalar_perfil_apu_por_hoja(_bytes(crudo), tmp_path)
    otro = _crudo(nombre="obra_local", prefijo_hoja="Partida")
    with pytest.raises(_ya_instalado()) as error:
        instalar_perfil_apu_por_hoja(_bytes(otro), tmp_path)
    assert str(error.value) == (
        "Ya hay un perfil «obra_local» en esta instalación: marque «Reemplazar» para cambiarlo."
    )
    assert cargar_perfil_apu_por_hoja("obra_local", (tmp_path,)).prefijo_hoja == "APU"
    instalar_perfil_apu_por_hoja(_bytes(otro), tmp_path, reemplazar=True)
    assert cargar_perfil_apu_por_hoja("obra_local", (tmp_path,)).prefijo_hoja == "Partida"


@pytest.mark.parametrize(
    ("datos", "dice"),
    [
        (b"{no es json", "El archivo no es un JSON legible"),
        (_bytes(["lista"]), "perfil '?': la raíz debe ser un objeto"),
        (_bytes({**_crudo(), "nombre": "../fuera"}), "nombre de perfil no válido: '../fuera'"),
        (_bytes({**_crudo(nombre="otro_tipo"), "tipo": "plantilla"}), "perfil 'otro_tipo': tipo"),
        (_bytes({**_crudo(nombre="sin_prefijo"), "prefijo_hoja": ""}), "prefijo_hoja"),
        (b"x" * (64 * 1024 + 1), "El perfil pasa de 64 KiB"),
    ],
    ids=["no_json", "raiz", "nombre", "tipo", "prefijo", "grande"],
)
def test_instalar_valida_antes_de_escribir(tmp_path: Path, datos: bytes, dice: str):
    with pytest.raises(PerfilInvalido) as error:
        instalar_perfil_apu_por_hoja(datos, tmp_path)
    assert dice in str(error.value)
    assert not any(tmp_path.iterdir())


def test_instalar_respeta_la_variable_de_la_carpeta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Si `SILICE_PERFILES_LIBROS` dice otra carpeta, ahí se lee y ahí se escribe."""
    otra = tmp_path / "otra"
    otra.mkdir()
    monkeypatch.setenv(VARIABLE_PERFILES, str(otra))
    instalar_perfil_apu_por_hoja(_bytes(_crudo(nombre="obra_local")), tmp_path / "datos")
    assert (otra / "obra_local.json").is_file()
    assert not (tmp_path / "datos").exists()
