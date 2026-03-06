import os
import asyncio
import requests
import logging
import time

logger = logging.getLogger("Provisioner")

class Provisioner:
    """
    Handles the injection of .st logic into a running OpenPLC container
    and starts the PLC via the OpenPLC v3 Web API.
    """
    def __init__(self, docker_manager):
        self.dm = docker_manager
        self.client = docker_manager.client

    def _wait_for_openplc(self, base_url: str, timeout: int = 60) -> bool:
        """Poll the OpenPLC login page until the container is ready."""
        logger.info(f"Waiting for OpenPLC at {base_url} to become ready...")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                res = requests.get(f"{base_url}/login", timeout=3)
                if res.status_code == 200:
                    logger.info("OpenPLC is ready!")
                    return True
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(2)
        logger.error("OpenPLC did not become ready in time.")
        return False

    async def provision_ied(self, ied_id: str, st_path: str, web_port: int) -> bool:
        """
        Full provisioning pipeline:
        1. Wait for container web server to be ready
        2. Login with session cookies
        3. Upload the .st file
        4. Compile the program
        5. Start PLC Runtime
        """
        base_url = f"http://127.0.0.1:{web_port}"

        # Wait in a thread to not block the event loop
        loop = asyncio.get_event_loop()
        ready = await loop.run_in_executor(None, self._wait_for_openplc, base_url)
        if not ready:
            return False

        session = requests.Session()

        try:
            # --- Step 1: Login ---
            logger.info(f"IED {ied_id}: Authenticating with OpenPLC...")
            login_res = session.post(
                f"{base_url}/login",
                data={"username": "openplc", "password": "openplc"},
                timeout=10,
                allow_redirects=True
            )
            # A successful login returns 200 on the dashboard page
            if login_res.status_code != 200 or "dashboard" not in login_res.text.lower():
                logger.error(f"IED {ied_id}: Login failed. Status: {login_res.status_code}")
                return False
            logger.info(f"IED {ied_id}: Login successful.")

            # --- Step 2: Upload Program ---
            logger.info(f"IED {ied_id}: Uploading ST code from {st_path}...")
            with open(st_path, 'rb') as f:
                files = {'file': ('trinetra.st', f, 'text/plain')}
                upload_res = session.post(
                    f"{base_url}/upload-program",
                    files=files,
                    timeout=15
                )
            
            if upload_res.status_code not in (200, 302):
                logger.error(f"IED {ied_id}: Upload failed. Status: {upload_res.status_code}")
                logger.error(f"IED {ied_id}: Response: {upload_res.text[:500]}")
                return False
            logger.info(f"IED {ied_id}: Upload successful. Waiting for compilation...")

            # --- Step 3: Wait for Compilation ---
            # OpenPLC compiles immediately on upload. We give it time.
            await asyncio.sleep(25)

            # --- Step 4: Start PLC ---
            logger.info(f"IED {ied_id}: Starting PLC Runtime...")
            start_res = session.get(f"{base_url}/start_plc", timeout=10)
            logger.info(f"IED {ied_id}: Start PLC response: {start_res.status_code}")

            # Verify it started
            await asyncio.sleep(2)
            status_res = session.get(f"{base_url}/dashboard", timeout=10)
            if "running" in status_res.text.lower():
                logger.info(f"IED {ied_id}: ✅ PLC CONFIRMED RUNNING at http://127.0.0.1:{web_port}/dashboard")
                return True
            else:
                logger.warning(f"IED {ied_id}: PLC start sent. Check http://127.0.0.1:{web_port}/dashboard manually.")
                return True

        except Exception as e:
            logger.error(f"Failed to provision IED {ied_id}: {e}", exc_info=True)
            return False
