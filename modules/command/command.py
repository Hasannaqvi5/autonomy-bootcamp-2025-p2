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
        telemetry_data: telemetry.TelemetryData,
    ) -> str:
        """
        Make a decision based on received telemetry data.
        Calculates average velocity and adjusts altitude and yaw to reach the target.
        """

        # Extract current velocity from telemetry and store it for averaging
        vx, vy, vz = telemetry_data.x_velocity, telemetry_data.y_velocity, telemetry_data.z_velocity
        self.velocity_data.append([vx, vy, vz])

        # Calculate moving average of velocity component-wise
        sum_vx = sum_vy = sum_vz = 0
        for v in self.velocity_data:
            sum_vx += v[0]
            sum_vy += v[1]
            sum_vz += v[2]

        avg_vx = sum_vx / len(self.velocity_data)
        avg_vy = sum_vy / len(self.velocity_data)
        avg_vz = sum_vz / len(self.velocity_data)

        # Log the average velocity for performance tracking
        self.logger.info(
            f"avg velocity for trip so far: ({avg_vx:.2f}, {avg_vy:.2f}, {avg_vz:.2f})"
        )

        # 1. Height Adjustment
        # Use MAV_CMD_CONDITION_CHANGE_ALT (113). If error from target is > 0.5m, send command.
        if abs(self.target.z - telemetry_data.z) > 0.5:
            self.connection.mav.command_long_send(
                1,
                0,  # target_system, target_component
                mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT,
                0,  # confirmation
                1,  # change rate (1m/s)
                0,
                0,
                0,
                0,
                0,
                self.target.z,  # param 7: target altitude
            )
            return f"CHANGE_ALTITUDE: {self.target.z-telemetry_data.z:.2f}m"

        # 2. Heading (Yaw) Adjustment
        # Calculate the angle between current position and target using atan2
        target_yaw_degrees = math.degrees(
            math.atan2(self.target.y - telemetry_data.y, self.target.x - telemetry_data.x)
        )

        current_yaw_degrees = math.degrees(telemetry_data.yaw)
        # Calculate the shortest angle to reach target yaw
        yaw_angle = (target_yaw_degrees - current_yaw_degrees + 180) % 360 - 180

        # If the yaw error is > 5 degrees, send MAV_CMD_CONDITION_YAW (115)
        if abs(yaw_angle) > 5:
            # direction: 1 for CW, -1 for CCW. MAVLink uses 1 for CW and -1 for CCW for relative yaw.
            direction = -1 if yaw_angle > 0 else 1

            self.connection.mav.command_long_send(
                1,
                0,  # target_system, target_component
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                0,  # confirmation
                abs(yaw_angle),  # param 1: degree angle
                5,  # param 2: angular speed (5 deg/s)
                direction,  # param 3: direction
                1,  # param 4: relative (1) or absolute (0)
                0,
                0,
                0,
            )
            return f"CHANGING_YAW: {yaw_angle:.2f} degrees"

        return ""


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
