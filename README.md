# 🤖 Auto Applier — Automated Resume Tailoring Pipeline

An end-to-end automated job application assistant that:

1. **Scrapes** job postings from major job boards (LinkedIn, Indeed, Greenhouse, Lever)
2. **Tailors** your master resume using Google Gemini AI — with strict no-hallucination rules
3. **Compiles** a polished, watermark-free PDF using ReportLab
4. **Notifies** you instantly via WhatsApp (Twilio) when each resume is ready
5. **Tracks** processed jobs in SQLite so you never generate duplicates

---

## 📁 Project Structure

```
Auto Applier/
├── .env.example           ← Credential template (copy to .env)
├── .gitignore
├── requirements.txt
├── config.py              ← ⭐ Edit this: job URLs, board selectors, settings
├── master_resume.md       ← ⭐ Edit this: your base resume in Markdown
├── run_pipeline.py        ← Main entry point
├── scheduler.py           ← Python-based scheduler (alternative to cron)
│
├── modules/
│   ├── scraper.py         ← Playwright + BeautifulSoup scraping
│   ├── tailor.py          ← Gemini API resume tailoring
│   ├── pdf_builder.py     ← ReportLab PDF generation
│   ├── notifier.py        ← Twilio WhatsApp alerts
│   └── state_manager.py   ← SQLite deduplication tracker
│
├── output/                ← Generated PDFs land here (auto-created)
└── logs/
    └── execution.log      ← Run history (auto-created)
```

---

## 🚀 Setup

### 1. Install Dependencies

```bash
cd "Auto Applier"
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Credentials

Copy the example env file and fill in your API keys:

```bash
cp .env.example .env
```

Open `.env` and add:
- `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/app/apikey)
- `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` — from [Twilio Console](https://console.twilio.com)
- `MY_PHONE_NUMBER` — your WhatsApp-enabled number in E.164 format (e.g., `+14155551234`)

> **Twilio WhatsApp Sandbox:** The first time you use Twilio's WhatsApp sandbox, send
> `join <your-sandbox-keyword>` to **+1 (415) 523-8886** on WhatsApp to opt in.

### 3. Add Your Master Resume

Edit [`master_resume.md`](master_resume.md) with your real information. This is the
source of truth — Gemini will only work with content you've provided here.

### 4. Add Target Job URLs

Open [`config.py`](config.py) and add URLs to the `JOB_URLS` list:

```python
JOB_URLS = [
    "https://boards.greenhouse.io/yourcompany/jobs/123456",
    "https://jobs.lever.co/startup/abc-def",
    "https://www.linkedin.com/jobs/view/9876543210",
]
```

---

## ▶️ Running

### One-Off Run
```bash
python run_pipeline.py
```

### Dry Run (no API calls — for testing)
```bash
python run_pipeline.py --dry-run
```

### Python Scheduler (30-minute repeating)
```bash
python scheduler.py
```

### Custom Interval
```bash
python scheduler.py --interval 15   # Every 15 minutes
```

### Cron Job (alternative to scheduler.py)

```bash
# Open crontab
crontab -e

# Add this line (update the paths to match your system):
*/30 * * * * /usr/bin/python3 "/Users/arunprakash/Desktop/Auto Applier/run_pipeline.py" >> "/Users/arunprakash/Desktop/Auto Applier/logs/execution.log" 2>&1
```

---

## 🛠 CLI Reference

| Command | Description |
|---|---|
| `python run_pipeline.py` | Full pipeline run |
| `python run_pipeline.py --dry-run` | Test without API calls |
| `python run_pipeline.py --list` | Show all processed jobs |
| `python run_pipeline.py --reset <URL>` | Re-process a specific URL |
| `python scheduler.py` | Start recurring scheduler |
| `python scheduler.py --once` | Run once and exit |
| `python scheduler.py --interval N` | Custom interval (minutes) |

---

## 🎯 Supported Job Boards

| Board | Selectors | Notes |
|---|---|---|
| **Greenhouse** | `boards.greenhouse.io` | Pre-configured ✅ |
| **Lever** | `jobs.lever.co` | Pre-configured ✅ |
| **Indeed** | `indeed.com` | Pre-configured ✅ |
| **LinkedIn** | `linkedin.com` | Pre-configured ✅ |
| **Other** | `default` fallback | Add custom selectors to `config.py` |

To add a new board, add an entry to `BOARD_SELECTORS` in `config.py`:

```python
"myboard.com": {
    "title":       ".my-job-title-selector",
    "company":     ".my-company-selector",
    "description": "#my-description-id",
},
```

---

## 🔒 Security Notes

- **Never commit `.env`** — it's listed in `.gitignore`
- The SQLite database (`jobs.db`) stores only URLs, job titles, and PDF paths — no personal data
- The Gemini prompt includes explicit anti-hallucination instructions

---

## 🗺 Roadmap

- [ ] Multi-column PDF layout option
- [ ] Cover letter generation per job
- [ ] Email delivery of PDFs
- [ ] Web dashboard to manage job URLs and view generated resumes
- [ ] Keyword match scoring (before/after Gemini tailoring)
