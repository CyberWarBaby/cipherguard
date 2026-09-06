import uvicorn
from app.main import app
from app.config import settings

# Export app instance for uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
