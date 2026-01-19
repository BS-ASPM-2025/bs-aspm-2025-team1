PRAGMA foreign_keys = ON;

-- companies
CREATE TABLE IF NOT EXISTS companies (
    id            INTEGER PRIMARY KEY,
    company_name  TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);
CREATE INDEX IF NOT EXISTS ix_companies_company_name ON companies(company_name);

-- job_seekers (users)
CREATE TABLE IF NOT EXISTS job_seekers (
    id            INTEGER PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    first_name    TEXT,
    last_name     TEXT,
    password_hash TEXT NOT NULL,
    created_at    DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);
CREATE INDEX IF NOT EXISTS ix_job_seekers_email ON job_seekers(email);

-- jobs
CREATE TABLE IF NOT EXISTS jobs (
    id             INTEGER PRIMARY KEY,
    company_id     INTEGER NOT NULL,
    source_id_text TEXT,
    raw_text       TEXT NOT NULL,

    title          TEXT,
    required_skills TEXT,
    degree         TEXT,
    experience     TEXT,

    skills_weight      REAL NOT NULL DEFAULT 1.0,
    degree_weight      REAL NOT NULL DEFAULT 1.0,
    experience_weight  REAL NOT NULL DEFAULT 1.0,
    weight_general     REAL NOT NULL DEFAULT 1.0,

    is_open        INTEGER NOT NULL DEFAULT 1 CHECK (is_open IN (0, 1)),
    created_at     DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),

    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_jobs_company_id ON jobs(company_id);
CREATE INDEX IF NOT EXISTS ix_jobs_is_open ON jobs(is_open);

-- resumes
CREATE TABLE IF NOT EXISTS resumes (
    id             INTEGER PRIMARY KEY,
    job_seeker_id  INTEGER NOT NULL,
    source_id_text TEXT,
    raw_text       TEXT NOT NULL,
    created_at     DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),

    FOREIGN KEY (job_seeker_id) REFERENCES job_seekers(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_resumes_job_seeker_id ON resumes(job_seeker_id);

-- matches
CREATE TABLE IF NOT EXISTS matches (
    id         INTEGER PRIMARY KEY,
    resume_id  INTEGER NOT NULL,
    job_id     INTEGER NOT NULL,
    score      REAL NOT NULL,
    created_at DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),

    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id)    REFERENCES jobs(id) ON DELETE CASCADE,

    UNIQUE (resume_id, job_id)
);
CREATE INDEX IF NOT EXISTS ix_matches_resume_id ON matches(resume_id);
CREATE INDEX IF NOT EXISTS ix_matches_job_id ON matches(job_id);
