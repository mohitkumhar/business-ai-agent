import re
import os
from pydantic import BaseModel, Field
from typing import Literal, List
from dotenv import load_dotenv
from logger.logger import logger
from langchain_core.prompts import ChatPromptTemplate
from llm.base_llm import base_llm
from schemas.responses import IntentDetectionSchema

load_dotenv()


intent_detection_llm_with_structure = base_llm.with_structured_output(
    IntentDetectionSchema
)


_GREETING_FAST = re.compile(
    r"^("
    r"hi\b|hello\b|hey\b|howdy\b|sup\b|greetings\b|"
    r"yo\b|hiya\b|what\'?s\s+up\b|wassup\b|"
    r"good\s+(morning|afternoon|evening|night)\b|"
    r"how\s+are\s+you\b|how\s+u\b|"
    r"namaste\b|namaskar\b|"
    r"thanks?\b|thank\s+you\b|thx\b|ty\b"
    r")[\s!.,?]*$",
    re.IGNORECASE,
)

_GREETING_RELAXED = re.compile(
    r"^(hi|hello|hey|howdy|good\s+(morning|afternoon|evening)|namaste|what\'?s\s+up)\b",
    re.IGNORECASE,
)

_OUT_OF_SCOPE = re.compile(
    r"\b("
    r"joke|funny|weather|prime\s+minister|trivia|riddle|"
    r"2\s*\+\s*2|who\s+is\s+the|capital\s+of|meaning\s+of\s+life"
    r")\b",
    re.IGNORECASE,
)

_HYBRID = re.compile(
    r"\b("
    r"\bloan\b|can\s+i\s+afford|afford\s+to|survive\s+if|runway|"
    r"burn\s*rate|drops?\s+\d+\s*%|revenue\s+drops?"
    r")\b",
    re.IGNORECASE,
)

_DATABASE_FACT = re.compile(
    r"\b("
    r"how\s+much\s+(revenue|sales|profit|income|expense|did|have|was)|"
    r"what\s+(is|was)\s+my\s+(net\s+)?profit|net\s+profit|"
    r"cash\s+balance|healthy\s*cash|"
    r"expenses?\s+(in|for|during)|"
    r"revenue\s+(last|this|in)|"
    r"last\s+month|this\s+year|in\s+january|ytd|quarter"
    r")\b",
    re.IGNORECASE,
)

_ADVISORY = re.compile(
    r"\b("
    r"should\s+i|is\s+it\s+a\s+good\s+idea|good\s+idea\s+to|"
    r"what\s+percentage|how\s+much\s+should\s+i\s+spend|"
    r"marketing\s+campaign|where\s+should\s+i\s+spend|"
    r"allocate\s+.*(budget|revenue|marketing)|"
    r"hire\s+\d+|hiring\s+\d+\s+employees|expand\s+my\s+business|"
    r"worth\s+it\s+to|recommend"
    r")\b",
    re.IGNORECASE,
)

_LOGS_HINT = re.compile(
    r"\b(logs?|stack\s*trace|traceback|exception|stderr|loki|error\s*message|debug\s+log)\b",
    re.IGNORECASE,
)

_METRICS_INFRA = re.compile(
    r"\b("
    r"prometheus|grafana|cadvisor|node[-_\s]?exporter|"
    r"cpu|memory|ram|disk\s*i/?o|network\s*i/?o|"
    r"request\s*rate|error\s*rate|percentile|p95|p99|"
    r"api\s*latency|service\s*latency|throughput|qps|rps|uptime|"
    r"pods?|containers?|kubernetes|k8s"
    r")\b",
    re.IGNORECASE,
)

_METRICS_BUSINESS = re.compile(
    r"\b(business\s+score|health\s*check|kpi|performance\s+metrics?)\b",
    re.IGNORECASE,
)


def _normalize_labels(intents: list[str]) -> list[str]:
    out = []
    for x in intents:
        if x == "greeting":
            out.append("greeting_request")
        elif x == "out_of_scope":
            out.append("out_of_scope_request")
        else:
            out.append(x)
    return out


def _fast_intent(text: str) -> dict | None:
    t = (text or "").strip()
    if not t:
        return None

    # Pure / short greetings → greeting_request (never out_of_scope)
    if len(t) <= 96 and _GREETING_FAST.match(t) and not _DATABASE_FACT.search(t) and not _ADVISORY.search(t):
        logger.info("Intent fast-path: greeting_request")
        return {"intent": ["greeting_request"]}

    if _OUT_OF_SCOPE.search(t):
        logger.info("Intent fast-path: out_of_scope_request (trivia / unrelated)")
        return {"intent": ["out_of_scope_request"]}

    if _LOGS_HINT.search(t) and not _METRICS_INFRA.search(t):
        return {"intent": ["logs_request"]}

    if _METRICS_INFRA.search(t) or _METRICS_BUSINESS.search(t):
        if not _DATABASE_FACT.search(t):
            return {"intent": ["metrics_request"]}

    if _HYBRID.search(t) and not _OUT_OF_SCOPE.search(t):
        logger.info("Intent fast-path: hybrid_request")
        return {"intent": ["hybrid_request"]}

    if _DATABASE_FACT.search(t):
        chain = ["database_request"]
        if _ADVISORY.search(t) and not _HYBRID.search(t):
            chain.append("advisory_request")
            logger.info("Intent fast-path: database_request + advisory_request (compound question)")
        else:
            logger.info("Intent fast-path: database_request (factual financial / ops data)")
        return {"intent": order_intents_for_execution(chain)}

    if _ADVISORY.search(t):
        logger.info("Intent fast-path: advisory_request")
        return {"intent": ["advisory_request"]}

    if len(t) <= 72 and _GREETING_RELAXED.match(t) and not _DATABASE_FACT.search(t):
        logger.info("Intent fast-path: greeting_request (relaxed opening)")
        return {"intent": ["greeting_request"]}

    return None


def _looks_like_pure_greeting(text: str) -> bool:
    """Heuristic: short casual hello without data/advice asks — never classify as out_of_scope."""
    t = (text or "").strip()
    if not t:
        return False
    if _DATABASE_FACT.search(t) or _ADVISORY.search(t):
        return False
    if len(t) <= 96 and _GREETING_FAST.match(t):
        return True
    if len(t) <= 120 and _GREETING_RELAXED.match(t):
        return True
    return False


_INTENT_SYSTEM_PROMPT = """You are an intent classifier for a business advisory agent (Intelligent Business Agent).

Classify the user message into one or more labels. Use the suffix _request exactly as shown.

Allowed intents:
- greeting_request — hi, hello, hey, good morning/evening, namaste, what's up, how are you, short thanks; any casual hello alone
- database_request — revenue, profit, expenses, cash balance, sales figures, "how much did I make", YTD numbers from their data
- general_information_request — marketing/hiring/expansion/budget planning advice without asking for a specific stored number first
- logs_request — application logs, errors, Loki, stack traces, "what failed last week"
- metrics_request — business health score, KPIs, performance metrics, or infra metrics (Prometheus/Grafana style)
- out_of_scope_request — weather, jokes, raw math puzzles, politics, clearly not business-related
- advisory_request — "should I…", strategic recommendations tied to their situation (budget rules, go/no-go)
- hybrid_request — loans, runway, affordability, "can I survive if revenue drops…"

RULES (critical):
- Any form of greeting or casual hello by itself → greeting_request (NEVER out_of_scope_request).
- Questions about business data / numbers from their records → database_request.
- Questions asking for advice/recommendations (not a specific DB figure) → general_information_request or advisory_request.
- Non-business topics → out_of_scope_request.
- Compound messages: return MULTIPLE intents in execution order — data paths (database_request, logs_request, metrics_request) first, then general_information_request, then hybrid_request, then advisory_request.

Reply only via structured output (ordered list field)."""


def detect_intent(text: str):
    try:
        text = (text or "").strip()
        logger.info("Detecting intent for query: '%s'", text)

        quick = _fast_intent(text)
        if quick is not None:
            return quick

        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", _INTENT_SYSTEM_PROMPT),
                ("human", "{text}"),
            ]
        )
        prompt = prompt_template.format_prompt(text=text)
        logger.info("Formatted prompt for intent detection: %s", prompt.to_messages())

        intent = intent_detection_llm_with_structure.invoke(prompt).model_dump()
        logger.info("Raw intent detection output: %s", intent)
        raw_list = _normalize_labels(intent.get("intent") or [])

        if raw_list and raw_list[0] == "metrics_request" and _DATABASE_FACT.search(text):
            logger.warning("Intent override: metrics_request + factual DB pattern → database_request")
            return {"intent": ["database_request"]}
        if raw_list and raw_list[0] == "advisory_request" and _DATABASE_FACT.search(text) and not _ADVISORY.search(text):
            logger.warning("Intent override: advisory + clear DB fact pattern → database_request")
            return {"intent": ["database_request"]}
        if raw_list and raw_list[0] == "database_request" and _ADVISORY.search(text) and not _DATABASE_FACT.search(text):
            logger.warning("Intent override: database + pure advisory pattern → advisory_request")
            return {"intent": ["advisory_request"]}
        if raw_list and raw_list[0] == "out_of_scope_request" and _looks_like_pure_greeting(text):
            logger.warning("Intent override: out_of_scope + greeting pattern → greeting_request")
            return {"intent": ["greeting_request"]}

        intent["intent"] = order_intents_for_execution(raw_list)
        return intent

    except Exception as e:
        logger.error("Error during intent detection for query '%s': %s", text, e, exc_info=True)
        t = (text or "").strip()
        if _GREETING_RELAXED.match(t) and len(t) <= 96:
            return {"intent": ["greeting_request"]}
        if _DATABASE_FACT.search(t):
            return {"intent": ["database_request"]}
        if _ADVISORY.search(t):
            return {"intent": ["advisory_request"]}
        return {"intent": ["general_information_request"]}


def map_app_intent_to_high_level(primary: str) -> str:
    """Map detect_intent primary string to graph high_level_intent (business subgraph)."""
    if primary in ("out_of_scope_request",):
        return "out_of_scope"
    if primary == "advisory_request":
        return "advisory"
    if primary == "hybrid_request":
        return "hybrid"
    if primary == "database_request":
        return "database"
    return "database"


MAX_CHAIN_INTENTS = 4


def order_intents_for_execution(intents: list[str]) -> list[str]:
    """Deduplicate, cap length, sort so data runs before advice. Drop stray greetings in compound turns."""
    if not intents:
        return ["general_information_request"]

    seen: set[str] = set()
    unique: list[str] = []
    for x in intents:
        if x not in seen:
            seen.add(x)
            unique.append(x)

    if len(unique) > MAX_CHAIN_INTENTS:
        logger.warning("Truncating intent chain from %s to %s", len(unique), MAX_CHAIN_INTENTS)
        unique = unique[:MAX_CHAIN_INTENTS]

    if len(unique) > 1:
        if "out_of_scope_request" in unique:
            unique = [x for x in unique if x != "out_of_scope_request"]
            if not unique:
                unique = ["out_of_scope_request"]
        if "greeting_request" in unique:
            unique = [x for x in unique if x != "greeting_request"]
            if not unique:
                unique = ["greeting_request"]

    priority = {
        "greeting_request": -1,
        "database_request": 0,
        "logs_request": 0,
        "metrics_request": 0,
        "general_information_request": 1,
        "hybrid_request": 2,
        "advisory_request": 3,
        "out_of_scope_request": 99,
    }
    indexed = [(priority.get(i, 50), idx, i) for idx, i in enumerate(unique)]
    indexed.sort()
    return [tpl[2] for tpl in indexed]
