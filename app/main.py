from fastapi import FastAPI

app = FastAPI(
    title="각할모 API",
    version="0.1.0",
    description="각자 모여서 할거 하는 모임",
)

@app.get("/")
async def root():
    return {"message": "Hello, 각할모 World"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "gakhalmo-api"}