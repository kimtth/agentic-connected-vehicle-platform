"""
Initialize agent creation and route registration.
"""

from fastapi import FastAPI, APIRouter
from apis.agent_routes import router as agent_router
