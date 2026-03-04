-- Retire approved duplicate skill IDs while preserving backward compatibility
-- through runtime alias resolution in the app layer.

DO $$
BEGIN
  IF to_regclass('public.skill_usage_log') IS NOT NULL THEN
    WITH alias_map(alias_name, canonical_name) AS (
      VALUES
        ('brand-guidelines-community', 'brand-guidelines-anthropic'),
        ('cc-skill-continuous-learning', 'cc-skill-strategic-compact'),
        ('docx', 'docx-official'),
        ('internal-comms-community', 'internal-comms-anthropic'),
        ('pdf', 'pdf-official'),
        ('xlsx', 'xlsx-official')
    )
    UPDATE skill_usage_log AS log
    SET skill_id = alias_map.canonical_name
    FROM alias_map
    WHERE log.skill_id = alias_map.alias_name;
  END IF;
END $$;

WITH alias_map(alias_name, canonical_name) AS (
  VALUES
    ('brand-guidelines-community', 'brand-guidelines-anthropic'),
    ('cc-skill-continuous-learning', 'cc-skill-strategic-compact'),
    ('docx', 'docx-official'),
    ('internal-comms-community', 'internal-comms-anthropic'),
    ('pdf', 'pdf-official'),
    ('xlsx', 'xlsx-official')
)
DELETE FROM skills AS s
USING alias_map
WHERE s.name = alias_map.alias_name
  AND EXISTS (
    SELECT 1
    FROM skills AS canonical
    WHERE canonical.name = alias_map.canonical_name
  );
