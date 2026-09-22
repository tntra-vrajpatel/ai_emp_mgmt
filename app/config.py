import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
APP_ENV = os.environ.get("APP_ENV", "development")
