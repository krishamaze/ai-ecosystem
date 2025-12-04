# Supabase Migration Rules

## Golden Rule
**NEVER apply SQL directly to remote. ALL changes go through local migration files.**

## Naming Convention
```
<YYYYMMDDHHMMSS>_<descriptive_name>.sql
```
- Timestamp: 14 digits (to the second)
- Always include `_name` suffix — bare timestamps are SKIPPED by CLI
- Use lowercase snake_case for names

**Examples:**
- ✅ `20251203110000_seed_entities.sql`
- ❌ `20251203.sql` (no name suffix — will be skipped)
- ❌ `20251203_seed.sql` (timestamp too short)

## Workflow
```powershell
# 1. Create migration
supabase migration new <name>

# 2. Edit the generated file in supabase/migrations/

# 3. Verify sync
supabase migration list

# 4. Push
supabase db push
```

## If Sync Breaks
```powershell
# Check state
supabase migration list

# Revert orphan remote entries
supabase migration repair --status reverted <timestamp>

# Push with out-of-order migrations
supabase db push --include-all
```

## Table Defaults
Always use explicit defaults for UUID primary keys:
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

When seeding, explicitly call the function if default fails:
```sql
INSERT INTO table (id, ...) VALUES (gen_random_uuid(), ...)
```

## Never Do
- Run SQL in Supabase Dashboard SQL Editor for schema changes
- Rename migration files after they've been pushed
- Delete migration files that have been applied
- Use short timestamps (must be 14 digits)

