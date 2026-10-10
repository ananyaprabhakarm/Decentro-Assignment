from sqlalchemy import create_engine, sessionmaker, declarative_base

SQLALCHEMY_URL = 'sqlite:///./expense_sharing.db'
engine = create_engine(SQLALCHEMY_URL, check_same_thread=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()

def get_db():
    """Get the database connection from session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()