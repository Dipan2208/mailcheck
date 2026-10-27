"""Email deliverability checks: syntax -> DNS (MX) -> SMTP RCPT probe.

The SMTP probe stops after RCPT TO and sends QUIT. DATA is never sent,
so no message is ever delivered to the address being checked.
"""
import os, re, random, string, socket, smtplib, difflib
from functools import lru_cache
import dns.resolver, dns.exception

HELO = os.getenv("SMTP_HELO", "mailcheck.example.com")
FROM = os.getenv("SMTP_FROM", "probe@mailcheck.example.com")
TIMEOUT = 8

SYNTAX = re.compile(
    r"^([A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+)@((?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,})$")
# Providers that accept every address at RCPT time and bounce later,
# so a probe tells us nothing.
OPAQUE = {"yahoo.com", "ymail.com", "aol.com", "outlook.com", "hotmail.com",
          "live.com", "msn.com", "icloud.com", "me.com"}
DISPOSABLE = {"mailinator.com", "guerrillamail.com", "10minutemail.com",
              "tempmail.com", "yopmail.com", "trashmail.com", "sharklasers.com"}
COMMON = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "proton.me"]
ROLES = {"admin", "info", "support", "sales", "contact", "noreply", "no-reply", "postmaster"}


def result(email, status, reason, note=""):
    return {"email": email, "status": status, "reason": reason, "note": note}


@lru_cache(maxsize=1)
def smtp_available():
    """Can this host open outbound port 25 at all? Many PaaS hosts block it."""
    for host in ("gmail-smtp-in.l.google.com", "mx.yandex.net"):
        try:
            socket.create_connection((host, 25), timeout=4).close()
            return True
        except OSError:
            continue
    return False


@lru_cache(maxsize=2048)
def mx_hosts(domain):
    """List of MX hosts, None if the domain cannot receive mail, 'null' for
    a null MX (RFC 7505), 'error' if DNS itself failed."""
    try:
        recs = sorted((r.preference, str(r.exchange).rstrip("."))
                      for r in dns.resolver.resolve(domain, "MX", lifetime=5))
        return "null" if recs == [(0, "")] else [h for _, h in recs]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        try:  # RFC 5321: fall back to an A record
            dns.resolver.resolve(domain, "A", lifetime=5)
            return [domain]
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return None
        except dns.exception.DNSException:
            return "error"
    except dns.exception.DNSException:
        return "error"


def rcpt(host, addr):
    with smtplib.SMTP(host, 25, timeout=TIMEOUT, local_hostname=HELO) as s:
        s.ehlo_or_helo_if_needed()
        s.mail(FROM)
        return s.rcpt(addr)[0]


@lru_cache(maxsize=2048)
def is_catch_all(host, domain):
    junk = "".join(random.choices(string.ascii_lowercase, k=14))
    try:
        return rcpt(host, f"{junk}@{domain}") < 300
    except (OSError, smtplib.SMTPException):
        return None


def suggest(domain):
    m = difflib.get_close_matches(domain, COMMON, n=1, cutoff=0.8)
    return m[0] if m and m[0] != domain else None


def check(email):
    email = email.strip()
    m = SYNTAX.match(email)
    if not m or len(email) > 254 or len(m.group(1)) > 64 or ".." in email:
        return result(email, "bounce", "Not a valid address format")
    local, domain = m.group(1), m.group(2).lower()
    note = "Role address, may be a shared inbox" if local.lower() in ROLES else ""

    hint = suggest(domain)
    mx = mx_hosts(domain)
    if mx is None:
        why = "Domain does not exist or has no mail server"
        return result(email, "bounce", why + (f". Did you mean @{hint}?" if hint else ""))
    if mx == "null":
        return result(email, "bounce", "Domain does not accept email (null MX)")
    if mx == "error":
        return result(email, "unknown", "DNS lookup failed, try again")
    if domain in DISPOSABLE:
        return result(email, "unknown", "Disposable provider, mailbox may expire", note)
    if domain in OPAQUE:
        return result(email, "unknown", "Provider does not reveal whether a mailbox exists", note)
    if not smtp_available():
        return result(email, "unknown", "Domain accepts mail; mailbox not checked (port 25 blocked here)", note)

    last = "No mail server responded"
    for host in mx[:2]:
        try:
            code = rcpt(host, email)
        except (OSError, smtplib.SMTPException) as e:
            last = f"Mail server unreachable ({type(e).__name__})"
            continue
        if 200 <= code < 300:
            if is_catch_all(host, domain):
                return result(email, "unknown", "Server accepts every address (catch-all)", note)
            return result(email, "deliverable", "Mail server confirmed the mailbox", note)
        if code in (550, 551, 553):
            return result(email, "bounce", "Mail server says the mailbox does not exist", note)
        return result(email, "unknown", f"Server deferred or refused the probe ({code})", note)
    return result(email, "unknown", last, note)
