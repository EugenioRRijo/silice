import { Header, HeaderName, Theme } from "@carbon/react";

// Pantalla de esta tarea: cabecera y estado inicial. El formulario de entrada lo completa la tarea 2.4.
export function App() {
  return (
    <Theme theme="g10">
      <Header aria-label="Sílice">
        <HeaderName href="#" prefix="">
          Sílice
        </HeaderName>
      </Header>
      <main className="silice-entrada">
        <h1 className="cds--type-heading-03">Entrar</h1>
        <p className="silice-entrada__texto cds--type-body-compact-01">
          Entre con su cuenta de Sílice para ver y auditar el libro de presupuesto de la empresa.
        </p>
      </main>
    </Theme>
  );
}
