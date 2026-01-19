PRAGMA foreign_keys = ON;

-- =========================================================
-- PARAMETERS (edit only here)
-- =========================================================
DROP TABLE IF EXISTS seed_params;
CREATE TEMP TABLE seed_params(
    jobseeker_count INTEGER NOT NULL,
    password_hash   TEXT    NOT NULL
);

INSERT INTO seed_params(jobseeker_count, password_hash)
VALUES (
    100,
    '$2b$12$RDQb5kON0nWLbfss/pyoD.B7qpKeeHJIrtlQ6aIx7QMWZb1PdKVQG'
);

-- =========================================================
-- DEMO COMPANIES
-- =========================================================
INSERT OR IGNORE INTO companies(company_name, password_hash)
SELECT c.company_name, p.password_hash
FROM seed_params p
JOIN (
    SELECT 'ResMe'   AS company_name
    UNION ALL SELECT 'Oracle'
    UNION ALL SELECT 'TechNova'
) c;

-- =========================================================
-- DEMO JOB SEEKERS (generated via recursive CTE)
-- =========================================================
WITH RECURSIVE
first_names(idx, name) AS (
    VALUES
      (0,'Alex'), (1,'Dana'), (2,'Maya'), (3,'Noam'), (4,'Lior'),
      (5,'Yana'), (6,'Oleg'), (7,'Ilya'), (8,'Sasha'), (9,'Nina'),
      (10,'Tom'), (11,'Lena'), (12,'Omer'), (13,'Leah'), (14,'Ron'),
      (15,'Alina'), (16,'Max'), (17,'Tanya'), (18,'Eitan'), (19,'Sara')
),
last_names(idx, name) AS (
    VALUES
      (0,'Cohen'), (1,'Levi'), (2,'Mizrahi'), (3,'Friedman'), (4,'Kaplan'),
      (5,'Goldberg'), (6,'Katz'), (7,'Rosen'), (8,'Smirnov'), (9,'Ivanov'),
      (10,'Petrov'), (11,'Sokolov'), (12,'Mor'), (13,'Shapiro'), (14,'Bar'),
      (15,'Ben-David'), (16,'Novak'), (17,'Orlov'), (18,'Kogan'), (19,'Weiss')
),
fn_count(cnt) AS (SELECT COUNT(*) FROM first_names),
ln_count(cnt) AS (SELECT COUNT(*) FROM last_names),
seq(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1
    FROM seq
    WHERE n < (SELECT jobseeker_count FROM seed_params LIMIT 1)
)
INSERT OR IGNORE INTO job_seekers(email, first_name, last_name, password_hash)
SELECT
    'jobseeker' || seq.n || '@mail.com',
    fn.name,
    ln.name,
    (SELECT password_hash FROM seed_params LIMIT 1)
FROM seq
CROSS JOIN fn_count
CROSS JOIN ln_count
JOIN first_names fn ON fn.idx = ((seq.n - 1) % fn_count.cnt)
JOIN last_names  ln ON ln.idx = ((seq.n - 1) % ln_count.cnt);

-- cleanup temp params table
DROP TABLE IF EXISTS seed_params;
