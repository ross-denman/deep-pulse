import os
import logging
from langchain_openai import ChatOpenAI

logger = logging.getLogger("llm_client")

def get_llm():
    """
    Returns a universal LLM client compatible with OpenAI, OpenRouter, or Ollama.
    Configured via LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL in .env.
    """
    api_key = os.getenv("LLM_API_KEY", "ollama")
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    model = os.getenv("LLM_MODEL", "llama3")
    
    logger.info(f"Initializing Core Intelligence -> {model} via {base_url}")
    
    # Custom headers for OpenRouter (ignored by other providers)
    default_headers = {
        "HTTP-Referer": "https://github.com/ross-denman/deep-pulse",
        "X-Title": "Sovereign Outpost"
    }

    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0.3,
        default_headers=default_headers
    )

# Singleton instance for the session
llm = get_llm()
