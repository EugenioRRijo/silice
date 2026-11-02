import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  {
    files: ["src/**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended, reactHooks.configs.flat.recommended],
    languageOptions: { ecmaVersion: 2023, globals: globals.browser },
    rules: {
      // Hallazgo 14 del recorrido (01-11-2026): estos componentes de Carbon traen textos por defecto en inglés; se usan
      // los de src/comun/carbonEs.tsx, que los dejan en español.
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "@carbon/react",
              importNames: ["TabList", "Search", "InlineNotification", "InlineLoading", "PasswordInput", "Pagination", "TableHeader"],
              message: "Importe este componente de src/comun/carbonEs.tsx: allí lleva sus textos en español.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["src/comun/carbonEs.tsx"],
    rules: { "no-restricted-imports": "off" },
  },
  {
    files: ["scripts/**/*.mjs", "*.config.{js,ts}"],
    extends: [js.configs.recommended],
    languageOptions: { ecmaVersion: 2023, globals: globals.node },
  },
);
