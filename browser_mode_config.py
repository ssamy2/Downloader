"""
Browser Mode Configuration
Allows switching between different browser modes for testing
"""
import os
from enum import Enum

class BrowserMode(Enum):
    HEADLESS = "headless"
    HEADED = "headed"
    NEW_HEADLESS = "new_headless"

# Get browser mode from environment variable
# Default to headless for server environments
BROWSER_MODE = BrowserMode(os.getenv("BROWSER_MODE", "headless").lower())

def get_browser_launch_args():
    """Get browser launch arguments based on mode"""
    base_args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
    ]
    
    if BROWSER_MODE == BrowserMode.HEADLESS:
        return {"headless": True, "args": base_args}
    elif BROWSER_MODE == BrowserMode.HEADED:
        return {"headless": False, "args": base_args}
    elif BROWSER_MODE == BrowserMode.NEW_HEADLESS:
        return {"headless": "new", "args": base_args}
    
    return {"headless": False, "args": base_args}

print(f"🌐 Browser mode: {BROWSER_MODE.value}")
