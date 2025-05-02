"""
Initialize agent creation and route registration.
"""

from fastapi import FastAPI, APIRouter
from agents.agent_routes import router as agent_router
