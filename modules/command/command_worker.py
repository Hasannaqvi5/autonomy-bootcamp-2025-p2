"""
Command worker to make decisions based on Telemetry Data.
"""

import os
import pathlib

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from . import command
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def command_worker(
    connection: mavutil.mavfile,
    target: command.Position,
    input_queue: queue_proxy_wrapper.QueueProxyWrapper,
    output_queue: queue_proxy_wrapper.QueueProxyWrapper,
    controller: worker_controller.WorkerController,
    # Place your own arguments here
    # Add other necessary worker arguments here
) -> None:
    """
    Worker process.
    target:target position
    input:recieve telemetry data
    output:output to other processes
    controller: how main process communicates to worker process
    args... describe what the arguments are
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
    # Instantiate class object (command.Command)
    # This class handles the logic for determining which commands to send based on telemetry
    flag, command_instance = command.Command.create(connection, target, local_logger)

    if not flag:
        local_logger.error("Error while creating Command instance")
        return

    # Main loop: listen for telemetry data and generate commands
    while not controller.is_exit_requested():
        controller.check_pause()

        # If the input queue (telemetry data) is empty, skip to the next iteration
        if input_queue.queue.empty():
            continue

        # Get the next message from the input queue
        msg = input_queue.queue.get(timeout=1.0)
        if msg is None:
            continue

        # Process the telemetry message to generate a command
        result = command_instance.run(msg)

        # If a command was generated, put it into the output queue
        if result != "":
            output_queue.queue.put(result)


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
