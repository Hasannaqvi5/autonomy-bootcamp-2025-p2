"""
Telemtry worker that gathers GPS data.
"""

import os
import pathlib

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from . import telemetry
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def telemetry_worker(
    connection: mavutil.mavfile,
    output_queue: queue_proxy_wrapper.QueueProxyWrapper,
    controller: worker_controller.WorkerController,
    # Place your own arguments here
    # Add other necessary worker arguments here
) -> None:
    """
    Worker process.

    connection:connection instance
    output_queue: output to other processes
    controller: how main process communicates with worker process
    """
    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    # Instantiate logger
    worker_name = pathlib.Path(__file__).stem
    process_id = os.getpid()
    result, local_logger = logger.Logger.create(f"{worker_name}_{process_id}", True)
    if not result:
        print("ERROR: Worker failed to create logger")
        return

    # Get Pylance to stop complaining
    assert local_logger is not None

    local_logger.info("Logger initialized", True)

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Instantiate class object (telemetry.Telemetry)
    # This creates an instance that will handle the actual MAVLink communication for telemetry
    flag, telemetry_instance = telemetry.Telemetry.create(connection, local_logger)
    if not flag:
        local_logger.error("Failed to create Telemetry instance")
        return

    local_logger.info("Telemetry Worker Started")

    # Main loop: continue running until the controller requests an exit
    while not controller.is_exit_requested():
        # Check if the process should be paused
        controller.check_pause()

        # Run the telemetry instance to fetch the latest data from the drone
        data = telemetry_instance.run()

        # If no data was received (e.g., due to timeout), skip this iteration
        if not data:
            continue

        # Put the telemetry data into the output queue for the main process
        output_queue.queue.put(data)
        local_logger.info(f"Telemetry data: {data}")

    local_logger.info("Telemetry Worker Stopped")


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
