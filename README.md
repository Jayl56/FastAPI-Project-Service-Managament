# 🚀 Project Management Service
![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791)
![AWS S3](https://img.shields.io/badge/AWS-S3-orange)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED)
> A FastAPI backend for collaborative project management with secure authentication, document storage on Amazon S3, email-based workflows, and PostgreSQL persistence.

---

## ✨ Overview

This project provides a RESTful API that allows users to:

- 👤 Register and authenticate using JWT.
- 📁 Create and manage collaborative projects.
- 🤝 Invite other users to participate in projects.
- 📄 Upload, download and delete project documents.
- ☁️ Store documents securely in Amazon S3.
- 📧 Send invitation and password recovery emails.
- 🔒 Enforce role-based authorization for project resources.

### 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI |
| ORM | SQLModel |
| Database | PostgreSQL |
| Authentication | JWT |
| Password Hashing | Argon2 |
| Cloud Storage | Amazon S3 (Boto3) |
| Email | SMTP + Emails |
| Validation | Pydantic |
| Testing | Pytest |
| Containerization | Docker & Docker Compose |

---

# 📂 Repository Structure

```text
backend/
│
├── API/                # FastAPI endpoints
├── core/               # Security, dependencies & configuration
├── models_API/         # Pydantic request/response models
├── models_db/          # SQLModel ORM models
├── templates/          # HTML templates
├── utils/              # Email & S3 utilities
├── tests/              # Automated tests
│
├── main.py
├── backend_prestart.py
├── init_database.py
└── init_s3.py
```

---

# 🏗️ Application Architecture

```text
        Client
          │
          ▼
     FastAPI Endpoints
          │
          ▼
 Dependency Injection
(Auth • Permissions • DB)
          │
          ▼
   Business Logic / CRUD
          │
     ┌────┴────┐
     ▼         ▼
PostgreSQL   Amazon S3
```

---

# 🔐 Authentication & Authorization

Authentication uses **JWT Access Tokens** sent through:

```text
Authorization: Bearer <token>
```

Passwords are hashed using **Argon2**.

## 👥 Permission Model

```text
Owner
 │
 ├── View Project
 ├── Upload/Delete Documents
 ├── Update Project (details:name,description)
 ├── Delete Project
 └── Manage Members

Participant
 │
 ├── View Project
 ├── Upload Documents
 └── Delete Documents
```

Project ownership is resolved through the **ProjectMembers** association table instead of storing an explicit owner field in the project.

---

# 🗄️ Database Design

The application consists of four main entities.

```text
User
 │
 ├──────────────┐
 ▼              │
ProjectMembers  │
 │              │
 ▼              │
Project─────────┘
 │
 ▼
Document
```

### Relationships

- 👤 One user → Many projects
- 📁 One project → Many users
- 📄 One project → Many documents
- 📄 One document → One project

Document metadata is stored in PostgreSQL, while file contents remain in Amazon S3.

---

# ☁️ Amazon S3 Integration

Documents are stored externally in **Amazon S3**.

### Upload Flow

```text
Client
   │
   ▼
Upload File
   │
   ▼
Amazon S3
   │
   ▼
Metadata → PostgreSQL
```

### Download Flow

Authorized users receive **Pre-Signed URLs**, allowing secure direct downloads from S3.

Deleting a document removes both:

- ☁️ The S3 object
- 🗄️ Its database record

---

# 📧 Email Workflows

The application uses configurable SMTP settings to send HTML emails.

Supported workflows:

- 🔑 Password Recovery
- 🤝 Project Invitations

Both rely on **signed JWT tokens with configurable expiration times**.

```text
Generate Token
      │
      ▼
Send Email
      │
      ▼
HTML Form
      │
      ▼
Validate Token
      │
      ▼
Execute Action
```

---

# ⚙️ Configuration

Application settings are managed through **Pydantic Settings**.

Configuration includes:

- 🗄️ PostgreSQL
- ☁️ Amazon S3
- 🔑 JWT
- 📧 SMTP
- ⚙️ Application settings

---

# ▶️ Running the Project

## Local Development

```bash
uvicorn backend.main:app --reload
```

Initialization scripts:

- `backend/backend_prestart.py`
- `backend/init_database.py`
- `backend/init_s3.py`

---

## Docker

Build and start the complete environment:

```bash
docker compose up --build
```

The Docker Compose configuration:

- Builds the FastAPI image.
- Starts PostgreSQL.
- Runs the API container.

---

# 🧪 Running the Tests

```bash
pytest backend/tests -vv -s
```

The startup process supports:

- ✅ Blocking tests (CI)
- ⚡ Non-blocking tests (Development)

using the `RUN_TESTS` environment variable.

---

# 🧭 Code Navigation

| Review | Location |
|---------|----------|
| 🔐 Authentication | `backend/API/auth.py` |
| 👤 Users | `backend/API/users.py` |
| 📁 Projects | `backend/API/projects.py` |
| 📄 Documents | `backend/API/documents.py` |
| 🛡️ Security | `backend/core/security.py` |
| 🔗 Dependencies | `backend/core/dependencies.py` |
| 🗄️ ORM Models | `backend/models_db/` |
| 📦 API Schemas | `backend/models_API/` |
| ☁️ Amazon S3 | `backend/utils/s3_utils.py` |
| 📧 Email | `backend/utils/email_utils.py` |
| 🧪 Tests | `backend/tests/` |

---

<div align="center">

Built with effort 🏋️ and passion 🔥 using FastAPI, SQLModel and Amazon S3.

</div>