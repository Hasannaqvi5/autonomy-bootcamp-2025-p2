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
        timeout_period = 1  # Wait up to 1 second for both messages

        _position_msg = None
        _attitude_msg = None

        # Loop until both position and attitude messages are received or timeout occurs
        while time.time() - starting_time < timeout_period:
            # Look for specific MAVLink message types
            msg = self.connection.recv_match(
                type=["LOCAL_POSITION_NED", "ATTITUDE"], blocking=False, timeout=0.1
            )
            if not msg:
                continue

            # Store the latest position message
            if msg.get_type() == "LOCAL_POSITION_NED":
                _position_msg = msg
            # Store the latest attitude (orientation) message
            if msg.get_type() == "ATTITUDE":
                _attitude_msg = msg

            # If both have been received, we can stop early
            if _position_msg and _attitude_msg:
                break

        # If we have both messages, package them into a TelemetryData object
        if _position_msg and _attitude_msg:
            self.attitude_message = _attitude_msg
            self.position_message = _position_msg
            telemetry_data = TelemetryData(
                # Use the most recent timestamp from either message for synchronization
                time_since_boot=max(
                    self.position_message.time_boot_ms, self.attitude_message.time_boot_ms
                ),
                # Position coordinates (North-East-Down coordinate system)
                x=self.position_message.x,
                y=self.position_message.y,
                z=self.position_message.z,
                # Velocity components
                x_velocity=self.position_message.vx,
                y_velocity=self.position_message.vy,
                z_velocity=self.position_message.vz,
                # Orientation (Roll, Pitch, Yaw)
                roll=self.attitude_message.roll,
                pitch=self.attitude_message.pitch,
                yaw=self.attitude_message.yaw,
                # Rotational speeds
                roll_speed=self.attitude_message.rollspeed,
                pitch_speed=self.attitude_message.pitchspeed,
                yaw_speed=self.attitude_message.yawspeed,
            )
            return telemetry_data

        # Return None if both messages were not received within the timeout
        return None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
