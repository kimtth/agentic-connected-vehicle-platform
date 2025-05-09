import os
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv(override=True)

endpoint = os.getenv("COSMOS_DB_ENDPOINT")

credential = DefaultAzureCredential()

client = CosmosClient(endpoint, credential=credential)

container = client.get_database_client(os.getenv("COSMOS_DB_DATABASE")).get_container_client(os.getenv("COSMOS_DB_CONTAINER_VEHICLES"))

print("Connected to Azure Cosmos DB successfully.")