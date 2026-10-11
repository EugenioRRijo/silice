"""Revisión base del caso: esquema EXACTO de Sílice 0.5.0 (v0.5.0, 8610053).

Generada una vez con `scripts/congelar_esquema.py` desde la base de prueba de esa versión
(`tests/fixtures/bases/`), creada con el código de su etiqueta; revisada a mano y CONGELADA: no se
deriva de los modelos (spec S5 §6.1). Idempotente (DA-S5-4): crea las tablas que faltan y verifica
las existentes; una diferencia es `BaseNoAdoptable`.
"""

from alembic import op

from migraciones.comun import TablaCongelada, borrar_tablas, crear_o_verificar

revision = "caso_0001_base_0_5_0"
down_revision = None
branch_labels = None
depends_on = None

TABLAS = (
    TablaCongelada(
        nombre="partida",
        ddl=(
            "CREATE TABLE partida (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tcodigo VARCHAR(40) NOT NULL, \n"
            "\tcodigo_covenin VARCHAR(40), \n"
            "\tdescripcion VARCHAR(300) NOT NULL, \n"
            "\tunidad VARCHAR(20) NOT NULL, \n"
            "\tdominio VARCHAR(20) NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tUNIQUE (codigo)\n"
            ")"
        ),
        indices=("CREATE INDEX ix_partida_descripcion ON partida (descripcion)",),
    ),
    TablaCongelada(
        nombre="insumo",
        ddl=(
            "CREATE TABLE insumo (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tcodigo VARCHAR(20) NOT NULL, \n"
            "\ttipo VARCHAR(10) NOT NULL, \n"
            "\tdescripcion VARCHAR(300) NOT NULL, \n"
            "\tunidad VARCHAR(20), \n"
            "\tPRIMARY KEY (id), \n"
            "\tUNIQUE (codigo)\n"
            ")"
        ),
        indices=("CREATE INDEX ix_insumo_tipo_descripcion ON insumo (tipo, descripcion)",),
    ),
    TablaCongelada(
        nombre="lista_precios",
        ddl=(
            "CREATE TABLE lista_precios (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tnombre VARCHAR(120) NOT NULL, \n"
            "\tmoneda VARCHAR(10) NOT NULL, \n"
            "\tfecha_vigencia DATE NOT NULL, \n"
            "\torigen VARCHAR(200) NOT NULL, \n"
            "\tPRIMARY KEY (id)\n"
            ")"
        ),
        indices=("CREATE INDEX ix_lista_precios_fecha_vigencia ON lista_precios (fecha_vigencia)",),
    ),
    TablaCongelada(
        nombre="proyecto",
        ddl=(
            "CREATE TABLE proyecto (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tnombre VARCHAR(200) NOT NULL, \n"
            "\tdescripcion VARCHAR(500) NOT NULL, \n"
            "\tdominio VARCHAR(20) NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tUNIQUE (nombre)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="composicion_apu",
        ddl=(
            "CREATE TABLE composicion_apu (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpartida_id INTEGER NOT NULL, \n"
            "\tinsumo_id INTEGER NOT NULL, \n"
            "\tcantidad VARCHAR(40) NOT NULL, \n"
            "\tdepreciacion VARCHAR(40), \n"
            "\tmodalidad VARCHAR(10), \n"
            "\torden INTEGER NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tFOREIGN KEY(partida_id) REFERENCES partida (id), \n"
            "\tFOREIGN KEY(insumo_id) REFERENCES insumo (id)\n"
            ")"
        ),
        indices=(
            "CREATE INDEX ix_composicion_partida_orden ON composicion_apu (partida_id, orden)",
        ),
    ),
    TablaCongelada(
        nombre="ejecucion",
        ddl=(
            "CREATE TABLE ejecucion (\n"
            "\tid INTEGER NOT NULL, \n"
            "\treferencia VARCHAR(60) NOT NULL, \n"
            "\tproyecto_id INTEGER, \n"
            "\tfecha_inicio DATE NOT NULL, \n"
            "\tfecha_fin DATE, \n"
            "\tdescripcion VARCHAR(300) NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tUNIQUE (referencia), \n"
            "\tFOREIGN KEY(proyecto_id) REFERENCES proyecto (id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="precio_insumo",
        ddl=(
            "CREATE TABLE precio_insumo (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tlista_id INTEGER NOT NULL, \n"
            "\tinsumo_id INTEGER NOT NULL, \n"
            "\tprecio VARCHAR(40) NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_precio_insumo_lista_insumo UNIQUE (lista_id, insumo_id), \n"
            "\tFOREIGN KEY(lista_id) REFERENCES lista_precios (id), \n"
            "\tFOREIGN KEY(insumo_id) REFERENCES insumo (id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="cambio_precio",
        ddl=(
            "CREATE TABLE cambio_precio (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tlista_anterior_id INTEGER NOT NULL, \n"
            "\tlista_nueva_id INTEGER NOT NULL, \n"
            "\tinsumo_id INTEGER NOT NULL, \n"
            "\tprecio_anterior VARCHAR(40) NOT NULL, \n"
            "\tprecio_nuevo VARCHAR(40) NOT NULL, \n"
            "\tvariacion VARCHAR(40) NOT NULL, \n"
            "\tfecha DATE NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tFOREIGN KEY(lista_anterior_id) REFERENCES lista_precios (id), \n"
            "\tFOREIGN KEY(lista_nueva_id) REFERENCES lista_precios (id), \n"
            "\tFOREIGN KEY(insumo_id) REFERENCES insumo (id)\n"
            ")"
        ),
        indices=("CREATE INDEX ix_cambio_precio_lista_nueva ON cambio_precio (lista_nueva_id)",),
    ),
    TablaCongelada(
        nombre="presupuesto",
        ddl=(
            "CREATE TABLE presupuesto (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tcodigo VARCHAR(40) NOT NULL, \n"
            "\tproyecto_id INTEGER NOT NULL, \n"
            "\tfecha DATE NOT NULL, \n"
            "\tmoneda VARCHAR(10) NOT NULL, \n"
            "\tlista_precios_id INTEGER NOT NULL, \n"
            "\tfcas VARCHAR(40) NOT NULL, \n"
            "\tbono_alimentacion VARCHAR(40) NOT NULL, \n"
            "\tadministracion VARCHAR(40) NOT NULL, \n"
            "\tutilidad VARCHAR(40) NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_presupuesto_proyecto_codigo UNIQUE (proyecto_id, codigo), \n"
            "\tFOREIGN KEY(proyecto_id) REFERENCES proyecto (id), \n"
            "\tFOREIGN KEY(lista_precios_id) REFERENCES lista_precios (id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="lista_precios_origen",
        ddl=(
            "CREATE TABLE lista_precios_origen (\n"
            "\tlista_id INTEGER NOT NULL, \n"
            "\ttasa VARCHAR(40), \n"
            "\tfecha_tasa DATE, \n"
            "\talcance VARCHAR(10) NOT NULL, \n"
            "\tproyecto_id INTEGER, \n"
            "\tlista_base_id INTEGER, \n"
            "\tPRIMARY KEY (lista_id), \n"
            "\tFOREIGN KEY(lista_id) REFERENCES lista_precios (id) ON DELETE CASCADE, \n"
            "\tFOREIGN KEY(proyecto_id) REFERENCES proyecto (id) ON DELETE CASCADE, \n"
            "\tFOREIGN KEY(lista_base_id) REFERENCES lista_precios (id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="cotizacion",
        ddl=(
            "CREATE TABLE cotizacion (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tlista_id INTEGER NOT NULL, \n"
            "\tinsumo_id INTEGER NOT NULL, \n"
            "\tprecio VARCHAR(40) NOT NULL, \n"
            "\tprecio_base VARCHAR(40), \n"
            "\tproveedor VARCHAR(120) NOT NULL, \n"
            "\tnumero VARCHAR(60) NOT NULL, \n"
            "\tfecha DATE NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_cotizacion_lista_insumo UNIQUE (lista_id, insumo_id), \n"
            "\tFOREIGN KEY(lista_id) REFERENCES lista_precios (id) ON DELETE CASCADE, \n"
            "\tFOREIGN KEY(insumo_id) REFERENCES insumo (id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="rendimiento",
        ddl=(
            "CREATE TABLE rendimiento (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpartida_id INTEGER NOT NULL, \n"
            "\tvalor VARCHAR(40) NOT NULL, \n"
            "\ttipo VARCHAR(10) NOT NULL, \n"
            "\tfecha DATE NOT NULL, \n"
            "\tcondiciones VARCHAR(300) NOT NULL, \n"
            "\tejecucion_id INTEGER, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT ck_rendimiento_medido_exige_ejecucion CHECK (tipo <> 'medido' OR ejecucion_id IS NOT NULL), \n"
            "\tFOREIGN KEY(partida_id) REFERENCES partida (id), \n"
            "\tFOREIGN KEY(ejecucion_id) REFERENCES ejecucion (id)\n"
            ")"
        ),
        indices=(
            "CREATE INDEX ix_rendimiento_partida_tipo_fecha ON rendimiento (partida_id, tipo, fecha)",
        ),
    ),
    TablaCongelada(
        nombre="incidencia_cambio",
        ddl=(
            "CREATE TABLE incidencia_cambio (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tcambio_id INTEGER NOT NULL, \n"
            "\tpartida_id INTEGER NOT NULL, \n"
            "\tprecio_unitario_anterior VARCHAR(40) NOT NULL, \n"
            "\tprecio_unitario_nuevo VARCHAR(40) NOT NULL, \n"
            "\tvariacion VARCHAR(40) NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tFOREIGN KEY(cambio_id) REFERENCES cambio_precio (id), \n"
            "\tFOREIGN KEY(partida_id) REFERENCES partida (id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="descarte_version",
        ddl=(
            "CREATE TABLE descarte_version (\n"
            "\tpresupuesto_id INTEGER NOT NULL, \n"
            "\tfecha DATE NOT NULL, \n"
            "\tPRIMARY KEY (presupuesto_id), \n"
            "\tFOREIGN KEY(presupuesto_id) REFERENCES presupuesto (id) ON DELETE CASCADE\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="item_computo",
        ddl=(
            "CREATE TABLE item_computo (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tcodigo_partida VARCHAR(40) NOT NULL, \n"
            "\tdescripcion VARCHAR(300) NOT NULL, \n"
            "\tunidad_original VARCHAR(20) NOT NULL, \n"
            "\tunidad VARCHAR(20) NOT NULL, \n"
            "\tcantidad VARCHAR(40) NOT NULL, \n"
            "\torigen_id VARCHAR(120) NOT NULL, \n"
            "\torigen_tipo VARCHAR(20) NOT NULL, \n"
            "\tdominio VARCHAR(20) NOT NULL, \n"
            "\tpresupuesto_id INTEGER, \n"
            "\tregla VARCHAR(300), \n"
            "\tparametros TEXT NOT NULL, \n"
            "\tespecificaciones TEXT NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tFOREIGN KEY(presupuesto_id) REFERENCES presupuesto (id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="punto_curva",
        ddl=(
            "CREATE TABLE punto_curva (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpresupuesto_id INTEGER NOT NULL, \n"
            "\torden INTEGER NOT NULL, \n"
            "\tperiodo VARCHAR(120) NOT NULL, \n"
            "\tmonto VARCHAR(40) NOT NULL, \n"
            "\tacumulado VARCHAR(40) NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tFOREIGN KEY(presupuesto_id) REFERENCES presupuesto (id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="hallazgo",
        ddl=(
            "CREATE TABLE hallazgo (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpresupuesto_id INTEGER NOT NULL, \n"
            "\tregla VARCHAR(10) NOT NULL, \n"
            "\tseveridad INTEGER NOT NULL, \n"
            "\tdescripcion VARCHAR(500) NOT NULL, \n"
            "\timpacto VARCHAR(40), \n"
            "\torigen_ids TEXT NOT NULL, \n"
            "\tvalor_observado VARCHAR(40), \n"
            "\tvalor_esperado VARCHAR(40), \n"
            "\tPRIMARY KEY (id), \n"
            "\tFOREIGN KEY(presupuesto_id) REFERENCES presupuesto (id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="composicion_version",
        ddl=(
            "CREATE TABLE composicion_version (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpresupuesto_id INTEGER NOT NULL, \n"
            "\tcodigo_partida VARCHAR(40) NOT NULL, \n"
            "\tdescripcion VARCHAR(300) NOT NULL, \n"
            "\tunidad VARCHAR(20) NOT NULL, \n"
            "\trendimiento VARCHAR(40) NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_composicion_version UNIQUE (presupuesto_id, codigo_partida), \n"
            "\tFOREIGN KEY(presupuesto_id) REFERENCES presupuesto (id) ON DELETE CASCADE\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="plan_version",
        ddl=(
            "CREATE TABLE plan_version (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpresupuesto_id INTEGER NOT NULL, \n"
            "\tperiodo INTEGER NOT NULL, \n"
            "\tetiqueta VARCHAR(120) NOT NULL, \n"
            "\torden INTEGER NOT NULL, \n"
            "\tcodigo_partida VARCHAR(40), \n"
            "\tfraccion VARCHAR(40), \n"
            "\tPRIMARY KEY (id), \n"
            "\tFOREIGN KEY(presupuesto_id) REFERENCES presupuesto (id) ON DELETE CASCADE\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="version_origen",
        ddl=(
            "CREATE TABLE version_origen (\n"
            "\tpresupuesto_id INTEGER NOT NULL, \n"
            "\torigen_id INTEGER, \n"
            "\tmotivo VARCHAR(20) NOT NULL, \n"
            "\tPRIMARY KEY (presupuesto_id), \n"
            "\tFOREIGN KEY(presupuesto_id) REFERENCES presupuesto (id) ON DELETE CASCADE, \n"
            "\tFOREIGN KEY(origen_id) REFERENCES presupuesto (id) ON DELETE SET NULL\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="registro_cambio",
        ddl=(
            "CREATE TABLE registro_cambio (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tproyecto_id INTEGER NOT NULL, \n"
            "\tversion_origen_id INTEGER, \n"
            "\tversion_resultante_id INTEGER NOT NULL, \n"
            "\tobjeto VARCHAR(20) NOT NULL, \n"
            "\tclave VARCHAR(200) NOT NULL, \n"
            "\tcampo VARCHAR(60) NOT NULL, \n"
            "\tvalor_anterior TEXT NOT NULL, \n"
            "\tvalor_nuevo TEXT NOT NULL, \n"
            "\tfuente VARCHAR(300) NOT NULL, \n"
            "\tresponsable VARCHAR(120) NOT NULL, \n"
            "\tfecha_hora DATETIME NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tFOREIGN KEY(proyecto_id) REFERENCES proyecto (id) ON DELETE CASCADE, \n"
            "\tFOREIGN KEY(version_origen_id) REFERENCES presupuesto (id) ON DELETE SET NULL, \n"
            "\tFOREIGN KEY(version_resultante_id) REFERENCES presupuesto (id) ON DELETE CASCADE\n"
            ")"
        ),
        indices=(
            "CREATE INDEX ix_registro_cambio_resultante ON registro_cambio (version_resultante_id)",
        ),
    ),
    TablaCongelada(
        nombre="referencia_precio",
        ddl=(
            "CREATE TABLE referencia_precio (\n"
            "\tprecio_id INTEGER NOT NULL, \n"
            "\treferencia VARCHAR(60) NOT NULL, \n"
            "\tPRIMARY KEY (precio_id), \n"
            "\tFOREIGN KEY(precio_id) REFERENCES precio_insumo (id) ON DELETE CASCADE\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="justificacion_rendimiento",
        ddl=(
            "CREATE TABLE justificacion_rendimiento (\n"
            "\trendimiento_id INTEGER NOT NULL, \n"
            "\ttexto TEXT NOT NULL, \n"
            "\tadvertencia TEXT NOT NULL, \n"
            "\tfecha DATE NOT NULL, \n"
            "\tPRIMARY KEY (rendimiento_id), \n"
            "\tFOREIGN KEY(rendimiento_id) REFERENCES rendimiento (id) ON DELETE CASCADE\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="partida_presupuestada",
        ddl=(
            "CREATE TABLE partida_presupuestada (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpresupuesto_id INTEGER NOT NULL, \n"
            "\tpartida_id INTEGER NOT NULL, \n"
            "\titem_computo_id INTEGER NOT NULL, \n"
            "\torden INTEGER NOT NULL, \n"
            "\tcantidad VARCHAR(40) NOT NULL, \n"
            "\tmateriales VARCHAR(40) NOT NULL, \n"
            "\tequipos VARCHAR(40) NOT NULL, \n"
            "\tmano_obra VARCHAR(40) NOT NULL, \n"
            "\tcosto_directo VARCHAR(40) NOT NULL, \n"
            "\tcon_administracion VARCHAR(40) NOT NULL, \n"
            "\tprecio_unitario VARCHAR(40) NOT NULL, \n"
            "\ttotal VARCHAR(40) NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tFOREIGN KEY(presupuesto_id) REFERENCES presupuesto (id), \n"
            "\tFOREIGN KEY(partida_id) REFERENCES partida (id), \n"
            "\tFOREIGN KEY(item_computo_id) REFERENCES item_computo (id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="linea_composicion_version",
        ddl=(
            "CREATE TABLE linea_composicion_version (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tcomposicion_id INTEGER NOT NULL, \n"
            "\torden INTEGER NOT NULL, \n"
            "\ttipo VARCHAR(10) NOT NULL, \n"
            "\tinsumo_id INTEGER, \n"
            "\tdescripcion VARCHAR(300) NOT NULL, \n"
            "\tunidad VARCHAR(20), \n"
            "\tcantidad VARCHAR(40) NOT NULL, \n"
            "\tprecio VARCHAR(40) NOT NULL, \n"
            "\tdepreciacion VARCHAR(40), \n"
            "\tmodalidad VARCHAR(10), \n"
            "\tPRIMARY KEY (id), \n"
            "\tFOREIGN KEY(composicion_id) REFERENCES composicion_version (id) ON DELETE CASCADE, \n"
            "\tFOREIGN KEY(insumo_id) REFERENCES insumo (id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="esp_origenes",
        ddl=(
            "CREATE TABLE esp_origenes (\n"
            "\tversion_id INTEGER NOT NULL, \n"
            "\tid VARCHAR NOT NULL, \n"
            "\ttipo VARCHAR NOT NULL, \n"
            "\treferencia TEXT, \n"
            "\tPRIMARY KEY (version_id, id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="esp_ambientes",
        ddl=(
            "CREATE TABLE esp_ambientes (\n"
            "\tversion_id INTEGER NOT NULL, \n"
            "\tid VARCHAR NOT NULL, \n"
            "\tnombre VARCHAR NOT NULL, \n"
            "\tx0 VARCHAR NOT NULL, \n"
            "\ty0 VARCHAR NOT NULL, \n"
            "\tlargo VARCHAR NOT NULL, \n"
            "\tancho VARCHAR NOT NULL, \n"
            "\talto VARCHAR NOT NULL, \n"
            "\torigen_id VARCHAR NOT NULL, \n"
            "\tPRIMARY KEY (version_id, id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="esp_fuentes",
        ddl=(
            "CREATE TABLE esp_fuentes (\n"
            "\tversion_id INTEGER NOT NULL, \n"
            "\tid VARCHAR NOT NULL, \n"
            "\tespecialidad VARCHAR NOT NULL, \n"
            "\ttipo VARCHAR NOT NULL, \n"
            "\tambiente_id VARCHAR NOT NULL, \n"
            "\tposicion VARCHAR NOT NULL, \n"
            "\torigen_id VARCHAR NOT NULL, \n"
            "\tPRIMARY KEY (version_id, id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="esp_circuitos",
        ddl=(
            "CREATE TABLE esp_circuitos (\n"
            "\tversion_id INTEGER NOT NULL, \n"
            "\tid VARCHAR NOT NULL, \n"
            "\ttablero VARCHAR NOT NULL, \n"
            "\tnumero INTEGER NOT NULL, \n"
            "\tconductores VARCHAR NOT NULL, \n"
            "\tcalibre VARCHAR NOT NULL, \n"
            "\tpuntos_maximos INTEGER NOT NULL, \n"
            "\torden TEXT NOT NULL, \n"
            "\tPRIMARY KEY (version_id, id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="esp_puntos",
        ddl=(
            "CREATE TABLE esp_puntos (\n"
            "\tversion_id INTEGER NOT NULL, \n"
            "\tid VARCHAR NOT NULL, \n"
            "\tnombre VARCHAR NOT NULL, \n"
            "\tespecialidad VARCHAR NOT NULL, \n"
            "\ttipo VARCHAR NOT NULL, \n"
            "\tambiente_id VARCHAR NOT NULL, \n"
            "\tsuperficie VARCHAR NOT NULL, \n"
            "\tposicion VARCHAR NOT NULL, \n"
            "\tfuente_id VARCHAR, \n"
            "\tcircuito_id VARCHAR, \n"
            "\tespecificaciones TEXT NOT NULL, \n"
            "\torigen_id VARCHAR NOT NULL, \n"
            "\tPRIMARY KEY (version_id, id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="esp_recorridos",
        ddl=(
            "CREATE TABLE esp_recorridos (\n"
            "\tversion_id INTEGER NOT NULL, \n"
            "\tid VARCHAR NOT NULL, \n"
            "\tpunto_id VARCHAR, \n"
            "\tcircuito_id VARCHAR, \n"
            "\tmodo VARCHAR NOT NULL, \n"
            "\tPRIMARY KEY (version_id, id)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="esp_tramos",
        ddl=(
            "CREATE TABLE esp_tramos (\n"
            "\tversion_id INTEGER NOT NULL, \n"
            "\trecorrido_id VARCHAR NOT NULL, \n"
            "\torden INTEGER NOT NULL, \n"
            "\tsuperficie VARCHAR NOT NULL, \n"
            "\tempotrado BOOLEAN, \n"
            "\tvertices TEXT NOT NULL, \n"
            "\tpendiente VARCHAR, \n"
            "\tlongitud VARCHAR NOT NULL, \n"
            "\tPRIMARY KEY (version_id, recorrido_id, orden)\n"
            ")"
        ),
        indices=(),
    ),
    TablaCongelada(
        nombre="esp_sobrescrituras",
        ddl=(
            "CREATE TABLE esp_sobrescrituras (\n"
            "\tversion_id INTEGER NOT NULL, \n"
            "\tclave VARCHAR NOT NULL, \n"
            "\tdiametro VARCHAR, \n"
            "\tempotrado BOOLEAN, \n"
            "\tPRIMARY KEY (version_id, clave)\n"
            ")"
        ),
        indices=(),
    ),
)


def upgrade() -> None:
    crear_o_verificar(op.get_bind(), TABLAS)


def downgrade() -> None:
    borrar_tablas(op.get_bind(), TABLAS)
