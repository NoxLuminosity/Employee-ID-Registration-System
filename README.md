# Employee ID Registration System

A full-stack employee ID registration system with AI-powered headshot generation, background removal, and HR management dashboard.

## 🌟 Features

### Employee Portal
- **AI Headshot Generation**: Upload a photo and get a professional AI-generated headshot using BytePlus Seedream API
- **Background Removal**: Automatic background removal using Cloudinary AI or Remove.bg
- **Digital Signature**: Canvas-based signature pad with transparent background export
- **Live ID Preview**: Real-time ID card preview as you fill the form
- **Form Validation**: Client-side and server-side validation

### HR Dashboard
- **Session-Based Authentication**: Secure login with bcrypt password hashing
- **Employee Management**: View, approve, and manage ID card applications
- **Background Removal**: One-click background removal for employee photos
- **ID Gallery**: Visual gallery of approved and completed ID cards
- **Google Sheets Sync**: Automatic sync of employee data to Google Sheets
- **CSV Export**: Export employee data to CSV

## 🚀 Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: Supabase PostgreSQL (production) / SQLite (local development)
- **Frontend**: Vanilla JavaScript, CSS
- **Templates**: Jinja2
- **Image Storage**: Cloudinary
- **AI Services**: 
  - BytePlus Seedream (headshot generation)
  - Cloudinary AI / Remove.bg (background removal)
- **Integrations**:
  - Google Sheets (data sync)
  - Lark Bitable (optional)

## 🗄️ Database Setup (Supabase)

For persistent data on Vercel, the system uses Supabase PostgreSQL.

### Setting up Supabase

1. **Create a Supabase account** at https://supabase.com

2. **Create a new project** and note down:
   - Project URL (e.g., `https://xxxxx.supabase.co`)
   - Anon/Service key (found in Settings > API)

3. **Create the employees table**:
   - Go to SQL Editor in Supabase Dashboard
   - Run the script from `supabase_setup.sql`

4. **Add environment variables** in Vercel:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-service-role-key
   ```

### Local Development (SQLite)

For local development without Supabase, the system automatically falls back to SQLite. No configuration needed - just run the app and it will create a local `database.db` file.

## 📦 Installation

### Prerequisites
- Python 3.9+
- pip (Python package manager)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/NoxLuminosity/Employee-ID-Registration-System.git
   cd Employee-ID-Registration-System
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env with your API keys
   ```

5. **Run the development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the application**
   - Landing Page: http://localhost:8000
   - Employee Registration: http://localhost:8000/apply
   - HR Dashboard: http://localhost:8000/hr/dashboard

## ⚙️ Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | Yes (production) |
| `SUPABASE_KEY` | Supabase anon/service key | Yes (production) |
| `BYTEPLUS_API_KEY` | BytePlus Seedream API key for AI headshots | Yes |
| `BYTEPLUS_MODEL` | BytePlus model name (default: seedream-4-5-251128) | Yes |
| `BYTEPLUS_ENDPOINT` | BytePlus API endpoint | Yes |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | Yes |
| `CLOUDINARY_API_KEY` | Cloudinary API key | Yes |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | Yes |
| `REMOVEBG_API_KEY` | Remove.bg API key (optional) | No |
| `HR_USERS` | HR login credentials (format: user1:pass1,user2:pass2) | Yes |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | Path to Google service account JSON | No |
| `GOOGLE_SPREADSHEET_ID` | Google Spreadsheet ID for data sync | No |

## 📁 Project Structure

```
id-registration-system/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── auth.py              # HR authentication module
│   ├── database.py          # SQLite database with auto-migration
│   ├── models.py            # Pydantic models
│   ├── routes/
│   │   ├── employee.py      # Employee registration endpoints
│   │   └── hr.py            # HR dashboard endpoints
│   ├── services/
│   │   ├── cloudinary_service.py      # Image upload & bg removal
│   │   ├── seedream_service.py        # AI headshot generation
│   │   ├── background_removal_service.py  # Remove.bg integration
│   │   ├── google_sheets.py           # Google Sheets sync
│   │   └── lark_service.py            # Lark Bitable integration
│   ├── static/
│   │   ├── styles.css       # Employee form styles
│   │   ├── app.js           # Employee form JavaScript
│   │   ├── landing.css      # Landing page styles
│   │   ├── landing.js       # Landing page animations
│   │   ├── dashboard.css    # HR dashboard styles
│   │   ├── dashboard.js     # HR dashboard logic
│   │   ├── gallery.css      # ID gallery styles
│   │   └── gallery.js       # ID gallery logic
│   └── templates/
│       ├── landing.html     # Role selection page
│       ├── form.html        # Employee registration form
│       ├── hr_login.html    # HR login page
│       ├── dashboard.html   # HR dashboard
│       └── gallery.html     # ID card gallery
├── credentials/             # Service account files (gitignored)
├── requirements.txt         # Python dependencies
├── vercel.json             # Vercel deployment config
├── .env.example            # Environment variables template
└── README.md
```

## 🔐 HR Dashboard Access

Default credentials (configurable via `HR_USERS` env var):
- Username: `admin`
- Password: `admin123`

**Important**: Change these credentials in production!

## 🚢 Deployment

### Vercel Deployment

1. Push your code to GitHub
2. Connect your repository to Vercel
3. Configure environment variables in Vercel dashboard
4. Deploy!

The `vercel.json` is pre-configured for seamless deployment.

### Environment Variables on Vercel

Add all required environment variables in the Vercel project settings under "Environment Variables".

## 🛠️ API Endpoints

### Employee Endpoints
- `POST /generate-headshot` - Generate AI headshot from uploaded photo
- `POST /remove-background` - Remove background from image
- `POST /submit` - Submit employee registration

### HR Endpoints
- `POST /hr/login` - HR authentication
- `GET /hr/logout` - Logout
- `GET /hr/api/employees` - Get all employees
- `POST /hr/api/employees/{id}/approve` - Approve application
- `POST /hr/api/employees/{id}/remove-background` - Remove photo background
- `DELETE /hr/api/employees/{id}` - Delete employee
- `POST /hr/api/sync-sheets` - Sync to Google Sheets

## 📄 License

MIT License - feel free to use and modify for your projects.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

Built with ❤️ using FastAPI and modern web technologies.
