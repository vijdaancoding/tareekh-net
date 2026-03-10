from neo4j import AsyncDriver


async def get_all_politicians(driver: AsyncDriver) -> list[dict]:
    async with driver.session() as session:
        result = await session.run(
            "MATCH (p:Politician) RETURN p.id AS id, p.name AS name, p.born AS born, p.bio AS bio"
        )
        return [dict(record) async for record in result]


async def get_politician_by_id(driver: AsyncDriver, politician_id: str) -> dict | None:
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Politician {id: $id})
            OPTIONAL MATCH (p)-[r]->(n)
            RETURN p, collect({rel: type(r), node: n}) AS relationships
            """,
            id=politician_id,
        )
        record = await result.single()
        if not record:
            return None
        p = dict(record["p"])
        p.pop("embedding", None)
        return {"politician": p, "relationships": record["relationships"]}


async def semantic_search(driver: AsyncDriver, embedding: list[float], top_k: int = 5) -> list[dict]:
    async with driver.session() as session:
        result = await session.run(
            """
            CALL db.index.vector.queryNodes('politician_bio_embedding', $top_k, $embedding)
            YIELD node AS p, score
            RETURN p.id AS id, p.name AS name, p.born AS born, p.bio AS bio, score
            """,
            top_k=top_k,
            embedding=embedding,
        )
        return [dict(record) async for record in result]


async def get_graph_data(driver: AsyncDriver) -> dict:
    """Return nodes + links in D3 force-graph format."""
    async with driver.session() as session:
        result = await session.run("""
            MATCH (n)
            WHERE n:Politician OR n:Party OR n:Position
            OPTIONAL MATCH (n)-[r]->(m)
            WHERE m:Politician OR m:Party OR m:Position
            RETURN
                n.id AS src_id, n.name AS src_name, labels(n)[0] AS src_type,
                type(r) AS rel_type,
                m.id AS tgt_id, m.name AS tgt_name, labels(m)[0] AS tgt_type
        """)
        nodes: dict[str, dict] = {}
        links: list[dict] = []
        async for record in result:
            sid = record["src_id"]
            if sid and sid not in nodes:
                nodes[sid] = {"id": sid, "name": record["src_name"], "type": record["src_type"]}
            if record["tgt_id"]:
                tid = record["tgt_id"]
                if tid not in nodes:
                    nodes[tid] = {"id": tid, "name": record["tgt_name"], "type": record["tgt_type"]}
                links.append({"source": sid, "target": tid, "type": record["rel_type"]})
        return {"nodes": list(nodes.values()), "links": links}
