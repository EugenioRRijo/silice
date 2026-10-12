"""La empresa propia, su clave de firma y las empresas ajenas registradas (spec S3 §7).

Una sola empresa propia por instalación (RV-6, P1) y, a lo sumo, una clave de firma **activa**.
La privada vive cifrada con su propia contraseña (`seguridad.secretos`) y solo la conoce el
administrador. Retirar o revocar **destruye** la privada de la base (los respaldos anteriores la
conservan cifrada: la pantalla lo advierte). Las empresas de los paquetes que se reciben se
registran como ajenas, con su clave pública y la huella comprobada por otro canal: sin esa marca
no se registra nada. Cada función confirma su transacción; nada de aquí guarda una contraseña.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from seguridad import eventos, firma
from seguridad.modelo import ClaveEmpresa, EmpresaPropia, EmpresaRegistrada
from seguridad.secretos import (
    InvalidTag,
    ParametrosKdf,
    SecretoCifrado,
    cifrar,
    descifrar,
    exigir_contrasena_de_clave,
)

ACTIVA, RETIRADA, REVOCADA = "activa", "retirada", "revocada"
METODOS = ("telefono", "en persona", "qr")
PIE_DE_RESPALDOS = (
    "Los respaldos hechos antes de retirar la clave todavía la contienen, cifrada con su "
    "contraseña."
)


class ClaveError(ValueError):  # noqa: N818
    """Un rechazo de la gestión de claves, en lenguaje llano y sin traza."""


class ContrasenaDeClaveIncorrecta(ClaveError):  # noqa: N818
    """La contraseña de la clave de firma no es la que la cifró."""


class HuellaNoCoincide(ClaveError):  # noqa: N818
    """La huella leída por el otro canal no es la que calculó el sistema."""


def exigir_equipo_propio(ip_cliente: str | None, direccion: str = "") -> None:
    """Gancho de RV-15: firmar y gestionar la clave solo se hace desde el propio equipo. La
    interfaz o la ruta lo llaman con la IP del cliente antes de `generar_clave`, `abrir_privada`,
    `exportar_respaldo_cifrado`, `retirar_clave` o `revocar_clave_propia`; aquí no se adivina la
    IP. Usa `operacion.red.es_cliente_local` (importado al llamar: `operacion` importa a
    `seguridad`)."""
    from operacion.red import es_cliente_local

    if not es_cliente_local(ip_cliente, direccion):
        raise ClaveError("La clave de firma solo se gestiona desde el propio equipo.")


# --- empresa propia -------------------------------------------------------------------------


def empresa_propia(session: Session) -> EmpresaPropia | None:
    return session.get(EmpresaPropia, 1)


def guardar_empresa_propia(
    session: Session, nombre: str, rif: str, ciudad: str, actor: str, ahora: datetime
) -> EmpresaPropia:
    if not nombre.strip() or not rif.strip():
        raise ClaveError("La empresa necesita nombre y RIF.")
    fila = empresa_propia(session)
    if fila is None:
        fila = EmpresaPropia(id=1, nombre="", rif="", actualizada=ahora)
        session.add(fila)
    fila.nombre, fila.rif, fila.ciudad = nombre.strip(), rif.strip(), ciudad.strip()
    fila.actualizada, fila.actualizada_por = ahora, actor
    eventos.registrar(session, "empresa", ahora, detalle=f"{fila.nombre}; por {actor}")
    session.commit()
    return fila


# --- clave de firma propia ------------------------------------------------------------------


def clave_activa(session: Session) -> ClaveEmpresa | None:
    return session.scalar(select(ClaveEmpresa).where(ClaveEmpresa.estado == ACTIVA))


def generar_clave(
    session: Session,
    contrasena_clave: str,
    actor: str,
    ahora: datetime,
    parametros: ParametrosKdf | None = None,
) -> ClaveEmpresa:
    """Genera el par Ed25519 en este equipo y guarda la privada cifrada (Argon2id -> AES-GCM)."""
    if empresa_propia(session) is None:
        raise ClaveError("Registre primero los datos de la empresa.")
    if clave_activa(session) is not None:
        raise ClaveError("Ya hay una clave activa: retírela o revóquela antes de generar otra.")
    exigir_contrasena_de_clave(contrasena_clave)
    par = firma.generar_par()
    huella = firma.huella_completa(par.publica)
    guardado = cifrar(par.privada, contrasena_clave, huella, parametros)
    clave = ClaveEmpresa(
        publica=par.publica,
        huella=huella,
        privada_cifrada=guardado.cifrado,
        kdf=guardado.kdf,
        sal=guardado.sal,
        nonce=guardado.nonce,
        estado=ACTIVA,
        creada=ahora,
        creada_por=actor,
    )
    session.add(clave)
    session.flush()
    eventos.registrar(
        session, "alta de clave", ahora, detalle=f"{firma.huella_corta(par.publica)}; por {actor}"
    )
    session.commit()
    return clave


def abrir_privada(session: Session, contrasena_clave: str) -> bytes:
    """La privada de la clave activa. `ContrasenaDeClaveIncorrecta` (sin traza) si no es la
    contraseña; el `InvalidTag` de la biblioteca no sale de aquí."""
    clave = clave_activa(session)
    if clave is None or clave.privada_cifrada is None:
        raise ClaveError("La empresa no tiene una clave de firma activa.")
    cifrado = SecretoCifrado(
        clave.kdf or "", clave.sal or b"", clave.nonce or b"", clave.privada_cifrada
    )
    try:
        return descifrar(cifrado, contrasena_clave, clave.huella)
    except InvalidTag:
        raise ContrasenaDeClaveIncorrecta("La contraseña de la clave no es correcta.") from None


def exportar_clave_publica_propia(session: Session, ahora: datetime) -> bytes:
    """El `.silice-clave` para mandarlo a quien recibe los paquetes."""
    clave, empresa = clave_activa(session), empresa_propia(session)
    if clave is None or empresa is None:
        raise ClaveError("La empresa no tiene una clave de firma activa.")
    return firma.exportar_clave_publica(empresa.nombre, empresa.rif, clave.publica, ahora)


def exportar_respaldo_cifrado(session: Session) -> bytes:
    """La clave activa tal como está guardada (cifrada), para un respaldo aparte. Nunca sale la
    privada en claro; solo se hace desde el propio equipo."""
    clave = clave_activa(session)
    if clave is None or clave.privada_cifrada is None:
        raise ClaveError("La empresa no tiene una clave de firma activa.")

    def b64(octetos: bytes | None) -> str:
        return base64.b64encode(octetos or b"").decode("ascii")

    return json.dumps(
        {
            "formato": "silice-clave-cifrada",
            "version_formato": 1,
            "huella": clave.huella,
            "clave_publica": b64(clave.publica),
            "kdf": clave.kdf,
            "sal": b64(clave.sal),
            "nonce": b64(clave.nonce),
            "cifrado": b64(clave.privada_cifrada),
        },
        sort_keys=True,
    ).encode("utf-8")


def _destruir_privada(clave: ClaveEmpresa) -> None:
    clave.privada_cifrada = clave.kdf = clave.sal = clave.nonce = None


def retirar_clave(session: Session, actor: str, ahora: datetime, motivo: str = "") -> ClaveEmpresa:
    """Sustitución sin compromiso: **se destruye la privada** en la base."""
    clave = clave_activa(session)
    if clave is None:
        raise ClaveError("La empresa no tiene una clave de firma activa.")
    _destruir_privada(clave)
    clave.estado, clave.fecha_estado, clave.motivo = RETIRADA, ahora, motivo
    eventos.registrar(session, "retiro", ahora, detalle=f"{firma.huella_corta(clave.publica)}")
    session.commit()
    return clave


def revocar_clave_propia(
    session: Session, actor: str, ahora: datetime, motivo: str, contrasena_clave: str | None = None
) -> bytes | None:
    """Comprometida o perdida. Con la contraseña genera el **aviso de revocación** firmado con la
    propia clave (dominio de revocación); sin ella (se perdió) no hay aviso y se avisa por
    teléfono. Destruye la privada en ambos casos."""
    clave = clave_activa(session)
    if clave is None:
        raise ClaveError("La empresa no tiene una clave de firma activa.")
    aviso = None
    if contrasena_clave is not None:
        privada = abrir_privada(session, contrasena_clave)
        aviso = firma.crear_aviso_revocacion(privada, motivo, ahora)
    _destruir_privada(clave)
    clave.estado, clave.fecha_estado, clave.motivo = REVOCADA, ahora, motivo
    eventos.registrar(
        session, "revocacion", ahora, detalle=f"{firma.huella_corta(clave.publica)}; {motivo}"
    )
    session.commit()
    return aviso


# --- empresas ajenas ------------------------------------------------------------------------


def buscar_por_publica(session: Session, publica: bytes) -> EmpresaRegistrada | None:
    """Búsqueda interna por la CLAVE PÚBLICA COMPLETA (la corta solo se compara a viva voz)."""
    return session.scalar(select(EmpresaRegistrada).where(EmpresaRegistrada.publica == publica))


def registrar_empresa_ajena(
    session: Session,
    archivo_clave: bytes,
    huella_leida: str,
    comprobada_con: str,
    metodo: str,
    actor: str,
    ahora: datetime,
) -> EmpresaRegistrada:
    """Registra la clave de otra empresa. El sistema calcula la huella él mismo (no confía en la
    escrita en el archivo) y exige la que se leyó por otro canal: sin coincidencia, nada."""
    leida = firma.leer_clave_publica(archivo_clave)
    if metodo not in METODOS:
        raise ClaveError(f"Indique cómo se comprobó la huella: {', '.join(METODOS)}.")
    if not comprobada_con.strip():
        raise ClaveError("Indique con quién se comprobó la huella.")
    try:
        vista = firma.normalizar_huella_corta(huella_leida)
    except ValueError as error:
        raise HuellaNoCoincide(str(error)) from None
    if vista != leida.huella_corta:
        raise HuellaNoCoincide(
            f"La huella leída no coincide con la de la clave ({leida.huella_corta}). "
            "No se registró nada."
        )
    if buscar_por_publica(session, leida.publica) is not None:
        raise ClaveError("Esa clave ya está registrada.")
    propia = clave_activa(session)
    if propia is not None and propia.publica == leida.publica:
        raise ClaveError("Esa es la clave de esta misma empresa; no se registra como ajena.")
    fila = EmpresaRegistrada(
        empresa=leida.nombre,
        rif=leida.rif,
        publica=leida.publica,
        huella=leida.huella,
        estado=ACTIVA,
        comprobada_con=comprobada_con.strip(),
        metodo=metodo,
        fecha_comprobacion=ahora,
        registrada_por=actor,
    )
    session.add(fila)
    session.flush()
    eventos.registrar(
        session, "clave registrada", ahora, detalle=f"{leida.nombre}; {leida.huella_corta}"
    )
    session.commit()
    return fila


def retirar_ajena(
    session: Session, empresa_id: int, fecha_retiro: datetime, actor: str, ahora: datetime
) -> EmpresaRegistrada:
    """La contratista avisó que retiró su clave. 'Verificado (retirada)' vale solo para paquetes
    recibidos ANTES de `fecha_retiro`."""
    fila = _ajena(session, empresa_id)
    fila.estado, fila.fecha_estado = RETIRADA, fecha_retiro
    eventos.registrar(session, "retiro", ahora, detalle=f"{fila.empresa}; por {actor}")
    session.commit()
    return fila


def revocar_ajena(
    session: Session,
    empresa_id: int,
    motivo: str,
    actor: str,
    ahora: datetime,
    aviso: bytes | None = None,
) -> EmpresaRegistrada:
    """Importar el aviso firmado (se verifica con la clave registrada) o marcarla a mano con el
    motivo. Tras revocar, ningún paquete de esa clave verifica."""
    fila = _ajena(session, empresa_id)
    if aviso is not None:
        publica, motivo_aviso, valida = firma.leer_aviso_revocacion(aviso)
        if publica != fila.publica or not valida:
            raise ClaveError("El aviso de revocación no es válido para esta clave.")
        motivo = motivo or motivo_aviso
    fila.estado, fila.fecha_estado, fila.motivo = REVOCADA, ahora, motivo
    eventos.registrar(session, "revocacion", ahora, detalle=f"{fila.empresa}; {motivo}")
    session.commit()
    return fila


def _ajena(session: Session, empresa_id: int) -> EmpresaRegistrada:
    fila = session.get(EmpresaRegistrada, empresa_id)
    if fila is None:
        raise ClaveError("No hay una empresa registrada con ese número.")
    return fila
