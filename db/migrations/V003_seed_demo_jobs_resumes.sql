PRAGMA foreign_keys = ON;

-- =========================================================
-- OPTIONAL CLEANUP (for demo repeatability)
-- Uncomment if you want a clean demo each time
-- =========================================================
-- DELETE FROM matches;
-- DELETE FROM jobs;
-- DELETE FROM resumes;

-- =========================================================
-- 1) DEMO JOB OFFERS (10 different roles)
-- =========================================================

-- ResMe (3 offers)
INSERT INTO jobs(
  company_id, title, degree, experience, required_skills, raw_text,
  skills_weight, degree_weight, experience_weight, weight_general, is_open
)
SELECT
  c.id,
  'Junior Python Backend (FastAPI)',
  'BSc Computer Science or equivalent',
  '0-2 years',
  'Python, FastAPI, SQL, PostgreSQL, SQLAlchemy, REST, Git',
  'Description:\nBuild REST APIs with FastAPI, work with PostgreSQL, write clean code, basic CI/CD and Docker is a plus.',
  2.0, 0.5, 1.0, 0.5, 1
FROM companies c WHERE c.company_name='ResMe';

INSERT INTO jobs(
  company_id, title, degree, experience, required_skills, raw_text,
  skills_weight, degree_weight, experience_weight, weight_general, is_open
)
SELECT
  c.id,
  'React Frontend Developer',
  'BSc or Bootcamp',
  '1-3 years',
  'React, TypeScript, JavaScript, HTML, CSS, REST, UI',
  'Description:\nDevelop web UI in React + TypeScript, integrate with REST API, focus on clean UX and responsive layout.',
  2.0, 0.3, 0.8, 0.6, 1
FROM companies c WHERE c.company_name='ResMe';

INSERT INTO jobs(
  company_id, title, degree, experience, required_skills, raw_text,
  skills_weight, degree_weight, experience_weight, weight_general, is_open
)
SELECT
  c.id,
  'QA Automation (Python)',
  'Any technical degree',
  '0-2 years',
  'Python, pytest, Selenium or Playwright, API testing, CI',
  'Description:\nWrite automated tests in Python (pytest), web/UI tests (Selenium/Playwright), API tests, integrate with CI pipelines.',
  2.0, 0.2, 0.8, 0.5, 1
FROM companies c WHERE c.company_name='ResMe';


-- Oracle (4 offers)
INSERT INTO jobs(
  company_id, title, degree, experience, required_skills, raw_text,
  skills_weight, degree_weight, experience_weight, weight_general, is_open
)
SELECT
  c.id,
  'Java Backend Engineer (Spring Boot)',
  'BSc Computer Science',
  '2-5 years',
  'Java, Spring Boot, Hibernate, JPA, SQL, PostgreSQL, Maven, REST',
  'Description:\nDevelop backend services in Java Spring Boot, use JPA/Hibernate, write integration tests, SQL and performance basics.',
  2.0, 0.6, 1.2, 0.4, 1
FROM companies c WHERE c.company_name='Oracle';

INSERT INTO jobs(
  company_id, title, degree, experience, required_skills, raw_text,
  skills_weight, degree_weight, experience_weight, weight_general, is_open
)
SELECT
  c.id,
  'DevOps Engineer (Cloud + Kubernetes)',
  'BSc or equivalent',
  '2-6 years',
  'Docker, Kubernetes, Linux, CI/CD, GitHub Actions, AWS, Terraform',
  'Description:\nMaintain CI/CD pipelines, containerize services with Docker, deploy to Kubernetes, cloud infrastructure on AWS, IaC with Terraform.',
  2.0, 0.3, 1.4, 0.6, 1
FROM companies c WHERE c.company_name='Oracle';

INSERT INTO jobs(
  company_id, title, degree, experience, required_skills, raw_text,
  skills_weight, degree_weight, experience_weight, weight_general, is_open
)
SELECT
  c.id,
  'Data Analyst (SQL + BI)',
  'BSc Statistics / CS / Engineering',
  '1-4 years',
  'SQL, Python, Excel, Power BI, Tableau, Data visualization',
  'Description:\nAnalyze product metrics, build dashboards (Power BI/Tableau), write SQL queries, Python for data cleaning and reporting.',
  2.0, 0.5, 0.9, 0.6, 1
FROM companies c WHERE c.company_name='Oracle';

INSERT INTO jobs(
  company_id, title, degree, experience, required_skills, raw_text,
  skills_weight, degree_weight, experience_weight, weight_general, is_open
)
SELECT
  c.id,
  'Android Developer (Kotlin)',
  'BSc or equivalent',
  '1-4 years',
  'Kotlin, Android, Jetpack Compose, REST, Room, Git',
  'Description:\nDevelop Android app in Kotlin, use Jetpack Compose, network via REST, local storage Room, clean architecture.',
  2.0, 0.3, 1.0, 0.5, 1
FROM companies c WHERE c.company_name='Oracle';


-- TechNova (3 offers)
INSERT INTO jobs(
  company_id, title, degree, experience, required_skills, raw_text,
  skills_weight, degree_weight, experience_weight, weight_general, is_open
)
SELECT
  c.id,
  'Machine Learning Engineer (NLP)',
  'MSc (preferred) or strong experience',
  '1-5 years',
  'Python, Machine Learning, PyTorch, Transformers, NLP, Data',
  'Description:\nTrain and evaluate ML models for NLP tasks, PyTorch, transformers (BERT-like), data preprocessing, experiment tracking.',
  2.0, 0.7, 1.1, 0.6, 1
FROM companies c WHERE c.company_name='TechNova';

INSERT INTO jobs(
  company_id, title, degree, experience, required_skills, raw_text,
  skills_weight, degree_weight, experience_weight, weight_general, is_open
)
SELECT
  c.id,
  'Cybersecurity Analyst (SOC)',
  'BSc IT / CS',
  '1-4 years',
  'SOC, SIEM, Incident response, OWASP, Network security, Linux',
  'Description:\nMonitor alerts in SIEM, incident response, basic threat hunting, OWASP awareness, logs analysis, Linux networking.',
  2.0, 0.4, 1.0, 0.5, 1
FROM companies c WHERE c.company_name='TechNova';

INSERT INTO jobs(
  company_id, title, degree, experience, required_skills, raw_text,
  skills_weight, degree_weight, experience_weight, weight_general, is_open
)
SELECT
  c.id,
  'Fullstack (React + FastAPI)',
  'BSc or equivalent',
  '1-5 years',
  'React, TypeScript, Python, FastAPI, SQL, PostgreSQL, Docker',
  'Description:\nBuild fullstack features: React UI + FastAPI backend, PostgreSQL, Docker for local dev, basic CI pipelines.',
  2.0, 0.3, 1.2, 0.7, 1
FROM companies c WHERE c.company_name='TechNova';


-- =========================================================
-- 2) DEMO RESUMES (100 resumes; 10 profiles)
--    One resume per job seeker. Titles are visible in UI as r.source_id_text
-- =========================================================

WITH js AS (
  SELECT
    id AS job_seeker_id,
    email,
    ROW_NUMBER() OVER (ORDER BY id) AS rn
  FROM job_seekers
  WHERE email LIKE 'jobseeker%@mail.com'
  LIMIT 100
)
INSERT INTO resumes(job_seeker_id, source_id_text, raw_text)
SELECT
  job_seeker_id,
  'CV - ' || email,
  CASE (rn % 10)

    WHEN 0 THEN
      'Profile: Python Backend Developer\n' ||
      'Skills: Python, FastAPI, Flask, REST, SQL, PostgreSQL, SQLAlchemy, Git, Docker, Linux\n' ||
      'Experience: 1-2 years backend development; API design; testing basics\n' ||
      'Education: BSc Computer Science\n' ||
      'Projects: resume/job matching service, CRUD APIs, authentication, DB migrations\n'

    WHEN 1 THEN
      'Profile: Java Backend Developer\n' ||
      'Skills: Java, Spring Boot, Hibernate, JPA, Maven, SQL, PostgreSQL, REST, JUnit, Testcontainers\n' ||
      'Experience: 2-4 years; building services; transactions; integration tests\n' ||
      'Education: BSc Software Engineering\n' ||
      'Projects: student/course management system, DAO layer, Spring Data JPA\n'

    WHEN 2 THEN
      'Profile: Data Analyst\n' ||
      'Skills: SQL, Python, Pandas, Excel, Power BI, Tableau, Data visualization, Statistics\n' ||
      'Experience: dashboards, KPI reporting, ETL basics, data cleaning\n' ||
      'Education: BSc Engineering\n' ||
      'Projects: sales dashboard, cohort analysis, churn reporting\n'

    WHEN 3 THEN
      'Profile: DevOps Engineer\n' ||
      'Skills: Docker, Kubernetes, Linux, CI/CD, GitHub Actions, GitLab CI, AWS, Terraform, Monitoring\n' ||
      'Experience: pipelines, deployments, containers, infra-as-code\n' ||
      'Education: BSc Computer Science\n' ||
      'Projects: deploy Flask/FastAPI app with Docker, K8s manifests, automated tests\n'

    WHEN 4 THEN
      'Profile: Frontend Developer\n' ||
      'Skills: React, TypeScript, JavaScript, HTML, CSS, REST, UI, responsive design\n' ||
      'Experience: building SPA, forms, validation, API integration\n' ||
      'Education: Bootcamp + projects\n' ||
      'Projects: job board UI, resume upload page, admin dashboard\n'

    WHEN 5 THEN
      'Profile: QA Automation Engineer\n' ||
      'Skills: Python, pytest, Selenium, Playwright, API testing, Postman, CI\n' ||
      'Experience: test plans, automation frameworks, regression suites\n' ||
      'Education: Any technical degree\n' ||
      'Projects: UI tests + API tests, CI pipeline integration\n'

    WHEN 6 THEN
      'Profile: Cybersecurity Analyst\n' ||
      'Skills: SOC, SIEM, Incident response, OWASP, Linux, Networking, logs analysis\n' ||
      'Experience: alert triage, basic threat hunting, incident tickets\n' ||
      'Education: BSc IT\n' ||
      'Projects: lab pentest report, log parsing, security monitoring basics\n'

    WHEN 7 THEN
      'Profile: Machine Learning Engineer\n' ||
      'Skills: Python, Machine Learning, PyTorch, Transformers, NLP, data preprocessing\n' ||
      'Experience: model training, evaluation, metrics, experiments\n' ||
      'Education: MSc (in progress) or strong ML background\n' ||
      'Projects: text classification, embedding similarity search, model fine-tuning\n'

    WHEN 8 THEN
      'Profile: Android Developer\n' ||
      'Skills: Kotlin, Android, Jetpack Compose, REST, Room, Git, clean architecture\n' ||
      'Experience: mobile UI, networking, local storage\n' ||
      'Education: BSc or equivalent\n' ||
      'Projects: Android app with Compose + REST API integration\n'

    ELSE
      'Profile: Fullstack Developer\n' ||
      'Skills: React, TypeScript, Python, FastAPI, SQL, PostgreSQL, Docker, REST\n' ||
      'Experience: fullstack features end-to-end, auth, DB migrations\n' ||
      'Education: BSc Software Engineering\n' ||
      'Projects: fullstack resume platform, matching engine, deploy via containers\n'
  END
FROM js;
