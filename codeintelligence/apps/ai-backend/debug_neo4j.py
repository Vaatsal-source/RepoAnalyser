import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

print(f"📡 Testing fresh .env credentials for: {uri}")

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    print("🎉 SUCCESS! Neo4j Aura Cloud has authorized your session completely!")
    driver.close()
except Exception as e:
    print(f"\n❌ Error: {str(e)}")