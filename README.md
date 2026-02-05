# Employee ID Registration System

A full-stack employee ID registration and management system with AI-powered headshot generation, background removal, and HR dashboard. Built with FastAPI and integrates with Lark Bitable for enterprise data sync.

## Features

### Employee Portal
- **AI Headshot Generation** - Upload a photo and get a professional AI-generated headshot using BytePlus Seedream API
- **Background Removal** - Automatic background removal using Cloudinary AI or Remove.bg
- **Digital Signature** - Canvas-based signature pad with transparent background export
- **Live ID Preview** - Real-time ID card preview as you fill the form
- **Lark Authentication** - Mandatory Lark SSO for all access

### HR Dashboard  
- **Lark SSO Authentication** - Secure login via Lark OAuth
- **Employee Management** - View, approve, and manage ID card applications
- **ID Gallery** - Visual gallery of rendered and approved ID cards
- **PDF Generation** - Generate printable ID card PDFs with QR codes
- **POC Routing** - Automatic routing to nearest printing POC using haversine distance
- **Lark Bitable Sync** - Real-time sync of employee data to Lark Bitable

## Tech Stack

- **Backend**: FastAPI (Python 3.9+)
- **Database**: Supabase PostgreSQL (production) / SQLite (local)
- **Frontend**: Vanilla JavaScript, Jinja2 templates
- **Image Storage**: Cloudinary
- **AI Services**: BytePlus Seedream (headshot), Cloudinary AI (background removal)
- **Integrations**: Lark Bitable, Google Sheets (optional)

## Quick Start

### Prerequisites
- Python 3.9+
- Lark Developer App credentials
- Cloudinary account
- BytePlus API access

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd Employee-ID-Registration-System

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

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
- ID Gallery: http://localhost:8000/gallery

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
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google service account JSON string | - |
| `GOOGLE_SPREADSHEET_ID` | Google Sheets spreadsheet ID | - |
| `HR_USERS` | Legacy HR credentials (format: `user1:pass1,user2:pass2`) | - |
| `JWT_SECRET` | Session encryption secret | Generated |
| `POC_TEST_MODE` | Send POC messages to test recipient | `true` |
| `POC_TEST_RECIPIENT_EMAIL` | Test mode recipient email | - |

### SPMA-Specific (Multi-Table)

| Variable | Description |
|----------|-------------|
| `LARK_APP_ID_SPMA` | SPMA Lark App ID |
| `LARK_APP_SECRET_SPMA` | SPMA Lark App Secret |
| `LARK_BITABLE_ID_SPMA` | SPMA Bitable App Token |
| `LARK_TABLE_ID_SPMA` | SPMA Bitable Table ID |

## Project Structure

```
├── api/
│   └── index.py              # Vercel serverless entry point
├── app/
│   ├── main.py               # FastAPI application
│   ├── auth.py               # Session management
│   ├── database.py           # SQLite/Supabase database
│   ├── models.py             # Pydantic models
│   ├── routes/
│   │   ├── auth.py           # Lark OAuth routes
│   │   ├── employee.py       # Employee registration
│   │   ├── hr.py             # HR dashboard API
│   │   └── security.py       # Security endpoints
│   ├── services/
│   │   ├── lark_service.py   # Lark Bitable integration
│   │   ├── lark_auth_service.py  # Lark OAuth
│   │   ├── cloudinary_service.py # Image upload/processing
│   │   ├── seedream_service.py   # AI headshot generation
│   │   ├── poc_routing_service.py # POC branch routing
│   │   └── google_sheets.py      # Google Sheets sync
│   ├── static/               # CSS, JS, images
│   └── templates/            # Jinja2 HTML templates
├── scripts/
│   ├── bulk_card_router_bot.py   # Batch POC messaging bot
│   ├── diagnose_lark.py          # Lark config diagnostics
│   └── diagnose_ai_preview.py    # AI service diagnostics
├── tests/                    # Test files
├── credentials/              # Service account files (gitignored)
├── requirements.txt          # Python dependencies
├── vercel.json               # Vercel deployment config
├── supabase_setup.sql        # Production database schema
└── SPMA_LARK_SETUP.md        # Multi-table setup guide
```

## Deployment

### Vercel

1. Push code to GitHub
2. Connect repository to Vercel
3. Add environment variables in Vercel dashboard
4. Deploy

The `vercel.json` is pre-configured for deployment.

### Production Database (Supabase)

1. Create Supabase project at https://supabase.com
2. Run `supabase_setup.sql` in SQL Editor
3. Set `SUPABASE_URL` and `SUPABASE_KEY` in environment

## Troubleshooting

### Common Issues

1. **"TARGET_LARK_DEPARTMENT_ID not set"**: Set this env var to your Lark org's Department ID for access control.

2. **Email lookup fails**: Ensure the email exists in your Lark organization. Use actual Lark account emails.

3. **AI headshot not generating**: Check `BYTEPLUS_API_KEY` is valid. Run `python scripts/diagnose_ai_preview.py` to test.

4. **Lark Bitable sync fails**: Run `python scripts/diagnose_lark.py` to check table configuration.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/bulk_card_router_bot.py` | Batch send ID cards to POCs via Lark messages |
| `scripts/diagnose_lark.py` | Check Lark Bitable field configuration |
| `scripts/diagnose_ai_preview.py` | Test BytePlus/Cloudinary connectivity |

## License

MIT License
