#!/bin/bash

# Attempt to get the web app URL from an environment variable
WEBAPP_URL=$(printenv | grep -i "WEBAPP_URL" | cut -d'=' -f2)

# If the URL is not found in environment variables, try to extract it from logs
if [ -z "$WEBAPP_URL" ]; then
    WEBAPP_URL=$(your_platform_cli logs | grep -oP 'http://\S+')
fi

# If the URL is successfully found, start sending periodic requests
if [ -n "$WEBAPP_URL" ]; then
    echo "Web app URL found: $WEBAPP_URL"
    while true; do
        curl -s "$WEBAPP_URL" > /dev/null
        echo "Sent request to keep the web app alive."
        sleep 60  # Adjust the sleep duration as needed
    done
else
    echo "Failed to determine the web app URL. Please check your configuration."
fi
