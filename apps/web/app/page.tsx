"use client";

import { useEffect, useState } from "react";
import { parseProject, parseTask, parseRun } from "../lib/api-parsers";

export default function HomePage() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  
  const [view, setView] = useState<"projects" | "tasks" | "runs">("projects");
  
  const [projects, setProjects] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);

  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [selectedTaskId, setSelectedTaskId] = useState<string>("");
  const [token, setToken] = useState("");

  const handleRegister = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    setLoginError("");
    try {
      const res = await fetch("/api/control-plane/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Registration failed");
      setToken(data.tokens?.accessToken);
      setIsLoggedIn(true);
    } catch(err: any) {
      setLoginError(err.message);
    }
  };

  const handleLogin = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    setLoginError("");
    try {
      const res = await fetch("/api/control-plane/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Login failed");
      setToken(data.tokens?.accessToken);
      setIsLoggedIn(true);
    } catch(err: any) {
      setLoginError(err.message);
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await fetch("/api/control-plane/v1/projects?offset=0&limit=50", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Unavailable control-plane");
      const data = await res.json();
      setProjects(data.items || []);
    } catch (err: any) {
      setLoginError("Error: " + err.message);
    }
  };

  const handleCreateProject = async () => {
    try {
      const res = await fetch("/api/control-plane/v1/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}`, "x-actor-id": "test-actor" },
        body: JSON.stringify({ name: "Test Project " + Date.now(), description: "A test project" })
      });
      if (res.ok) fetchProjects();
    } catch (err) {
      console.error(err);
    }
  };

  const fetchTasks = async (projectId: string) => {
    try {
      const res = await fetch(`/api/control-plane/v1/tasks?projectId=${projectId}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTasks(data.items || []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateTask = async () => {
    if (!selectedProjectId) return;
    try {
      const res = await fetch("/api/control-plane/v1/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}`, "x-actor-id": "test-actor" },
        body: JSON.stringify({ projectId: selectedProjectId, title: "Test Task " + Date.now(), description: "Task desc" })
      });
      if (res.ok) fetchTasks(selectedProjectId);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateRun = async () => {
    if (!selectedProjectId || !selectedTaskId) return;
    try {
      const res = await fetch("/api/pipeline/pipelines/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: selectedProjectId, task_id: selectedTaskId })
      });
      if (res.ok) {
        const data = await res.json();
        setRuns([...runs, parseRun({
           id: data.task_id, 
           steps: data.steps || [],
           requiresHumanDecision: data.status === "human_required"
        })]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadRun = async (taskId: string) => {
    try {
      const res = await fetch(`/api/pipeline/${taskId}`);
      if (res.ok) {
        const data = await res.json();
        const existing = runs.find(r => r.id === taskId);
        if (existing) {
          setRuns(runs.map(r => r.id === taskId ? parseRun({
             id: data.task_id,
             steps: data.steps || [],
             requiresHumanDecision: data.status === "human_required"
          }) : r));
        } else {
          setRuns([...runs, parseRun({
             id: data.task_id,
             steps: data.steps || [],
             requiresHumanDecision: data.status === "human_required"
          })]);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (isLoggedIn) {
      fetchProjects();
    }
  }, [isLoggedIn]);

  return (
    <main style={{ maxWidth: 800, margin: "0 auto", padding: "2rem" }}>
      <h1>Панель управления</h1>
      {!isLoggedIn ? (
        <div>
          <h2>Login or Register</h2>
          {loginError && <p style={{color: 'red'}} className="error-message">{loginError}</p>}
          <form>
            <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
            <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
            <button onClick={handleLogin}>Login</button>
            <button onClick={handleRegister}>Register</button>
          </form>
        </div>
      ) : (
        <div>
           <nav style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
             <button onClick={() => setView('projects')}>Projects</button>
             <button onClick={() => setView('tasks')}>Tasks</button>
             <button onClick={() => setView('runs')}>Runs</button>
           </nav>
           
           {loginError && <p style={{color: 'red'}} className="error-message">{loginError}</p>}

           {view === 'projects' && (
             <div>
               <h2>Project List</h2>
               <button onClick={handleCreateProject}>Create Project</button>
               <ul>
                 {projects.map(p => (
                    <li key={p.id} className="project-item">
                      {p.name}
                      <button onClick={() => { setSelectedProjectId(p.id); setView('tasks'); fetchTasks(p.id); }}>Select</button>
                    </li>
                 ))}
               </ul>
             </div>
           )}

           {view === 'tasks' && (
             <div>
               <h2>Task List</h2>
               <p>Selected Project: {selectedProjectId}</p>
               <button onClick={handleCreateTask}>Create Task</button>
               <ul>
                 {tasks.map(t => (
                   <li key={t.id} className="task-item">
                     {t.title}
                     <button onClick={() => { setSelectedTaskId(t.id); setView('runs'); }}>Select for Run</button>
                   </li>
                 ))}
               </ul>
             </div>
           )}

           {view === 'runs' && (
             <div>
               <h2>Run View</h2>
               <button onClick={handleCreateRun}>Create Run</button>
               <ul>
                 {runs.map(r => (
                   <li key={r.id} className="run-item">
                     Run {r.id} - Steps: {r.steps?.length || 0}, Models: {r.models?.length || 0}, Tokens: {r.tokens || 0}, Cost: ${r.cost || 0}
                     <button onClick={() => loadRun(r.id)}>Load Detail</button>
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
