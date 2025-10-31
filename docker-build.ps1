#!/usr/bin/env pwsh
param(
    [string]$Tag = "latest"
)

$imageName = "agentic-vehicle-platform:$Tag"

Write-Host "`nBuilding with docker-compose: $imageName`n"

$env:IMAGE_TAG = $Tag
docker-compose --env-file .env.docker up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Build successful: $imageName`n"
    docker-compose --env-file .env.docker ps
} else {
    Write-Host "`n✗ Build failed`n"
    exit 1
}
