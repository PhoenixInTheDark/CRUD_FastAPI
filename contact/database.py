from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///./{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)