from fastapi import FastAPI

app = FastAPI(
    title="Expense Sharing Service",
    description="Backend service for sharing expenses among users",
    version="0.1.0",
)


@app.get("/", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
