"""Cuentas, contraseñas, bloqueo y primer administrador (RF-80, RF-81; spec S3 §5.2 a §5.5)."""

from __future__ import annotations

import threading
import time
from datetime import timedelta
from pathlib import Path

import pytest

from seguridad import cuentas, eventos
from seguridad.modelo import CodigoInstalacion, EventoAcceso, IntentoAcceso, Usuario
from seguridad.permisos import PermisoDenegado
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, instalacion, persona

MALA = "mala contrasena larga"


@pytest.fixture
def freno() -> cuentas.FrenoGlobal:
    return cuentas.FrenoGlobal()


def _entrar(sesion, login, contrasena, freno, cuando=AHORA):
    return cuentas.autenticar(
        sesion, login, contrasena, cuando, freno=freno, dormir=lambda segundos: None
    )


# --- primer administrador -------------------------------------------------------------------


def test_el_codigo_tiene_20_caracteres_base32_y_su_huella_no_es_el_codigo(tmp_path: Path):
    with instalacion(tmp_path) as sesion:
        codigo = cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        assert len(codigo) == 20 and set(codigo) <= set(cuentas.ALFABETO_CODIGO)
        archivo = (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).read_text()
        assert archivo.strip().replace("-", "") == codigo
        fila = sesion.query(CodigoInstalacion).one()
        assert fila.huella != codigo and len(fila.huella) == 64 and fila.usado is None


def test_cien_codigos_no_se_repiten(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        codigos = {cuentas.emitir_codigo(sesion, tmp_path, AHORA) for _ in range(100)}
    assert len(codigos) == 100


def test_el_primer_administrador_se_crea_con_el_codigo_y_el_archivo_se_borra(tmp_path: Path):
    with instalacion(tmp_path) as sesion:
        codigo = cuentas.preparar_primera_vez(sesion, tmp_path, AHORA)
        assert codigo is not None and (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).exists()
        assert cuentas.preparar_primera_vez(sesion, tmp_path, AHORA) is None  # ya hay uno vigente
        usuario = cuentas.reclamar_instalacion(
            sesion, codigo.lower(), "Admin", "Ana Admin", CONTRASENA, AHORA, tmp_path
        )
        assert usuario.roles == "administrador" and usuario.login == "admin"
        assert not (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).exists()
        assert sesion.query(CodigoInstalacion).one().usado == AHORA


def test_un_codigo_usado_o_ajeno_se_rechaza(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        codigo = cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        cuentas.reclamar_instalacion(sesion, codigo, "admin", "A", CONTRASENA, AHORA, tmp_path)
        for malo in (codigo, "A" * 20, ""):
            with pytest.raises(cuentas.ErrorDeAcceso, match="código de instalación"):
                cuentas.reclamar_instalacion(
                    sesion, malo, "otro", "B", CONTRASENA, AHORA, tmp_path, freno=freno
                )
        assert sesion.query(Usuario).count() == 1


def test_con_cuentas_el_codigo_de_primera_vez_no_sirve_pero_el_de_restablecimiento_si(
    tmp_path: Path, freno
) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        tardio = cuentas.emitir_codigo(sesion, tmp_path, AHORA)  # primera vez, con cuentas
        with pytest.raises(cuentas.ErrorDeAcceso):
            cuentas.reclamar_instalacion(
                sesion, tardio, "nuevo", "N", CONTRASENA, AHORA, tmp_path, freno=freno
            )
        rescate = cuentas.emitir_codigo_de_restablecimiento(sesion, tmp_path, AHORA)
        otra = "otra contrasena larga distinta"
        recuperado = cuentas.reclamar_instalacion(
            sesion, rescate, admin.login, "Admin", otra, AHORA, tmp_path, freno=freno
        )
        assert recuperado.id == admin.id
        assert _entrar(sesion, "admin", otra, freno).id == admin.id


def test_5_codigos_malos_seguidos_bloquean_el_reclamo(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        for _ in range(4):
            with pytest.raises(cuentas.ErrorDeAcceso) as error:
                cuentas.reclamar_instalacion(
                    sesion, "A" * 20, "x", "x", CONTRASENA, AHORA, tmp_path, freno=freno
                )
            assert not isinstance(error.value, cuentas.CuentaBloqueada)
        with pytest.raises(cuentas.CuentaBloqueada):
            cuentas.reclamar_instalacion(
                sesion, "A" * 20, "x", "x", CONTRASENA, AHORA, tmp_path, freno=freno
            )


# --- contraseñas ----------------------------------------------------------------------------


def test_politica_de_contrasenas() -> None:
    cuentas.validar_contrasena("a" * 10, "ana")  # 10 pasa
    with pytest.raises(cuentas.ContrasenaInvalida):
        cuentas.validar_contrasena("a" * 9, "ana")
    cuentas.validar_contrasena("ñ" * 128, "ana")  # 128 pasa, Unicode
    with pytest.raises(cuentas.ContrasenaInvalida):
        cuentas.validar_contrasena("a" * 129, "ana")
    with pytest.raises(cuentas.ContrasenaInvalida, match="igual al usuario"):
        cuentas.validar_contrasena("administrador", "Administrador")
    with pytest.raises(cuentas.ContrasenaInvalida, match="común"):
        cuentas.validar_contrasena("1234567890", "ana")


def test_ninguna_contrasena_queda_en_la_base_ni_en_los_eventos(tmp_path: Path, freno) -> None:
    secreta = "esta-contrasena-no-debe-aparecer-1"
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        cuentas.crear_usuario(sesion, admin, "luis", "Luis", ["arma"], secreta, AHORA)
        with pytest.raises(cuentas.ErrorDeAcceso):
            _entrar(sesion, "luis", secreta + "x", freno)
        cuentas.restablecer(sesion, admin, 2, secreta + "2", AHORA)
        texto = " ".join(
            f"{e.login_intentado} {e.detalle} {e.tipo}" for e in eventos.ultimos(sesion)
        )
        assert secreta not in texto and CONTRASENA not in texto
        huella = sesion.get(Usuario, 2).huella_clave
        assert huella.startswith("$argon2id$") and secreta not in huella
        sesion.commit()
    bruto = (tmp_path / "instalacion.db").read_bytes()
    for secreto in (secreta, CONTRASENA):
        assert secreto.encode() not in bruto


# --- bloqueo --------------------------------------------------------------------------------


@pytest.mark.parametrize("existe", [True, False])
def test_4_fallos_no_bloquean_y_el_quinto_si(tmp_path: Path, freno, existe: bool) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        login = "admin" if existe else "fantasma"
        for _ in range(4):
            with pytest.raises(cuentas.ErrorDeAcceso) as error:
                _entrar(sesion, login, MALA, freno)
            assert str(error.value) == cuentas.MENSAJE_FALLO
        if existe:  # el cuarto fallo no bloqueó: la contraseña buena aún entra y reinicia
            assert _entrar(sesion, login, CONTRASENA, freno).id == admin.id
            for _ in range(4):
                with pytest.raises(cuentas.ErrorDeAcceso):
                    _entrar(sesion, login, MALA, freno)
        with pytest.raises(cuentas.CuentaBloqueada) as quinto:
            _entrar(sesion, login, MALA, freno)
        assert str(quinto.value) == cuentas.MENSAJE_BLOQUEO
        with pytest.raises(cuentas.CuentaBloqueada):  # ni con la buena mientras dure
            _entrar(sesion, login, CONTRASENA, freno)


def test_el_bloqueo_dura_15_minutos_exactos(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        for _ in range(5):
            with pytest.raises(cuentas.ErrorDeAcceso):
                _entrar(sesion, "admin", MALA, freno)
        casi = AHORA + timedelta(minutes=15) - timedelta(seconds=1)
        with pytest.raises(cuentas.CuentaBloqueada):
            _entrar(sesion, "admin", CONTRASENA, freno, casi)
        assert _entrar(sesion, "admin", CONTRASENA, freno, AHORA + timedelta(minutes=15))


def test_el_administrador_desbloquea(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",))
        for _ in range(5):
            with pytest.raises(cuentas.ErrorDeAcceso):
                _entrar(sesion, "luis", MALA, freno)
        cuentas.desbloquear(sesion, admin, "luis", AHORA)
        assert _entrar(sesion, "luis", CONTRASENA, freno).id == luis.id
        with pytest.raises(PermisoDenegado):  # luis no es administrador
            cuentas.desbloquear(sesion, luis, "luis", AHORA)


def test_un_login_inexistente_se_verifica_contra_la_huella_de_relleno(
    tmp_path: Path, freno, monkeypatch
) -> None:
    vistas: list[str] = []
    verdadera = cuentas._coincide

    def espia(huella: str, contrasena: str) -> bool:
        vistas.append(huella)
        return verdadera(huella, contrasena)

    monkeypatch.setattr(cuentas, "_coincide", espia)
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        with pytest.raises(cuentas.ErrorDeAcceso):
            _entrar(sesion, "no-existe", CONTRASENA, freno)
        with pytest.raises(cuentas.ErrorDeAcceso):
            _entrar(sesion, "admin", MALA, freno)
        assert vistas[0] == cuentas._huella_de_relleno()
        assert vistas[1] == admin.huella_clave != vistas[0]


def test_una_cuenta_desactivada_no_entra_con_el_mismo_mensaje(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",))
        cuentas.desactivar(sesion, admin, luis.id, AHORA)
        with pytest.raises(cuentas.ErrorDeAcceso) as error:
            _entrar(sesion, "luis", CONTRASENA, freno)
        assert str(error.value) == cuentas.MENSAJE_FALLO


@pytest.mark.parametrize(
    "fallos,espera",
    [(19, 0.0), (20, 1.0), (21, 2.0), (22, 4.0), (25, 32.0), (26, 60.0), (40, 60.0)],
)
def test_freno_global_espera_progresiva(fallos: int, espera: float) -> None:
    freno = cuentas.FrenoGlobal()
    for _ in range(fallos):
        freno.registrar_fallo(AHORA)
    assert freno.espera(AHORA) == espera
    assert freno.espera(AHORA + timedelta(minutes=10)) == 0.0  # la ventana de 10 min se vació


def test_el_freno_global_hace_dormir_al_intento(tmp_path: Path) -> None:
    freno, dormidas = cuentas.FrenoGlobal(), []
    for _ in range(20):
        freno.registrar_fallo(AHORA)
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        cuentas.autenticar(sesion, "admin", CONTRASENA, AHORA, freno=freno, dormir=dormidas.append)
    assert dormidas == [1.0]


def test_el_semaforo_limita_las_verificaciones_simultaneas(monkeypatch) -> None:
    activas, maxima, candado = [0], [0], threading.Lock()

    class HasherLento:
        def verify(self, huella: str, contrasena: str) -> bool:
            with candado:
                activas[0] += 1
                maxima[0] = max(maxima[0], activas[0])
            time.sleep(0.03)
            with candado:
                activas[0] -= 1
            return True

    monkeypatch.setattr(cuentas, "_hasher", HasherLento())
    hilos = [threading.Thread(target=cuentas._coincide, args=("h", "c")) for _ in range(16)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert 1 <= maxima[0] <= cuentas.VERIFICACIONES_SIMULTANEAS


def test_los_contadores_de_logins_inexistentes_se_purgan_a_las_24_horas(tmp_path, freno):
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        with pytest.raises(cuentas.ErrorDeAcceso):
            _entrar(sesion, "fantasma", MALA, freno)
        assert cuentas.purgar_intentos_de_inexistentes(sesion, AHORA + timedelta(hours=23)) == 0
        assert cuentas.purgar_intentos_de_inexistentes(sesion, AHORA + timedelta(hours=24)) == 1


# --- administrar ----------------------------------------------------------------------------


def test_alta_con_temporal_obliga_a_cambiarla_y_cambiarla_da_ficha_nueva(tmp_path, freno):
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",))
        assert luis.debe_cambiar_clave
        entrada = _entrar(sesion, "luis", CONTRASENA, freno)
        nueva = "otra contrasena larga y nueva"
        ficha = cuentas.cambiar_contrasena(sesion, entrada.id, CONTRASENA, nueva, AHORA)
        assert ficha and not sesion.get(Usuario, luis.id).debe_cambiar_clave
        assert _entrar(sesion, "luis", nueva, freno).id == luis.id
        with pytest.raises(cuentas.ErrorDeAcceso):
            cuentas.cambiar_contrasena(sesion, luis.id, "no es la actual", nueva + "2", AHORA)


def test_no_se_puede_dejar_la_instalacion_sin_administrador(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        with pytest.raises(ValueError, match="al menos un administrador"):
            cuentas.desactivar(sesion, admin, admin.id, AHORA)
        with pytest.raises(ValueError, match="al menos un administrador"):
            cuentas.cambiar_roles(sesion, admin, admin.id, ["arma"], AHORA)


def test_un_alta_repetida_o_con_login_malo_se_rechaza(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        persona(sesion, admin, "luis", ("arma",))
        with pytest.raises(ValueError, match="Ya existe"):
            persona(sesion, admin, "LUIS", ("arma",))
        for malo in ("ab", "con espacio", "x" * 41, "ñandú"):
            with pytest.raises(ValueError, match="usuario"):
                cuentas.validar_login(malo)


def test_el_responsable_es_nombre_y_login_y_se_marca_tras_un_restablecimiento(tmp_path):
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",), "Luis Pérez")
        assert cuentas.responsable_de(luis) == "Luis Pérez <luis>"
        cuentas.restablecer(sesion, admin, luis.id, "otra contrasena temporal", AHORA)
        marcado = cuentas.responsable_de(sesion.get(Usuario, luis.id))
        assert marcado == "Luis Pérez <luis> (tras restablecimiento)"
        largo = Usuario(login="x" * 40, nombre="N" * 300, roles="arma", restablecida_por_admin=True)
        assert len(cuentas.responsable_de(largo)) <= 120


def test_cada_accion_de_administracion_queda_en_el_registro(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",))
        cuentas.cambiar_roles(sesion, admin, luis.id, ["arma", "revisa"], AHORA)
        cuentas.desactivar(sesion, admin, luis.id, AHORA)
        tipos = [e.tipo for e in sesion.query(EventoAcceso).order_by(EventoAcceso.id)]
        assert {"alta", "cambio de roles", "baja", "codigo de instalacion"} <= set(tipos)


# --- el último administrador no se pierde por una carrera (hallazgo de seguridad) -----------


@pytest.mark.parametrize("operacion", ["desactivar", "quitar el rol"])
def test_dos_administradores_que_se_quitan_a_la_vez_dejan_uno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operacion: str
) -> None:
    """Dos hilos, dos conexiones, una base en archivo. La ventana entre «queda otro» y la
    escritura se ensancha con una pausa. Sin una transacción que tome el bloqueo de escritura
    ANTES de leer (`BEGIN IMMEDIATE`), ambos leen «queda otro» y confirman: cero
    administradores. Con ella, el segundo espera, ve el resultado del primero y falla."""
    from seguridad.base import abrir_sesion, crear_motor

    with instalacion(tmp_path) as sesion:
        a = administrador(sesion, tmp_path, "admina")
        b = persona(sesion, a, "adminb", ("administrador",))
        ids = {"admina": a.id, "adminb": b.id}
    motor = crear_motor(tmp_path / "instalacion.db")

    original = cuentas._exigir_otro_administrador

    def con_ventana(session, usuario):
        original(session, usuario)
        time.sleep(0.4)  # la ventana de la carrera

    monkeypatch.setattr(cuentas, "_exigir_otro_administrador", con_ventana)
    resultados: dict[str, object] = {}

    def quitar(actor_login: str, objetivo_login: str) -> None:
        with abrir_sesion(motor) as bd:
            actor = bd.get(Usuario, ids[actor_login])
            try:
                if operacion == "desactivar":
                    cuentas.desactivar(bd, actor, ids[objetivo_login], AHORA)
                else:
                    cuentas.cambiar_roles(bd, actor, ids[objetivo_login], ["arma"], AHORA)
                resultados[actor_login] = "ok"
            except (ValueError, PermisoDenegado) as error:  # el segundo ya ve al otro cambio
                bd.rollback()
                resultados[actor_login] = str(error)

    hilos = [
        threading.Thread(target=quitar, args=("admina", "adminb")),
        threading.Thread(target=quitar, args=("adminb", "admina")),
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)

    with abrir_sesion(motor) as bd:
        activos = [
            u for u in bd.query(Usuario).filter(Usuario.activo.is_(True))
            if "administrador" in u.roles.split(",")
        ]
    motor.dispose()
    assert len(activos) == 1, resultados
    # exactamente una operación se completa; la otra la rechaza la regla o la cuenta ya inactiva
    assert sorted(v == "ok" for v in resultados.values()) == [False, True], resultados


# --- lo que un anónimo teclea en el usuario no se guarda si no es un usuario posible --------


def _filas_de_eventos(sesion) -> list[str]:
    return [
        f"{e.login_intentado}|{e.ip_cliente}|{e.tipo}|{e.detalle}|{e.usuario_id}"
        for e in sesion.query(EventoAcceso)
    ]


def test_un_usuario_con_forma_valida_se_guarda_tal_cual(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        with pytest.raises(cuentas.ErrorDeAcceso):
            _entrar(sesion, "  Nadie.Real  ", MALA, freno)
        assert [e.login_intentado for e in sesion.query(EventoAcceso)] == ["nadie.real"]


@pytest.mark.parametrize(
    "tecleado",
    [
        "Mi Contraseña Muy Secreta 2026!",  # espacios, mayúsculas y símbolos
        "x" * 60 + "cola-que-se-corta",  # largo
        "ab",  # corto
        "contra señal pegada",
        "-guion-inicial",
    ],
)
def test_lo_tecleado_que_no_es_un_usuario_posible_no_se_guarda(
    tmp_path: Path, freno, tecleado: str
) -> None:
    with instalacion(tmp_path) as sesion:
        with pytest.raises(cuentas.ErrorDeAcceso):
            _entrar(sesion, tecleado, MALA, freno)
        filas = _filas_de_eventos(sesion)
        assert [e.login_intentado for e in sesion.query(EventoAcceso)] == ["(usuario no válido)"]
        sesion.commit()
        # ninguna columna de ninguna tabla guarda el texto
        pegado = tecleado.strip().casefold()
        volcado = " ".join(filas) + " ".join(
            str(c) for i in sesion.query(IntentoAcceso) for c in (i.login_normalizado,)
        )
        assert pegado not in volcado and pegado[:20] not in volcado
    if len(pegado) >= 8:  # un texto de 2 letras aparece por azar en cualquier archivo binario
        assert pegado.encode() not in (tmp_path / "instalacion.db").read_bytes()


def test_un_login_real_cuenta_y_bloquea_igual_y_lo_no_valido_no_bloquea_a_nadie(
    tmp_path: Path, freno
) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        persona(sesion, admin, "ana", ("arma",))
        for _ in range(cuentas.FALLOS_PARA_BLOQUEAR - 1):
            with pytest.raises(cuentas.ErrorDeAcceso) as error:
                _entrar(sesion, "ana", MALA, freno)
            assert not isinstance(error.value, cuentas.CuentaBloqueada)
        with pytest.raises(cuentas.CuentaBloqueada):
            _entrar(sesion, "ana", MALA, freno)
        bloqueos = sesion.query(EventoAcceso).filter_by(tipo="bloqueo")
        assert [e.login_intentado for e in bloqueos] == ["ana"]
        # el bloqueo del marcador (texto imposible como usuario) no alcanza a una cuenta real
        otra = persona(sesion, admin, "luis", ("arma",))
        for i in range(cuentas.FALLOS_PARA_BLOQUEAR):
            with pytest.raises(cuentas.ErrorDeAcceso):
                _entrar(sesion, f"con espacio {i}", MALA, freno)
        assert _entrar(sesion, otra.login, CONTRASENA, freno).login == "luis"
        # y cada fallo, también el del marcador, alimenta el freno global
        assert len(freno._fallos) >= 2 * cuentas.FALLOS_PARA_BLOQUEAR - 1


def _dos_administradores(tmp_path: Path):
    from seguridad.base import crear_motor

    with instalacion(tmp_path) as sesion:
        a = administrador(sesion, tmp_path, "admina")
        b = persona(sesion, a, "adminb", ("administrador",))
        ids = (a.id, b.id)
    return crear_motor(tmp_path / "instalacion.db"), ids


@pytest.mark.parametrize("operacion", ["desactivar", "quitar el rol"])
def test_una_base_ocupada_da_un_mensaje_y_no_una_traza(tmp_path: Path, operacion: str) -> None:
    """Si otra conexión retiene el bloqueo de escritura y vence la espera, es un `ValueError`
    con mensaje (422 en la API), no un `OperationalError` (500)."""
    from sqlalchemy import text

    from seguridad.base import abrir_sesion

    motor, (id_a, id_b) = _dos_administradores(tmp_path)
    retenedora = motor.raw_connection()
    retenedora.isolation_level = None
    retenedora.execute("BEGIN IMMEDIATE")  # retiene el bloqueo de escritura
    try:
        with abrir_sesion(motor) as bd:
            actor = bd.get(Usuario, id_a)
            bd.execute(text("PRAGMA busy_timeout=100"))
            with pytest.raises(ValueError, match="La base está ocupada; reintente"):
                if operacion == "desactivar":
                    cuentas.desactivar(bd, actor, id_b, AHORA)
                else:
                    cuentas.cambiar_roles(bd, actor, id_b, ["arma"], AHORA)
    finally:
        retenedora.execute("ROLLBACK")
        retenedora.close()
        motor.dispose()


@pytest.mark.parametrize("operacion", ["desactivar", "quitar el rol"])
def test_un_administrador_desactivado_en_vuelo_no_completa_otra_accion(
    tmp_path: Path, operacion: str
) -> None:
    """El actor cargado antes puede haber sido desactivado por otro: tras tomar el bloqueo se
    relee y la acción se rechaza."""
    from seguridad.base import abrir_sesion

    motor, (id_a, id_b) = _dos_administradores(tmp_path)
    with abrir_sesion(motor) as bd_a, abrir_sesion(motor) as bd_b:
        actor = bd_a.get(Usuario, id_a)  # cargado y en caché con activo=True
        cuentas.desactivar(bd_b, bd_b.get(Usuario, id_b), id_a, AHORA)  # b desactiva a a
        with pytest.raises(PermisoDenegado, match="desactivada"):
            if operacion == "desactivar":
                cuentas.desactivar(bd_a, actor, id_b, AHORA)
            else:
                cuentas.cambiar_roles(bd_a, actor, id_b, ["arma"], AHORA)
    motor.dispose()
