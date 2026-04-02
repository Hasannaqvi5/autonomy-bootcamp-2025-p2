"""
Heartbeat receiving logic.
"""

from pymavlink import mavutil

from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatReceiver:
    """
    HeartbeatReceiver class to send a heartbeat
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,  # Put your own arguments here
        local_logger: logger,
    ) -> "tuple[True, HeartbeatReceiver] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a HeartbeatReceiver object.
        """
        if connection is None or local_logger is None:
            return False, None
        return True, cls(cls.__private_key, connection, local_logger)

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger,
        # Put your own arguments here
    ) -> None:
        assert key is HeartbeatReceiver.__private_key, "Use create() method"

        # Do any intializiation here
        self.connection = connection
        self._log = local_logger
        self._log.info("heartbeat reciever initialized")
        self._missed = 0
        self.state = "Disconnected"

    def run(self) -> str:
        """
        Attempt to receive a heartbeat message from the drone.
        If heartbeats are missed for 5 consecutive periods, the drone is considered disconnected.
        """
        # Try to find a heartbeat message in the incoming MAVLink stream
        message = self.connection.recv_match(type="HEARTBEAT", blocking=False)

        if message:
            # Heartbeat received: reset missed counter and set state to Connected
            self._missed = 0
            self.state = "Connected"
        else:
            # No heartbeat: increment missed counter and log a warning
            self._missed += 1
            self._log.warning(f"Missed heartbeat. {self._missed} missed in a row.")

            # If 5 or more heartbeats are missed, transition to Disconnected state
            if self._missed >= 5:
                self.state = "Disconnected"

        self._log.info(f"Current receiver status: {self.state}")
        return self.state


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
