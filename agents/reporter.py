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
        return """You are the Sovereign Distribution Reporter. 
Your goal is to synthesize finding digests into high-impact, public-facing intelligence reports.

DISTRIBUTION FOCUS: 'The Public Record'
- Prioritize: Statistical anchors, decoupling viral narratives from reality, and verifying regional stability.
- Synthesis Logic: Focus on data points that have reached the 2+1/3+1 consensus threshold.
- Tone: Objective, transparent, and sovereign.

REPORTER STRUCTURE:
1. PUBLIC FINDINGS: Clear, verified discoveries from the Discovery Mesh.
2. NARRATIVE DECOUPLING: Explicitly address and debunk viral discrepancies using statistical evidence.
3. MESH HEALTH: Brief update on regional swarm performance and consensus integrity.
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
    from src.public.core.briefing import BriefingEngine
    
    async def test():
        engine = BriefingEngine()
        digest = engine.synthesize_digest(hours_back=168)
        reporter = ReporterAgent()
        md = await reporter.generate_markdown_report(digest)
        reporter.save_report(md)
    
    asyncio.run(test())
