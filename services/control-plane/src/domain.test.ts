import { describe, it, expect } from "vitest";
import { TASK_TRANSITIONS, type TaskStatus } from "./domain.js";

describe("TASK_TRANSITIONS", () => {
  it("allows all valid forward and cancellation transitions", () => {
    const allowed: Record<TaskStatus, TaskStatus[]> = {
      draft: ["planned", "cancelled"],
      planned: ["approved", "cancelled"],
      approved: ["in_progress", "cancelled"],
      in_progress: ["review", "cancelled"],
      review: ["in_progress", "done", "cancelled"],
      done: [],
      cancelled: [],
    };
    for (const [status, targets] of Object.entries(allowed) as [TaskStatus, TaskStatus[]][]) {
      for (const target of targets) {
        expect(TASK_TRANSITIONS[status]).toContain(target);
      }
    }
  });

  it("blocks invalid transitions", () => {
    expect(TASK_TRANSITIONS.draft).not.toContain("done");
    expect(TASK_TRANSITIONS.done).not.toContain("planned");
    expect(TASK_TRANSITIONS.cancelled).not.toContain("in_progress");
  });
});
