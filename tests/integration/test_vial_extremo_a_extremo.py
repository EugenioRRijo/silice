"""El plan vial de punta a punta, todo por la API (plan vial, Tarea 22). Datos FICTICIOS.

Una cantera y una planta ficticias (`data/samples/produccion/`, su README dice que son inventadas)
producen dos meses; sus costos se calculan, se publican al catálogo, una persona compone los APU
de las partidas viales con esos precios, crea la obra, importa los tramos y los **lleva** al
presupuesto con `POST /v1/vial/tramos/llevar` (nunca `derivar_tramos` ni un `origen_id` escrito
aquí), la auditoría muestra VR1 a VR6, corrige y guarda; luego la conciliación, la proyección del
riesgo, su comprobación, la mejora de la estimación y los seis reportes.

Lo único que no entra por la API es lo que la carpeta ya tiene antes de empezar: las cuentas de
la instalación (admin, ana y rita de `tests/fixtures/sesion_web.py`) y la lista de precios de lo
que la planta compra (`lista_comprados.csv`), porque la primera lista de una carpeta nace de
MaPreX o de una conversión y no de un archivo.

Oráculos a mano (memoria completa en `data/samples/produccion/README.md`):

- Octubre: cantera 2.000 USD + 36.500 Bs ÷ 36,50 = 3.000 USD sobre 300 + 200 = 500 t → 6 USD/t;
  planta 4.000 ÷ 400 t = 10; mezcla 10 + (0,55 + 0,40) × 6 + 0,05 × 600 + 8 × 0,50 = 49,70.
- Noviembre: cantera 2.500 + 49.275 ÷ 36,50 = 3.850 USD sobre 550 t → 7; planta 5.500 ÷ 500 = 11;
  mezcla 11 + 0,95 × 7 + 30 + 4 = 51,65.
- Tramos: 16 cantidades; T1 mezcla 1.000 × 7 × 0,05 × 2,40 = 840 t, transporte de T2
  420 × 20 = 8.400 t·km, pintura de T1 2.000 m × 0,0365 = 73 l.
- Presupuesto (solo materiales: precio unitario = materiales × 1,15 × 1,10 = × 1,265): costo
  directo 110.101,40 USD; total 139.278,271; IVA 16 % 22.284,52; con IVA 161.562,79.
- Riesgo: el PPI sube 10 % exacto cada mes y el gasoil queda quieto, así todas las trayectorias
  dan lo mismo. Factor del asfalto en 6 meses = (1,1 + 1,21 + … + 1,771561) ÷ 6 = 1,4145285; la
  mezcla sube 30 × 0,4145285 USD/t; 1.296 t de mezcla × 1,265 → + 20.387,8381212 USD.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook

from api import caso_web, dependencias
from api.rutas import hoja as rutas_hoja
from api.rutas import produccion as rutas_produccion
from api.rutas import riesgo as rutas_riesgo
from api.rutas import vial as rutas_vial
from aplicacion import hoja_borradores
from aplicacion.riesgo.series import CEMENTO_ASFALTICO_PPI, GASOIL_USD
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from seguridad import cuentas
from tests.fixtures.produccion_api import Web
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

D = Decimal
MUESTRA = Path(__file__).resolve().parents[2] / "data" / "samples" / "produccion"
CARPETA = "via_extremo.db"
OBRA = "Vía Ficticia El Ensayo"
HOY = date(2026, 12, 2)
AHORA = datetime(2026, 12, 1, 8, 0)
LISTA_BASE = "Lista USD de la carpeta (ficticia)"
MEZCLA_T1 = "C-000.000.009|tramo:T1:capa:2"
TRANSPORTE_T2 = "C-000.000.014|tramo:T2:capa:3"
PINTURA_T1 = "C-000.000.015|tramo:T1:demarcacion:1"
#: Costo directo 110.101,40 USD × 1,265 (memoria del README).
TOTAL = D("139278.271")
#: TOTAL + 1.296 t × 30 USD/t × (1,4145285 − 1) × 1,265 = TOTAL + 20.387,8381212.
P80 = D("159666.1091212")


def _filas(nombre: str, separador: str = ",") -> list[dict[str, str]]:
    with (MUESTRA / nombre).open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo, delimiter=separador))


def _carpeta(ruta: Path) -> Path:
    """La carpeta del caso, migrada, con la lista de lo que la planta compra (en USD)."""
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            lista = models.ListaPrecios(
                nombre=LISTA_BASE, moneda="USD", fecha_vigencia=date(2026, 9, 1), origen="prueba"
            )
            sesion.add(lista)
            sesion.flush()
            for fila in _filas("lista_comprados.csv"):
                insumo = models.Insumo(
                    codigo=fila["codigo"],
                    tipo="material",
                    descripcion=fila["descripcion"],
                    unidad=fila["unidad"],
                )
                sesion.add(insumo)
                sesion.flush()
                sesion.add(
                    models.PrecioInsumo(
                        lista_id=lista.id, insumo_id=insumo.id, precio=D(fila["precio"])
                    )
                )
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_vial_extremo")
    return {"instalacion": plantilla_con_cuentas(carpeta), CARPETA: _carpeta(carpeta / CARPETA)}


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos = config.carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    (casos / CARPETA).write_bytes(_plantillas[CARPETA].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    monkeypatch.setattr(rutas_produccion, "_ahora", lambda: AHORA)
    monkeypatch.setattr(rutas_hoja, "_hoy", lambda: HOY)
    monkeypatch.setattr(rutas_vial, "_hoy", lambda: HOY)
    monkeypatch.setattr(rutas_vial, "ahora", lambda: AHORA)
    monkeypatch.setattr(rutas_riesgo, "hoy", lambda: date(2026, 12, 15))
    yield
    hoja_borradores.olvidar_todo()
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()
    cuentas.FRENO.reiniciar()


def _en_la_carpeta(login: str) -> Web:
    web = Web(login)
    elegida = web.post("/v1/casos/actual", json={"nombre": CARPETA})
    assert elegida.status_code == 200, elegida.text
    return web


def _ok(respuesta, estado: int = 200):
    assert respuesta.status_code == estado, respuesta.text
    return respuesta.json()


# --- 1. La cantera y la planta: producción, costos, cálculo y publicación -------------------------


def _produccion(ana: Web) -> None:
    for fila in _filas("materiales.csv"):
        _ok(ana.post("/v1/produccion/materiales", json=fila), 201)
    for fila in _filas("movimientos.csv"):
        _ok(ana.post("/v1/produccion/movimientos", json=fila), 201)
    receta = _filas("receta.csv")
    componentes = [
        {k: f[k] for k in ("codigo", "cantidad_por_t", "unidad", "tipo")} for f in receta
    ]
    cuerpo = {
        "producto": "MZ-C",
        "componentes": componentes,
        "fuente": "dosificación ficticia de la planta",
        "vigente_desde": "2026-09-01",
    }
    _ok(ana.post("/v1/produccion/recetas", json=cuerpo), 201)
    for fila in _filas("producciones.csv"):
        _ok(ana.post("/v1/produccion/producciones", json=fila), 201)
    for fila in _filas("costos.csv"):
        _ok(ana.post("/v1/produccion/costos", json=fila), 201)


def _series(admin: Web) -> None:
    """La tasa del BCV, el PPI del asfalto y el gasoil, como los importa el administrador en
    «Índices»: leer el CSV canónico y confirmarlo con su huella y lo que declara de cada serie."""
    contenido = (MUESTRA / "series.csv").read_bytes()
    campos = {"tipo": "csv", "fecha_descarga": "2026-12-01", "fuente": "series ficticias"}
    archivo = {"archivo": ("series.csv", contenido, "text/csv")}
    leido = _ok(admin.post("/v1/indices/leer", data=campos, files=archivo))
    definiciones = [
        {
            "serie": s.codigo,
            "nombre": s.nombre,
            "organismo": s.organismo,
            "unidad": s.unidad,
            "periodicidad": s.periodicidad,
        }
        for s in (CEMENTO_ASFALTICO_PPI, GASOIL_USD)
    ]
    confirmado = admin.post(
        "/v1/indices/confirmar",
        data={**campos, "huella": leido["huella"], "definiciones": json.dumps(definiciones)},
        files={"archivo": ("series.csv", contenido, "text/csv")},
    )
    _ok(confirmado)


def _calcular(ana: Web, periodo: str) -> dict:
    return _ok(ana.post("/v1/produccion/calculos", json={"periodo": periodo, "moneda": "USD"}), 201)


def _por_tonelada(calculo: dict) -> dict[str, D]:
    return {p["codigo"]: D(p["por_tonelada"]) for p in calculo["productos"]}


# --- 2. La obra: APU compuestos, la obra y su primera versión ------------------------------------


def _componer(ana: Web) -> None:
    """Cada APU como lo guarda una persona en «Componer»: una línea de material tecleada. Las
    mezclas usan el costo propio publicado («Costo propio de mezcla MZ-C», 51,65); la base
    granular, el de la piedra con el precio de **octubre** (6), que la conciliación señalará."""
    for fila in _filas("apu.csv", ";"):
        material = {
            "descripcion": fila["material"],
            "unidad": fila["unidad_material"],
            "cantidad": fila["cantidad"],
            "precio": fila["precio"],
        }
        cuerpo = {
            "codigo": fila["codigo"],
            "descripcion": fila["descripcion"],
            "unidad": fila["unidad"],
            "dominio": "civil",
            "rendimiento": "1",
            "fecha": "2026-12-01",
            "condiciones": "Obra vial ficticia de la prueba de punta a punta",
            "materiales": [material],
        }
        _ok(ana.post("/v1/composicion/guardar", json=cuerpo))


def _borrador(ana: Web, id_: str) -> dict:
    return _ok(ana.get(f"/v1/hoja/borradores/{id_}"))["resumen"]


def _primera_version(ana: Web) -> None:
    """La Hoja en blanco de la obra con la movilización, guardada como V-001."""
    _ok(ana.post("/v1/proyectos", json={"nombre": OBRA, "moneda": "USD", "dominio": "civil"}), 201)
    id_ = _ok(ana.post("/v1/hoja/borradores", json={"proyecto": OBRA}), 201)["id"]
    rev = _borrador(ana, id_)["rev"]
    cuerpo = {"rev": rev, "codigo": "MOV-01", "cantidad": "1"}
    _ok(ana.post(f"/v1/hoja/borradores/{id_}/partidas", json=cuerpo))
    rev = _borrador(ana, id_)["rev"]
    cuerpo = {"rev": rev, "fuente": "primera versión de la obra ficticia", "codigo": "V-001"}
    guardada = _ok(ana.post(f"/v1/hoja/borradores/{id_}/guardar", json=cuerpo))
    assert D(guardada["total"]["exacto"]) == D("2530")  # 2.000 × 1,265


# --- 3. Los tramos van al presupuesto y la auditoría vial -----------------------------------------


def _vista(ana: Web, id_: str, vista: str) -> dict:
    return _ok(ana.get(f"/v1/hoja/borradores/{id_}/vistas/{vista}"))


def _viales(ana: Web, id_: str) -> list[tuple[str, list[str]]]:
    hallazgos = _vista(ana, id_, "auditoria")["hallazgos"]
    return [(h["regla"], h["origen"]) for h in hallazgos if h["regla"].startswith("VR")]


def _escribir(ana: Web, id_: str, cantidades: dict[str, str]) -> None:
    filas = [{"clave": c, "cantidad": v} for c, v in cantidades.items()]
    rev = _borrador(ana, id_)["rev"]
    respuesta = ana.cliente.put(
        f"/v1/hoja/borradores/{id_}/cantidades",
        json={"rev": rev, "filas": filas},
        headers=ana.cabeceras(),
    )
    _ok(respuesta)


def _llevar_tramos(ana: Web) -> str:
    contenido = (MUESTRA / "via.csv").read_bytes()
    importado = ana.post(
        "/v1/vial/tramos/importar",
        params={"proyecto": OBRA, "version": "V-001"},
        files={"archivo": ("via.csv", contenido, "text/csv")},
    )
    _ok(importado)
    llevado = _ok(ana.post("/v1/vial/tramos/llevar", json={"proyecto": OBRA, "version": "V-001"}))
    assert (llevado["renglones"], llevado["version"]) == (16, "V-001")
    return llevado["borrador_id"]


# --- 4. Conciliación, riesgo, comprobación, mejora y los seis reportes ----------------------------


def _libro(respuesta):
    assert respuesta.status_code == 200, respuesta.text
    return load_workbook(BytesIO(respuesta.content))


def _hoja(libro, nombre: str) -> list[tuple]:
    return [f for f in libro[nombre].iter_rows(values_only=True) if any(c is not None for c in f)]


def _valor(libro, nombre: str, rotulo: str):
    (valor,) = [f[1] for f in _hoja(libro, nombre) if f[0] == rotulo]
    return valor


def _reportes_viales(ana: Web) -> None:
    def pedir(tipo: str, **params):
        base = {"proyecto": OBRA, "version": "V-002"}
        return _libro(ana.get(f"/v1/vial/reportes/{tipo}", params={**base, **params}))

    computos = pedir("computos")
    assert computos.sheetnames == ["Portada", "Tramos", "Cómputos por tramo", "Totales por partida"]
    por_tramo = _hoja(computos, "Cómputos por tramo")[1:]
    assert len(por_tramo) == 16
    assert {(f[0], f[1]): D(str(f[4])) for f in por_tramo}[("T1", "C-000.000.009")] == D(840)
    totales = {f[0]: D(str(f[3])) for f in _hoja(computos, "Totales por partida")[1:]}
    assert totales["C-000.000.009"] == D(1260)  # 840 + 420
    assert totales["C-000.000.014"] == D(25920)  # 16.800 + 8.400 + 720

    apu = pedir("apu")
    assert apu.sheetnames == ["Portada", "Partidas", "APU con origen", "Conciliación"]
    (cv3,) = _hoja(apu, "Conciliación")[1:]
    assert cv3[:2] == ("CV3", "ADVERTENCIA")
    assert (D(str(cv3[3])), D(str(cv3[4])), cv3[5]) == (D(6), D(7), "tramo:T2:capa:1")
    assert "el último cálculo publicado, el cálculo n.º 2 (período 2026-11)" in cv3[2]

    # El de producción vive bajo /v1/produccion (pantallas de informes, fila 112).
    produccion = _libro(
        ana.get("/v1/produccion/reportes/produccion", params={"periodo": "2026-11"})
    )
    costo = {f[2]: D(str(f[4])) for f in _hoja(produccion, "Costo por tonelada")[1:]}
    assert costo == {"PC-19": D(7), "AR-01": D(7), "MZ-C": D("51.65")}

    resumen = pedir("resumen")
    assert D(str(_valor(resumen, "Resumen", "Subtotal sin IVA"))) == D("139278.27")
    assert D(str(_valor(resumen, "Resumen", "IVA (16 %)"))) == D("22284.52")
    assert D(str(_valor(resumen, "Resumen", "Total con IVA"))) == D("161562.79")
    assert _valor(resumen, "Resumen", "Moneda") == "USD"


def _riesgo_y_mejora(ana: Web) -> None:
    mapa = {"CA-30": CEMENTO_ASFALTICO_PPI.codigo, "GO": GASOIL_USD.codigo}
    pedido = {"proyecto": OBRA, "version": "V-002", "meses": 6, "semilla": 7, "mapa": mapa}
    proyeccion = _ok(
        ana.post(
            "/v1/riesgo/proyeccion", json={**pedido, "inicio": "2026-12-01", "trayectorias": 200}
        )
    )
    assert (D(proyeccion["total_base"]), proyeccion["meses_usados"]) == (TOTAL, 24)
    assert D(proyeccion["p50"]) == D(proyeccion["p80"]) == P80
    assert D(proyeccion["reserva"]) == P80 - TOTAL
    (contribucion,) = proyeccion["contribucion"]
    assert contribucion["insumo"] == "Costo propio de mezcla MZ-C"
    assert round(D(contribucion["monto"]), 7) == P80 - TOTAL
    assert proyeccion["mezclas"] == [{"insumo": "Costo propio de mezcla MZ-C", "calculo": 2}]

    comprobacion = _ok(
        ana.post("/v1/riesgo/comprobacion", json={**pedido, "trayectorias_por_corte": 20})
    )
    assert (comprobacion["n_cortes"], comprobacion["cobertura_pct"]) == (7, "100.00")
    assert {D(c["real"]) for c in comprobacion["cortes"]} == {P80}

    cifras = {
        "costo_final_real": "160000",
        "presupuesto_original": "139278.27",
        "estimacion_silice": "159666.11",
    }
    # a mano: (160.000 − 139.278,27) ÷ 160.000 = 12,951 %; (160.000 − 159.666,11) ÷ 160.000 =
    # 0,209 %; la diferencia, 12,742 puntos
    esperado = {"error_original_pct": "12.95", "error_silice_pct": "0.21", "mejora_pp": "12.74"}
    assert _ok(ana.post("/v1/riesgo/mejora", json=cifras)) == esperado

    riesgo = _libro(
        ana.get(
            "/v1/riesgo/reportes/riesgo",
            params={
                **{k: v for k, v in pedido.items() if k != "mapa"},
                "mapa": json.dumps(mapa),
                "inicio": "2026-12-01",
                "trayectorias": 200,
                "comprobar": "true",
                "trayectorias_por_corte": 20,
            },
        )
    )
    assert D(str(_valor(riesgo, "Proyección", "Total base"))) == TOTAL
    assert D(str(_valor(riesgo, "Proyección", "P80"))) == P80
    assert _valor(riesgo, "Comprobación", "Cortes") == 7
    assert D(str(_valor(riesgo, "Comprobación", "Cobertura (%)"))) == D("100.00")

    informe = _libro(ana.get("/v1/riesgo/reportes/mejora", params=cifras))
    assert informe.sheetnames == ["Portada", "Mejora"]
    for rotulo, valor in (
        ("Error del presupuesto original (%)", "12.95"),
        ("Error de la estimación de Sílice (%)", "0.21"),
        ("Mejora (puntos porcentuales)", "12.74"),
    ):
        assert D(str(_valor(informe, "Mejora", rotulo))) == D(valor), rotulo


def test_de_punta_a_punta() -> None:
    ana = _en_la_carpeta("ana")
    admin = _en_la_carpeta("admin")
    _ok(
        admin.post(
            "/v1/admin/empresa",
            json={
                "nombre": "Constructora Ejemplo, C.A.",
                "rif": "J-00000000-0",
                "ciudad": "Ficticia",
            },
        )
    )

    _produccion(ana)
    # Foco 1: sin la tasa del día de la nómina de octubre, el cálculo se niega y no escribe nada
    sin_tasa = ana.post("/v1/produccion/calculos", json={"periodo": "2026-10", "moneda": "USD"})
    assert sin_tasa.status_code == 422, sin_tasa.text
    assert "costo n.º 2 del 06/10/2026" in sin_tasa.json()["detalle"]
    _series(admin)
    octubre = _calcular(ana, "2026-10")
    assert _por_tonelada(octubre) == {"PC-19": D(6), "AR-01": D(6), "MZ-C": D("49.70")}
    _ok(admin.post(f"/v1/produccion/calculos/{octubre['id']}/publicar", json={}), 201)
    noviembre = _calcular(ana, "2026-11")
    assert _por_tonelada(noviembre) == {"PC-19": D(7), "AR-01": D(7), "MZ-C": D("51.65")}
    _ok(admin.post(f"/v1/produccion/calculos/{noviembre['id']}/publicar", json={}), 201)

    _componer(ana)
    _primera_version(ana)

    id_ = _llevar_tramos(ana)
    filas = {f["clave"]: f["cantidad"] for f in _vista(ana, id_, "presupuesto")["filas"]}
    assert filas[MEZCLA_T1] == "840"
    assert filas[TRANSPORTE_T2] == "8.400"
    assert filas[PINTURA_T1] == "73"
    assert _viales(ana, id_) == [
        ("VR2", ["tramo:T1:capa:2"]),
        ("VR3", ["tramo:T1:capa:1"]),
        ("VR6", ["tramo:T2", "tramo:T3"]),
    ]
    _escribir(ana, id_, {MEZCLA_T1: "800", TRANSPORTE_T2: "8.000", PINTURA_T1: "40"})
    assert _viales(ana, id_) == [
        ("VR1", ["tramo:T1:capa:2"]),
        ("VR4", ["tramo:T2:capa:3"]),
        ("VR2", ["tramo:T1:capa:2"]),
        ("VR3", ["tramo:T1:capa:1"]),
        ("VR5", ["tramo:T1:demarcacion:1"]),
        ("VR6", ["tramo:T2", "tramo:T3"]),
    ]
    descripciones = {
        h["regla"]: h["descripcion"]
        for h in _vista(ana, id_, "auditoria")["hallazgos"]
        if h["regla"].startswith("VR")
    }
    for regla, cifras in {
        "VR1": ("800 t en el presupuesto y 840 t",),
        "VR2": ("asfalto de 6,5 % y la fórmula de trabajo dice 5 %",),  # receta: 0,05 t/t
        "VR3": ("0,3 l/m² dejan 180 g/m²", "200 g/m²"),  # 0,30 × 1,0 × 1.000 × 0,60
        "VR4": ("8.000 t·km en el presupuesto y 8.400 t·km",),
        "VR5": ("40 l de pintura en 2 km", "20 l por km", "de 29 a 44"),
        "VR6": ("hueco de 0,1 km entre T2 y T3",),  # T2 termina en 1,5 y T3 empieza en 1,6
    }.items():
        assert all(c in descripciones[regla] for c in cifras), descripciones[regla]
    # corregido: lo que queda es del diseño de la vía (fórmula, dosis y el hueco), no del cómputo
    _escribir(ana, id_, {MEZCLA_T1: "840", TRANSPORTE_T2: "8.400", PINTURA_T1: "73"})
    assert [r for r, _ in _viales(ana, id_)] == ["VR2", "VR3", "VR6"]
    rev = _borrador(ana, id_)["rev"]
    cuerpo = {"rev": rev, "fuente": "tramos llevados y corregidos tras la auditoría"}
    guardada = _ok(ana.post(f"/v1/hoja/borradores/{id_}/guardar", json=cuerpo))
    assert guardada["codigo"] == "V-002"
    assert D(guardada["total"]["exacto"]) == TOTAL

    _reportes_viales(ana)
    _riesgo_y_mejora(ana)
