import globals from "globals";
import js from "@eslint/js";
import htmlPlugin from "eslint-plugin-html";

/** @type {import('eslint').Linter.FlatConfig[]} */
export default [
  {
    languageOptions: {
      globals: {
        ...globals.browser, // Include browser globals
        bootstrap: "readonly", // Declare Bootstrap as a global variable
      },
    },
    ...js.configs.recommended,
  },
  {
    files: ["**/*.html"],  // This should match any .html files in the project
    plugins: {
      html: htmlPlugin,
    },
    rules: {
      // Optionally define any specific rules for HTML files here
    },
  },
];