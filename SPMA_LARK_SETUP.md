# SPMA Lark Table Integration - Setup Guide

## Problem Identified

Your **SPMA table** (`tblajlHwJ6qFRlVa`) is in a **DIFFERENT Lark Base** than your **SPMC table** (`tbl3Jm6881dJMF6E`).

**Proof:**
```
SPMC Base (WxvXbLMt8aoPzzszjR3lIXhlgNc) contains:
  - tbl3Jm6881dJMF6E ✅

SPMA Base (unknown) contains:
  - tblajlHwJ6qFRlVa ❌ (not found in WxvXbLMt8aoPzzszjR3lIXhlgNc)
```

Both tables cannot use the same `LARK_BITABLE_ID`. They need separate credentials.

---

## Solution: Create a New Lark App for SPMA Base

### Step 1: Find the SPMA Base App Token

1. Open your SPMA Lark Base in browser:
   ```
   https://spmadridlaw.sg.larksuite.com/wiki/JSE6wQzR5iDll1kbyR1lYIZxg9e
   ```

2. Look at the URL - extract the Base ID. You should see a pattern like:
   ```
   /wiki/[BASE_ID]?table=tblajlHwJ6qFRlVa
   ```

3. Alternative: Click "Share" → "API" or look in Bitable settings for the app token

4. **Copy the SPMA Base app token** (looks like: `Wxv...`)

### Step 2: Create or Use Existing Lark App

You have two options:

#### Option A: Use the Same App (Easier - if you control both Bases)

If you want to use the same `cli_a866185f1638502f` app for both tables:

1. The app must have access to BOTH Bases
2. Share both Bases with the app or invite it as a collaborator
3. Use the SPMA Base app token in the `.env`

**In `.env`, replace these:**
```dotenv
# Same app, but SPMA Base token
LARK_BITABLE_ID_SPMA=[SPMA_BASE_BITABLE_ID]  # Get from step 1
LARK_APP_ID_SPMA=cli_a866185f1638502f       # Same as SPMC
LARK_APP_SECRET_SPMA=zaduPnvOLTxcb7W8XHYIaggtYgzOUOI6  # Same as SPMC
```

#### Option B: Create a New App (Better Separation)

If SPMA Base is managed by a different team:

1. Go to: `https://open.larksuite.com/app`
2. Create a new app or ask SPMA Base admin to create one
3. Get the new app credentials:
   - `App ID` (looks like: `cli_...`)
   - `App Secret` (long random string)
4. Grant the app permissions:
   - Scope: `bitable:app`, `bitable:record:create`, `bitable:record:read`
   - Share the SPMA Base with the app

**In `.env`, add:**
```dotenv
LARK_BITABLE_ID_SPMA=[SPMA_BASE_BITABLE_ID]
LARK_APP_ID_SPMA=cli_new_app_id_here
LARK_APP_SECRET_SPMA=new_app_secret_here
```

---

## Step 3: Update `.env` File

Edit `.env` and ensure these fields are set correctly:

```dotenv
# SPMC (Working)
LARK_APP_ID=cli_a866185f1638502f
LARK_APP_SECRET=zaduPnvOLTxcb7W8XHYIaggtYgzOUOI6
LARK_BITABLE_ID=WxvXbLMt8aoPzzszjR3lIXhlgNc
LARK_TABLE_ID=tbl3Jm6881dJMF6E

# SPMA (Different Base - requires separate config)
LARK_BITABLE_ID_SPMA=WxvXbLMt8aoPzzszjR3lIXhlgNc    # ← UPDATE with SPMA Base ID
LARK_TABLE_ID_SPMA=tblajlHwJ6qFRlVa
LARK_APP_ID_SPMA=cli_a866185f1638502f               # ← Can be same as SPMC if shared app
LARK_APP_SECRET_SPMA=zaduPnvOLTxcb7W8XHYIaggtYgzOUOI6  # ← Can be same as SPMC if shared app
```

---

## Step 4: Test the Connection

Run the updated test:

```bash
python test_lark2.py
```

Expected output if successful:
```
✅ Found 1 tables. Scanning for target table id...
   - tblajlHwJ6qFRlVa  Legal Officers
   ✅ FOUND TARGET TABLE!
   
✅ Successfully appended test record!
```

---

## Step 5: Verify Form Submissions

1. Start the server:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. Test SPMC form (`/choose-form` → SPMC):
   - Should append to `tbl3Jm6881dJMF6E` ✅

3. Test SPMA form (`/choose-form` → SPMA):
   - Should append to `tblajlHwJ6qFRlVa` ✅

---

## Troubleshooting

If test still fails:

| Error | Solution |
|-------|----------|
| `Found 0 tables` | App lacks read permission for SPMA Base. **Action:** Share the SPMA Base with the app or publish app with correct scopes. |
| `TARGET TABLE ID NOT FOUND` | Wrong `LARK_BITABLE_ID_SPMA`. **Action:** Verify the Base ID from URL or Lark settings. |
| `Permission denied` | App has read access but not write. **Action:** Grant app write permission to SPMA Base or publish new app version with `bitable:record:create` scope. |

---

## Quick Reference: What Changed

✅ **Files Modified:**
- `.env` - Added SPMA-specific app credentials
- `app/services/lark_service.py` - Added support for separate SPMA token
- `app/routes/employee.py` - New `/submit-spma` endpoint (already done)
- `app/static/spma-form.js` - Updated to use `/submit-spma` endpoint (already done)
- `test_lark2.py` - Added table listing debug (already done)

✅ **Key Feature:**
- SPMC form → Appends to SPMC table (`tbl3Jm6881dJMF6E`)
- SPMA form → Appends to SPMA table (`tblajlHwJ6qFRlVa`)
- Both can use same app or different apps

---

## Next Action

**Provide the SPMA Base app token and we'll finish the setup:**

1. Get `LARK_BITABLE_ID_SPMA` from your SPMA Base
2. Update `.env` 
3. Run `python test_lark2.py`
4. Share output so I can verify the fix
