# code.py - Main CircuitPython code for Smart Bookshelf with servo manager

import time
import board
import pwmio
import busio
import microcontroller
import neopixel
import adafruit_requests
import ssl
import socketpool
import wifi
import json
import traceback
from adafruit_motor import servo
from servo_manager import ServoManager

# Wi-Fi and API Configuration
try:
    from secrets import secrets
    WIFI_SSID = secrets["ssid"]
    WIFI_PASSWORD = secrets["password"]
    API_URL = secrets["api_url"]
except ImportError:
    # Fallback values if secrets.py doesn't exist
    WIFI_SSID = "your_wifi_ssid"
    WIFI_PASSWORD = "your_wifi_password"
    API_URL = "http://your-database-server.com:8000/api"

# Constants
CHECK_INTERVAL = 5  # Check for new commands every 5 seconds
SERVO_PUSH_DURATION = 1.5  # How long to hold the push position

# LED status colors
LED_COLORS = {
    "boot": (255, 0, 255),    # Magenta - Starting up
    "connecting": (0, 0, 255), # Blue - Connecting to WiFi
    "ready": (0, 255, 0),      # Green - Connected and ready
    "active": (255, 255, 0),   # Yellow - Servo active
    "error": (255, 0, 0),      # Red - Error
    "off": (0, 0, 0)           # Off
}

# Configure servo pins
SERVO_PINS = [
    board.GP0, board.GP1, board.GP2, board.GP3, board.GP4,
    board.GP5, board.GP6, board.GP7, board.GP8, board.GP9
]

# Global variables
pixel = None
servo_manager = None
requests_session = None
last_command_id = None

def setup_hardware():
    """Initialize all hardware components"""
    global pixel, servo_manager
    
    # Setup onboard NeoPixel for status indication
    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3)
    pixel.fill(LED_COLORS["boot"])
    
    # Initialize Servo Manager
    servo_manager = ServoManager()
    
    # Create and add all servo objects to the manager
    for pin in SERVO_PINS:
        # Configure PWM output for each servo
        pwm = pwmio.PWMOut(pin, duty_cycle=0, frequency=50)
        # Create a servo object
        servo_motor = servo.Servo(pwm, min_pulse=500, max_pulse=2500)
        # Add to manager with default settings
        servo_manager.add_servo(servo_motor)
    
    print(f"Initialized {len(servo_manager.servos)} servo motors")
    
    # Optional: Test all servos briefly
    # servo_manager.center_all()
    # time.sleep(1)
    # servo_manager.test_all()

def set_status(status):
    """Set the status LED color"""
    if pixel:
        pixel.fill(LED_COLORS.get(status, LED_COLORS["error"]))

def connect_wifi():
    """Connect to WiFi network"""
    print(f"Connecting to {WIFI_SSID}...")
    set_status("connecting")
    
    # Connect to WiFi
    try:
        wifi.radio.connect(WIFI_SSID, WIFI_PASSWORD)
        print(f"Connected to {WIFI_SSID}!")
        print(f"IP Address: {wifi.radio.ipv4_address}")
        set_status("ready")
        time.sleep(1)
        return True
    except Exception as e:
        print(f"Failed to connect to WiFi: {e}")
        # Flash error pattern
        for _ in range(5):
            set_status("error")
            time.sleep(0.2)
            set_status("off")
            time.sleep(0.2)
        return False

def setup_http():
    """Set up the HTTP session for API requests"""
    global requests_session
    
    try:
        # Create a socket pool for the Wi-Fi interface
        pool = socketpool.SocketPool(wifi.radio)
        
        # Create a requests object
        requests_session = adafruit_requests.Session(pool, ssl.create_default_context())
        return True
    except Exception as e:
        print(f"Error setting up HTTP session: {e}")
        return False

def get_latest_command():
    """Check the API for any new commands"""
    global last_command_id
    
    try:
        # Brief LED flash to show we're checking
        current_status = pixel[0]
        set_status("connecting")
        
        # GET request to check for latest commands
        response = requests_session.get(f"{API_URL}/query/latest")
        data = response.json()
        
        # Restore LED
        pixel.fill(current_status)
        
        # Check if this is a new command
        if data.get("id") != last_command_id and data.get("status") == "pending":
            last_command_id = data.get("id")
            
            # Extract the book index and activate the servo
            book_index = data.get("match", {}).get("index")
            if book_index is not None:
                print(f"Received command to activate book at index {book_index}")
                
                # Activate the servo
                set_status("active")
                success = servo_manager.push_and_return(
                    book_index, 
                    push_angle=180, 
                    duration=SERVO_PUSH_DURATION
                )
                set_status("ready")
                
                # Update command status
                status_update = {"id": last_command_id, "status": "completed" if success else "failed"}
                update_response = requests_session.post(
                    f"{API_URL}/query/update", 
                    json=status_update,
                    headers={"Content-Type": "application/json"}
                )
                print(f"Command {last_command_id} completed with status: {status_update['status']}")
                
        return True
    except Exception as e:
        print(f"Error checking for commands: {e}")
        traceback.print_exception(e, e, e.__traceback__)
        
        # Flash error briefly
        set_status("error")
        time.sleep(0.5)
        set_status("ready")
        return False

def main():
    """Main program entry point"""
    try:
        # Initialize hardware
        setup_hardware()
        
        # Connect to WiFi
        wifi_connected = connect_wifi()
        if not wifi_connected:
            # If we can't connect, go into a safe mode
            # Blink error pattern indefinitely
            while True:
                set_status("error")
                time.sleep(0.5)
                set_status("off")
                time.sleep(0.5)
        
        # Set up HTTP session
        http_setup = setup_http()
        if not http_setup:
            # If HTTP setup fails, indicate error but try to continue
            set_status("error")
            time.sleep(2)
            set_status("ready")
        
        # Center all servos at startup
        servo_manager.center_all()
        
        # Main loop
        print("Entering main loop")
        while True:
            try:
                get_latest_command()
                time.sleep(CHECK_INTERVAL)
                
                # Optional: Add a heartbeat indicator
                pixel.brightness = 0.1  # Dim briefly
                time.sleep(0.1)
                pixel.brightness = 0.3  # Back to normal
                
            except Exception as e:
                print(f"Main loop error: {e}")
                # Indicate error but continue
                set_status("error")
                time.sleep(1)
                set_status("ready")
                
                # Try to reconnect if needed
                if not wifi.radio.connected:
                    print("WiFi disconnected. Attempting to reconnect...")
                    connect_wifi()
                    setup_http()
    
    except Exception as e:
        # Catch any unhandled exceptions
        print(f"Critical error: {e}")
        traceback.print_exception(e, e, e.__traceback__)
        
        # Flash SOS pattern
        while True:
            # ... 3 short flashes
            for _ in range(3):
                set_status("error")
                time.sleep(0.2)
                set_status("off")
                time.sleep(0.2)
            time.sleep(0.4)
            
            # --- 3 long flashes
            for _ in range(3):
                set_status("error")
                time.sleep(0.6)
                set_status("off")
                time.sleep(0.2)
            time.sleep(0.4)
            
            # ... 3 short flashes again
            for _ in range(3):
                set_status("error")
                time.sleep(0.2)
                set_status("off")
                time.sleep(0.2)
            
            time.sleep(1.5)  # Pause between SOS signals

# Run the main function
if __name__ == "__main__":
    main()
