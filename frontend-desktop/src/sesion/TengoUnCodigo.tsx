import { Button, Form } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { CampoTexto } from "../comun/CampoTexto";
import { InlineNotification, PasswordInput } from "../comun/carbonEs";
import { mensajeDeError } from "../comun/errores";
import { useTituloDelDocumento } from "../comun/tituloDelDocumento";
import { canjearCodigo } from "./useSesion";
import "./sesion.scss";

interface Props {
  onCanjear?: (login: string, contrasena: string, codigo: string) => Promise<void>;
  alVolver?: () => void;
}

type CampoDeCanje = "login" | "contrasena" | "codigo";

const ID_CAMPO: Record<CampoDeCanje, string> = {
  login: "canjear-usuario",
  contrasena: "canjear-contrasena",
  codigo: "canjear-codigo",
};

export function TengoUnCodigo({ onCanjear, alVolver }: Props) {
  useTituloDelDocumento("Tengo un código");
  const [login, setLogin] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [codigo, setCodigo] = useState("");
  const [intentado, setIntentado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const focoPendiente = useRef<{ tipo: "campo"; campo: CampoDeCanje } | { tipo: "alerta" } | null>(null);
  const refAlerta = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const objetivo = focoPendiente.current;
    if (objetivo === null) return;
    focoPendiente.current = null;
    if (objetivo.tipo === "campo") {
      document.getElementById(ID_CAMPO[objetivo.campo])?.focus();
    } else {
      refAlerta.current?.focus();
    }
  });

  const codigoSinSeparadores = codigo.replace(/[\s-]+/g, "");

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (enviando) return;
    setIntentado(true);
    setError(null);

    const faltante: CampoDeCanje | null = !login.trim()
      ? "login"
      : !contrasena
        ? "contrasena"
        : !codigoSinSeparadores
          ? "codigo"
          : null;
    if (faltante !== null) {
      focoPendiente.current = { tipo: "campo", campo: faltante };
      document.getElementById(ID_CAMPO[faltante])?.focus();
      return;
    }

    const usuarioEnviado = login.trim();
    const claveEnviada = contrasena;
    const codigoEnviado = codigo.trim();
    const ejecutar = onCanjear ?? canjearCodigo;

    setEnviando(true);
    setContrasena("");
    setCodigo("");
    setIntentado(false);

    try {
      await ejecutar(usuarioEnviado, claveEnviada, codigoEnviado);
    } catch (fallo) {
      focoPendiente.current = { tipo: "alerta" };
      setError(mensajeDeError(fallo));
      setEnviando(false);
    }
  }

  return (
    <main className="silice-entrada">
      <section className="silice-entrada__secundaria">
        <div className="silice-entrada__cabecera">
          <h1 className="cds--type-heading-04">Tengo un código</h1>
          <p className="silice-entrada__texto cds--type-body-compact-01">
            Escriba su usuario, la contraseña que eligió al pedir la cuenta y el código aprobado por el administrador.
          </p>
        </div>

        <Form className="silice-entrada__formulario" onSubmit={(e) => void enviar(e)} noValidate>
          {error !== null && (
            <div ref={refAlerta} tabIndex={-1} className="silice-entrada__aviso-foco">
              <InlineNotification
                kind="error"
                role="alert"
                title="Error: no se pudo activar la cuenta"
                subtitle={error}
                lowContrast
                hideCloseButton
              />
            </div>
          )}
          <CampoTexto
            id={ID_CAMPO.login}
            labelText="Usuario"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            invalid={intentado && !login.trim()}
            invalidText="Escriba su usuario."
          />
          <PasswordInput
            id={ID_CAMPO.contrasena}
            labelText="Contraseña"
            autoComplete="current-password"
            value={contrasena}
            onChange={(e) => setContrasena(e.target.value)}
            invalid={intentado && !contrasena}
            invalidText="Escriba su contraseña."
          />
          <CampoTexto
            id={ID_CAMPO.codigo}
            labelText="Código"
            helperText="20 caracteres en 5 grupos de 4, como lo recibió en su correo"
            autoComplete="off"
            spellCheck={false}
            autoCapitalize="characters"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            invalid={intentado && !codigoSinSeparadores}
            invalidText="Escriba el código de 20 caracteres."
          />
          <div className="silice-entrada__acciones">
            <Button type="submit" disabled={enviando} className="silice-entrada__enviar">
              {enviando ? "Canjeando el código…" : "Canjear el código y entrar"}
            </Button>
            {alVolver && (
              <Button kind="ghost" size="sm" type="button" onClick={alVolver}>
                Volver
              </Button>
            )}
          </div>
        </Form>
      </section>
    </main>
  );
}
