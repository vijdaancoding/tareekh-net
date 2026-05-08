"""
Module to populate Neo4j with Pakistani political members and their relationships.
"""

from neo4j import GraphDatabase
from typing import Optional


class Neo4jPoliticalGraphLoader:
    """Loader for Pakistani political members into Neo4j."""
    
    def __init__(self, uri: str, username: str, password: str):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j connection URI (e.g., "bolt://localhost:7687")
            username: Neo4j username
            password: Neo4j password
        """
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
    
    def close(self):
        """Close the driver connection."""
        self.driver.close()
    
    def clear_database(self):
        """Clear all nodes and relationships from the database."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✓ Database cleared")
    
    def create_indexes(self):
        """Create indexes for better query performance."""
        with self.driver.session() as session:
            # Create indexes
            session.run("CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.name)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (p:Party) ON (p.name)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (p:Position) ON (p.title)")
            print("✓ Indexes created")
    
    def add_person(self, person_id: str, name: str, birth_year: Optional[int] = None, 
                   bio: Optional[str] = None, aliases: Optional[list] = None) -> bool:
        """Add a person node to the graph."""
        with self.driver.session() as session:
            query = """
            MERGE (p:Person {id: $id})
            SET p.name = $name, p.birth_year = $birth_year, p.bio = $bio
            """
            if aliases:
                query += ", p.aliases = $aliases"
            
            session.run(query, id=person_id, name=name, birth_year=birth_year, 
                       bio=bio, aliases=aliases)
        return True
    
    def add_party(self, party_id: str, name: str, founded_year: Optional[int] = None,
                  description: Optional[str] = None) -> bool:
        """Add a political party node."""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (p:Party {id: $id})
                SET p.name = $name, p.founded_year = $founded_year, p.description = $description
                """,
                id=party_id, name=name, founded_year=founded_year, description=description
            )
        return True
    
    def add_position(self, position_id: str, title: str, description: Optional[str] = None,
                     level: Optional[str] = None) -> bool:
        """Add a political position node."""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (pos:Position {id: $id})
                SET pos.title = $title, pos.description = $description, pos.level = $level
                """,
                id=position_id, title=title, description=description, level=level
            )
        return True
    
    def create_member_of_party(self, person_id: str, party_id: str, 
                              start_year: Optional[int] = None,
                              end_year: Optional[int] = None) -> bool:
        """Create MEMBER_OF relationship between person and party."""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Person {id: $person_id}), (party:Party {id: $party_id})
                MERGE (p)-[r:MEMBER_OF]->(party)
                SET r.start_year = $start_year, r.end_year = $end_year
                """,
                person_id=person_id, party_id=party_id, 
                start_year=start_year, end_year=end_year
            )
        return True
    
    def create_held_position(self, person_id: str, position_id: str,
                            start_year: Optional[int] = None,
                            end_year: Optional[int] = None) -> bool:
        """Create HELD_POSITION relationship between person and position."""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Person {id: $person_id}), (pos:Position {id: $position_id})
                MERGE (p)-[r:HELD_POSITION]->(pos)
                SET r.start_year = $start_year, r.end_year = $end_year
                """,
                person_id=person_id, position_id=position_id,
                start_year=start_year, end_year=end_year
            )
        return True
    
    def create_collaborated_with(self, person_id_1: str, person_id_2: str,
                                description: Optional[str] = None) -> bool:
        """Create COLLABORATED_WITH relationship between two persons."""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p1:Person {id: $person_id_1}), (p2:Person {id: $person_id_2})
                MERGE (p1)-[r:COLLABORATED_WITH]->(p2)
                SET r.description = $description
                """,
                person_id_1=person_id_1, person_id_2=person_id_2, description=description
            )
        return True
    
    def load_sample_data(self):
        """Load sample Pakistani political members data."""
        print("\n🔄 Loading Pakistani political members data...")
        
        # Add Political Parties
        parties = [
            ("ppp", "Pakistan Peoples Party", 1967, "Major center-left political party"),
            ("pmln", "Pakistan Muslim League (Nawaz)", 1997, "Major center-right political party"),
            ("ptm", "Pakistan Tehreek-e-Insaaf", 1996, "Center-right political party"),
            ("jui", "Jamiat Ulema-e-Islam", 1945, "Religious political party"),
            ("mqi", "Muttahida Qaumi Movement", 1984, "Political party based in Karachi"),
        ]
        
        for party_id, name, year, desc in parties:
            self.add_party(party_id, name, year, desc)
        print(f"✓ Added {len(parties)} political parties")
        
        # Add Positions
        positions = [
            ("pm", "Prime Minister", "Head of government of Pakistan", "National"),
            ("president", "President", "Head of state of Pakistan", "National"),
            ("cm", "Chief Minister", "Head of provincial government", "Provincial"),
            ("fm", "Foreign Minister", "Minister of Foreign Affairs", "National"),
            ("finance_min", "Finance Minister", "Minister of Finance", "National"),
            ("defense_min", "Defense Minister", "Minister of Defense", "National"),
            ("interior_min", "Interior Minister", "Minister of Interior", "National"),
        ]
        
        for pos_id, title, desc, level in positions:
            self.add_position(pos_id, title, desc, level)
        print(f"✓ Added {len(positions)} political positions")
        
        # Add Political Members
        members = [
            ("iqbal_khan", "Muhammad Iqbal Khan", 1945, "Prominent political figure and statesman"),
            ("ashraf_jahangir", "Ashraf Jahangir Qazi", 1949, "Senior political leader and diplomat"),
            ("raza_gillani", "Raja Pervaiz Ashraf", 1954, "Former Prime Minister of Pakistan"),
            ("nawaz_sharif", "Muhammad Nawaz Sharif", 1949, "Former Prime Minister and business tycoon"),
            ("imran_khan", "Imran Khan", 1952, "Former cricketer and politician, founder of PTI"),
            ("benazir_bhutto", "Benazir Bhutto", 1953, "First female Prime Minister of Pakistan"),
            ("zardari", "Asif Ali Zardari", 1955, "Former President of Pakistan"),
            ("shehbaz_sharif", "Shehbaz Sharif", 1951, "Chief Minister and politician"),
            ("maryam_nawaz", "Maryam Nawaz Sharif", 1973, "Vice President of PMLN"),
            ("shahid_khaqan", "Shahid Khaqan Abbasi", 1958, "Former Prime Minister"),
            ("bilawal_bhutto", "Bilawal Bhutto Zardari", 1988, "Chairman of PPP"),
            ("hafiz_sheikh", "Muhammad Hafeez Sheikh", 1955, "Finance Minister and politician"),
            ("fawad_chaudhry", "Fawad Chaudhry", 1970, "Minister of Information"),
        ]
        
        for person_id, name, birth_year, bio in members:
            self.add_person(person_id, name, birth_year, bio)
        print(f"✓ Added {len(members)} political members")
        
        # Add Party Memberships
        memberships = [
            ("raza_gillani", "ppp", 1980, 2022),
            ("benazir_bhutto", "ppp", 1982, 2007),
            ("zardari", "ppp", 1990, None),
            ("nawaz_sharif", "pmln", 1997, None),
            ("shehbaz_sharif", "pmln", 1997, None),
            ("maryam_nawaz", "pmln", 2002, None),
            ("shahid_khaqan", "pmln", 2000, 2019),
            ("imran_khan", "ptm", 1996, None),
            ("bilawal_bhutto", "ppp", 2010, None),
            ("hafiz_sheikh", "pmln", 2005, None),
            ("fawad_chaudhry", "ptm", 2014, None),
            ("ashraf_jahangir", "ppp", 1985, 2015),
            ("iqbal_khan", "pmln", 1990, 2010),
        ]
        
        for person_id, party_id, start_year, end_year in memberships:
            self.create_member_of_party(person_id, party_id, start_year, end_year)
        print(f"✓ Created {len(memberships)} party memberships")
        
        # Add Position Holdings
        positions_held = [
            ("raza_gillani", "pm", 2008, 2012),
            ("nawaz_sharif", "pm", 1990, 1993),
            ("nawaz_sharif", "pm", 1997, 1999),
            ("imran_khan", "pm", 2018, 2022),
            ("shehbaz_sharif", "pm", 2022, None),
            ("bilawal_bhutto", "fm", 2023, None),
            ("ashraf_jahangir", "fm", 2002, 2007),
            ("hafiz_sheikh", "finance_min", 2022, None),
            ("fawad_chaudhry", "interior_min", 2020, 2022),
            ("benazir_bhutto", "pm", 1988, 1990),
            ("nawaz_sharif", "president", 2001, None),
            ("zardari", "president", 2008, 2013),
        ]
        
        for person_id, position_id, start_year, end_year in positions_held:
            self.create_held_position(person_id, position_id, start_year, end_year)
        print(f"✓ Created {len(positions_held)} position holdings")
        
        # Add Collaborations
        collaborations = [
            ("nawaz_sharif", "shehbaz_sharif", "Brothers and political allies"),
            ("maryam_nawaz", "nawaz_sharif", "Father and daughter political team"),
            ("zardari", "benazir_bhutto", "Husband and wife (deceased)"),
            ("bilawal_bhutto", "zardari", "Son and father in same party"),
            ("imran_khan", "fawad_chaudhry", "Political allies in PTI"),
        ]
        
        for person_id_1, person_id_2, description in collaborations:
            self.create_collaborated_with(person_id_1, person_id_2, description)
        print(f"✓ Created {len(collaborations)} collaborations")
        
        print("\n✅ All data loaded successfully!\n")
    
    def get_statistics(self) -> dict:
        """Get statistics about the graph."""
        with self.driver.session() as session:
            people_count = session.run("MATCH (p:Person) RETURN count(p) as count").single()["count"]
            parties_count = session.run("MATCH (p:Party) RETURN count(p) as count").single()["count"]
            positions_count = session.run("MATCH (p:Position) RETURN count(p) as count").single()["count"]
            relationships_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            return {
                "people": people_count,
                "parties": parties_count,
                "positions": positions_count,
                "relationships": relationships_count
            }


def setup_neo4j_graph(uri: str = "bolt://localhost:7687", 
                      username: str = "neo4j",
                      password: str = "password",
                      clear: bool = False) -> Neo4jPoliticalGraphLoader:
    """
    Setup Neo4j graph with Pakistani political members.
    
    Args:
        uri: Neo4j connection URI
        username: Neo4j username
        password: Neo4j password
        clear: Whether to clear existing data
    
    Returns:
        Configured Neo4jPoliticalGraphLoader instance
    """
    loader = Neo4jPoliticalGraphLoader(uri, username, password)
    
    if clear:
        loader.clear_database()
    
    loader.create_indexes()
    loader.load_sample_data()
    
    stats = loader.get_statistics()
    print(f"📊 Graph Statistics:")
    print(f"   People: {stats['people']}")
    print(f"   Parties: {stats['parties']}")
    print(f"   Positions: {stats['positions']}")
    print(f"   Relationships: {stats['relationships']}")
    
    return loader
