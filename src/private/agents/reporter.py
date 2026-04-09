import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.public.core.models import PeriodicalBrief

# Setup logging
logger = logging.getLogger("narrative_reporter")

from src.public.core.llm_client import llm


REPORT_DIR = Path("harvest/briefs")

class ReporterAgent:
    """
    The Narrative Reporter Agent.
    Translates raw JSON synthesis into a Sovereign Intelligence Brief (Markdown).
    """
    def __init__(self):
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

    def get_system_prompt(self):
        return """You are the Nexus Intelligence Reporter. 
Your goal is to synthesize a JSON finding digest into a high-impact, professional intelligence brief focusing on MACRO-ANOMALIES.

STRATEGIC FOCUS: 'The Geopolitical Backbone'
- Prioritize: Commodity Integrity (Energy/Water), Security Escalation, Technological Edge, and Geopolitical Policy shifts.
- Synthesis Logic: Instead of reporting individual social media grains, cross-reference social volatility with institutional anchors.
- Tone: Forensic, authoritative, and sovereign.

REPORTER STRUCTURE:
1. MACRO-ANOMALY SUMMARY: Synthesize confirmed bottlenecks or policy shifts.
2. EPISTEMIC GAP ANALYSIS: Cross-reference 'unverified social hysteria' against 'institutional stability'.
3. SOVEREIGN ACTION ITEMS: Suggested expansions for the Investigative Agenda.
"""

    async def generate_markdown_report(self, brief: PeriodicalBrief) -> str:
        """Uses LLM to generate the final narrative."""
        prompt = self.get_system_prompt()
        findings_json = brief.model_dump_json(indent=2)
        
        human_msg = f"Please synthesize the following JSON digest into a periodical brief:\n\n{findings_json}"
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=human_msg)
        ]
        
        response = await llm.ainvoke(messages)
        return response.content

    def save_report(self, markdown_content: str):
        """Saves the brief to the gitignored briefs directory."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
        file_path = REPORT_DIR / f"NexusBrief_{timestamp}.md"
        
        with open(file_path, 'w') as f:
            f.write(markdown_content)
        
        logger.info(f"Intelligence Brief saved to {file_path}")
        return file_path

if __name__ == "__main__":
    # Test stub
    import asyncio
    from src.private.briefing_engine import BriefingEngine
    
    async def test():
        engine = BriefingEngine()
        digest = engine.synthesize_digest(hours_back=168)
        reporter = ReporterAgent()
        md = await reporter.generate_markdown_report(digest)
        reporter.save_report(md)
    
    asyncio.run(test())
