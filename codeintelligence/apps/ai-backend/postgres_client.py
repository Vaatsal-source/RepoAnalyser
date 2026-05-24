import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import Base

# Force load environment variables from our backend configuration space
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is missing from your .env file!")

# Neon utilizes connection pooling over SSL. We explicitly pass require parameters
# to prevent handshake degradation issues over standard internet hops.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class PostgresClient:
    def __init__(self):
        self.engine = engine

    def init_tables(self):
        """Creates all structural tables defined in models.py on your cloud Neon DB instance."""
        print("🚀 Syncing schemas with Neon Cloud Postgres...")
        Base.metadata.create_all(bind=self.engine)
        print("✨ Database tables synchronized successfully!")

    def get_session(self):
        """Spins up a clean context session layer for processing standard mutations."""
        return SessionLocal()