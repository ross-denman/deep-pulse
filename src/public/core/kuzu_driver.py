import kuzu
import logging
import os
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("kuzu_driver")

class KuzuDriver:
    """
    Embedded Graph Driver for Discovery Mesh Outposts.
    Optimized for low-resource environments (Pi Zero 2 W).
    Implementation of the 'Hybrid Sovereignty' model.
    """
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to harvest/kuzu_db
            project_root = Path(__file__).resolve().parent.parent.parent
            db_path = str(project_root / "harvest" / "kuzu_db")
        
        self.db_path = db_path
        self._db = None
        self._conn = None
        self.is_connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def __aenter__(self):
        self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        try:
            # Ensure harvest dir exists
            Path(self.db_path).parent.mkdir(exist_ok=True, parents=True)
            self._db = kuzu.Database(self.db_path)
            self._conn = kuzu.Connection(self._db)
            self.is_connected = True
            logger.info(f"KuzuDB connected at {self.db_path}")
            self._initialize_schema()
        except Exception as e:
            logger.error(f"KuzuDB connection failed: {e}")
            self.is_connected = False

    def close(self):
        self._conn = None
        self._db = None
        self.is_connected = False

    def _initialize_schema(self):
        """Ensures the standard LEAP schema exists for the Outpost."""
        try:
            # Node Tables
            self._conn.execute("CREATE NODE TABLE Entity(name STRING, type STRING, description STRING, PRIMARY KEY (name))")
            self._conn.execute("CREATE NODE TABLE ChronicleEntry(id STRING, title STRING, timestamp STRING, PRIMARY KEY (id))")
            
            # Relationship Tables
            self._conn.execute("CREATE REL TABLE RELATED_TO(FROM Entity TO Entity)")
            self._conn.execute("CREATE REL TABLE MENTIONED_IN(FROM Entity TO ChronicleEntry, signature STRING)")
            
            logger.info("KuzuDB Outpost Schema initialized.")
        except Exception:
            # Table likely exists, Kuzu throws error on duplicate table creation
            pass

    async def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Executes a Cypher query (Compatible with Neo4j patterns)."""
        if not self.is_connected:
            return []
        
        try:
            result = self._conn.execute(query, params or {})
            cols = result.get_column_names()
            rows = []
            while result.has_next():
                row = result.get_next()
                rows.append(dict(zip(cols, row)))
            return rows
        except Exception as e:
            logger.error(f"Cypher Error: {e}")
            return []

    async def ingest_scout_result(self, res: Any, cid: str, signature: str):
        """
        Ingests a ScoutResult into the local graph.
        Matches the interface expected by ArchiveController.
        """
        if not self.is_connected: return {"entry_merged": False}
        
        try:
            # 1. Ingest Chronicle Entry
            await self.execute_query(
                "COPY ChronicleEntry FROM (SELECT $id, $title, $ts)", 
                {"id": cid, "title": res.intel.title, "ts": res.timestamp.isoformat()}
            )
        except:
            # Entry likely exists, we'll try to link entities anyway or use MERGE if supported
            pass

        # Manual MERGE substitute for entities to be safe across Kuzu versions
        for ent in res.entities:
            try:
                # 2. Ingest Entity
                check = await self.execute_query("MATCH (e:Entity {name: $name}) RETURN e.name", {"name": ent.name})
                if not check:
                    await self.execute_query(
                        "CREATE (e:Entity {name: $name, type: $type, description: $desc})",
                        {"name": ent.name, "type": ent.entity_type, "desc": ent.description or ""}
                    )
                
                # 3. Link Entity to Chronicle
                await self.execute_query(
                    "MATCH (e:Entity {name: $name}), (c:ChronicleEntry {id: $cid}) "
                    "CREATE (e)-[r:MENTIONED_IN {signature: $sig}]->(c)",
                    {"name": ent.name, "cid": cid, "sig": signature}
                )
            except Exception as e:
                logger.warning(f"Failed to ingest entity {ent.name} link: {e}")

        return {"entry_merged": True}
