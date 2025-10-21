"""
Decision-making logic.
"""

import math

from pymavlink import mavutil

from ..common.modules.logger import logger
from ..telemetry import telemetry


class Position:
    """
    3D vector struct.
    """

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Command:  # pylint: disable=too-many-instance-attributes
    """
    Command class to make a decision based on recieved telemetry,
    and send out commands based upon the data.
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        target: Position,  # Put your own arguments here
        local_logger: logger.Logger,
    ) -> "tuple[True, Command] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a Command object.
        """
        if connection is None or local_logger is None:
            return False, None
        command = cls(cls.__private_key, connection, target, local_logger)
        return True, command

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        target: Position,
        # Put your own arguments here
        local_logger: logger.Logger,
    ) -> None:
        assert key is Command.__private_key, "Use create() method"

        # Do any intializiation here
        self.connection = connection
        self.target = target
        self.logger = local_logger
        self.velocity_data = []

    def run(
        self,
        telemetry_data: telemetry.TelemetryData,  # Put your own arguments here
    ) -> str:
        """
        Make a decision based on received telemetry data.
        """

        # calculation
        vx, vy, vz = telemetry_data.x_velocity, telemetry_data.y_velocity, telemetry_data.z_velocity
        self.velocity_data.append([vx, vy, vz])
        sum_vx = 0
        sum_vy = 0
        sum_vz = 0

        for v in self.velocity_data:
            sum_vx += v[0]
            sum_vy += v[1]
            sum_vz += v[2]
        avg_vx = sum_vx / (len(self.velocity_data) * 1.0)
        avg_vy = sum_vy / (len(self.velocity_data) * 1.0)
        avg_vz = sum_vz / (len(self.velocity_data) * 1.0)

        # Log average velocity for this trip so far
        self.logger.info(f"avg velocity for trip: ({avg_vx}, {avg_vy}, {avg_vz})")

        # Use COMMAND_LONG (76) message, assume the target_system=1 and target_componenet=0
        # The appropriate commands to use are instructed below

        # Adjust height using the comand MAV_CMD_CONDITION_CHANGE_ALT (113)
        if abs(self.target.z - telemetry_data.z) > 0.5:
            self.connection.mav.command_long_send(
                1,
                0,
                mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT,
                0,
                1,
                0,
                0,
                0,
                0,
                0,
                self.target.z,
            )

            # String to return to main: "CHANGE_ALTITUDE: {amount you changed it by, delta height in meters}"
            return f"CHANGE_ALTITUDE: {self.target.z-telemetry_data.z}m"

        # Adjust direction (yaw) using MAV_CMD_CONDITION_YAW (115). Must use relative angle to current state
        # String to return to main: "CHANGING_YAW: {degree you changed it by in range [-180, 180]}"
        # Positive angle is counter-clockwise as in a right handed system

        target_yaw_degrees = math.degrees(
            math.atan2(self.target.y - telemetry_data.y, self.target.x - telemetry_data.x)
        )

        current_yaw_degrees = math.degrees(telemetry_data.yaw)
        yaw_angle = (target_yaw_degrees - current_yaw_degrees + 180) % 360 - 180

        if abs(yaw_angle) > 5:
            direction = -1
            if yaw_angle <= 0:
                direction = 1  # neg angle=cw=dir 1
            self.connection.mav.command_long_send(
                1,  # system
                0,  # component
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                0,  # confirmation
                yaw_angle,
                5,
                direction,
                1,
                0,
                0,
                0,
            )
            return f"CHANGING_YAW: {yaw_angle}"
        return ""


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
