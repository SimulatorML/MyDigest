#!/bin/sh

# write your own values
IMAGE_NAME=my-digest
TAG=last

docker build --build-arg SOME_NEED_ARG=$SOME_NEED_ARG \
 -t local/$IMAGE_NAME:$TAG .