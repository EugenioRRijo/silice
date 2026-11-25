"""Pruebas unitarias de `scripts/insumos_criticos.py` (insumos críticos ABC y frescura)."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.modelo import TipoInsumo
from scripts import insumos_criticos as ic
from tests.fixtures.libros_empresa import INSUMOS, Siembra, construir_libro, libro_limpio


def test_pesos_libro_limpio_orden_y_valores_a_mano() -> None:
    construido = libro_limpio()
    libro = leer_libro(construido.datos, "limpio.xlsx")
    resultado = ic.pesos(libro)

    # Valores calculados a mano desde APUS_LIMPIOS e INSUMOS:
    # MT-03: 80 * (12,5 * 0,8) = 800
    # MO-02: 120*(1*15/10) + 80*(2*15/8) + 50*(2*15/20) = 180 + 300 + 75 = 555
    # MO-01: 120*(1*20/10) + 80*(1*20/8) = 240 + 200 = 440
    # MT-01: 120*(0,2*10) + 80*(0,1*10) = 240 + 80 = 320
    # MT-02: 120*(0,05*25) + 80*(0,02*25) = 150 + 40 = 190
    # EQ-01: 120*(0,5*30/10) = 180
    # EQ-02: 80*(2*4/8) = 80
    esperado = [
        ("MT-03", Decimal("800")),
        ("MO-02", Decimal("555")),
        ("MO-01", Decimal("440")),
        ("MT-01", Decimal("320")),
        ("MT-02", Decimal("190")),
        ("EQ-01", Decimal("180")),
        ("EQ-02", Decimal("80")),
    ]
    assert [(p.codigo, p.peso) for p in resultado] == esperado
    assert all(p.sin_rendimiento == 0 for p in resultado)


def test_pesos_rendimiento_cero_no_aporta_y_cuenta_sin_rendimiento() -> None:
    base = libro_limpio()
    fila_rend = base.filas_apu["APU-01"].rend
    construido = construir_libro(siembra=Siembra(parches={f"APU-01!F{fila_rend}": (Decimal(0), None)}))
    libro = leer_libro(construido.datos, "sin_rend.xlsx")
    por_codigo = {p.codigo: p for p in ic.pesos(libro)}

    assert por_codigo["MT-01"].peso == Decimal("320")
    assert por_codigo["MT-02"].peso == Decimal("190")
    assert por_codigo["MT-01"].sin_rendimiento == 0
    assert por_codigo["MO-01"].peso == Decimal("200")
    assert por_codigo["MO-01"].sin_rendimiento == 1
    assert por_codigo["MO-02"].peso == Decimal("375")
    assert por_codigo["MO-02"].sin_rendimiento == 1
    assert por_codigo["EQ-01"].peso == Decimal("0")
    assert por_codigo["EQ-01"].sin_rendimiento == 1


def test_abc_clasificacion_y_frontera_80() -> None:
    sinteticos = [
        ic.PesoInsumo(
            codigo=f"MT-{i:02d}",
            descripcion="",
            tipo=TipoInsumo.MATERIAL,
            peso=Decimal(peso),
        )
        for i, peso in enumerate([4, 50, 6, 30, 10], start=1)
    ]
    clasificados = ic.abc(sinteticos)

    assert [c.peso for c in clasificados] == [
        Decimal(50),
        Decimal(30),
        Decimal(10),
        Decimal(6),
        Decimal(4),
    ]
    assert [c.clase for c in clasificados] == ["A", "A", "B", "B", "C"]
    # La frontera exacta del 80 % pertenece a la clase A.
    assert clasificados[1].acumulado == Decimal("80")
    assert clasificados[1].clase == "A"
    assert clasificados[2].clase == "B"


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Cotización 15/07/2026", date(2026, 7, 15)),
        ("Lista 15-07-2026", date(2026, 7, 15)),
        ("Factura 2026-07-15", date(2026, 7, 15)),
        ("MaPreX julio 2026", date(2026, 7, 1)),
        ("Lista jul-2026", date(2026, 7, 1)),
        ("Tabulador Julio de 2026", date(2026, 7, 1)),
        ("POR COTIZAR", None),
        ("", None),
        ("Proveedor X", None),
        ("31/02/2026", None),
    ],
)
def test_fecha_de_fuente(texto: str, esperado: date | None) -> None:
    assert ic.fecha_de_fuente(texto) == esperado


def test_indicadores_frescura_y_regla_sin_fuente(tmp_path: Path) -> None:
    fuentes = {
        "MT-03": "REFERENCIAL — ajustar",
        "MO-02": "Tabulador 15/06/2026",
        "MO-01": "Tabulador ene-2026",
        "MT-01": "Cotización julio 2026",
    }
    insumos = tuple(replace(ins, fuente=fuentes.get(ins.codigo, ins.fuente)) for ins in INSUMOS)
    construido = construir_libro(siembra=Siembra(fecha_texto="31/07/2026", insumos=insumos))
    libro_xlsx = tmp_path / "frescura.xlsx"
    libro_xlsx.write_bytes(construido.datos)

    destino, _ = ic.ejecutar(
        libro_xlsx,
        tmp_path / "salida",
        ventana=90,
        raiz_repo=tmp_path / "repo",
    )
    datos = json.loads(destino.read_text(encoding="utf-8"))
    ind = datos["indicadores"]

    assert ind["insumos_a"] == 4
    assert ind["a_vigentes"] == 2
    assert ind["a_sin_fuente"] == 1
    assert Decimal(ind["porcentaje_costo_a"]) == (
        Decimal("2115") / Decimal("2565") * Decimal(100)
    )

    por_cod = {item["codigo"]: item for item in datos["insumos"]}
    assert por_cod["MT-03"]["vigente"] == "sin_dato"
    assert por_cod["MT-03"]["sin_fuente"] is True
    assert por_cod["MO-02"]["edad_dias"] == 46
    assert por_cod["MO-02"]["vigente"] == "sí"
    assert por_cod["MO-01"]["edad_dias"] == 211
    assert por_cod["MO-01"]["vigente"] == "no"
    assert por_cod["MT-01"]["edad_dias"] == 30
    assert por_cod["MT-01"]["vigente"] == "sí"

    sin_fecha = construir_libro(siembra=Siembra(fecha_texto="", insumos=insumos))
    libro_sf = tmp_path / "sin_fecha.xlsx"
    libro_sf.write_bytes(sin_fecha.datos)
    dest_sf, _ = ic.ejecutar(
        libro_sf,
        tmp_path / "salida_sf",
        raiz_repo=tmp_path / "repo",
    )
    datos_sf = json.loads(dest_sf.read_text(encoding="utf-8"))
    assert datos_sf["fecha_libro"] is None
    assert all(item["edad_dias"] is None for item in datos_sf["insumos"])
    assert all(item["vigente"] == "sin_dato" for item in datos_sf["insumos"])


def test_se_niega_a_escribir_dentro_del_repositorio(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    libro = tmp_path / "entrada.xlsx"
    libro.write_bytes(libro_limpio().datos)

    with pytest.raises(ValueError, match="repositorio"):
        ic.main([str(libro), "--salida", str(repo / "sub"), "--raiz-repo", str(repo)])
    with pytest.raises(ValueError, match="repositorio"):
        ic.main([str(libro), "--salida", str(ic.RAIZ / "docs")])


def test_no_sobrescribe_json_existente(tmp_path: Path) -> None:
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(libro_limpio().datos)
    salida = tmp_path / "fuera"
    repo = tmp_path / "repo"

    assert ic.main([str(libro), "--salida", str(salida), "--raiz-repo", str(repo)]) == 0
    with pytest.raises(FileExistsError):
        ic.main([str(libro), "--salida", str(salida), "--raiz-repo", str(repo)])


def test_salida_cp1252_coma_decimal_y_sin_descripciones(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    libro = tmp_path / "obra.xlsx"
    libro.write_bytes(libro_limpio().datos)
    salida = tmp_path / "medicion"
    repo = tmp_path / "repo"

    codigo = ic.main(
        [
            str(libro),
            "--salida",
            str(salida),
            "--fecha",
            "2026-07-31",
            "--ventana",
            "90",
            "--raiz-repo",
            str(repo),
        ]
    )
    assert codigo == 0

    texto_pantalla = capsys.readouterr().out
    texto_pantalla.encode("cp1252")

    assert "MT-03" in texto_pantalla
    assert "," in texto_pantalla
    secretos = (
        "Cemento gris",
        "Arena lavada",
        "Bloque de arcilla",
        "Albañil",
        "Ayudante",
        "Mezcladora",
        "Condominio Ejemplo",
        "Constructora Didáctica",
        "Rehabilitación",
    )
    for secreto in secretos:
        assert secreto not in texto_pantalla

    archivos = list(salida.glob("*.json"))
    assert len(archivos) == 1
    datos = json.loads(archivos[0].read_text(encoding="utf-8"))
    assert "Eugenio" in datos["supuestos"]["nota_cortes"]
    assert set(datos["insumos"][0]) >= {
        "codigo",
        "descripcion",
        "tipo",
        "peso",
        "porcentaje",
        "acumulado",
        "clase",
        "fuente",
        "fecha",
        "edad_dias",
        "vigente",
    }
