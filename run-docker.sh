#!/bin/bash

# Check if docker is installed
if ! [ -x "$(command -v docker)" ]; then
  echo 'Error: docker is not installed.' >&2
  exit 1
fi

echo "Starting TIITBA Web with Docker..."
docker compose up --build -d

echo "------------------------------------------------"
echo "Application is starting up!"
echo "Visit: http://localhost:8000"
echo "------------------------------------------------"
echo "To stop the app, run: docker compose down"
