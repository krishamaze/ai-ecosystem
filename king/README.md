# KING MVP (Microservices Architecture)

This directory contains the experimental microservices implementation of the Kingdom Intelligence Nexus Gateway.

## Architecture

- **Gateway** (Port 8000): Thin orchestrator handling routing and state.
- **Code Writer** (Port 8001): Agent service for generating code.
- **Code Reviewer** (Port 8002): Agent service for reviewing code.
- **Video Planner** (Port 8003): Agent service for planning video content.
- **Script Writer** (Port 8004): Agent service for writing scripts.

## Prerequisites

1. **Supabase**: Apply the migration `supabase/migrations/20251202_king_registry.sql` to your Supabase project.
2. **Environment**: Create a `.env` file in this directory based on `.env.example`.

## Running the Stack

```bash
# Start all services
docker-compose up --build

# Verify Gateway
curl http://localhost:8000/health

# List Agents
curl http://localhost:8000/agents/list
```

## Testing an Agent

```bash
# Execute Code Writer via Gateway
curl -X POST http://localhost:8000/execute/code_writer \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "code_writer", "input_data": {"task": "Write a python fibonacci function", "language": "python"}}'
```

