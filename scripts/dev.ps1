docker compose -f docker-compose.dev.yaml up -d
fastapi dev ./src/pindb/ --host 0.0.0.0
