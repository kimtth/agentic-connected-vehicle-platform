# """
# Integration tests for Azure-based Connected Vehicle Platform.
# """
# import os
# import sys
# import pytest
# import asyncio
# from dotenv import load_dotenv
# from fastapi.testclient import TestClient # !Important: To use TestClient, first install httpx.

# # Add the parent directory to the Python path so we can import modules from there
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from main import app
# from azure.cosmos_db import cosmos_client

# # Load Azure environment variables
# load_dotenv(override=True)

# # Test client
# client = TestClient(app)

# @pytest.fixture(scope="session")
# def event_loop():
#     """Create an event loop for tests"""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()

# @pytest.fixture
# async def test_vehicle():
#     """Create a test vehicle for use in tests"""
#     # Create test vehicle
#     vehicle_data = {
#         "vehicle_id": "test-vehicle-1",
#         "Make": "Tesla",
#         "Model": "Model 3",
#         "Year": 2023,
#         "VIN": "TEST12345678901234",
#         "Color": "Red"
#     }
    
#     # Create in Cosmos DB
#     try:
#         await cosmos_client.create_vehicle(vehicle_data)
#     except Exception:
#         # Vehicle might already exist
#         pass
    
#     yield vehicle_data
    
#     # We don't clean up to avoid test failures in shared environment
#     # In a real setup, we'd use a test database or container

# # Test API endpoints
# @pytest.mark.asyncio
# async def test_health_endpoint():
#     """Test the health endpoint"""
#     response = client.get("/")
#     assert response.status_code == 200
#     assert "status" in response.json()
#     assert "azure_enabled" in response.json()
#     assert response.json()["azure_enabled"] is True

# @pytest.mark.asyncio
# async def test_vehicle_endpoints(test_vehicle):
#     """Test vehicle endpoints"""
#     # List vehicles
#     response = client.get("/vehicles")
#     assert response.status_code == 200
    
#     # Check if test vehicle is in the list
#     vehicles = response.json()
#     assert any(v["vehicle_id"] == test_vehicle["vehicle_id"] for v in vehicles)
    
#     # Get vehicle status
#     response = client.get(f"/vehicle/{test_vehicle['vehicle_id']}/status")
#     assert response.status_code == 200
#     assert "Battery" in response.json()

# @pytest.mark.asyncio
# async def test_command_flow():
#     """Test the command flow"""
#     # Create a test command
#     command = {
#         "vehicle_id": "test-vehicle-1",
#         "commandType": "START_ENGINE",
#         "payload": {}
#     }
    
#     # Send the command
#     response = client.post("/command", json=command)
#     assert response.status_code == 200
#     assert "commandId" in response.json()
    
#     command_id = response.json()["commandId"]
    
#     # Wait for command processing
#     await asyncio.sleep(2)
    
#     # Get commands to verify
#     response = client.get("/commands")
#     assert response.status_code == 200
    
#     # Find our command
#     commands = response.json()
#     our_command = next((c for c in commands if c.get("commandId") == command_id), None)
    
#     assert our_command is not None
#     assert our_command["status"] in ["completed", "processing"]  # May be still processing

# @pytest.mark.asyncio
# async def test_service_flow(test_vehicle):
#     """Test the service flow"""
#     # Create a test service
#     service = {
#         "ServiceCode": "TEST_SERVICE",
#         "Description": "Test service for integration tests",
#         "StartDate": "2025-01-01",
#         "EndDate": "2025-01-02"
#     }
    
#     # Add service to vehicle
#     response = client.post(f"/vehicle/{test_vehicle['vehicle_id']}/service", json=service)
#     assert response.status_code == 200
    
#     # List services for vehicle
#     response = client.get(f"/vehicle/{test_vehicle['vehicle_id']}/services")
#     assert response.status_code == 200
    
#     # Check if our service is in the list
#     services = response.json()
#     assert any(s["ServiceCode"] == service["ServiceCode"] for s in services)

# @pytest.mark.asyncio
# async def test_agent_integration():
#     """Test agent integration"""
#     # Test query
#     query = "What services are available for vehicle test-vehicle-1?"
    
#     # Call agent
#     response = client.post("/agent/ask", json={"query": query})
#     assert response.status_code == 200
#     assert "response" in response.json()
#     assert "plugins_used" in response.json()

# if __name__ == "__main__":
#     pytest.main(["-xvs", __file__])
