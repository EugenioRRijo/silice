"""Caso de la memoria s1_precios_empresa.md: referencia, lista de empresa, tasa y versión en Bs."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto
from core.catalog import Catalogo, leer_lista_precios
from core.catalog.empresa import (
    crear_lista_de_empresa,
    crear_lista_de_referencia,
    precios_propios_desde,
)
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from core.catalog.moneda import TasaDeclarada
from core.contracts import ComposicionAPU, Dominio, ItemComputo, LineaMaterial, ParametrosCosto
from core.contracts.item_computo import OrigenTipo
from scripts.lista_maprex_bs import FECHA_TASA_MAPREX, FUENTE_TASA_MAPREX, RUTA_SALIDA, TASA_MAPREX

CSV = Path(__file__).resolve().parent / "precios_empresa_s1.csv"
EVALUACION = date(2026, 10, 1)
PARAMETROS = ParametrosCosto(
    fcas=Decimal(0),
    bono_alimentacion=Decimal(0),
    administracion=Decimal("0.15"),
    utilidad=Decimal("0.10"),
)
GRANULAR = "MATERIAL GRANULAR INTEGRAL"


def sembrar(sesion):
    referencia = crear_lista_de_referencia(
        sesion,
        RUTA_SALIDA,
        nombre="MaPreX julio 2026 en Bs",
        moneda="Bs",
        tasa=TasaDeclarada(TASA_MAPREX, FECHA_TASA_MAPREX, FUENTE_TASA_MAPREX),
    )
    Catalogo(sesion).dar_de_alta_insumo(models.TipoInsumo.MATERIAL, "LIJA DE AGUA N 100", "pza")
    propios, _ = precios_propios_desde(sesion, leer_lista_precios(CSV))
    lista = crear_lista_de_empresa(
        sesion,
        "Constructora Ejemplo, C.A.",
        "J-00000000-0",
        referencia,
        propios,
        moneda="Bs",
        fecha=date(2026, 9, 20),
        fuente="lista interna 2026-09",
        referencia=referencia,
    )
    registrar_importacion(
        sesion,
        definicion_tasa("venta"),
        [Observacion(EVALUACION, Decimal("860.18"))],
        archivo="FUENTE.md",
        huella="c" * 64,
        fuente="https://www.bcv.org.ve/",
        responsable="A",
        fecha_descarga=date(2026, 10, 8),
        filas_leidas=1,
        filas_rechazadas=0,
    )
    usados = {p.insumo.descripcion.upper(): p for p in lista.precios}
    descripciones = [fila["insumo"] for fila in _filas()] + [GRANULAR]
    lineas = tuple(
        LineaMaterial(d, usados[d].insumo.unidad, Decimal(1), usados[d].precio)
        for d in descripciones
    )
    sesion.add(
        models.Partida(
            codigo="S1-EMP-01",
            descripcion="Partida de prueba de precios",
            unidad="m2",
            dominio="civil",
        )
    )
    composicion = ComposicionAPU(
        "S1-EMP-01", "Partida de prueba de precios", "m2", Decimal(1), lineas
    )
    item = ItemComputo(
        "S1-EMP-01",
        "Partida de prueba",
        "m2",
        Decimal(10),
        "memoria-s1",
        OrigenTipo.MANUAL,
        Dominio.CIVIL,
    )
    resultado = elaborar(
        [item],
        {"S1-EMP-01": composicion},
        PARAMETROS,
        codigo="001",
        fecha=date(2026, 9, 20),
        moneda="Bs",
    )
    proyecto = crear_proyecto(sesion, "Precios de empresa S1")
    version = guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=lista,
        parametros=PARAMETROS,
    )
    return referencia, lista, version


def _filas():
    import csv

    with CSV.open(encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))
