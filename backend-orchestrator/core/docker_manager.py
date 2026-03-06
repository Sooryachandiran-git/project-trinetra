import docker
import logging
from typing import List, Dict, Any

logger = logging.getLogger("DockerManager")

class DockerManager:
    """
    Automates the lifecycle of OpenPLC Docker containers for the TRINETRA testbed.
    """
    def __init__(self, image: str = "tuttas/openplc_v3"):
        try:
            self.client = docker.from_env()
            self.image = image
            # On Apple Silicon Macs, we need to force amd64 for this specific image
            self.platform = "linux/amd64" 
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None

    def run_ied(self, ied_id: str, modbus_port: int, web_port: int) -> bool:
        """
        Launches an OpenPLC container for a specific IED.
        Maps the Web UI and Modbus TCP ports.
        """
        if not self.client:
            return False

        container_name = f"trinetra-ied-{ied_id}"
        
        # Check if already running
        try:
            existing = self.client.containers.get(container_name)
            if existing.status == "running":
                logger.info(f"IED {ied_id} is already running.")
                return True
            else:
                existing.start()
                return True
        except docker.errors.NotFound:
            pass

        logger.info(f"Launching IED {ied_id} (Web: {web_port}, Modbus: {modbus_port})...")
        try:
            self.client.containers.run(
                self.image,
                name=container_name,
                detach=True,
                platform=self.platform,
                ports={
                    '8080/tcp': web_port,
                    '502/tcp': modbus_port
                },
                restart_policy={"Name": "unless-stopped"}
            )
            return True
        except Exception as e:
            logger.error(f"Error launching IED {ied_id}: {e}")
            return False

    def stop_all_ieds(self):
        """
        Finds and stops all containers with the 'trinetra-ied-' prefix.
        """
        if not self.client:
            return

        containers = self.client.containers.list(all=True, filters={"name": "trinetra-ied-"})
        for container in containers:
            logger.info(f"Stopping and removing container {container.name}...")
            try:
                container.stop()
                container.remove()
            except Exception as e:
                logger.error(f"Error removing container {container.name}: {e}")

    def get_container_ip(self, ied_id: str) -> str:
        """Returns the internal Docker bridge IP of the IED container."""
        if not self.client:
            return "127.0.0.1"
        
        try:
            container = self.client.containers.get(f"trinetra-ied-{ied_id}")
            return container.attrs['NetworkSettings']['IPAddress']
        except:
            return "127.0.0.1"
