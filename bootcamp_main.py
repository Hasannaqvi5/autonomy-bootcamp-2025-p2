"""
Bootcamp F2025

Main process to setup and manage all the other working processes
"""

import multiprocessing as mp
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger
from modules.common.modules.logger import logger_main_setup
from modules.common.modules.read_yaml import read_yaml
from modules.command import command
from modules.command import command_worker
from modules.heartbeat import heartbeat_receiver_worker
from modules.heartbeat import heartbeat_sender_worker
from modules.telemetry import telemetry_worker
from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from utilities.workers import worker_manager


# MAVLink connection
CONNECTION_STRING = "tcp:localhost:12345"

# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
# Set queue max sizes (<= 0 for infinity)
COMMAND_QUEUE_SIZE = 5
HB_QUEUE_SIZE = 5
TELEMETRY_QUEUE_SIZE = 10
# Set worker counts
HEARTBEAT_SENDER_WORKER_COUNT = 1
HEARTBEAT_RECEIVER_WORKER_COUNT = 1
TELEMETRY_WORKER_COUNT = 1
COMMAND_WORKER_COUNT = 1

# Any other constants
RUN_TIME = 100  # number of seconds for test to run for
TARGET = command.Position(0, 20, 10)

# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================


def main() -> int:
    """
    Main function.
    """
    # Configuration settings
    result, config = read_yaml.open_config(logger.CONFIG_FILE_PATH)
    if not result:
        print("ERROR: Failed to load configuration file")
        return -1

    # Get Pylance to stop complaining
    assert config is not None

    # Setup main logger
    result, main_logger, _ = logger_main_setup.setup_main_logger(config)
    if not result:
        print("ERROR: Failed to create main logger")
        return -1

    # Get Pylance to stop complaining
    assert main_logger is not None

    # Create a connection to the drone. Assume that this is safe to pass around to all processes
    # In reality, this will not work, but to simplify the bootamp, preetend it is allowed
    # To test, you will run each of your workers individually to see if they work
    # (test "drones" are provided for you test your workers)
    # NOTE: If you want to have type annotations for the connection, it is of type mavutil.mavfile
    connection = mavutil.mavlink_connection(CONNECTION_STRING)
    connection.wait_heartbeat(timeout=30)  # Wait for the "drone" to connect

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Create a worker controller
    wc = worker_controller.WorkerController()
    # Create a multiprocess manager for synchronized queues
    mp_manager = mp.Manager()

    # Create queues
    telemetry_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, TELEMETRY_QUEUE_SIZE)
    heartbeat_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, HB_QUEUE_SIZE)
    command_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, COMMAND_QUEUE_SIZE)

    # Create worker properties for each worker type (what inputs it takes, how many workers)
    # Heartbeat sender
    flag, heartbeat_sender_worker_properties = worker_manager.WorkerProperties.create(
        count=HEARTBEAT_SENDER_WORKER_COUNT,
        target=heartbeat_sender_worker.heartbeat_sender_worker,  # function to run
        work_arguments=(connection,),
        input_queues=[],
        output_queues=[],
        controller=wc,
        local_logger=main_logger,
    )
    if not flag:
        main_logger.error("Failed to create heartbeat sender worker properties")
        return -1

    # Heartbeat receiver
    flag, heartbeat_receiver_worker_properties = worker_manager.WorkerProperties.create(
        count=HEARTBEAT_RECEIVER_WORKER_COUNT,
        target=heartbeat_receiver_worker.heartbeat_receiver_worker,  # function to run
        work_arguments=(connection,),
        input_queues=[],
        output_queues=[heartbeat_queue],
        controller=wc,
        local_logger=main_logger,
    )
    if not flag:
        main_logger.error("Failed to create heartbeat receiver worker properties")
        return -1

    # Telemetry
    flag, telemetry_worker_properties = worker_manager.WorkerProperties.create(
        count=TELEMETRY_WORKER_COUNT,
        target=telemetry_worker.telemetry_worker,  # function to run
        work_arguments=(connection,),
        input_queues=[],
        output_queues=[telemetry_queue],
        controller=wc,
        local_logger=main_logger,
    )
    if not flag:
        main_logger.error("Failed to create telemetry worker properties")
        return -1

    # Command
    flag, command_worker_properties = worker_manager.WorkerProperties.create(
        count=COMMAND_WORKER_COUNT,
        target=command_worker.command_worker,  # function to run
        work_arguments=(TARGET, connection),
        input_queues=[
            telemetry_queue,
        ],
        output_queues=[command_queue],
        controller=wc,
        local_logger=main_logger,
    )
    if not flag:
        main_logger.error("Failed to create command worker properties")
        return -1

    # Create the workers (processes) and obtain their managers
    # hb sender
    result, heartbeat_sender_manager = worker_manager.WorkerManager.create(
        heartbeat_sender_worker_properties, main_logger
    )
    if not result:
        main_logger.error("Failed to create heartbeat sender manager")

    # Start worker processes

    # hb receiver
    result, heartbeat_receiver_manager = worker_manager.WorkerManager.create(
        heartbeat_receiver_worker_properties, main_logger
    )
    if not result:
        main_logger.error("Failed to create heartbeat receiver manager")

    # telemetry
    result, telemetry_manager = worker_manager.WorkerManager.create(
        telemetry_worker_properties, main_logger
    )
    if not result:
        main_logger.error("Failed to create telemetry manager")

    # command
    # hb sender
    result, command_manager = worker_manager.WorkerManager.create(
        command_worker_properties, main_logger
    )
    if not result:
        main_logger.error("Failed to create command worker manager")

    # Start worker processes
    heartbeat_sender_manager.start_workers()
    heartbeat_receiver_manager.start_workers()
    telemetry_manager.start_workers()
    command_manager.start_workers()

    main_logger.info("Started")

    # Main's work: read from all queues that output to main, and log any commands that we make
    # Continue running for 100 seconds or until the drone disconnects
    starting_time = time.time()
    while time.time() - starting_time < RUN_TIME:
        command_data = command_queue.queue.get(block=True, timeout=3)
        if command_data is not None:
            main_logger.info(f"received command:{command_data}")

        hb_data = heartbeat_queue.queue.get(block=True, timeout=5)
        if hb_data is not None:
            if hb_data == "Disconnected":
                break
            main_logger.info(f"received status:{hb_data}")

    # Stop the processes
    wc.request_exit()
    main_logger.info("Requested exit")

    # Fill and drain queues from END TO START
    command_queue.fill_and_drain_queue()
    heartbeat_queue.fill_and_drain_queue()
    telemetry_queue.fill_and_drain_queue()
    main_logger.info("Queues cleared")

    # Clean up worker processes
    heartbeat_sender_manager.join_workers()
    heartbeat_receiver_manager.join_workers()
    telemetry_manager.join_workers()
    command_manager.join_workers()

    main_logger.info("Stopped")

    # We can reset controller in case we want to reuse it
    # Alternatively, create a new WorkerController instance
    wc.clear_exit()
    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Failed with return code {result_main}")
    else:
        print("Success!")
