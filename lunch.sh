#!/usr/bin/env bash
set -e #sale del script si algo sale mal
set -a
source .envi
set +a

docker secret inspect postgres_host >/dev/null 2>&1 || echo "$postgres_host" | docker secret create postgres_host -
docker secret inspect postgres_user >/dev/null 2>&1 || echo "$postgres_user" | docker secret create postgres_user -
docker secret inspect postgres_password >/dev/null 2>&1 || echo "$postgres_password" | docker secret create postgres_password -

docker build -t api-fast:v1 .

sleep 5

docker stack deploy -c stack.yaml app