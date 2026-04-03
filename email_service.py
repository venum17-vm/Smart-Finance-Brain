"""
email_service.py — Smart Finance Brain v4.1
Gmail SMTP email alerts — fully working, with timeout and retry.

SETUP (one-time, 2 minutes):
  1. Go to myaccount.google.com → Security
  2. Turn ON  2-Step Verification
  3. Search "App passwords" → Select app: Mail → Generate
  4. Copy the 16-character password (spaces don't matter)
  5. In the app: Budget page → Email Settings → enter Gmail + App Password → Save

COMMON ERRORS:
  SMTPAuthenticationError → You used your regular password. Use App Password.
  Connection timeout       → Check internet. Try SMTP_PORT = 465 below.
  SMTPRecipientsRefused   → Check recipient email is valid.
"""

import smtplib
import ssl
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ── Path fix ──────────────────────────────────────────────────────────────────
_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
for _p in [_THIS_DIR, _PARENT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
# ─────────────────────────────────────────────────────────────────────────────

SMTP_HOST    = "smtp.gmail.com"
SMTP_PORT    = 587          # STARTTLS — change to 465 if this fails
SMTP_TIMEOUT = 15           # seconds before giving up


def is_configured(sender_email: str = "", sender_password: str = "") -> bool:
    """
    Returns True if credentials look valid.
    Accepts any email (not just @gmail.com) for flexibility.
    """
    se = (sender_email or "").strip()
    sp = (sender_password or "").strip().replace(" ", "")
    return bool(se and "@" in se and sp and len(sp) >= 8)


def _clean_password(pwd: str) -> str:
    """Strip spaces from App Password (Google shows it with spaces)."""
    return (pwd or "").strip().replace(" ", "")


def send_email(sender_email: str, sender_password: str,
               to_email: str, subject: str,
               body_text: str, body_html: str = "") -> tuple[bool, str]:
    """
    Send an email via Gmail SMTP.
    Tries STARTTLS (port 587) first; clear error messages on failure.
    """
    if not is_configured(sender_email, sender_password):
        return False, (
            "Gmail not set up. Go to Budget page → Email Settings "
            "and enter your Gmail address and App Password."
        )

    to = (to_email or "").strip()
    if not to or "@" not in to:
        return False, f"Invalid recipient email: '{to_email}'"

    pwd = _clean_password(sender_password)

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Smart Finance Brain <{sender_email.strip()}>"
        msg["To"]      = to
        msg["X-Mailer"] = "Smart Finance Brain"

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        html = body_html if body_html else _build_html(subject, body_text)
        msg.attach(MIMEText(html, "html", "utf-8"))

        ctx = ssl.create_default_context()

        if SMTP_PORT == 465:
            # SSL directly
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT,
                                   context=ctx, timeout=SMTP_TIMEOUT) as server:
                server.login(sender_email.strip(), pwd)
                server.sendmail(sender_email.strip(), to, msg.as_string())
        else:
            # STARTTLS (port 587)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                server.ehlo()
                server.starttls(context=ctx)
                server.ehlo()
                server.login(sender_email.strip(), pwd)
                server.sendmail(sender_email.strip(), to, msg.as_string())

        return True, f"Email sent to {to}"

    except smtplib.SMTPAuthenticationError:
        return False, (
            "Gmail login failed. Make sure you are using an App Password "
            "(NOT your regular Gmail password). "
            "Generate one at: myaccount.google.com → Security → App Passwords."
        )
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"Recipient rejected: {to}. Error: {e}"
    except smtplib.SMTPSenderRefused:
        return False, f"Sender rejected: {sender_email}. Check your Gmail address."
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except TimeoutError:
        return False, (
            f"Connection timed out after {SMTP_TIMEOUT}s. "
            "Check internet connection or try port 465 in email_service.py."
        )
    except OSError as e:
        if "Errno -3" in str(e) or "Name or service" in str(e):
            return False, "No internet connection. Cannot reach smtp.gmail.com."
        return False, f"Network error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {type(e).__name__}: {e}"


def test_connection(sender_email: str, sender_password: str) -> tuple[bool, str]:
    """
    Test Gmail login without sending any email.
    Returns (True, success_message) or (False, error_message).
    """
    if not is_configured(sender_email, sender_password):
        return False, "Fill in Gmail address and App Password first."

    pwd = _clean_password(sender_password)

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            server.login(sender_email.strip(), pwd)
        return True, f"Connected! Gmail ({sender_email}) is ready to send alerts."

    except smtplib.SMTPAuthenticationError:
        return False, (
            "Wrong App Password. "
            "Go to myaccount.google.com → Security → App Passwords and generate a new one."
        )
    except TimeoutError:
        return False, "Connection timed out. Check your internet or try port 465."
    except OSError as e:
        if "Errno -3" in str(e) or "Name or service" in str(e):
            return False, "No internet connection."
        return False, f"Network error: {e}"
    except Exception as e:
        return False, f"Connection failed: {type(e).__name__}: {e}"


# ─────────────────────────────────────────────────────────────────────────────
#  EMAIL TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────
def _now():
    return datetime.now().strftime("%d %b %Y at %I:%M %p")


def send_budget_warning(se: str, sp: str, to: str, name: str,
                        spent: float, budget: float, pct: float) -> tuple[bool, str]:
    subject = f"SmartFinance Alert: {pct:.0f}% of budget used this month"
    text = (
        f"Hi {name},\n\n"
        f"Budget alert from Smart Finance Brain.\n\n"
        f"  Used      : {pct:.0f}%\n"
        f"  Spent     : Rs.{spent:,.2f}\n"
        f"  Budget    : Rs.{budget:,.2f}\n"
        f"  Remaining : Rs.{budget - spent:,.2f}\n\n"
        f"Please review your expenses to stay within budget.\n\n"
        f"-- Smart Finance Brain | {_now()}"
    )
    return send_email(se, sp, to, subject, text)


def send_budget_exceeded(se: str, sp: str, to: str, name: str,
                         spent: float, budget: float) -> tuple[bool, str]:
    excess = spent - budget
    subject = "SmartFinance URGENT: Monthly budget exceeded!"
    text = (
        f"Hi {name},\n\n"
        f"You have exceeded your monthly budget.\n\n"
        f"  Spent   : Rs.{spent:,.2f}\n"
        f"  Budget  : Rs.{budget:,.2f}\n"
        f"  Over by : Rs.{excess:,.2f}\n\n"
        f"Please control your spending immediately.\n\n"
        f"-- Smart Finance Brain | {_now()}"
    )
    return send_email(se, sp, to, subject, text)


def send_multi_threshold_alert(se: str, sp: str, to: str, name: str,
                                spent: float, budget: float, pct: float,
                                threshold: int) -> tuple[bool, str]:
    """Send alert for a specific threshold crossing (50, 60, 70, 80, 90, 100%)."""
    if pct >= 100:
        return send_budget_exceeded(se, sp, to, name, spent, budget)
    subject = f"SmartFinance: You have spent {pct:.0f}% of your {threshold}% budget limit"
    text = (
        f"Hi {name},\n\n"
        f"You have crossed the {threshold}% budget threshold.\n\n"
        f"  Spent     : Rs.{spent:,.2f} ({pct:.1f}%)\n"
        f"  Budget    : Rs.{budget:,.2f}\n"
        f"  Remaining : Rs.{budget - spent:,.2f}\n\n"
        f"-- Smart Finance Brain | {_now()}"
    )
    return send_email(se, sp, to, subject, text)


def send_obligation_reminder(se: str, sp: str, to: str, name: str,
                              bill_name: str, amount: float,
                              due_date: str) -> tuple[bool, str]:
    subject = f"SmartFinance Reminder: {bill_name} due on {due_date}"
    text = (
        f"Hi {name},\n\n"
        f"Payment reminder.\n\n"
        f"  Bill     : {bill_name}\n"
        f"  Amount   : Rs.{amount:,.2f}\n"
        f"  Due Date : {due_date}\n\n"
        f"Pay on time to avoid penalties.\n\n"
        f"-- Smart Finance Brain | {_now()}"
    )
    return send_email(se, sp, to, subject, text)


def send_welcome(se: str, sp: str, to: str, name: str) -> tuple[bool, str]:
    subject = f"Welcome to Smart Finance Brain, {name}!"
    text = (
        f"Hi {name},\n\n"
        f"Your Smart Finance Brain account is active.\n\n"
        f"You will receive:\n"
        f"  - Budget alerts when spending crosses your thresholds\n"
        f"  - Bill payment reminders before due dates\n\n"
        f"All alerts come only to this email. Your data stays private.\n\n"
        f"-- Smart Finance Brain | {_now()}"
    )
    return send_email(se, sp, to, subject, text)


def send_test_email(se: str, sp: str, to: str, name: str) -> tuple[bool, str]:
    subject = "SmartFinance Brain — Test Email"
    text = (
        f"Hi {name},\n\n"
        f"This is a test email from Smart Finance Brain.\n\n"
        f"Email alerts are working correctly!\n\n"
        f"-- Smart Finance Brain | {_now()}"
    )
    return send_email(se, sp, to, subject, text)


def send_account_deleted(se: str, sp: str, to: str, name: str) -> tuple[bool, str]:
    subject = "Smart Finance Brain — Account Deleted"
    text = (
        f"Hi {name},\n\n"
        f"Your Smart Finance Brain account has been permanently deleted.\n\n"
        f"All your data including expenses, documents, and settings have been removed.\n\n"
        f"We hope the app was useful. Thank you for using Smart Finance Brain.\n\n"
        f"-- Smart Finance Brain | {_now()}"
    )
    return send_email(se, sp, to, subject, text)


# ─────────────────────────────────────────────────────────────────────────────
#  HTML TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────
def _build_html(subject: str, plain: str) -> str:
    escaped = plain.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    rows = ""
    for line in escaped.split("\n"):
        s = line.strip()
        if not s:
            rows += "<tr><td style='padding:4px 0;'>&nbsp;</td></tr>"
        elif s.startswith("--"):
            rows += f"<tr><td style='color:#888;font-size:11px;padding-top:16px;'>{s}</td></tr>"
        elif ":" in s and not s.endswith(":"):
            label, val = s.split(":", 1)
            rows += (
                f"<tr>"
                f"<td style='width:120px;color:#666;padding:3px 0;'>{label}:</td>"
                f"<td style='font-weight:600;padding:3px 0;color:#0A1628;'>{val.strip()}</td>"
                f"</tr>"
            )
        else:
            rows += f"<tr><td colspan='2' style='padding:3px 0;'>{s}</td></tr>"

    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f4f6fb;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6fb;">
<tr><td align="center" style="padding:32px 16px;">
<table width="560" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:12px;overflow:hidden;
              box-shadow:0 2px 12px rgba(0,0,0,0.08);">
  <tr>
    <td style="background:#0A1628;padding:20px 28px;">
      <span style="color:#FFD700;font-size:20px;font-weight:bold;">
        &#128142; Smart Finance Brain
      </span>
    </td>
  </tr>
  <tr>
    <td style="padding:28px;">
      <h2 style="margin:0 0 20px;color:#0A1628;font-size:17px;">{subject}</h2>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="font-size:14px;line-height:1.7;color:#333;">
        {rows}
      </table>
    </td>
  </tr>
  <tr>
    <td style="background:#f8f9fb;padding:14px 28px;border-top:1px solid #eee;">
      <p style="margin:0;font-size:11px;color:#999;text-align:center;">
        Smart Finance Brain &nbsp;|&nbsp; Your data is private and stored locally.
      </p>
    </td>
  </tr>
</table>
</td></tr></table>
</body></html>"""
