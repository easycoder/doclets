#!/usr/bin/env python3
"""
Kills the running instance of docletServer.ecs
"""

import os
import sys
import subprocess
import signal
import time

def main():
    # Look for a running instance of docletServer.ecs
    try:
        # Use ps to find docletServer.ecs processes
        result = subprocess.run(
            ["ps", "-eaf"],
            capture_output=True,
            text=True,
            check=True
        )

        # Filter for docletServer.ecs (excluding grep itself and this script)
        pid = None
        for line in result.stdout.splitlines():
            if "docletServer.ecs" in line and "grep" not in line and str(os.getpid()) not in line:
                # Get the second field (PID)
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        break
                    except ValueError:
                        continue

        # If we found a PID, kill the process
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Killed process {pid}")
            except ProcessLookupError:
                print(f"Process {pid} already terminated")
            except PermissionError:
                print(f"Permission denied to kill process {pid}")
                sys.exit(1)

    except subprocess.CalledProcessError as e:
        print(f"Error running ps command: {e}")
    #     sys.exit(1)
    #
    # # Start a new instance and wait for it to complete
    # print("Start a new instance")
    # try:
    #     result = subprocess.run(["$HOME/easycoder", "docletServer.ecs"], check=True)
    #     # print("docletServer.ecs completed successfully")
    # except Exception as e:
    #     print("Terminated: ,e")

if __name__ == "__main__":
    main()
