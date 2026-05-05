import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Simulator")

def main():
    logger.info("Simulator scaffolding complete. Waiting for implementation of data/raw replay...")
    
    # Keeps container alive until we implement the actual Mosquitto publishing loop
    while True:
        time.sleep(10)

if __name__ == "__main__":
    main()
