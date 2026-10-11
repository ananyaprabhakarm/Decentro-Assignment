from fastapi import FastAPI
from app.database.database import Base, engine
from app.database import models
from app.routers.balance import router as balance_router
from app.routers.expenses import router as expenses_router
from app.routers.users import router as user_router
from app.routers.groups import router as groups_router
from app.routers.settlements import router as settlements_router

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(user_router)
app.include_router(expenses_router)
app.include_router(balance_router)
app.include_router(groups_router)
app.include_router(settlements_router)


@app.get("/", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
