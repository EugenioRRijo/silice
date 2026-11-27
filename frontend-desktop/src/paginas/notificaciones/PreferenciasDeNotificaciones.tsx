import { Button, Toggle } from "@carbon/react";
import { useEffect, useId, useState } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { RUTA_DE_PREFERENCIAS } from "../../comun/notificaciones/PanelDeNotificaciones";
import { fijarPreferencia, leerPreferencias } from "./api";
import type { CategoriaDeNotificacion } from "./api";
import "./PreferenciasDeNotificaciones.scss";

// La ruta vive en lo común (el pie del panel la usa y lo común no importa de las páginas); aquí se vuelve a exportar
// para que el marco registre la pantalla con ella.
export { RUTA_DE_PREFERENCIAS };

// Por qué una categoría no se puede apagar, dicho en texto: el servidor solo marca `obligatoria`.
const RAZONES_DE_LO_OBLIGATORIO: Record<string, string> = {
  por_dictaminar: "Quien revisa recibe siempre las versiones que esperan su dictamen.",
};
const RAZON_GENERAL = "Su papel en el programa no permite apagar este aviso.";

type Estado =
  | { tipo: "cargando" }
  | { tipo: "error"; error: unknown }
  | { tipo: "listo"; categorias: CategoriaDeNotificacion[] };

const TITULO = "Notificaciones";

// Cuenta › Notificaciones (C11b): qué avisos le llegan a la campanita. Cada interruptor se guarda al momento; si el servidor
// lo rechaza, vuelve a como estaba y se dice por qué. Las categorías que no le tocan por su papel no se muestran.
export default function PreferenciasDeNotificaciones() {
  const base = useId();
  const [estado, setEstado] = useState<Estado>({ tipo: "cargando" });
  const [intento, setIntento] = useState(0);
  const [guardando, setGuardando] = useState<ReadonlySet<string>>(new Set());
  const [errorAlGuardar, setErrorAlGuardar] = useState<unknown>(null);

  useEffect(() => {
    let vigente = true;
    leerPreferencias().then(
      (r) => {
        if (vigente) setEstado({ tipo: "listo", categorias: r.categorias });
      },
      (error: unknown) => {
        if (vigente) setEstado({ tipo: "error", error });
      },
    );
    return () => {
      vigente = false;
    };
  }, [intento]);

  function reintentar() {
    setEstado({ tipo: "cargando" });
    setIntento((n) => n + 1);
  }

  function ponerActiva(categoria: string, activa: boolean) {
    setEstado((actual) =>
      actual.tipo === "listo"
        ? { tipo: "listo", categorias: actual.categorias.map((c) => (c.categoria === categoria ? { ...c, activa } : c)) }
        : actual,
    );
  }

  function marcarGuardando(categoria: string, enCurso: boolean) {
    setGuardando((actual) => {
      const siguiente = new Set(actual);
      if (enCurso) siguiente.add(categoria);
      else siguiente.delete(categoria);
      return siguiente;
    });
  }

  async function cambiar(categoria: string, activa: boolean) {
    setErrorAlGuardar(null);
    marcarGuardando(categoria, true);
    ponerActiva(categoria, activa);
    try {
      const respuesta = await fijarPreferencia(categoria, activa);
      const guardada = respuesta.categorias.find((c) => c.categoria === categoria);
      ponerActiva(categoria, guardada?.activa ?? activa);
    } catch (error) {
      ponerActiva(categoria, !activa);
      setErrorAlGuardar(error);
    } finally {
      marcarGuardando(categoria, false);
    }
  }

  if (estado.tipo === "cargando") return <EsqueletoPagina titulo={TITULO} etiqueta="Cargando sus notificaciones" />;

  const cabecera = (
    <>
      <h1 className="cds--type-heading-04">{TITULO}</h1>
      <p className="cds--type-body-compact-01">
        Elija qué avisos quiere recibir en la campanita. Apagar uno no borra lo que ya recibió: solo deja de llegarle lo nuevo.
      </p>
    </>
  );

  if (estado.tipo === "error") {
    return (
      <section className="silice-pref-notificaciones" aria-label="Notificaciones que recibe">
        {cabecera}
        <AvisoError error={estado.error} titulo="No se pudieron cargar sus notificaciones" />
        <div className="silice-pref-notificaciones__acciones">
          <Button kind="tertiary" size="sm" onClick={reintentar}>
            Reintentar
          </Button>
        </div>
      </section>
    );
  }

  const visibles = estado.categorias.filter((c) => c.aplica);

  return (
    <section className="silice-pref-notificaciones" aria-label="Notificaciones que recibe">
      {cabecera}
      <AvisoError error={errorAlGuardar} titulo="No se pudo guardar el cambio" alCerrar={() => setErrorAlGuardar(null)} />
      {visibles.length === 0 ? (
        <EstadoVacio
          titulo="Por ahora no hay avisos que elegir."
          descripcion="Lo que puede recibir se decide según los permisos de su cuenta. Si se los amplían, aparecerá aquí para elegirlo."
        />
      ) : (
        <ul className="silice-pref-notificaciones__lista">
          {visibles.map((c) => {
            const idDescripcion = `${base}-${c.categoria}-descripcion`;
            const idRazon = `${base}-${c.categoria}-razon`;
            const enCurso = guardando.has(c.categoria);
            return (
              <li key={c.categoria} className="silice-pref-notificaciones__item">
                <Toggle
                  id={`${base}-${c.categoria}`}
                  labelText={c.titulo}
                  labelA="Apagada"
                  labelB="Encendida"
                  toggled={c.obligatoria ? true : c.activa}
                  disabled={c.obligatoria || enCurso}
                  aria-describedby={c.obligatoria ? `${idDescripcion} ${idRazon}` : idDescripcion}
                  onToggle={(encendida: boolean) => void cambiar(c.categoria, encendida)}
                />
                <p id={idDescripcion} className="silice-pref-notificaciones__descripcion cds--type-body-compact-01">
                  {c.descripcion}
                </p>
                {c.obligatoria && (
                  <p id={idRazon} className="silice-pref-notificaciones__razon cds--type-label-01">
                    {RAZONES_DE_LO_OBLIGATORIO[c.categoria] ?? RAZON_GENERAL}
                  </p>
                )}
                {enCurso && (
                  <p role="status" className="silice-pref-notificaciones__estado cds--type-label-01">
                    Guardando…
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
