import os
import asyncio
import requests
import logging
import time
import subprocess

logger = logging.getLogger("Provisioner")

CONTAINER_ST_PATH = "/root/OpenPLC_v3/webserver/st_files/blank_program.st"
COMPILE_SCRIPT = "scripts/compile_program.sh"
COMPILE_WORKDIR = "/root/OpenPLC_v3/webserver"

class Provisioner:
    """
    Handles the injection and compilation of .st logic into a running OpenPLC container.
    
    CONFIRMED WORKING STRATEGY (verified via docker exec + modbus reads):
    1. docker cp .st file into container
    2. docker exec <container> bash scripts/compile_program.sh blank_program.st
       (This correctly runs iec2c + g++ and updates the running openplc binary)
    3. Login via HTTP and call start_plc to restart the PLC runtime
    
    NOTE: reload-program?table_id=1 does NOT recompile. It only reloads the already-compiled binary.
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

    def _docker_exec(self, container_name: str, cmd: str, timeout: int = 60) -> tuple:
        """Run a command inside the container via docker exec. Returns (returncode, stdout, stderr)."""
        result = subprocess.run(
            ["docker", "exec", container_name, "bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr

    async def provision_ied(self, ied_id: str, st_path: str, web_port: int) -> bool:
        """
        Full compilation and provisioning pipeline:
        1. Wait for container web server
        2. Copy ST file into container via docker cp
        3. Compile via docker exec + compile_program.sh (CORRECT compile method)
        4. Login via HTTP
        5. start_plc to restart the PLC runtime
        """
        base_url = f"http://127.0.0.1:{web_port}"
        container_name = f"trinetra-ied-{ied_id}"

        # --- Step 1: Wait for web server ---
        loop = asyncio.get_event_loop()
        ready = await loop.run_in_executor(None, self._wait_for_openplc, base_url)
        if not ready:
            return False

        # --- Step 2: Copy ST file into container ---
        logger.info(f"IED {ied_id}: Injecting ST file via docker cp...")
        try:
            result = subprocess.run(
                ["docker", "cp", st_path, f"{container_name}:{CONTAINER_ST_PATH}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                logger.error(f"IED {ied_id}: docker cp failed: {result.stderr}")
                return False
            logger.info(f"IED {ied_id}: ST file injected ✓")
        except Exception as e:
            logger.error(f"IED {ied_id}: docker cp exception: {e}")
            return False

        # --- Step 3: Compile via the correct script (confirmed working) ---
        logger.info(f"IED {ied_id}: Compiling ST code via compile_program.sh (~30s)...")
        try:
            rc, stdout, stderr = await loop.run_in_executor(
                None,
                lambda: self._docker_exec(
                    container_name,
                    f"cd {COMPILE_WORKDIR} && bash {COMPILE_SCRIPT} blank_program.st 2>&1",
                    timeout=120
                )
            )
            if "Compilation finished successfully!" in stdout:
                logger.info(f"IED {ied_id}: ✅ Compilation successful!")
                # Log which variables were compiled
                for line in stdout.split("\n"):
                    if "varName" in line:
                        logger.info(f"  {line.strip()}")
            else:
                logger.error(f"IED {ied_id}: Compilation may have failed:\n{stdout[-500:]}")
                return False
        except Exception as e:
            logger.error(f"IED {ied_id}: Compilation exception: {e}")
            return False

        # --- Step 4: Login and restart PLC via HTTP ---
        await asyncio.sleep(2)
        session = requests.Session()
        try:
            login_res = session.post(
                f"{base_url}/login",
                data={"username": "openplc", "password": "openplc"},
                timeout=10, allow_redirects=True
            )
            if "dashboard" not in login_res.text.lower():
                logger.error(f"IED {ied_id}: Login failed.")
                return False
            logger.info(f"IED {ied_id}: Logged in ✓")
        except Exception as e:
            logger.error(f"IED {ied_id}: Login exception: {e}")
            return False

        # --- Step 5: Start the PLC (loads the freshly compiled binary) ---
        logger.info(f"IED {ied_id}: Starting PLC Runtime...")
        try:
            start_res = session.get(f"{base_url}/start_plc", timeout=10)
            logger.info(f"IED {ied_id}: start_plc → HTTP {start_res.status_code}")
        except Exception as e:
            logger.error(f"IED {ied_id}: start_plc exception: {e}")
            return False

        # --- Step 6: Verify ---
        await asyncio.sleep(3)
        try:
            status_res = session.get(f"{base_url}/dashboard", timeout=10)
            if "running" in status_res.text.lower():
                logger.info(f"IED {ied_id}: ✅ PLC RUNNING → http://127.0.0.1:{web_port}/dashboard")
            else:
                logger.warning(f"IED {ied_id}: PLC started but verify at http://127.0.0.1:{web_port}/dashboard")
        except Exception:
            pass

        return True
