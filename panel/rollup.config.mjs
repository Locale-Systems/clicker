import resolve from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";
import terser from "@rollup/plugin-terser";

const dev = process.env.ROLLUP_WATCH === "true";

// Home Assistant serves the build from the integration. It isn't committed:
// releases build it into clicker.zip.
export default {
  input: "src/clicker-panel.ts",
  output: {
    file: "../custom_components/clicker/frontend/clicker-panel.js",
    format: "es",
    inlineDynamicImports: true,
  },
  plugins: [
    resolve(),
    typescript({ tsconfig: "./tsconfig.json" }),
    !dev && terser({ format: { comments: false } }),
  ],
};
