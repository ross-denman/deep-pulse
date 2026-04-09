import imaplib
import email
import logging
import os
import re
import time
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime, timezone

# Robust PROJECT_ROOT calculation
_current_file = Path(__file__).resolve()
if "src" in _current_file.parts:
    PROJECT_ROOT = _current_file.parent.parent.parent.parent
else:
    PROJECT_ROOT = _current_file.parent.parent

from src.public.storage.state_machine import MeshStateMachine
from src.public.core.identity import load_identity
from src.public.core.scent_engine import ScentEngine
from src.public.core.kuzu_driver import KuzuDriver

logger = logging.getLogger("email_ingress")

def html_to_markdown(html_content: str) -> str:
    """Minimalist HTML to Markdown converter for zero-dependency environments."""
    if not html_content: return ""
    # Remove script and style elements
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL)
    # Convert common tags to markdown
    text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'# \1\n', text)
    text = re.sub(r'<a[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a>', r'[\2](\1)', text)
    text = re.sub(r'<(strong|b)[^>]*>(.*?)</\1>', r'**\2**', text)
    text = re.sub(r'<(em|i)[^>]*>(.*?)</\1>', r'*\2*', text)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text)
    text = re.sub(r'<br[^>]*>', r'\n', text)
    # Strip all other tags
    text = re.sub(r'<[^>]*>', '', text)
    return text.strip()

class EmailIngress:
    """
    Ingests investigative data from secure IMAP channels.
    Strategic Guardrails: Whitelisting, Read-and-Delete, and Graph Injection.
    """
    def __init__(self):
        self.host = os.getenv("NOTARY_IMAP_HOST")
        self.port = int(os.getenv("NOTARY_IMAP_PORT", 993))
        self.user = os.getenv("NOTARY_IMAP_USER")
        self.password = os.getenv("NOTARY_IMAP_PASS")
        
        # Security: Whitelist of allowed senders
        whitelist_raw = os.getenv("NOTARY_IMAP_WHITELIST", "noreply@arxiv.org")
        self.whitelist = [s.strip().lower() for s in whitelist_raw.split(",")]
        
        self.state_machine = MeshStateMachine()
        self.identity = load_identity()
        self.scent_engine = ScentEngine()
        self.kuzu = KuzuDriver()

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

    def process_inbox(self, delete_after: bool = True):
        """
        Scans the inbox, validates senders, ingests findings, and cleans up.
        Forensic Guardrail: Keeps the Hostinger footprint at near-zero.
        """
        mail = self.connect()
        if not mail: return
        
        try:
            mail.select("INBOX")
            # Only process UNSEEN to be efficient, or ALL if we delete anyway
            status, messages = mail.search(None, "ALL")
            if status != "OK": return
            
            msg_ids = messages[0].split()
            logger.info(f"Scanning {len(msg_ids)} messages in Forensic Intake...")
            
            processed_count = 0
            for msg_id in msg_ids:
                status, data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK": continue
                
                msg = email.message_from_bytes(data[0][1])
                sender = email.utils.parseaddr(msg["From"])[1].lower()
                
                # Guardrail: Whitelist check
                if sender not in self.whitelist:
                    logger.warning(f"Skipping unauthorized sender: {sender}")
                    continue
                
                subject = msg["Subject"]
                logger.info(f"Processing '{subject}' from {sender}")
                
                # Attachment Safety: Parse body first
                content = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        cdisp = str(part.get("Content-Disposition"))
                        
                        if ctype == "text/plain" and "attachment" not in cdisp:
                            content = part.get_payload(decode=True).decode()
                            break
                        elif ctype == "text/html" and not content:
                            html = part.get_payload(decode=True).decode()
                            content = html_to_markdown(html)
                else:
                    content = msg.get_payload(decode=True).decode()
                
                # Ingest into Graph (Kuzu)
                pulse_id = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{msg_id.decode()}"
                self._ingest_to_graph(pulse_id, subject, content, sender)
                
                # Trigger Scent Cascades
                pulse = {
                    "id": pulse_id,
                    "data": {"title": subject, "content": content, "entities": []}
                }
                self.scent_engine.process_pulse(pulse)
                
                # Guardrail: Read-and-Delete
                if delete_after:
                    mail.store(msg_id, '+FLAGS', '\\Deleted')
                
                processed_count += 1
                
            # Final Cleanup
            if delete_after:
                mail.expunge()
                logger.info(f"Cleanup Complete: {processed_count} messages purged from host.")
            
            mail.logout()
        except Exception as e:
            logger.error(f"Forensic Intake Error: {e}")

    def _ingest_to_graph(self, pulse_id: str, title: str, content: str, source: str):
        """Internalizes the finding into the Kùzu Knowledge Graph."""
        try:
            self.kuzu.connect()
            # 1. Create Chronicle Entry
            self.kuzu._conn.execute(
                "CREATE (c:ChronicleEntry {id: $id, title: $title, timestamp: $ts})", 
                {"id": pulse_id, "title": title, "ts": datetime.now(timezone.utc).isoformat()}
            )
            # 2. Add Source Entity
            source_name = f"Source: {source}"
            check = self.kuzu._conn.execute("MATCH (e:Entity {name: $name}) RETURN e.name", {"name": source_name})
            if not check.has_next():
                 self.kuzu._conn.execute(
                    "CREATE (e:Entity {name: $name, type: 'EMAIL_SOURCE', description: $desc})",
                    {"name": source_name, "desc": f"Automated Ingress from {source}"}
                )
            # 3. Link
            self.kuzu._conn.execute(
                "MATCH (e:Entity {name: $name}), (c:ChronicleEntry {id: $id}) "
                "CREATE (e)-[:MENTIONED_IN]->(c)",
                {"name": source_name, "id": pulse_id}
            )
            logger.info(f"Graph Injection Successful for Pulse {pulse_id}")
        except Exception as e:
            logger.error(f"Kuzu Ingestion Failed: {e}")
        finally:
            self.kuzu.close()

def main():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    ingress = EmailIngress()
    
    interval = int(os.getenv("NOTARY_IMAP_INTERVAL", 300)) # Default 5 mins
    logger.info(f"Starting IMAP Watcher (Interval: {interval}s)...")
    
    while True:
        try:
            ingress.process_inbox(delete_after=True)
        except Exception as e:
            logger.error(f"Watcher Loop Error: {e}")
        
        time.sleep(interval)

if __name__ == "__main__":
    main()
