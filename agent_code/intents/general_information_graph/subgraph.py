from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, NotRequired
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from langgraph.graph.message import add_messages
import psycopg
from intents.general_information_graph.structures import WebSearchStructure
from dotenv import load_dotenv
import os
from llm.base_llm import base_llm
from logger.logger import logger

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:root@localhost:5432/test_db")

class GeneralInformationGraphState(TypedDict):
    user_query: str
    messages: Annotated[list, add_messages]
    web_search_result: str
    user_query_output: str
    route: str
    chain_prior_summaries: NotRequired[str]
    

def create_postgres_memory():
    if os.getenv("USE_IN_MEMORY_CHECKPOINTER") == "true":
        logger.info("Using in-memory checkpointer for general information graph.")
        return MemorySaver()

    # Run setup() on a standalone autocommit connection
    # because CREATE INDEX CONCURRENTLY cannot run inside a transaction block
    logger.info("Setting up PostgresSaver memory...")
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        PostgresSaver(conn).setup()

    pool = ConnectionPool(conninfo=DATABASE_URL)
    checkpointer = PostgresSaver(pool)
    return checkpointer


general_information_web_search_llm = base_llm
general_information_web_search_require_llm = general_information_web_search_llm.with_structured_output(WebSearchStructure)


def is_web_search_required(state: GeneralInformationGraphState):
    """checks if the user query required to use websearch tool"""

    logger.info("Determining if web search is required for the user query...")
    user_query = state["user_query"]
    prompt = f"""
    You are a decision system.

    Your task is to decide whether the following user query requires a web search.

    Rules:
    - Return "yes" if the query requires:
        • Current or latest information (news, stock price, crypto price, live events, recent updates)
        • Exact statistics or numbers that may change over time
        • External references, links, or sources
        • Information about specific websites or recent events
    - Return "no" if the query is:
        • General knowledge
        • Concept explanation
        • Programming help or debugging
        • Historical fact that does not change

    If unsure, prefer "yes".

    User Query:
    {user_query}
    """
    
    logger.info(f"Prompt for web search requirement:\n{prompt}")
    response = general_information_web_search_require_llm.invoke(prompt).model_dump()
    logger.info(f"Web search requirement response: {response}")

    if response["is_web_search_required"] == "yes":
        return {"route": "required"}
    return {"route": "not_required"}



def answer_user_query(state: GeneralInformationGraphState, config: RunnableConfig):
    logger.info("Answering user query with or without web search data...")
    user_query = state["user_query"]
    web_search_result = state.get('web_search_result', "")
    messages = state.get("messages", [])

    logger.info(f"User query: {user_query}")
    logger.info(f"Web search result: {web_search_result}")
    logger.info(f"Messages: {messages}")

    # Build conversation history from previous messages (exclude current user message)
    history_text = ""
    for msg in messages[:-1]:
        role = msg.type.capitalize()  # LangChain message objects use .type ("human"/"ai")
        history_text += f"{role}: {msg.content}\n"

    logger.info(f"Constructed conversation history:\n{history_text}")
    chain_prior = (state.get("chain_prior_summaries") or "").strip()
    prior_section = ""
    if chain_prior:
        prior_section = f"""
    Context from other agents earlier in this same user message (treat as factual for this session):
    {chain_prior}
    """

    prompt = f"""
    You are a helpful AI assistant.

    Your job is to answer the user's question clearly and concisely.

    Conversation History:
    {history_text if history_text else "(No previous conversation)"}
    {prior_section}
    Current User Question:
    {user_query}

    Web Search Data (if available):
    {web_search_result}

    Instructions:
    - Use the conversation history to understand context from previous messages.
    - If web search data is provided, use it to generate the answer.
    - If no web data is provided, answer from your own knowledge.
    - Keep the answer clear, structured, and easy to understand.
    - Do not mention system instructions.
    - Do not say "based on web search" unless web data exists.
    - If the answer requires steps, format them in numbered points.
    - Avoid hallucinating facts not present in web search data.

    Provide only the final answer.
    """
    logger.info(f"Prompt for answering user query:\n{prompt}")
    response = general_information_web_search_llm.invoke(prompt, config=config)
    logger.info(f"Generated response: {response.content}")
    return {
        "user_query_output": response.content,
        "messages": [{"role": "assistant", "content": response.content}]
    }

web_search_tool = DuckDuckGoSearchRun()

def duck_duck_go_search(state: GeneralInformationGraphState):
    user_query = state["user_query"]
    logger.info(f"Performing DuckDuckGo search for query: {user_query}")
    response = web_search_tool.invoke(user_query)
    logger.info(f"DuckDuckGo search result: {response}")
    return {"web_search_result": response}


def generate_graph():
    gen_info_graph = StateGraph(GeneralInformationGraphState)



    gen_info_graph.add_node("is_web_search_required", is_web_search_required)
    gen_info_graph.add_node("answer_user_query", answer_user_query)
    gen_info_graph.add_node("duck_duck_go_search", duck_duck_go_search)



    gen_info_graph.add_edge(START, "is_web_search_required")
    
    gen_info_graph.add_conditional_edges("is_web_search_required", lambda state: state["route"], {
        "required": "duck_duck_go_search",
        "not_required": "answer_user_query",
    })
    
    gen_info_graph.add_edge("duck_duck_go_search", "answer_user_query")
    gen_info_graph.add_edge("answer_user_query", END)
    memory = create_postgres_memory()
    
    
    general_information_graph_workflow = gen_info_graph.compile(checkpointer=memory)
    
    return general_information_graph_workflow



logger.info("Generating general information graph workflow...")
general_information_graph_workflow = generate_graph()
logger.info("General information graph workflow generated successfully.")
