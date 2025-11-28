import { useEffect, useState } from 'react'
import './App.css'

interface Task {
  id: string
  title: string
  status: string
  created_at: string
}

interface TaskDetail {
  task: Task
  context: { context_json: Record<string, unknown> } | null
  last_run: { output_json: { current_question?: string; confidence?: number; missing_fields?: string[] } } | null
}

function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null)
  const [newTitle, setNewTitle] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)

  const fetchTasks = () => {
    fetch('/api/tasks/')
      .then(res => res.json())
      .then(data => setTasks(data.tasks || []))
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  const createTask = async () => {
    if (!newTitle.trim()) return
    setLoading(true)
    await fetch('/api/tasks/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newTitle })
    })
    setNewTitle('')
    fetchTasks()
    setLoading(false)
  }

  const selectTask = async (taskId: string) => {
    const res = await fetch(`/api/tasks/${taskId}`)
    const data = await res.json()
    setSelectedTask(data)
  }

  const runPlanner = async () => {
    if (!selectedTask) return
    setLoading(true)
    const context = selectedTask.context?.context_json || {}
    await fetch(`/api/tasks/planner/${selectedTask.task.id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ known_context: context })
    })
    await selectTask(selectedTask.task.id)
    fetchTasks()
    setLoading(false)
  }

  const submitAnswer = async () => {
    if (!selectedTask || !answer.trim()) return
    setLoading(true)
    const context = selectedTask.context?.context_json || {}
    const missingField = selectedTask.last_run?.output_json?.missing_fields?.[0]
    if (missingField) {
      (context as Record<string, string>)[missingField] = answer
    }
    await fetch(`/api/tasks/planner/${selectedTask.task.id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ known_context: context })
    })
    setAnswer('')
    await selectTask(selectedTask.task.id)
    setLoading(false)
  }

  return (
    <div className="container">
      <h1>🧠 AI Ecosystem</h1>

      <div className="create-task">
        <input
          type="text"
          placeholder="New task title..."
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && createTask()}
        />
        <button onClick={createTask} disabled={loading}>Create Task</button>
      </div>

      <div className="layout">
        <div className="task-list">
          <h2>Tasks</h2>
          {tasks.map(t => (
            <div
              key={t.id}
              className={`task-item ${selectedTask?.task.id === t.id ? 'selected' : ''}`}
              onClick={() => selectTask(t.id)}
            >
              <strong>{t.title}</strong>
              <span className={`status ${t.status}`}>{t.status}</span>
            </div>
          ))}
        </div>

        {selectedTask && (
          <div className="task-detail">
            <h2>{selectedTask.task.title}</h2>
            <p className="task-id">ID: {selectedTask.task.id}</p>

            {selectedTask.last_run?.output_json && (
              <div className="planner-output">
                <div className="confidence">
                  Confidence: {((selectedTask.last_run.output_json.confidence || 0) * 100).toFixed(0)}%
                </div>
                <div className="question">
                  <strong>🤖 Agent asks:</strong>
                  <p>{selectedTask.last_run.output_json.current_question}</p>
                </div>
                <div className="answer-box">
                  <input
                    type="text"
                    placeholder="Your answer..."
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && submitAnswer()}
                  />
                  <button onClick={submitAnswer} disabled={loading}>Answer</button>
                </div>
              </div>
            )}

            {!selectedTask.last_run && (
              <button onClick={runPlanner} disabled={loading}>Start Planning</button>
            )}

            {selectedTask.context?.context_json && (
              <div className="context">
                <h3>Known Context</h3>
                <pre>{JSON.stringify(selectedTask.context.context_json, null, 2)}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default App
