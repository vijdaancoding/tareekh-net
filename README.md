# Tareekh Net - Pakistani Political Members Graph

A comprehensive GraphRAG system that builds a Neo4j knowledge graph of Pakistani political members and their relationships, with LangGraph-based querying capabilities.

## Features

✨ **Core Features:**
- **Neo4j Graph Database**: Stores Pakistani political members, parties, positions, and relationships
- **GraphRAG Support**: Structured knowledge graphs for retrieval-augmented generation
- **LangGraph Agent**: AI-powered querying with LangChain integration
- **Rich Data Model**: People, parties, positions, collaborations, and memberships
- **Sample Data**: Pre-loaded with 13+ prominent Pakistani political figures

## Architecture

```
┌─────────────────────────────────────────────────┐
│         User Queries (Natural Language)         │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  LangGraph Agent     │
            │  (langgraph_agent.py)│
            └──────────┬───────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
  ┌──────────────┐         ┌──────────────────┐
  │  LLM (GPT-4) │         │  Neo4j Database  │
  │  (OpenAI)    │         │ (neo4j_loader.py)│
  └──────────────┘         └──────────────────┘
```

## Graph Schema

### Nodes
- **Person**: Pakistani political figures
- **Party**: Political parties
- **Position**: Government positions

### Relationships
- **MEMBER_OF**: Person → Party (with start/end years)
- **HELD_POSITION**: Person → Position (with start/end years)
- **COLLABORATED_WITH**: Person → Person (with description)

## Installation

### Prerequisites
- Python 3.12+
- Neo4j 5.14+
- OpenAI API key (for LangGraph agent functionality)

### Step 1: Clone and Setup Environment

```bash
cd /home/ali-vijdaan/Projects/tareekh-net
```

### Step 2: Start Neo4j

Using Docker (recommended):
```bash
docker run -d \
  -p 7687:7687 \
  -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.14-community
```

Or install locally from: https://neo4j.com/download/

### Step 3: Install Python Dependencies

Using `uv` (faster):
```bash
uv sync
```

Or using pip:
```bash
pip install -e .
```

### Step 4: Configure Environment

Copy `.env.example` to `.env` and update with your credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
OPENAI_API_KEY=sk-your-key-here
```

## Usage

### Quick Start

```bash
python main.py
```

This will:
1. Connect to Neo4j
2. Load sample Pakistani political members data
3. Create indexes for performance
4. Run sample queries both directly and through the LangGraph agent

### Using the Neo4j Loader Directly

```python
from scraping.neo4j_loader import setup_neo4j_graph

# Setup the graph with sample data
loader = setup_neo4j_graph(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password",
    clear=True  # Clear previous data
)

# Get statistics
stats = loader.get_statistics()
print(f"People: {stats['people']}, Parties: {stats['parties']}")

loader.close()
```

### Using the LangGraph Agent

```python
from scraping.langgraph_agent import create_political_agent
import os

# Create agent
agent = create_political_agent(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_pass="password",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# Query with natural language
response = agent.query("Who are the Prime Ministers of Pakistan?")
print(response)

agent.close()
```

### Direct Neo4j Queries

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

with driver.session() as session:
    # Get all Prime Ministers
    result = session.run("""
        MATCH (p:Person)-[r:HELD_POSITION]->(pos:Position)
        WHERE pos.title = 'Prime Minister'
        RETURN p.name, r.start_year, r.end_year
        ORDER BY r.start_year DESC
    """)
    for record in result:
        print(f"{record['p.name']} ({record['r.start_year']}-{record['r.end_year']})")

driver.close()
```

## Sample Data

The system includes 13+ Pakistani political figures:

- **Benazir Bhutto**: First female PM (1988-1990)
- **Muhammad Nawaz Sharif**: Former PM (1990-1993, 1997-1999)
- **Raja Pervaiz Ashraf**: Former PM (2008-2012)
- **Imran Khan**: Cricketer-turned-PM (2018-2022)
- **Shehbaz Sharif**: Current PM & PMLN member
- **Asif Ali Zardari**: Former President (2008-2013)
- **Bilawal Bhutto Zardari**: PPP Chairman
- **Maryam Nawaz**: Vice President of PMLN

Plus more members from:
- Pakistan Peoples Party (PPP)
- Pakistan Muslim League (PMLN)
- Pakistan Tehreek-e-Insaaf (PTI)
- And others...

## API Reference

### Neo4jPoliticalGraphLoader

**Methods:**

```python
# Add entities
add_person(person_id, name, birth_year, bio, aliases)
add_party(party_id, name, founded_year, description)
add_position(position_id, title, description, level)

# Create relationships
create_member_of_party(person_id, party_id, start_year, end_year)
create_held_position(person_id, position_id, start_year, end_year)
create_collaborated_with(person_id_1, person_id_2, description)

# Utilities
load_sample_data()
get_statistics()
clear_database()
create_indexes()
```

### PoliticalGraphAgent

**Methods:**

```python
# Query the graph
query(question: str) -> str

# Specialized queries
process_query(state)
generate_response(state)
create_graph()
```

## Neo4j Browser

Access the Neo4j browser at: **http://localhost:7474**

**Useful Cypher Queries:**

```cypher
# Get network visualization
MATCH (p:Person)-[r:COLLABORATED_WITH]-(other:Person) 
RETURN p, r, other

# Find political network path
MATCH path = (p1:Person {name: "Nawaz Sharif"})-[*1..3]-(p2:Person)
RETURN path

# Count members by party
MATCH (p:Person)-[:MEMBER_OF]->(party:Party)
RETURN party.name, count(p) as member_count

# Timeline of Prime Ministers
MATCH (p:Person)-[r:HELD_POSITION]->(pos:Position {title: "Prime Minister"})
RETURN p.name, r.start_year, r.end_year
ORDER BY r.start_year
```

## Extending the System

### Adding More Political Members

```python
from scraping.neo4j_loader import Neo4jPoliticalGraphLoader

loader = Neo4jPoliticalGraphLoader(uri, user, pass)

# Add new person
loader.add_person(
    "new_person",
    "Name Here",
    birth_year=1960,
    bio="Description"
)

# Create relationships
loader.create_member_of_party("new_person", "pmln", 2020)
loader.create_held_position("new_person", "cm", 2020, 2025)
```

### Custom Query Patterns

```python
# In langgraph_agent.py, extend Neo4jQuerier class:
def query_by_region(self, region: str) -> list[dict]:
    """Get members from a specific region."""
    with self.driver.session() as session:
        result = session.run(
            "MATCH (p:Person) WHERE p.region = $region RETURN p",
            region=region
        )
        return [dict(r) for r in result]
```

## Troubleshooting

### Connection Error to Neo4j

```
Error: Could not connect to Neo4j at bolt://localhost:7687
```

**Solution:**
1. Ensure Neo4j is running: `docker ps`
2. Check credentials in `.env`
3. Try restarting Neo4j

### OpenAI API Errors

```
AuthenticationError: Incorrect API key provided
```

**Solution:**
1. Verify OPENAI_API_KEY is set in `.env`
2. Check API key is valid at https://platform.openai.com/api-keys

## Performance Tips

1. **Create Indexes**: Automatically done on startup
2. **Use Specific Queries**: Rather than wildcard matches
3. **Batch Operations**: For adding multiple entities
4. **Connection Pooling**: Driver handles this automatically

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! Areas for enhancement:
- Add more Pakistani political figures
- Implement GraphRAG retrieval chains
- Add temporal analysis
- Integrate news APIs for real-time updates
- Create visualization dashboard

## References

- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [GraphRAG](https://microsoft.github.io/graphrag/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/)

## Support

For issues and questions:
1. Check the Troubleshooting section
2. Review Neo4j logs: `docker logs <container_id>`
3. Test Neo4j connectivity independently
