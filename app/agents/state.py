from typing import Annotated, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ScrapedSource(TypedDict):
    url: str
    title: str
    markdown: str


class AgentState(TypedDict):
    target_url: str
    query: Optional[str]
    scraped_sources: list[ScrapedSource]
    extracted_entities: Optional[dict]
    cypher_write_query: Optional[str]
    cypher_write_params: Optional[dict]
    hitl_job_id: Optional[str]
    hitl_decision: Optional[str]
    hitl_feedback: Optional[str]
    query_results: Optional[list[dict]]
    final_answer: Optional[str]
    validation_passed: Optional[bool]
    validation_notes: Optional[str]
    messages: Annotated[list[BaseMessage], add_messages]
    error: Optional[str]
    retry_count: int
