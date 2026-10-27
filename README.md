# Mailcheck

> Paste a list of email addresses and find out which ones will actually land, before you hit send.

**Live app:** https://mailcheck-rrl6.onrender.com · **Code:** https://github.com/Dipan2208/mailcheck

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Flask](https://img.shields.io/badge/flask-API-lightgrey) ![Deploy](https://img.shields.io/badge/deploy-Render-46e3b7)

Every address gets one of three verdicts, with the reason shown:

| Verdict | Meaning |
|---|---|
| ✅ **Likely delivered** | The mail server accepted the mailbox |
| ❌ **Likely to bounce** | Bad syntax, no such domain, or the server rejected the mailbox |
| ❔ **Unknown** | The server won't say (catch-all, greylisting, blocked probes) |

**No message is ever sent.** The SMTP conversation stops before the `DATA` command, so nothing is delivered to any address.

## Features

- Three-state verdicts, each with a plain-language reason
- Typo hints (`gmial.com` → `gmail.com`)
- Role-address notes (`info@`, `admin@`)
- Disposable-domain detection
- Catch-all detection
- Duplicate removal
- Filter by result and export to CSV
- Up to 100 addresses per run, checked 8 at a time

## How it works

Each address passes through these checks in order and stops at the first conclusive one:

1. **Syntax**: format and length limits (RFC 5321). Failure → bounce.
2. **DNS**: looks up MX records, falling back to A records. A non-existent domain or a null MX (RFC 7505) → bounce.
3. **Known limits**: disposable providers, and providers that accept everything at SMTP time (Yahoo, Outlook, iCloud and similar) → unknown, because no probe can tell.
4. **SMTP probe**: connects to the domain's mail server on port 25 and runs `EHLO`, `MAIL FROM`, `RCPT TO`, then `QUIT`.

| Server response | Result |
|---|---|
| `250` | Mailbox accepted. A second probe to a random address detects **catch-all** domains (→ unknown). Otherwise → delivered |
| `550` / `551` / `553` | Bounce |
| `4xx`, other codes, timeouts | Unknown (greylisting, rate limiting, refusal) |

## Why "unknown" is common

Many servers never confirm mailboxes. They accept all recipients and bounce later, block probes from unfamiliar IPs, or greylist. Guessing would be worse than admitting uncertainty, so these are reported as **unknown** along with the cause.

## Hosted vs. local

Free hosts such as Render block outbound port 25. The app detects this at runtime and shows a banner.

| | Hosted ([live demo](https://mailcheck-rrl6.onrender.com)) | Local / VPS |
|---|---|---|
| Syntax, domain, MX, null MX | ✅ | ✅ |
| Typos, disposable domains | ✅ | ✅ |
| Mailbox-level SMTP check | ❌ (reported as *unknown*, "port 25 blocked") | ✅ |

For the full SMTP check, run it locally (home networks and many VPS providers allow port 25) or on a VPS.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py            # http://127.0.0.1:5000
```

Run the tests:

```bash
pip install pytest && pytest
```

**Optional environment variables**

| Variable | Purpose |
|---|---|
| `SMTP_HELO` | Hostname used in `EHLO` |
| `SMTP_FROM` | Envelope sender |

Set both to a domain you control for best results, since some servers check them.

## Deploy on Render

1. Push the repo to GitHub.
2. Create a new **Web Service** from the repo.
3. `render.yaml` supplies the settings (build: `pip install -r requirements.txt`, start: `gunicorn app:app`).

## Project layout

```
├── app.py               # Flask API: POST /api/check, GET /api/status
├── verifier.py          # Validation and probe logic
├── templates/
│   └── index.html       # UI
├── test_verifier.py     # Tests
├── render.yaml          # Render deploy config
└── requirements.txt
```

## API

| Endpoint | Description |
|---|---|
| `POST /api/check` | Check a list of addresses |
| `GET /api/status` | Report whether port 25 is reachable |

---
