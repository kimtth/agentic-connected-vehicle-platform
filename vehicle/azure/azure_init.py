"""
Azure Resources Initialization Script

This script helps initialize Azure resources required for the Connected Vehicle Platform:
1. Azure OpenAI service
2. Cosmos DB
3. Azure AD App Registration (for authentication)
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.cosmosdb import CosmosDBManagementClient
from azure.cosmos import CosmosClient
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Initialize Azure resources for Connected Vehicle Platform')
    parser.add_argument('--resource-group', required=True, help='Azure Resource Group name')
    parser.add_argument('--location', default='eastus', help='Azure region (default: eastus)')
    parser.add_argument('--cosmos-account', required=True, help='Cosmos DB account name')
    parser.add_argument('--database-name', default='VehiclePlatformDB', help='Cosmos DB database name')
    parser.add_argument('--env-file', default='.env', help='Path to save environment variables')
    return parser.parse_args()

def get_credentials():
    """Get Azure credentials"""
    try:
        # Try to use DefaultAzureCredential (works with az login, managed identity, etc.)
        credential = DefaultAzureCredential()
        # Test the credential
        subscription_id = os.environ.get('AZURE_SUBSCRIPTION_ID')
        if not subscription_id:
            logger.error("AZURE_SUBSCRIPTION_ID environment variable not set")
            sys.exit(1)
        
        # Create a client to verify credentials
        resource_client = ResourceManagementClient(credential, subscription_id)
        list(resource_client.resource_groups.list())
        logger.info("Successfully authenticated with DefaultAzureCredential")
        return credential, subscription_id
    except Exception as e:
        logger.error(f"DefaultAzureCredential failed: {str(e)}")
        
        # Fall back to client secret
        tenant_id = os.environ.get('AZURE_TENANT_ID')
        client_id = os.environ.get('AZURE_CLIENT_ID')
        client_secret = os.environ.get('AZURE_CLIENT_SECRET')
        
        if not all([tenant_id, client_id, client_secret]):
            logger.error("Azure service principal credentials not properly configured")
            logger.error("Please set AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET environment variables")
            sys.exit(1)
        
        credential = ClientSecretCredential(tenant_id, client_id, client_secret)
        
        # Test the credential
        resource_client = ResourceManagementClient(credential, subscription_id)
        list(resource_client.resource_groups.list())
        logger.info("Successfully authenticated with ClientSecretCredential")
        return credential, subscription_id

def ensure_resource_group(credential, subscription_id, rg_name, location):
    """Ensure the resource group exists"""
    client = ResourceManagementClient(credential, subscription_id)
    
    # Check if the resource group exists
    for resource_group in client.resource_groups.list():
        if resource_group.name == rg_name:
            logger.info(f"Resource group {rg_name} already exists")
            return
    
    # Create the resource group
    client.resource_groups.create_or_update(
        rg_name,
        {
            'location': location
        }
    )
    logger.info(f"Created resource group {rg_name} in {location}")

def create_cosmos_db(credential, subscription_id, rg_name, account_name, location, db_name):
    """Create Cosmos DB account and database"""
    client = CosmosDBManagementClient(credential, subscription_id)
    
    # Check if the account exists
    try:
        account = client.database_accounts.get(rg_name, account_name)
        logger.info(f"Cosmos DB account {account_name} already exists")
    except:
        # Create the account
        logger.info(f"Creating Cosmos DB account {account_name}...")
        poller = client.database_accounts.begin_create_or_update(
            rg_name,
            account_name,
            {
                'location': location,
                'locations': [{'location_name': location}],
                'database_account_offer_type': 'Standard',
                'enable_free_tier': True
            }
        )
        account = poller.result()
        logger.info(f"Created Cosmos DB account {account_name}")
    
    # Get the connection keys
    keys = client.database_accounts.list_keys(rg_name, account_name)
    
    # Create the database and containers
    cosmos_client = CosmosClient(
        url=f'https://{account_name}.documents.azure.com:443/',
        credential=keys.primary_master_key
    )
    
    # Create database if it doesn't exist
    try:
        database = cosmos_client.create_database(db_name)
        logger.info(f"Created database {db_name}")
    except:
        database = cosmos_client.get_database_client(db_name)
        logger.info(f"Database {db_name} already exists")
    
    # Create containers
    containers = [
        {'id': 'vehicles', 'partition_key': '/VehicleId'},
        {'id': 'services', 'partition_key': '/vehicleId'},
        {'id': 'commands', 'partition_key': '/vehicleId'},
        {'id': 'notifications', 'partition_key': '/vehicleId'}
    ]
    
    for container_spec in containers:
        try:
            container = database.create_container(
                id=container_spec['id'],
                partition_key=container_spec['partition_key']
            )
            logger.info(f"Created container {container_spec['id']}")
        except:
            container = database.get_container_client(container_spec['id'])
            logger.info(f"Container {container_spec['id']} already exists")
    
    return {
        'endpoint': f'https://{account_name}.documents.azure.com:443/',
        'key': keys.primary_master_key,
        'database': db_name,
        'containers': {c['id']: c['id'] for c in containers}
    }

def save_to_env_file(env_file, values):
    """Save values to .env file"""
    with open(env_file, 'w') as f:
        for key, value in values.items():
            f.write(f"{key}={value}\n")
    logger.info(f"Saved environment variables to {env_file}")

def main():
    """Main function"""
    args = parse_args()
    
    # Load existing environment variables
    load_dotenv(args.env_file, override=True)
    
    logger.info("Initializing Azure resources for Connected Vehicle Platform")
    
    # Get credentials
    credential, subscription_id = get_credentials()
    
    # Ensure resource group exists
    ensure_resource_group(credential, subscription_id, args.resource_group, args.location)
    
    # Create Cosmos DB
    cosmos_config = create_cosmos_db(
        credential, 
        subscription_id, 
        args.resource_group, 
        args.cosmos_account, 
        args.location, 
        args.database_name
    )
      # Generate environment variables
    env_vars = {
        'AZURE_ENABLED': 'true',
        'AZURE_SUBSCRIPTION_ID': subscription_id,
        'COSMOS_DB_ENDPOINT': cosmos_config['endpoint'],
        'COSMOS_DB_KEY': cosmos_config['key'],
        'COSMOS_DB_DATABASE': cosmos_config['database'],
        'COSMOS_DB_CONTAINER_VEHICLES': cosmos_config['containers']['vehicles'],
        'COSMOS_DB_CONTAINER_SERVICES': cosmos_config['containers']['services'],
        'COSMOS_DB_CONTAINER_COMMANDS': cosmos_config['containers']['commands'],
        'COSMOS_DB_CONTAINER_NOTIFICATIONS': cosmos_config['containers']['notifications'],
        'AZURE_OPENAI_DEPLOYMENT_NAME': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4'),
        'AZURE_OPENAI_ENDPOINT': os.getenv('AZURE_OPENAI_ENDPOINT', ''),
        'AZURE_OPENAI_API_KEY': os.getenv('AZURE_OPENAI_API_KEY', ''),
        'AZURE_OPENAI_API_VERSION': os.getenv('AZURE_OPENAI_API_VERSION', '2023-12-01-preview')
    }
    
    # Save to .env file
    save_to_env_file(args.env_file, env_vars)
    
    logger.info("Azure resources initialization complete")
    logger.info(f"To use the Azure resources, make sure to set AZURE_ENABLED=true in your environment")
    logger.info(f"You may need to manually configure your Azure OpenAI service and update the values in {args.env_file}")

if __name__ == "__main__":
    main()
