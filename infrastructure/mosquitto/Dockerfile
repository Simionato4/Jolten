FROM eclipse-mosquitto:2

COPY mosquitto.conf /mosquitto/config/mosquitto.conf

ENTRYPOINT ["/bin/sh", "-c", "\
  rm -f /mosquitto/config/passwd && \
  mosquitto_passwd -c -b /mosquitto/config/passwd ${MQTT_USER} ${MQTT_PASS} && \
  chown mosquitto:mosquitto /mosquitto/config/passwd && \
  chmod 0700 /mosquitto/config/passwd && \
  exec mosquitto -c /mosquitto/config/mosquitto.conf \
"]
