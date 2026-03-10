from neo4j import AsyncDriver


async def init_schema(driver: AsyncDriver) -> None:
    async with driver.session() as session:
        # Uniqueness constraints
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Politician) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Position) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Source) REQUIRE s.id IS UNIQUE",
        ]
        for c in constraints:
            await session.run(c)

        # Lookup indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (p:Politician) ON (p.name)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Party) ON (p.abbreviation)",
            "CREATE INDEX IF NOT EXISTS FOR (s:Source) ON (s.url)",
        ]
        for i in indexes:
            await session.run(i)

        # Vector index for semantic search (768-dim Gemini embeddings, cosine)
        await session.run("""
            CREATE VECTOR INDEX politician_bio_embedding IF NOT EXISTS
            FOR (p:Politician) ON (p.embedding)
            OPTIONS {indexConfig: {
                `vector.dimensions`: 768,
                `vector.similarity_function`: 'cosine'
            }}
        """)
