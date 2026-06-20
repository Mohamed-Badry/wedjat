#!/bin/sh
set -e

echo "Generating mosquitto configuration..."

# Write configuration
cat <<EOF > /mosquitto/config/mosquitto.conf
listener 1883
protocol mqtt
allow_anonymous false
password_file /mosquitto/config/pwfile
EOF

# Create password file
touch /mosquitto/config/pwfile
if [ -n "$MQTT_USERNAME" ] && [ -n "$MQTT_PASSWORD" ]; then
    echo "Creating MQTT user: $MQTT_USERNAME"
    mosquitto_passwd -b /mosquitto/config/pwfile "$MQTT_USERNAME" "$MQTT_PASSWORD"
fi

echo "Starting Mosquitto broker..."
exec /docker-entrypoint.sh mosquitto -c /mosquitto/config/mosquitto.conf
