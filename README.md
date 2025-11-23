# HR-AI-Tool Documentation

## 1. General Overview

### Project Description
**HR-AI-Tool** is an advanced recruitment platform designed to automate and enhance the process of matching candidates to job descriptions. Unlike traditional keyword matching, this system utilizes **Generative AI (LLMs)** and **Vector Search (RAG)** to understand the semantic meaning of resumes and job requirements, supporting both English and Hebrew.

### Core Capabilities
1.  **Smart Resume Ingestion:** Automatically detects, parses, and structures resume data (PDF/DOCX) from a watched directory. It handles complex layouts and Hebrew RTL (Right-to-Left) text issues.
2.  **Job Analysis:** Deconstructs job descriptions into structured criteria (skills, experience, tech stack) and searchable chunks.
3.  **AI Matching Engine:** Performs a deep comparison between candidates and jobs using a hybrid approach:
    *   **Vector Search:** Finds candidates conceptually related to the job.
    *   **LLM Judge:** A "virtual recruiter" that evaluates candidates based on specific criteria (Stability, Experience, Skills).
4.  **Recruiter Dashboard:** A visual interface to manage jobs, view parsed resumes, and analyze match scores with explanations.

### Technology Stack
*   **Backend:** Python, FastAPI, SQLAlchemy, Alembic.
*   **AI/ML:** OpenAI API, Vector Embeddings (pgvector), RAG (Retrieval-Augmented Generation).
*   **Frontend:** TypeScript, React, Vite.
*   **Infrastructure:** Docker, Docker Compose, PostgreSQL.

---

## 2. Backend Architecture

The backend is built with **FastAPI** and follows a service-oriented architecture. It is responsible for data processing, AI integration, and serving the API.

### Key Services

#### 1. Resume Ingestion Pipeline
*   **Watcher:** A background worker monitors a specific directory for new resume files.
*   **Parsing:** Converts PDF and DOCX files into raw text. It includes specialized logic to fix Hebrew text direction and extract text from tables.
*   **Extraction:** Uses a **Hybrid Approach**:
    *   *Deterministic:* Regex and rule-based extraction for contact info and known skills (high precision).
    *   *LLM-Boost:* Generative AI extraction for complex fields like work experience, education history, and summaries.

#### 2. Job Analysis Service
*   **Normalization:** Takes raw job descriptions and converts them into a structured JSON schema (requirements, tech stack, seniority).
*   **Chunking:** Breaks the job description into semantic "chunks" (e.g., "Responsibilities", "Tech Stack") to allow for precise vector matching against specific parts of a resume.

#### 3. Matching Engine (The "Brain")
*   **Retrieval (RAG):** Converts resumes and jobs into mathematical vectors (embeddings) to perform semantic searches in the database.
*   **Scoring System:**
    *   **Hard Filters:** Checks for mandatory skills.
    *   **Soft Scoring:** Calculates scores for "Employment Stability," "Title Match," and "Experience Duration."
    *   **LLM Judge:** An AI agent reviews the top candidates and provides a textual justification for why a candidate is a good or bad fit.

#### 4. Data Layer
*   Uses **PostgreSQL** with the `pgvector` extension to store both relational data (user info, structured resume fields) and vector embeddings for AI search.

---

## 3. Frontend Architecture

The frontend is a Single Page Application (SPA) built with **React**, **TypeScript**, and **Vite**. It focuses on providing a clean, responsive interface for HR professionals.

### Core Modules

#### 1. AI Search (Dashboard)
*   The central hub of the application.
*   Allows users to select a job and immediately see a ranked list of candidates.
*   Displays the "Match Score" and AI-generated reasoning for every candidate.
*   Includes a multi-step wizard for initiating new searches.

#### 2. Job Board
*   A management interface for creating and editing job descriptions.
*   Provides a view of the "Analyzed Job," showing how the AI interprets the requirements (e.g., separating "Must Have" vs. "Nice to Have" skills).

#### 3. Resume Repository
*   A searchable list of all ingested candidates.
*   **Resume Detail View:** A comprehensive view of a specific candidate, displaying:
    *   Parsed contact details.
    *   Standardized timeline of experience and education.
    *   Extracted skills and languages.
    *   Link to the original file.

### Technical Design
*   **Component Library:** Uses modular, reusable components (e.g., `JobCard`, `ResumeCard`, `ProgressSteps`) located in `src/components`.
*   **Styling:** Uses **CSS Modules** (e.g., `Dashboard.module.css`) to ensure styles are scoped locally to components and do not leak.
*   **State & API:** Manages data fetching via dedicated service layers (`services/jobs.ts`, `services/resumes.ts`) that communicate with the FastAPI backend.


