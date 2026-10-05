"""Piezas comunes de las reglas de cantidades por especialidad (agua, datos y electricidad).

Lo que las tres especialidades hacen igual vive aquí una sola vez (NORMAS.md §2, DRY): el
`origen_id` acotado, las etiquetas de la descripción, la construcción del `ItemComputo` y la
elección del valor (material, tipo de canalización) de un segmento compartido.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal

from adapters.espacio.especialidades import SUPUESTO_DECLARADO, Constante, porcentaje
from adapters.espacio.geometria import magnitud_diametro, normalizar_diametro
from adapters.espacio.modelo import Punto
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo

UNIDAD_LONGITUD = "m"
UNIDAD_CONTEO = "u"
UNIDAD_PIEZA = "pieza"
UNIDAD_PUNTO = "punto"
CERO = Decimal(0)
UNO = Decimal(1)

#: Constantes que comparten datos y electricidad (memoria `of001.md`, sección 5): un solo lugar.
D12 = Constante("D-12", "Tipo de canalización por defecto", "EMT", SUPUESTO_DECLARADO)
D17 = Constante(
    "D-17",
    "Desperdicio de cajas, salidas, jacks, certificación y protección (conteo exacto)",
    Decimal("0"),
    SUPUESTO_DECLARADO,
)
D18 = Constante(
    "D-18",
    "Desperdicio de la canalización de datos y de la tubería eléctrica",
    Decimal("0"),
    SUPUESTO_DECLARADO,
)
CANALIZACION_POR_DEFECTO = str(D12.valor)
DESPERDICIO_CONTEO = Decimal(D17.valor)
DESPERDICIO_CANALIZACION = Decimal(D18.valor)

#: `core/models/entidades.py`: `origen_id` es `String(120)`.
LIMITE_ORIGEN = 120


def origen(principales: Iterable[str], secundarios: Iterable[str]) -> str:
    """`origen_id` de a lo más 120 caracteres, determinista y trazable hasta la fuente.

    Cita primero las referencias principales (fuentes) y luego las secundarias (segmentos o
    puntos), cada grupo ordenado, mientras quepan; las que no caben se resumen en un sufijo `;+N`.
    La lista completa no se guarda (el contrato no tiene dónde): se recalcula desde la fuente.
    """
    refs = sorted(set(principales))
    refs += sorted(set(secundarios) - set(refs))
    elegidas: list[str] = []
    largo = 0
    for i, ref in enumerate(refs):
        nuevo = largo + (1 if elegidas else 0) + len(ref)
        reserva = len(f";+{len(refs)}") if i < len(refs) - 1 else 0
        if nuevo + reserva > LIMITE_ORIGEN:
            break
        elegidas.append(ref)
        largo = nuevo
    if not elegidas:  # una sola referencia desmedida: se corta, no se desborda
        elegidas = [refs[0][: LIMITE_ORIGEN - 8]]
    omitidas = len(refs) - len(elegidas)
    texto = ";".join(elegidas)
    return f"{texto};+{omitidas}" if omitidas else texto


def codigo_diametro(diametro: str | None) -> str:
    return diametro.replace(" ", "-") if diametro else "SIN-DIAMETRO"


def texto_diametro(diametro: str | None) -> str:
    return f'{diametro}"' if diametro else "sin diámetro declarado"


def etiqueta(c: Constante) -> str:
    """`desperdicio 10 %: supuesto declarado` para la descripción de un ítem."""
    return f"desperdicio {porcentaje(Decimal(c.valor))}: {c.fuente}"


def item(
    codigo: str,
    descripcion: str,
    unidad: str,
    cantidad: Decimal,
    principales: Iterable[str],
    secundarios: Iterable[str],
    regla: str,
    parametros: dict[str, Decimal],
    especificaciones: dict[str, str],
    dominio: Dominio,
    especialidad: str | None = None,
) -> ItemComputo:
    """Un `ItemComputo` de origen REGLA. Con `especialidad`, la anota en la directiva
    `_especialidad` (DA-SF-3); R4 ignora las claves que empiezan por `_`."""
    if especialidad is not None:
        especificaciones = {**especificaciones, "_especialidad": especialidad}
    return ItemComputo(
        codigo_partida=codigo,
        descripcion=descripcion,
        unidad=unidad,
        cantidad=cantidad,
        origen_id=origen(principales, secundarios),
        origen_tipo=OrigenTipo.REGLA,
        dominio=dominio,
        regla=regla,
        parametros=parametros,
        especificaciones=especificaciones,
    )


def datos_de_valor(puntos: Mapping[str, Punto], clave: str) -> dict[str, tuple[int, str]]:
    """Por punto: rango de la magnitud de su diámetro (-1 vale lo que no declara; los rangos
    conservan el orden de las magnitudes, así la comparación por segmento es entre enteros) y el
    valor de su especificación `clave` en mayúsculas ('' si no la declara). Se calcula una vez por
    derivación, no por segmento (RNF-11)."""
    magnitudes = {
        i: magnitud_diametro(d) if (d := normalizar_diametro(p.espec.get("diametro"))) else -1
        for i, p in puntos.items()
    }
    rango = {m: r for r, m in enumerate(sorted(set(magnitudes.values())))}
    return {
        i: (rango[m], puntos[i].espec.get(clave, "").strip().upper()) for i, m in magnitudes.items()
    }


def valor_de(
    sirve: Iterable[str], datos: Mapping[str, tuple[int, str]], por_defecto: str
) -> tuple[str, bool]:
    """Valor (material, tipo de canalización) de un segmento y si es el de por defecto.

    Entre los que sirven de mayor diámetro, el primero en orden alfabético de los valores
    declarados: no depende de los ids ni del orden de entrada."""
    servidos = [datos[i] for i in sirve if i in datos]
    mayor = max((m for m, _ in servidos), default=-1)
    declarados = sorted(valor for m, valor in servidos if m == mayor and valor)
    if declarados:
        return declarados[0], False
    return por_defecto, True
