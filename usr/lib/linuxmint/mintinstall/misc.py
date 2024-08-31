#!/usr/bin/python3

import os
import time
import requests
import logging
from typing import Callable

# Environment variable is converted to a boolean value.
DEBUG_MODE = bool(os.getenv("MINTINSTALL_DEBUG", "False").lower() in ("true", "1", "t"))

# Setup logging if in debug mode
if DEBUG_MODE:
    logging.basicConfig(filename='mintinstall_debug.log', level=logging.DEBUG,
                        format='%(asctime)s - %(message)s')

def print_timing(func: Callable) -> Callable:
    if not DEBUG_MODE:
        return func
    
    def wrapper(*args, **kwargs):
        t1 = time.time()
        res = func(*args, **kwargs)
        t2 = time.time()
        logging.debug(f'{func.__qualname__} took {((t2 - t1) * 1000.0):.3f} ms')
        return res
    
    return wrapper

def debug(message: str) -> None:
    if DEBUG_MODE:
        print(f"Mintinstall (DEBUG): {message}")
        logging.debug(message)

def networking_available(url: str = "https://8.8.8.8", timeout: int = 1, retries: int = 3) -> bool:
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()  # Ensure the request was successful
            return True
        except requests.RequestException as e:
            debug(f"Network check failed (Attempt {attempt + 1}/{retries}): {e}")
            time.sleep(1)  # Wait a moment before retrying
    return False

def check_specific_url(url: str, timeout: int = 1) -> bool:
    return networking_available(url=url, timeout=timeout)

# Example usage
if __name__ == "__main__":
    if networking_available():
        debug("Network is available.")
    else:
        debug("Network is not available.")
    
    # Example for checking a specific URL
    if check_specific_url("https://www.example.com"):
        debug("www.example.com is reachable.")
    else:
        debug("www.example.com is not reachable.")

