# Ensure az is available
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI (az) not found. Install it and try again."
    exit 1
}

$resourceGroup = '<RESOURCE_GROUP_NAME>'
$templateFile  = 'deploy.bicep'
$paramsFile    = 'params.json'

az deployment group create `
    --resource-group $resourceGroup `
    --template-file $templateFile `
    --parameters @$paramsFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "Deployment failed."
    exit $LASTEXITCODE
}

Write-Output "Deployment completed successfully."
