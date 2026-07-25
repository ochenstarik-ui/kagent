import type {
  CorrelationId,
  EventId,
  ProjectId,
  TaskId
} from "./ids.js";

export interface EventEnvelope<Type extends string, Payload> {
  readonly id: EventId;
  readonly type: Type;
  readonly schemaVersion: 1;
  readonly occurredAt: string;
  readonly correlationId: CorrelationId;
  readonly causationId?: EventId;
  readonly projectId?: ProjectId;
  readonly taskId?: TaskId;
  readonly payload: Payload;
}

export interface TaskStatusChangedPayload {
  readonly previousStatus: string;
  readonly nextStatus: string;
  readonly reason: string;
}

export type TaskStatusChangedEvent = EventEnvelope<
  "task.status_changed",
  TaskStatusChangedPayload
>;
