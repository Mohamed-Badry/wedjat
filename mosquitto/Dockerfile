FROM eclipse-mosquitto:2.0.18

COPY entrypoint.sh /mosquitto/entrypoint.sh
RUN chmod +x /mosquitto/entrypoint.sh

ENTRYPOINT ["/mosquitto/entrypoint.sh"]
