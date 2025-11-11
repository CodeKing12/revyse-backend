from sqlmodel import create_engine, SQLModel
from app.core.config import settings

# Build connection string only if all required settings are present
if all([settings.DB_USER, settings.DB_PASSWORD, settings.DB_HOST, settings.DB_PORT, settings.DB_NAME]):
    conn_str = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    database = create_engine(conn_str, echo=True)
else:
    # Use a dummy in-memory SQLite database for development/testing
    conn_str = "sqlite:///./test.db"
    database = create_engine(conn_str, echo=True)

def create_tables():
    SQLModel.metadata.create_all(database)

if __name__ == "__main__":
    create_tables()