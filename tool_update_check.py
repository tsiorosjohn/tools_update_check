import os
import json
import time
import threading
import re
from urllib import request, error

LAST_CHECK_FILE = "last_check.json"
UPDATE_URL = "https://raw.githubusercontent.com/tsiorosjohn/tools_update_check/master/latest_versions.json"
TOOL_VERSION = '1.1.0_beta 12.11.2023'
UPDATE_CHECK_DEBUG = True

# Lock for thread-safe access to shared resources
lock = threading.Lock()


def version_str_to_tuple(version_str):
    # Use regular expression to extract the version number
    version_match = re.match(r'^(\d+\.\d+\.\d+)', version_str)

    if version_match:
        version_number = version_match.group(1)
        return tuple(map(int, version_number.split('.')))
    else:
        if UPDATE_CHECK_DEBUG:
            print(f"Invalid version string: {version_str}")
        return None


def check_online_version():
    try:
        response = request.urlopen(UPDATE_URL)
        online_data = json.loads(response.read().decode('utf-8'))
        latest_version = online_data.get("latest_version", "")
        last_update_date = online_data.get("last_update_date", "")
        repo_url = online_data.get("repo_url", "")
        project_name = online_data.get("project_name", "")
        if UPDATE_CHECK_DEBUG:
            print(f"{latest_version = } // {repo_url = } // { project_name = }")
        return latest_version, last_update_date, repo_url, project_name
    except (error.URLError, json.JSONDecodeError) as e:
        if UPDATE_CHECK_DEBUG:
            print(f"Error checking online version: {e}")
        return None, None, None, None


def save_last_check_info(last_check_timestamp, latest_version, last_update_date, repo_url, project_name):
    data = {"last_check_timestamp": last_check_timestamp, "last_update_date": last_update_date, "latest_version_local": latest_version, "repo_url": repo_url,
            "project_name": project_name}
    print('saving...')
    with open(LAST_CHECK_FILE, 'w') as file:
        json.dump(data, file, indent=4)


def load_last_check_info(create_if_missing=False):
    default_timestamp = 0
    default_version = ''
    if os.path.exists(LAST_CHECK_FILE):
        with open(LAST_CHECK_FILE, 'r') as file:
            try:
                data = json.load(file)
                return data.get("last_check_timestamp", 0), data.get("latest_version_local")
            except json.JSONDecodeError:
                if UPDATE_CHECK_DEBUG:
                    print("Error decoding JSON in last_check.json. Creating a new one.")
    elif create_if_missing:
        if UPDATE_CHECK_DEBUG:
            print("last_check.json not found. Creating a new one.")
        # Create a new last_check.json file with default values
        default_timestamp = 0
        default_version = None
        data = {"last_check_timestamp": default_timestamp, "latest_version_local": default_version}
        with open(LAST_CHECK_FILE, 'w') as file:
            json.dump(data, file, indent=4)

    return default_timestamp, default_version


def update_check_thread():
    """
    Start a thread and check online if latest_version exists.
    If yes, store this in local json. Tool will get the info from local_json in next tool run and compare this with tool version
    """
    with lock:
        last_check_timestamp, local_latest_version = load_last_check_info(create_if_missing=True)
        current_timestamp = time.time()
        # delay_check_in_seconds = 7 * 24 * 60 * 60  # Approximate seconds in a week
        delay_check_in_seconds = 15  # Approximate seconds in a week

        # check online if delay_check_in_seconds has been elapsed - else, try to compare from locally stored (previously retrieved) 'local_latest_version'
        if current_timestamp - last_check_timestamp >= delay_check_in_seconds:
            latest_version, last_update_date, repo_url, project_name = check_online_version()

            if latest_version is not None:

                if version_str_to_tuple(latest_version) > version_str_to_tuple(TOOL_VERSION):
                    if UPDATE_CHECK_DEBUG:
                        print(f"New version available: {latest_version}, while tool version is: {TOOL_VERSION = }")
                        print(f"last_update_date: {last_update_date}")
                        print(f"Repository URL: {repo_url}")
                        print(f"Project Name: {project_name}")
                    # Implement update mechanism here

                    # Save the new version and timestamp to the local JSON file
                    save_last_check_info(current_timestamp, latest_version, last_update_date, repo_url, project_name)
                else:
                    if UPDATE_CHECK_DEBUG:
                        print("You have the latest version. Proceeding with execution.")

            else:
                if UPDATE_CHECK_DEBUG:
                    print("Error fetching online version or loading local version information. Proceeding with execution.")

        else:
            if UPDATE_CHECK_DEBUG:
                print(f"Check already performed within the last week. \n"
                      f"Latest version from local info: {local_latest_version}, while tool version is: {TOOL_VERSION = }")


def main_tool_update_check():
    try:
        update_needed = False
        # Create a separate thread for the update check
        update_thread = threading.Thread(target=update_check_thread)

        # Start the update check thread in the background
        update_thread.start()

        # check from local json if update is needed and display appropriate warning
        last_check_timestamp, local_latest_version = load_last_check_info()
        if UPDATE_CHECK_DEBUG:
            print(f"{local_latest_version = }")
        if local_latest_version is not None:
            if version_str_to_tuple(local_latest_version) > version_str_to_tuple(TOOL_VERSION):
                if UPDATE_CHECK_DEBUG:
                    print(f"New version available: {local_latest_version}, while tool version is: {TOOL_VERSION = }")
                update_needed = True
            else:
                if UPDATE_CHECK_DEBUG:
                    print(f"You have already the latest version, i.e., {local_latest_version}. No need to update")
        # Wait for the update check thread to finish before exiting the main thread
        update_thread.join()
        return local_latest_version, update_needed
    except:  # if for any reason update is failing... do NOT terminate the whole program!
        pass


if __name__ == "__main__":
    print('hello')

    update_version = main_tool_update_check()
    time.sleep(3)
    print('sleep over...')

    print('ending...')
