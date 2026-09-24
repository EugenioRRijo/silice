"""Funciones puras de composición de un APU a mano (Sesión P2.1, UC-10 y UC-11).

La lógica de convertir las tres tablas de la futura pantalla (`ui/paginas/componer.py`, Sesión
P2.2) en un `ComposicionAPU` del contrato vive aquí, fuera de `render()`, porque hoy el repositorio
no tiene ninguna prueba de interfaz: lo único verificable es lo que se puede llamar sin Streamlit
(spec de diseño §4, `docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md`). Por
eso este módulo no importa `streamlit` ni `pandas`: `st.data_editor` devuelve un `DataFrame`, pero
convertirlo a las listas de diccionarios que aquí se reciben es trabajo de la página, no de esta
capa de dominio.

Las filas son diccionarios de texto (las claves que produce cada tabla de la pantalla), nunca
`Decimal` ni objetos del contrato: el usuario escribe texto y esta capa es la única que decide qué
significa "vacío" y qué mensaje de error señala la fila y el campo culpables.

Depende de `core.costing` solo para `desglose` (`calcular_apu` es una función pura) y **no escribe
en la base**: la persistencia de una composición vive en `ui/elaboracion.guardar_composicion`
(INV-043, fase C3). Lo vigila `tests/unit/test_arquitectura.py`.
"""

from __future__ import annotations

import csv
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ModalidadManoObra,
    ParametrosCosto,
    ResultadoAPU,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.unidades import unidades_equivalentes
from core.contracts.verificacion import Hallazgo
from core.costing import calcular_apu
from core.verification.texto import normalizar_texto

if TYPE_CHECKING:
    from ml.anomaly import VeredictoRendimiento
    from ml.normalization import PartidaSimilar


def desglose(composicion: ComposicionAPU) -> ResultadoAPU:
    """El desglose de costos de `composicion` con los parametros por defecto (CLAUDE.md §4).

    Es lo que la pagina de componer muestra en vivo, contrasta y confirma al guardar: una funcion
    pura (`calcular_apu`), sin base de datos.
    """
    return calcular_apu(composicion, ParametrosCosto())


class ComposicionInvalida(ValueError):  # noqa: N818
    """Una tabla de la pantalla no se puede convertir en un APU del contrato.

    El nombre no lleva el sufijo `Error` que pide la convención inglesa de N818: el proyecto
    escribe sus identificadores en español (CLAUDE.md §3), igual que `ExpresionInvalida`
    (`core/verification/expresiones.py`) y `PlanInvalido` (`core/budget/curva.py`).
    """


def decimal_desde_texto(texto: str, campo: str) -> Decimal:
    """`Decimal` desde el texto del formulario, con el campo culpable en el mensaje.

    Movido de `ui/paginas/escenarios.py` (antes `_decimal`, privado): un nombre privado importado
    desde otro módulo era una contradicción, y P2.2/P2.3 lo necesitan igual que UC-08.
    """
    try:
        valor = Decimal(texto.strip())
    except InvalidOperation as error:
        raise ComposicionInvalida(f"{campo}: {texto!r} no es un numero decimal valido") from error
    if not valor.is_finite():
        raise ComposicionInvalida(f"{campo}: {texto!r} no es un monto finito")
    return valor


def texto_de_celda(fila: Mapping[str, object], clave: str) -> str:
    """Extrae y normaliza una celda, incluida la frontera con el productor real de las filas.

    Es la unica lectura de celdas de tabla de `ui/` (INV-046): la usan estas funciones y
    `ui.elaboracion.items_desde_filas`.

    El tipo declarado de `fila` es `Mapping[str, str]`, pero `st.data_editor` con
    `num_rows="dynamic"` (docstring líneas 6-8) entrega `None` o NaN en las celdas de una fila
    recién añadida en blanco: `str(None)` es `"None"` y `str(float("nan"))` es `"nan"`, y ninguno
    de los dos es vacío para `str.strip()`. Esta es la frontera donde ambos se normalizan a
    cadena vacía, antes de que lleguen a `_fila_vacia` o a cualquier conversión.
    """
    valor = fila.get(clave)
    if valor is None:
        return ""
    texto = str(valor).strip()
    return "" if texto.lower() == "nan" else texto


def _fila_vacia(valores: Sequence[str]) -> bool:
    """Una fila dinámica sin ningún dato todavía no es un error: es una fila que el usuario no
    llenó. Se descarta antes de intentar convertir nada.
    """
    return all(not valor.strip() for valor in valores)


def _exigir_descripcion(tabla: str, indice: int, descripcion: str) -> None:
    """Una fila con algún dato pero sin descripción no es "vacía": es un error (spec §4, plan P2.2).

    Sin este control, `Catalogo._resolver_insumo` (core/catalog/repositorio.py) identifica los
    insumos por (tipo, descripcion, unidad): varias líneas sin nombre con la misma unidad y precio
    colapsarían calladamente en un solo insumo, y la regla R6 (`CriterioDepreciacion`) las
    confundiría con "el mismo insumo" entre APU distintos.
    """
    if not descripcion:
        raise ComposicionInvalida(f"{tabla}, fila {indice}: la descripcion no puede estar vacia")


def _modalidad_desde_texto(texto: str, descripcion: str) -> ModalidadManoObra:
    """Vacía es JORNAL (el caso por defecto del contrato); cualquier otra debe ser válida.

    `ModalidadManoObra(texto)` deja escapar un `ValueError` del `StrEnum` sin decir de qué fila
    viene; con tres tablas y filas dinámicas eso no basta para ubicar el error.
    """
    texto = texto.strip()
    if not texto:
        return ModalidadManoObra.JORNAL
    try:
        return ModalidadManoObra(texto)
    except ValueError as error:
        raise ComposicionInvalida(
            f"modalidad ({descripcion}): {texto!r} no es una modalidad de mano de obra valida"
        ) from error


def _material_desde_fila(fila: Mapping[str, str], indice: int) -> LineaMaterial | None:
    descripcion = texto_de_celda(fila, "descripcion")
    unidad = texto_de_celda(fila, "unidad")
    cantidad_texto = texto_de_celda(fila, "cantidad")
    precio_texto = texto_de_celda(fila, "precio")
    if _fila_vacia((descripcion, unidad, cantidad_texto, precio_texto)):
        return None
    _exigir_descripcion("materiales", indice, descripcion)

    cantidad = decimal_desde_texto(cantidad_texto, f"cantidad ({descripcion})")
    precio = decimal_desde_texto(precio_texto, f"precio ({descripcion})")
    try:
        return LineaMaterial(
            descripcion=descripcion, unidad=unidad, cantidad=cantidad, precio=precio
        )
    except ValueError as error:
        raise ComposicionInvalida(
            f"materiales, fila {indice} ({descripcion}): {error}"
        ) from error


def _equipo_desde_fila(fila: Mapping[str, str], indice: int) -> LineaEquipo | None:
    descripcion = texto_de_celda(fila, "descripcion")
    cantidad_texto = texto_de_celda(fila, "cantidad")
    precio_texto = texto_de_celda(fila, "precio")
    depreciacion_texto = texto_de_celda(fila, "depreciacion")
    if _fila_vacia((descripcion, cantidad_texto, precio_texto, depreciacion_texto)):
        return None
    _exigir_descripcion("equipos", indice, descripcion)

    cantidad = decimal_desde_texto(cantidad_texto, f"cantidad ({descripcion})")
    precio = decimal_desde_texto(precio_texto, f"precio ({descripcion})")
    depreciacion = decimal_desde_texto(depreciacion_texto, f"depreciacion ({descripcion})")
    try:
        return LineaEquipo(
            descripcion=descripcion, cantidad=cantidad, precio=precio, depreciacion=depreciacion
        )
    except ValueError as error:
        raise ComposicionInvalida(
            f"equipos, fila {indice} ({descripcion}): {error}"
        ) from error


def _mano_obra_desde_fila(fila: Mapping[str, str], indice: int) -> LineaManoObra | None:
    descripcion = texto_de_celda(fila, "descripcion")
    cantidad_texto = texto_de_celda(fila, "cantidad")
    sueldo_texto = texto_de_celda(fila, "sueldo")
    modalidad_texto = texto_de_celda(fila, "modalidad")
    if _fila_vacia((descripcion, cantidad_texto, sueldo_texto, modalidad_texto)):
        return None
    _exigir_descripcion("mano de obra", indice, descripcion)

    cantidad = decimal_desde_texto(cantidad_texto, f"cantidad ({descripcion})")
    sueldo = decimal_desde_texto(sueldo_texto, f"sueldo ({descripcion})")
    modalidad = _modalidad_desde_texto(modalidad_texto, descripcion)
    try:
        return LineaManoObra(
            descripcion=descripcion, cantidad=cantidad, sueldo=sueldo, modalidad=modalidad
        )
    except ValueError as error:
        raise ComposicionInvalida(
            f"mano de obra, fila {indice} ({descripcion}): {error}"
        ) from error


def composicion_desde_tablas(
    codigo: str,
    descripcion: str,
    unidad: str,
    rendimiento: str,
    filas_materiales: Sequence[Mapping[str, str]],
    filas_equipos: Sequence[Mapping[str, str]],
    filas_mano_obra: Sequence[Mapping[str, str]],
) -> ComposicionAPU:
    """Arma la `ComposicionAPU` que compone la pantalla a partir de sus tres tablas de texto.

    Claves esperadas por fila (una ausente se trata como cadena vacía):
    materiales `descripcion`, `unidad`, `cantidad`, `precio`; equipos `descripcion`, `cantidad`,
    `precio`, `depreciacion`; mano de obra `descripcion`, `cantidad`, `sueldo`, `modalidad`.
    """
    # El indice empieza en 1 y cuenta las filas tal como llegaron (antes de descartar las
    # vacias), para que el mensaje de error coincida con lo que la persona ve en pantalla.
    materiales = tuple(
        linea
        for indice, fila in enumerate(filas_materiales, start=1)
        if (linea := _material_desde_fila(fila, indice)) is not None
    )
    equipos = tuple(
        linea
        for indice, fila in enumerate(filas_equipos, start=1)
        if (linea := _equipo_desde_fila(fila, indice)) is not None
    )
    mano_obra = tuple(
        linea
        for indice, fila in enumerate(filas_mano_obra, start=1)
        if (linea := _mano_obra_desde_fila(fila, indice)) is not None
    )
    valor_rendimiento = decimal_desde_texto(rendimiento, "rendimiento")

    try:
        return ComposicionAPU(
            codigo_partida=codigo,
            descripcion=descripcion,
            unidad=unidad,
            rendimiento=valor_rendimiento,
            materiales=materiales,
            equipos=equipos,
            mano_obra=mano_obra,
        )
    except ValueError as error:
        # `rendimiento > 0` y `codigo_partida` no vacío ya los valida el contrato; aquí solo se
        # traduce la excepción, sin duplicar la invariante.
        raise ComposicionInvalida(str(error)) from error


def _tabla_vacia(filas: Sequence[Mapping[str, str]]) -> bool:
    """Ninguna fila de la tabla tiene todavía un solo carácter escrito (ayudante de
    `formulario_vacio`; reutiliza `texto_de_celda` y `_fila_vacia`, las mismas fronteras que ya
    limpian `None`/NaN antes de decidir qué es "vacío").
    """
    return all(_fila_vacia(tuple(texto_de_celda(fila, clave) for clave in fila)) for fila in filas)


def formulario_vacio(
    codigo: str,
    descripcion: str,
    filas_materiales: Sequence[Mapping[str, str]],
    filas_equipos: Sequence[Mapping[str, str]],
    filas_mano_obra: Sequence[Mapping[str, str]],
) -> bool:
    """El formulario está en su estado prístino: nadie ha tecleado nada todavía.

    Se usa para distinguir la bienvenida (`ui/paginas/componer.py`, `_desglose_en_vivo`) del
    aviso de "a medio llenar" que produce `composicion_desde_tablas` vía `ComposicionInvalida`:
    ese aviso sigue siendo la funcionalidad principal (retroalimentación en vivo mientras se
    teclea) y no debe ocultarse. Antes de este chequeo, una pantalla completamente en blanco
    mostraba "rendimiento: '' no es un numero decimal valido" como primer mensaje, que es
    correcto pero una mala bienvenida.
    """
    if codigo.strip() or descripcion.strip():
        return False
    return (
        _tabla_vacia(filas_materiales)
        and _tabla_vacia(filas_equipos)
        and _tabla_vacia(filas_mano_obra)
    )


def item_desde_cantidad(
    codigo: str,
    descripcion: str,
    unidad: str,
    cantidad: str,
    origen_id: str,
    dominio: Dominio,
) -> ItemComputo:
    """Un `ItemComputo` de origen MANUAL: la cantidad que el proyectista escribe a mano al
    componer el APU (no viene de IFC, regla ni CSV). `dominio` es el sexto parámetro porque
    `ItemComputo` lo exige sin valor por defecto (`core/contracts/item_computo.py`).
    """
    valor_cantidad = decimal_desde_texto(cantidad, "cantidad")
    try:
        return ItemComputo(
            codigo_partida=codigo,
            descripcion=descripcion,
            unidad=unidad,
            cantidad=valor_cantidad,
            origen_id=origen_id,
            origen_tipo=OrigenTipo.MANUAL,
            dominio=dominio,
        )
    except ValueError as error:
        # `origen_id` no vacío ya lo exige el contrato (toda cantidad debe ser trazable); aquí
        # solo se traduce la excepción.
        raise ComposicionInvalida(str(error)) from error


# --- Editar una partida existente (UC-11): precarga y guarda antes de reemplazar -----------------
#
# Auditoria del PR #7: la pantalla arrancaba siempre con las tres tablas vacias (el paso 1 de UC-11,
# "el sistema precarga sus tres tablas de insumos", no estaba implementado) y guardar sobre una
# partida existente llamaba a `Catalogo.reemplazar_composicion` con lo que hubiera en pantalla, que
# borra las lineas sin impedir una composicion de cero lineas y no actualiza ni la descripcion ni
# la unidad de la partida. Las dos decisiones viven aqui, puras; `ui/paginas/componer.py` solo
# pinta y llama. `core/` no se toca (CLAUDE.md §9).


def _decimal_como_texto(valor: Decimal) -> str:
    """El `Decimal` tal como lo teclea una persona: notacion fija, sin exponente ni perder escala.

    Mismo criterio que `tests/integration/test_composicion_extremo_a_extremo.py::_texto`:
    `str(Decimal("1E+2"))` da `"1E+2"`, que ninguna pantalla muestra.
    """
    return f"{valor:f}"


def filas_desde_composicion(
    composicion: ComposicionAPU,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """Las tres tablas de texto de la pantalla a partir de una composicion (UC-11, paso 1).

    Es la inversa de `composicion_desde_tablas`: mismas claves por fila (materiales `descripcion`,
    `unidad`, `cantidad`, `precio`; equipos `descripcion`, `cantidad`, `precio`, `depreciacion`;
    mano de obra `descripcion`, `cantidad`, `sueldo`, `modalidad`), todo como texto, de modo que
    volver a leerlas reproduce la misma composicion.
    """
    materiales = [
        {
            "descripcion": linea.descripcion,
            "unidad": linea.unidad,
            "cantidad": _decimal_como_texto(linea.cantidad),
            "precio": _decimal_como_texto(linea.precio),
        }
        for linea in composicion.materiales
    ]
    equipos = [
        {
            "descripcion": linea.descripcion,
            "cantidad": _decimal_como_texto(linea.cantidad),
            "precio": _decimal_como_texto(linea.precio),
            "depreciacion": _decimal_como_texto(linea.depreciacion),
        }
        for linea in composicion.equipos
    ]
    mano_obra = [
        {
            "descripcion": linea.descripcion,
            "cantidad": _decimal_como_texto(linea.cantidad),
            "sueldo": _decimal_como_texto(linea.sueldo),
            "modalidad": linea.modalidad.value,
        }
        for linea in composicion.mano_obra
    ]
    return materiales, equipos, mano_obra


def motivo_para_no_reemplazar(
    descripcion_registrada: str,
    unidad_registrada: str,
    composicion: ComposicionAPU,
) -> str | None:
    """Por que no se debe reemplazar la composicion de una partida existente, o `None` si se puede.

    Se evalua antes de `Catalogo.reemplazar_composicion` (UC-11) con la descripcion y la unidad que
    la partida tiene en el catalogo:

    - una composicion sin ninguna linea en las tres tablas no reemplaza nada: borraria el desglose
      de la partida (el defecto reproducido con `DEMO-01-INST`, 3/2/2 -> 0/0/0);
    - la cabecera de una partida existente no se edita por esta via: `reemplazar_composicion` solo
      sustituye lineas y rendimiento, asi que una unidad o una descripcion distintas se
      descartarian en silencio. Las unidades se comparan con `unidades_equivalentes` (`m³` es
      `m3`), no por igualdad de texto; la descripcion, sin los espacios de borde.
    """
    codigo = composicion.codigo_partida
    if not (composicion.materiales or composicion.equipos or composicion.mano_obra):
        return (
            f"la partida {codigo} ya existe y la composicion no tiene ninguna linea de insumo: "
            "guardarla borraria su desglose. Declare al menos una linea en materiales, equipos "
            "o mano de obra."
        )
    if not unidades_equivalentes(composicion.unidad, unidad_registrada):
        return (
            f"la partida {codigo} ya existe con la unidad {unidad_registrada!r} y la cabecera dice "
            f"{composicion.unidad!r}: la cabecera de una partida existente no se edita desde esta "
            "pantalla. Escriba la unidad registrada o use otro codigo para una partida nueva."
        )
    if composicion.descripcion.strip() != descripcion_registrada.strip():
        return (
            f"la partida {codigo} ya existe con la descripcion {descripcion_registrada!r} y la "
            f"cabecera dice {composicion.descripcion!r}: la cabecera de una partida existente no "
            "se edita desde esta pantalla. Escriba la descripcion registrada o use otro codigo "
            "para una partida nueva."
        )
    return None


# --- Búsqueda en la referencia MaPreX (Tarea 2, UC-10/UC-11) -----------------------------------
#
# `data/precios/maprex_2026-07/referencia_{civil,telecom,industrial,sistemas}.csv` (Sesión M0.2,
# `scripts/extraer_maprex.py`) son 111 filas verificadas. A diferencia de la lista canónica de
# cuatro columnas que deriva `scripts/lista_maprex_usd.py`, aquí se leen los CSV crudos porque
# solo ellos traen `factor_depreciacion`, `bono_bs` y `ref_maprex`: el propósito de esta búsqueda
# es sugerir esos datos para autocompletar una fila de la pantalla, no solo un precio.

_RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]
_CARPETA_REFERENCIA = Path("data") / "precios" / "maprex_2026-07"
#: Mismo orden que `scripts/lista_maprex_usd.py` (civil, telecom, industrial, sistemas), para que
#: la posición de una fila en el resultado sea reproducible entre ejecuciones.
_ARCHIVOS_REFERENCIA = (
    "referencia_civil.csv",
    "referencia_telecom.csv",
    "referencia_industrial.csv",
    "referencia_sistemas.csv",
)


@dataclass(frozen=True, slots=True)
class FilaReferencia:
    """Una fila de la referencia MaPreX, como sugerencia editable.

    MaPreX es referencia de mercado, no verdad (spec §3.4): quien presupuesta puede sobrescribir
    el precio con su cotizacion. `factor_depreciacion` solo viene lleno en equipos.
    """

    tipo: str
    descripcion: str
    unidad: str
    precio_usd: Decimal
    factor_depreciacion: Decimal | None
    bono_bs: Decimal | None
    ref_maprex: str


def _decimal_o_nada(texto: str) -> Decimal | None:
    """`Decimal` desde una celda que puede venir vacía (`factor_depreciacion` y `bono_bs` solo se
    llenan para ciertos `tipo`: ver `buscar_referencia`). Construido siempre desde texto.
    """
    texto = texto.strip()
    return Decimal(texto) if texto else None


def _fila_referencia_desde_csv(fila: Mapping[str, str]) -> FilaReferencia:
    return FilaReferencia(
        tipo=fila["tipo"],
        descripcion=fila["insumo"],
        unidad=fila["unidad"],
        precio_usd=Decimal(fila["precio_usd"].strip()),
        factor_depreciacion=_decimal_o_nada(fila["factor_depreciacion"]),
        bono_bs=_decimal_o_nada(fila["bono_bs"]),
        ref_maprex=fila["ref_maprex"],
    )


def buscar_referencia(texto: str, tipo: str, raiz: Path | None = None) -> list[FilaReferencia]:
    """Sugerencias de la referencia MaPreX para autocompletar una fila de la composición.

    MaPreX es referencia de mercado, no verdad (spec §3.4,
    `docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md`): esta función busca
    y sugiere; la Tarea 3 la muestra en pantalla, y quien compone decide si usa el precio
    sugerido, lo edita o lo ignora. Autocompletar `factor_depreciacion` desde una sola fuente es
    lo que evita que dos personas le den un factor distinto al mismo insumo en dos APU, que es
    exactamente lo que vigila la regla R6 (`CriterioDepreciacion`).

    Lee los cuatro `referencia_*.csv` de `data/precios/maprex_2026-07/` con el módulo `csv` de la
    biblioteca estándar (este módulo no importa `pandas` ni `streamlit`) y filtra por `tipo`
    exacto (`material`, `equipo` o `mano_obra`, los tres únicos que trae el archivo) y por
    coincidencia de subcadena de `texto` contra la descripción (columna `insumo`). Ambos se
    comparan ya normalizados con `normalizar_texto` (`core/verification/texto.py`, la única
    normalización de texto del repositorio) para que "tuberia" encuentre "TUBERÍA" sin importar
    mayúsculas ni acentos.

    Devuelve las filas en el orden en que aparecen leyendo los archivos civil, telecom,
    industrial y sistemas (el mismo orden que `scripts/lista_maprex_usd.py`), o una lista vacía
    si nada coincide: nunca `None` ni una excepción.

    `raiz` es la raíz del repositorio; por defecto, la que resulta de la ubicación de este
    archivo (`ui/composicion.py` está a un nivel de la raíz, igual que `scripts/*.py`). Las
    pruebas pueden pasar otra para apuntar a un directorio distinto.
    """
    carpeta = (raiz if raiz is not None else _RAIZ_REPOSITORIO) / _CARPETA_REFERENCIA
    objetivo = normalizar_texto(texto)
    encontradas: list[FilaReferencia] = []
    for nombre in _ARCHIVOS_REFERENCIA:
        with (carpeta / nombre).open(newline="", encoding="utf-8") as archivo:
            for fila in csv.DictReader(archivo):
                if fila["tipo"] != tipo:
                    continue
                if objetivo not in normalizar_texto(fila["insumo"]):
                    continue
                encontradas.append(_fila_referencia_desde_csv(fila))
    return encontradas


# --- Autocompletado de una fila de la pantalla desde una FilaReferencia (Tarea 3) --------------
#
# La página (`ui/paginas/componer.py`) pinta el buscador y decide cuándo agregar una fila; estas
# funciones deciden QUÉ va en esa fila, que es la parte con lógica y por eso vive aquí, no allá
# (spec §4). Los tres `fila_*_desde_referencia` dejan `cantidad` en blanco a propósito: la
# referencia de mercado no puede saber cuánto de ese insumo consume ESTA partida, solo su precio
# (y, para equipos, su factor de depreciación).


def etiqueta_referencia(fila: FilaReferencia) -> str:
    """Rótulo legible de una `FilaReferencia` para el selector de resultados de la búsqueda.

    Un factor de depreciación o un bono de alimentación en cero es un dato (una fracción o un
    bono declarados como cero), no una ausencia: por eso la comparación es `is not None` y no la
    verdad de Python (`Decimal("0.00")` es falsy). Sin esto, las filas de mano de obra de
    `referencia_sistemas.csv` (`bono_bs="0.00"`, a diferencia de las de civil e industrial, que
    traen un monto real) se pintarían como "sin dato" cuando en realidad el dato es cero.
    """
    partes = [f"{fila.descripcion} — {fila.precio_usd} USD/{fila.unidad}"]
    if fila.factor_depreciacion is not None:
        partes.append(f"depreciación {fila.factor_depreciacion}")
    if fila.bono_bs is not None:
        partes.append(f"bono {fila.bono_bs} Bs")
    partes.append(f"ref. {fila.ref_maprex}")
    return " · ".join(partes)


def fila_materiales_desde_referencia(fila: FilaReferencia) -> dict[str, str]:
    """Autocompleta una fila de la tabla de materiales: descripción, unidad y precio.

    El precio queda editable (spec §3.4, MaPreX es referencia de mercado y no verdad): esta
    función solo propone el valor inicial de la celda en el `st.data_editor` de siempre.
    """
    return {
        "descripcion": fila.descripcion,
        "unidad": fila.unidad,
        "cantidad": "",
        "precio": str(fila.precio_usd),
    }


def fila_equipos_desde_referencia(fila: FilaReferencia) -> dict[str, str]:
    """Autocompleta una fila de equipos, incluido el factor de depreciación (regla R6).

    Tomar `depreciacion` de una sola fuente para todas las partidas es lo que evita que dos
    personas le den un factor distinto al mismo equipo en dos APU
    (`tests/integration/test_composicion_r6.py`).
    """
    depreciacion = "" if fila.factor_depreciacion is None else str(fila.factor_depreciacion)
    return {
        "descripcion": fila.descripcion,
        "cantidad": "",
        "precio": str(fila.precio_usd),
        "depreciacion": depreciacion,
    }


def fila_mano_obra_desde_referencia(fila: FilaReferencia) -> dict[str, str]:
    """Autocompleta una fila de mano de obra: `precio_usd` de la referencia es el sueldo diario.

    `modalidad` queda en blanco (el contrato la interpreta como JORNAL, `ModalidadManoObra`):
    a destajo o no es una decisión del proyecto, no un dato de la referencia de mercado.
    """
    return {
        "descripcion": fila.descripcion,
        "cantidad": "",
        "sueldo": str(fila.precio_usd),
        "modalidad": "",
    }


# --- Ayudas de AREN.IA (Tarea 4, spec §3.7): sugieren, nunca deciden ----------------------------
#
# Las cuatro funciones de esta sección envuelven una llamada a `ml/` (o, para la ayuda 3, la
# lectura adicional de `ml.anomaly` sobre el rendimiento ya cableado en la Tarea 1,
# `ui/paginas/componer.py`) de modo que un fallo -- el extra `ml` ausente, sin red para descargar
# el modelo semántico, un error aritmético del bosque de aislamiento -- degrade siempre a "sin
# sugerencia", nunca a una excepción que interrumpa la página ni impida guardar: la condición de
# diseño es absoluta (spec §3.7, "todas sugerencia y ninguna bloqueante"; quien compone decide,
# nunca el sistema). El import de cada submódulo de `ml` ocurre dentro de un `_importar_*`
# perezoso (mismo criterio que `ui/paginas/similares.py::_cargar_normalizacion`, para que la
# interfaz siga arrancando sin el extra `ml`), inyectable por parámetro para que las pruebas lo
# sustituyan por un doble sin instalar ni desinstalar nada real
# (`tests/unit/test_composicion_ia.py`).

#: Clave sintética de la variación implícita del precio recién tecleado (ayuda 2): no es un
#: `CambioPrecio` real, así que no puede colisionar con un id de la base (todos son enteros).
_ID_CANDIDATO_PRECIO = "candidato-precio-tecleado"


def _importar_normalizacion() -> ModuleType:
    import ml.normalization

    return ml.normalization


def _importar_anomalia() -> ModuleType:
    import ml.anomaly

    return ml.anomaly


def _importar_prediccion() -> ModuleType:
    import ml.prediction

    return ml.prediction


def sugerir_partidas_similares(
    partidas: Mapping[str, str],
    descripcion: str,
    cargar_normalizacion: Callable[[], ModuleType] = _importar_normalizacion,
) -> list[PartidaSimilar]:
    """Ayuda 1 (spec §3.7): partidas del catálogo parecidas a la descripción tecleada, para partir
    de algo en vez de una tabla vacía (reutiliza la similitud semántica de UC-03,
    `ml.normalization.NormalizadorPartidas`, desde la composición a mano).

    Nunca decide por la persona ni llena ninguna tabla: solo devuelve la lista de propuestas
    (posiblemente vacía) para que la página las muestre de solo lectura. La respuesta es una lista
    vacía sin descripción, sin catálogo, o si `cargar_normalizacion` falla por cualquier motivo (el
    extra `ml` ausente, sin red para el modelo, o cualquier otro error): la persona sigue con la
    tabla en blanco, exactamente como sin esta ayuda.
    """
    if not descripcion.strip() or not partidas:
        return []
    try:
        normalizacion = cargar_normalizacion()
        normalizador = normalizacion.NormalizadorPartidas(partidas)
        return list(normalizador.similares(descripcion))
    except Exception:
        return []


def advertencia_precio_atipico(
    historico: Mapping[str, Decimal],
    precio_anterior: Decimal | None,
    precio_nuevo: Decimal,
    cargar_anomalia: Callable[[], ModuleType] = _importar_anomalia,
) -> bool:
    """Ayuda 2 (spec §3.7): si el precio recién tecleado resulta atípico frente al histórico de
    variaciones de ese insumo (la página lo arma con `core.catalog.cambios_precio`).

    Construye la variación implícita `(precio_nuevo - precio_anterior) / precio_anterior` y le
    pide a `ml.anomaly.precios_atipicos` que la juzgue junto con el histórico real, exactamente
    como esa función juzga cualquier otra variación (no hay un atajo de una sola observación: por
    debajo de `ml.anomaly.MINIMO_OBSERVACIONES` el módulo ya se abstiene por su cuenta). Sin un
    precio anterior conocido no hay variación que calcular y la respuesta es "no es atípico"
    (`False`), igual que si `ml` fallara por cualquier motivo. Solo avisa; nunca corrige el precio
    tecleado.
    """
    if precio_anterior is None or precio_anterior == 0:
        return False
    variacion = (precio_nuevo - precio_anterior) / precio_anterior
    try:
        anomalia = cargar_anomalia()
        serie = {**historico, _ID_CANDIDATO_PRECIO: variacion}
        atipicos = anomalia.precios_atipicos(serie)
    except Exception:
        return False
    return any(atipico.id == _ID_CANDIDATO_PRECIO for atipico in atipicos)


def veredicto_ml_rendimiento(
    observados: Sequence[Decimal],
    valor: Decimal,
    cargar_anomalia: Callable[[], ModuleType] = _importar_anomalia,
) -> VeredictoRendimiento | None:
    """Ayuda 3 (spec §3.7): la lectura estadística de `ml.anomaly` sobre el rendimiento tecleado,
    que se suma (no sustituye) al aviso por rango de `core.catalog.advertencia_rendimiento`
    (Tarea 1, ya cableado en `ui/paginas/componer.py`).

    `None` si no hay observaciones suficientes (el propio módulo se abstiene por debajo de
    `ml.anomaly.MINIMO_OBSERVACIONES`, un juicio estadístico declarado) o si `ml` no está
    disponible o falla por cualquier razón: en cualquiera de los dos casos el rendimiento se
    registra igual, sin esta advertencia adicional.
    """
    try:
        anomalia = cargar_anomalia()
        return anomalia.evaluar_rendimiento(observados, valor)
    except Exception:
        return None


@dataclass(frozen=True, slots=True)
class ContrasteAace:
    """El resultado de la ayuda 4: la técnica que dicta la compuerta G2 y el hallazgo AACE, si lo
    hay. `hallazgo` es `None` cuando el precio construido cae dentro de la clase 3 declarada.
    """

    tecnica: str
    pu_estimado: Decimal
    hallazgo: Hallazgo | None


def contrastar_precio_con_reglas(
    codigo_partida: str,
    pu_construido: Decimal,
    pu_anterior: Decimal,
    variaciones: Sequence[Decimal],
    registros: int,
    cargar_prediccion: Callable[[], ModuleType] = _importar_prediccion,
) -> ContrasteAace | None:
    """Ayuda 4 (spec §3.7): al terminar la composición, contrasta el precio unitario obtenido
    contra la estimación por reglas (UC-07, compuerta G2) y devuelve el marco AACE del resultado.

    `pu_anterior` es el PU vigente de la partida ANTES de esta edición: la regla de
    `ml.prediction.predecir_por_reglas` no conoce la composición nueva (esa es la verdad de
    terreno del motor de `core.costing`, contra la que se mide) y solo proyecta un precio base con
    la variación media del histórico, declarado como limitación en `ml/prediction/reglas.py`. Sin
    un PU anterior conocido (partida nueva, UC-10) no hay base que proyectar y esta ayuda no
    aplica: la página no la invoca en ese caso. `None` también si `ml` no está disponible o el
    cálculo falla por cualquier razón: el precio construido se guarda igual, con o sin este
    contraste.
    """
    try:
        prediccion_mod = cargar_prediccion()
        (prediccion,) = prediccion_mod.predecir_por_reglas(
            {codigo_partida: pu_anterior}, variaciones
        )
        hallazgo = prediccion_mod.contrastar_aace(
            codigo_partida, pu_construido, prediccion.pu_estimado
        )
        tecnica = prediccion_mod.tecnica_para(registros)
    except Exception:
        return None
    return ContrasteAace(
        tecnica=str(tecnica), pu_estimado=prediccion.pu_estimado, hallazgo=hallazgo
    )
