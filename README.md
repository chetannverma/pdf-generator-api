# 📄 Anuj Jindal — Automated Branded PDF Generator

> **End-to-end automation pipeline** that converts raw educational notes into a professionally branded, multi-page PDF document — triggered by a single click in n8n Cloud and delivered automatically to Google Drive and Gmail.

---

## 🎯 What This Does

Every time the workflow is executed:

1. n8n Cloud sends a request to a Flask API hosted on Railway
2. The API runs a Python script that generates a fully branded A4 PDF
3. The PDF is returned to n8n as base64 data
4. n8n uploads the PDF to Google Drive
5. n8n emails the PDF to your inbox as an attachment

**Zero manual steps after triggering. Zero file management. Zero downloads needed.**

---

## 🖼️ Output Preview

| Element | Specification |
|---|---|
| Page size | A4 |
| Header | Blue (`#1B71AC`) bar — Logo top-left, Subject + Chapter + Date top-right |
| Accent line | Green (`#2AB573`) stripe below header |
| Watermark | `LOGO-CROP.png` — 550×550 px, 20% opacity, centred on every page |
| Footer | Blue bar — Phone left · Website centred · Page number right |
| Content | 7 sections with branded headings, callout boxes, comparison tables, embedded diagrams |
| Delivery | Google Drive upload + Gmail attachment |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      n8n Cloud                              │
│                                                             │
│  Manual Trigger                                             │
│       │                                                     │
│       ▼                                                     │
│  Set API Configuration  ◄── only thing you ever change      │
│       │                                                     │
│       ▼                                                     │
│  Health Check  ──────────────────────────────────────────┐  │
│       │                                                  │  │
│       ▼                                                  │  │
│  Verify API is Live                                      │  │
│       │                          ┌───────────────────┐  │  │
│       ▼                          │  Railway (Python) │  │  │
│  Generate PDF via API ──POST───► │  api_server.py    │  │  │
│       │                          │  generate_pdf.py  │  │  │
│       │        PDF as base64 ◄── │  + all assets     │  │  │
│       ▼                          └───────────────────┘  │  │
│  Validate PDF Response                                   │  │
│       │                                                  │  │
│       ▼                                                  │  │
│  Success Summary                           Error Handler ◄┘  │
│       │                                                     │
│       ▼                                                     │
│  Prepare Binary PDF                                         │
│       │                                                     │
│       ▼                                                     │
│  Upload to Google Drive  ◄── PDF saved automatically        │
│       │                                                     │
│       ▼                                                     │
│  Send Email with PDF  ◄── PDF attached automatically        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
pdf-generator-api/
│
├── generate_pdf.py              # PDF engine — ReportLab + Pillow
├── api_server.py                # Flask HTTP API wrapper
├── requirements.txt             # Python dependencies
├── Procfile                     # Railway start command
│
├── LOGO-FULL-01.png             # Header logo (top-left, every page)
├── LOGO-CROP.png                # Watermark logo (550×550 px, 20% opacity)
│
├── Untitled.png                 # Types of Economic Growth diagram
├── Untitled_1.png               # Traditional Approach cards
├── Untitled_2.png               # Modern Approach mind-map
├── Untitled_3.png               # Structural changes diagram
├── Untitled_4.png               # Structural changes (continued)
├── Untitled_5.png               # HDR tree diagram
├── Untitled_6.png               # HDI components
├── Untitled_7.png               # IHDI structure
├── Untitled_8.png               # GII structure
├── Untitled_9.png               # GSNI components
├── Untitled_10.png              # MPI structure
├── Untitled_11.png              # MPI global table
├── Untitled_12.png              # World Happiness Index components
├── Screenshot_2023-12-11_114429.png   # OECD Better Life Index
└── Screenshot_2023-12-11_153014.png   # GDI diagram
```

**Total: 23 files** — 4 code/config + 2 logos + 15 content images + 2 screenshots

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Automation | [n8n Cloud](https://n8n.io) | Workflow orchestration, scheduling, delivery |
| API Server | [Flask](https://flask.palletsprojects.com/) | HTTP wrapper around the Python script |
| Hosting | [Railway](https://railway.app) | Cloud deployment of the Flask API |
| PDF Generation | [ReportLab](https://www.reportlab.com/) | Programmatic PDF rendering (canvas + Platypus) |
| Image Processing | [Pillow](https://python-pillow.org/) | Watermark resize (550×550) and opacity (20%) |
| Process Manager | [Gunicorn](https://gunicorn.org/) | Production WSGI server on Railway |
| Delivery | Google Drive API + Gmail API | Auto-upload and email via n8n connectors |

---

## 🚀 Deployment Guide

### Prerequisites

- GitHub account (free)
- Railway account — sign up at [railway.app](https://railway.app) with GitHub
- n8n Cloud account — sign up at [app.n8n.cloud](https://app.n8n.cloud)
- Google account (for Drive + Gmail delivery)

---

### Step 1 — Fork or Clone this Repository

```bash
git clone https://github.com/YOUR_USERNAME/pdf-generator-api.git
cd pdf-generator-api
```

Or upload all 23 files manually through the GitHub web interface:
**New repo → Add file → Upload files → commit**

---

### Step 2 — Deploy to Railway

1. Go to [railway.app](https://railway.app) → **New Project**
2. Click **Deploy from GitHub repo**
3. Select **`pdf-generator-api`**
4. Railway auto-detects `Procfile` and `requirements.txt` — build starts automatically
5. Wait ~3 minutes for **"Deploy successful"**
6. Go to **Settings → Networking → Generate Domain**
7. Copy your URL — it looks like:
   ```
   https://pdf-generator-api-production.up.railway.app
   ```

**Verify deployment:**
```
GET https://YOUR-RAILWAY-URL.up.railway.app/health
```
Expected response:
```json
{"service": "pdf-generator", "status": "ok"}
```

---

### Step 3 — Import Workflow into n8n Cloud

1. Log into your n8n Cloud instance
2. **Workflows → + → Import from File**
3. Select `n8n_with_delivery.json`
4. The workflow loads with all 10 nodes pre-connected

---

### Step 4 — Configure the Workflow (One Change Only)

Open the **"Set API Configuration"** node and update:

```javascript
const RAILWAY_URL = 'https://YOUR-RAILWAY-URL.up.railway.app';
//                   ↑ paste your actual Railway URL here
```

Save. That's the only configuration required.

---

### Step 5 — Connect Google Drive & Gmail

**Google Drive:**
1. Open the **"Upload to Google Drive"** node
2. Credentials → Create new → **Google Drive OAuth2**
3. Sign in with Google → Allow → Save

**Gmail:**
1. Open the **"Send Email with PDF"** node
2. Credentials → Create new → **Gmail OAuth2**
3. Sign in with Google → Allow → Save
4. Update the **"Send To"** field with your email address

---

### Step 6 — Run

Click **Execute Workflow** on the Manual Trigger node.

**Expected node execution times:**

| Node | Time |
|---|---|
| Manual Trigger → Set API Configuration | < 1 sec |
| Health Check + Verify | 1–2 sec |
| Generate PDF via API | 15–40 sec |
| Validate + Success Summary | < 1 sec |
| Prepare Binary PDF | < 1 sec |
| Upload to Google Drive | 3–8 sec |
| Send Email with PDF | 2–5 sec |

**Total: ~30–60 seconds from click to PDF in inbox.**

---

## 🔌 API Reference

### `GET /health`

Health check endpoint. Used by n8n to confirm the server is live before generating.

**Response:**
```json
{
  "status": "ok",
  "service": "pdf-generator"
}
```

---

### `POST /generate-pdf`

Generates the branded PDF and returns it as base64.

**Request body (optional):**
```json
{
  "output_filename": "Economic_Growth_and_Development.pdf"
}
```

**Success response:**
```json
{
  "success": true,
  "filename": "Economic_Growth_and_Development.pdf",
  "pdf_base64": "JVBERi0xLjQ...",
  "size_kb": 1903
}
```

**Error response:**
```json
{
  "success": false,
  "error": "error message here"
}
```

---

## 📐 PDF Design Specifications

### Header (every page)
- Background: Blue `#1B71AC`, height `1.9 cm`
- **Left:** `LOGO-FULL-01.png` — drawn using `cv.drawImage` with `ImageReader` (not Platypus flowable)
- **Right:** Three lines right-aligned in white:
  - Line 1 (bold): Subject name
  - Line 2: Chapter name
  - Line 3: Today's date (`DD Month YYYY`)
- Green `#2AB573` accent line (3pt) immediately below

### Watermark (every page)
- Source: `LOGO-CROP.png`
- Resized to exactly **550 × 550 px** using `Pillow LANCZOS`
- Alpha channel multiplied by **0.20** (20% opacity)
- Drawn centred on each page, behind all content

### Footer (every page)
- Background: Blue `#1B71AC`, height `0.9 cm`
- Green `#2AB573` accent line (2pt) above footer
- **Left:** Phone number
- **Centre:** Website URL — `drawCentredString` at `w/2`
- **Right:** Page number

### Content Structure
| Section | Description |
|---|---|
| 1.0 | Economic Growth — meaning, factors, limitations |
| 2.0 | Economic Development — meaning, evolution, approaches |
| 3.0 | Growth vs Development — comparison table |
| 4.0 | Structural Changes — Kuznets, Chenery |
| 5.0 | Indices — HDI, IHDI, GDI, GII, GSNI, MPI, WHI, OECD, GPI, PQLI |
| 6.0 | Developed vs Developing Economies — World Bank classification |
| 7.0 | Composite Development Index — Raghuram Rajan Committee |

---

## 🔄 n8n Workflow Node Summary

| # | Node | Type | Purpose |
|---|---|---|---|
| 1 | Manual Trigger | Trigger | Start button |
| 2 | Set API Configuration | Code | Railway URL — only config needed |
| 3 | Health Check | HTTP GET | Pings `/health` — fast-fail if server down |
| 4 | Verify API is Live | Code | Validates `{"status":"ok"}` response |
| 5 | Generate PDF via API | HTTP POST | Calls `/generate-pdf` — 120s timeout |
| 6 | Validate PDF Response | Code | Confirms `pdf_base64` present in response |
| 7 | Success Summary | Code | Formats final output object |
| 8 | Prepare Binary PDF | Code | Decodes base64 → binary for Drive upload |
| 9 | Upload to Google Drive | Google Drive | Saves PDF to Drive root |
| 10 | Send Email with PDF | Gmail | Emails PDF as attachment |
| 11 | Error Handler | Code | Catches and formats any failure |

---

## 🐛 Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Health Check` turns red | Railway URL wrong or server not running | Check URL in Set API Configuration has no typos, no trailing slash |
| `Generate PDF` times out | Cold start on Railway free tier | Re-run — second execution is always faster |
| `ModuleNotFoundError` in Railway logs | Dependencies still installing | Wait 2 minutes, then re-run |
| Images missing in PDF | PNG files not uploaded to GitHub | Check all 23 files exist in the repo |
| Logo not showing in header | `LOGO-FULL-01.png` filename mismatch | Confirm exact filename — case sensitive |
| Watermark not visible | `LOGO-CROP.png` not found | Confirm exact filename in repo |
| Google Drive node fails | OAuth credential not connected | Re-authenticate in the node credentials |
| Gmail node fails | OAuth credential not connected | Re-authenticate in the node credentials |
| `Unrecognized node type: executeCommand` | Using old local workflow on n8n Cloud | Import `n8n_with_delivery.json` instead |

---

## 🔧 Local Development & Testing

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/pdf-generator-api.git
cd pdf-generator-api

# Install dependencies
pip install flask reportlab pillow requests gunicorn

# Test PDF generation directly
python generate_pdf.py --img-dir . --output test_output.pdf

# Start the API server locally
python api_server.py
# Server starts at http://localhost:5000

# Test health endpoint
curl http://localhost:5000/health

# Test PDF generation endpoint
curl -X POST http://localhost:5000/generate-pdf \
  -H "Content-Type: application/json" \
  -d '{"output_filename": "test.pdf"}'
```

---

## 📦 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5000` | Port the Flask server listens on (set automatically by Railway) |
| `IMG_DIR` | Script directory | Path to folder containing logos and PNG images |

Railway sets `PORT` automatically. You do not need to configure it manually.

---

## 🗂️ Brand Assets

| File | Usage | Dimensions |
|---|---|---|
| `LOGO-FULL-01.png` | Header — top-left every page | Scaled to fit header height |
| `LOGO-CROP.png` | Watermark — centred every page | Resized to 550×550 px in code |

**Brand colours:**
- Blue: `#1B71AC`
- Green: `#2AB573`

---

## 📬 Delivery Options

| Method | How to Enable |
|---|---|
| **Google Drive** (default) | Connect Google Drive OAuth2 in the "Upload to Google Drive" node |
| **Gmail attachment** (default) | Connect Gmail OAuth2 in the "Send Email with PDF" node |
| **Manual download** | Click "Success Summary" node output → download `pdf_base64` field |
| **Webhook** | Replace Manual Trigger with Webhook node + add HTTP Response at end |
| **Schedule** | Replace Manual Trigger with Schedule Trigger — set any cron interval |

---

## 🙏 Credits

Built for **Anuj Jindal** ([anujjindal.in](https://anujjindal.in))

| Component | Tool |
|---|---|
| Workflow automation | n8n Cloud |
| API hosting | Railway |
| PDF engine | ReportLab (Python) |
| Image processing | Pillow (Python) |
| Web framework | Flask (Python) |

---

## 📄 License

Private repository — all brand assets, logos, and content belong to Anuj Jindal.
