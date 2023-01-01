#!/bin/sh

sudo docker pull python:3
sudo docker build --tag saltyhash/led_strip_controller -f Dockerfile .
