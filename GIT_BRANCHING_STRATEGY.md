# Git Branching Strategy - AI Ecosystem

**Date:** 2025-12-01
**Strategy:** Branch-based isolation (NOT folder-based)
**Goal:** Clean MVP deployment while preserving Phase 1 work

---

## 🎯 Branch Architecture

```
Repository: ai-ecosystem
├── main                    # Production (syncs with mvp when stable)
├── future-platform         # Phase 1 complete (13 agents, full system)
├── mvp                     # Deployable MVP (4 agents, 8 endpoints)
└── king-microservices      # Optional experimental microservices
```

---

## 📊 Branch Comparison

| Branch | Agents | Endpoints | Tables | Purpose | Deploy Target |
|--------|--------|-----------|--------|---------|---------------|
| **future-platform** | 13 | 34 | 13 | Full ecosystem | Development |
| **mvp** | 4 | 8 | 3 | Deployable subset | Cloud Run |
| **king-microservices** | 4 | 8 | 4 | Microservices experiment | Docker/K8s |
| **main** | Syncs with mvp | N/A | N/A | Production stable | Cloud Run |

---

## 🚀 Execution Plan

### Phase 1: Preserve Everything (5 minutes)

```bash
cd d:/ai-ecosystem

# 1. Commit all current work
git add .
git commit -m "Phase 1 complete: 13 agents, ministers, pipelines, telemetry"
git push origin main

# 2. Create future-platform branch (preserves ALL Phase 1 work)
git branch future-platform
git push -u origin future-platform

# Verify preservation
git log --oneline --all --graph
```

**Result:** All Phase 1 work safely preserved in `future-platform` branch.

---

### Phase 2: Create MVP Branch (10 minutes)

```bash
# 3. Create MVP branch from main
git checkout main
git checkout -b mvp

# 4. Remove non-MVP files (see MVP_FILES.txt for exact list)
# CRITICAL: Use git rm, not manual deletion
git rm -r backend/orchestrator/agents/audit_minister.py
git rm -r backend/orchestrator/agents/guardian_minister.py
git rm -r backend/orchestrator/agents/validator_minister.py
git rm -r backend/orchestrator/agents/spec_designer.py
git rm -r backend/orchestrator/agents/planner_agent.py
git rm -r backend/orchestrator/services/dna_mutator.py
git rm -r backend/orchestrator/services/mem0_tool.py
git rm -r backend/orchestrator/services/retrieval_service.py
git rm -r backend/orchestrator/services/user_preferences.py
git rm -r backend/orchestrator/services/telegram_bot.py
git rm -r backend/orchestrator/services/eval_runner.py
git rm -r backend/orchestrator/services/action_executor.py
# ... (see complete list in MVP_FILES.txt)

# 5. Create MVP-specific files
# (Copy from templates in CLAUDE_MVP.md)

# 6. Commit MVP branch
git add .
git commit -m "MVP: 4 agents, 8 endpoints, 3 tables - Cloud Run ready"
git push -u origin mvp
```

**Result:** Clean MVP branch ready for deployment.

---

### Phase 3: Deploy MVP (15 minutes)

```bash
# 7. Ensure on mvp branch
git checkout mvp

# 8. Setup Supabase Cloud
# - Go to supabase.com
# - Create project
# - Copy URL and service key
# - Run migration from mvp/supabase/migrations/

# 9. Deploy to Cloud Run (FROM mvp BRANCH)
gcloud run deploy ai-orchestrator \
  --source . \
  --branch mvp \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY,SUPABASE_URL=$SUPABASE_URL,SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY

# 10. Verify deployment
export SERVICE_URL=$(gcloud run services describe ai-orchestrator --region us-central1 --format 'value(status.url)')
curl $SERVICE_URL/health
curl $SERVICE_URL/meta/dependencies/health
```

**Result:** MVP deployed to Cloud Run from `mvp` branch.

---

### Phase 4: Optional - Merge MVP to Main (Later)

```bash
# When MVP proven stable in production
git checkout main
git merge mvp --no-ff -m "Merge MVP to main - production stable"
git push origin main

# Tag release
git tag -a v1.0.0-mvp -m "MVP Release: 4 agents, Cloud Run deployment"
git push origin v1.0.0-mvp
```

---

## 🔄 Workflow Patterns

### Adding Features from Future to MVP

```bash
# Scenario: Add guardian_minister to MVP

# 1. Checkout mvp branch
git checkout mvp

# 2. Cherry-pick specific file from future-platform
git checkout future-platform -- backend/orchestrator/agents/guardian_minister.py

# 3. Update agent_specs_mvp.json to include guardian_minister
# 4. Update agent_dependencies.py to include guardian_minister

# 5. Test locally
uvicorn backend.main:app --reload

# 6. Commit and deploy
git add .
git commit -m "Add guardian_minister to MVP"
git push origin mvp

# 7. Redeploy Cloud Run
gcloud run deploy ai-orchestrator --source . --branch mvp
```

### Developing New Features

```bash
# 1. Create feature branch from future-platform
git checkout future-platform
git checkout -b feature/new-agent

# 2. Develop and test
# ... make changes ...

# 3. Merge back to future-platform
git checkout future-platform
git merge feature/new-agent

# 4. Later: Port to MVP if needed
git checkout mvp
git cherry-pick <commit-hash>
```

### Syncing MVP ↔ Future

```bash
# Port MVP improvements to future-platform
git checkout future-platform
git cherry-pick <mvp-commit-hash>

# Port future features to MVP (selective)
git checkout mvp
git checkout future-platform -- path/to/file.py
```

---

## 📁 Branch Contents

### future-platform Branch

```
backend/orchestrator/
├── agents/
│   ├── agent_factory.py
│   ├── agent_runner.py (hybrid: LLM + ministers)
│   ├── agent_specs.json (13 agents)
│   ├── audit_minister.py
│   ├── guardian_minister.py
│   ├── validator_minister.py
│   ├── spec_designer.py
│   ├── planner_agent.py
│   └── video_planner.py
├── api/
│   ├── meta.py (34 endpoints)
│   └── tasks.py
├── services/
│   ├── agent_dependencies.py (13 agents)
│   ├── pipeline_executor.py (full)
│   ├── conversation_service.py (full)
│   ├── dna_mutator.py
│   ├── mem0_tool.py
│   ├── retrieval_service.py
│   ├── user_preferences.py
│   ├── telegram_bot.py
│   ├── eval_runner.py
│   ├── action_executor.py
│   ├── contracts.py
│   ├── eval_contracts.py
│   ├── gemini.py
│   └── supabase_client.py
└── main.py

supabase/migrations/
├── 20251127055045_init_ai_tables.sql
├── 20251127073300_meta_learning.sql
├── 20251127085303_telemetry_metrics.sql
├── 20251127120000_action_layer.sql
├── 20251127130000_user_preferences.sql
├── 20251127140000_conversation_feedback.sql
├── 20251127150000_service_registry.sql
├── 20251127160000_memory_telemetry.sql
└── 20251127170000_rag_telemetry.sql

tests/
├── test_ministers.py
├── test_creation_pipeline.py
├── test_spec_designer.py
└── ... (full test suite)
```

### mvp Branch

```
backend/
├── agents/
│   ├── __init__.py
│   ├── agent_factory.py (from future-platform)
│   ├── agent_runner.py (simplified: LLM-only)
│   └── agent_specs_mvp.json (4 agents)
├── api/
│   ├── __init__.py
│   ├── meta.py (8 endpoints)
│   └── tasks.py (3 endpoints)
├── services/
│   ├── __init__.py
│   ├── agent_dependencies.py (4 agents)
│   ├── pipeline_executor.py (basic)
│   ├── conversation_service.py (simplified)
│   ├── gemini.py (from future-platform)
│   └── supabase_client.py (from future-platform)
├── main.py (simplified)
├── requirements_mvp.txt
└── Dockerfile

supabase/migrations/
└── 001_mvp_tables.sql (3 tables)

.env.example
README_MVP.md
```

### king-microservices Branch (Optional)

```
gateway/
├── main.py
├── state_manager.py
└── Dockerfile

services/
├── code-writer/
│   ├── main.py
│   └── Dockerfile
├── code-reviewer/
├── video-planner/
└── script-writer/

supabase/migrations/
├── 001_agent_registry.sql
└── 002_agent_specs.sql

docker-compose.yml
```

---

## 🔐 Branch Protection Rules

### main Branch
- ✅ Require pull request reviews (1 approval)
- ✅ Require status checks to pass
- ✅ Enforce linear history
- ✅ Require signed commits
- ❌ Do not allow force push
- ❌ Do not allow deletions

### future-platform Branch
- ✅ Require pull request reviews (1 approval)
- ✅ Allow force push (development branch)
- ✅ Allow deletions (can reset if needed)

### mvp Branch
- ✅ Require pull request reviews (1 approval)
- ✅ Require status checks to pass
- ✅ No force push (production-ready)
- ✅ Deploy on push (GitHub Actions)

---

## 🤖 CI/CD Integration

### GitHub Actions - MVP Deploy

**File:** `.github/workflows/deploy-mvp.yml`

```yaml
name: Deploy MVP to Cloud Run

on:
  push:
    branches: [mvp]
  workflow_dispatch:

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  SERVICE_NAME: ai-orchestrator
  REGION: us-central1

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout mvp branch
        uses: actions/checkout@v3
        with:
          ref: mvp

      - name: Setup Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: ${{ env.PROJECT_ID }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ env.SERVICE_NAME }} \
            --source ./backend \
            --region ${{ env.REGION }} \
            --platform managed \
            --allow-unauthenticated \
            --set-env-vars GEMINI_API_KEY=${{ secrets.GEMINI_API_KEY }},SUPABASE_URL=${{ secrets.SUPABASE_URL }},SUPABASE_SERVICE_KEY=${{ secrets.SUPABASE_SERVICE_KEY }}

      - name: Verify Deployment
        run: |
          SERVICE_URL=$(gcloud run services describe ${{ env.SERVICE_NAME }} --region ${{ env.REGION }} --format 'value(status.url)')
          curl -f $SERVICE_URL/health || exit 1
          curl -f $SERVICE_URL/meta/dependencies/health || exit 1
```

---

## 📋 Branch Strategy Decision Tree

```
New Feature?
    │
    ├─ MVP-Critical? → Develop in mvp branch → Deploy
    │
    ├─ Advanced Feature? → Develop in future-platform → Test → Port to mvp later
    │
    └─ Experimental? → Create feature branch from future-platform → Merge when ready
```

---

## 🎓 Best Practices

### DO ✅
- Always commit to the correct branch
- Use descriptive commit messages
- Cherry-pick specific features between branches
- Tag releases (v1.0.0-mvp, v1.1.0-future, etc.)
- Keep mvp branch clean and deployable
- Document branch merges in PR descriptions
- Test before merging to main

### DON'T ❌
- Don't merge future-platform directly to mvp (too big)
- Don't force push to main or mvp
- Don't delete branches without backup
- Don't mix MVP and future work in same commit
- Don't deploy from future-platform to production

---

## 🆘 Troubleshooting

### "I'm on wrong branch"
```bash
git branch  # Check current branch
git checkout mvp  # Switch to correct branch
```

### "I committed to wrong branch"
```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Switch to correct branch
git checkout correct-branch

# Re-commit
git add .
git commit -m "Correct commit message"
```

### "MVP deploy failed"
```bash
# Check branch
git branch

# Ensure on mvp
git checkout mvp

# Verify files exist
ls backend/agents/agent_specs_mvp.json

# Check Cloud Run logs
gcloud run services logs read ai-orchestrator --region us-central1
```

### "Want to rollback MVP"
```bash
# Find previous working commit
git log --oneline

# Reset to that commit
git reset --hard <commit-hash>

# Force push (use with caution)
git push origin mvp --force

# Redeploy
gcloud run deploy ai-orchestrator --source . --branch mvp
```

---

## 📊 Git Graph Visualization

```
main ──────────────────────●─────────────────────> (production)
                           │ merge mvp
                           │
future-platform ───●───●───●───●───●───●──────────> (full ecosystem)
                   │   │   │   │
                   │   │   cherry-pick features
                   │   │   │   │
mvp ───────────────●───●───●───●───●───●──────────> (deployable)
                                       │
                                       deploy to Cloud Run
```

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] On mvp branch: `git branch`
- [ ] All changes committed: `git status`
- [ ] Tests pass locally: `pytest`
- [ ] Health endpoints work: `curl /health`
- [ ] Dependencies validated: `curl /meta/dependencies/health`

### Deployment
- [ ] Push to mvp branch: `git push origin mvp`
- [ ] GitHub Actions triggered (if configured)
- [ ] OR manual deploy: `gcloud run deploy`
- [ ] Service URL obtained
- [ ] Environment variables set

### Post-Deployment
- [ ] Health check: `curl $SERVICE_URL/health`
- [ ] Dependencies check: `curl $SERVICE_URL/meta/dependencies/health`
- [ ] Test conversation: `curl -X POST $SERVICE_URL/meta/converse`
- [ ] Monitor logs: `gcloud run services logs read`
- [ ] Check costs: Cloud Console
- [ ] Tag release: `git tag v1.0.0`

---

## 🎯 Success Criteria

### Branch Strategy Successful When:
- ✅ future-platform contains ALL Phase 1 work (untouched)
- ✅ mvp branch deploys cleanly to Cloud Run
- ✅ Can cherry-pick features from future → mvp
- ✅ Can develop new features in future-platform
- ✅ main branch syncs with stable mvp releases
- ✅ No Git history corruption
- ✅ All branches protected with proper rules

---

## 📝 Summary

**Branch Strategy Benefits:**
1. ✅ Preserves ALL Phase 1 work in `future-platform`
2. ✅ Clean MVP deployment from `mvp` branch
3. ✅ Can selectively port features between branches
4. ✅ Clear separation of concerns
5. ✅ Production stability in `main` branch
6. ✅ Experimental work in feature branches
7. ✅ Full Git history preserved
8. ✅ Easy rollback and recovery

**Next Steps:**
1. Execute Phase 1: Preserve (5 min)
2. Execute Phase 2: Create MVP branch (10 min)
3. Execute Phase 3: Deploy MVP (15 min)
4. Monitor production (48 hours)
5. Plan feature additions (ongoing)

---

**Branch strategy > Folder strategy**
**Git history > Manual copying**
**Clean separation > Monolithic merging**
