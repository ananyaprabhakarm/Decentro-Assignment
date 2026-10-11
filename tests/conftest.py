import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database.models import Group, GroupMember, User
from app.main import app
from app.database.database import Base, get_db


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

@pytest.fixture
def test_group(db_session):
    user1 = User(name="Test User 1", email="test1@example.com")
    user2 = User(name="Test User 2", email="test2@example.com")

    db_session.add_all([user1, user2])
    db_session.commit()
    db_session.refresh(user1)
    db_session.refresh(user2)

    group = Group(name="Test Group")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    db_session.add_all([
        GroupMember(group_id=group.id, user_id=user1.id),
        GroupMember(group_id=group.id, user_id=user2.id),
    ])
    db_session.commit()

    return group, user1, user2
