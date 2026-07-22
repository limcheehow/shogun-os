#!/usr/bin/env python3
"""
Gmail Draft Creator — creates Gmail drafts via the Gmail API (never sends).

Single draft mode:
  python3 gmail-draft.py --to "recipient@example.com" --subject "Subject" --body "<p>HTML body</p>"

Batch mode (reads drafts from a markdown file):
  python3 gmail-draft.py --source drafts.md [--cc CC] [--dry-run] [--skip N]

Configure via env vars:
  GMAIL_SENDER_NAME  — sender display name (default: "Agent")
  GMAIL_SENDER_EMAIL — sender email address (default: "agent@example.com")
  HERMES_PROFILE     — profile for Google token (default: "crm-manager")

Output: JSON with draft_id(s), message_id(s), thread_id(s) on stdout.
Errors go to stderr with exit code 1.
"""
import os, sys, json, base64, re, argparse, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

SENDER_NAME = os.environ.get("GMAIL_SENDER_NAME", "Agent")
SENDER_EMAIL = os.environ.get("GMAIL_SENDER_EMAIL", "agent@example.com")
HERMES_PROFILE = os.environ.get("HERMES_PROFILE", "crm-manager")
TOKEN_DIR = os.environ.get(
    "HERMES_TOKEN_DIR",
    os.path.expanduser(f"~/.hermes/profiles/{HERMES_PROFILE}")
)


def get_token_path(profile=None):
    profile = profile or HERMES_PROFILE
    token_dir = os.environ.get(
        "HERMES_TOKEN_DIR",
        os.path.expanduser(f"~/.hermes/profiles/{profile}")
    )
    return os.path.join(token_dir, "google_token.json")


def load_credentials(profile=None):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    token_path = get_token_path(profile)
    if not os.path.exists(token_path):
        print(json.dumps({"error": f"Token file not found: {token_path}"}), file=sys.stderr)
        sys.exit(1)
    with open(token_path) as f:
        token_data = json.load(f)
    creds = Credentials.from_authorized_user_info(token_data)
    if creds.expired and creds.refresh_token:
        print("Token expired, refreshing...", file=sys.stderr)
        creds.refresh(Request())
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
        print("Token refreshed and saved.", file=sys.stderr)
    return creds


def build_service(profile=None):
    from googleapiclient.discovery import build
    return build('gmail', 'v1', credentials=load_credentials(profile))


def html_to_text(html):
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text


def create_draft(service, to_email, subject, body_html, cc_email=None,
                 from_name=None, from_email=None):
    from_name = from_name or SENDER_NAME
    from_email = from_email or SENDER_EMAIL
    msg = MIMEMultipart('alternative')
    msg['From'] = formataddr((from_name, from_email))
    msg['To'] = to_email
    if cc_email:
        msg['Cc'] = cc_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_to_text(body_html), 'plain'))
    msg.attach(MIMEText(body_html, 'html'))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
    return service.users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()


def parse_markdown_drafts(filepath):
    """Parse a markdown file of email drafts into a list of dicts."""
    with open(filepath) as f:
        content = f.read()
    sections = re.split(r'\n---\n', content)
    drafts = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        header_match = re.search(
            r'^##\s+\d+\.\s+(.+?)\s+[—–]\s+(.+?)\s+[—–]\s+(\S+@\S+)',
            section, re.MULTILINE
        )
        if not header_match:
            continue
        to_email = header_match.group(3).strip()
        subject_match = re.search(r'\*\*Subject:\*\*\s*(.+)', section)
        if not subject_match:
            continue
        subject = subject_match.group(1).strip()
        subject_line_end = section.find(subject_match.group(0)) + len(subject_match.group(0))
        body_section = section[subject_line_end:].lstrip('\n').strip()
        drafts.append({
            'to': to_email,
            'contact': header_match.group(1).strip(),
            'company': header_match.group(2).strip(),
            'subject': subject,
            'body_text': body_section,
        })
    return drafts


def text_to_html(text):
    paragraphs = re.split(r'\n\s*\n', text)
    html_parts = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para = re.sub(r'(https?://[^\s<]+)', r'<a href="\1">\1</a>', para)
        para = para.replace('\n', '<br>\n')
        html_parts.append(f'<p>{para}</p>')
    return '\n'.join(html_parts)


def main():
    parser = argparse.ArgumentParser(description='Create Gmail drafts (never sends)')
    parser.add_argument('--to', help='Recipient email (single-draft mode)')
    parser.add_argument('--subject', help='Email subject (single-draft mode)')
    parser.add_argument('--body', help='Email body as HTML (single-draft mode)')
    parser.add_argument('--source', help='Markdown file with multiple drafts (batch mode)')
    parser.add_argument('--cc', default=None, help='CC email address')
    parser.add_argument('--from-name', default=SENDER_NAME, help='Sender display name')
    parser.add_argument('--from-email', default=SENDER_EMAIL, help='Sender email')
    parser.add_argument('--profile', default=HERMES_PROFILE, help='Hermes profile for token')
    parser.add_argument('--dry-run', action='store_true', help='Parse and show what would be sent (batch only)')
    parser.add_argument('--skip', type=int, default=0, help='Skip first N drafts for resuming (batch only)')

    args = parser.parse_args()

    if args.source:
        if not os.path.exists(args.source):
            print(json.dumps({"error": f"Source file not found: {args.source}"}), file=sys.stderr)
            sys.exit(1)
        drafts = parse_markdown_drafts(args.source)
        if args.skip > 0:
            drafts = drafts[args.skip:]
        if args.dry_run:
            output = {"mode": "dry_run", "total": len(drafts), "drafts": []}
            for i, d in enumerate(drafts, 1):
                output["drafts"].append({
                    "index": i, "to": d['to'], "contact": d['contact'],
                    "company": d['company'], "subject": d['subject'],
                })
            print(json.dumps(output, indent=2))
            return
        service = build_service(args.profile)
        results, failures = [], []
        for i, d in enumerate(drafts, 1):
            try:
                body_html = text_to_html(d['body_text'])
                draft = create_draft(service, d['to'], d['subject'], body_html,
                                     cc_email=args.cc, from_name=args.from_name,
                                     from_email=args.from_email)
                results.append({
                    'index': i, 'to': d['to'], 'contact': d['contact'],
                    'company': d['company'], 'subject': d['subject'],
                    'draft_id': draft['id'], 'message_id': draft['message']['id'],
                    'status': 'created'
                })
                print(f"[{i}/{len(drafts)}] ✅ {d['contact']} — draft_id: {draft['id']}", file=sys.stderr)
                if i < len(drafts):
                    time.sleep(0.25)
            except Exception as e:
                failures.append({'index': i, 'to': d['to'], 'contact': d['contact'], 'error': str(e)})
                print(f"[{i}/{len(drafts)}] ❌ {d['contact']} — {e}", file=sys.stderr)
        output = {'mode': 'batch', 'total': len(drafts), 'created': len(results),
                  'failed': len(failures), 'drafts': results, 'failures': failures}
        print(json.dumps(output, indent=2))
        if failures:
            sys.exit(1)
        return

    if not args.to or not args.subject or not args.body:
        parser.print_help()
        sys.exit(1)
    try:
        service = build_service(args.profile)
        draft = create_draft(service, args.to, args.subject, args.body,
                             cc_email=args.cc, from_name=args.from_name,
                             from_email=args.from_email)
        print(json.dumps({
            'draft_id': draft['id'], 'message_id': draft['message']['id'],
            'thread_id': draft['message'].get('threadId', ''),
            'to': args.to, 'subject': args.subject, 'cc': args.cc or '', 'status': 'created'
        }, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e), 'to': args.to, 'subject': args.subject,
                          'status': 'failed'}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()