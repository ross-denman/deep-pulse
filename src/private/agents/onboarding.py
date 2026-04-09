import os
import json
import logging
from typing import TypedDict, List, Annotated
from datetime import datetime, timezone
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

# Setup logging
logger = logging.getLogger("socratic_onboarder")

class AgentState(TypedDict):
    messages: List[BaseMessage]
    profile: dict
    question_count: int

from src.public.core.llm_client import llm


def get_onboarding_prompt():
    return """You are the Socratic Onboarding Agent for the Notary Nexus.
Your goal is to perform a deep investigative interview to build a 'User Interest Profile'. 
This profile will drive autonomous OSINT probes.

STRATEGY: 'Peel the Onion'
1. Start broad (Sectors like Water, Aviation, Power).
2. Challenge the user based on their answers. (e.g., 'If we track water rights, should we monitor the capital flow from src.private equity firms?')
3. Narrow down to specific Keywords, Regions, and Entities.

GOAL: Extract JSON-like interests (Perimeters, Keywords, Entities).

Current Profile: {profile}
Question Number: {count}/7

If you have enough information or reached 7 questions, conclude by saying 'ONBOARDING_COMPLETE' followed by the final summary of their interests.
"""

def socratic_step(state: AgentState):
    """The brain of the Socratic interview."""
    prompt = get_onboarding_prompt().format(
        profile=json.dumps(state['profile']),
        count=state['question_count']
    )
    
    messages = [SystemMessage(content=prompt)] + state['messages']
    response = llm.invoke(messages)
    
    # Simple extraction logic (can be refined with Pydantic)
    # This is where we update the profile dict based on the conversation
    
    return {
        "messages": [response],
        "question_count": state['question_count'] + 1
    }

def build_onboarding_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("socratic_step", socratic_step)
    workflow.set_entry_point("socratic_step")
    
    # Continue until completion or limit
    workflow.add_conditional_edges(
        "socratic_step",
        lambda x: "end" if x['question_count'] > 7 or "ONBOARDING_COMPLETE" in x['messages'][-1].content else "continue",
        {
            "end": END,
            "continue": "socratic_step"
        }
    )
    
    return workflow.compile()

class SocraticOnboarder:
    def __init__(self, profile_path: str = "harvest/user_profile.json"):
        self.profile_path = Path(profile_path)
        self.graph = build_onboarding_graph()

    def save_profile(self, profile: dict):
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.profile_path, 'w') as f:
            json.dump(profile, f, indent=4)
        logger.info(f"Sovereign Interest Profile saved to {self.profile_path}")

    async def run_cli_session(self):
        """Standard terminal-based interaction for bridge.py onboard."""
        print("\n" + "="*50)
        print("NEXUS ONBOARDING: SECURE SOCRATIC CHANNEL ACTIVE")
        print("="*50 + "\n")
        
        state = {
            "messages": [],
            "profile": {"perimeters": [], "keywords": [], "entities": []},
            "question_count": 0
        }
        
        while True:
            # Run graph step
            result = self.graph.invoke(state)
            state.update(result)
            
            ai_msg = state['messages'][-1].content
            print(f"\n[Nexus Auditor]: {ai_msg}")
            
            if "ONBOARDING_COMPLETE" in ai_msg:
                # Final Pass: Extract JSON from AI concluding message
                # For now, we'll use a simple regex or prompt for structured extraction
                self.save_profile(state['profile'])
                break
                
            user_input = input("\n[Sovereign User]: ")
            state['messages'].append(HumanMessage(content=user_input))

if __name__ == "__main__":
    import asyncio
    onboarder = SocraticOnboarder()
    asyncio.run(onboarder.run_cli_session())
