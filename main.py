from fastapi import FastAPI
import models
from database import engine

# Create tables defined in models.py when the app starts
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Permissions-as-Data Hybrid Service")

# This will be populated in the next branches.
# We just need the app object here.