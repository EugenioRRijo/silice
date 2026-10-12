"""Revisar un paquete o un presupuesto externo, sin Streamlit (S3 §9 y §10, UC-23; RF-86/87).

Orquesta lo que `core`, `paquete`, `seguridad` y `adapters.espacio` no pueden orquestar entre sí.
Todo el análisis es **en memoria**: el paquete se reaudita con las reglas de ESTA instalación
sobre el documento canónico que trae (`canonico.leer`), sin cargarlo al catálogo ni escribir una
sola fila de las versiones del caso (DA-S3-7, maestro §3.3). Lo único que se guarda es el archivo
recibido (`datos\\paquetes\\`), su registro (`paq_recibido`) y el dictamen (`paq_dictamen`).

La reauditoría misma vive en `auditoria/` (RP8-6: la API no puede importar `ui`); aquí se reexporta
y se le suma lo propio de la vista: recibir, diferencias, quién cambió qué, quién revisa y Excel.
Recalcula cada precio unitario desde las composiciones del paquete (no se confía en los precios ni
en los totales escritos) y separa los hallazgos que el emisor **no declaró**, los que declaró y
**ya no aparecen** y los comunes. R16 no corre aquí (maestro §3.3).
"""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from auditoria.reauditoria import (
    LIMITE_SEGUNDOS,
    NOMBRE_CONTROL,
    NOMBRE_ESPACIO,
    DiferenciaDeclarada,
    Reauditoria,
    ReferenciaDeMercado,
    Servicios,
    instantanea_del_documento,
    leer_documento,
)
from auditoria.reauditoria import reauditar as _reauditar
from core import models
from core.budget import canonico
from core.budget.comparacion import (
    Diferencia,
    PrecioDeLista,
    Revaloracion,
    diferencia_entre_versiones,
    filas_de,
    revalorar,
)
from core.budget.excel import TablaExportable, exportar_hoja
from core.budget.importacion import (
    COLUMNAS_APU,
    COLUMNAS_CURVA,
    COLUMNAS_DATOS,
    COLUMNAS_INSUMOS,
    COLUMNAS_PRESUPUESTO,
    HOJA_APU,
    HOJA_CURVA,
    HOJA_DATOS,
    HOJA_INSUMOS,
    HOJA_PRESUPUESTO,
    leer_presupuesto_tabular,
)
from core.verification import REGLAS, auditar
from paquete import modelo as paq
from paquete.verificar import (
    RECHAZADO,
    EmpresaConocida,
    Verificacion,
    evaluar_anterioridad,
    verificar,
)
from seguridad import empresas
from seguridad.json_estricto import leer_json
from seguridad.modelo import EmpresaRegistrada
from ui.subidas import nombre_seguro

__all__ = [
    "LIMITE_SEGUNDOS",
    "DiferenciaDeclarada",
    "EntregaAnterior",
    "Recibido",
    "Reauditoria",
    "ReferenciaDeMercado",
    "Servicios",
    "auditar_excel_externo",
    "banner_de_version",
    "cambios_nuevos",
    "contra_la_base_del_revisor",
    "contra_la_entrega_anterior",
    "declaracion_retroactiva",
    "dictaminar",
    "empresa_propia_para_revisar",
    "entrega_anterior",
    "excel_de_presupuesto",
    "excel_de_revision",
    "instantanea_del_documento",
    "leer_documento",
    "login_de",
    "plantilla_uc05",
    "precios_de_lista",
    "reauditar",
    "recibir",
    "revisor_armo",
    "tablas_de_revision",
]

_CAMPOS_DE_CAMBIO = (
    "version",
    "objeto",
    "clave",
    "campo",
    "antes",
    "despues",
    "fuente",
    "responsable",
    "fecha",
    "marca",
)
_LOGIN = re.compile(r"<([^<>]+)>")
_NOMBRE_POR_OMISION = "paquete.silice"
_MARCA_RESTABLECIMIENTO = "(tras restablecimiento)"


def reauditar(
    v: Verificacion, servicios: Servicios, *, tiempo_maximo: float = LIMITE_SEGUNDOS
) -> Reauditoria:
    """La reauditoría de un paquete legible (todo menos «rechazado») a la FECHA DE EMISIÓN del
    manifiesto: el mismo paquete reauditado otro día da lo mismo (maestro §3.3)."""
    emision = _emitido(v.manifiesto).date()
    return _reauditar(
        leer_documento(v.archivos),
        servicios,
        emision,
        espacio_json=v.archivos.get(NOMBRE_ESPACIO),
        control_json=v.archivos.get(NOMBRE_CONTROL),
        tiempo_maximo=tiempo_maximo,
    )


def _emitido(manifiesto: Mapping[str, Any] | None) -> datetime:
    """La fecha de emisión del manifiesto, sin zona horaria (la base guarda fechas ingenuas)."""
    return datetime.fromisoformat(str((manifiesto or {})["emitido"])).replace(tzinfo=None)


# --- diferencia entre versiones -------------------------------------------------------------


def precios_de_lista(session: Session, lista: models.ListaPrecios) -> list[PrecioDeLista]:
    """Los precios de una lista de quien revisa, con su referencia de precio (Ref MaPreX)."""
    referencias = dict(
        session.execute(
            select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
        ).all()
    )
    return [
        PrecioDeLista(p.insumo.codigo, referencias.get(p.id, ""), p.precio) for p in lista.precios
    ]


def contra_la_entrega_anterior(
    actual: canonico.DocumentoLeido, anterior: canonico.DocumentoLeido
) -> Diferencia:
    return diferencia_entre_versiones(filas_de(anterior), filas_de(actual))


def contra_la_base_del_revisor(
    doc: canonico.DocumentoLeido, precios: Sequence[PrecioDeLista]
) -> tuple[Diferencia, Revaloracion]:
    """El paquete revalorado en memoria con la lista de quien revisa; lo que no empareja es
    «no contrastable» y no suma."""
    revalorado = revalorar(doc, precios)
    return diferencia_entre_versiones(filas_de(doc), revalorado.filas), revalorado


def declaracion_retroactiva(cadena: Mapping[str, Any]) -> str | None:
    """S3 §6.5: «Versiones 001 a 004 selladas el …», si la cadena del paquete trae eslabones
    retroactivos; `None` si no. Es la misma declaración de la hoja, leída del paquete."""
    retro = [e for e in cadena["eslabones"] if e.get("tipo") == "retroactivo"]
    if not retro:
        return None
    codigos = [e["codigo"] for e in retro]
    rango = codigos[0] if len(codigos) == 1 else f"{codigos[0]} a {codigos[-1]}"
    cuando = min(str(e["fecha_hora"]) for e in retro)[:10]
    plural = "Versión" if len(codigos) == 1 else "Versiones"
    return (
        f"{plural} {rango} selladas el {cuando}: prueban que no cambiaron desde esa fecha; "
        "antes no hay garantía."
    )


# --- quién cambió qué y quién revisa --------------------------------------------------------


def login_de(responsable: str) -> str | None:
    """`ana` de `Ana Pérez <ana> (tras restablecimiento)`; `None` si no hay `<login>`."""
    hallados = _LOGIN.findall(responsable or "")
    return hallados[-1] if hallados else None


def cambios_nuevos(
    cadena: Mapping[str, Any], huellas_previas: Sequence[str]
) -> list[dict[str, str]]:
    """Los `RegistroCambio` de las versiones que la entrega anterior no traía."""
    conocidas = set(huellas_previas)
    filas = []
    for e in cadena["eslabones"]:
        if e["huella_eslabon"] in conocidas:
            continue
        for fila in cadena.get("cambios", {}).get(e["codigo"], []):
            objeto, clave, campo, antes, despues, fuente, responsable, cuando = fila
            filas.append(
                {
                    "version": e["codigo"],
                    "objeto": objeto,
                    "clave": clave,
                    "campo": campo,
                    "antes": antes,
                    "despues": despues,
                    "fuente": fuente,
                    "responsable": responsable,
                    "fecha": cuando,
                    "marca": "hecho tras un restablecimiento del administrador"
                    if _MARCA_RESTABLECIMIENTO in responsable
                    else "",
                }
            )
    return filas


def revisor_armo(
    v: Verificacion, *, login_revisor: str, empresa_propia: tuple[str | None, str | None]
) -> list[str]:
    """Las versiones en que quien revisa figura como quien armó (P2, ratificada): solo si el
    paquete es de la empresa propia (firmado con su clave, o sin firma con su nombre) y su login
    es el del usuario emisor o el de algún eslabón. Vacío si no."""
    if v.manifiesto is None or v.cadena is None:
        return []
    nombre, huella = empresa_propia
    huella_clave = v.manifiesto.get("huella_clave")
    propia = (huella_clave is not None and huella_clave == huella) or (
        huella_clave is None and nombre is not None and v.manifiesto.get("empresa") == nombre
    )
    if not propia:
        return []
    donde = [
        e["codigo"]
        for e in v.cadena["eslabones"]
        if login_de(e.get("usuario", "")) == login_revisor
    ]
    emisor = login_de(str(v.manifiesto.get("usuario_emisor") or ""))
    if emisor == login_revisor and not donde:
        donde = [str(v.manifiesto["codigo"])]
    return donde


# --- recibir, guardar y dictaminar ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Recibido:
    verificacion: Verificacion
    paquete_id: int
    ruta: Path
    ya_recibido: bool
    avisos: tuple[str, ...]
    ultima_recibida: str  # «versión 004 del 2026-11-03» o «» si es la primera
    ya_recibido_el: str = ""  # el día en que se recibió este mismo archivo, si ya se había


def banner_de_version(r: Recibido) -> str:
    """El banner de versión, siempre (S3 §8.3 paso 7): «Versión 005 del 2026-11-10; la última que
    usted recibió de este proyecto: versión 004 del 2026-11-03», o «es la primera que recibe», o
    «ya recibió este mismo paquete el …». Lo que viene del paquete lo escapa quien lo pinta."""
    m = r.verificacion.manifiesto or {}
    inicio = f"Versión {m.get('codigo', '')} del {str(m.get('emitido', ''))[:10]}"
    if r.ya_recibido:
        return f"{inicio}; ya recibió este mismo paquete el {r.ya_recibido_el}."
    if r.ultima_recibida:
        return f"{inicio}; la última que usted recibió de este proyecto: {r.ultima_recibida}."
    return f"{inicio}; es la primera que recibe de este proyecto."


def _buscar_empresa(instalacion: Session):
    def buscar(huella: str) -> EmpresaConocida | None:
        fila = instalacion.scalars(
            select(EmpresaRegistrada)
            .where(EmpresaRegistrada.huella == huella)
            .order_by(EmpresaRegistrada.id.desc())
        ).first()
        if fila is None:
            return None
        return EmpresaConocida(fila.empresa, fila.publica, fila.estado, fila.fecha_estado)

    return buscar


def _nombre_de_archivo(nombre: str) -> str:
    try:
        return nombre_seguro(nombre)
    except ValueError:
        return _NOMBRE_POR_OMISION


def _huellas_de_anexos(archivos: Mapping[str, bytes]) -> dict[str, list[str]]:
    """Las huellas de entradas de los anexos con cadena propia (S3 §6.5). Un anexo con la forma
    equivocada no tiene entradas que comparar: no rompe la recepción."""
    salida: dict[str, list[str]] = {}
    for nombre in ("anexos/reajuste.json", NOMBRE_CONTROL):
        if nombre not in archivos:
            continue
        try:
            entradas = leer_json(archivos[nombre]).get("entradas", [])
            salida[nombre] = [str(e["huella"]) for e in entradas]
        except (ValueError, KeyError, TypeError, AttributeError):
            salida[nombre] = []
    return salida


def recibir(
    datos: bytes,
    nombre: str,
    *,
    caso: Session,
    instalacion: Session,
    carpeta_paquetes: Path,
    revisor: str,
    ahora: datetime,
    mi_empresa: tuple[str | None, str | None] = (None, None),
) -> Recibido:
    """Verifica `datos`, guarda el archivo y su registro (una vez por SHA-256: 23h) y evalúa la
    anterioridad respecto de lo ya recibido. Un paquete «rechazado» no se guarda."""
    v = verificar(
        datos, buscar_empresa=_buscar_empresa(instalacion), recibido_en=ahora, mi_empresa=mi_empresa
    )
    if not v.legible or v.cadena is None or v.manifiesto is None:
        return Recibido(v, 0, Path(), False, (), "")
    m = v.manifiesto
    try:
        emitido = _emitido(m)
        proyecto, codigo, paquete_id = str(m["proyecto"]), str(m["codigo"]), str(m["paquete_id"])
        eslabones = [[e["codigo"], e["huella_eslabon"]] for e in v.cadena["eslabones"]]
    except (KeyError, ValueError, TypeError):
        malo = replace(
            v,
            estado=RECHAZADO,
            motivo="rechazado",
            detalle="El manifiesto o la cadena no traen los datos mínimos de un paquete.",
        )
        return Recibido(malo, 0, Path(), False, (), "")
    existente = paq.buscar_por_huella(caso, v.sha256)
    huella_clave = str(m.get("huella_clave") or "")
    previos = paq.paquetes_del_proyecto(caso, proyecto, huella_clave)
    anexos_huellas = _huellas_de_anexos(v.archivos)
    anterioridad = evaluar_anterioridad(m, v.cadena, anexos_huellas, v.sha256, previos)
    avisos = (*v.avisos, *anterioridad.avisos)
    if existente is not None:
        return Recibido(
            v,
            existente["id"],
            Path(existente["ruta"]),
            True,
            avisos,
            anterioridad.ultima_recibida,
            existente["fecha"].date().isoformat(),
        )
    carpeta_paquetes.mkdir(parents=True, exist_ok=True)
    archivo = _nombre_de_archivo(nombre)
    ruta = carpeta_paquetes / f"{v.sha256}-{archivo}"
    ruta.write_bytes(datos)
    identificador = paq.registrar_recibido(
        caso,
        archivo=archivo,
        huella_archivo=v.sha256,
        paquete_id=paquete_id,
        destinatario=str(m.get("destinatario") or ""),
        ruta=str(ruta),
        empresa_declarada=str(v.empresa_declarada or ""),
        empresa_verificada=str(v.empresa_verificada or ""),
        huella_clave=huella_clave,
        estado=v.estado,
        proyecto=proyecto,
        codigo=codigo,
        emitido=emitido,
        cadena=json.dumps(eslabones),
        huellas_anexos=json.dumps(anexos_huellas),
        recibido_por=revisor,
        fecha=ahora,
    )
    caso.commit()
    return Recibido(v, identificador, ruta, False, avisos, anterioridad.ultima_recibida)


def dictaminar(
    caso: Session,
    recibido: Recibido,
    *,
    resultado: str,
    notas: str,
    revisor: str,
    ahora: datetime,
    armo: bool,
) -> int:
    """El dictamen, atado al SHA-256 del archivo y al estado de verificación de ESE momento."""
    identificador = paq.registrar_dictamen(
        caso,
        paquete_id=recibido.paquete_id,
        huella_archivo=recibido.verificacion.sha256,
        resultado=resultado,
        notas=notas,
        usuario=revisor,
        fecha=ahora,
        estado_verificacion=recibido.verificacion.estado,
        revisor_armo=armo,
    )
    caso.commit()
    return identificador


@dataclass(frozen=True, slots=True)
class EntregaAnterior:
    """Lo que esta instalación recibió antes del mismo proyecto y emisor (maestro §3.3)."""

    codigo: str
    documento: canonico.DocumentoLeido
    huellas: tuple[str, ...]  # las huellas de eslabón que esa entrega ya traía


def entrega_anterior(
    caso: Session, instalacion: Session, v: Verificacion
) -> EntregaAnterior | None:
    """La última entrega del mismo proyecto y emisor emitida ANTES de `v`, releída del archivo
    guardado (con el mismo lector seguro). `None` si no hay, o si el archivo ya no está."""
    if v.manifiesto is None:
        return None
    emitido = _emitido(v.manifiesto)
    previas = [
        f
        for f in paq.paquetes_del_proyecto(
            caso, str(v.manifiesto["proyecto"]), str(v.manifiesto.get("huella_clave") or "")
        )
        if f["huella_archivo"] != v.sha256 and f["emitido"] < emitido
    ]
    if not previas:
        return None
    fila = max(previas, key=lambda f: f["emitido"])
    ruta = Path(fila["ruta"])
    if not ruta.is_file():
        return None
    antes = verificar(
        ruta.read_bytes(), buscar_empresa=_buscar_empresa(instalacion), recibido_en=fila["fecha"]
    )
    if not antes.legible:
        return None
    return EntregaAnterior(
        fila["codigo"],
        leer_documento(antes.archivos),
        tuple(huella for _, huella in json.loads(fila["cadena"])),
    )


def empresa_propia_para_revisar(instalacion: Session) -> tuple[str | None, str | None]:
    """`(nombre, huella de la clave activa)` de la empresa de esta instalación, para el aviso de
    «quien revisa es quien armó»; `None` donde falte."""
    propia = empresas.empresa_propia(instalacion)
    clave = empresas.clave_activa(instalacion)
    return (propia.nombre if propia else None, clave.huella if clave else None)


# --- tablas y Excel -------------------------------------------------------------------------


def tablas_de_revision(
    v: Verificacion,
    r: Reauditoria,
    diferencia: Diferencia | None,
    cambios: Sequence[dict],
) -> tuple[TablaExportable, ...]:
    """Las hojas Verificación, Hallazgos, Diferencias y Cambios (todo texto con el escape de M-1
    de `exportar_hoja`)."""
    verificacion = TablaExportable(
        "Verificación",
        ("Dato", "Valor"),
        (
            ("Estado", v.estado),
            ("Motivo", v.motivo),
            ("Detalle", v.detalle),
            ("Empresa declarada", v.empresa_declarada or ""),
            ("Empresa verificada", v.empresa_verificada or ""),
            ("SHA-256", v.sha256),
            *(("Aviso", a) for a in v.avisos),
        ),
    )
    hallazgos = TablaExportable(
        "Hallazgos",
        ("Origen", "Regla", "Severidad", "Descripción"),
        tuple(
            (origen, h.regla, h.severidad.name, h.descripcion)
            for origen, lote in (
                ("No declarado por el emisor", r.nuevos),
                ("Declarado y ya no aparece", r.ya_no),
                ("Común", r.comunes),
            )
            for h in lote
        ),
    )
    filas = (
        tuple(
            (
                p.codigo_partida,
                p.descripcion,
                p.estado,
                p.desvio_cantidad,
                p.desvio_precio,
                p.desvio_total,
            )
            for p in diferencia.partidas
        )
        if diferencia
        else ()
    )
    return (
        verificacion,
        hallazgos,
        TablaExportable(
            "Diferencias",
            ("Partida", "Descripción", "Estado", "Δ cantidad", "Δ precio", "Δ total"),
            filas,
        ),
        TablaExportable(
            "Cambios",
            (
                "Versión",
                "Objeto",
                "Clave",
                "Campo",
                "Antes",
                "Después",
                "Fuente",
                "Responsable",
                "Fecha",
                "Marca",
            ),
            tuple(tuple(c[k] for k in _CAMPOS_DE_CAMBIO) for c in cambios),
        ),
    )


def excel_de_presupuesto(r: Reauditoria, *, extras: Sequence[TablaExportable] = ()) -> bytes:
    """El Excel del presupuesto del paquete REGENERADO desde `presupuesto.json` con
    `exportar_hoja` en esta instalación; nunca el del emisor (DA-S3-10)."""
    if r.resultado is None:
        raise ValueError("la reauditoría no terminó: no hay presupuesto que exportar")
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "presupuesto.xlsx"
        exportar_hoja(
            r.resultado.presupuesto,
            r.resultado.informe,
            ruta,
            r.documento.parametros,
            hojas_extra=tuple(extras),
        )
        return ruta.read_bytes()


def excel_de_revision(
    v: Verificacion, r: Reauditoria, diferencia: Diferencia | None, cambios: Sequence[dict]
) -> bytes:
    return excel_de_presupuesto(r, extras=tablas_de_revision(v, r, diferencia, cambios))


# --- presupuesto externo en Excel (UC-05, 23d) y su plantilla ---------------------------------


def plantilla_uc05() -> bytes:
    """La plantilla descargable del formato UC-05: las cinco hojas de `core.budget.importacion`
    (su fuente única) y una fila de ejemplo en cada una."""
    libro = Workbook()
    datos = libro.active
    datos.title = HOJA_DATOS
    filas = {
        HOJA_DATOS: [
            COLUMNAS_DATOS,
            ("codigo", "EJ-001"),
            ("fecha", "2026-11-01"),
            ("moneda", "USD"),
            ("dominio", "civil"),
            ("fcas", "6.00"),
            ("bono_alimentacion", "1.00"),
            ("administracion", "0.15"),
            ("utilidad", "0.10"),
        ],
        HOJA_PRESUPUESTO: [
            COLUMNAS_PRESUPUESTO,
            ("EJ-P1", "Relleno de ejemplo", "m3", "20", "FILA-1", "", "{}", "{}"),
        ],
        HOJA_APU: [COLUMNAS_APU, ("EJ-P1", "Relleno de ejemplo", "m3", "8")],
        HOJA_INSUMOS: [
            COLUMNAS_INSUMOS,
            ("EJ-P1", "material", "Arena", "m3", "1.00", "14.00", "", ""),
            ("EJ-P1", "equipo", "Compactadora", "", "1", "71.00", "0.10", ""),
            ("EJ-P1", "mano de obra", "Obrero", "", "2", "10.25", "", "jornal"),
        ],
        HOJA_CURVA: [COLUMNAS_CURVA, ("Dia 1", "836.7975", "836.7975")],
    }
    for nombre, lineas in filas.items():
        hoja = datos if nombre == HOJA_DATOS else libro.create_sheet(nombre)
        for linea in lineas:
            hoja.append(list(linea))
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "plantilla.xlsx"
        libro.save(ruta)
        return ruta.read_bytes()


def auditar_excel_externo(ruta: Path):
    """UC-05 sin persistir: lee SOLO valores (nunca fórmulas ni vínculos externos) y audita en
    memoria con `REGLAS`. Siempre «no verificado»: un Excel no trae cadena ni firma."""
    importado = leer_presupuesto_tabular(ruta)
    return importado, auditar(importado.presupuesto, REGLAS)
