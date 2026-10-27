# Mailcheck

Paste a list of email addresses and get one of three verdicts for each:
**likely delivered**, **likely to bounce**, or **unknown**, with the reason shown.

Live: _add link_ · Code: _add link_

## How it works

Each address goes through checks in order, stopping at the first conclusive one:

1. **Syntax**: format and length limits (RFC 5321). Failure -> bounce.
2. **DNS**: looks up MX records, falling back to A records. No such domain, or a null MX (RFC 7505) -> bounce.
3. **Known limits**: disposable providers and providers that accept everything at SMTP time (Yahoo, Outlook, iCloud and similar) -> unknown, because no probe can tell.
4. **SMTP probe**: connects to the domain's mail server on port 25 and runs `EHLO`, `MAIL FROM`, `RCPT TO`, then `QUIT`.
   - `250` -> the server accepts the mailbox. A second probe to a random address detects **catch-all** domains, which accept anything (-> unknown). Otherwise -> delivered.
   - `550/551/553` -> bounce.
   - `4xx`, other codes, timeouts -> unknown (greylisting, rate limiting, refusal).

**No message is ever sent.** The conversation ends before the `DATA` command, so nothing is delivered to any address.

Also: typo hints (`gmial.com` -> `gmail.com`), role-address notes (`info@`, `admin@`), duplicate removal, a filter by result, and CSV export. Limit is 100 addresses per run, checked 8 at a time.

## Why "unknown" is common

Many servers never confirm mailboxes: they accept all recipients and bounce later, block probes from unfamiliar IPs, or greylist. Guessing would be worse than saying so, so these are reported as unknown with the cause.

## What the deployed version can and cannot check

Free hosts (Render and similar) block outbound port 25. The app detects this at runtime and shows a banner. On the deployed version:

- **Can check:** syntax, domain existence, MX records, null MX, typos, disposable domains.
- **Cannot check:** whether a specific mailbox exists. Addresses with a working domain are reported as *unknown* with the reason "port 25 blocked".

Run it locally (home networks and many VPS providers allow port 25) or on a VPS to get the full SMTP check.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py            # http://127.0.0.1:5000
pip install pytest && pytest
```

Optional env vars: `SMTP_HELO` (hostname used in EHLO) and `SMTP_FROM` (envelope sender). Set both to a domain you control for best results, since some servers check them.

## Deploy on Render

Push to GitHub, create a new **Web Service** from the repo; `render.yaml` supplies the settings (build `pip install -r requirements.txt`, start `gunicorn app:app`).

## Layout

`verifier.py` checks · `app.py` Flask API (`POST /api/check`, `GET /api/status`) · `templates/index.html` UI · `test_verifier.py` tests
