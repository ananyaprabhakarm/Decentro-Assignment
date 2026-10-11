from fastapi import FastAPI
from app.database.database import Base, engine
from app.database import models

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
