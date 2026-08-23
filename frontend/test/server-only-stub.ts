/**
 * `server-only` is resolved by the Next compiler, not by a package — it does not exist in
 * node_modules, so Vitest cannot resolve it. Aliased to this no-op so server modules can be
 * unit tested. The guard it provides is a build-time one and is unaffected.
 */
export {};
