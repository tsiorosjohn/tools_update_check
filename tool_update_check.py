import os
import json
import time
import threading
import requests

LOCAL_VERSION_FILE = "local_version.json"
LAST_CHECK_FILE = "last_check.json"
UPDATE_URL = "https://example.com/check_version"

# Lock for thread-safe access to shared resources
lock = threading.Lock()


def version_str_to_tuple(version_str):
    try:
        return tuple(map(int, version_str.split('.')))
    except ValueError:
        print(f"Invalid version string: {version_str}")
        return None


def check_online_version():
    try:
        response = requests.get(UPDATE_URL)
        online_data = response.json()  # Assumes the response is in JSON format
        return version_str_to_tuple(online_data.get("version", ""))
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Error checking online version: {e}")
        return None


def save_last_check_timestamp():
    current_timestamp = time.time()
    data = {"last_check_timestamp": current_timestamp}

    with open(LAST_CHECK_FILE, 'w') as file:
        json.dump(data, file)


def load_last_check_timestamp():
    if os.path.exists(LAST_CHECK_FILE):
        with open(LAST_CHECK_FILE, 'r') as file:
            data = json.load(file)
            return data.get("last_check_timestamp", 0)
    return 0  # Return 0 if the file doesn't exist


def load_local_version():
    if os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, 'r') as file:
            data = json.load(file)
            return data.get("latest_version")
    return None


def save_local_version(latest_version):
    data = {"latest_version": latest_version}

    with open(LOCAL_VERSION_FILE, 'w') as file:
        json.dump(data, file)


def update_check_thread():
    with lock:
        last_check_timestamp = load_last_check_timestamp()
        current_timestamp = time.time()
        one_month_seconds = 30 * 24 * 60 * 60  # Approximate seconds in a month

        if current_timestamp - last_check_timestamp >= one_month_seconds:
            local_version = load_local_version()
            latest_version = check_online_version()

            if latest_version and local_version:
                if latest_version > local_version:
                    print(f"New version available: {latest_version}")
                    # Implement update mechanism here

                    # Save the new version to the local JSON file
                    save_local_version(latest_version)
                else:
                    print("You have the latest version. Proceeding with execution.")

                # Save the current timestamp after a successful check
                save_last_check_timestamp()
            else:
                print("Version comparison failed. Proceeding with execution.")
        else:
            print(f"Check already performed within the last month. Latest version from local info: {load_local_version()}")


def main():
    # Create a separate thread for the update check
    update_thread = threading.Thread(target=update_check_thread)

    # Start the update check thread in the background
    update_thread.start()

    # Rest of your script goes here

    # Wait for the update check thread to finish before exiting the main thread
    update_thread.join()


if __name__ == "__main__":
    main()
