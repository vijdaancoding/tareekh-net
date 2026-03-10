"""
LangGraph agent for querying Pakistani political members from Neo4j.
"""

import json
from typing import Any
from neo4j import GraphDatabase
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage


class GraphState(TypedDict):
    """State for the graph."""
    messages: list[BaseMessage]
    query: str
    neo4j_results: dict[str, Any]
    response: str


class Neo4jQuerier:
    """Class to query Neo4j database."""
    
    def __init__(self, uri: str, username: str, password: str):
        """Initialize Neo4j connection."""
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
    
    def close(self):
        """Close the driver."""
        self.driver.close()
    
    def query_members_by_party(self, party_name: str) -> list[dict]:
        """Get all members of a specific party."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Person)-[:MEMBER_OF]->(party:Party)
                WHERE party.name CONTAINS $party_name
                RETURN p.name as name, p.birth_year as birth_year, p.bio as bio
                ORDER BY p.name
                """,
                party_name=party_name
            )
            return [dict(record) for record in result]
    
    def query_prime_ministers(self) -> list[dict]:
        """Get all Prime Ministers."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Person)-[r:HELD_POSITION]->(pos:Position)
                WHERE pos.title = 'Prime Minister'
                RETURN p.name as name, p.birth_year as birth_year, 
                       r.start_year as start_year, r.end_year as end_year
                ORDER BY r.start_year DESC
                """
            )
            return [dict(record) for record in result]
    
    def query_person_info(self, name: str) -> dict:
        """Get detailed information about a person."""
        with self.driver.session() as session:
            # Get person info
            person_result = session.run(
                """
                MATCH (p:Person)
                WHERE p.name CONTAINS $name
                RETURN p.name as name, p.birth_year as birth_year, p.bio as bio
                LIMIT 1
                """,
                name=name
            ).single()
            
            if not person_result:
                return {"error": f"Person '{name}' not found"}
            
            person_data = dict(person_result)
            
            # Get parties
            parties = session.run(
                """
                MATCH (p:Person)-[r:MEMBER_OF]->(party:Party)
                WHERE p.name CONTAINS $name
                RETURN party.name as party, r.start_year as start_year, r.end_year as end_year
                """,
                name=name
            )
            person_data["parties"] = [dict(p) for p in parties]
            
            # Get positions
            positions = session.run(
                """
                MATCH (p:Person)-[r:HELD_POSITION]->(pos:Position)
                WHERE p.name CONTAINS $name
                RETURN pos.title as position, r.start_year as start_year, r.end_year as end_year
                """,
                name=name
            )
            person_data["positions"] = [dict(pos) for pos in positions]
            
            # Get collaborations
            collabs = session.run(
                """
                MATCH (p:Person)-[r:COLLABORATED_WITH]->(other:Person)
                WHERE p.name CONTAINS $name
                RETURN other.name as collaborator, r.description as description
                """,
                name=name
            )
            person_data["collaborators"] = [dict(c) for c in collabs]
            
            return person_data
    
    def query_political_network(self) -> dict:
        """Get overall political network statistics."""
        with self.driver.session() as session:
            people = session.run("MATCH (p:Person) RETURN count(p) as count").single()["count"]
            parties = session.run("MATCH (p:Party) RETURN count(p) as count").single()["count"]
            positions = session.run("MATCH (p:Position) RETURN count(p) as count").single()["count"]
            
            top_parties = session.run(
                """
                MATCH (p:Person)-[:MEMBER_OF]->(party:Party)
                RETURN party.name as party, count(p) as member_count
                ORDER BY member_count DESC
                """
            )
            top_parties_data = [dict(p) for p in top_parties]
            
            return {
                "total_people": people,
                "total_parties": parties,
                "total_positions": positions,
                "top_parties": top_parties_data
            }


class PoliticalGraphAgent:
    """LangGraph agent for querying political data."""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_pass: str, 
                 openai_api_key: str = None):
        """Initialize the agent."""
        self.querier = Neo4jQuerier(neo4j_uri, neo4j_user, neo4j_pass)
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=openai_api_key,
            temperature=0.7
        )
    
    def close(self):
        """Close connections."""
        self.querier.close()
    
    def process_query(self, state: GraphState) -> Command:
        """Process user query and determine what Neo4j queries to run."""
        messages = state.get("messages", [])
        query = state.get("query", "")
        
        # Create a system prompt
        system_prompt = """You are an expert analyst of Pakistani politics.
        You have access to a Neo4j database with information about Pakistani political figures.
        
        Based on the user's query, respond with clear, informative answers using the data provided.
        If you need more specific data, you can ask for it."""
        
        # Add the current query to messages if not already there
        if not messages or (isinstance(messages[-1], HumanMessage) and query not in messages[-1].content):
            messages.append(HumanMessage(content=query))
        
        # Determine what to query based on the input
        results = {}
        query_lower = query.lower()
        
        if "prime minister" in query_lower:
            results["prime_ministers"] = self.querier.query_prime_ministers()
        
        if "member" in query_lower and "party" in query_lower:
            # Extract party name
            for party in ["ppp", "pmln", "ptm", "jui", "mqm"]:
                if party.lower() in query_lower:
                    results[f"party_members_{party}"] = self.querier.query_members_by_party(party)
                    break
        
        if "network" in query_lower or "statistics" in query_lower or "overview" in query_lower:
            results["network_stats"] = self.querier.query_political_network()
        
        # Check if query is about a specific person
        keywords = ["who is", "about", "tell me", "information", "details"]
        if any(kw in query_lower for kw in keywords):
            # Extract potential person names
            words = query.split()
            for i, word in enumerate(words):
                if word.lower() in ["is", "about", "tell"]:
                    if i + 1 < len(words):
                        potential_name = " ".join(words[i+1:i+3])
                        person_info = self.querier.query_person_info(potential_name)
                        if "error" not in person_info:
                            results["person_info"] = person_info
                            break
        
        # If no specific queries matched, get network overview
        if not results:
            results["network_stats"] = self.querier.query_political_network()
        
        state["neo4j_results"] = results
        
        return Command(goto="generate_response")
    
    def generate_response(self, state: GraphState) -> Command:
        """Generate LLM response based on Neo4j results."""
        messages = state.get("messages", [])
        query = state.get("query", "")
        results = state.get("neo4j_results", {})
        
        # Format the results for the LLM
        results_text = json.dumps(results, indent=2, default=str)
        
        # Create a prompt for the LLM
        llm_prompt = f"""Based on the following data from the Pakistani political database, 
        please answer this question: {query}
        
        Data:
        {results_text}
        
        Provide a comprehensive and informative answer."""
        
        messages.append(HumanMessage(content=llm_prompt))
        
        # Get response from LLM
        response = self.llm.invoke(messages)
        
        messages.append(response)
        state["messages"] = messages
        state["response"] = response.content
        
        return Command(goto=END)
    
    def create_graph(self):
        """Create the LangGraph graph."""
        graph_builder = StateGraph(GraphState)
        
        # Add nodes
        graph_builder.add_node("process_query", self.process_query)
        graph_builder.add_node("generate_response", self.generate_response)
        
        # Set up edges
        graph_builder.add_edge(START, "process_query")
        
        # Compile and return
        return graph_builder.compile()
    
    def query(self, question: str) -> str:
        """Query the political graph with a question."""
        graph = self.create_graph()
        
        initial_state = {
            "messages": [],
            "query": question,
            "neo4j_results": {},
            "response": ""
        }
        
        final_state = graph.invoke(initial_state)
        
        return final_state.get("response", "No response generated")


def create_political_agent(neo4j_uri: str = "bolt://localhost:7687",
                          neo4j_user: str = "neo4j",
                          neo4j_pass: str = "password",
                          openai_api_key: str = None) -> PoliticalGraphAgent:
    """Create and return a political graph agent."""
    return PoliticalGraphAgent(neo4j_uri, neo4j_user, neo4j_pass, openai_api_key)
