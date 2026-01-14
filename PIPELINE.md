# CI/CD & Metrics Pipeline

This repository uses GitHub Actions to implement:
- **CI (Continuous Integration):** tests, lint, and Docker build verification.
- **Metrics Delivery:** publish the latest coverage report to GitHub Pages.
- **CD (Continuous Delivery):** release by Git tag → build & push Docker image → deploy to Azure Web App.

## High-level flow

| Workflow | Trigger | Purpose | Output |
|---|---|---|---|
| **CI** (`ci.yml`) | `push` to any branch, `pull_request`, manual | Quality gate: unit tests + lint + Docker build check | Artifacts: test logs/JUnit, lint report, coverage HTML (artifact) |
| **Metrics** (`metrics.yml`) | After successful CI on PR (`workflow_run`), manual | Publish **coverage HTML** to GitHub Pages | GitHub Pages site (latest report) |
| **CD** (`cd.yml`) | `push` of tag `v*`, manual | Release: build & push Docker image, then deploy to Azure | Docker Hub image (version + latest), Azure deployment |

---

<details>
  <summary><b>CI workflow (ci.yml)</b></summary>

### Jobs

- **tests**
  - Installs dependencies
  - Runs `pytest` with coverage
  - Uploads artifacts:
    - `test-artifacts-<run_number>` (logs/JUnit + coverage folder)
    - `coverage-html` (stable artifact name used by Metrics)

- **lint**
  - Runs `pylint` using `.pylintrc`
  - Uploads `lint-report-<run_number>` artifact

- **docker-build-check**
  - Builds Docker image locally (no push) to validate Dockerfile correctness
  - Runs only after `tests` and `lint` succeed

</details>

---

<details>
  <summary><b>Metrics workflow (metrics.yml)</b></summary>

### Modes

1) **Automatic (PR)**
- Trigger: `workflow_run` after **successful CI** executed for a Pull Request
- Downloads `coverage-html` artifact from the CI run
- Publishes it to GitHub Pages (latest report)

2) **Manual**
- Trigger: `workflow_dispatch`
- Input: `pages_ref` (branch/tag/SHA)
- Recomputes coverage for the selected ref and publishes to GitHub Pages

</details>

---

<details>
  <summary><b>CD workflow (cd.yml)</b></summary>

### Release trigger
- CD runs on Git tag push matching `v*` (e.g., `v1.4.0`).
- The tag value is used as the Docker image version.

### Jobs
- **build_and_push**
  - Builds and pushes Docker image to Docker Hub:
    - `<DOCKER_USERNAME>/aspm:<tag>`
    - `<DOCKER_USERNAME>/aspm:latest`

- **deploy_azure**
  - Deploys the version-tagged image to Azure Web App (`projectmanagement`)
  - Runs only if `build_and_push` succeeded

</details>

---

## Secrets / Configuration

Add secrets in **GitHub → Settings → Secrets and variables → Actions**.

| Secret name | Used in | What to put there |
|---|---|---|
| `DOCKER_USERNAME` | CD (`cd.yml`) | Docker Hub username / namespace |
| `DOCKER_PASSWORD` | CD (`cd.yml`) | Docker Hub access token (recommended) or password |
| `AZURE_CREDENTIALS` | CD (`cd.yml`) | Azure Service Principal credentials JSON for `azure/login` |

## GitHub Pages setup
- Repository Settings → Pages
- Source: **GitHub Actions**

## Tagging / Release policy
- Releases are created by pushing a tag `vX.Y.Z` on a commit in `main`.
- CI should be green before tagging.
- (Optional) With branch protection enabled, merges to `main` require successful CI checks.
