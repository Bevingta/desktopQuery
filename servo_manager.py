# servo_manager.py - Helper module for managing servos in CircuitPython

import time
from adafruit_motor import servo

class ServoManager:
    """Helper class to manage multiple servo motors"""
    
    def __init__(self):
        self.servos = []
        self.positions = []  # Store current positions
        self.min_angles = []  # Store min angle for each servo
        self.max_angles = []  # Store max angle for each servo
        self.names = []      # Optional names for servos
    
    def add_servo(self, servo_obj, name=None, min_angle=0, max_angle=180):
        """Add a servo to the manager"""
        self.servos.append(servo_obj)
        self.positions.append(servo_obj.angle)  # Store initial position
        self.min_angles.append(min_angle)
        self.max_angles.append(max_angle)
        self.names.append(name if name else f"servo_{len(self.servos)-1}")
        return len(self.servos) - 1  # Return the index
    
    def set_angle(self, index, angle):
        """Set a servo to a specific angle, respecting its limits"""
        if 0 <= index < len(self.servos):
            # Constrain the angle to the servo's limits
            constrained_angle = max(self.min_angles[index], 
                                  min(self.max_angles[index], angle))
            
            # Update the servo
            self.servos[index].angle = constrained_angle
            self.positions[index] = constrained_angle
            return True
        return False
    
    def get_angle(self, index):
        """Get the current angle of a servo"""
        if 0 <= index < len(self.servos):
            return self.positions[index]
        return None
    
    def push_and_return(self, index, push_angle=180, duration=1.5):
        """Push a servo to a position and return to original position"""
        if 0 <= index < len(self.servos):
            # Store original position
            original = self.positions[index]
            
            # Move to push position
            self.set_angle(index, push_angle)
            time.sleep(duration)
            
            # Return to original position
            self.set_angle(index, original)
            return True
        return False
    
    def sequence(self, index, angles, durations):
        """Move a servo through a sequence of angles with specified durations"""
        if 0 <= index < len(self.servos) and len(angles) == len(durations):
            for i, angle in enumerate(angles):
                self.set_angle(index, angle)
                time.sleep(durations[i])
            return True
        return False
    
    def center_all(self):
        """Center all servos (90 degrees)"""
        for i in range(len(self.servos)):
            self.set_angle(i, 90)
    
    def rest_all(self):
        """Set all servos to their minimum position to reduce power consumption"""
        for i in range(len(self.servos)):
            self.set_angle(i, self.min_angles[i])
    
    def test_servo(self, index):
        """Test a servo with a simple movement sequence"""
        if 0 <= index < len(self.servos):
            original = self.positions[index]
            
            # Move to min, center, max, then back to original
            self.set_angle(index, self.min_angles[index])
            time.sleep(0.5)
            
            self.set_angle(index, 90)
            time.sleep(0.5)
            
            self.set_angle(index, self.max_angles[index])
            time.sleep(0.5)
            
            self.set_angle(index, original)
            return True
        return False
    
    def test_all(self):
        """Test all servos sequentially"""
        for i in range(len(self.servos)):
            print(f"Testing {self.names[i]} (index {i})")
            self.test_servo(i)
            time.sleep(0.5)  # Pause between servos
