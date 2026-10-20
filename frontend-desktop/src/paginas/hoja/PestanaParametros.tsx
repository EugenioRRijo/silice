import { useCallback, useId, useState } from "react";
import { pedir } from "../../api/cliente";
import { useAplicacion } from "../../shell/contexto";
import { AvisoDeEdicion, AvisoDeEnvio } from "./AvisoDeEdicion";
import { CampoDeCelda } from "./CampoDeCelda";
import { Cifra } from "./Cifra";
import { VistaCarga } from "./VistaCarga";
import { rutaDeVista } from "./logica";
import type { Resumen, VistaParametros } from "./logica";
import { FRASES_DE_RECHAZO, cuerpoDeParametros, rutaDeParametros, sembrarParametros, ubicarErrorDeParametro } from "./logicaSecciones";
import type { UbicacionDeParametro, ValoresDeParametros } from "./logicaSecciones";
import { useEdicionDeSeccion } from "./useEdicionDeSeccion";

interface Props {
  id: string;
  // El `rev` del borrador según la página.
  rev: number;
  moneda: string;
  alAusente: () => void;
  // El servidor aceptó una edición: su resumen pasa a la barra de estado de la página.
  alAceptar: (resumen: Resumen) => void;
  alRecargarBorrador: () => Promise<void>;
  // Descarta lo que se ve y abre otro borrador de la versión (cuando recargar no sirve).
  alReabrir: () => void;
}

interface PropsContenido extends Props {
  vista: VistaParametros;
  alRelectura: () => void;
}

function ContenidoParametros({ id, rev, moneda, vista, alAusente, alAceptar, alRecargarBorrador, alReabrir, alRelectura }: PropsContenido) {
  const { alExpirar } = useAplicacion();
  const idDelError = useId();
  const edicion = useEdicionDeSeccion<ValoresDeParametros, UbicacionDeParametro>({
    inicial: sembrarParametros(vista.campos),
    rev,
    peticion: (r, valores) => ({ ruta: rutaDeParametros(id), metodo: "PUT", cuerpo: cuerpoDeParametros(r, valores) }),
    ubicar: ubicarErrorDeParametro,
    frase: FRASES_DE_RECHAZO.parametros,
    leerFresca: async () => sembrarParametros((await pedir<VistaParametros>(rutaDeVista(id, "parametros"))).campos),
    alAceptar,
    alRelectura,
    alRecargarBorrador,
    alAusente,
    alExpirar,
  });
  const { error } = edicion;
  const ubicacion = error?.ubicacion ?? null;

  return (
    <div className="silice-hoja__pestana">
      <p className="cds--type-body-compact-01">
        Los parámetros de costo del borrador. Decimales con punto, por ejemplo 2.5: la coma no se acepta. Cambiarlos recalcula todos los
        APU y el total; los cambios se aplican al borrador cuando deja de escribir y no se guardan como versión hasta que lo pida.
      </p>
      <AvisoDeEnvio envio={edicion.envio} />
      {error !== null && <AvisoDeEdicion error={error} id={idDelError} alRecargar={() => void edicion.recargar()} alReabrir={alReabrir} />}
      <div className="silice-hoja__campos">
        {vista.campos.map((c) => (
          <CampoDeCelda
            key={c.clave}
            id={`hoja-parametro-${c.clave}`}
            etiqueta={c.rotulo}
            etiquetaVisible
            valor={edicion.estado[c.clave] ?? ""}
            invalido={ubicacion !== null && ubicacion.campo === c.clave}
            textoInvalido={ubicacion?.texto}
            descripcionId={idDelError}
            alCambiar={(valor) => edicion.cambiar((previo) => ({ ...previo, [c.clave]: valor }))}
            alRestaurar={() => edicion.cambiar((previo) => ({ ...previo, [c.clave]: edicion.aceptado()[c.clave] ?? "" }))}
          />
        ))}
      </div>
      {vista.moneda_proyecto !== null && (
        <p className="cds--type-body-compact-01">Moneda del proyecto: {vista.moneda_proyecto}</p>
      )}
      <p className="silice-hoja__total cds--type-heading-03">
        Total del presupuesto <Cifra monto={vista.total} unidad={moneda} />
      </p>
    </div>
  );
}

// Pestaña «Parámetros»: los cuatro se editan como texto (rebanada 3c-2) y se aplican al borrador del servidor; convertir la
// moneda llega en la rebanada 3d.
export function PestanaParametros(props: Props) {
  // Sube cada vez que hay que volver a leer la vista tras una edición: la anterior sigue a la vista mientras llega.
  const [lecturas, setLecturas] = useState(0);
  const alRelectura = useCallback(() => setLecturas((n) => n + 1), []);
  return (
    <VistaCarga<VistaParametros> ruta={rutaDeVista(props.id, "parametros")} etiqueta="Parámetros" alAusente={props.alAusente} recarga={lecturas}>
      {(vista) => <ContenidoParametros {...props} vista={vista} alRelectura={alRelectura} />}
    </VistaCarga>
  );
}
