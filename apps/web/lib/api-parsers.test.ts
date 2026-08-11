import { describe, it, expect } from 'vitest';
import { parseProject, parseTask, parseRun } from './api-parsers';

describe('API Parsers', () => {
  it('parses project', () => {
    expect(parseProject({ id: '1', name: 'Test' })).toEqual({ id: '1', name: 'Test', status: 'unknown' });
  });
  it('parses task', () => {
    expect(parseTask({ id: '1', title: 'Task' })).toEqual({ id: '1', projectId: 'unknown', title: 'Task', status: 'unknown' });
  });
  it('parses run', () => {
    const run = parseRun({ id: '1', requiresHumanDecision: true });
    expect(run.requiresHumanDecision).toBe(true);
    expect(run.steps).toEqual([]);
  });
});
