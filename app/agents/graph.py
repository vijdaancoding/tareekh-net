from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import AgentState
from app.agents.web_scraper_agent import web_scraper_node
from app.agents.data_processor_agent import data_processor_node
from app.agents.validator_agent import validator_node, validation_router
from app.agents.cypher_write_agent import cypher_write_node, execute_write_node, hitl_router
from app.agents.cypher_query_agent import cypher_query_node, format_results_node

checkpointer = MemorySaver()


def build_ingestion_graph():
    builder = StateGraph(AgentState)

    builder.add_node("web_scraper", web_scraper_node)
    builder.add_node("data_processor", data_processor_node)
    builder.add_node("validator", validator_node)
    builder.add_node("cypher_write", cypher_write_node)
    builder.add_node("execute_write", execute_write_node)

    builder.add_edge(START, "web_scraper")
    builder.add_edge("web_scraper", "data_processor")
    builder.add_edge("data_processor", "validator")

    builder.add_conditional_edges(
        "validator",
        validation_router,
        {
            "cypher_write": "cypher_write",
            "data_processor": "data_processor",
            "end_failed": END,
        },
    )

    builder.add_conditional_edges(
        "cypher_write",
        hitl_router,
        {
            "execute_write": "execute_write",
            "end": END,
        },
    )

    builder.add_edge("execute_write", END)

    return builder.compile(checkpointer=checkpointer)


def build_query_graph():
    builder = StateGraph(AgentState)

    builder.add_node("cypher_query", cypher_query_node)
    builder.add_node("format_results", format_results_node)

    builder.add_edge(START, "cypher_query")
    builder.add_edge("cypher_query", "format_results")
    builder.add_edge("format_results", END)

    return builder.compile()


ingestion_graph = build_ingestion_graph()
query_graph = build_query_graph()
