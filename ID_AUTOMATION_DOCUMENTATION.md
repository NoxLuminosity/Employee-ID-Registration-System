# ID Automation Documentation V1.4

> **Project Title:** ID Automation (Permanent ID)
> **Version:** V1.4
> **Last Updated:** 02-16-26
> **Release Date:** 02-18-26
> **Development Team:** Miguel L. Manuel, Kzyrell A. Dela Paz

---

## Table of Contents

1. [Overview](#1-overview)
2. [Purpose and Goals](#2-purpose-and-goals)
3. [Success Metrics](#3-success-metrics)
4. [Project Timeline](#4-project-timeline)
5. [System Architecture](#5-system-architecture)
6. [Process Flow and Workflow Description](#6-process-flow-and-workflow-description)
7. [Deployment and Installation Instructions](#7-deployment-and-installation-instructions)
8. [Server Requirements](#8-server-requirements)
9. [Tech Stacks](#9-tech-stacks)
10. [Database Structure](#10-database-structure)
11. [Features and Functionalities](#11-features-and-functionalities)
12. [User Roles and Access](#12-user-roles-and-access)
13. [Security and Privacy](#13-security-and-privacy)
14. [Third-Party Integrations](#14-third-party-integrations)
15. [Troubleshooting](#15-troubleshooting)
16. [Development Cost](#16-development-cost)
17. [Stakeholders](#17-stakeholders)
18. [User Feedback](#18-user-feedback)
19. [Frequently Asked Questions](#19-frequently-asked-questions)
20. [In Scope](#20-in-scope)
21. [Out of Scope](#21-out-of-scope)
22. [Discrepancies and Suggestions](#22-discrepancies-and-suggestions)

---

## 1. Overview

The Employee ID Registration System is a web-based, end-to-end ID card automation platform that streamlines the complete lifecycle of employee ID processing. It replaces the traditional, manual approach to ID creation with a structured digital workflow where employees submit their information through a self-service portal, the system standardizes and enhances photos using AI, and HR manages review, approval, and print-ready outputs through a dedicated dashboard. The process ends with automatic routing of completed ID files to the correct Point of Contact (POC) branch for printing and distribution.

The current process being improved is the manual coordination of ID requests, which typically involves back-and-forth communication, inconsistent photo quality, manual validation of employee details, and time-consuming compilation of print materials. These steps often result in long turnaround times, repeated rework, and routing mistakes when IDs are sent to the wrong branch or printing contact.

The system is composed of two main experiences:

1. **Employee Portal** — Authenticated employees log in via Lark SSO, upload or generate a professional headshot using BytePlus Seedream, apply automatic background removal through Cloudinary AI, provide their details with a live ID preview, and submit a digital signature via a built-in canvas tool.

2. **HR Dashboard** — Provides a controlled environment for People Support to review submissions, validate details, preview ID cards, generate print-ready PDFs, perform bulk approvals, and trigger delivery steps. Once an ID is finalized, the system supports automated POC routing by calculating the nearest POC branch using branch coordinates and haversine distance logic. HR can then send the completed PDF to the assigned POC through Lark messaging with the required file attachments.

Throughout the process, the system also supports enterprise-level visibility through integration with Lark Bitable for real-time syncing and status tracking.

**Target User Groups:**
- **Employees** who need an easy and consistent way to request their IDs.
- **HR (People Support)** who are responsible for validating, approving, generating, and distributing ID cards at scale.

---

## 2. Purpose and Goals

The Employee ID Registration System exists to standardize and automate the employee ID issuance process so that ID requests can be submitted, validated, and completed through one controlled workflow. The system was built to reduce the manual effort involved in collecting employee details, checking photo compliance, producing print-ready ID outputs, and coordinating distribution to the correct branch or point of contact.

The project addresses recurring operational pain points:
- Incomplete or inconsistent employee data
- Repeated rework due to non-compliant photos
- Reliance on manual compilation of ID files
- Routing mistakes when output files are sent to the wrong recipient

### Primary Goals

1. **Reduce manual ID processing** by digitizing employee submission, validation, and HR review into a single end-to-end workflow.
2. **Standardize and improve ID photo quality** through AI headshot generation and background removal to produce consistent, professional outputs.
3. **Increase HR review speed and control** using a dedicated dashboard with searchable records, preview galleries, and bulk actions for faster decision-making.
4. **Minimize routing and delivery errors** by automatically determining the correct POC and enabling centralized sending/distribution of print-ready ID files to POCs (including bulk sending).
5. **Improve visibility and accountability** by maintaining real-time status progression (e.g., `Reviewing → Rendered → Approved → Sent to POC → Completed`) and ensuring every request is traceable from submission to turnover.

---

## 3. Success Metrics

The success of the system is evaluated based on how effectively it improves reliability, efficiency, data accuracy, and overall user experience compared to the previous process.

| Metric | Description | Target |
|--------|-------------|--------|
| Service Uptime (Core App) | Availability of the web app and backend API routes | ≥ 99.5% monthly uptime |
| API Error Rate (5xx) | Frequency of server-side failures during normal use | ≤ 1% of total requests |
| Submission Reliability | Whether employee submissions consistently save records and required assets | ≥ 98% submissions complete end-to-end |
| Session/Auth Reliability (HR) | HR login/session stability | ≥ 99% successful HR logins for valid users |
| Recovery Expectation | Ability to restore service after deployment errors | RTO ≤ 30 minutes |
| Employee Form Page Load | Time for the employee form UI to become usable | ≤ 3 seconds on average connections |
| Submission Processing Time (Non-AI) | Time from "Submit" to confirmation | ≤ 5 seconds average |
| AI Headshot Generation Time | End-to-end time for AI-enhanced headshot | ≤ 60 seconds average, ≤ 120 seconds p95 |
| Background Removal Time | Time to produce a background-removed photo | ≤ 20 seconds average, ≤ 45 seconds p95 |
| HR Dashboard Load | Speed of loading the employee list | ≤ 2 seconds average |
| HR Actions Response Time | Speed of HR operations (approve, reject, delete) | ≤ 3 seconds average per action |
| Batch Export Readiness | Ability to generate/export ID outputs reliably | ≥ 95% success rate |
| PDF Upload Success (Cloudinary) | Reliability of storing generated ID PDFs | ≥ 98% successful uploads |
| Data Accuracy | Correctness of stored employee data fields | ≤ 1% of records require HR correction |
| ID Number Uniqueness | No duplicate ID numbers in the database | 0 duplicates allowed |
| Barcode Correctness | Generated barcode scans successfully | ≥ 99% scan success rate |
| Image Output Quality | AI headshots accepted without reprocessing | ≥ 85% acceptance on first output |
| Photo Compliance | Adherence to photo rules (closed mouth, centered face) | ≥ 90% of submissions meet requirements |
| Integration Reliability (Lark/Sheets) | Sync success rate to external tracking systems | ≥ 95% sync success |
| Adoption (Employee Usage) | Employees using the system vs manual channels | ≥ 90% of ID requests through the system |
| Completion Rate | Percentage of employees who finish submission | ≥ 85% completion rate |
| HR Throughput Improvement | Speed/volume HR can process vs manual workflow | Reduce HR handling time by ≥ 50% per ID |
| User Satisfaction (HR) | HR perception of usability and efficiency | ≥ 4.2/5 average satisfaction |
| User Satisfaction (Employees) | Employee experience on form clarity and ease | ≥ 4.0/5 average satisfaction |

---

## 4. Project Timeline

The project was executed over a four-week delivery timeline following Scrum-style sprint cycles.

### Sprint 1 — Discovery, Research, Planning, and Process Proposal (Week 1: Jan 14–16)

**Objectives:**
- Establish understanding of the current Employee ID request process
- Define the proposed automated workflow
- Produce proposal artifacts for HR review
- Begin early exploration of AI-based image standardization feasibility

**Key Deliverables:**
1. Proposed end-to-end workflow (employee submission → HR review)
2. Process flow diagram and user journey outline
3. Initial user stories (employee-side and HR-side)
4. Draft HR review/approval criteria
5. Presentation-ready proposal pack for HR review
6. Early findings on AI image enhancement feasibility

### Sprint 2 — System Build, Integrations, and Platform Consolidation (Week 2: Jan 19–23)

**Objectives:**
- Build the working Employee Portal and begin HR Portal implementation
- Integrate core processing services (submission handling, AI headshot generation, background removal)
- Establish deployment readiness (local + cloud)
- Explore and validate integration options for data storage and syncing

**Key Deliverables:**
1. Employee Portal (working submission experience)
2. Initial HR Portal structure and dashboard foundation
3. Cloudinary integration for image storage
4. BytePlus AI headshot generation integrated into the workflow
5. Background removal workflow explored/validated
6. Deployed test environment on Vercel
7. Landing page + HR page integration under one platform
8. Initial ID template work and database adjustments

### Sprint 3 — HR Demo Iterations, Reviewer Workflow, and Stabilization (Week 3: Jan 26–30)

**Objectives:**
- Stabilize HR-side reviewer workflow and session handling
- Apply feedback-based improvements for demo readiness
- Fix HR dashboard issues

**Key Deliverables:**
1. Improved demo-ready build based on HR-facing review requirements
2. HR reviewer-side workflow implemented
3. HR session handling strengthened
4. HR dashboard fixes applied for improved stability and usability

### Sprint 4 — Access Readiness, Operational Dependencies, and Dry Run Preparation (Week 4: Feb 2–6)

**Objectives:**
- Finalize access requirements for HR and system operation
- Resolve operational dependencies tied to storage and platform access
- Prepare the system for demo dry run

**Key Deliverables:**
1. HR dashboard access requirements completed and documented
2. Drive/system access readiness confirmed
3. Dry run readiness supported by resolved access dependencies

### Sprint 5 — Deployment Readiness, Final QA, and Turnover Preparation (Week 5: Feb 9–13)

**Objectives:**
- Finalize remaining corrections identified during dry run feedback
- Validate outputs and access controls under real HR usage conditions
- Ensure documentation reflects updated cost and scaling assumptions
- Prepare for deployment readiness and turnover

**Key Deliverables:**
1. Updated PDF generation rules with corrected expiration behavior
2. Finalized branch-level POC mapping (Bulacan/Malolos, Laguna/Calamba, Pampanga/San Fernando)
3. Enhanced notification mechanism with attachments
4. Revised cost documentation (3,000–3,500 employees)
5. Corrected desktop watermark behavior for screenshot restriction
6. Completed HR-led dry run results

---

## 5. System Architecture

The Employee ID Registration System follows a FastAPI-based web application architecture deployed on Vercel serverless infrastructure.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     VERCEL (Serverless)                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              FastAPI Application (Python)              │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │  │
│  │  │  Auth    │ │ Employee │ │    HR    │ │ Security │ │  │
│  │  │  Router  │ │  Router  │ │  Router  │ │  Router  │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │  │
│  │  ┌──────────────────────────────────────────────────┐ │  │
│  │  │               Service Layer                      │ │  │
│  │  │ Cloudinary │ Seedream │ Lark │ Sheets │ Barcode  │ │  │
│  │  │ BG Removal │ POC Routing                         │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────┐  ┌──────────────┐  ┌───────────────────┐    │
│  │  Jinja2   │  │ Static Files │  │ Security Middleware│    │
│  │ Templates │  │  (JS/CSS)    │  │   (CSP, Headers)  │    │
│  └───────────┘  └──────────────┘  └───────────────────┘    │
└─────────────────────────────────────────────────────────────┘
            │             │              │
            ▼             ▼              ▼
    ┌──────────────┐ ┌──────────┐ ┌────────────┐
    │   Supabase   │ │Cloudinary│ │  BytePlus  │
    │ (PostgreSQL) │ │ (Images) │ │ (Seedream) │
    └──────────────┘ └──────────┘ └────────────┘
            │
            ▼
    ┌──────────────┐ ┌──────────┐ ┌────────────┐
    │  Lark Suite  │ │  Google  │ │BarcodeAPI  │
    │ (SSO/Bitable/│ │  Sheets  │ │   .org     │
    │  Messaging)  │ │(Optional)│ │            │
    └──────────────┘ └──────────┘ └────────────┘
```

### Application Entry Point

- **Vercel**: All requests are routed via `vercel.json` to `api/index.py`, which imports the FastAPI `app` from `app/main.py`.
- **Local Development**: Run directly with `uvicorn app.main:app --reload`.

### Router Architecture

The application registers four routers in `app/main.py`:

| Router | Prefix | Purpose |
|--------|--------|---------|
| `auth` | `/auth` | Lark SSO login/logout, employee session management |
| `employee` | `/` | Employee form submission, headshot generation, background removal, barcode API |
| `hr` | `/hr` | HR dashboard, gallery, employee management, PDF upload, POC routing |
| `security` | `/api/security` | Screenshot/recording attempt logging and event retrieval |

### Middleware

- **SecurityHeadersMiddleware** (`app/main.py`): Adds Content Security Policy (CSP), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, HSTS, and `Referrer-Policy` headers to all responses.

---

## 6. Process Flow and Workflow Description

### High-Level Flow

```
Employee Submits ID Request
        │
        ▼
System Validates Data + Processes Photo
  (AI Enhancement → Background Removal)
        │
        ▼
Digital ID Generated (Template-Based)
        │
        ▼
HR Reviews & Approves
        │
        ▼
ID Output Routed to POC for Printing
```

### Detailed Flow

1. **Employee Access & Submission**: An employee accesses the ID Registration platform and authenticates via Lark SSO (OAuth 2.0 with PKCE). They submit required information including personal details, role/assignment information, a photo, and a digital signature.

2. **Validation**: The system performs validation checks to confirm completeness and required formatting (both client-side and server-side via `app/validators.py`).

3. **Data Storage**: The submission is saved in the Supabase database as the primary record, while a synchronized copy is also logged in Lark Bitable for monitoring and reporting.

4. **Image Processing Pipeline**:
   - The uploaded photo is routed through AI-based headshot enhancement (BytePlus Seedream 4.5) to improve lighting and framing.
   - Background removal is applied via Cloudinary AI to produce a clean ID photo.
   - Processed images are stored in Cloudinary and referenced via public URLs.

5. **ID Generation**: Using validated employee data and the processed image, the system generates a digital employee ID based on the approved template and marks the output as ready for review.

6. **HR Review Queue**: HR personnel verify correctness, compliance, and output quality. During this stage, HR can approve the ID, return it for revision, or reject the request.

7. **Distribution & Turnover**: Once approved, the print-ready ID output is routed to the designated POC based on the employee's branch using haversine distance calculation. The system records this handoff as part of the status progression.

### Status Lifecycle

```
Reviewing → Rendered → Approved → Sent to POC → Completed
                                                    │
                                              (Removed — soft delete)
```

---

## 7. Deployment and Installation Instructions

### 7.1 Supported Environments

| Environment | Purpose | Storage |
|-------------|---------|---------|
| Local Development | Development, testing, debugging | Full filesystem access |
| Production (Vercel Serverless) | Live employee and HR operations | Cloud services (Cloudinary, Supabase) |

### 7.2 Prerequisites

**System Requirements:**
- Operating System: Windows, macOS, or Linux
- Python 3.9 or later
- Internet access for API integrations
- Modern web browser (Chrome, Edge, Firefox)

**Required Accounts and Services:**
- **Cloudinary** — image hosting + background removal via Cloudinary AI
- **BytePlus** — Seedream headshot generation API key
- **Lark Developer** — OAuth/SSO + app credentials for employee login and profile autofill

**Optional (Feature-Based):**
- **Google Sheets** — service account for optional sheet syncing
- **Supabase** — persistent database storage (otherwise SQLite fallback)
- **remove.bg** — optional fallback background removal

### 7.3 Local Installation Procedure

**Step 1: Clone the Project Repository**
```bash
git clone <repository-url>
cd hr-id-automation-main
```

**Step 2: Create and Activate a Virtual Environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

**Step 3: Install Dependencies**
```bash
pip install -r requirements.txt
```

**Step 4: Create Environment Configuration File**
```bash
cp .env.example .env
```

Configure the `.env` file with the required values:
- Cloudinary credentials (`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`)
- BytePlus API key (`BYTEPLUS_API_KEY`, `BYTEPLUS_ENDPOINT`, `BYTEPLUS_MODEL`)
- Lark App credentials (`LARK_APP_ID`, `LARK_APP_SECRET`, `LARK_REDIRECT_URI`)
- Optional: Supabase, Google Sheets, remove.bg credentials

> ⚠️ The `.env` file must never be committed to version control.

**Step 5: Database Initialization**

The system initializes database connectivity on startup automatically:
- If Supabase credentials are provided → connects to Supabase for persistent storage
- If Supabase is not configured → uses SQLite fallback and creates required tables automatically
- Minor schema updates for SQLite fallback are applied automatically during initialization

**Step 6: Start the Development Server**
```bash
uvicorn app.main:app --reload
```

**Step 7: Access the Application**
- Landing Page: `http://localhost:8000/`
- Employee Form: `http://localhost:8000/apply`
- HR Dashboard: `http://localhost:8000/hr/dashboard`

### 7.4 Production Deployment (Vercel)

**Step 8: Configure Production Environment Variables**
- Set all environment variables directly in Vercel Project Settings
- Do not rely on a `.env` file in production

**Step 9: Deploy Application**
- Deploy as a serverless Python service via Git-based deployment from GitHub
- Static assets are served through the platform's static file routing
- Backend routes are handled by the FastAPI application entry point configured in `vercel.json`

**Deployment Configuration** (`vercel.json`):
```json
{
  "version": 2,
  "builds": [{ "src": "api/index.py", "use": "@vercel/python", "config": { "maxLambdaSize": "50mb" } }],
  "routes": [{ "src": "/(.*)", "dest": "/api/index.py" }],
  "env": { "PYTHONUNBUFFERED": "1" }
}
```

### 7.5 Post-Deployment Verification

1. Access the landing page successfully
2. Complete an employee submission flow:
   - Confirm employee authentication via Lark SSO
   - Confirm AI headshot generation executes (BytePlus)
   - Confirm background removal is applied (Cloudinary AI)
   - Confirm data is stored correctly (Supabase)
3. Login to the HR dashboard
4. Verify submitted request appears in the HR management interface
5. Verify status progression and export/PDF generation functions

### 7.6 File Storage and Image Handling

Due to serverless filesystem limitations:
- Uploaded images are **not** stored permanently on the server
- All employee photos and generated ID images are uploaded to Cloudinary and referenced via public URLs
- Temporary runtime files may be stored in ephemeral directories (`/tmp`) during execution

---

## 8. Server Requirements

### 8.1 Application Runtime Requirements

| Requirement | Specification |
|-------------|---------------|
| Programming Language | Python 3.9 or higher |
| Application Framework | FastAPI |
| Web Server | ASGI-compatible server (Uvicorn) |
| Package Manager | pip |
| Environment Configuration | `.env` file or platform-based environment variables |
| Template Engine | Jinja2 (server-rendered HTML templates) |

### 8.2 Compute Requirements

| Resource | Minimum Requirement | Notes |
|----------|-------------------|-------|
| CPU | 1 vCPU | Suitable for concurrent form submissions and HR access |
| Memory | 512 MB (local), 1024 MB (cloud recommended) | Higher memory improves stability for image processing |
| Execution Time | Platform-limited | External API latency (AI/background removal) can affect runtime |
| Concurrent Requests | Moderate | Designed for internal organizational usage |

### 8.3 Storage Requirements

| Type | Requirement |
|------|-------------|
| Local Development | Writable filesystem |
| Cloud Deployment | Ephemeral storage only |
| Primary Database | Supabase (PostgreSQL) |
| Fallback Database | SQLite |

### 8.4 Network and Connectivity

The server must have outbound internet access to communicate with:

| Service | Purpose |
|---------|---------|
| Cloudinary | Image upload, retrieval, and processing |
| BytePlus (Seedream) | Professional headshot generation |
| Cloudinary AI / remove.bg | Background removal |
| Google Sheets (Optional) | Data sync and reporting |
| Lark | OAuth 2.0 authentication and Bitable sync |
| BarcodeAPI.org | Barcode generation for ID elements |

### 8.5 Scalability Considerations

- The system is designed for internal organizational scale
- Horizontal scaling is handled by the deployment platform (serverless)
- External services handle storage and processing scalability
- No manual load balancing is required

### 8.6 Limitations

| Limitation | Description |
|------------|-------------|
| Persistent Storage (Fallback Mode) | SQLite on serverless uses ephemeral `/tmp` storage |
| Large File Uploads | Limited by external service constraints |
| Long-Running Tasks | Bound by serverless execution limits and external API latency |

---

## 9. Tech Stacks

### 9.1 Backend Technologies

| Component | Technology | Description |
|-----------|-----------|-------------|
| Backend Framework | FastAPI (Python) | Core backend framework for API endpoints, HTTP request handling, routing, and request validation |
| Application Server | Uvicorn (ASGI) | ASGI server for running the FastAPI application |
| Authentication (HR) | Custom JWT (HS256) + bcrypt | HR authentication using JWT tokens stored in `hr_session` cookies with bcrypt password hashing (`app/auth.py`) |
| Authentication (Employee) | Lark SSO (OAuth 2.0 + PKCE) | Employee authentication via Lark OAuth with PKCE for secure sign-in and profile-based autofill (`app/services/lark_auth_service.py`) |
| API Design | RESTful APIs | Backend exposes REST endpoints for employee submission, AI processing, HR dashboard access, and data retrieval |
| Environment Configuration | python-dotenv | Loads environment variables securely from `.env` files |
| File Upload Handling | python-multipart | Enables handling of multipart form submissions for image uploads and signature capture |
| Async File I/O | aiofiles | Supports async-friendly file operations |
| HTTP Utilities | httpx, requests | Used for calling external services and fetching/processing remote assets |

### 9.2 Frontend Technologies

| Component | Technology | Description |
|-----------|-----------|-------------|
| Markup | HTML (Jinja2 Templates) | Server-rendered HTML templates for landing page, employee form, HR login, HR dashboard, and gallery views |
| Styling | CSS (Custom Stylesheets) | Custom CSS files for layout, responsiveness, animations, and UI consistency |
| Client-side Logic | Vanilla JavaScript | Handles form interactions, live ID preview, AI image generation calls, background removal triggers, and UI feedback |
| PDF Rendering (Client-side) | html2canvas | Captures the ID card preview/layout in the browser as an image for export rendering |
| PDF Export (Client-side) | jsPDF | Generates print-ready PDFs in the browser based on captured ID layouts at 300 DPI (2.13" × 3.33") |
| UI Design Approach | Responsive Web Design | Interfaces optimized for desktop and mobile usage |

### 9.3 Database and Storage

| Component | Technology | Description |
|-----------|-----------|-------------|
| Primary Database | Supabase (PostgreSQL) | Cloud-based PostgreSQL database when Supabase credentials are configured |
| Fallback Database | SQLite | Fallback when Supabase credentials are not set; also used during local development |
| Cloud Storage | Cloudinary | Stores employee images, AI-generated photos, background-removed assets, and rendered ID PDFs |
| Serverless Temporary Storage | `/tmp` Directory (Vercel) | Temporary storage used during execution in Vercel's serverless environment |

### 9.4 AI and Image Processing Services

| Component | Technology | Description |
|-----------|-----------|-------------|
| AI Headshot Generation | BytePlus Seedream 4.5 | Generates professional, standardized employee headshots from uploaded images. 8 prompt types (male/female × 4 styles) |
| Background Removal (Primary) | Cloudinary AI | Default method for background removal and image standardization |
| Background Removal (Optional) | remove.bg API | Optional fallback used only when `REMOVEBG_API_KEY` is provided |
| Image Processing | Pillow (PIL) | Handles image resizing, format handling, and processing before upload or rendering |

### 9.5 Identification and Validation Services

| Component | Technology | Description |
|-----------|-----------|-------------|
| Barcode Generation | BarcodeAPI.org | Generates barcodes (CODE128 default, also supports CODE39, QR, DataMatrix, EAN13, UPC) for employee ID validation |

### 9.6 External Integrations

| Integration | Technology | Purpose |
|-------------|-----------|---------|
| Image Hosting | Cloudinary API | Stores original, AI-generated, and processed images; provides public URLs; handles PDF uploads |
| Data Synchronization (Optional) | Google Sheets (gspread + Service Account) | Appends employee submission data and image URLs to Google Sheets for reporting |
| Collaboration Platform | Lark | Employee authentication (SSO), profile autofill, Bitable data tracking, messaging for POC routing |
| Tracking/Database Sync | Lark Bitable | Real-time syncing of employee records and status progression |
| Notifications/Routing | Lark Messaging | Sends/notifies designated POCs with finalized outputs/links |

### 9.7 Deployment and Infrastructure

| Component | Technology | Description |
|-----------|-----------|-------------|
| Hosting Platform | Vercel (Serverless) | Hosts the FastAPI backend and frontend as serverless functions |
| Deployment Method | Git-based Deployment | Code deployed directly from GitHub repository |
| Configuration Management | Environment Variables | Sensitive credentials stored as environment variables |
| Routing | Vercel Routing Rules | Handles static file serving and API request routing |

### 9.8 Development and Productivity Tools

| Tool | Purpose |
|------|---------|
| GitHub | Source code version control and collaboration |
| Lark Docs | Task tracking, sprint planning, and progress monitoring |
| Figma / FigmaMake | UI/UX planning and layout prototyping |
| AI Tools | ChatGPT, Claude Opus 4.5 (for ideation, prompt refinement, and development support) |

### 9.9 Key Dependencies (requirements.txt)

```
fastapi==0.109.0        uvicorn[standard]==0.27.0
python-multipart==0.0.6 aiofiles==23.2.1
jinja2==3.1.2           supabase==2.10.0
bcrypt==4.1.2           httpx==0.26.0
requests==2.31.0        cloudinary==1.38.0
Pillow==10.2.0          gspread==6.0.0
google-auth==2.27.0     google-auth-oauthlib==1.2.0
python-dotenv==1.0.0    mangum==0.17.0
```

---

## 10. Database Structure

### 10.1 Database Engine

- **Type**: Supabase (PostgreSQL) with SQLite fallback
- **Initialization Method**: `init_db()` in `app/database.py`
- **Environment Handling**:
  - If `SUPABASE_URL` and `SUPABASE_KEY` are set → connects using Supabase client
  - If credentials are not set or initialization fails → falls back to SQLite
- **SQLite Storage Location**:
  - Local Development: `database.db` in the project root
  - Cloud/Serverless (Vercel fallback): `/tmp/database.db` (ephemeral)

### 10.2 Database Tables Overview

The system uses the following tables:

| Table | Purpose |
|-------|---------|
| `employees` | Stores employee submissions, image references, processing states, and generated ID outputs |
| `security_events` | Stores security-related logs (screenshot/recording attempt events) |
| `oauth_states` | Stores OAuth PKCE state for Lark SSO (Supabase only, 10-minute TTL) |
| `headshot_usage` | Tracks per-user AI headshot generation count for rate limiting (limit: 5/user) |

### 10.3 `employees` Table Structure

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `id` | INTEGER / BIGSERIAL (PK, Auto Increment) | Unique internal identifier for each submission |
| `employee_name` | TEXT (Not Null) | Full name of the employee |
| `first_name` | TEXT | First name (stored separately when provided) |
| `middle_initial` | TEXT | Middle initial (stored separately when provided) |
| `last_name` | TEXT | Last name (stored separately when provided) |
| `suffix` | TEXT | Optional suffix (e.g., Jr., III) |
| `id_nickname` | TEXT | Optional nickname displayed on the ID |
| `id_number` | TEXT (Not Null) | Official employee ID number |
| `position` | TEXT (Not Null) | Employee job position |
| `location_branch` | TEXT | Employee branch/location |
| `department` | TEXT | Employee department |
| `email` | TEXT | Employee email address |
| `personal_number` | TEXT | Employee contact number |
| `photo_path` | TEXT (Not Null) | Local file path of the uploaded or generated photo |
| `photo_url` | TEXT | Public URL of the original photo (Cloudinary) |
| `new_photo` | INTEGER/BOOLEAN (Default: 1/TRUE) | Flag indicating whether a new photo was generated |
| `new_photo_url` | TEXT | URL of AI-enhanced or AI-generated photo |
| `nobg_photo_url` | TEXT | URL of background-removed photo |
| `signature_path` | TEXT | Local file path of the signature image |
| `signature_url` | TEXT | Public URL of the signature image |
| `status` | TEXT (Default: 'Reviewing') | Current processing status |
| `date_last_modified` | TEXT | Timestamp of the last update |
| `id_generated` | INTEGER/BOOLEAN (Default: 0/FALSE) | Flag indicating if an ID output has been generated |
| `render_url` | TEXT | URL or path to the final rendered ID output |
| `emergency_name` | TEXT | Emergency contact name |
| `emergency_contact` | TEXT | Emergency contact number |
| `emergency_address` | TEXT | Emergency contact address |
| `field_officer_type` | TEXT | Field officer classification/type |
| `field_clearance` | TEXT | Field clearance value/flag |
| `fo_division` | TEXT | Field officer division |
| `fo_department` | TEXT | Field officer department |
| `fo_campaign` | TEXT | Field officer campaign |
| `resolved_printer_branch` | TEXT | System-resolved printer/POC branch used for routing |

**Status Constraint (Supabase):** `Reviewing | Rendered | Approved | Sent to POC | Completed | Removed`

### 10.4 `security_events` Table Structure

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `id` | INTEGER (PK, Auto Increment) | Unique identifier for the event |
| `event_type` | TEXT (Not Null) | Type of security event (e.g., screenshot attempt) |
| `details` | TEXT | Additional event details |
| `user_id` | INTEGER | Related user/employee record ID |
| `username` | TEXT | Username/email if available |
| `url` | TEXT | Page/route where the event occurred |
| `user_agent` | TEXT | Browser user agent string |
| `screen_resolution` | TEXT | Client screen resolution |
| `timestamp_server` | TEXT (Not Null) | Server-side timestamp |
| `timestamp_client` | TEXT | Client-side timestamp |
| `created_at` | TEXT (Not Null) | Event creation timestamp |

### 10.5 `oauth_states` Table Structure (Supabase Only)

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `state` | TEXT (PK) | OAuth state parameter |
| `code_verifier` | TEXT (Not Null) | PKCE code verifier |
| `redirect_uri` | TEXT (Not Null) | OAuth redirect URI |
| `created_at` | TIMESTAMPTZ (Default: NOW()) | Creation timestamp |
| `expires_at` | TIMESTAMPTZ (Default: NOW() + 10 min) | Expiration timestamp |

### 10.6 `headshot_usage` Table Structure (Supabase Only)

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `id` | BIGSERIAL (PK) | Unique identifier |
| `lark_user_id` | TEXT (Not Null) | Lark user identifier |
| `created_at` | TIMESTAMPTZ (Default: NOW()) | Usage timestamp |

### 10.7 Status and Lifecycle Tracking

- **Initial State**: `status = 'Reviewing'`, `id_generated = 0`
- **During Processing**:
  - AI-generated and processed image URLs are stored (`new_photo_url`, `nobg_photo_url`)
  - Signature assets are saved and linked
  - `date_last_modified` is updated on changes
- **Post-HR Approval**:
  - Status is updated through workflow states (`Rendered → Approved → Sent to POC → Completed`)
  - `id_generated` is set to 1 when an output is produced
  - `render_url` is populated with the final output reference

### 10.8 Migration and Schema Evolution

- For **SQLite fallback**: New columns are added dynamically using `ALTER TABLE` statements if they do not yet exist, preventing database breakage when updates are introduced
- For **Supabase**: Schema migrations are provided in `supabase_setup.sql` using `ADD COLUMN IF NOT EXISTS`

---

## 11. Features and Functionalities

### 11.1 Employee Portal

#### Lark SSO Authentication
- Employees authenticate via Lark OAuth 2.0 with PKCE (`app/services/lark_auth_service.py`)
- Upon login, the system auto-fills employee details (name, email, employee number, mobile) from the Lark profile
- Name is parsed into `first_name`, `middle_initial`, `last_name`, and `suffix` components (`parse_lark_name()` in `app/main.py`)
- Session stored as a 24-hour JWT token in the `employee_session` cookie

#### Photo Upload and AI Headshot Generation
- Employees can upload a photo or generate an AI-enhanced professional headshot
- AI generation uses **BytePlus Seedream 4.5** with 8 prompt types:
  - `male_1` through `male_4` and `female_1` through `female_4`
  - Smart casual attire, Filipino appearance, 3/4 angle, 85mm lens, transparent background, closed mouth
- Rate-limited to **5 headshot generations per Lark user** (tracked in `headshot_usage` table)
- Uploaded photos are stored in Cloudinary; processing pipeline: Upload → Seedream AI → Cloudinary Background Removal

#### Automatic Background Removal
- Primary method: **Cloudinary AI** background removal (via `upload_url_with_bg_removal()`)
- Optional fallback: **remove.bg API** (used only when `REMOVEBG_API_KEY` is configured)

#### Live ID Card Preview
- Real-time ID card preview updates as form fields are filled in (`updateIdCardPreview()` in `app/static/app.js`)
- **Portrait template** (512×800): Standard employee ID with nickname, full name (dynamic font scaling), position, barcode, photo, signature
- **Field Office template** (landscape 512×319): For Field Officer positions with clearance level
- **Dual template mode**: For Repossessor/Shared FO types showing both Portrait (SPMC) + Landscape (Field Office) cards
- Backside preview includes emergency contact, dynamic URL (`www.okpo.com/spm/{name}`), vCard QR code, URL QR with OKPO logo

#### Digital Signature Capture
- Built-in canvas-based signature pad with transparent PNG output
- Touch support for mobile devices

#### Form Validation
- **Client-side** (`app/static/app.js`): Real-time field-level validation with comprehensive pre-submit validation
- **Server-side** (`app/validators.py`): QA-grade backend validation mirroring frontend rules
  - Phone number: PH 11-digit starting with `09`, blocks test patterns
  - Name: Letters/spaces/hyphens/apostrophes, title-case formatting
  - Middle initial: Single letter → uppercase + period
  - Email: Regex + typo detection (`gmial.com` → `gmail.com`)
  - Birthdate: Age range 15–80
  - Position: `Field Officer` / `Freelancer` / `Intern` / `Others`
  - Branch: 18 canonical + 12 legacy branch names
  - ID number uniqueness check (Supabase)

#### Position-Based Conditional UI
- Position radio buttons: Freelancer / Intern / Field Officer / Others
- Field Officer selection shows: subtype, department/campaign dropdowns
- Expiration date field: Only for Freelancer and Intern positions
- Searchable dropdowns and multi-select dropdown (Campaign field)

#### Barcode Generation
- Employee ID barcode generated via **BarcodeAPI.org** (CODE128 default)
- Barcode displayed on the live ID card preview
- Proxy endpoint: `GET /api/barcode/{id_number}/image`

### 11.2 HR Dashboard

#### Authentication
- HR login via custom session-based authentication with bcrypt password hashing
- Credentials configured via `HR_USERS` environment variable (format: `user1:pass1,user2:pass2`)
- Default credentials: `hradmin / HR@2026`
- 8-hour JWT session stored in `hr_session` cookie

#### Employee Management
- Searchable employee table with status badges, photo/AI photo columns, and action buttons
- Filtering: Search + status + position filters (excludes `Removed` records)
- Data fetching with Vercel cold-start resilience: 20-second timeout, 2 retries, `sessionStorage` caching (5-minute TTL)

#### HR Actions
- **View Details**: Modal showing original/AI/no-bg photos, employee info, barcode, and signature
- **Render ID** (`Reviewing → Rendered`): Marks submission for rendering
- **Approve** (`Rendered → Approved`): Approves with Lark Bitable sync
- **Send to POC** (`Approved → Sent to POC`): Haversine-based POC routing with Lark DM + optional PDF attachment
- **Complete** (`Sent to POC → Completed`): Final status
- **Remove** (soft-delete → `Removed`): Removes from active view

#### Bulk Actions
- **Approve All Rendered**: Batch approval with concurrency limit of 2
- **Send All to POCs**: Batch POC routing (55-second timeout for Vercel)

#### Data Export & Sync
- **Sync to Google Sheets**: Appends employee data and image URLs to Google Sheets
- **Export Data**: CSV download of employee records
- **Upload PDF**: PDF → Cloudinary → Lark Bitable `id_card` field (10 MB limit)

#### Statistics
- Status summary cards: Rendered / Approved / Sent to POC counts

### 11.3 ID Gallery

#### Gallery Grid
- Renders ID card HTML for employees in Rendered / Approved / Sent to POC status
- Status-aware action buttons (Approve / Send to POC / Completed)

#### ID Card Templates
- **Regular ID Card** (portrait 512×800): Standard employee ID
- **Field Office ID Card** (landscape 512×319): For Field Officer positions
- **Dual Template**: Combined SPMC portrait + Field Office landscape for ALL Field Officers
- **Card Backside**: Emergency contact, QR codes (dynamic URL + vCard), OKPO branding

#### PDF Generation
- Uses **jsPDF** + **html2canvas** at **300 DPI** (2.13" × 3.33")
- Regular employees: 2-page PDF (portrait front + back)
- Field Officers: 4-page PDF (portrait front/back + landscape front/back)
- **Upload-before-download**: PDF must successfully upload to Cloudinary + Lark Bitable before local download is allowed
- Size check: 10 MB limit

#### Bulk Operations
- Bulk PDF download (`downloadAllPdfs()`)
- Bulk approve and save ID (`approveAndSaveID()`)
- Bulk POC distribution with LarkBot messaging (`sendAllToPOCs()`)

### 11.4 POC Routing System

The system implements intelligent ID card routing to Points of Contact:

- **Haversine-based routing** (`app/services/poc_routing_service.py`): 7-step algorithm
  1. Normalize branch name
  2. Direct POC match
  3. Alias resolution
  4. Guardrail check
  5. Pending check
  6. Haversine distance calculation
  7. Default to QC (Quezon City)
- **18 active POC branches** with contacts and coordinates
- **40+ branch coordinates** for fallback distance calculation

### 11.5 Lark Integration

- **OAuth 2.0 + PKCE** for employee authentication
- **Lark Bitable** for employee record syncing and status tracking
- **Lark Messaging** for POC notification with file attachments
- **Lark Drive** for file uploads
- **HR Access Control**: Validates HR users are in People Support department hierarchy via Lark Contact API (30-minute cache)
- **Dual Lark App Support**: Separate SPMC and SPMA credentials, Bitable tables, and submission flows

### 11.6 Screenshot Protection

Client-side security module (`app/static/screenshot_protection.js`):
- **Black overlay** when tab is hidden (Page Visibility API) or window loses focus
- **Dynamic watermark**: Rotated `CONFIDENTIAL • {user} • {timestamp}`, updates every 30 seconds
- **Keyboard shortcut detection**: PrintScreen, Ctrl+Shift+S, Win+Shift+S, Cmd+Shift+3/4/5
- **Server logging**: POSTs events to `/api/security/log-attempt`
- **Employee-side only**: Screenshot restrictions are NOT enforced for HR users (per HR feedback)
- Configurable via `data-screenshot-protection="true"` body attribute

### 11.7 Security Base Template

Additional protections in `app/templates/security_base.html`:
- No-cache meta headers
- `user-select: none` on `.sensitive-data` elements
- Print prevention (`@media print` hides sensitive content)
- CSS watermarks (corner + diagonal)
- Right-click/context menu prevention
- Developer Tools detection (via `debugger` timer)

---

## 12. User Roles and Access

### 12.1 Authorized User Roles

| User Role | Access Scope | Primary Responsibilities | Authentication Method |
|-----------|-------------|-------------------------|----------------------|
| Employee | Employee Portal (ID Application Form) | Submit personal/employment details, upload photo and signature, review live ID preview before submission | Lark SSO (OAuth 2.0 + PKCE) |
| HR Personnel | HR Dashboard + Gallery | Review ID applications, validate submitted information, approve or reject requests, generate and manage ID outputs, route to POC | Custom JWT session (bcrypt password auth) |
| System Administrator | Application Configuration & Deployment | Manage environment variables, configure integrations, deploy and maintain the system | Server/platform-level access |

### 12.2 Access Control Principles

- Access is limited strictly to assigned roles and cannot be shared across user types
- Employees cannot access HR dashboard functionalities
- HR users cannot modify system configuration or deployment settings
- Administrative access is limited to personnel responsible for system maintenance

### 12.3 Authentication and Authorization Rules

- All HR access requires successful authentication before dashboard access is granted
- User sessions are validated on each protected request to prevent unauthorized access
- Unauthorized users attempting to access restricted routes are redirected or denied access
- Authentication credentials and access rules are configurable via environment variables
- HR session: 8-hour JWT token in `hr_session` cookie
- Employee session: 24-hour JWT token in `employee_session` cookie

### 12.4 HR Access Control via Lark (Additional)

In the codebase, there is an additional mechanism (`is_descendant_of_people_support()` in `app/services/lark_auth_service.py`) that validates whether a user belongs to the People Support department hierarchy via the Lark Contact API. This provides an enterprise-level access control layer beyond basic password authentication.

---

## 13. Security and Privacy

### 13.1 Credential Management

- All credentials and tokens are managed through environment variables — never hardcoded
- The `.env` file is excluded from version control
- Sensitive keys: `JWT_SECRET`, `HR_USERS`, `LARK_APP_ID`, `LARK_APP_SECRET`, Cloudinary credentials, `BYTEPLUS_API_KEY`

### 13.2 Authentication Security

| Area | Implementation |
|------|---------------|
| HR Authentication | Custom JWT (HS256) tokens with bcrypt password hashing |
| Employee Authentication | Lark OAuth 2.0 with PKCE (state stored in Supabase `oauth_states` table) |
| Session Handling | Time-bound JWT cookies (`hr_session` = 8h, `employee_session` = 24h) |
| Password Security | bcrypt hashing with 72-byte truncation for long passwords |

### 13.3 HTTP Security Headers

Applied via `SecurityHeadersMiddleware` in `app/main.py`:
- **Content Security Policy (CSP)**: script-src, img-src, connect-src directives
- **X-Frame-Options**: `DENY`
- **X-Content-Type-Options**: `nosniff`
- **HSTS** (HTTP Strict Transport Security)
- **Referrer-Policy**: Strict referrer policy

### 13.4 Client-Side Security

- **Screenshot protection** (employee-side): Black overlay, keyboard shortcut blocking, server-side event logging
- **Dynamic watermarking**: CONFIDENTIAL overlay with user identity and timestamp
- **Print prevention**: `@media print` rules hide sensitive content
- **Context menu prevention**: Right-click disabled
- **Developer Tools detection**: `debugger` timer-based detection
- **No-cache headers**: Prevents browser caching of sensitive pages
- **User selection prevention**: `user-select: none` on sensitive data elements

### 13.5 Data Storage Security

- Employee data stored in Supabase (PostgreSQL) with optional Row Level Security (RLS)
- Images stored in Cloudinary with controlled URLs
- No persistent file storage on serverless infrastructure
- Temporary files cleaned up after request completion

### 13.6 Network Security

- HTTPS recommended for deployed environments
- Inbound access limited to standard HTTP/HTTPS requests
- All external API calls use secure endpoints

---

## 14. Third-Party Integrations

### 14.1 Cloudinary (Required)

**Purpose**: Image hosting, delivery, transformations, and background removal

| Function | Description |
|----------|-------------|
| `upload_image_to_cloudinary()` | Upload employee photos |
| `upload_base64_to_cloudinary()` | Upload base64-encoded images |
| `upload_url_with_bg_removal()` | Cloudinary AI background removal |
| `upload_url_to_cloudinary_simple()` | Simple URL-based upload |
| `upload_bytes_to_cloudinary()` | Upload raw bytes |
| `upload_pdf_to_cloudinary()` | Upload raw PDF files (10 MB limit) |

**Env Variables**: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `CLOUDINARY_FOLDER`

### 14.2 BytePlus Seedream 4.5 (Required)

**Purpose**: AI-powered professional headshot generation

- Generates standardized employee headshots from uploaded images
- 8 prompt types (male/female × 4 styles)
- Prompt constraints: Smart casual attire, Filipino appearance, 3/4 angle, 85mm lens, transparent background, closed mouth

**Env Variables**: `BYTEPLUS_API_KEY`, `BYTEPLUS_ENDPOINT`, `BYTEPLUS_MODEL`

### 14.3 Lark Suite (Required)

**Purpose**: Employee authentication, enterprise data sync, messaging

| Feature | Description |
|---------|-------------|
| OAuth 2.0 + PKCE | Employee SSO authentication |
| Bitable CRUD | Real-time employee record syncing and status tracking |
| Drive Upload | File uploads to Lark Drive |
| IM Messaging | POC notification with file attachments |
| Contact API | HR department hierarchy validation |

**Env Variables**: `LARK_APP_ID`, `LARK_APP_SECRET`, `LARK_BITABLE_ID`, `LARK_TABLE_ID`, `LARK_REDIRECT_URI`, `LARK_EMPLOYEE_REDIRECT_URI`, `TARGET_LARK_DEPARTMENT_ID`, `LARK_APP_ID_SPMA`, `LARK_APP_SECRET_SPMA`, `LARK_BITABLE_ID_SPMA`, `LARK_TABLE_ID_SPMA`

### 14.4 Supabase (Required for Production)

**Purpose**: Persistent PostgreSQL database storage

- Employee records, security events, OAuth state, headshot usage tracking
- Falls back to SQLite if credentials are not configured

**Env Variables**: `SUPABASE_URL`, `SUPABASE_KEY`

### 14.5 BarcodeAPI.org (Required)

**Purpose**: Barcode generation for employee ID validation elements

- Supports: CODE128 (default), CODE39, QR, DataMatrix, EAN13, UPC
- Free tier: 10,000 tokens/day

### 14.6 Google Sheets (Optional)

**Purpose**: Data synchronization for reporting and tracking

- Appends employee submission data and image URLs (with `IMAGE()` formulas) to Google Sheets
- Uses Google Service Account authentication

**Env Variables**: `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SPREADSHEET_ID`, `GOOGLE_WORKSHEET_NAME`

### 14.7 remove.bg (Optional)

**Purpose**: Fallback background removal service

- Used only when `REMOVEBG_API_KEY` is provided and Cloudinary AI is insufficient
- Credit-based pricing

**Env Variable**: `REMOVEBG_API_KEY`

---

## 15. Troubleshooting

| Issue | Possible Causes | Troubleshooting Steps |
|-------|----------------|----------------------|
| **Application Does Not Start** | Missing/incorrect environment variables; dependencies not installed; incorrect Python version | 1. Verify all required env vars in `.env` or deployment environment. 2. Run `pip install -r requirements.txt`. 3. Ensure Python 3.9+. 4. Check terminal logs for errors. |
| **Static Assets Not Loading** | Static files not mounted correctly; incorrect file paths; deployment platform limitations | 1. Verify `/static` directory is correctly mounted. 2. Confirm CSS/JS files exist in `app/static/`. 3. Clear browser cache. 4. Ensure static files are included in deployment build. |
| **Employee Form Submission Fails** | Invalid/missing form inputs; image upload failure; backend validation errors | 1. Confirm all required fields are filled correctly. 2. Check file upload size and format. 3. Inspect backend logs for validation errors. 4. Verify multipart form handling is configured. |
| **AI Headshot Generation Not Working** | Missing/invalid API key; external AI service downtime; unsupported image format | 1. Confirm BytePlus API key is correctly set. 2. Test with a valid image file. 3. Monitor logs for timeout/request errors. 4. Verify fallback to original image handling. |
| **Background Removal Fails** | Service not installed/disabled; resource limitations; service dependency download failure | 1. Check whether background removal dependency is available. 2. Review logs for service unavailability. 3. Test locally. 4. Disable background removal temporarily if needed. |
| **Images Not Appearing in HR Dashboard** | Image storage credentials missing/invalid; incorrect image URLs in database; filesystem restrictions | 1. Verify Cloudinary credentials are correct and active. 2. Check database records for valid image URLs. 3. Confirm images are served from Cloudinary. 4. Test image URLs directly. |
| **HR Login/Dashboard Access Issues** | Invalid credentials; expired/missing session cookies; misconfigured access control | 1. Verify HR credentials in `HR_USERS` env variable. 2. Clear browser cookies. 3. Check session handling logic. 4. Review access logs. |
| **Data Not Persisting After Deployment** | Temporary storage in serverless environments; application restart/redeployment | 1. Confirm whether running on serverless with ephemeral storage. 2. Understand `/tmp` data resets on redeployments. 3. Migrate to Supabase for persistence. |
| **Deployment-Specific Issues** | Environment variable mismatch; platform limitations; build/routing misconfiguration | 1. Compare local `.env` with deployed settings. 2. Review deployment logs. 3. Confirm `vercel.json` routing and entry-point configurations. 4. Redeploy after fixes. |

---

## 16. Development Cost

### 16.1 Cost Scope and Assumptions

| Item | Description |
|------|-------------|
| Development Type | Internal (no outsourcing) |
| Billing Model | Mixed (Free tier, subscription, usage-based) |
| Employee Volume | 3,000 employees |
| Cost Coverage | AI processing, image storage, database, hosting |
| Currency | PHP (with USD reference where applicable) |

> Development labor costs are excluded as this is an internal initiative. This section focuses on tooling and infrastructure costs only.

### 16.2 AI and Image Processing Costs

#### Background Removal (Primary: Cloudinary AI)
- **Cost Type**: Included in Cloudinary monthly credits/usage
- **Risk**: High usage if reprocessing is triggered frequently
- **Mitigation**: Limit retries, cache processed outputs, reuse transformed URLs

#### Background Removal (Optional Fallback: remove.bg)
| Item | Value |
|------|-------|
| Total Employees | 3,000 |
| Images per Credit | 4 |
| Total Credits Required | 750 credits |
| Cost per Credit | $1 |
| Total Cost (USD) | $750 |
| Total Cost (PHP) | ₱45,000 |

#### AI Headshot Generation (BytePlus Seedream 4.5)
| Item | Value |
|------|-------|
| Total Employees | 3,000 |
| Cost per Image | ₱2.40 ($0.04) |
| Max Attempts per Employee | 5 |
| Cost per Employee | ₱12 |
| Total Cost (PHP) | ₱36,000 |

### 16.3 Barcode Generation (BarcodeAPI.org)
| Plan | Cost | Daily Token Limit |
|------|------|------------------|
| Free Tier | ₱0 | 10,000 tokens/day |
| Pro Tier | $15/month | 25,000 tokens/day |

**Estimated Cost**: ₱0 (fits entirely within Free Tier)

### 16.4 Image Storage (Cloudinary)
| Plan | Cost | Monthly Credits |
|------|------|-----------------|
| Free | ₱0 | 25 |
| Plus | ₱5,340 | 225 |

- 1 credit = 1 GB
- Plus plan is required for sustained operations.

### 16.5 Database and Storage (Supabase)
| Plan | Included Storage | Monthly Cost |
|------|-----------------|-------------|
| Free | 1 GB | ₱0 |
| Pro | 100 GB | $0.021 per GB/month |

### 16.6 Hosting (Vercel)
- Currently running on Hobby (Free) Plan
- No charges incurred yet

### 16.7 Consolidated Cost Summary

**One-Time/Volume-Based Costs:**
| Item | Cost (PHP) |
|------|-----------|
| AI Headshot Generation | ₱36,000 |
| Background Removal (remove.bg) | ₱45,000 |
| **Total One-Time AI Cost** | **₱81,000** |

**Recurring Monthly Costs (Minimum):**
| Item | Cost (PHP) |
|------|-----------|
| Cloudinary Plus Plan | ₱5,340 |
| Supabase Storage | Usage-based |
| Vercel Hosting | ₱0 (current) |

---

## 17. Stakeholders

### 17.1 Primary Stakeholders

| Stakeholder | Role | Responsibility |
|-------------|------|----------------|
| Human Resources (HR) Team | System Owner / Primary User | Reviews employee submissions, validates information, approves ID generation, manages employee records |
| Employees | End Users | Submit personal information, photos, and signatures for ID registration |
| Project Lead | Product Oversight | Oversees system direction, prioritizes features, ensures alignment with business requirements |
| Development Team | System Development | Designs, builds, tests, and maintains the Employee ID Registration System |

### 17.2 Secondary Stakeholders

| Stakeholder | Role | Responsibility |
|-------------|------|----------------|
| IT/Technical Support | Infrastructure Support | Assists with deployment, system access, troubleshooting, and environment configuration |
| Management/Decision Makers | Review and Approval | Reviews project progress, evaluates effectiveness, approves rollout or enhancements |
| Data Protection/Compliance | Advisory | Ensures proper handling of employee data and adherence to internal data privacy standards |

---

## 18. User Feedback

User feedback was gathered during system demonstrations, walkthroughs, and review discussions with intended users.

### Key Feedback and Actions Taken

| Feedback Area | User Input | System Response |
|---------------|-----------|-----------------|
| Background Removal Cost | Supervisor suggested exploring Canva Premium as lower-cost alternative | Evaluated; supervisor confirmed current implementation was sufficient |
| Position Input on New ID Template | HR clarified positions should no longer be manually typed | Position handling aligned to predefined options and HR-controlled logic |
| Personal Details – Name Suffix | HR requested support for name suffixes (Jr., Sr., III) | Suffix field added to personal details handling and ID data mapping |
| Signature Layout Adjustment | HR requested position label moved closer to signature area | ID layout positioning adjusted |
| Manual Name Entry Errors | HR observed auto-linking names from Lark caused frequent errors | Manual name input retained with clear input instructions |
| Temporary ID Expiration Rules | HR clarified Temporary IDs should not have expiration dates except for interns/freelancers | Expiration logic updated to apply only to interns and freelancers |
| Position Classification – "Others" | HR clarified "Others" should include Agents and Solutions | Logic updated to include Agents and Solutions under "Others" |
| Screenshot Restriction (Employee Side) | HR and supervisors suggested preventing screenshots during form filling | Screenshot restriction implemented at application and browser level |
| HR Dashboard Access | HR requested ability to take screenshots freely for reporting | Screenshot restrictions not enforced for HR users |
| POC Notifications | HR clarified specific individuals must receive POC notifications | POC notification requirements noted for targeted routing |
| Missing Location Field | HR pointed out form lacked location/branch field | Mandatory Location/Branch field added |
| Barcode Content | HR requested removal of numeric values alongside barcodes | Barcode rendering updated to display barcode only |
| Outfit Guidelines (CEO Feedback) | CEO suggested modernizing attire guidelines | AI prompt guidelines updated for modern, professional attire |
| PDF Download Concerns | HR suggested removing "Download PDF" button; IDs should be sent directly to POCs | PDF download deprioritized; IDs generated and sent directly via email/Lark |
| Facial Expression Requirement | HR specified mouths should be closed in ID photos | AI prompt constraints adjusted to enforce closed-mouth expressions |

---

## 19. Frequently Asked Questions

### 19.1 End User (Employee) FAQs

**Q1. Who can use the Employee ID Automation system?**
The system can be used by employees who are required to request or update their company ID. Access is limited to authorized users via Lark SSO.

**Q2. How do I submit an ID request?**
Employees submit an ID request by completing the online form, providing required personal details, uploading a photo and signature, and reviewing the live ID preview before submission.

**Q3. Do I need to edit or resize my photo before uploading?**
No. The system automatically enhances the uploaded photo and removes the background to meet ID photo standards.

**Q4. Can I preview my ID before submitting the form?**
Yes. A real-time ID preview is available while filling out the form.

**Q5. Can I edit my submission after it has been sent?**
Once submitted, the request is forwarded for HR review. Any required changes must be coordinated with HR.

**Q6. Will the system work on mobile devices?**
Yes. The system is responsive and can be accessed using both desktop and mobile web browsers.

### 19.2 HR User FAQs

**Q1. Who can access the HR Dashboard?**
Only authorized HR personnel are allowed to access the HR Dashboard. Authentication is required via password login.

**Q2. How does HR review employee ID requests?**
HR users can view submitted ID requests through the dashboard, review employee information, and proceed with approval or further processing.

**Q3. Can HR manage multiple ID requests at once?**
Yes. The HR Dashboard supports bulk actions including Approve All Rendered and Send All to POCs.

**Q4. Where is employee data stored after submission?**
Employee data is stored in Supabase (PostgreSQL) when configured; otherwise, SQLite fallback is used. Data is also synced to Lark Bitable.

**Q5. What happens if an external integration fails?**
The system continues to operate normally. Optional integrations that become unavailable are handled gracefully without blocking the core flow.

---

## 20. In Scope

### 20.1 Functional Scope
- Submission of Employee ID requests through a centralized web-based form
- Collection of required employee information (full name, position, department, photo, signature)
- Automatic validation of required form fields prior to submission
- Real-time ID preview that updates dynamically based on user inputs
- AI-assisted image enhancement to standardize employee photos
- Automated background removal for uploaded or generated photos
- Generation of a standardized digital ID layout based on approved templates
- Storage of employee submissions for tracking and review
- Status tagging of submissions (Reviewing, Rendered, Approved, Sent to POC, Completed, Removed)
- Controlled access for HR personnel to review employee ID requests
- HR capability to view, manage, and process multiple ID requests
- Export of individual or multiple ID records for operational use

### 20.2 Technical Scope
- Backend application built using FastAPI (Python)
- Frontend interface implemented using HTML, CSS, JavaScript
- Local database support (SQLite) for development and testing
- Cloud-compatible deployment using Vercel serverless infrastructure
- Secure image storage using Cloudinary
- Integration with BytePlus Seedream for AI image generation
- Optional integration with Google Sheets for data sync
- Environment-based configuration using environment variables
- Logging and error-handling mechanisms for operational visibility

### 20.3 Security and Access Scope
- Session-based JWT authentication for HR access
- Restricted HR Dashboard access based on authorized credentials
- Controlled exposure of employee data to authorized roles only
- Secure handling of uploaded images and personal information
- Screenshot protection on employee-facing pages

### 20.4 User Scope
- End Users (Employees) submitting ID requests
- HR Users responsible for reviewing and approving ID requests

---

## 21. Out of Scope

### 21.1 Functional Exclusions
- Physical printing and distribution of employee ID cards
- Issuance, tracking, or lifecycle management of physical ID hardware
- Automatic deactivation or revocation of employee IDs upon resignation/termination
- Payroll, attendance, or timekeeping integration
- Biometric authentication (fingerprint, facial recognition for access control)
- Real-time synchronization with enterprise HR systems beyond configured integrations
- Automated approval logic without human HR review
- Employee role-based permission management beyond defined HR access

### 21.2 Technical Exclusions
- Custom mobile application development (Android or iOS)
- Offline system usage or local-first synchronization
- High-availability clustering or multi-region redundancy
- Performance load testing beyond development validation
- Data migration from legacy HR systems
- Automated database failover or disaster recovery infrastructure
- Long-term archival or cold storage management
- Custom analytics dashboards outside the HR portal

### 21.3 Operational and Support Exclusions
- 24/7 system monitoring or on-call production support
- Dedicated help desk or ticketing system integration
- End-user training programs or formal onboarding materials
- SLA-backed uptime guarantees
- Automated incident response or escalation workflows
- Ongoing system administration beyond basic configuration

### 21.4 Third-Party and Cost Exclusions
- Subscription costs for third-party services beyond free or trial tiers
- Licensing fees for paid AI, storage, or database platforms
- Vendor support agreements
- Procurement or management of external infrastructure
- Future pricing changes of integrated services

---

## 22. Discrepancies and Suggestions

### 22.1 Discrepancies Between Documentation and Codebase

The following discrepancies were identified after cross-referencing the V1.4 documentation with the current state of the codebase:

#### 1. Additional Database Tables Not Documented

**Issue**: The documentation (Section 10) only describes two tables — `employees` and `security_events`. The codebase and `supabase_setup.sql` include two additional tables:
- **`oauth_states`** — Stores OAuth PKCE state for Lark SSO in serverless environments
- **`headshot_usage`** — Tracks per-user AI headshot generation count for rate limiting (5/user)

**Recommendation**: Add these tables to the Database Structure section of the documentation.

#### 2. Status Flow Includes "Rendered" State

**Issue**: The documentation describes the status flow as `Reviewing → Approved → Sent to POC → Completed`, but the codebase includes an additional intermediate state: **`Rendered`** (between Reviewing and Approved). The `supabase_setup.sql` constraint confirms: `Reviewing | Rendered | Approved | Sent to POC | Completed | Removed`.

**Status**: This MD file already reflects the correct 6-state flow from the codebase.

#### 3. Dual Lark App Configuration (SPMC vs SPMA)

**Issue**: The documentation does not explicitly describe the **dual Lark app configuration** that exists in the codebase. The system has separate credentials, Bitable tables, and submission flows for **SPMC** and **SPMA** (including `LARK_APP_ID_SPMA`, `LARK_APP_SECRET_SPMA`, `LARK_BITABLE_ID_SPMA`, `LARK_TABLE_ID_SPMA`). There are separate submission endpoints: `POST /submit` (SPMC) and `POST /submit-spma` (SPMA/Legal Officer).

**Recommendation**: Document the dual Lark app configuration and the distinction between SPMC and SPMA submission flows.

#### 4. HR Authentication Mechanism

**Issue**: The documentation (Section 9.1) describes HR authentication as "Session-based Authentication (Custom)" with session cookies and bcrypt. The codebase actually uses **custom JWT (HS256) tokens** stored in session cookies — not traditional server-side sessions. This is critical because the system runs on serverless Vercel, where in-memory sessions would not persist across function invocations.

**Recommendation**: Clarify that HR authentication uses JWT-based stateless tokens (not server-side sessions) for serverless compatibility.

#### 5. HR Access Control via Lark Contact API

**Issue**: The codebase includes `is_descendant_of_people_support()` in `lark_auth_service.py`, which validates that HR users belong to the People Support department hierarchy via the Lark Contact API with a 30-minute cache. This enterprise-level access control mechanism is not documented.

**Recommendation**: Add this as an additional authentication layer in the documentation.

#### 6. Headshot Generation Rate Limiting

**Issue**: The documentation does not mention the **5 headshots per user rate limit** that is implemented in the codebase via the `headshot_usage` table and `check_headshot_limit()` function.

**Recommendation**: Document the rate limiting mechanism in the Features section.

#### 7. Bulk Card Router Bot Script

**Issue**: The codebase includes `scripts/bulk_card_router_bot.py` (936 lines), a production CLI tool for bulk ID card routing via Lark Bot. This tool fetches records from Lark Bitable, resolves printer branches using haversine proximity, groups records by branch, and sends bot messages with ID card links. This is not documented.

**Recommendation**: Add a section documenting the Bulk Card Router Bot as an operational tool.

#### 8. QR Code and vCard Generation on ID Card Back

**Issue**: The documentation mentions emergency contact information on the ID card backside, but does not describe the **dynamic URL generation** (`www.okpo.com/spm/{name}`) or **vCard QR code** generation that is implemented in the frontend code.

**Recommendation**: Document the QR code and vCard features on the ID card backside.

#### 9. Barcode Service Implementation Details

**Issue**: The documentation mentions `barcodeAPI.org` for barcode generation but the gallery JavaScript (`gallery.js`) also references **QuickChart.io** for barcode URLs (`getBarcodeUrl()` function), suggesting a different or additional barcode service may be used in the gallery view.

**Recommendation**: Clarify which barcode service is used in each context (employee form vs gallery view).

#### 10. `mangum` Dependency

**Issue**: `requirements.txt` includes `mangum==0.17.0` (ASGI adapter for AWS Lambda), but `vercel.json` uses Vercel's native Python builder and `api/index.py` does not use Mangum. This appears to be an unused dependency.

**Recommendation**: Verify if `mangum` is needed or can be removed from `requirements.txt`.

### 22.2 Suggestions for Documentation Improvement

1. **Add an Environment Variables Reference Table**: Create a comprehensive table listing all environment variables with their service associations, whether they are required or optional, and their format/expected values. This exists partially in Section 8 but should be consolidated.

2. **Document the Diagnostic Scripts**: The `scripts/` directory contains useful diagnostic tools (`diagnose_ai_preview.py`, `diagnose_lark.py`, `test_routing_logic.py`) that are not mentioned in the documentation. These are valuable for troubleshooting.

3. **Add ID Card Template Specifications**: Document the exact ID card dimensions, DPI, and JPEG quality settings used in PDF generation (Portrait: 2.13"×3.33", Landscape: 3.33"×2.13", 300 DPI, JPEG quality 0.92–0.95).

4. **Document the Upload-Before-Download PDF Policy**: The codebase enforces that PDFs must be successfully uploaded to Cloudinary and Lark Bitable before local download is permitted. This is an important operational behavior.

5. **Clarify the "Removed" Status**: The documentation mentions status states but should explicitly note that `Removed` is a soft-delete mechanism — records are not truly deleted from the database.

6. **Document sessionStorage Caching**: The HR Dashboard and Gallery share a `sessionStorage` cache (`hrEmployeeDataCache`) with a 5-minute TTL if the browser already has loaded data, improving performance for Vercel cold starts. Document this as an optimization.

7. **Add POC Test Mode Documentation**: The codebase supports a test mode for POC routing via `POC_TEST_MODE` and `POC_TEST_RECIPIENT_EMAIL` environment variables. This is useful for testing without sending real notifications.

8. **Document the Vercel Cold-Start Resilience Pattern**: The frontend implements specific patterns for Vercel cold-start handling (20-second initial timeout, 15-second retry timeout, 2 retries). This is a key architectural decision worth documenting.
