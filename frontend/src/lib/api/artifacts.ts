import "server-only";

import { apiGet } from "./client";
import type { ArtifactDetail } from "./types";

export async function getArtifact(
  artifactId: string,
  includeMeta: boolean,
): Promise<ArtifactDetail> {
  const q = includeMeta ? "?include_meta=true" : "";
  return apiGet<ArtifactDetail>(`/v1/artifacts/${artifactId}${q}`);
}
