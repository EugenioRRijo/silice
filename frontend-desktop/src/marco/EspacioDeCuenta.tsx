import { Button } from "@carbon/react";
import { Logout, User } from "@carbon/icons-react";
import { Suspense, lazy } from "react";
import type { ReactNode } from "react";
import { Link, Navigate, useLocation, useParams } from "react-router";
import type { SesionRespuesta } from "../api/tipos";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import { SelectorDeModo } from "../comun/SelectorDeModo";
import { TamanoLetra } from "../comun/TamanoLetra";
import { rolesConEtiqueta } from "../paginas/administracion/logica";
import { ContrasenaDeLaCuenta } from "../sesion/ContrasenaDeLaCuenta";
import { iniciales } from "../shell/iniciales";
import { LimiteDeError } from "../shell/LimiteDeError";
import { AvisoSinPermiso } from "./avisos";
import { BarraDeEspacio } from "./BarraDeEspacio";
import type { PestanaDeEspacio } from "./BarraDeEspacio";
import { SECCIONES_DE_CUENTA, SECCION_DE_ACTIVIDAD, esCuenta, rutaDeActividad, rutaDeCuenta } from "./espacios";
import type { CuentaDef } from "./espacios";
import { useOferta } from "./oferta";
import { RecorridosGuiados } from "./RecorridosGuiados";

// La actividad se carga a demanda: pesa lo que pesa su calendario y casi nadie la abre en cada sesión.
const Actividad = lazy(() => import("../paginas/actividad/Actividad"));
const PreferenciasDeNotificaciones = lazy(() => import("../paginas/notificaciones/PreferenciasDeNotificaciones"));

interface Props {
  sesion: SesionRespuesta;
  // La pantalla que monta una sección (`pagina` de SECCIONES_DE_CUENTA): la pinta el marco, con sus permisos y avisos.
  pantalla: (pagina: string) => ReactNode;
  alSalir: () => void;
}

// La cabecera de la Cuenta (diseño visual 2.3): quién es la persona, con qué rol, y «Salir de la sesión». No es un
// encabezado: el único h1 es el de la sección que se está viendo.
function CabeceraDeCuenta({ sesion, alSalir }: Pick<Props, "sesion" | "alSalir">) {
  const letras = iniciales(sesion.nombre);
  return (
    <section aria-label="Cuenta" className="silice-cuenta-cabecera">
      <div className="silice-cuenta-cabecera__persona">
        {letras ? (
          <span className="silice-cuenta__iniciales cds--type-label-01" aria-hidden="true">
            {letras}
          </span>
        ) : (
          <User size={16} className="silice-cuenta__persona" aria-hidden="true" />
        )}
        <div>
          <p className="silice-espacio-cabecera__titulo">{sesion.nombre}</p>
          <p className="silice-cuenta-cabecera__detalle cds--type-body-compact-01">
            {`${sesion.login} · ${rolesConEtiqueta(sesion.roles)}`}
          </p>
        </div>
      </div>
      <Button kind="tertiary" size="sm" renderIcon={Logout} onClick={alSalir}>
        Salir de la sesión
      </Button>
    </section>
  );
}

// «Configuración» (adenda C): el único lugar del tamaño de letra dentro del marco, para toda cuenta, con una
// muestra de lectura para comprobar al instante cómo se ve, y los datos de la cuenta.
function Preferencias({ sesion }: { sesion: SesionRespuesta }) {
  return (
    <div className="silice-cuenta-preferencias">
      <section aria-labelledby="pref-letra-titulo" className="silice-cuenta-preferencias__bloque">
        <h2 id="pref-letra-titulo" className="cds--type-heading-compact-02">
          Tamaño de letra
        </h2>
        <p className="cds--type-body-compact-01">
          Ajusta el tamaño de todos los textos, tablas y hojas en este navegador (Normal 100 %, Grande 125 %, Muy grande 150 %).
        </p>
        <TamanoLetra />
        <p className="silice-cuenta-preferencias__muestra cds--type-body-compact-01">
          {"Partida C-001 · Vaciado de concreto f'c 210 kgf/cm² — "}
          <span className="silice-codigo silice-cuenta-preferencias__cifra">242,64 USD/m³</span>
        </p>
      </section>
      <section className="silice-cuenta-preferencias__bloque">
        <SelectorDeModo />
      </section>
      <section aria-labelledby="pref-sesion-titulo" className="silice-cuenta-preferencias__bloque">
        <h2 id="pref-sesion-titulo" className="cds--type-heading-compact-02">
          Datos de la cuenta
        </h2>
        <dl className="silice-cuenta-preferencias__datos cds--type-body-compact-01">
          <dt>Nombre</dt>
          <dd>{sesion.nombre}</dd>
          <dt>Usuario</dt>
          <dd>{sesion.login}</dd>
          <dt>Rol</dt>
          <dd>{rolesConEtiqueta(sesion.roles)}</dd>
        </dl>
        <p className="cds--type-body-compact-01">
          <Link to={rutaDeActividad(sesion.login)} className="cds--link">
            Ver mi actividad
          </Link>
        </p>
      </section>
    </div>
  );
}

// El cuerpo de una sección, sin su h1: lo que la sección monta. Las cuatro de administración y la Ayuda pesan lo que pesa su
// pantalla (carga a demanda); «Configuración» no tiene pantalla en el registro.
function Contenido({ def, sesion, pantalla }: { def: CuentaDef; sesion: SesionRespuesta; pantalla: Props["pantalla"] }) {
  if (def.id === "preferencias") return <Preferencias sesion={sesion} />;
  if (def.id === "contrasena") return <ContrasenaDeLaCuenta />;
  if (def.id === "notificaciones") return <PreferenciasDeNotificaciones />;
  const montada = def.pagina === null ? null : pantalla(def.pagina);
  if (def.id !== "ayuda") return <>{montada}</>;
  return (
    <>
      {montada}
      <div className="silice-pagina">
        <RecorridosGuiados />
      </div>
    </>
  );
}

// La actividad de una cuenta (`/cuenta/actividad?usuario=<login>`): la cabecera y la barra de la Cuenta de siempre, con la
// pestaña de «Cuentas y permisos» marcada cuando quien administra mira a otra persona y la de «Configuración» en los demás
// casos. Si la consulta no trae usuario, es la propia cuenta. Quién puede ver a quién lo decide el servidor (403).
function ActividadDeUnaCuenta({ sesion, alSalir, usuario }: Pick<Props, "sesion" | "alSalir"> & { usuario: string }) {
  const { oferta } = useOferta();
  const pestanas: PestanaDeEspacio[] = oferta.cuenta.map((c) => ({ id: c.id, titulo: c.titulo, ruta: rutaDeCuenta(c.id) }));
  const deOtra = usuario !== sesion.login && oferta.cuenta.some((c) => c.id === "cuentas");
  return (
    <>
      <CabeceraDeCuenta sesion={sesion} alSalir={alSalir} />
      <BarraDeEspacio etiqueta="Secciones de la cuenta" pestanas={pestanas} activa={deOtra ? "cuentas" : "preferencias"} nivel="espacio" />
      <LimiteDeError key={usuario}>
        <Suspense fallback={<EsqueletoPagina />}>
          <div className="silice-pagina silice-cuenta-seccion">
            <h1 className="cds--type-heading-04">{`Actividad de ${usuario}`}</h1>
            <Actividad usuario={usuario} />
          </div>
        </Suspense>
      </LimiteDeError>
    </>
  );
}

// La Cuenta como espacio (`#/cuenta/:seccion`; plan F6, T6; contrato de rutas §3): su cabecera con la persona, la barra de
// secciones que la cuenta puede usar y, en el lienzo, la sección. Una sección que no existe lleva a «Configuración»; una
// que existe pero la cuenta no puede usar, escrita a mano, dice «Sin permiso» con la barra de lo que sí puede.
// «Ayuda y acerca de Sílice» no pone h1 propio: lo trae su pantalla, con el mismo nombre que la pestaña (como en las demás
// secciones, el h1 y la pestaña dicen lo mismo). Las demás lo ponen aquí, una sola vez.
export function EspacioDeCuenta({ sesion, pantalla, alSalir }: Props) {
  const { seccion } = useParams();
  const { search } = useLocation();
  const { oferta } = useOferta();
  if (seccion === SECCION_DE_ACTIVIDAD) {
    const usuario = new URLSearchParams(search).get("usuario")?.trim() || sesion.login;
    return <ActividadDeUnaCuenta sesion={sesion} alSalir={alSalir} usuario={usuario} />;
  }
  const def = seccion !== undefined && esCuenta(seccion) ? SECCIONES_DE_CUENTA.find((c) => c.id === seccion) : undefined;
  if (def === undefined) return <Navigate to={`${rutaDeCuenta("preferencias")}${search}`} replace />;
  const pestanas: PestanaDeEspacio[] = oferta.cuenta.map((c) => ({ id: c.id, titulo: c.titulo, ruta: rutaDeCuenta(c.id) }));
  const puede = oferta.cuenta.some((c) => c.id === def.id);
  return (
    <>
      <CabeceraDeCuenta sesion={sesion} alSalir={alSalir} />
      <BarraDeEspacio etiqueta="Secciones de la cuenta" pestanas={pestanas} activa={def.id} nivel="espacio" />
      <LimiteDeError key={def.id}>
        <Suspense fallback={<EsqueletoPagina />}>
          {puede ? (
            <div className={def.id === "ayuda" ? undefined : "silice-pagina silice-cuenta-seccion"}>
              {/* La Ayuda y Notificaciones ponen su propio h1: la pantalla tiene uno solo. */}
              {def.id !== "ayuda" && def.id !== "notificaciones" && <h1 className="cds--type-heading-04">{def.titulo}</h1>}
              <Contenido def={def} sesion={sesion} pantalla={pantalla} />
            </div>
          ) : (
            <div className="silice-pagina silice-cuenta-seccion">
              <h1 className="cds--type-heading-04">{def.titulo}</h1>
              <AvisoSinPermiso nivel={2} />
            </div>
          )}
        </Suspense>
      </LimiteDeError>
    </>
  );
}
