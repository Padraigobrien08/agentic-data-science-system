import { readFileSync } from "node:fs";

export type E2EFixture = {
  admin_email: string;
  admin_password: string;
  project_id: string;
  run_id: string;
  artifact_id: string;
};

let cachedFixture: E2EFixture | null = null;

function readRequiredString(
  payload: Record<string, unknown>,
  key: keyof E2EFixture,
): string {
  const value = payload[key];
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`E2E fixture key ${key} is missing or invalid.`);
  }
  return value;
}

export function getFixture(): E2EFixture {
  if (cachedFixture) {
    return cachedFixture;
  }

  const fixturePath = process.env.E2E_FIXTURE_PATH;
  if (!fixturePath) {
    throw new Error("E2E_FIXTURE_PATH must point to a seeded browser fixture JSON file.");
  }

  const raw = readFileSync(fixturePath, "utf-8");
  const parsed = JSON.parse(raw) as Record<string, unknown>;
  cachedFixture = {
    admin_email: readRequiredString(parsed, "admin_email"),
    admin_password: readRequiredString(parsed, "admin_password"),
    project_id: readRequiredString(parsed, "project_id"),
    run_id: readRequiredString(parsed, "run_id"),
    artifact_id: readRequiredString(parsed, "artifact_id"),
  };
  return cachedFixture;
}
