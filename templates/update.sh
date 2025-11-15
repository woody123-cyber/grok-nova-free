#!/bin/bash
cd /opt/nova-bot
git pull origin main
docker restart nova
