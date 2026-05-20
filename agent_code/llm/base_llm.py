import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from logger.logger import logger

load_dotenv()

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

if not openrouter_api_key:
    raise ValueError("OPENROUTER_API_KEY is required (set in environment or .env).")

model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

logger.info(
    "Initializing LLM via OpenRouter: model=%s (set OPENROUTER_MODEL, OPENROUTER_API_KEY to configure)",
    model_name,
)

base_llm = ChatOpenAI(
    model=model_name,
    api_key=openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
    temperature=0,
    default_headers={
        "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:3000"),
        "X-Title": os.getenv("OPENROUTER_SITE_NAME", "Intelligent Business Agent"),
    }
)

logger.info("Base LLM initialized successfully.")
