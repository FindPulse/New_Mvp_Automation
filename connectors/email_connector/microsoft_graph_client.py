from __future__ import annotations

from pathlib import Path
from typing import Optional

import msal
import requests


class MicrosoftGraphEmailClient:
    """Microsoft Graph email connector extracted from the original Streamlit app."""

    def __init__(
        self,
        client_id: str,
        authority: str = "https://login.microsoftonline.com/common",
        scopes: Optional[list[str]] = None,
        cache_file: str = "msal_token_cache.bin",
    ) -> None:
        self.client_id = client_id
        self.authority = authority
        self.scopes = scopes or ["User.Read", "Mail.Read"]
        self.cache_file = Path(cache_file)
        self.cache = self._load_token_cache()
        self.app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority,
            token_cache=self.cache,
        )

    def _load_token_cache(self) -> msal.SerializableTokenCache:
        cache = msal.SerializableTokenCache()
        if self.cache_file.exists():
            cache.deserialize(self.cache_file.read_text(encoding="utf-8"))
        return cache

    def save_token_cache(self) -> None:
        if self.cache.has_state_changed:
            self.cache_file.write_text(self.cache.serialize(), encoding="utf-8")

    def acquire_token_silent(self) -> Optional[str]:
        accounts = self.app.get_accounts()
        if not accounts:
            return None
        result = self.app.acquire_token_silent(self.scopes, account=accounts[0])
        if result and "access_token" in result:
            self.save_token_cache()
            return result["access_token"]
        return None

    def initiate_device_flow(self) -> dict:
        return self.app.initiate_device_flow(scopes=self.scopes)

    def acquire_token_by_device_flow(self, flow: dict) -> dict:
        result = self.app.acquire_token_by_device_flow(flow)
        self.save_token_cache()
        return result

    @staticmethod
    def fetch_profile(access_token: str) -> dict:
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def fetch_recent_attachment_emails(access_token: str, search_text: str = "", limit: int = 100) -> list[dict]:
        headers = {"Authorization": f"Bearer {access_token}"}
        email_url = (
            "https://graph.microsoft.com/v1.0/me/messages"
            f"?$top={limit}"
            "&$select=id,subject,from,receivedDateTime,hasAttachments"
            "&$orderby=receivedDateTime desc"
        )
        response = requests.get(email_url, headers=headers, timeout=30)
        response.raise_for_status()
        emails = response.json().get("value", [])
        attachment_emails: list[dict] = []

        for email in emails:
            if not email.get("hasAttachments"):
                continue
            subject = email.get("subject") or ""
            sender = email.get("from", {}).get("emailAddress", {})
            from_name = sender.get("name") or ""
            from_email = sender.get("address") or ""
            search_area = f"{subject} {from_name} {from_email}".lower()
            if search_text and search_text.lower() not in search_area:
                continue

            attachment_url = f"https://graph.microsoft.com/v1.0/me/messages/{email.get('id')}/attachments"
            attachment_response = requests.get(attachment_url, headers=headers, timeout=30)
            attachment_response.raise_for_status()
            attachments = attachment_response.json().get("value", [])
            excel_csv_files = []
            for attachment in attachments:
                file_name = attachment.get("name") or ""
                if file_name.lower().endswith((".csv", ".xlsx", ".xls")):
                    excel_csv_files.append(
                        {
                            "attachment_id": attachment.get("id"),
                            "file_name": file_name,
                            "size": attachment.get("size"),
                        }
                    )
            if excel_csv_files:
                attachment_emails.append(
                    {
                        "message_id": email.get("id"),
                        "subject": subject,
                        "from_name": from_name,
                        "from_email": from_email,
                        "received": email.get("receivedDateTime"),
                        "files": ", ".join([file["file_name"] for file in excel_csv_files]),
                        "attachments": excel_csv_files,
                    }
                )
        return attachment_emails

    @staticmethod
    def download_attachment(access_token: str, message_id: str, attachment_id: str) -> bytes:
        download_url = (
            f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/attachments/{attachment_id}/$value"
        )
        response = requests.get(
            download_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=60,
        )
        response.raise_for_status()
        return response.content
