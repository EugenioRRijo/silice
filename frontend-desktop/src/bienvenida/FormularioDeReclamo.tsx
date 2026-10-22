import { Button, Checkbox, InlineNotification, PasswordInput } from "@carbon/react";
import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent, RefObject } from "react";
import { ErrorDeApi } from "../api/cliente";
import { CampoTexto } from "../comun/CampoTexto";
import { mensajeDeError } from "../comun/errores";
import "./bienvenida.scss";

// Contrato P1 del diseño (POST /v1/primer-arranque/reclamo). La contraseña repetida se compara aquí y NUNCA se manda.
export interface CuerpoDeReclamo {
  codigo: string;
  usuario: string;
  nombre: string;
  contrasena: string;
  tambien_arma: boolean;
}

export interface Politica {
  minimo: number;
  maximo: number;
}

type Variante = "bienvenida" | "recuperar";

const TEXTOS = {
  bienvenida: {
    codigo: "Código de instalación",
    usuario: "Usuario",
    contrasena: "Contraseña",
    repetida: "Repita la contraseña",
    enviar: "Crear la cuenta y entrar",
    enviando: "Creando la cuenta…",
    titulo: "No se pudo crear la cuenta",
    escribaCodigo: "Escriba el código de instalación.",
    escribaUsuario: "Escriba el usuario que va a usar.",
    escribaContrasena: "Escriba una contraseña.",
  },
  recuperar: {
    codigo: "Código de restablecimiento",
    usuario: "Usuario del administrador",
    contrasena: "Contraseña nueva",
    repetida: "Repita la contraseña nueva",
    enviar: "Restablecer y entrar",
    enviando: "Restableciendo el acceso…",
    titulo: "No se pudo restablecer el acceso",
    escribaCodigo: "Escriba el código de restablecimiento.",
    escribaUsuario: "Escriba el usuario del administrador.",
    escribaContrasena: "Escriba la contraseña nueva.",
  },
} as const;

const ESCRIBA_NOMBRE = "Escriba su nombre.";
export const NO_COINCIDEN = "Las dos contraseñas no coinciden.";
const LISTO_DE_NUEVO = "Ya puede volver a intentarlo.";

interface Props {
  variante: Variante;
  politica: Politica;
  onReclamar: (cuerpo: CuerpoDeReclamo) => Promise<void>;
  // Solo en la bienvenida: la casilla «usaré esta cuenta también para armar presupuestos» (D-2), desmarcada.
  tambienArma?: boolean;
  alCambiarTambienArma?: (valor: boolean) => void;
}

// El `aria-describedby` de Carbon sale de su propio ayudante y reemplaza al que se le pase: aquí se le suma, después
// de cada render, el texto de la política (siempre visible) para que la lectora lo diga con el campo.
function useDescritoPor(campo: RefObject<HTMLInputElement | null>, id: string) {
  useEffect(() => {
    const entrada = campo.current;
    if (!entrada) return;
    const ids = (entrada.getAttribute("aria-describedby") ?? "").split(" ").filter(Boolean);
    if (!ids.includes(id)) entrada.setAttribute("aria-describedby", [...ids, id].join(" "));
  });
}

export function FormularioDeReclamo({ variante, politica, onReclamar, tambienArma = false, alCambiarTambienArma }: Props) {
  const t = TEXTOS[variante];
  const base = useId().replace(/:/g, "");
  const ids = {
    codigo: `${base}-codigo`,
    nombre: `${base}-nombre`,
    usuario: `${base}-usuario`,
    contrasena: `${base}-contrasena`,
    repetida: `${base}-repetida`,
    politica: `${base}-politica`,
    politicaTitulo: `${base}-politica-titulo`,
  };

  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [usuario, setUsuario] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [repetida, setRepetida] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [intentado, setIntentado] = useState(false);
  const [errorDelServidor, setErrorDelServidor] = useState<string | null>(null);
  const [espera, setEspera] = useState(0);
  const [aviso, setAviso] = useState("");

  // Una sola petición en vuelo: el estado `enviando` llega tarde a un segundo envío con Intro; la ref no.
  const enEnvio = useRef(false);
  const resumen = useRef<HTMLDivElement>(null);
  const resumenYaEnfocado = useRef(false);
  const entradaContrasena = useRef<HTMLInputElement>(null);
  const entradaRepetida = useRef<HTMLInputElement>(null);
  useDescritoPor(entradaContrasena, ids.politica);
  useDescritoPor(entradaRepetida, ids.politica);

  const errores = {
    codigo: !codigo.trim() ? t.escribaCodigo : null,
    nombre: !nombre.trim() ? ESCRIBA_NOMBRE : null,
    usuario: !usuario.trim() ? t.escribaUsuario : null,
    contrasena: !contrasena ? t.escribaContrasena : null,
    repetida: contrasena && contrasena !== repetida ? NO_COINCIDEN : null,
  };
  const lista = Object.values(errores).filter((m): m is string => m !== null);
  const hayEspera = espera > 0;

  // El resumen recibe el foco la primera vez que se envía con fallos; después solo se anuncia (role="alert").
  useEffect(() => {
    if (intentado && lista.length > 0 && !resumenYaEnfocado.current) {
      resumenYaEnfocado.current = true;
      resumen.current?.focus();
    }
  });

  // 429: la cuenta regresiva corre por intervalo, no por una cadena de temporizadores, para no depender del render.
  useEffect(() => {
    if (!hayEspera) return;
    const reloj = setInterval(() => setEspera((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(reloj);
  }, [hayEspera]);
  const esperaPrevia = useRef(0);
  useEffect(() => {
    if (esperaPrevia.current > 0 && espera === 0) setAviso(LISTO_DE_NUEVO);
    esperaPrevia.current = espera;
  }, [espera]);

  function borrarSecretos(incluirContrasenas: boolean) {
    setCodigo("");
    if (incluirContrasenas) {
      setContrasena("");
      setRepetida("");
    }
  }

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (enEnvio.current || hayEspera) return;
    setIntentado(true);
    setErrorDelServidor(null);
    setAviso("");
    if (lista.length > 0) return;

    enEnvio.current = true;
    setEnviando(true);
    try {
      await onReclamar({
        codigo: codigo.trim(),
        usuario: usuario.trim(),
        nombre: nombre.trim(),
        contrasena, // sin recortar: los espacios son parte de la contraseña
        tambien_arma: variante === "bienvenida" && tambienArma,
      });
      // Éxito: la sesión ya está abierta y esta pantalla se va; ningún secreto queda en el estado.
      borrarSecretos(true);
      setIntentado(false);
    } catch (error) {
      // Los avisos de «falta esto» son de antes del envío: el código recién borrado no debe pintarse como un olvido.
      setIntentado(false);
      setErrorDelServidor(mensajeDeError(error));
      if (error instanceof ErrorDeApi && error.estado === 429) setEspera(error.reintentarEnSegundos ?? 1);
      // El código se borra tras cualquier error (se vuelve a pegar). Con 401 y 423 la cuenta pedida no se creó y el
      // código no sirvió: tampoco se deja la contraseña escrita en el DOM.
      const sinCuenta = error instanceof ErrorDeApi && (error.estado === 401 || error.estado === 423);
      borrarSecretos(sinCuenta);
      document.getElementById(ids.codigo)?.focus();
    } finally {
      enEnvio.current = false;
      setEnviando(false);
    }
  }

  const mostrar = (clave: keyof typeof errores) => (intentado ? errores[clave] : null);
  const contador = `${[...contrasena].length} de ${politica.minimo} caracteres como mínimo`;
  const textoDelBoton = enviando ? t.enviando : hayEspera ? `Espere ${espera} s` : t.enviar;

  return (
    <form className="silice-bienvenida__formulario" onSubmit={enviar} noValidate>
      {intentado && lista.length > 0 && (
        <div ref={resumen} className="silice-bienvenida__resumen" role="alert" tabIndex={-1}>
          <p className="cds--type-heading-compact-01">Revise estos datos antes de seguir:</p>
          <ul>
            {lista.map((mensaje) => (
              <li key={mensaje}>{mensaje}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="silice-bienvenida__campos">
        <div className="silice-bienvenida__ancho-completo">
          <CampoTexto
            id={ids.codigo}
            labelText={t.codigo}
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            autoComplete="off"
            spellCheck={false}
            autoCapitalize="characters"
            invalid={mostrar("codigo") !== null}
            invalidText={mostrar("codigo") ?? ""}
          />
        </div>
        <CampoTexto
          id={ids.nombre}
          labelText="Su nombre"
          helperText="Así aparecerá en lo que usted guarde."
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          autoComplete="name"
          invalid={mostrar("nombre") !== null}
          invalidText={mostrar("nombre") ?? ""}
        />
        <CampoTexto
          id={ids.usuario}
          labelText={t.usuario}
          helperText="De 3 a 40 letras minúsculas, números, punto o guion."
          value={usuario}
          onChange={(e) => setUsuario(e.target.value)}
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          invalid={mostrar("usuario") !== null}
          invalidText={mostrar("usuario") ?? ""}
        />
        <div
          id={ids.politica}
          className="silice-bienvenida__politica silice-bienvenida__ancho-completo"
          role="group"
          aria-labelledby={ids.politicaTitulo}
        >
          <p id={ids.politicaTitulo} className="cds--type-heading-compact-01">
            Cómo debe ser la contraseña
          </p>
          <ul className="cds--type-body-compact-01">
            <li>De {politica.minimo} a {politica.maximo} caracteres. Una frase larga es mejor que una palabra con símbolos.</li>
            <li>No puede ser igual a su usuario ni una contraseña muy conocida (por ejemplo «password123»).</li>
            <li>No hace falta mezclar mayúsculas, números o símbolos.</li>
            <li>Sílice no puede recuperarla: si la olvida, un administrador del equipo tiene que restablecerla.</li>
          </ul>
        </div>
        <PasswordInput
          ref={entradaContrasena}
          id={ids.contrasena}
          labelText={t.contrasena}
          helperText={contador}
          value={contrasena}
          onChange={(e) => setContrasena(e.target.value)}
          autoComplete="new-password"
          invalid={mostrar("contrasena") !== null}
          invalidText={mostrar("contrasena") ?? ""}
          showPasswordLabel="Mostrar la contraseña"
          hidePasswordLabel="Ocultar la contraseña"
        />
        <PasswordInput
          ref={entradaRepetida}
          id={ids.repetida}
          labelText={t.repetida}
          value={repetida}
          onChange={(e) => setRepetida(e.target.value)}
          autoComplete="new-password"
          invalid={mostrar("repetida") !== null}
          invalidText={mostrar("repetida") ?? ""}
          showPasswordLabel="Mostrar la contraseña"
          hidePasswordLabel="Ocultar la contraseña"
        />
      </div>
      {variante === "bienvenida" && (
        <Checkbox
          id={`${base}-arma`}
          labelText="Usaré esta cuenta también para armar presupuestos"
          helperText="Si usted trabaja solo, márquelo. Si no, luego cree otra cuenta con el rol «Arma»."
          checked={tambienArma}
          onChange={(_, { checked }) => alCambiarTambienArma?.(checked)}
        />
      )}
      {errorDelServidor && (
        <InlineNotification kind="error" role="alert" title={t.titulo} subtitle={errorDelServidor} hideCloseButton lowContrast />
      )}
      <Button type="submit" disabled={enviando || hayEspera}>
        {textoDelBoton}
      </Button>
      <p className="silice-bienvenida__estado cds--type-body-compact-01" role="status">
        {enviando ? t.enviando : aviso}
      </p>
    </form>
  );
}
