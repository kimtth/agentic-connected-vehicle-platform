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
import time
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.cosmosdb import CosmosDBManagementClient
from azure.cosmos import CosmosClient, exceptions
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
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
    parser.add_argument('--skip-openai', action='store_true', help='Skip Azure OpenAI service validation')
    return parser.parse_args()

def validate_resource_names(rg_name, cosmos_account, location):
    """Validate Azure resource naming conventions"""
    # Validate resource group name
    if not rg_name or len(rg_name) > 90:
        raise ValueError("Resource group name must be 1-90 characters")
    
    # Validate Cosmos DB account name
    if not cosmos_account or len(cosmos_account) > 50 or not cosmos_account.replace('-', '').isalnum():
        raise ValueError("Cosmos DB account name must be 3-50 characters, alphanumeric with hyphens")
    
    # Validate location
    valid_locations = ['eastus', 'westus', 'westus2', 'eastus2', 'centralus', 'northcentralus', 'southcentralus']
    if location not in valid_locations:
        logger.warning(f"Location {location} may not be valid. Common locations: {', '.join(valid_locations)}")

def get_credentials():
    """Get Azure credentials with improved error handling"""
    subscription_id = os.environ.get('AZURE_SUBSCRIPTION_ID')
    if not subscription_id:
        logger.error("AZURE_SUBSCRIPTION_ID environment variable not set")
        logger.error("Please set this variable or run 'az account show' to get your subscription ID")
        sys.exit(1)
    
    try:
        # Try DefaultAzureCredential first
        credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
        
        # Test the credential with a simple operation
        resource_client = ResourceManagementClient(credential, subscription_id)
        try:
            # Try to list resource groups to validate credentials
            list(resource_client.resource_groups.list(top=1))
            logger.info("Successfully authenticated with DefaultAzureCredential")
            return credential, subscription_id
        except Exception as auth_error:
            logger.warning(f"DefaultAzureCredential test failed: {str(auth_error)}")
            raise auth_error
            
    except Exception as e:
        logger.warning(f"DefaultAzureCredential failed: {str(e)}")
        logger.info("Attempting to use service principal credentials...")
        
        # Fall back to service principal
        tenant_id = os.environ.get('AZURE_TENANT_ID')
        client_id = os.environ.get('AZURE_CLIENT_ID')
        client_secret = os.environ.get('AZURE_CLIENT_SECRET')
        
        if not all([tenant_id, client_id, client_secret]):
            logger.error("Service principal credentials not properly configured")
            logger.error("Please run 'az login' or set AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET")
            sys.exit(1)
        
        try:
            credential = ClientSecretCredential(tenant_id, client_id, client_secret)
            
            # Test the credential
            resource_client = ResourceManagementClient(credential, subscription_id)
            list(resource_client.resource_groups.list(top=1))
            logger.info("Successfully authenticated with service principal")
            return credential, subscription_id
        except Exception as sp_error:
            logger.error(f"Service principal authentication failed: {str(sp_error)}")
            sys.exit(1)

def ensure_resource_group(credential, subscription_id, rg_name, location):
    """Ensure the resource group exists with proper error handling"""
    try:
        client = ResourceManagementClient(credential, subscription_id)
        
        # Check if the resource group exists
        try:
            rg = client.resource_groups.get(rg_name)
            logger.info(f"Resource group {rg_name} already exists in {rg.location}")
            return rg
        except ResourceNotFoundError:
            # Create the resource group
            logger.info(f"Creating resource group {rg_name} in {location}...")
            rg_params = {
                'location': location,
                'tags': {
                    'project': 'connected-vehicle-platform',
                    'environment': 'development'
                }
            }
            rg = client.resource_groups.create_or_update(rg_name, rg_params)
            logger.info(f"Successfully created resource group {rg_name}")
            return rg
            
    except Exception as e:
        logger.error(f"Failed to ensure resource group {rg_name}: {str(e)}")
        raise

def create_cosmos_db(credential, subscription_id, rg_name, account_name, location, db_name):
    """Create Cosmos DB account and database with improved error handling"""
    try:
        client = CosmosDBManagementClient(credential, subscription_id)
        
        # Check if the account exists
        try:
            account = client.database_accounts.get(rg_name, account_name)
            logger.info(f"Cosmos DB account {account_name} already exists")
        except ResourceNotFoundError:
            # Create the account
            logger.info(f"Creating Cosmos DB account {account_name}... This may take several minutes.")
            
            account_params = {
                'location': location,
                'locations': [{'location_name': location, 'failover_priority': 0}],
                'database_account_offer_type': 'Standard',
                'consistency_policy': {
                    'default_consistency_level': 'Session'
                },
                'enable_free_tier': True,
                'enable_automatic_failover': False,
                'capabilities': [
                    {'name': 'EnableServerless'}  # Use serverless for development
                ],
                'tags': {
                    'project': 'connected-vehicle-platform',
                    'environment': 'development'
                }
            }
            
            poller = client.database_accounts.begin_create_or_update(
                rg_name, account_name, account_params
            )
            
            # Wait for completion with progress updates
            logger.info("Waiting for Cosmos DB account creation to complete...")
            start_time = time.time()
            while not poller.done():
                elapsed = int(time.time() - start_time)
                logger.info(f"Still creating... ({elapsed}s elapsed)")
                time.sleep(30)
            
            account = poller.result()
            logger.info(f"Successfully created Cosmos DB account {account_name}")
        
        # Get the connection keys
        try:
            keys = client.database_accounts.list_keys(rg_name, account_name)
        except Exception as e:
            logger.error(f"Failed to retrieve Cosmos DB keys: {str(e)}")
            raise
        
        # Create the database and containers
        endpoint = f'https://{account_name}.documents.azure.com:443/'
        cosmos_client = CosmosClient(url=endpoint, credential=keys.primary_master_key)
        
        return create_cosmos_database_and_containers(cosmos_client, db_name, endpoint, keys.primary_master_key)
        
    except Exception as e:
        logger.error(f"Failed to create Cosmos DB: {str(e)}")
        raise

def create_cosmos_database_and_containers(cosmos_client, db_name, endpoint, key):
    """Create Cosmos DB database and containers with proper configuration"""
    try:
        # Create database if it doesn't exist
        try:
            database = cosmos_client.create_database(
                id=db_name,
                offer_throughput=400  # Minimum throughput
            )
            logger.info(f"Created database {db_name}")
        except exceptions.CosmosResourceExistsError:
            database = cosmos_client.get_database_client(db_name)
            logger.info(f"Database {db_name} already exists")
        
        # Define containers with proper configuration
        containers = [
            {
                'id': 'vehicles',
                'partition_key': {'paths': ['/VehicleId'], 'kind': 'Hash'},
                'indexing_policy': {
                    'indexingMode': 'consistent',
                    'automatic': True,
                    'includedPaths': [{'path': '/*'}],
                    'excludedPaths': [{'path': '/"_etag"/?'}]
                }
            },
            {
                'id': 'services',
                'partition_key': {'paths': ['/vehicleId'], 'kind': 'Hash'},
                'indexing_policy': {
                    'indexingMode': 'consistent',
                    'automatic': True,
                    'includedPaths': [{'path': '/*'}],
                    'excludedPaths': [{'path': '/"_etag"/?'}]
                }
            },
            {
                'id': 'commands',
                'partition_key': {'paths': ['/vehicleId'], 'kind': 'Hash'},
                'default_ttl': 86400,  # 24 hours TTL for commands
                'indexing_policy': {
                    'indexingMode': 'consistent',
                    'automatic': True,
                    'includedPaths': [
                        {'path': '/vehicleId/?'},
                        {'path': '/timestamp/?'},
                        {'path': '/status/?'}
                    ],
                    'excludedPaths': [{'path': '/*'}]
                }
            },
            {
                'id': 'notifications',
                'partition_key': {'paths': ['/vehicleId'], 'kind': 'Hash'},
                'default_ttl': 2592000,  # 30 days TTL for notifications
                'indexing_policy': {
                    'indexingMode': 'consistent',
                    'automatic': True,
                    'includedPaths': [
                        {'path': '/vehicleId/?'},
                        {'path': '/timestamp/?'},
                        {'path': '/type/?'}
                    ],
                    'excludedPaths': [{'path': '/*'}]
                }
            }
        ]
        
        created_containers = {}
        for container_spec in containers:
            try:
                container = database.create_container(
                    id=container_spec['id'],
                    partition_key=container_spec['partition_key'],
                    indexing_policy=container_spec.get('indexing_policy'),
                    default_ttl=container_spec.get('default_ttl'),
                    offer_throughput=400  # Minimum throughput per container
                )
                logger.info(f"Created container {container_spec['id']}")
                created_containers[container_spec['id']] = container_spec['id']
            except exceptions.CosmosResourceExistsError:
                logger.info(f"Container {container_spec['id']} already exists")
                created_containers[container_spec['id']] = container_spec['id']
        
        return {
            'endpoint': endpoint,
            'key': key,
            'database': db_name,
            'containers': created_containers
        }
        
    except Exception as e:
        logger.error(f"Failed to create database and containers: {str(e)}")
        raise

def validate_openai_config():
    """Validate Azure OpenAI configuration"""
    endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    api_key = os.getenv('AZURE_OPENAI_API_KEY')
    deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
    
    if not all([endpoint, api_key, deployment]):
        logger.warning("Azure OpenAI configuration incomplete")
        logger.warning("Please manually configure AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT_NAME")
        return False
    
    logger.info("Azure OpenAI configuration found")
    return True

def merge_env_variables(env_file, new_vars):
    """Merge new environment variables with existing ones"""
    existing_vars = {}
    
    # Load existing variables if file exists
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    existing_vars[key] = value
    
    # Merge variables (new variables take precedence)
    merged_vars = {**existing_vars, **new_vars}
    
    # Save merged variables
    with open(env_file, 'w') as f:
        f.write("# Azure Configuration for Connected Vehicle Platform\n")
        f.write("# Generated by azure_init.py\n\n")
        
        # Group variables by category
        azure_vars = {k: v for k, v in merged_vars.items() if k.startswith('AZURE_')}
        cosmos_vars = {k: v for k, v in merged_vars.items() if k.startswith('COSMOS_')}
        other_vars = {k: v for k, v in merged_vars.items() if not k.startswith(('AZURE_', 'COSMOS_'))}
        
        if azure_vars:
            f.write("# Azure Settings\n")
            for key, value in sorted(azure_vars.items()):
                f.write(f"{key}={value}\n")
            f.write("\n")
        
        if cosmos_vars:
            f.write("# Cosmos DB Settings\n")
            for key, value in sorted(cosmos_vars.items()):
                f.write(f"{key}={value}\n")
            f.write("\n")
        
        if other_vars:
            f.write("# Other Settings\n")
            for key, value in sorted(other_vars.items()):
                f.write(f"{key}={value}\n")
    
    logger.info(f"Updated environment variables in {env_file}")

def main():
    """Main function with comprehensive error handling"""
    try:
        args = parse_args()
        
        # Load existing environment variables
        if os.path.exists(args.env_file):
            load_dotenv(args.env_file, override=False)
        
        logger.info("Initializing Azure resources for Connected Vehicle Platform")
        
        # Validate resource names
        validate_resource_names(args.resource_group, args.cosmos_account, args.location)
        
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
        
        # Validate OpenAI configuration (optional)
        if not args.skip_openai:
            validate_openai_config()
        
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
        }
        
        # Only add OpenAI vars if they're not already set or if we have new values
        openai_vars = {
            'AZURE_OPENAI_DEPLOYMENT_NAME': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4'),
            'AZURE_OPENAI_ENDPOINT': os.getenv('AZURE_OPENAI_ENDPOINT', ''),
            'AZURE_OPENAI_API_KEY': os.getenv('AZURE_OPENAI_API_KEY', ''),
            'AZURE_OPENAI_API_VERSION': os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
        }
        env_vars.update(openai_vars)
        
        # Merge and save environment variables
        merge_env_variables(args.env_file, env_vars)
        
        logger.info("✅ Azure resources initialization complete!")
        logger.info(f"📝 Environment variables saved to: {args.env_file}")
        logger.info("🚀 Next steps:")
        logger.info("   1. Review and update Azure OpenAI settings in the .env file")
        logger.info("   2. Set AZURE_ENABLED=true in your application environment")
        logger.info("   3. Test the connection with your application")
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to initialize Azure resources: {str(e)}")
        logger.error("Please check your Azure credentials and permissions")
        sys.exit(1)

if __name__ == "__main__":
    main()
