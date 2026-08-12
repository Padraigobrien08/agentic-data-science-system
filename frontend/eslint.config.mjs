import coreWebVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = [
  { ignores: [".next/**", "out/**", "coverage/**", "next-env.d.ts"] },
  ...coreWebVitals,
  {
    // New react-hooks v6 rules flag pre-existing patterns; kept as warnings
    // until the components are refactored.
    rules: {
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/immutability": "warn",
    },
  },
];

export default eslintConfig;
