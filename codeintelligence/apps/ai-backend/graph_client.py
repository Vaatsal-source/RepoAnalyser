import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class GraphDBClient:
    def __init__(self):
        self.uri = NEO4J_URI
        self.auth = (NEO4J_USER, NEO4J_PASSWORD)
        # We don't verify connectivity on init to avoid holding long-lived idle connections

    def create_file_node(self, repo_id, file_path):
        """Creates a codebase file node and links it directly to its parent Repository."""
        query = """
        MERGE (r:Repository {id: $repo_id})
        MERGE (f:File {path: $file_path, repo_id: $repo_id})
        MERGE (r)-[:CONTAINS_FILE]->(f)
        RETURN f
        """
        # Using a direct context block guarantees the session is safely disposed of immediately
        with GraphDatabase.driver(self.uri, auth=self.auth) as driver:
            with driver.session() as session:
                session.run(query, repo_id=repo_id, file_path=file_path)

    def delete_repository(self, repo_id):
        """Deletes graph nodes for a workspace before re-indexing it."""
        query = """
        MATCH (r:Repository {id: $repo_id})
        OPTIONAL MATCH (r)-[:CONTAINS_FILE]->(f:File {repo_id: $repo_id})
        DETACH DELETE f, r
        """
        with GraphDatabase.driver(self.uri, auth=self.auth) as driver:
            with driver.session() as session:
                session.run(query, repo_id=repo_id)

    def get_file_siblings(self, repo_id, current_file):
        """Fetches related repository assets sharing the same root structure."""
        query = """
        MATCH (r:Repository {id: $repo_id})-[:CONTAINS_FILE]->(sibling:File)
        WHERE sibling.path <> $current_file
        RETURN sibling.path AS sibling_path LIMIT 5
        """
        with GraphDatabase.driver(self.uri, auth=self.auth) as driver:
            with driver.session() as session:
                result = session.run(query, repo_id=repo_id, current_file=current_file)
                return [record["sibling_path"] for record in result]
