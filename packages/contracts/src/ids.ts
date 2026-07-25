export type Brand<Value, Name extends string> = Value & {
  readonly __brand: Name;
};

export type ProjectId = Brand<string, "ProjectId">;
export type TaskId = Brand<string, "TaskId">;
export type EventId = Brand<string, "EventId">;
export type ArtifactId = Brand<string, "ArtifactId">;
export type CorrelationId = Brand<string, "CorrelationId">;

export function asProjectId(value: string): ProjectId {
  return validateId(value, "ProjectId") as ProjectId;
}

export function asTaskId(value: string): TaskId {
  return validateId(value, "TaskId") as TaskId;
}

function validateId(value: string, kind: string): string {
  const trimmed = value.trim();
  if (trimmed.length < 8 || trimmed.length > 128) {
    throw new Error(`${kind} must contain between 8 and 128 characters`);
  }
  return trimmed;
}
