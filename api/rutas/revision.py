"""«Revisar un paquete» por la API (T7 de la migración final; UC-23, RF-86, RF-87; S3 §8.3-§10).

Es la página `ui/paginas/revisar.py` hecha servicio, sobre `aplicacion.revision` (la misma lógica y
los mismos textos que usa Streamlit):

- `POST /v1/revision/paquete` (multipart `paquete` y, opcional, `lista`): verifica el `.silice`
  (formato con límites, integridad, firma con la clave registrada y cadena), registra lo recibido
  una vez por SHA-256 (archivo en `datos\\paquetes\\` y fila `paq_recibido`, como la clásica), lo
  reaudita **en memoria** a la fecha de emisión y responde lo que la pantalla clásica muestra.
  Un archivo «rechazado» responde 200 con su banner (es el resultado de la verificación) y no se
  guarda; un documento con la forma equivocada es 422 con el mensaje de la clásica.
- `POST /v1/revision/contra-lista` (`paquete`, `lista`): el contraste con otra lista del caso.
- `POST /v1/revision/dictamen` (`paquete`, `resultado`, `notas`): el dictamen atado al SHA-256 del
  archivo y a su estado de verificación de ese momento. Lo da una persona: la clave de API no
  sirve (403).
- `POST /v1/revision/excel` (`paquete`, `tipo` = `presupuesto` | `revision`): el Excel regenerado
  en esta instalación desde `presupuesto.json` (el del emisor no viaja y no se ofrece).
- `GET /v1/revision/plantilla` y `POST /v1/revision/excel-externo` (`presupuesto`): la pestaña
  «Presupuesto en Excel» (UC-05, en memoria y siempre «no verificado»).

Todas exigen `REVISAR_PAQUETE` (rol revisa) con la sesión del navegador (CSRF y `Origin` en los
POST) o la clave de API, y responden `Cache-Control: no-store`. La interfaz nueva no guarda nada
entre peticiones: cada acción vuelve a subir el archivo, que se verifica otra vez (el registro no
se duplica). Subidas con tope: el paquete hasta 20 MiB (`paquete.formato.LIMITE_ARCHIVO`, el mismo
tope del cuerpo entero de `api.proteccion`) y después la guardia del formato (`abrir_zip`: nombres,
bomba de compresión, cifrado); el Excel externo pasa por `adapters.hoja_empresa.guardia` antes de
`openpyxl`. El 422 de validación no repite lo enviado (`RutaSinEco`). Los montos viajan como texto:
el exacto y, en `*_texto`, como los escribe la clásica (dos decimales; cuatro en lo declarado y lo
recalculado de una diferencia de precio).
"""

from __future__ import annotations

import re
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from adapters.hoja_empresa.guardia import MAX_BYTES, ArchivoRechazado, verificar_archivo
from api.archivos import nombre_seguro
from api.dependencias import USUARIO_SIN_CLAVE, SesionDep
from api.proteccion import LIMITE_CUERPO
from api.redaccion import pulir
from api.rutas.auditorias import ServiciosDep
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import revision as logica
from core import models
from core.budget.comparacion import Diferencia
from core.verification.texto import formatear_decimal
from operacion.config import carpeta_datos
from operacion.instalacion import sesion_de_instalacion
from paquete import modelo as paq
from paquete.formato import LIMITE_ARCHIVO, PaqueteRechazado
from paquete.verificar import banner
from seguridad.json_estricto import JsonRechazado
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

TOPE_PAQUETE = LIMITE_ARCHIVO  # 20 MiB: lo que `abrir_zip` admite
TOPE_EXCEL = min(MAX_BYTES, LIMITE_CUERPO)  # 20 MiB: el cuerpo entero no pasa de ahí
MENSAJE_TOPE_PAQUETE = (
    "El archivo pesa más de 20 MiB, el máximo de un paquete. Pida al emisor un paquete más pequeño."
)
MENSAJE_TOPE_EXCEL = "El presupuesto en Excel supera el máximo de 20 MiB."
MENSAJE_CUERPO_INVALIDO = (
    "Suba el archivo .silice que recibió; la lista se indica por su número, el dictamen es "
    "conforme, con observaciones o rechazado, y el Excel, presupuesto o revision."
)
MENSAJE_RESULTADO = "Elija el dictamen: conforme, con observaciones o rechazado."
MENSAJE_SOLO_PERSONA = (
    "El dictamen lo da una persona: entre con una cuenta que revisa; la clave de API no sirve."
)
MENSAJE_LISTA = "La lista {id} no existe en este caso."
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SIN_CACHE = {"Cache-Control": "no-store"}  # lo recibido y su análisis no se guardan en el navegador
ERRORES_DEL_PAQUETE = (PaqueteRechazado, JsonRechazado, ValueError)  # la clásica: `st.error(str())`


class _RutaRevision(RutaSinEco):
    mensaje_por_omision = MENSAJE_CUERPO_INVALIDO


router = APIRouter(prefix="/v1/revision", tags=["revision"], route_class=_RutaRevision)
REVISAR = Depends(exigir_clave_o_sesion(Accion.REVISAR_PAQUETE))
Activa = Annotated[SesionActiva | None, REVISAR]


# --- esquemas -------------------------------------------------------------------------------


class HallazgoRevision(BaseModel):
    regla: str
    severidad: str
    descripcion: str


class LoteDeHallazgos(BaseModel):
    titulo: str
    hallazgos: list[HallazgoRevision]


class DiferenciaDePrecio(BaseModel):
    codigo_partida: str
    campo: str
    declarado: str
    declarado_texto: str
    recalculado: str
    recalculado_texto: str
    monto: str
    monto_texto: str


class PartidaDiferente(BaseModel):
    codigo_partida: str
    descripcion: str
    estado: str
    desvio_cantidad: str
    desvio_cantidad_texto: str
    desvio_precio: str
    desvio_precio_texto: str
    desvio_total: str
    desvio_total_texto: str


class TablaDeDiferencia(BaseModel):
    titulo: str
    total_antes: str
    total_antes_texto: str
    total_despues: str
    total_despues_texto: str
    diferencia: str
    diferencia_texto: str
    desvio_cantidad: str
    desvio_cantidad_texto: str
    desvio_precio: str
    desvio_precio_texto: str
    partidas: list[PartidaDiferente]  # solo las que no quedaron iguales


class ReauditoriaRevision(BaseModel):
    termino: bool
    avisos: list[str]
    total_recalculado: str | None
    total_recalculado_texto: str | None
    reglas: str | None
    precios_coinciden: bool
    mensaje_precios: str | None
    diferencias: list[DiferenciaDePrecio]
    hallazgos: list[LoteDeHallazgos]


class ListaDelCaso(BaseModel):
    id: int
    nombre: str


class ContraLista(BaseModel):
    lista_id: int
    diferencia: TablaDeDiferencia
    no_contrastables: str | None


class DictamenAnterior(BaseModel):
    resultado: str
    usuario: str
    fecha: str
    estado_verificacion: str
    texto: str


class RevisionRespuesta(BaseModel):
    sha256: str
    estado: str
    motivo: str
    color: str  # verde | ambar | rojo
    banner: str
    legible: bool
    banner_version: str | None
    ayuda_registro: str | None
    avisos: list[str]
    retroactiva: str | None
    aviso_armo: str | None
    reauditoria: ReauditoriaRevision | None
    entrega_anterior: TablaDeDiferencia | None
    sin_entrega_anterior: str | None
    listas: list[ListaDelCaso]
    sin_listas: str | None
    contra_lista: ContraLista | None
    cambios_titulo: str
    cambios: list[dict[str, str]]
    dictamenes: list[DictamenAnterior]
    resultados: list[str]
    admite_dictamen: bool  # lo recibido quedó registrado: hay a qué atar el dictamen
    sin_dictamen: str | None
    nota_excel: str


class DictamenGuardado(BaseModel):
    mensaje: str
    dictamenes: list[DictamenAnterior]


class ExcelExternoRespuesta(BaseModel):
    aviso: str
    total: str
    total_texto: str
    hallazgos: list[HallazgoRevision]


# --- piezas ---------------------------------------------------------------------------------


def _leer(archivo: UploadFile, tope: int, mensaje: str) -> bytes:
    """Los bytes de la subida, leyendo a lo sumo `tope + 1`: 413 si pasa del tope."""
    datos = archivo.file.read(tope + 1)
    if len(datos) > tope:
        raise HTTPException(413, mensaje)
    return datos


def _exacto(valor: Decimal) -> str:
    return format(valor, "f")


def _hallazgo(h) -> HallazgoRevision:
    return HallazgoRevision(
        regla=h.regla, severidad=h.severidad.name, descripcion=pulir(h.descripcion)
    )


def _tabla(d: Diferencia, titulo: str) -> TablaDeDiferencia:
    return TablaDeDiferencia(
        titulo=titulo,
        total_antes=_exacto(d.total_1),
        total_antes_texto=formatear_decimal(d.total_1, 2),
        total_despues=_exacto(d.total_2),
        total_despues_texto=formatear_decimal(d.total_2, 2),
        diferencia=_exacto(d.total_2 - d.total_1),
        diferencia_texto=formatear_decimal(d.total_2 - d.total_1, 2),
        desvio_cantidad=_exacto(d.desvio_cantidad),
        desvio_cantidad_texto=formatear_decimal(d.desvio_cantidad, 2),
        desvio_precio=_exacto(d.desvio_precio),
        desvio_precio_texto=formatear_decimal(d.desvio_precio, 2),
        partidas=[
            PartidaDiferente(
                codigo_partida=p.codigo_partida,
                descripcion=p.descripcion,
                estado=p.estado,
                desvio_cantidad=_exacto(p.desvio_cantidad),
                desvio_cantidad_texto=formatear_decimal(p.desvio_cantidad, 2),
                desvio_precio=_exacto(p.desvio_precio),
                desvio_precio_texto=formatear_decimal(p.desvio_precio, 2),
                desvio_total=_exacto(p.desvio_total),
                desvio_total_texto=formatear_decimal(p.desvio_total, 2),
            )
            for p in d.partidas
            if p.estado != "igual"
        ],
    )


def _reauditoria(r: logica.Reauditoria) -> ReauditoriaRevision:
    if r.resultado is None:  # no terminó: la clásica muestra los avisos y nada más
        return ReauditoriaRevision(
            termino=False,
            avisos=list(r.avisos),
            total_recalculado=None,
            total_recalculado_texto=None,
            reglas=None,
            precios_coinciden=False,
            mensaje_precios=None,
            diferencias=[],
            hallazgos=[],
        )
    return ReauditoriaRevision(
        termino=True,
        avisos=list(r.avisos),
        total_recalculado=_exacto(r.total_recalculado),
        total_recalculado_texto=formatear_decimal(r.total_recalculado, 2),
        reglas=_es(logica.texto_de_reglas(r)),
        precios_coinciden=not r.diferencias,
        mensaje_precios=logica.PRECIOS_NO_COINCIDEN if r.diferencias else logica.PRECIOS_COINCIDEN,
        diferencias=[
            DiferenciaDePrecio(
                codigo_partida=d.codigo_partida,
                campo=d.campo,
                declarado=_exacto(d.declarado),
                declarado_texto=formatear_decimal(d.declarado, 4),
                recalculado=_exacto(d.recalculado),
                recalculado_texto=formatear_decimal(d.recalculado, 4),
                monto=_exacto(d.monto),
                monto_texto=formatear_decimal(d.monto, 2),
            )
            for d in r.diferencias
        ],
        hallazgos=[
            LoteDeHallazgos(titulo=titulo, hallazgos=[_hallazgo(h) for h in getattr(r, campo)])
            for campo, titulo in logica.TITULOS_DE_HALLAZGOS
        ],
    )


def _dictamenes(caso: Session, sha256: str) -> list[DictamenAnterior]:
    return [
        DictamenAnterior(
            resultado=d["resultado"],
            usuario=d["usuario"],
            fecha=d["fecha"].isoformat(timespec="minutes"),
            estado_verificacion=d["estado_verificacion"],
            texto=_es(logica.texto_de_dictamen(d)) or "",
        )
        for d in paq.dictamenes_de(caso, sha256)
    ]


def _lista(caso: Session, lista_id: int) -> models.ListaPrecios:
    lista = caso.get(models.ListaPrecios, lista_id)
    if lista is None:
        raise HTTPException(404, MENSAJE_LISTA.format(id=lista_id))
    return lista


def _contra(caso: Session, documento, lista: models.ListaPrecios) -> ContraLista:
    diferencia, revalorado = logica.contra_mi_lista(caso, documento, lista)
    return ContraLista(
        lista_id=lista.id,
        diferencia=_tabla(diferencia, logica.TITULO_CONTRA_MI_LISTA),
        no_contrastables=logica.texto_de_no_contrastables(revalorado),
    )


_FECHA_ISO = re.compile(r"(?<![\d-])(\d{4})-(\d{2})-(\d{2})(?![\d-])")


def _es(texto: str | None) -> str | None:
    """Las fechas AAAA-MM-DD de un texto que se MUESTRA, en dd/mm/aaaa (es-VE)."""
    return None if texto is None else _FECHA_ISO.sub(r"\3/\2/\1", texto)


def _quien(activa: SesionActiva | None) -> tuple[str, str]:
    """`(responsable, login)`: la persona de la sesión, o la integración sin login."""
    return (USUARIO_SIN_CLAVE, "") if activa is None else (activa.usuario, activa.login)


def _analizar(
    sesion: Session,
    activa: SesionActiva | None,
    datos: bytes,
    nombre: str | None,
    servicios: logica.Servicios,
) -> logica.Analisis:
    responsable, login = _quien(activa)
    with sesion_de_instalacion() as bd:
        try:
            return logica.analizar(
                datos,
                nombre or "",
                caso=sesion,
                instalacion=bd,
                carpeta_paquetes=carpeta_datos() / logica.CARPETA_PAQUETES,
                revisor=responsable,
                login=login,
                ahora=ahora(),
                servicios=lambda: servicios,
            )
        except ERRORES_DEL_PAQUETE as error:
            raise HTTPException(422, str(error)) from None


def _legible(a: logica.Analisis) -> logica.Analisis:
    """El análisis de un paquete que se puede reauditar; si no, 422 con su banner."""
    v = a.recibido.verificacion
    if not v.legible:
        raise HTTPException(422, banner(v)[1])
    return a


# --- rutas ----------------------------------------------------------------------------------


@router.post("/paquete", response_model=RevisionRespuesta, dependencies=[REVISAR])
def revisar_paquete(
    sesion: SesionDep,
    response: Response,
    activa: Activa,
    servicios: ServiciosDep,
    paquete: Annotated[UploadFile, File()],
    lista: Annotated[int | None, Form()] = None,
) -> RevisionRespuesta:
    """Verifica, registra y reaudita el paquete; todo lo que la pantalla clásica muestra."""
    response.headers.update(SIN_CACHE)
    datos = _leer(paquete, TOPE_PAQUETE, MENSAJE_TOPE_PAQUETE)
    a = _analizar(sesion, activa, datos, paquete.filename, servicios)
    v = a.recibido.verificacion
    color, texto = banner(v)
    listas = logica.listas_del_caso(sesion) if v.legible else []
    contra = None
    r = a.reauditoria
    if r is not None and r.resultado is not None and listas:
        elegida = listas[0] if lista is None else _lista(sesion, lista)
        contra = _contra(sesion, r.documento, elegida)
    termino = r is not None and r.resultado is not None
    return RevisionRespuesta(
        sha256=v.sha256,
        estado=v.estado,
        motivo=v.motivo,
        color=color,
        banner=_es(texto) or "",
        legible=v.legible,
        banner_version=_es(
            logica.banner_de_version(a.recibido) if v.manifiesto is not None else None
        ),
        ayuda_registro=logica.ayuda_de_registro(v),
        avisos=logica.avisos_visibles(a.recibido),
        retroactiva=_es(logica.declaracion_retroactiva(v.cadena) if v.cadena else None),
        aviso_armo=logica.aviso_de_quien_armo(a.armo),
        reauditoria=_reauditoria(r) if r is not None else None,
        entrega_anterior=(
            _tabla(a.diferencia, logica.titulo_contra_anterior(a.previa.codigo))
            if a.previa is not None and a.diferencia is not None
            else None
        ),
        sin_entrega_anterior=logica.SIN_ENTREGA_ANTERIOR if termino and a.previa is None else None,
        listas=[ListaDelCaso(id=x.id, nombre=x.nombre) for x in listas],
        sin_listas=logica.SIN_LISTAS if termino and not listas else None,
        contra_lista=contra,
        cambios_titulo=logica.titulo_de_cambios(a.previa is not None),
        cambios=[{k: str(x) for k, x in c.items()} for c in a.cambios],
        dictamenes=_dictamenes(sesion, v.sha256) if v.legible else [],
        resultados=list(paq.RESULTADOS),
        admite_dictamen=a.recibido.paquete_id != 0,
        sin_dictamen=logica.SIN_DICTAMEN if v.legible and a.recibido.paquete_id == 0 else None,
        nota_excel=logica.NOTA_EXCEL,
    )


@router.post("/contra-lista", response_model=ContraLista, dependencies=[REVISAR])
def contra_otra_lista(
    sesion: SesionDep,
    response: Response,
    activa: Activa,
    servicios: ServiciosDep,
    paquete: Annotated[UploadFile, File()],
    lista: Annotated[int, Form()],
) -> ContraLista:
    """El paquete revalorado en memoria con otra lista del caso («Contrastar con mi lista»)."""
    response.headers.update(SIN_CACHE)
    elegida = _lista(sesion, lista)
    datos = _leer(paquete, TOPE_PAQUETE, MENSAJE_TOPE_PAQUETE)
    a = _legible(_analizar(sesion, activa, datos, paquete.filename, servicios))
    r = a.reauditoria
    if r is None or r.resultado is None:
        raise HTTPException(422, " ".join(r.avisos) if r else MENSAJE_CUERPO_INVALIDO)
    return _contra(sesion, r.documento, elegida)


@router.post("/dictamen", response_model=DictamenGuardado, dependencies=[REVISAR])
@sin_eco(MENSAJE_RESULTADO)
def dictaminar(
    sesion: SesionDep,
    response: Response,
    activa: Activa,
    paquete: Annotated[UploadFile, File()],
    resultado: Annotated[str, Form(max_length=40)],
    notas: Annotated[str, Form(max_length=20_000)] = "",
) -> DictamenGuardado:
    """Guarda el dictamen atado al SHA-256 del archivo (no hace falta reauditar para eso)."""
    response.headers.update(SIN_CACHE)
    if activa is None:
        raise HTTPException(403, MENSAJE_SOLO_PERSONA)
    if resultado not in paq.RESULTADOS:
        raise HTTPException(422, MENSAJE_RESULTADO)
    datos = _leer(paquete, TOPE_PAQUETE, MENSAJE_TOPE_PAQUETE)
    with sesion_de_instalacion() as bd:
        try:
            mi_empresa = logica.empresa_propia_para_revisar(bd)
            recibido = logica.recibir(
                datos,
                paquete.filename or "",
                caso=sesion,
                instalacion=bd,
                carpeta_paquetes=carpeta_datos() / logica.CARPETA_PAQUETES,
                revisor=activa.usuario,
                ahora=ahora(),
                mi_empresa=mi_empresa,
            )
            v = recibido.verificacion
            if not v.legible:
                raise HTTPException(422, banner(v)[1])
            armo = logica.revisor_armo(v, login_revisor=activa.login, empresa_propia=mi_empresa)
            logica.dictaminar(
                sesion,
                recibido,
                resultado=resultado,
                notas=notas,
                revisor=activa.usuario,
                ahora=ahora(),
                armo=bool(armo),
            )
        except ERRORES_DEL_PAQUETE as error:
            raise HTTPException(422, str(error)) from None
    return DictamenGuardado(
        mensaje=logica.DICTAMEN_GUARDADO, dictamenes=_dictamenes(sesion, v.sha256)
    )


@router.post(
    "/excel",
    response_class=Response,
    responses={200: {"content": {XLSX: {}}}},
    dependencies=[REVISAR],
)
def excel(
    sesion: SesionDep,
    activa: Activa,
    servicios: ServiciosDep,
    paquete: Annotated[UploadFile, File()],
    tipo: Annotated[str, Form(max_length=20)],
) -> Response:
    """El Excel del presupuesto o el de la revisión, regenerado aquí (DA-S3-10)."""
    if tipo not in logica.TIPOS_DE_EXCEL:
        raise HTTPException(422, MENSAJE_CUERPO_INVALIDO)
    datos = _leer(paquete, TOPE_PAQUETE, MENSAJE_TOPE_PAQUETE)
    a = _legible(_analizar(sesion, activa, datos, paquete.filename, servicios))
    r = a.reauditoria
    try:
        if tipo == "presupuesto":
            contenido = logica.excel_de_presupuesto(r)
        else:
            contenido = logica.excel_de_revision(
                a.recibido.verificacion, r, a.diferencia, list(a.cambios)
            )
    except ValueError as error:  # la reauditoría no terminó: no hay presupuesto que exportar
        raise HTTPException(422, str(error)) from None
    nombre = logica.nombre_de_excel(tipo, a.sha_del_archivo)
    return Response(
        content=contenido,
        media_type=XLSX,
        headers={**SIN_CACHE, "Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get(
    "/plantilla",
    response_class=Response,
    responses={200: {"content": {XLSX: {}}}},
    dependencies=[REVISAR],
)
def plantilla() -> Response:
    """La plantilla del formato UC-05, con una fila de ejemplo en cada hoja."""
    return Response(
        content=logica.plantilla_uc05(),
        media_type=XLSX,
        headers={
            **SIN_CACHE,
            "Content-Disposition": 'attachment; filename="plantilla-presupuesto.xlsx"',
        },
    )


@router.post("/excel-externo", response_model=ExcelExternoRespuesta, dependencies=[REVISAR])
def excel_externo(
    response: Response, presupuesto: Annotated[UploadFile, File()]
) -> ExcelExternoRespuesta:
    """Audita en memoria un presupuesto en Excel de otra herramienta: nada se guarda."""
    response.headers.update(SIN_CACHE)
    datos = _leer(presupuesto, TOPE_EXCEL, MENSAJE_TOPE_EXCEL)
    nombre = presupuesto.filename or ""
    with tempfile.TemporaryDirectory() as carpeta:
        try:
            verificar_archivo(datos, nombre)  # la guardia, antes de que openpyxl lo abra
            ruta = Path(carpeta) / nombre_seguro(nombre)  # el error nombra el archivo recibido
            ruta.write_bytes(datos)
            importado, informe = logica.auditar_excel_externo(ruta)
        except (ArchivoRechazado, ValueError, KeyError) as error:
            raise HTTPException(422, str(error)) from None
    total = importado.presupuesto.total
    return ExcelExternoRespuesta(
        aviso=logica.EXCEL_NO_VERIFICADO,
        total=_exacto(total),
        total_texto=formatear_decimal(total, 2),
        hallazgos=[_hallazgo(h) for h in informe.hallazgos],
    )
