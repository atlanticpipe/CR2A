"""Lambda entrypoint adapting FastAPI to API Gateway via Mangum."""
from mangum import Mangum
from api.main import app

# Wrap the FastAPI app so API Gateway/Lambda can proxy requests without code changes.
handler = Mangum(app)
