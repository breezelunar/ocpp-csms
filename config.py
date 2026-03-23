import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "ocpp_csms")

WS_HOST: str = os.getenv("WS_HOST", "0.0.0.0")
WS_PORT: int = int(os.getenv("WS_PORT", "9000"))

HTTP_HOST: str = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT: int = int(os.getenv("HTTP_PORT", "8000"))
