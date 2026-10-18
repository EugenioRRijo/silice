"""Lo que la pantalla «Existencias de la arenera» hace, sin Streamlit (Tarea 4.9; UC-28 / UC-29).

`ui.paginas.existencias` pinta; este módulo arma las filas del tablero con el estado de cada
material y ejecuta las acciones del usuario sobre los servicios de `produccion/`: registrar
entradas, despachos y conteos, importar un reporte de báscula y resolver o descartar un pesaje
sospechoso.

Transacciones: los servicios de `produccion/` hacen `flush`; el `commit` es de esta capa. Cada
acción confirma al terminar y deshace (`rollback`) si algo falla, para que la sesión siga siendo
útil. Los errores que son del usuario (`ErrorDeInventario`, `ReporteRechazado`, `MapeoNecesario`,
`ArchivoRechazado`) traen su mensaje escrito para él; ninguna acción deja pasar una traza.

Estado de cada material (RF-129, RT-S4-2): `negativa` si la existencia es menor que cero (un
despacho nunca se bloquea: se registra y se marca); `queda poco` si es menor o igual que la
mínima; `normal` en los demás casos. Cada estado se rotula con un signo propio y un texto,
nunca solo con color.

Sin Streamlit ni pandas (`tests/unit/test_arquitectura.py`): se prueba como cualquier función.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import PurePath

from sqlalchemy.orm import Session

from adapters.hoja_empresa.guardia import ArchivoRechazado, verificar_archivo
from produccion import importacion, inventario
from produccion.conectores.bascula import ReporteRechazado, leer
from produccion.conectores.detector_columnas import CAMPOS, MapeoNecesario
from produccion.importacion import ResultadoImportacion
from produccion.inventario import ErrorDeInventario
from produccion.modelo import Material, Movimiento, PesajeSospechoso

__all__ = [
    "CAMPOS",
    "ERRORES_DEL_USUARIO",
    "ESTADOS",
    "ArchivoRechazado",
    "ErrorDeInventario",
    "FilaPantalla",
    "MapeoNecesario",
    "ReporteRechazado",
    "cantidad_de_texto",
    "crear_material_desde_pantalla",
    "descartar_desde_pantalla",
    "etiqueta_de_material",
    "filas_de_sospechosos",
    "filas_de_tablero",
    "importar_desde_pantalla",
    "materiales_activos",
    "registrar_conteo_desde_pantalla",
    "registrar_despacho_desde_pantalla",
    "registrar_entrada_desde_pantalla",
    "resolver_desde_pantalla",
    "rotulo_de_estado",
    "sospechosos_pendientes",
    "tablero_para_pantalla",
]

ESTADOS = ("normal", "queda poco", "negativa")
#: Un signo propio por estado (no solo color; IBCS): ✔ favorable, ▲ a vigilar, ✖ desfavorable.
ROTULOS: Mapping[str, str] = {
    "normal": "✔ Normal",
    "queda poco": "▲ Queda poco",
    "negativa": "✖ Existencia negativa: falta registrar producción o conteo",
}
UNIDADES: Mapping[str, str] = {"m3": "m³", "t": "t"}
ERRORES_DEL_USUARIO = (ErrorDeInventario, ReporteRechazado, MapeoNecesario, ArchivoRechazado)

_CERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class FilaPantalla:
    """Una fila del tablero tal como se muestra: textos ya formateados y el estado."""

    codigo: str
    nombre: str
    unidad: str
    existencia_texto: str
    minima_texto: str
    estado: str  # uno de ESTADOS


# --- formato --------------------------------------------------------------------------------------


def texto_de_cantidad(valor: Decimal) -> str:
    """El valor exacto, sin ceros de más y con coma decimal (`24.5000` -> `24,5`; `20` -> `20`)."""
    return format(valor.normalize(), "f").replace(".", ",")


def rotulo_de_estado(estado: str) -> str:
    """El signo y el texto del estado (`✔ Normal`, `▲ Queda poco`, `✖ Existencia negativa…`)."""
    return ROTULOS[estado]


def cantidad_de_texto(texto: str, que: str) -> Decimal:
    """Un número escrito por el usuario: `24,5` y `24.5` se leen exactos. Con coma y punto a la vez
    (`1.234,5`) no se adivina cuál es el decimal: se pide escribirlo sin separador de miles."""
    limpio = texto.strip()
    if "," in limpio and "." in limpio:
        raise ErrorDeInventario(
            f"La cantidad de {que} no debe llevar separador de miles: escriba, por ejemplo, 1234,5."
        )
    try:
        valor = Decimal(limpio.replace(",", "."))
    except InvalidOperation:
        valor = None
    if valor is None or not valor.is_finite():
        raise ErrorDeInventario(f"La cantidad de {que} debe ser un número mayor que cero.")
    return valor


def etiqueta_de_material(material: Material) -> str:
    return f"{material.codigo} · {material.nombre}"


# --- el tablero -----------------------------------------------------------------------------------


def _estado(queda_poco: bool, negativa: bool) -> str:
    if negativa:
        return "negativa"
    return "queda poco" if queda_poco else "normal"


def tablero_para_pantalla(sesion: Session, a_fecha: date | None) -> list[FilaPantalla]:
    """El tablero de los materiales activos a `a_fecha`, listo para pintar."""
    return [
        FilaPantalla(
            codigo=fila.material.codigo,
            nombre=fila.material.nombre,
            unidad=UNIDADES.get(fila.material.unidad_venta, fila.material.unidad_venta),
            existencia_texto=texto_de_cantidad(fila.existencia),
            minima_texto=texto_de_cantidad(fila.minima),
            estado=_estado(fila.queda_poco, fila.negativa),
        )
        for fila in inventario.tablero(sesion, a_fecha)
    ]


def filas_de_tablero(filas: list[FilaPantalla]) -> list[dict[str, str]]:
    """Las filas de la tabla de la pantalla; el estado va con su signo y su texto."""
    return [
        {
            "Código": f.codigo,
            "Material": f.nombre,
            "Unidad": f.unidad,
            "Existencia": f.existencia_texto,
            "Mínima": f.minima_texto,
            "Estado": rotulo_de_estado(f.estado),
        }
        for f in filas
    ]


def materiales_activos(sesion: Session) -> list[Material]:
    return [fila.material for fila in inventario.tablero(sesion)]


# --- acciones (confirman o deshacen) --------------------------------------------------------------


def _confirmando[T](sesion: Session, accion: Callable[[], T]) -> T:
    try:
        resultado = accion()
        sesion.commit()
    except BaseException:
        sesion.rollback()
        raise
    return resultado


def crear_material_desde_pantalla(
    sesion: Session,
    *,
    codigo: str,
    nombre: str,
    unidad_venta: str,
    minima_texto: str,
    densidad_texto: str,
) -> Material:
    """Crea un material. La densidad es dato de la empresa: vacía, el material no admite báscula en
    m³ (esos pesajes irán a la bandeja)."""

    def hacer() -> Material:
        try:
            minima = Decimal(minima_texto.strip().replace(",", "."))
        except InvalidOperation:
            raise ErrorDeInventario(
                "La existencia mínima debe ser un número de cero o más."
            ) from None
        densidad = None
        if densidad_texto.strip():
            try:
                densidad = Decimal(densidad_texto.strip().replace(",", "."))
            except InvalidOperation:
                raise ErrorDeInventario(
                    "La densidad (t/m3) debe ser un número mayor que cero."
                ) from None
        return inventario.crear_material(
            sesion,
            codigo=codigo,
            nombre=nombre,
            unidad_venta=unidad_venta,
            existencia_minima=minima,
            densidad_t_m3=densidad,
        )

    return _confirmando(sesion, hacer)


def registrar_entrada_desde_pantalla(
    sesion: Session, material_id: int, fecha: date, cantidad_texto: str, usuario: str, nota: str
) -> Movimiento:
    return _confirmando(
        sesion,
        lambda: inventario.registrar_entrada(
            sesion,
            material_id,
            fecha,
            cantidad_de_texto(cantidad_texto, "la entrada"),
            usuario=usuario,
            nota=nota.strip(),
        ),
    )


def registrar_despacho_desde_pantalla(
    sesion: Session,
    material_id: int,
    fecha: date,
    cantidad_texto: str,
    usuario: str,
    *,
    ticket: str = "",
    placa: str = "",
    cliente: str = "",
    nota: str = "",
) -> Movimiento:
    """Un despacho manual. Nunca se bloquea por dejar la existencia negativa (RT-S4-2)."""
    return _confirmando(
        sesion,
        lambda: inventario.registrar_despacho(
            sesion,
            material_id,
            fecha,
            cantidad_de_texto(cantidad_texto, "el despacho"),
            usuario=usuario,
            ticket=ticket.strip() or None,
            placa=placa.strip(),
            cliente=cliente.strip(),
            nota=nota.strip(),
        ),
    )


def registrar_conteo_desde_pantalla(
    sesion: Session, material_id: int, fecha: date, conteo_texto: str, usuario: str, nota: str
) -> Movimiento | None:
    """Un conteo físico: registra el ajuste que lleva la existencia a lo contado (o ninguno)."""

    def hacer() -> Movimiento | None:
        try:
            conteo = Decimal(conteo_texto.strip().replace(",", "."))
        except InvalidOperation:
            raise ErrorDeInventario("El conteo físico debe ser un número de cero o más.") from None
        return inventario.registrar_ajuste_por_conteo(
            sesion, material_id, fecha, conteo, usuario=usuario, nota=nota.strip()
        )

    return _confirmando(sesion, hacer)


def importar_desde_pantalla(
    sesion: Session,
    datos: bytes,
    nombre: str,
    fecha_referencia: date,
    unidad_peso: str | None,
    usuario: str,
    mapeo: Mapping[str, int] | None = None,
) -> ResultadoImportacion:
    """Lee un reporte de báscula (`.csv` o `.xlsx`) y lo importa.

    Un `.xlsx` pasa antes por la guardia de archivos ajenos (`ArchivoRechazado` si trae macros o es
    desmedido). `unidad_peso` es `"kg"`, `"t"` o `None` (se toma del encabezado; sin ninguna, el
    lector rechaza). Todo o nada: si algo falla no queda nada a medias.
    """
    if PurePath(nombre).suffix.lower() == ".xlsx":
        verificar_archivo(datos, nombre)

    def hacer() -> ResultadoImportacion:
        lectura = leer(
            datos, nombre, fecha_referencia=fecha_referencia, unidad_peso=unidad_peso, mapeo=mapeo
        )
        return importacion.importar(sesion, lectura, usuario=usuario)

    return _confirmando(sesion, hacer)


# --- la bandeja -----------------------------------------------------------------------------------


def sospechosos_pendientes(sesion: Session) -> list[PesajeSospechoso]:
    return importacion.pendientes(sesion)


def filas_de_sospechosos(pendientes: list[PesajeSospechoso]) -> list[dict[str, str]]:
    """La bandeja como tabla; los textos son los del archivo (ajenos) y van en celdas, no en
    Markdown."""
    return [
        {
            "Fila": str(s.fila),
            "Ticket": s.ticket,
            "Fecha": s.fecha_texto,
            "Placa": s.placa,
            "Material": s.material_texto,
            "Bruto": s.bruto_texto,
            "Tara": s.tara_texto,
            "Neto": s.neto_texto,
            "Motivo": s.motivo,
        }
        for s in pendientes
    ]


def resolver_desde_pantalla(
    sesion: Session,
    id_sospechoso: int,
    *,
    material_codigo: str,
    fecha: date,
    neto_texto: str,
    ticket: str,
    usuario: str,
    ahora: datetime,
) -> Movimiento:
    """Crea el despacho con los valores corregidos (neto en toneladas) y cierra el sospechoso."""
    return _confirmando(
        sesion,
        lambda: importacion.resolver(
            sesion,
            id_sospechoso,
            material_codigo=material_codigo,
            fecha=fecha,
            neto_t=cantidad_de_texto(neto_texto, "el peso neto"),
            ticket=ticket,
            usuario=usuario,
            ahora=ahora,
        ),
    )


def descartar_desde_pantalla(
    sesion: Session, id_sospechoso: int, *, usuario: str, ahora: datetime
) -> None:
    _confirmando(
        sesion,
        lambda: importacion.descartar(sesion, id_sospechoso, usuario=usuario, ahora=ahora),
    )
