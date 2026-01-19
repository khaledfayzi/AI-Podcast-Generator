#!/bin/bash
HOST="45.81.234.206"
USER="podcast-dev"
DIR="~/podcast"

echo "Sync Code zu $HOST..."
rsync -avz --exclude='.git' --exclude='.venv' --exclude='__pycache__' --exclude='Output' --exclude='.env' ./ $USER@$HOST:$DIR/
echo "Starte Docker neu..."
ssh $USER@$HOST "cd $DIR && docker compose up --build -d"
echo "Fertig!"