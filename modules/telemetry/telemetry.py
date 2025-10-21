"""
Telemetry gathering logic.
"""

import time

from pymavlink import mavutil

from ..common.modules.logger import logger


class TelemetryData:  # pylint: disable=too-many-instance-attributes
    """
    Python struct to represent Telemtry Data. Contains the most recent attitude and position reading.
    """

    def __init__(
        self,
        time_since_boot: int | None = None,  # ms
        x: float | None = None,  # m
        y: float | None = None,  # m
        z: float | None = None,  # m
        x_velocity: float | None = None,  # m/s
        y_velocity: float | None = None,  # m/s
        z_velocity: float | None = None,  # m/s
        roll: float | None = None,  # rad
        pitch: float | None = None,  # rad
        yaw: float | None = None,  # rad
        roll_speed: float | None = None,  # rad/s
        pitch_speed: float | None = None,  # rad/s
        yaw_speed: float | None = None,  # rad/s
    ) -> None:
        self.time_since_boot = time_since_boot
        self.x = x
        self.y = y
        self.z = z
        self.x_velocity = x_velocity
        self.y_velocity = y_velocity
        self.z_velocity = z_velocity
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.roll_speed = roll_speed
        self.pitch_speed = pitch_speed
        self.yaw_speed = yaw_speed

    def __str__(self) -> str:
        return f"""{{
            time_since_boot: {self.time_since_boot},
            x: {self.x},
            y: {self.y},
            z: {self.z},
            x_velocity: {self.x_velocity},
            y_velocity: {self.y_velocity},
            z_velocity: {self.z_velocity},
            roll: {self.roll},
            pitch: {self.pitch},
            yaw: {self.yaw},
            roll_speed: {self.roll_speed},
            pitch_speed: {self.pitch_speed},
            yaw_speed: {self.yaw_speed}
        }}"""


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Telemetry:
    """
    Telemetry class to read position and attitude (orientation).
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        # Put your own arguments here
        local_logger: logger.Logger,
    ) -> "tuple[True, Telemetry] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a Telemetry object.
        """
        if connection is None or local_logger is None:
            return False, None
        return True, cls(cls.__private_key, connection, local_logger)  # Create a Telemetry object

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        # Put your own arguments here
        local_logger: logger.Logger,
    ) -> None:
        assert key is Telemetry.__private_key, "Use create() method"

        # Do any intializiation here
        self.connection = connection
        self._logger = local_logger
        self.attitude_message = None
        self.position_message = None
        self._logger.info("telemetry.py initialized")

    # gets telemetry messages from drone and returns it
    def run(
        self,
    ) -> TelemetryData:
        """
        Receive LOCAL_POSITION_NED and ATTITUDE messages from the drone,
        combining them together to form a single TelemetryData object.
        """
        starting_time = time.time()
        timeout_period = 1

        _position_msg = None
        _attitude_msg = None

        while time.time() - starting_time < timeout_period:
            msg = self.connection.recv_match(
                type=["LOCAL_POSITION_NED", "ATTITUDE"], blocking=False, timeout=0.1
            )
            if not msg:
                continue
            if msg.get_type() == "LOCAL_POSITION_NED":
                _position_msg = msg
            if msg.get_type() == "ATTITUDE":
                _attitude_msg = msg

            if _position_msg and _attitude_msg:
                break
        if _position_msg and _attitude_msg:
            self.attitude_message = _attitude_msg
            self.position_message = _position_msg
            telemetry_data = TelemetryData(
                # Read MAVLink message LOCAL_POSITION_NED (32)
                # Read MAVLink message ATTITUDE (30)
                # Return the most recent of both, and use the most recent message's timestamp
                time_since_boot=max(
                    self.position_message.time_boot_ms, self.attitude_message.time_boot_ms
                ),  # ms
                x=self.position_message.x,  # m
                y=self.position_message.y,  # m
                z=self.position_message.z,  # m
                x_velocity=self.position_message.vx,  # m/s
                y_velocity=self.position_message.vy,  # m/s
                z_velocity=self.position_message.vz,  # m/s
                roll=self.attitude_message.roll,  # rad
                pitch=self.attitude_message.pitch,  # rad
                yaw=self.attitude_message.yaw,  # rad
                roll_speed=self.attitude_message.rollspeed,  # rad/s
                pitch_speed=self.attitude_message.pitchspeed,  # rad/s
                yaw_speed=self.attitude_message.yawspeed,  # rad/s
            )
            return telemetry_data
        return None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
