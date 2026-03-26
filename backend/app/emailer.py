import base64
from email.message import EmailMessage

from googleapiclient.discovery import build


def send_gmail_message(creds, to_email: str, subject: str, body: str, from_email: str):
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    message = EmailMessage()
    message["To"] = to_email
    message["From"] = from_email
    message["Subject"] = subject
    message.set_content(body)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
