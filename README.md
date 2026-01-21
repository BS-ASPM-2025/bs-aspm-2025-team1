# ResuME 

**Resume-to-Job Matching Web System**

An AI-powered web application that matches job seeker resumes with job offers using TF-IDF and cosine similarity algorithms.

---

##  Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Docker](#docker)
- [Database Migrations](#database-migrations)
- [Testing](#testing)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Team](#team)
- [Links](#links)

---

##  Overview

**ResuME** is a web-based resume–job matching system that helps:

- **Job Seekers** upload and manage resumes, and get matched with relevant job offers
- **Company Recruiters** create job postings with requirements and find the best candidates automatically

The system calculates a **match score (0-100%)** using TF-IDF vectorization and cosine similarity, weighted across four categories:
- Skills
- Education/Degree
- Experience
- General job text

---

##  Features

### For Job Seekers
-  Secure authentication and session management
-  Upload resumes (PDF, Word, TXT)
-  View extracted resume text
-  Delete resumes
-  Personal data isolation

### For Company Recruiters
-  Company authentication
-  Create, edit, and delete job offers
-  Configure scoring weights per job
-  View ranked candidate matches
-  Recalculate matches on demand
-  Top-N results filtering

### System Features
-  Role-based access control
-  Database versioning with Alembic
-  Docker containerization
-  Automated testing (unit + integration)
-  CI/CD with GitHub Actions

---

##  Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Web Layer                            │
│  (FastAPI Controllers + Jinja2 Templates)                   │
├─────────────────────────────────────────────────────────────┤
│                      Security Layer                         │
│  (Session Management, Auth Guards)                          │
├─────────────────────────────────────────────────────────────┤
│                      Service Layer                          │
│  (Business Logic: JobService, ResumeService, MatchService)  │
├─────────────────────────────────────────────────────────────┤
│                     Repository Layer                        │
│  (Data Access: CompanyRepo, JobRepo, ResumeRepo, MatchRepo) │
├─────────────────────────────────────────────────────────────┤
│                       Model Layer                           │
│  (SQLAlchemy ORM: companies, jobs, job_seekers, resumes,    │
│   matches)                                                  │
├─────────────────────────────────────────────────────────────┤
│                        Database                             │
│  (SQLite + Alembic Migrations)                              │
└─────────────────────────────────────────────────────────────┘
```

---

##  Tech Stack

| Category | Technology |
|----------|------------|
| **Language** | Python 3.10+ |
| **Web Framework** | FastAPI (ASGI) |
| **Templating** | Jinja2 |
| **Database** | SQLite |
| **ORM** | SQLAlchemy |
| **Migrations** | Alembic |
| **ML/Matching** | Scikit-learn (TF-IDF + Cosine Similarity) |
| **Testing** | pytest |
| **CI/CD** | GitHub Actions |
| **Containerization** | Docker |

---

##  Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git

### Clone the Repository

```bash
git clone https://github.com/BS-ASPM-2025/bs-aspm-2025-team1.git
cd bs-aspm-2025-team1
```

### Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

##  Running the Application

### 1. Apply Database Migrations

```bash
alembic upgrade head
```

### 2. Start the Server

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Access the Application

Open your browser and navigate to:

- **Application:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs

---

##  Docker

### Build the Image

```bash
docker build -t resume-app .
```

### Run the Container

```bash
docker run -p 8000:8000 resume-app
```

### Using Docker Compose (if available)

```bash
docker-compose up --build
```

---

##  Database Migrations

The project uses **Alembic** for database schema versioning.

### Apply All Migrations

```bash
alembic upgrade head
```

### Create New Migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### View Migration History

```bash
alembic history
```

### Downgrade Migration

```bash
alembic downgrade -1
```

---

##  Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/test_match_service.py -v
```

### Test Categories

| Type | Description |
|------|-------------|
| **Controller Tests** | HTTP routing, responses, redirects |
| **Service Tests** | Business logic with real database |
| **Unit Tests** | Scoring algorithm validation |

---

##  API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Landing page |
| GET | `/jobseeker/login` | Job seeker login page |
| POST | `/auth/jobseeker` | Job seeker authentication |
| GET | `/company/login` | Company login page |
| POST | `/auth/company` | Company authentication |
| POST | `/logout` | Logout (both roles) |

### Job Seeker Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/resumes/manage` | Resume management page |
| GET | `/resumes/upload` | Upload resume page |
| POST | `/resumes/upload` | Submit resume upload |
| GET | `/resumes/{id}/text` | View extracted text |
| POST | `/resumes/{id}/delete` | Delete resume |

### Company Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/jobs/manage` | Job offers management |
| GET | `/post_job` | Create job offer page |
| POST | `/post_job` | Submit new job offer |
| GET | `/jobs/{id}/edit` | Edit job offer page |
| POST | `/jobs/{id}/edit` | Update job offer |
| POST | `/jobs/{id}/delete` | Delete job offer |
| GET | `/jobs/{id}/matches` | View candidate matches |
| POST | `/jobs/{id}/matches/recompute` | Recalculate matches |

---

##  Project Structure

```
bs-aspm-2025-team1/
├── src/
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── company.py
│   │   ├── job_seeker.py
│   │   ├── job.py
│   │   ├── resume.py
│   │   └── match.py
│   ├── repositories/        # Data access layer
│   │   ├── company_repository.py
│   │   ├── job_repository.py
│   │   ├── resume_repository.py
│   │   └── match_repository.py
│   ├── services/            # Business logic
│   │   ├── job_service.py
│   │   ├── resume_service.py
│   │   └── match_service.py
│   ├── security/            # Auth & session management
│   │   └── session.py
│   ├── tools/               # Utilities
│   │   ├── matching_scorer.py
│   │   └── resume_extractor.py
│   └── web/                 # Controllers
│       ├── auth_controller.py
│       ├── job_controller.py
│       ├── resume_controller.py
│       └── match_controller.py
├── templates/               # Jinja2 HTML templates
├── static/                  # CSS, JS, images
├── alembic/                 # Database migrations
│   └── versions/
├── tests/                   # Test files
│   ├── test_controllers/
│   ├── test_services/
│   └── test_tools/
├── app.py                   # Application entry point
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker configuration
├── alembic.ini              # Alembic configuration
└── README.md
```

---

##  Matching Algorithm

The matching score is calculated using:

1. **TF-IDF Vectorization** - Convert text to numerical vectors
2. **Cosine Similarity** - Measure similarity between resume and job
3. **Weighted Scoring** - Apply configurable weights:

```
Final Score = (skills_weight × skills_score) +
              (degree_weight × degree_score) +
              (experience_weight × experience_score) +
              (general_weight × general_score)
```

Score range: **0-100%**

---

##  Team

| Name | Role |
|------|------|
| **Yahalomit Vaizman** | UI Design, Testing |
| **Ayman Elsayeed** | Frontend, Resume Upload, CI/CD |
| **Elena Prokofyeva** | Database Migrations, Authentication |
| **Yurii Korolkov** | Matching Algorithm, Authorization, Backend |

**Supervisors:** Dr. Hadas Hasidim, Mr. Genadi Kogan

---

##  Links

- **GitHub Repository:** https://github.com/BS-ASPM-2025/bs-aspm-2025-team1
- **Jira Board:** https://sce-ac.atlassian.net/jira/software/projects/BSASPM25T1/boards/2196

---

##  License

This project was developed as part of the **Advanced Software Project Management** course at SCE College of Engineering.

---

##  Acknowledgments

- SCE College of Engineering
- Course staff for guidance and support
- OpenAI ChatGPT for AI-assisted development

---



