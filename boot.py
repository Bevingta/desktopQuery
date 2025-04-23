# boot.py - This runs before code.py when the Pico boots
# Use this for configuring WiFi credentials, secrets, and other initialization

import board
import digitalio
import storage
import supervisor
import neopixel

# Optional: Use a button to enter "safe mode" if needed
# Connect a button between GP22 and GND
try:
    safe_mode_pin = digitalio.DigitalInOut(board.GP22)  # Choose any available GPIO
    safe_mode_pin.direction = digitalio.Direction.INPUT
    safe_mode_pin.pull = digitalio.Pull.UP
    
    # Check if button is pressed during startup (pulled to GND)
    if not safe_mode_pin.value:
        # Button is pressed - enable USB drive and enter safe mode
        print("Safe mode button detected! Enabling USB drive...")
        storage.remount("/", readonly=False)
        
        # Flash LED in a pattern to indicate safe mode
        led = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3)
        for i in range(10):  # Flash 10 times
            led[0] = (0, 0, 255)  # Blue
            supervisor.delay_us(200000)  # 0.2 seconds
            led[0] = (0, 0, 0)    # Off
            supervisor.delay_us(200000)  # 0.2 seconds
        
    else:
        # Normal operation - disable USB drive to prevent corruption during operation
        # Only enable this once your code is working properly
        # storage.disable_usb_drive()
        pass
        
except Exception as e:
    print(f"Error in boot.py: {e}")
    # If there's a problem, make sure USB drive remains enabled
    storage.remount("/", readonly=False)

# Configure CPU frequency for better power efficiency
# For battery operation, you might want to lower this
# supervisor.set_cpu_speed(supervisor.CPU_SPEED_125MHZ)  # Slower, more efficient
# supervisor.set_cpu_speed(supervisor.CPU_SPEED_250MHZ)  # Default speed
