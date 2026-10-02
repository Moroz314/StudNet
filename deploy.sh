#!/usr/bin/env bash
set -e

echo "============================================="
echo "  StudNet Deployment Script for 136.234.4.160"
echo "============================================="

# Проверка наличия .env файла
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    echo "⚠️  .env file not found, creating from .env.example..."
    cp .env.example .env
  else
    echo "❌ Error: Neither .env nor .env.example found!"
    exit 1
  fi
fi

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed. Please install Docker first."
    exit 1
fi

echo "📦 Pulling base images..."
docker compose pull postgres redis minio adminer || true

echo "🔨 Building and starting services..."
docker compose down --remove-orphans || true
docker compose up -d --build

echo "⏳ Waiting for services to become healthy..."
sleep 5

echo "📊 Checking container status:"
docker compose ps

echo ""
echo "============================================="
echo "✅ StudNet is deployed!"
echo "🌐 Frontend:  http://136.234.4.160:3000"
echo "⚙️ Backend:   http://136.234.4.160:8000"
echo "🗄️ Adminer:   http://136.234.4.160:8080"
echo "🪣 MinIO S3:  http://136.234.4.160:9100"
echo "🎛️ MinIO UI:  http://136.234.4.160:9101"
echo ""
echo "Для просмотра логов бэкенда (включая коды подтверждения email):"
echo "  docker compose logs -f backend"
echo "============================================="
