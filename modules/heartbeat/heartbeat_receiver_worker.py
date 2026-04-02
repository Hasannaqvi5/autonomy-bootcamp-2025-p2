"""
Heartbeat worker that sends heartbeats periodically.
"""

import os
import pathlib
import time

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from . import heartbeat_receiver
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def heartbeat_receiver_worker(
    heartbeat_time: float,
    connection: mavutil.mavfile,
    output_queue: queue_proxy_wrapper.QueueProxyWrapper,
    controller: worker_controller.WorkerController,
) -> None:
    """

    connection: connection instance
    output_queue: output to the main process
    controller: how the main process communicates to this worker
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
    # Instantiate class object (heartbeat_receiver.HeartbeatReceiver)
    # This class listens for incoming heartbeats from the drone to monitor connection status
    flag, reciever = heartbeat_receiver.HeartbeatReceiver.create(connection, local_logger)
    if not flag:
        local_logger.error("Failed to create receiver instance")
        return
    local_logger.info(f"receiver worker started: {flag}")

    # Main loop: periodically check for heartbeats
    while not controller.is_exit_requested():
        # Check for the latest heartbeat status
        status = reciever.run()

        # Always put the status into the queue (e.g., "Connected" or "Disconnected")
        # so the main process knows the current connection state
        output_queue.queue.put(f"{status} at {time.strftime('%H:%M:%S')}")

        # Wait for the specified interval before checking again
        time.sleep(heartbeat_time)

    local_logger.info("receiver worker stopped")

    # Main loop: do work.


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
