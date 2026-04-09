import os
import logging
from langchain_openai import ChatOpenAI

logger = logging.getLogger("llm_client")

def get_llm():
    """
    Returns an LLM client based on environment configuration.
    Toggles between local Ollama and OpenRouter.
    """
    use_ollama = os.getenv("USE_OLLAMA", "true").lower() == "true"
    
    if use_ollama:
        base_url = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
        model = os.getenv("OLLAMA_MODEL", "llama3")
        logger.info(f"Initializing Local LLM (Ollama) -> {model} via {base_url}")
        return ChatOpenAI(
            base_url=base_url,
            api_key="ollama",  # Not used for local
            model=model,
            temperature=0.4
        )
    else:
        # OpenRouter Configuration
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("MODEL", "openrouter/free")
        base_url = "https://openrouter.ai/api/v1"
        
        # Optional: OpenRouter specific headers for rankings/site-ID
        default_headers = {
            "HTTP-Referer": "https://github.com/soul-ledger/deep-pulse",
            "X-Title": "Nexus Intelligence Engine"
        }
        
        logger.info(f"Initializing Global LLM (OpenRouter) -> {model}")
        return ChatOpenAI(
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
            base_url=base_url,
            model=model,
            temperature=0.4,
            default_headers=default_headers
        )

# Singleton instance for the session
llm = get_llm()
