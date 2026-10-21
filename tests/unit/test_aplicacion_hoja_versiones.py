"""3b-B3C (T10, 3d-2): las cuatro operaciones (restaurar, cotizar, retirar, convertir).

Corre las cuatro operaciones en DOS capas sobre COPIAS de la misma base:

* `hoja`: `aplicacion.hoja`;
* `versiones`: `aplicacion.hoja_versiones`, la capa que usan las rutas S2 a S5 (resuelve el
  proyecto por codigo o nombre, comprueba la version, envuelve la cadena y deshace al rechazar).

De cada corrida se fija el codigo de la version nueva, el TEXTO de cada error (igualdad exacta de
cadena), las filas que quedan en la base (menos las columnas que dependen del reloj de la corrida)
y el estado de la cadena. Las dos capas deben dar lo mismo entre si (ambas viven en `aplicacion/`)
y ambas se comparan con literales a mano. Ya no se compara contra `ui.hoja` (retiro de Streamlit,
F6). Casos: OF-001 (con espacio) y TI-001 (sin espacio, otra moneda de codigo).

Oraculos a mano (ninguno sale del codigo): la restauracion deja el registro (version,
<restaurada>, restauracion, <vigente>, <nueva>); la cotizacion, (precio, <insumo>, cotizacion,
<antes>, <despues>); la conversion, (moneda, <proyecto>, moneda, USD, Bs); y los textos de error de
`core.budget` (`la fuente del cambio es obligatoria...`, `el proveedor de la cotizacion es
obligatorio`, ...). Una version nueva de OF-001 copia las 30 partidas, 6 ambientes, 6 fuentes, 2
circuitos y 21 puntos de la memoria (`of001.md` §1) y sella un eslabon; la de TI-001 copia sus 27
partidas y ningun anexo de espacio.
"""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from aplicacion import hoja
from aplicacion.entrega import con_anexos_de_cadena, estado_de_la_cadena
from aplicacion.errores import HojaInvalida
from core import models
from core.catalog import Catalogo, abrir_sesion, crear_motor
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    NOMBRE_TI001,
    plantilla_of001,
    plantilla_ti001,
)
from tests.fixtures.hoja_versiones_api import registrar_tasa

D = Decimal
FUENTE = "acta de revision 7: se vuelve a la medida original"
MOTIVO = "el proveedor retiro la oferta"
RESPONSABLE = "Ana <ana>"
PROVEEDOR = "Ferreteria Demo, C.A."
SIN_FUENTE = "la fuente del cambio es obligatoria: diga por que y con que respaldo"
HOY = date(2026, 10, 6)
#: Columnas que dependen del reloj de la corrida y no del contenido: la hora del sello, las
#: huellas que la incluyen (el registro de cambios lleva su fecha y hora), la hora del registro y
#: el momento en que empieza a regir una moneda. Que el sello sea valido lo dice
#: `estado_de_la_cadena`, que SI se compara.
RELOJ = {
    ("eslabon_version", "fecha_hora"),
    ("eslabon_version", "huella_eslabon"),
    ("eslabon_version", "huella_cambios"),
    ("eslabon_version", "anterior"),  # la huella del eslabon previo, que lleva su hora
    ("registro_cambio", "fecha_hora"),
    ("moneda_proyecto", "desde"),
}
SABORES = ["hoja", "versiones"]
#: Filas que una version nueva agrega por tabla (memoria de OF-001 §1; las 27 partidas de TI-001).
ESCRIBE = {
    "of001": {
        "presupuesto": 1,
        "eslabon_version": 1,
        "item_computo": 30,
        "composicion_version": 30,
        "esp_origenes": 1,
        "esp_ambientes": 6,
        "esp_fuentes": 6,
        "esp_circuitos": 2,
        "esp_puntos": 21,
    },
    "ti001": {"presupuesto": 1, "eslabon_version": 1, "item_computo": 27},
}


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("hoja_versiones")
    of001 = plantilla_of001(carpeta / "of001.db")
    ti001 = plantilla_ti001(carpeta / "ti001.db")
    for ruta in (of001, ti001):
        registrar_tasa(ruta, date(2026, 10, 5), "860.18")
    return {"of001": of001, "ti001": ti001}


#: Para cada caso: (clave de la plantilla, proyecto, version de partida, version nueva esperada,
#: el insumo que se cotiza).
CASOS = [
    pytest.param("of001", NOMBRE_OF001, "001", "002", "EQU-001", id="OF-001"),
    pytest.param("ti001", NOMBRE_TI001, "TI-001", "TI-002", None, id="TI-001"),
]


@dataclass
class _Corrida:
    """Lo que dio una operacion (codigo o texto del error) y el estado en que dejo la base."""

    resultado: tuple
    volcado: dict[str, list[tuple]]
    registros: list[tuple]
    cadena: tuple[bool, str]


class _Caso:
    """Una copia de la base con su sesion envuelta (la cadena cubre los anexos de espacio)."""

    def __init__(self, plantilla: Path, destino: Path, sabor: str) -> None:
        self.ruta = destino / f"{sabor}.db"
        shutil.copyfile(plantilla, self.ruta)
        self.motor = crear_motor(f"sqlite:///{self.ruta.as_posix()}")
        self.sesion = abrir_sesion(self.motor)
        con_anexos_de_cadena(self.sesion)
        self.catalogo = Catalogo(self.sesion)
        self.sabor = sabor

    def cerrar(self) -> None:
        self.sesion.close()
        self.motor.dispose()

    def volcado(self) -> dict[str, list[tuple]]:
        with closing(sqlite3.connect(f"file:{self.ruta.as_posix()}?mode=ro", uri=True)) as bd:
            tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            salida = {}
            for tabla in tablas:
                columnas = [c[1] for c in bd.execute(f'PRAGMA table_info("{tabla}")')]
                quitar = {n for n, c in enumerate(columnas) if (tabla, c) in RELOJ}
                filas = [
                    tuple(v for n, v in enumerate(fila) if n not in quitar)
                    for fila in bd.execute(f'SELECT * FROM "{tabla}"')
                ]
                salida[tabla] = sorted(filas, key=repr)
            return salida

    def registros(self, proyecto: str, codigo: str) -> list[tuple]:
        r = models.RegistroCambio
        return [
            tuple(f)
            for f in self.sesion.execute(
                select(
                    r.objeto,
                    r.clave,
                    r.campo,
                    r.valor_anterior,
                    r.valor_nuevo,
                    r.fuente,
                    r.responsable,
                )
                .join(models.Presupuesto, models.Presupuesto.id == r.version_resultante_id)
                .join(models.Proyecto, models.Proyecto.id == models.Presupuesto.proyecto_id)
                .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
                .order_by(r.id)
            )
        ]

    # --- las operaciones, en cada sabor ---

    def restaurar(self, proyecto: str, codigo: str, fuente: str) -> str:
        if self.sabor == "versiones":
            from aplicacion import hoja_versiones

            return hoja_versiones.restaurar(
                self.sesion, proyecto, codigo, fuente=fuente, responsable=RESPONSABLE
            ).codigo
        return hoja.restaurar(
            self.sesion, self.catalogo, proyecto, codigo, fuente=fuente, responsable=RESPONSABLE
        )

    def cotizar(self, proyecto: str, codigo: str, **datos) -> str:
        valores = {
            "insumo": "EQU-001",
            "precio": "999.5",
            "proveedor": PROVEEDOR,
            "numero": "COT-001",
            "fecha": date(2026, 10, 5),
            "evidencia": "",
            **datos,
        }
        if self.sabor == "versiones":
            from aplicacion import hoja_versiones

            return hoja_versiones.cotizar(
                self.sesion,
                proyecto,
                codigo,
                insumo=valores["insumo"],
                precio=valores["precio"],
                proveedor=valores["proveedor"],
                numero=valores["numero"],
                fecha=valores["fecha"],
                evidencia=valores["evidencia"] or None,
                responsable=RESPONSABLE,
            ).codigo
        try:
            precio = hoja.decimal_desde_texto(valores["precio"], "precio")
        except ValueError as error:  # la ruta lo captura igual (`except ValueError`)
            raise HojaInvalida(str(error)) from error
        return hoja.cotizar(
            self.sesion,
            self.catalogo,
            proyecto,
            codigo,
            insumo=valores["insumo"],
            precio=precio,
            proveedor=valores["proveedor"],
            numero=valores["numero"],
            fecha=valores["fecha"],
            responsable=RESPONSABLE,
            fuente=valores["evidencia"],
        )

    def retirar(self, proyecto: str, codigo: str, insumo: str, motivo: str) -> str:
        if self.sabor == "versiones":
            from aplicacion import hoja_versiones

            return hoja_versiones.retirar_cotizacion(
                self.sesion, proyecto, codigo, insumo=insumo, motivo=motivo, responsable=RESPONSABLE
            ).codigo
        return hoja.retirar_cotizacion(
            self.sesion,
            self.catalogo,
            proyecto,
            codigo,
            insumo=insumo,
            fuente=motivo,
            responsable=RESPONSABLE,
        )

    def convertir(self, proyecto: str, codigo: str, moneda: str, lado: str, fuente: str) -> str:
        if self.sabor == "versiones":
            from aplicacion import hoja_versiones

            return hoja_versiones.convertir(
                self.sesion,
                proyecto,
                codigo,
                moneda,
                lado=lado,
                fecha=HOY,
                fuente=fuente,
                responsable=RESPONSABLE,
            ).codigo
        return hoja.convertir(
            self.sesion,
            self.catalogo,
            proyecto,
            codigo,
            moneda,
            lado=lado,
            fecha=HOY,
            fuente=fuente,
            responsable=RESPONSABLE,
        )

    def correr(self, proyecto: str, accion) -> _Corrida:
        """Corre `accion(caso)`; `resultado` es ("ok", codigo) o ("error", texto)."""
        try:
            resultado = ("ok", accion(self))
        except HojaInvalida as error:
            resultado = ("error", str(error))
        self.sesion.expire_all()
        estado = estado_de_la_cadena(self.sesion, proyecto)
        self.sesion.rollback()  # cierra la lectura de la cadena: la proxima operacion parte limpia
        return _Corrida(
            resultado,
            self.volcado(),
            self.registros(proyecto, resultado[1]) if resultado[0] == "ok" else [],
            (estado.integra, estado.mensaje),
        )


@pytest.fixture
def abrir_caso(tmp_path):
    abiertos: list[_Caso] = []

    def abrir(plantilla: Path, sabor: str, carpeta: str = "") -> _Caso:
        carpeta = tmp_path / (carpeta or sabor)
        carpeta.mkdir(exist_ok=True)
        caso = _Caso(plantilla, carpeta, sabor)
        abiertos.append(caso)
        return caso

    yield abrir
    for caso in abiertos:
        caso.cerrar()


def _en_las_dos(abrir_caso, plantilla: Path, proyecto: str, accion) -> dict[str, _Corrida]:
    return {sabor: abrir_caso(plantilla, sabor).correr(proyecto, accion) for sabor in SABORES}


def _iguales(corridas: dict[str, _Corrida]) -> _Corrida:
    """Las dos capas dejan lo mismo; devuelve la de `aplicacion.hoja`."""
    base = corridas["hoja"]
    assert corridas["versiones"].resultado == base.resultado
    assert corridas["versiones"].registros == base.registros
    assert corridas["versiones"].cadena == base.cadena
    assert corridas["versiones"].volcado == base.volcado
    return base


def _agregado(antes: dict[str, list[tuple]], corrida: _Corrida) -> dict[str, int]:
    """Cuantas filas mas hay por tabla despues de la operacion (solo las que cambiaron)."""
    cambios = {t: len(f) - len(antes[t]) for t, f in corrida.volcado.items() if t in antes}
    return {t: n for t, n in cambios.items() if n}


# --- restaurar ---


@pytest.mark.parametrize(("clave", "proyecto", "origen", "nueva", "_insumo"), CASOS)
def test_restaurar_deja_el_registro_de_la_memoria_en_las_dos_capas(
    clave, proyecto, origen, nueva, _insumo, _plantillas, abrir_caso
) -> None:
    antes = abrir_caso(_plantillas[clave], "hoja", "antes").volcado()
    corridas = _en_las_dos(
        abrir_caso, _plantillas[clave], proyecto, lambda c: c.restaurar(proyecto, origen, FUENTE)
    )
    unica = _iguales(corridas)
    assert unica.resultado == ("ok", nueva)
    assert unica.registros == [
        ("version", origen, "restauracion", origen, nueva, FUENTE, RESPONSABLE)
    ]
    assert unica.cadena[0] is True
    # restaurar copia las partidas y sella el eslabon; las tablas del espacio no se miran aqui
    esperado = {
        **{t: n for t, n in ESCRIBE[clave].items() if not t.startswith("esp_")},
        "registro_cambio": 1,
        "version_origen": 1,
    }
    agregado = _agregado(antes, unica)
    assert {t: n for t, n in agregado.items() if t in esperado} == esperado


@pytest.mark.parametrize("fuente", ["", "   "])
@pytest.mark.parametrize(("clave", "proyecto", "origen", "_n", "_i"), CASOS)
def test_restaurar_sin_fuente_dice_lo_mismo_y_no_escribe(
    fuente, clave, proyecto, origen, _n, _i, _plantillas, abrir_caso
) -> None:
    antes = abrir_caso(_plantillas[clave], "hoja", "antes").volcado()
    corridas = _en_las_dos(
        abrir_caso, _plantillas[clave], proyecto, lambda c: c.restaurar(proyecto, origen, fuente)
    )
    unica = _iguales(corridas)
    assert unica.resultado == ("error", SIN_FUENTE)
    assert unica.volcado == antes


# --- cotizar y retirar (OF-001: EQU-001) ---


def test_cotizar_deja_lo_mismo_en_las_dos_capas(_plantillas, abrir_caso) -> None:
    corridas = _en_las_dos(
        abrir_caso,
        _plantillas["of001"],
        NOMBRE_OF001,
        lambda c: c.cotizar(NOMBRE_OF001, "001", evidencia="factura 77"),
    )
    unica = _iguales(corridas)
    assert unica.resultado == ("ok", "002")
    assert unica.registros[0][:3] == ("precio", "EQU-001", "cotizacion")
    assert unica.registros[0][4:] == (
        "999.5",
        "Cotizacion COT-001 de Ferreteria Demo, C.A. (2026-10-05). factura 77",
        RESPONSABLE,
    )
    assert unica.cadena[0] is True


DATOS_MALOS = [
    ({"precio": "abc"}, "precio: 'abc' no es un numero decimal valido"),
    ({"precio": "NaN"}, "precio: 'NaN' no es un monto finito"),
    ({"precio": "-1"}, "el precio cotizado debe ser un Decimal no negativo, no Decimal('-1')"),
    ({"proveedor": ""}, "el proveedor de la cotizacion es obligatorio"),
    ({"numero": " "}, "el numero de la cotizacion es obligatorio"),
    ({"insumo": "NO-EXISTE"}, "no hay ningun insumo con codigo 'NO-EXISTE'"),
    ({"precio": "abc", "proveedor": ""}, "precio: 'abc' no es un numero decimal valido"),
    ({"proveedor": "", "numero": ""}, "el proveedor de la cotizacion es obligatorio"),
]


@pytest.mark.parametrize(("datos", "texto"), DATOS_MALOS)
def test_cotizar_con_un_dato_malo_dice_el_texto_escrito_y_no_escribe(
    datos, texto, _plantillas, abrir_caso
) -> None:
    antes = abrir_caso(_plantillas["of001"], "hoja", "antes").volcado()
    corridas = _en_las_dos(
        abrir_caso,
        _plantillas["of001"],
        NOMBRE_OF001,
        lambda c: c.cotizar(NOMBRE_OF001, "001", **datos),
    )
    unica = _iguales(corridas)
    assert unica.resultado == ("error", texto)
    assert unica.volcado == antes


def test_cotizar_al_precio_que_ya_tiene_la_lista_lo_rechaza(_plantillas, abrir_caso) -> None:
    caso = abrir_caso(_plantillas["of001"], "hoja", "antes")
    de_lista = next(
        p.precio
        for p in hoja.precios_de_version(caso.sesion, NOMBRE_OF001, "001")
        if p.codigo == "EQU-001"
    )
    corridas = _en_las_dos(
        abrir_caso,
        _plantillas["of001"],
        NOMBRE_OF001,
        lambda c: c.cotizar(NOMBRE_OF001, "001", precio=str(de_lista)),
    )
    unica = _iguales(corridas)
    assert unica.resultado == (
        "error",
        f"el insumo EQU-001 ya vale {de_lista} en la lista de la version",
    )


def test_retirar_la_cotizacion_deja_lo_mismo_en_las_dos_capas(_plantillas, abrir_caso) -> None:
    def cotizar_y_retirar(c: _Caso) -> str:
        c.cotizar(NOMBRE_OF001, "001")
        return c.retirar(NOMBRE_OF001, "002", "EQU-001", MOTIVO)

    corridas = _en_las_dos(abrir_caso, _plantillas["of001"], NOMBRE_OF001, cotizar_y_retirar)
    unica = _iguales(corridas)
    assert unica.resultado == ("ok", "003")
    assert unica.registros[0][:5] == (
        "precio",
        "EQU-001",
        "cotizacion",
        "999.5",
        unica.registros[0][4],
    )
    assert unica.registros[0][5:] == (MOTIVO, RESPONSABLE)
    assert unica.cadena[0] is True


@pytest.mark.parametrize(
    ("version", "insumo", "motivo", "texto"),
    [
        ("001", "EQU-001", MOTIVO, "la version '001' no tiene cotizacion del insumo EQU-001"),
        ("001", "NO-EXISTE", MOTIVO, "no hay ningun insumo con codigo 'NO-EXISTE'"),
        ("001", "EQU-001", "  ", SIN_FUENTE),
    ],
)
def test_retirar_con_un_dato_malo_dice_el_texto_escrito_y_no_escribe(
    version, insumo, motivo, texto, _plantillas, abrir_caso
) -> None:
    antes = abrir_caso(_plantillas["of001"], "hoja", "antes").volcado()
    corridas = _en_las_dos(
        abrir_caso,
        _plantillas["of001"],
        NOMBRE_OF001,
        lambda c: c.retirar(NOMBRE_OF001, version, insumo, motivo),
    )
    unica = _iguales(corridas)
    assert unica.resultado == ("error", texto)
    assert unica.volcado == antes


# --- convertir ---


@pytest.mark.parametrize(("clave", "proyecto", "origen", "nueva", "_i"), CASOS)
def test_convertir_a_bs_deja_lo_mismo_en_las_dos_capas(
    clave, proyecto, origen, nueva, _i, _plantillas, abrir_caso
) -> None:
    antes = abrir_caso(_plantillas[clave], "hoja", "antes").volcado()
    corridas = _en_las_dos(
        abrir_caso,
        _plantillas[clave],
        proyecto,
        lambda c: c.convertir(proyecto, origen, "Bs", "venta", "cambio de moneda del contrato"),
    )
    unica = _iguales(corridas)
    assert unica.resultado == ("ok", nueva)
    assert unica.registros[0][:5] == ("moneda", proyecto, "moneda", "USD", "Bs")
    assert unica.registros[0][6] == RESPONSABLE
    assert unica.cadena[0] is True
    agregado = _agregado(antes, unica)
    assert (agregado["presupuesto"], agregado["eslabon_version"]) == (1, 1)
    assert agregado["item_computo"] == ESCRIBE[clave]["item_computo"]


CONVERSIONES_MALAS = [
    ("USD", "venta", "x", "No se convirtio nada: la version {v} ya esta en USD"),
    ("EUR", "venta", "x", "No se convirtio nada: moneda 'EUR'; se espera Bs o USD (UC-17 4b)"),
    ("Bs", "venta", "", f"No se convirtio nada: {SIN_FUENTE}"),
    (
        "Bs",
        "compra",
        "x",
        "No se convirtio nada: no hay tasa compra del BCV importada al 06/10/2026 o antes: "
        "importe el archivo trimestral (UC-17)",
    ),
]


@pytest.mark.parametrize(("moneda", "lado", "fuente", "texto"), CONVERSIONES_MALAS)
@pytest.mark.parametrize(("clave", "proyecto", "origen", "_n", "_i"), CASOS)
def test_convertir_con_un_dato_malo_dice_el_texto_escrito_y_no_escribe(
    moneda, lado, fuente, texto, clave, proyecto, origen, _n, _i, _plantillas, abrir_caso
) -> None:
    antes = abrir_caso(_plantillas[clave], "hoja", "antes").volcado()
    corridas = _en_las_dos(
        abrir_caso,
        _plantillas[clave],
        proyecto,
        lambda c: c.convertir(proyecto, origen, moneda, lado, fuente),
    )
    unica = _iguales(corridas)
    assert unica.resultado == ("error", texto.format(v=origen))
    assert unica.volcado == antes


# --- lo que SOLO tiene la capa nueva: el 404 de la API ---


def test_la_capa_nueva_dice_que_proyecto_o_version_falta_con_los_textos_escritos(
    _plantillas, abrir_caso
) -> None:
    from aplicacion import hoja_versiones

    caso = abrir_caso(_plantillas["of001"], "versiones")
    # `hoja.lista_de_version` dice lo mismo (H:1572): solo sabe de la version
    with pytest.raises(HojaInvalida) as dicho:
        hoja.lista_de_version(caso.sesion, NOMBRE_OF001, "009")
    with pytest.raises(hoja_versiones.VersionInexistente) as falta:
        hoja_versiones.restaurar(
            caso.sesion, NOMBRE_OF001, "009", fuente=FUENTE, responsable=RESPONSABLE
        )
    assert str(falta.value) == str(dicho.value)
    assert str(falta.value) == (
        f"El proyecto {NOMBRE_OF001!r} no tiene una version '009': elija una de la lista."
    )
    with pytest.raises(hoja_versiones.ProyectoInexistente) as sin_proyecto:
        hoja_versiones.restaurar(caso.sesion, "Z", "001", fuente=FUENTE, responsable=RESPONSABLE)
    assert str(sin_proyecto.value) == "El proyecto «Z» no existe en este caso."
