import os
import asyncio
import requests
import logging
import time
import subprocess

logger = logging.getLogger("Provisioner")

# The path inside the OpenPLC container where program files live
CONTAINER_ST_PATH = "/root/OpenPLC_v3/webserver/st_files/blank_program.st"

class Provisioner:
    """
    Handles the injection of .st logic into a running OpenPLC container.
    
    Strategy (confirmed working via smoke test):
    1. Copy our .st file into the container via `docker cp`, overwriting blank_program.st
    2. Call `reload-program?table_id=1` via HTTP to trigger compilation
    3. Wait for compilation to complete (~20s)
    4. Call `start_plc` to start the PLC runtime
    """
    def __init__(self, docker_manager):
        self.dm = docker_manager
        self.client = docker_manager.client

    def _wait_for_openplc(self, base_url: str, timeout: int = 90) -> bool:
        """Poll the OpenPLC login page until the container HTTP server is ready."""
        logger.info(f"Waiting for OpenPLC at {base_url}...")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                res = requests.get(f"{base_url}/login", timeout=3)
                if res.status_code == 200:
                    logger.info("OpenPLC web server is ready!")
                    return True
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(2)
        logger.error("OpenPLC did not start in time.")
        return False

    def _login(self, session: requests.Session, base_url: str, ied_id: str) -> bool:
        """Login to OpenPLC and return True on success."""
        try:
            res = session.post(
                f"{base_url}/login",
                data={"username": "openplc", "password": "openplc"},
                timeout=10,
                allow_redirects=True
            )
            if res.status_code == 200 and "dashboard" in res.text.lower():
                logger.info(f"IED {ied_id}: Login successful.")
                return True
            logger.error(f"IED {ied_id}: Login failed. Status: {res.status_code}")
            return False
        except Exception as e:
            logger.error(f"IED {ied_id}: Login exception: {e}")
            return False

    async def provision_ied(self, ied_id: str, st_path: str, web_port: int) -> bool:
        """
        Full automated provisioning:
        1. Wait for container web server
        2. Copy ST file into container via docker cp
        3. Trigger compilation via reload-program?table_id=1
        4. Wait ~20s for compilation
        5. Start PLC
        """
        base_url = f"http://127.0.0.1:{web_port}"
        container_name = f"trinetra-ied-{ied_id}"

        # --- Step 1: Wait for web server ---
        loop = asyncio.get_event_loop()
        ready = await loop.run_in_executor(None, self._wait_for_openplc, base_url)
        if not ready:
            return False

        # --- Step 2: Inject ST file via docker cp ---
        logger.info(f"IED {ied_id}: Injecting ST code into container via docker cp...")
        try:
            result = subprocess.run(
                ["docker", "cp", st_path, f"{container_name}:{CONTAINER_ST_PATH}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                logger.error(f"IED {ied_id}: docker cp failed: {result.stderr}")
                return False
            logger.info(f"IED {ied_id}: ST file injected successfully.")
        except Exception as e:
            logger.error(f"IED {ied_id}: docker cp exception: {e}")
            return False

        session = requests.Session()

        # --- Step 3: Login ---
        if not self._login(session, base_url, ied_id):
            return False

        # --- Step 4: Trigger compilation (reload-program activates the injected file) ---
        logger.info(f"IED {ied_id}: Triggering compilation via reload-program...")
        try:
            reload_res = session.get(f"{base_url}/reload-program?table_id=1", timeout=15)
            logger.info(f"IED {ied_id}: Reload response: {reload_res.status_code}")
        except Exception as e:
            logger.error(f"IED {ied_id}: reload-program failed: {e}")
            return False

        # --- Step 5: Wait for compilation ---
        logger.info(f"IED {ied_id}: Compiling logic... (~20 seconds)")
        await asyncio.sleep(22)

        # --- Step 6: Start PLC ---
        logger.info(f"IED {ied_id}: Starting PLC Runtime...")
        try:
            start_res = session.get(f"{base_url}/start_plc", timeout=10)
            logger.info(f"IED {ied_id}: start_plc response: {start_res.status_code}")
        except Exception as e:
            logger.error(f"IED {ied_id}: start_plc failed: {e}")
            return False

        # --- Step 7: Verify ---
        await asyncio.sleep(3)
        try:
            status_res = session.get(f"{base_url}/dashboard", timeout=10)
            if "running" in status_res.text.lower():
                logger.info(f"IED {ied_id}: ✅ PLC RUNNING at http://127.0.0.1:{web_port}/dashboard")
            else:
                logger.warning(f"IED {ied_id}: Start sent. Verify at http://127.0.0.1:{web_port}/dashboard")
        except Exception:
            pass

        return True
