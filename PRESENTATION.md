# HR ID Automation System
## Stakeholder Presentation

---

# Slide 1: Title

## HR ID Automation System
### Enterprise Employee ID Card Management

**People Support Engineering**  
**February 2026**

*Transforming ID Card Creation from Days to Hours*

---

# Slide 2: The Problem

## Manual Process Pain Points

### Before Automation:
- **Photo collection**: 1-2 days of email/chat back-and-forth
- **Photo editing**: 15 minutes per employee in Photoshop
- **ID design**: 10 minutes per card, inconsistent styling
- **Branch lookup**: Manual checking which POC prints which card
- **POC notification**: Individual messages via WhatsApp/Lark
- **Status tracking**: Spreadsheet chaos, no visibility

### Result:
- ⏱️ **3-7 business days** average turnaround
- ❌ **~10% routing errors** (wrong branch)
- 📊 **No real-time visibility** for management
- 👨‍💼 **2-3 HR FTEs** devoted to ID coordination

---

# Slide 3: The Solution

## Automated End-to-End System

### Self-Service Employee Portal
- Lark SSO authentication
- AI-generated professional headshots
- Live ID preview while filling form
- One-click submission

### HR Management Dashboard
- Single view of all requests nationwide
- Visual ID card gallery
- Bulk approve + bulk send actions
- Real-time status tracking

### Intelligent Distribution
- Automatic nearest-POC calculation
- Direct Lark messaging to POCs
- Audit trail in Lark Bitable

---

# Slide 4: System Architecture

## Technical Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER (Employee/HR)                     │
│  Landing → Application Form → HR Dashboard → ID Gallery     │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              FASTAPI APPLICATION (Vercel Serverless)         │
│   Routes: Auth | Employee | HR | Services: Lark | AI | CDN │
└──────────┬──────────┬───────────────┬────────────┬──────────┘
           │          │               │            │
           ▼          ▼               ▼            ▼
     ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐
     │ Supabase │ │Cloudinary│ │ BytePlus  │ │   Lark   │
     │PostgreSQL│ │Image CDN │ │ Seedream  │ │Bitable/IM│
     └──────────┘ └──────────┘ └───────────┘ └──────────┘
```

### Tech Stack:
| Layer | Technology |
|-------|------------|
| Frontend | Vanilla JS, Jinja2 |
| Backend | FastAPI (Python 3.9+) |
| Database | Supabase PostgreSQL |
| AI | BytePlus Seedream |
| Storage | Cloudinary |
| Enterprise | Lark Bitable + IM |
| Deployment | Vercel Serverless |

---

# Slide 5: Employee Journey

## From Application to Submission

### Step 1: Lark Login
- SSO validates employee identity
- Name and email auto-filled

### Step 2: Photo Upload + AI Generation
- Upload any photo
- AI generates professional headshot
- 8 attire options (smart casual styles)
- Background automatically removed

### Step 3: Form Completion
- Employee ID, position, location
- Contact details
- Digital signature (canvas)
- **Live ID preview** updates in real-time

### Step 4: Submit
- Data → Supabase
- Images → Cloudinary
- Record → Lark Bitable
- Status = "Reviewing"

---

# Slide 6: AI Headshot Generation

## Professional Photos Without a Studio

### How It Works:
1. Employee uploads any decent photo
2. System sends to BytePlus Seedream AI
3. AI generates professional corporate headshot
4. Cloudinary AI removes background

### 8 Attire Options:
| Male | Female |
|------|--------|
| Navy blue polo | Cream silk blouse |
| White button-down | Navy tailored blazer |
| Light gray sweater | Soft peach blouse |
| Dark green polo | Light gray sweater |

### AI Prompt Strategy:
- **Preserve**: Face, hair, identity
- **Transform**: Attire, lighting, background
- **Output**: 2K resolution, transparent PNG

*Result: Every employee gets a professional, consistent headshot*

---

# Slide 7: HR Workflow

## Dashboard + Gallery + Bulk Actions

### HR Dashboard
- View all submissions across 15+ branches
- Search by name, ID, email, location
- Filter by status (Reviewing, Rendered, Approved, etc.)
- Click to view full details

### ID Gallery
- Visual grid of actual ID cards
- Front and back preview
- Barcode (Code 128) + QR code (vCard)
- One-click PDF download

### Bulk Actions
- **Approve All Rendered**: One click to approve batch
- **Send All to POCs**: Automatic routing + Lark messaging

---

# Slide 8: Smart POC Routing

## Automatic Nearest-Branch Calculation

### The Challenge:
- 15 POC branches have printers
- 40+ non-POC locations need routing
- Manual lookup was error-prone

### The Solution: Haversine Distance

```
POC Branches: San Carlos, Pagadian, Zamboanga, Malolos, 
San Fernando, Cagayan De Oro, Tagum, Davao, Cebu, 
Batangas, General Santos, Bacolod, Ilo-Ilo, Quezon City, Calamba
```

**Algorithm**:
1. If employee's branch is a POC → use directly
2. Otherwise → calculate distance to all POCs
3. Return nearest POC branch

**Example**: 
- Employee in Manila (no POC) 
- → Nearest POC: Quezon City (5.2 km)
- → Lark message sent to Quezon City POC

---

# Slide 9: Lark Integration

## Enterprise Connectivity

### Lark SSO (OAuth 2.0 + PKCE)
- Employee portal: Validates org membership
- HR portal: Validates People Support department

### Lark Bitable Sync
- Every submission creates a record
- Status updates sync in real-time
- PDF URL saved to `id_card` field
- `email_sent` flag tracks POC notifications

### Lark IM Messaging
- POCs receive direct messages
- Message includes: Name, ID, Position, PDF link
- **Test Mode**: All messages route to test recipient during development

---

# Slide 10: Safety & Reliability

## Built-In Protections

### Test Mode (Backend-Enforced)
```
POC_TEST_MODE=true   → Messages go to test recipient
POC_TEST_MODE=false  → Messages go to real POCs
```
*Cannot be bypassed by frontend*

### Retry Logic
- Lark Bitable updates: 3 attempts, 0.5s delay
- Cloudinary uploads: Explicit error handling
- PDF URL verification before saving

### Session Caching
- Data cached in sessionStorage
- Survives Vercel cold starts
- 5-minute cache duration

### Data Integrity
- PDF upload must succeed before Lark sync
- Status transitions are logged
- Soft delete ("Removed" status) preserves data

---

# Slide 11: Impact & Metrics

## Before vs After

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Turnaround time | 3-7 days | Same day | ~90% faster |
| HR time per employee | 40-60 min | < 5 min | ~90% reduction |
| Routing errors | ~10% | 0% | Eliminated |
| Status visibility | None | Real-time | Full transparency |
| ID styling consistency | ~80% | 100% | Standardized |

### Qualitative Feedback:
- **HR Team**: "ID card days are no longer dreaded"
- **Employees**: "Got my ID the same day I submitted"
- **POCs**: "Clear Lark messages, know exactly what to print"
- **Management**: "Finally see status without asking HR"

---

# Slide 12: Live Demo

## See It In Action

### Employee Portal
- Lark login → Photo upload → AI headshot → Form → Submit

### HR Dashboard
- View employees → Filter by status → Preview ID

### ID Gallery
- Visual preview → Download PDF → Bulk approve

### POC Routing
- Approve → Send to POC → Lark message delivered

*[Insert screenshot or switch to live demo]*

---

# Slide 13: Roadmap

## Future Enhancements

### Near-Term (Phase 2)
- Batch POC messaging (one message with all cards)
- Employee self-reapplication (update existing ID)
- POC confirmation flow via Lark bot
- Analytics dashboard (charts + metrics)

### Medium-Term (Phase 3)
- Alternative ID formats (visitor, contractor, temp)
- Multi-language support (Filipino/English)
- ID expiry management
- Signature verification

### Long-Term (Phase 4)
- White-label for subsidiaries
- Mobile app for ID display
- Blockchain verification
- Biometric integration

---

# Slide 14: Q&A

## Questions?

### Common Questions:

**Q: What if BytePlus AI is down?**
A: Fallback uses original photo. Employee can regenerate later.

**Q: Can POCs access the system?**
A: No. POCs only receive Lark messages. No login needed.

**Q: How do we add a new POC branch?**
A: Add to POC_BRANCHES set + POC_CONTACTS mapping + coordinates.

**Q: What about data privacy?**
A: Lark SSO validates employees. HR access restricted to People Support.

**Q: Can data be deleted?**
A: Soft delete via "Removed" status. Hard delete via Supabase admin.

---

# Slide 15: Contact

## Get In Touch

**Project Lead**: Miguel  
**Team**: People Support Engineering  
**Repository**: Employee-ID-Registration-System  

**Key Links**:
- Production: [deployment URL]
- Lark Bitable: [SPMC + SPMA tables]
- Documentation: `SHOWCASE.md`

*Thank you!*

---

# Appendix A: Technical Details

## For IT/Engineering Teams

### Key Environment Variables:
```
LARK_APP_ID, LARK_APP_SECRET
CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY
BYTEPLUS_API_KEY, BYTEPLUS_MODEL
SUPABASE_URL, SUPABASE_KEY
POC_TEST_MODE, POC_TEST_RECIPIENT_EMAIL
JWT_SECRET
```

### Status Flow:
```
Reviewing → Rendered → Approved → Sent to POC → Completed
```

### Database Tables:
- Supabase: `employees`
- Lark Bitable: SPMC table + SPMA table

### API Endpoints:
- `/apply` - Employee form
- `/hr/dashboard` - HR management
- `/hr/gallery` - ID preview/PDF
- `/hr/api/employees/*` - REST operations

---

# Appendix B: Barcode & QR Specs

## Technical Specifications

### Barcode (Code 128)
- **Format**: Code 128
- **Data**: Employee ID number
- **Provider**: QuickChart.io
- **Usage**: Scannable on ID card front

### QR Code (vCard)
- **Format**: QR Code
- **Data**: vCard 3.0 format
- **Contents**: Name, Org, Title, Phone, Email
- **Provider**: QuickChart.io
- **Usage**: Scan to add employee to contacts

### PDF Specifications
- **Dimensions**: 2.13" × 3.33" (ID-1 card size)
- **Resolution**: 300 DPI
- **Format**: PDF with JPEG images
- **Generator**: jsPDF + html2canvas
