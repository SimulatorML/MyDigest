#!/bin/sh

# write your own values
CONTAINER_NAME=my-digest
PORT=
IMAGE_NAME=local/my-digest:last
ENV_FILE=.env

docker run --rm -d --name $CONTAINER_NAME \
    -p $PORT:8080 \
    --env-file $ENV_FILE \
    -t $IMAGE_NAME \
    2> /dev/null \
    && echo $CONTAINER_NAME started || (echo $CONTAINER_NAME failed to start && exit 1)
docker logs -f $CONTAINER_NAME
