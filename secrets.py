# secrets.py - Store sensitive configuration here
# This file should not be shared in public repositories

# IMPORTANT: Replace these values with your actual credentials
secrets = {
    # WiFi credentials
    'ssid': 'your_wifi_ssid',
    'password': 'your_wifi_password',
    
    # API endpoints
    'api_url': 'http://your-database-server.com:8000/api',
    
    # Optional: time server for RTC synchronization
    'time_server': 'pool.ntp.org',
    
    # Optional: Timezone offset in hours from UTC
    'timezone_offset': -5,  # Eastern Standard Time (UTC-5)
    
    # Optional: Name for this device (useful when you have multiple)
    'device_name': 'bookshelf_controller',
}
