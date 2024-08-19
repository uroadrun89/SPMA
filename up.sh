#!/bin/bash

while true; do
    curl -s http://your-webapp-url.com > /dev/null
    sleep 60  # Send a request every 60 seconds
done
