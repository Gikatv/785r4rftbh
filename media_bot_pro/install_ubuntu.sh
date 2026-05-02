#!/bin/bash
set -e
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg
cd "$(dirname "$0")"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp -n .env.example .env
echo "Edit .env and paste BOT_TOKEN, then run: ./run.sh"
