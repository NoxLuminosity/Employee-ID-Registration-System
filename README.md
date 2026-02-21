# Employee ID Registration System

A full-stack employee ID card registration and management system built with FastAPI and deployed on Vercel. Employees register through a Lark SSO-authenticated portal, and HR manages approvals, ID card generation, and distribution via an admin dashboard.

## Features

- **Lark SSO Authentication** — OAuth 2.0 PKCE login for all users via Lark/Feishu
- **AI Headshot Generation** — Professional headshot generation using BytePlus Seedream with outfit selection
- **Background Removal** — Remove.bg and Cloudinary AI photo background removal
- **ID Card Rendering** — Front/back ID card generation with barcode and QR codes (QuickChart.io)
- **HR Dashboard** — Employee review, approval, rendering, and status tracking
- **ID Gallery** — Visual gallery of generated ID cards with PDF export
- **POC Routing** — Automated ID card distribution to branch Points of Contact via Lark DM
- **Lark Bitable Integration** — Employee records stored and synced in Lark Bitable
- **SPMA Multi-Table Support** — Separate registration flow for SPMA employees
- **Screenshot Protection** — Client-side screenshot/screen-recording detection on employee forms
- **Usage Analytics** — AI generation quota tracking and rate limit management

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI 0.109.0 |
| **Frontend** | Jinja2 templates, vanilla JavaScript, CSS |
| **Database** | Supabase (PostgreSQL) with SQLite fallback |
| **Auth** | Lark OAuth 2.0 PKCE + JWT sessions |
| **Image Storage** | Cloudinary |
| **AI Generation** | BytePlus Seedream (headshots) |
| **Background Removal** | Remove.bg API |
| **Barcode/QR** | QuickChart.io (client-side) |
| **Messaging** | Lark IM (interactive cards, file messages) |
| **Deployment** | Vercel Serverless |

## Project Structure

```
├── api/
│   └── index.py                    # Vercel serverless entry point
├── app/
│   ├── main.py                     # FastAPI app, middleware, page routes
│   ├── auth.py                     # JWT session management
│   ├── database.py                 # Supabase/SQLite data layer
│   ├── validators.py               # Form validation
│   ├── transaction_manager.py      # ACID transaction manager
│   ├── workflow_cache.py           # Multi-layer caching
│   ├── utils.py                    # Shared utilities
│   ├── routes/
│   │   ├── auth.py                 # Lark OAuth routes
│   │   ├── employee.py             # Employee registration routes
│   │   ├── hr.py                   # HR dashboard & API routes
│   │   └── security.py             # Security event logging
│   ├── services/
│   │   ├── lark_service.py         # Lark Bitable CRUD & IM messaging
│   │   ├── lark_auth_service.py    # Lark OAuth 2.0 flow
│   │   ├── cloudinary_service.py   # Image upload/delete
│   │   ├── seedream_service.py     # BytePlus AI headshot generation
│   │   ├── background_removal_service.py  # Remove.bg integration
│   │   └── poc_routing_service.py  # Branch-to-POC distance routing
│   ├── static/                     # CSS, JavaScript, images
│   └── templates/                  # Jinja2 HTML templates
├── scripts/                        # Utility & diagnostic scripts
├── tests/                          # Integration & unit tests
├── credentials/                    # Service account credentials (gitignored)
├── requirements.txt                # Python dependencies
├── vercel.json                     # Vercel deployment config
├── supabase_setup.sql              # Database schema
└── .env.example                    # Environment variable template
```

## Getting Started

### Prerequisites

- Python 3.11+
- A [Lark/Feishu](https://open.larksuite.com/) app (App ID + Secret)
- [Cloudinary](https://cloudinary.com/) account
- [BytePlus](https://www.byteplus.com/) API key (for AI headshots)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/Employee-ID-Registration-System.git
   cd Employee-ID-Registration-System
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Linux/Mac
   .venv\Scripts\activate          # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your credentials. Required variables:
   - `LARK_APP_ID` / `LARK_APP_SECRET` — Lark app credentials
   - `LARK_BITABLE_ID` / `LARK_TABLE_ID` — Lark Bitable configuration
   - `LARK_REDIRECT_URI` — OAuth callback URL
   - `TARGET_LARK_DEPARTMENT_ID` — Department for HR portal access control
   - `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET`
   - `BYTEPLUS_API_KEY` — BytePlus Seedream API key

5. **Run locally**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Open [http://localhost:8000](http://localhost:8000)

### Database Setup

**Option A: SQLite (default, no config needed)**
Automatically creates `database.db` in the project root.

**Option B: Supabase (production)**
1. Create a Supabase project
2. Run the schema in `supabase_setup.sql`
3. Set `SUPABASE_URL` and `SUPABASE_KEY` in `.env`

## Deployment (Vercel)

The app is configured for Vercel serverless deployment:

```bash
vercel --prod
```

Set all environment variables in the Vercel dashboard. The `vercel.json` routes all traffic through `api/index.py`.

## API Overview

| Endpoint Group | Routes | Description |
|---------------|--------|-------------|
| `/` | 3 | Landing page, logout, registration form |
| `/auth/*` | 5 | Lark OAuth login/callback/logout |
| `/submit`, `/submit-spma` | 2 | Employee registration submission |
| `/generate-headshot` | 1 | AI headshot generation |
| `/remove-background` | 1 | Background removal |
| `/hr/*` | 20 | HR dashboard, gallery, employee CRUD, POC distribution |
| `/api/security/*` | 4 | Screenshot protection event logging |

## External Services

| Service | Usage |
|---------|-------|
| **Lark/Feishu** | SSO auth, Bitable records, IM messaging |
| **Cloudinary** | Image upload, storage, AI background removal |
| **BytePlus Seedream** | AI professional headshot generation |
| **Remove.bg** | Photo background removal |
| **QuickChart.io** | Barcode & QR code generation (client-side) |
| **Supabase** | PostgreSQL database & OAuth state management |

## License

This project is proprietary and confidential.
