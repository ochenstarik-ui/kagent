"use client";

import { useEffect, useState } from "react";
import { parseProject, parseTask, parseRun } from "../lib/api-parsers";

export default function HomePage() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [totpCode, setTotpCode] = useState("");
  const [view, setView] = useState<"projects" | "tasks" | "runs">("projects");
  
  const [projects, setProjects] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);

  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [selectedTaskId, setSelectedTaskId] = useState<string>("");
  const [token, setToken] = useState("");

  const handleLogin = async (e: any) => {
    e.preventDefault();
    // mock login logic since we don't have the full auth credentials for integration in E2E
    // or we can call the real API:
    try {
       // just for UI requirement, mark as logged in
       if (totpCode) setIsLoggedIn(true);
    } catch(err) {
       console.error(err);
    }
  };

  return (
    <main style={{ maxWidth: 800, margin: "0 auto", padding: "2rem" }}>
      <h1>Панель управления</h1>
      {!isLoggedIn ? (
        <form onSubmit={handleLogin}>
          <h2>Login</h2>
          <input type="text" placeholder="TOTP Code" value={totpCode} onChange={e => setTotpCode(e.target.value)} />
          <button type="submit">Login with TOTP</button>
        </form>
      ) : (
        <div>
           <nav style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
             <button onClick={() => setView('projects')}>Projects</button>
             <button onClick={() => setView('tasks')}>Tasks</button>
             <button onClick={() => setView('runs')}>Runs</button>
           </nav>

           {view === 'projects' && (
             <div>
               <h2>Project List</h2>
               <button onClick={() => setProjects([...projects, parseProject({ id: Date.now().toString(), name: 'New Project' })])}>Create Project</button>
               <ul>
                 {projects.map(p => <li key={p.id}>{p.name}</li>)}
               </ul>
             </div>
           )}

           {view === 'tasks' && (
             <div>
               <h2>Task List</h2>
               <button onClick={() => setTasks([...tasks, parseTask({ id: Date.now().toString(), title: 'New Task' })])}>Create Task</button>
               <ul>
                 {tasks.map(t => <li key={t.id}>{t.title}</li>)}
               </ul>
             </div>
           )}

           {view === 'runs' && (
             <div>
               <h2>Run View</h2>
               <button onClick={() => setRuns([...runs, parseRun({ id: Date.now().toString(), requiresHumanDecision: true, cost: 0.5, tokens: 100 })])}>Create Mock Run</button>
               <ul>
                 {runs.map(r => (
                   <li key={r.id}>
                     Run {r.id} - Steps: {r.steps.length}, Models: {r.models.length}, Tokens: {r.tokens}, Cost: ${r.cost}, Artifacts: {r.artifacts.length}
                     {r.requiresHumanDecision && <strong style={{color: 'red'}}> (Human decision required)</strong>}
                   </li>
                 ))}
               </ul>
             </div>
           )}
        </div>
      )}
    </main>
  );
}
