export function parseProject(data: any) {
  return {
    id: data.id || 'unknown',
    name: data.name || 'Unnamed',
    status: data.status || 'unknown'
  };
}

export function parseTask(data: any) {
  return {
    id: data.id || 'unknown',
    projectId: data.projectId || 'unknown',
    title: data.title || 'Untitled',
    status: data.status || 'unknown'
  };
}

export function parseRun(data: any) {
  return {
    id: data.id || 'unknown',
    steps: Array.isArray(data.steps) ? data.steps : [],
    models: Array.isArray(data.models) ? data.models : [],
    tokens: data.tokens || 0,
    cost: data.cost || 0,
    artifacts: Array.isArray(data.artifacts) ? data.artifacts : [],
    requiresHumanDecision: !!data.requiresHumanDecision
  };
}
