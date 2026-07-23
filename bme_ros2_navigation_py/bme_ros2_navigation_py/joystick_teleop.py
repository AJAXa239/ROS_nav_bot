#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import serial

SERIAL_PORT = '/dev/ttyACM0'   # change if needed
BAUD_RATE = 115200

CENTER = 512
DEADZONE = 40
MAX_LINEAR = 0.5    # m/s, matches your DiffDrive plugin's max_linear_velocity
MAX_ANGULAR = 1.0   # rad/s, matches your DiffDrive plugin's max_angular_velocity


class JoystickTeleop(Node):
    def __init__(self):
        super().__init__('joystick_teleop')
        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)

        try:
            self.serial_port = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
        except serial.SerialException as e:
            self.get_logger().error(f'Could not open serial port {SERIAL_PORT}: {e}')
            raise

        self.timer = self.create_timer(0.02, self.read_and_publish)

    def read_and_publish(self):
        # Drain everything currently buffered; only the LAST complete line matters.
        latest_line = None
        while self.serial_port.in_waiting > 0:
            line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
            if line:
                latest_line = line

        if latest_line is None:
            return

        parts = latest_line.split(',')
        if len(parts) != 4:
            return

        try:
            x_raw = int(parts[0])
            y_raw = int(parts[1])
            estop_raw = int(parts[3])
        except ValueError:
            return

        twist = Twist()

        # D6 e-stop: pressed (0, since INPUT_PULLUP) -> force stop
        if estop_raw == 0:
            self.publisher_.publish(twist)  # zeroed Twist
            return

        x_offset = x_raw - CENTER
        y_offset = y_raw - CENTER

        if abs(x_offset) < DEADZONE:
            x_offset = 0
        if abs(y_offset) < DEADZONE:
            y_offset = 0

        # Y axis -> forward/backward (linear.x)
        linear = (y_offset / (1023 - CENTER)) * MAX_LINEAR
        # X axis -> turning (angular.z), negated so right = clockwise
        angular = -(x_offset / (1023 - CENTER)) * MAX_ANGULAR

        twist.linear.x = max(min(linear, MAX_LINEAR), -MAX_LINEAR)
        twist.angular.z = max(min(angular, MAX_ANGULAR), -MAX_ANGULAR)

        self.publisher_.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = JoystickTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
