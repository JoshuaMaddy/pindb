if (-not (Test-Path node_modules)) {
    Write-Host "Installing npm dependencies..."
    npm ci
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

npm run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker compose -f docker-compose.dev.yaml up -d
fastapi dev ./src/pindb/ --host 0.0.0.0
