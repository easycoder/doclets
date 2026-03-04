#!/usr/bin/env sh
set -e

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <browser_mqtt_token>"
  exit 1
fi

printf '%s\n' "$1" > mqtt-client-token.txt
chmod 600 mqtt-client-token.txt

echo "Wrote mqtt-client-token.txt"
