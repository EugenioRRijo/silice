import { Button } from "@carbon/react";
import { Suspense, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Link, Navigate, useLocation, useParams } from "react-router";
import type { CasosRespuesta } from "../api/tipos";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import { ProveedorDeLaHoja } from "../paginas/hoja/ProveedorDeLaHoja";
import { ContextoAplicacion } from "../shell/contexto";
import { LimiteDeError } from "../shell/LimiteDeError";
import { BarraDeEspacio, pestanasUsables } from "./BarraDeEspacio";
import { CabeceraDeObra } from "./CabeceraDeObra";
import { SUBVISTAS, vistaDeLaSeccion } from "./espacios";
import { enfocarElTitulo } from "./focoAlTitulo";
import { ContextoDeLaObra } from "./obraAbierta";
import type { ObraAbierta } from "./obraAbierta";
import { seccionesDeLaObra, useOferta } from "./oferta";
import { RUTA_DE_PENDIENTES, SECCIONES_CON_HOJA, rutaDeObra } from "./secciones";
import type { SeccionDef } from "./secciones";
import { useFichaDeLaObra } from "./useFichaDeLaObra";
import type { FichaDeLaObra } from "./useFichaDeLaObra";
import { useObraDeLaRuta } from "./useObraDeLaRuta";
import type { VigilanteDeObra } from "./otraPestana";
import type { ObraDeCarpeta } from "./useObras";

interface Props {
  obras: readonly ObraDeCarpeta[];
  casos: CasosRespuesta | null;
  // La obra quedó lista (carpeta y obra fijadas en la sesión del servidor): el marco la recuerda.
  alEntrar: (carpeta: string | null, obraId: number) => void;
  // La pantalla de la sección (`pagina` de SECCIONES_DE_OBRA): la pinta el marco, con sus permisos.
  pantalla: (pagina: string) => ReactNode;
  vigilante?: VigilanteDeObra;
}

// Un aviso de pantalla completa con su h1 (el foco va a él al llegar, como con cualquier pantalla). Con `alerta`, el
// texto se anuncia solo (role="alert"): un fallo o un cambio que llega de fuera debe oírse aunque el foco no se mueva
// (la carga inicial, un reintento que vuelve a fallar, una respuesta que tarda, el mensaje de otra pestaña).
function Aviso({ titulo, texto, alerta = false, children }: { titulo: string; texto: string; alerta?: boolean; children: ReactNode }) {
  return (
    <div className="silice-pagina silice-obra-aviso">
      <h1 className="cds--type-heading-04">{titulo}</h1>
      <p className="cds--type-body-compact-01" role={alerta ? "alert" : undefined}>
        {texto}
      </p>
      {children}
    </div>
  );
}

// La obra de la ruta `#/obra/<carpeta>/<obra>/<sección>[/<subvista>]` como espacio de trabajo (plan del rediseño del marco, Tarea 8;
// especificación 2026-10-26, §2.3 y §8 ter): primero fija carpeta y obra en la sesión (useObraDeLaRuta) y solo
// entonces monta la sección, con la cabecera de la obra encima. Mientras otra pestaña tenga otra obra, la sección no se
// monta: no hay escrituras en la obra equivocada.
export function EspacioDeObra({ obras, casos, alEntrar, pantalla, vigilante }: Props) {
  const estado = useObraDeLaRuta({ vigilante });
  const { subvista } = useParams();
  const lista = estado.tipo === "lista" ? estado : null;
  const clave = lista ? JSON.stringify([lista.carpeta, lista.obraId]) : null;

  useEffect(() => {
    if (clave === null) return;
    const [carpeta, obraId] = JSON.parse(clave) as [string | null, number];
    alEntrar(carpeta, obraId);
  }, [clave, alEntrar]);

  // «Reintentar» y «Retomar» vuelven a entrar: quitan su botón (la obra vuelve a «cargando») y la ruta no cambia, así
  // que el marco no mueve el foco. Cuando se sabe el resultado, pasa al h1 del aviso otra vez o al de la sección.
  const [entradas, setEntradas] = useState(0);
  const tipo = estado.tipo;
  useEffect(() => {
    if (entradas === 0 || tipo === "cargando") return;
    return enfocarElTitulo();
  }, [entradas, tipo]);
  const volverAEntrar = (accion: () => void) => () => {
    setEntradas((n) => n + 1);
    accion();
  };

  switch (estado.tipo) {
    case "cargando":
      return <EsqueletoPagina etiqueta="Abriendo la obra" />;
    case "no_existe":
      return (
        <Aviso titulo="Esa obra ya no existe" texto="La borraron o su carpeta ya no está en esta instalación.">
          <Link className="cds--link" to={RUTA_DE_PENDIENTES}>
            Volver a Pendientes
          </Link>
        </Aviso>
      );
    case "en_otra_pestana":
      return (
        <Aviso
          titulo="Esta obra se abrió en otra pestaña"
          texto="Otra pestaña de Sílice abrió otra obra. Retómela aquí para seguir trabajando en esta."
          alerta
        >
          <Button kind="primary" size="md" onClick={volverAEntrar(estado.retomar)}>
            Retomar
          </Button>
        </Aviso>
      );
    case "error":
      return (
        <Aviso titulo="No se pudo abrir la obra" texto="Revise la conexión con Sílice y vuelva a intentarlo." alerta>
          <Button kind="tertiary" size="md" onClick={volverAEntrar(estado.reintentar)}>
            Reintentar
          </Button>
        </Aviso>
      );
    case "lista":
      return (
        <ObraDeLaRuta
          carpeta={estado.carpeta}
          obraId={estado.obraId}
          obra={obras.find((o) => o.carpeta === estado.carpeta && o.obra_id === estado.obraId)}
          casos={casos}
          seccion={estado.seccion}
          subvista={subvista}
          pantalla={pantalla}
        />
      );
  }
}

interface ObraDeLaRutaProps {
  carpeta: string | null;
  obraId: number;
  obra: ObraDeCarpeta | undefined;
  casos: CasosRespuesta | null;
  seccion: SeccionDef;
  // El cuarto segmento de la ruta (`:subvista`), si lo trae.
  subvista: string | undefined;
  pantalla: (pagina: string) => ReactNode;
}

// La obra lista: lee su ficha una vez, la comparte con las secciones (ContextoDeLaObra) y pinta la cabecera encima de la
// sección, con la barra de las secciones de la obra justo debajo (F6, T5; diseño visual 2.2). Dentro de la sección, si tiene
// 2 o más vistas usables, el conmutador de subvistas va a la cabeza del lienzo (adenda A.2). La sección lee la obra y la
// carpeta de la ruta desde el primer dibujo (no las del marco, que se ponen al día un momento después).
//
// F6, T5: la pantalla que se monta sale de `vistaDeLaSeccion` (sección + subvista de la ruta + permisos). Una ruta sin
// subvista o con una desconocida lleva a la primera subvista que la cuenta puede usar (la pantalla principal, si puede
// usarla; si no, la siguiente: Aprobaciones para quien solo revisa abre «Revisar un paquete»), con replace y conservando la
// consulta. Pasar de Presupuesto a Componer sigue en la misma sección: ni se vuelve a montar `ProveedorDeLaHoja` ni se
// pregunta por cambios sin guardar (`quedaEnLaHoja`).
//
// Tarea 3 del plan F4: en Presupuesto, Archivos y planos y Versiones (SECCIONES_CON_HOJA) la cabecera y la sección van
// dentro de `ProveedorDeLaHoja`, siempre en esta posición y con la clave de la obra: pasar entre esas tres no lo
// desmonta (el borrador sigue abierto) y cambiar de obra o de carpeta sí (se descarta, o se conserva para retomarlo si
// tiene cambios, como al salir de la Hoja). En las demás no se abre ningún borrador. Sin `leer_proyecto` (la acción de
// la Hoja y de sus lecturas, Tarea 2b) tampoco: la sección dice «Sin permiso» y el proveedor solo daría 403. El límite
// de error y la espera de la pantalla perezosa son de la sección: el marco ya no los reinicia al cambiar de sección.
function ObraDeLaRuta({ carpeta, obraId, obra, casos, seccion: def, subvista, pantalla: montar }: ObraDeLaRutaProps) {
  const seccion = def.id;
  const base = useContext(ContextoAplicacion);
  const { search } = useLocation();
  const { acciones, oferta } = useOferta();
  const modoEntrega = base?.sesion.modo_entrega ?? false;
  const apagados = base?.modulosApagados ?? [];
  const { recargar, ...ficha } = useFichaDeLaObra(obraId, carpeta);
  // Ronda 2 de la Tarea 3 (decisión del orquestador): volver al Resumen desde otra sección vuelve a leer la ficha, para
  // que diga lo que cambió en Presupuesto, Aprobaciones o Control. Mientras llega se ve la anterior (Tarea 1, decisión 3).
  // Ajuste durante el render (react.dev, «You might not need an effect»): `recargar` es estado de esta misma pieza.
  const [seccionVista, setSeccionVista] = useState(seccion);
  if (seccionVista !== seccion) {
    setSeccionVista(seccion);
    if (seccion === "resumen") recargar();
  }
  const valor = useMemo(() => {
    if (!base) return null;
    const caso =
      carpeta === null
        ? (casos?.empresa ?? base.caso)
        : (casos?.casos.find((c) => c.nombre === carpeta) ?? { nombre: carpeta, ruta_relativa: "" });
    return { ...base, proyecto: String(obraId), nombreProyecto: obra?.obra ?? null, caso };
  }, [base, carpeta, obraId, obra, casos]);
  // Sin useMemo: el valor cambia solo cuando cambia la ficha o la obra, que es cuando esta pieza vuelve a pintarse.
  const abierta: ObraAbierta = { carpeta, obraId, ficha: ficha as FichaDeLaObra, recargarFicha: recargar };

  const conHoja = SECCIONES_CON_HOJA.includes(seccion) && base?.sesion.acciones.includes("leer_proyecto") === true;
  const vista = vistaDeLaSeccion(def, subvista, acciones, modoEntrega, apagados);
  if (vista.redirigeA !== null) {
    return <Navigate to={`${rutaDeObra(carpeta, obraId, seccion, vista.redirigeA)}${search}`} replace />;
  }
  const secciones = seccionesDeLaObra(oferta).map((s) => ({ id: s.id, titulo: s.titulo, ruta: rutaDeObra(carpeta, obraId, s.id) }));
  const subvistas = pestanasUsables(SUBVISTAS[seccion] ?? [], (h) => rutaDeObra(carpeta, obraId, seccion, h.id), acciones, modoEntrega, apagados);
  const subvistaActiva = (SUBVISTAS[seccion] ?? []).find((v) => v.pagina === vista.pagina)?.id ?? "";
  const cabecera = (
    <>
      <CabeceraDeObra carpeta={carpeta} obraId={obraId} nombre={obra?.obra} version={obra?.version_codigo} ficha={abierta.ficha} />
      {/* Sin ninguna sección usable no hay barra que ofrecer (la pantalla dice por qué). */}
      {secciones.length > 0 && <BarraDeEspacio etiqueta="Secciones de la obra" pestanas={secciones} activa={seccion} nivel="espacio" />}
    </>
  );
  const pantalla = (
    <>
      <BarraDeEspacio etiqueta={`Vistas de ${def.titulo}`} pestanas={subvistas} activa={subvistaActiva} nivel="subvista" />
      <LimiteDeError key={`${seccion}|${vista.pagina}`}>
        <Suspense fallback={<EsqueletoPagina />}>{vista.pagina !== null && montar(vista.pagina)}</Suspense>
      </LimiteDeError>
    </>
  );

  return (
    <ContextoDeLaObra.Provider value={abierta}>
      <ContextoAplicacion.Provider value={valor}>
        {conHoja ? (
          <ProveedorDeLaHoja key={JSON.stringify([carpeta, obraId])}>
            {cabecera}
            {pantalla}
          </ProveedorDeLaHoja>
        ) : (
          <>
            {cabecera}
            {pantalla}
          </>
        )}
      </ContextoAplicacion.Provider>
    </ContextoDeLaObra.Provider>
  );
}
