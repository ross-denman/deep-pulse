import imaplib
import email
import logging
import os
from typing import List, Dict, Any
from pathlib import Path

# Robust PROJECT_ROOT calculation
_current_file = Path(__file__).resolve()
if "src" in _current_file.parts:
    PROJECT_ROOT = _current_file.parent.parent.parent
else:
    PROJECT_ROOT = _current_file.parent.parent

from src.public.storage.state_machine import MeshStateMachine
from src.public.core.identity import load_identity
from src.public.core.scent_engine import ScentEngine

logger = logging.getLogger("email_ingress")

class EmailIngress:
    """
    Ingests investigative data from secure IMAP channels.
    Converts email digests (e.g., arXiv, Newsletters) into Mesh Pulses.
    """
    def __init__(self):
        self.host = os.getenv("NOTARY_IMAP_HOST")
        self.port = int(os.getenv("NOTARY_IMAP_PORT", 993))
        self.user = os.getenv("NOTARY_IMAP_USER")
        self.password = os.getenv("NOTARY_IMAP_PASS")
        
        self.state_machine = MeshStateMachine()
        self.identity = load_identity()
        self.scent_engine = ScentEngine()

    def connect(self):
        """Establishes SSL connection to the IMAP server."""
        if not all([self.host, self.user, self.password]):
            logger.error("IMAP configuration missing in .env")
            return None
            
        try:
            mail = imaplib.IMAP4_SSL(self.host, self.port)
            mail.login(self.user, self.password)
            return mail
        except Exception as e:
            logger.error(f"Failed to connect to IMAP: {e}")
            return None

    def fetch_latest_emails(self, folder: str = "INBOX", limit: int = 5) -> List[Dict[str, Any]]:
        """Fetches the latest email headers and bodies from the specified folder."""
        mail = self.connect()
        if not mail: return []
        
        pulses = []
        try:
            mail.select(folder)
            status, messages = mail.search(None, "ALL")
            if status != "OK": return []
            
            # Get the latest message IDs
            msg_ids = messages[0].split()
            latest_ids = msg_ids[-limit:]
            
            for msg_id in reversed(latest_ids):
                status, data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK": continue
                
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                subject = msg["Subject"]
                sender = msg["From"]
                date = msg["Date"]
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()
                
                pulses.append({
                    "source": f"email://{sender}",
                    "title": subject,
                    "timestamp": date,
                    "content": body,
                    "meta": {"msg_id": msg_id.decode()}
                })
                
            mail.logout()
        except Exception as e:
            logger.error(f"Error during IMAP extraction: {e}")
            
        return pulses

    def ingest_to_mesh(self, folder: str = "INBOX", limit: int = 5):
        """Converts emails into Mesh Pulses and stages them in the State Machine."""
        emails = self.fetch_latest_emails(folder, limit)
        logger.info(f"Ingesting {len(emails)} emails into The Chronicle.")
        
        for e in emails:
            # We treat each email as a 'Pulse' that triggers the Scent Engine
            pulse_id = f"email_{e['meta']['msg_id']}"
            
            # Stage as a Finding with the Scent Engine trigger
            logger.info(f"  ↳ Internalizing Pulse: {e['title']} from {e['source']}")
            
            # Pack as a pulse compatible with scent engine
            pulse = {
                "id": pulse_id,
                "data": {"title": e["title"], "content": e["content"], "entities": []}
            }
            
            # Trigger Cascades
            self.scent_engine.process_pulse(pulse)
            
        return len(emails)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingress = EmailIngress()
    ingress.ingest_to_mesh()
