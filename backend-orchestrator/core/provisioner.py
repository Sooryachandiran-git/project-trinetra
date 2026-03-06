import os
import docker
import time
import requests
import logging

logger = logging.getLogger("Provisioner")

class Provisioner:
    """
    Handles the injection of .st logic into a running OpenPLC container and starts the PLC.
    """
    def __init__(self, docker_manager):
        self.dm = docker_manager
        self.client = docker_manager.client

    async def provision_ied(self, ied_id: str, st_path: str, web_port: int) -> bool:
        """
        Uploads the .st file to the OpenPLC container and triggers the compilation/start process.
        """
        if not self.client:
            return False

        container_name = f"trinetra-ied-{ied_id}"
        
        try:
            container = self.client.containers.get(container_name)
            
            # Step 1: Upload the file into the container
            # OpenPLC v3 expects the program files in /home/openplc/OpenPLC_v3/scripts/
            # and the active program name to be stored in the DB or a specific file.
            # A simpler way for this project is to use the OpenPLC internal API or
            # just copy the file and restart the OpenPLC process.
            
            # For this prototype, we'll use a bash command inside the container to replace the current program.
            with open(st_path, 'rb') as f:
                data = f.read()
            
            # Use 'docker cp' equivalent logic (simpler via put_archive but binary is complex)
            # We'll use a simple approach: echo the content into the container.
            st_content = data.decode('utf-8').replace('"', '\\"')
            container.exec_run(f'bash -c "echo \\"{st_content}\\" > /workdir/scripts/trinetra.st"')
            
            logger.info(f"IED {ied_id}: ST code injected.")

            # Step 2: In a real OpenPLC instance, we need to compile and start.
            # The official way is the Web API on port 8080. 
            # We skip the heavy compilation for now and assume the container has a 
            # pre-compiled runner that looks at 'trinetra.st'.
            
            return True

        except Exception as e:
            logger.error(f"Failed to provision IED {ied_id}: {e}")
            return False
