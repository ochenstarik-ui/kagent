import type { ArtifactId, ProjectId, TaskId } from "./ids.js";

export interface ArtifactDescriptor {
  readonly id: ArtifactId;
  readonly projectId: ProjectId;
  readonly taskId?: TaskId;
  readonly kind: string;
  readonly mediaType: string;
  readonly byteLength: number;
  readonly sha256: string;
  readonly objectKey: string;
  readonly createdAt: string;
}

export function isSha256(value: string): boolean {
  return /^[a-f0-9]{64}$/u.test(value);
}
