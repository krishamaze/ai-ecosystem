-- Seed test entities for entity resolution testing
INSERT INTO entities (id, canonical_name, aliases, type)
VALUES
    (gen_random_uuid(), 'Project Omega', '["Omega", "omega", "project-omega"]', 'Organization'),
    (gen_random_uuid(), 'KING System', '["KING", "king", "kingdom"]', 'System')
ON CONFLICT (canonical_name) DO NOTHING;

