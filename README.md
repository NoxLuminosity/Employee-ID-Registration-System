# Employee ID Registration System

<p align="center">
  <b>Enterprise Employee ID Card Automation Platform</b><br>
  FastAPI • BytePlus AI • Cloudinary • Lark Integration
</p>

---

## Overview

A production-grade employee ID card automation system that transforms the manual ID creation process from days to hours. The system handles the complete ID card lifecycle:

**Employee Self-Service** → **AI Photo Generation** → **HR Review** → **Automatic POC Routing** → **Print-Ready Delivery**

### What It Solves

| Before (Manual) | After (Automated) |
|-----------------|-------------------|
| 3-7 days turnaround | Same-day completion |
| 40-60 min HR time per employee | < 5 min per employee |
| ~10% routing errors | 0% errors |
| No visibility for management | Real-time Lark Bitable dashboard |
| 2-3 FTEs on ID coordination | < 1 FTE (bulk actions) |

---

## Features

### Employee Portal

| Feature | Description |
|---------|-------------|
| **Lark SSO** | OAuth 2.0 + PKCE authentication validates employee organization |
| **AI Headshot Generation** | 8 professional attire styles via BytePlus Seedream (4 male, 4 female) |
| **Background Removal** | Cloudinary AI automatic transparent background |
| **Digital Signature** | HTML5 Canvas with transparent PNG export |
| **Live ID Preview** | Real-time card preview updates as form is filled |
| **Auto-Fill** | Name and email populated from Lark profile |

### HR Dashboard

| Feature | Description |
|---------|-------------|
| **Department-Based Access** | Only People Support department members can access |
| **Employee Table** | Full-featured data table with search and filters |
| **Visual ID Gallery** | Preview actual ID cards with barcode/QR codes |
| **PDF Generation** | Print-ready PDFs at 2.13" × 3.33" (300 DPI) |
| **Bulk Actions** | "Approve All Rendered" and "Send All to POCs" |
| **POC Routing** | Automatic nearest-branch calculation (haversine) |
| **Lark Messaging** | Direct messages to POCs with PDF attachments |

### ID Card Generation

| Component | Technology |
|-----------|------------|
| **Barcode** | Code 128 via QuickChart.io (alphanumeric support) |
| **QR Code (Back)** | vCard format with employee contact info |
| **Employee URL QR** | Links to internal profile |
| **PDF Rendering** | Client-side html2canvas + jsPDF |
| **Formats** | SPMC (portrait), SPMA/Field Officer (landscape) |

### Enterprise Integration

| Integration | Purpose |
|-------------|---------|
| **Lark Bitable** | Real-time data sync, status tracking, audit trail |
| **Lark IM** | Automated POC notifications with PDF links |
| **Lark Contact API** | Department hierarchy validation |
| **Cloudinary** | Image/PDF CDN with background removal |
| **BytePlus Seedream** | AI corporate headshot generation |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | FastAPI (Python 3.11+) | API, routing, business logic |
| **Frontend** | Vanilla JS, Jinja2 | UI templates |
| **Database** | Supabase PostgreSQL | Production data |
| **Dev Database** | SQLite | Local development |
| **Image CDN** | Cloudinary | Photo/PDF storage + AI processing |
| **AI Headshots** | BytePlus Seedream | Professional photo generation |
| **Barcodes/QR** | QuickChart.io | Code 128 + vCard QR |
| **Auth** | Lark OAuth 2.0 + PKCE | SSO + JWT sessions |
| **Sync** | Lark Bitable | Enterprise visibility |
| **Messaging** | Lark IM API | POC notifications |
| **Deployment** | Vercel Serverless | Zero-ops hosting |

---

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     EMPLOYEE PORTAL                              │
│  1. Lark Login → 2. Upload Photo → 3. Generate AI Headshot     │
│  4. Fill Form (live preview) → 5. Sign → 6. Submit             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     HR DASHBOARD                                 │
│  7. View in Table → 8. Preview in Gallery → 9. Download PDF    │
│  10. Approve (individual or bulk)                               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     POC DELIVERY                                 │
│  11. Calculate nearest POC (haversine) → 12. Send Lark message │
│  13. POC downloads PDF → 14. Prints ID → 15. Mark Complete     │
└─────────────────────────────────────────────────────────────────┘
```

### Status Flow

```
Reviewing → Rendered → Approved → Sent to POC → Completed
                                              ↳ Removed (soft delete)
```

---

## POC Branches

The system routes ID cards to the nearest Point of Contact (POC) branch for printing.

### POC Branches (15 with printers)

| Branch | Region |
|--------|--------|
| San Carlos | Negros |
| Pagadian City | Zamboanga Peninsula |
| Zamboanga City | Zamboanga Peninsula |
| Malolos City | Central Luzon |
| San Fernando City | Central Luzon |
| Cagayan De Oro | Northern Mindanao |
| Tagum City | Davao Region |
| Davao City | Davao Region |
| Cebu City | Central Visayas |
| Batangas | Southern Luzon |
| General Santos City | SOCCSKSARGEN |
| Bacolod | Western Visayas |
| Ilo-Ilo | Western Visayas |
| Quezon City | Metro Manila |
| Calamba City | CALABARZON |

### Non-POC Branches (40+)

All other locations are routed to the nearest POC using haversine distance calculation based on GPS coordinates.

---

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
├── scripts/
│   ├── bulk_card_router_bot.py     # Batch POC messaging bot
│   ├── diagnose_lark.py            # Lark config diagnostics
│   ├── diagnose_ai_preview.py      # AI service diagnostics
│   └── test_routing_logic.py       # POC routing verification
├── tests/                          # Integration & unit tests
├── credentials/                    # Service account credentials (gitignored)
├── requirements.txt                # Python dependencies
├── vercel.json                     # Vercel deployment config
├── supabase_setup.sql              # Database schema
├── SPMA_LARK_SETUP.md              # Multi-table setup guide
└── .env.example                    # Environment variable template
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- [Lark/Feishu](https://open.larksuite.com/) Developer App credentials
- [Cloudinary](https://cloudinary.com/) account
- [BytePlus](https://www.byteplus.com/) API access

### Installation

```bash
# Clone the repository
git clone https://github.com/NoxLuminosity/Employee-ID-Registration-System.git
cd Employee-ID-Registration-System

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys

# Run development server
uvicorn app.main:app --reload --port 8000
```

### Access URLs

- Landing Page: http://localhost:8000
- Employee Registration: http://localhost:8000/apply
- HR Dashboard: http://localhost:8000/hr/dashboard
- ID Gallery: http://localhost:8000/hr/gallery

### Database Setup

**Option A: SQLite (default, no config needed)**
Automatically creates `database.db` in the project root.

**Option B: Supabase (production)**
1. Create a Supabase project at https://supabase.com
2. Run `supabase_setup.sql` in SQL Editor
3. Set `SUPABASE_URL` and `SUPABASE_KEY` in `.env`

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `LARK_APP_ID` | Lark App ID for authentication |
| `LARK_APP_SECRET` | Lark App Secret |
| `LARK_BITABLE_ID` | Lark Bitable App Token |
| `LARK_TABLE_ID` | Lark Bitable Table ID |
| `LARK_REDIRECT_URI` | OAuth callback URL (e.g., `https://yourdomain.com/lark/callback`) |
| `TARGET_LARK_DEPARTMENT_ID` | Lark Department ID for org validation |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |
| `BYTEPLUS_API_KEY` | BytePlus Seedream API key |
| `BYTEPLUS_MODEL` | BytePlus model (default: `seedream-4-5-251128`) |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | SQLite fallback |
| `SUPABASE_KEY` | Supabase service key | SQLite fallback |
| `REMOVEBG_API_KEY` | Remove.bg API key | Uses Cloudinary |
| `HR_USERS` | Legacy HR credentials (format: `user1:pass1,user2:pass2`) | — |
| `JWT_SECRET` | Session encryption secret | Generated |
| `POC_TEST_MODE` | Send POC messages to test recipient | `true` |
| `POC_TEST_RECIPIENT_EMAIL` | Test mode recipient email | — |

### SPMA Multi-Table (Optional)

| Variable | Description |
|----------|-------------|
| `LARK_APP_ID_SPMA` | SPMA Lark App ID |
| `LARK_APP_SECRET_SPMA` | SPMA Lark App Secret |
| `LARK_BITABLE_ID_SPMA` | SPMA Bitable App Token |
| `LARK_TABLE_ID_SPMA` | SPMA Bitable Table ID |

---

## API Endpoints

### Public Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Landing page |
| GET | `/apply` | Employee application form |
| GET | `/logout` | Clear session and redirect |

### Auth Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/login` | Lark SSO login page |
| GET | `/auth/lark/login` | Initiate Lark OAuth flow |
| GET | `/auth/lark/callback` | OAuth callback handler |
| GET | `/auth/logout` | Clear auth session |
| GET | `/auth/me` | Current user info |

### Employee Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/headshot-usage` | AI headshot generation quota |
| POST | `/generate-headshot` | Generate AI headshot from photo |
| POST | `/remove-background` | Remove photo background |
| GET | `/background-removal-status` | BG removal job status |
| POST | `/submit` | Submit employee registration |
| POST | `/submit-spma` | Submit SPMA registration |

### HR Routes (Authenticated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/hr/dashboard` | HR management dashboard |
| GET | `/hr/gallery` | ID card gallery |
| GET | `/hr/login` | HR login page |
| POST | `/hr/login` | HR password authentication |
| GET | `/hr/logout` | HR logout |
| GET | `/hr/api/employees` | Fetch all employees |
| GET | `/hr/api/employees/{id}` | Fetch single employee |
| POST | `/hr/api/employees/{id}/approve` | Approve employee ID |
| POST | `/hr/api/employees/{id}/render` | Mark as rendered |
| POST | `/hr/api/employees/{id}/complete` | Mark as completed |
| POST | `/hr/api/employees/{id}/send-to-poc` | Send to POC |
| POST | `/hr/api/employees/{id}/remove-background` | HR background removal |
| POST | `/hr/api/employees/{id}/upload-pdf` | Upload PDF to Cloudinary |
| POST | `/hr/api/employees/{id}/upload-card-images` | Upload card PNGs |
| GET | `/hr/api/employees/{id}/download-id` | Download PDF proxy |
| POST | `/hr/api/send-all-to-pocs` | Bulk send to POCs |
| DELETE | `/hr/api/employees/{id}` | Delete employee |
| GET | `/hr/api/stats` | Dashboard statistics |
| GET | `/hr/api/usage-summary` | AI usage stats |
| POST | `/hr/api/reset-rate-limit/{id}` | Reset user AI quota |
| POST | `/hr/api/reset-all-rate-limits` | Reset all AI quotas |

### Security Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/security/log-attempt` | Log screenshot attempt |
| GET | `/api/security/events` | List security events |
| GET | `/api/security/events/by-user/{username}` | User's security events |
| GET | `/api/security/stats` | Security statistics |

### Debug Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/hr/api/debug` | Environment/config info |
| GET | `/hr/api/debug/lark` | Lark configuration debug |

---

## Security Features

### Authentication

| Feature | Implementation |
|---------|----------------|
| **Employee SSO** | Lark OAuth 2.0 with PKCE |
| **HR Access Control** | Department hierarchy validation (People Support only) |
| **Session Management** | JWT tokens (serverless-compatible) |
| **Password Hashing** | bcrypt with 72-byte handling |

### Safety Mechanisms

| Feature | Description |
|---------|-------------|
| **Test Mode** | `POC_TEST_MODE=true` redirects all POC messages to test recipient |
| **Backend Enforcement** | Test mode is server-side only, cannot be bypassed by client |
| **Status Validation** | Only valid status transitions allowed |
| **Soft Delete** | "Removed" status preserves data for audit |
| **Retry Logic** | 3 attempts with 0.5s delay for Lark operations |

### Security Headers

- Content Security Policy (CSP)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Strict-Transport-Security (HSTS)

---

## Error Handling

### Retry Logic

```python
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 0.5

# Lark Bitable operations retry automatically
# Cloudinary uploads return explicit errors
# PDF URLs are verified accessible before saving
```

### Failure Scenarios

| Scenario | Behavior |
|----------|----------|
| AI generation fails | Fallback to original photo with warning |
| Cloudinary upload fails | Error returned, user can retry |
| Lark Bitable update fails | 3 retries, local DB still updated |
| POC message send fails | Error returned, status not changed |
| PDF URL inaccessible | Upload blocked until resolved |

### Session Caching

Data is cached in browser `sessionStorage` (5-minute duration) to survive Vercel cold starts.

---

## AI Headshot Styles

The system offers 8 professional attire options:

### Male Styles
1. **Navy Blue Polo** — Crisp navy polo, relaxed fit
2. **White Button-Down** — Classic long-sleeve with subtle check
3. **Light Gray Sweater** — V-neck over white undershirt
4. **Dark Green Polo** — Forest green, modern fit

### Female Styles
1. **Cream Silk Blouse** — Soft cream with subtle draping
2. **Navy Tailored Blazer** — Structured jacket, white top
3. **Soft Peach Blouse** — Round collar, flattering cut
4. **Light Gray Sweater** — Fine-knit, V-neck style

All styles preserve the employee's original facial features, hairstyle, and identity.

---

## Deployment (Vercel)

1. Push code to GitHub
2. Connect repository to Vercel
3. Add environment variables in Vercel dashboard
4. Deploy

```bash
vercel --prod
```

The `vercel.json` routes all traffic through `api/index.py`.

---

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_lark.py

# Run with verbose output
pytest tests/ -v
```

### Test Files

| File | Purpose |
|------|---------|
| `test_cloudinary_only.py` | Cloudinary upload tests |
| `test_dashboard_api.py` | HR API endpoint tests |
| `test_e2e_id_card_flow.py` | End-to-end workflow tests |
| `test_id_card_upload.py` | PDF upload tests |
| `test_lark.py` | Lark integration tests |

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "TARGET_LARK_DEPARTMENT_ID not set" | Set to your Lark org's People Support Department ID |
| Email lookup fails | Ensure email exists in Lark organization |
| AI headshot not generating | Check `BYTEPLUS_API_KEY` validity |
| Lark Bitable sync fails | Run `python scripts/diagnose_lark.py` |
| Session lost after refresh | Check JWT_SECRET is set (required for Vercel) |
| POC message not received | Check `POC_TEST_MODE=false` for production |

### Diagnostic Scripts

```bash
# Check Lark Bitable configuration
python scripts/diagnose_lark.py

# Check AI services
python scripts/diagnose_ai_preview.py

# Test POC routing logic
python scripts/test_routing_logic.py
```

---

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `bulk_card_router_bot.py` | Batch send ID cards to POCs | `python scripts/bulk_card_router_bot.py` |
| `diagnose_lark.py` | Check Lark Bitable fields | `python scripts/diagnose_lark.py` |
| `diagnose_ai_preview.py` | Test BytePlus/Cloudinary | `python scripts/diagnose_ai_preview.py` |
| `test_routing_logic.py` | Verify POC routing | `python scripts/test_routing_logic.py` |

---

## Documentation

| Document | Description |
|----------|-------------|
| [SPMA_LARK_SETUP.md](SPMA_LARK_SETUP.md) | Multi-table Lark Bitable setup guide |
| [supabase_setup.sql](supabase_setup.sql) | Production database schema |

---

## License

MIT License

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

<p align="center">
  <b>Built by People Support Engineering</b><br>
  Transforming ID Card Creation from Days to Hours
</p>
