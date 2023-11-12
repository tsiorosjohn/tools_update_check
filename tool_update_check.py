import os
import json
import time
import threading
import re
from urllib import request, error

LAST_CHECK_FILE = "last_check.json"
UPDATE_URL = "https://raw.githubusercontent.com/tsiorosjohn/tools_update_check/master/latest_versions.json"
UPDATE_CHECK_DEBUG = False

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


def check_online_version(project_name):
    try:
        response = request.urlopen(UPDATE_URL)
        online_data = json.loads(response.read().decode('utf-8'))
        online_data_project = online_data[project_name]
        latest_version = online_data_project.get("latest_version", "")
        last_update_date = online_data_project.get("last_update_date", "")
        repo_url = online_data_project.get("repo_url", "")
        if UPDATE_CHECK_DEBUG:
            print(f"...checking online... \n Found...{latest_version = } // {repo_url = } // {project_name = }")
        return latest_version, last_update_date, repo_url
    except (error.URLError, json.JSONDecodeError) as e:
        if UPDATE_CHECK_DEBUG:
            print(f"Error checking online version: {e}")
        return None, None, None


def check_online_version_test():
    """
    For testing purposes without need of GitHub
    """
    json_data = '''
    {
      "tdt": {
        "latest_version": "4.4.1",
        "last_update_date": "08.11.2023",
        "repo_url": "https://gitlabe2.ext.net.nokia.com/tsioros/TDT_simple"
      },
      "test_project": {
        "latest_version": "1.0.0",
        "last_update_date": "10.11.2023",
        "repo_url": "https://example.com/another_project"
      }
    }
    '''

    python_dict = json.loads(json_data)
    key = 'tdt'
    try:
        latest_version = python_dict[key].get("latest_version", "")
        last_update_date = python_dict[key].get("last_update_date", "")
        repo_url = python_dict[key].get("repo_url", "")
        project_name = key
        if UPDATE_CHECK_DEBUG:
            print(f"...checking online... \n Found...{latest_version = } // {repo_url = } // {project_name = }")
        return latest_version, last_update_date, repo_url
    except (error.URLError, json.JSONDecodeError) as e:
        if UPDATE_CHECK_DEBUG:
            print(f"Error checking online version: {e}")
        return None, None, None


def save_last_check_info(last_check_timestamp, latest_version, last_update_date, repo_url, project_name):
    data = {"last_check_timestamp": last_check_timestamp, "latest_version_local": latest_version, "last_update_date": last_update_date, "repo_url": repo_url,
            "project_name": project_name}
    with open(LAST_CHECK_FILE, 'w') as file:
        json.dump(data, file, indent=4)


def load_last_check_info(create_if_missing=False):
    data = {}
    if os.path.exists(LAST_CHECK_FILE):
        with open(LAST_CHECK_FILE, 'r') as file:
            try:
                data = json.load(file)
                return data
            except json.JSONDecodeError:
                if UPDATE_CHECK_DEBUG:
                    print("Error decoding JSON in last_check.json. Creating a new one.")
    elif create_if_missing:
        if UPDATE_CHECK_DEBUG:
            print("last_check.json not found. Creating a new one.")
        # Create a new last_check.json file with default values
        default_timestamp = 0
        default_version = None
        data = {"last_check_timestamp": default_timestamp, "last_update_date": '', "latest_version_local": default_version, "repo_url": '', "project_name": ''}
        with open(LAST_CHECK_FILE, 'w') as file:
            json.dump(data, file, indent=4)

    return data


def update_check_thread(project_name, local_tool_version_f):
    """
    Start a thread and check online if latest_version exists.
    If yes, store this in local json. Tool will get the info from local_json in next tool run and compare this with tool version
    """
    with lock:
        data = load_last_check_info(create_if_missing=True)
        # last_check_timestamp, local_latest_version = data.get("last_check_timestamp", 0), data.get("latest_version_local")
        last_check_timestamp, local_latest_version = data.get("last_check_timestamp", 0), data.get("latest_version_local")
        current_timestamp = time.time()
        # delay_check_in_seconds = 7 * 24 * 60 * 60  # Approximate seconds in a week
        delay_check_in_seconds = 15  # Approximate seconds in a week  # todo: comment / use a week delay

        # check online if delay_check_in_seconds has been elapsed - else, try to compare from locally stored (previously retrieved) 'local_latest_version'
        if current_timestamp - last_check_timestamp >= delay_check_in_seconds:
            latest_version, last_update_date, repo_url = check_online_version(project_name)

            if latest_version is not None:
                try:
                    if version_str_to_tuple(latest_version) > version_str_to_tuple(local_tool_version_f):
                        if UPDATE_CHECK_DEBUG:
                            print(f"{'-'*40} Checking online!!! {'-'*40}")
                            print(f"New version available: {latest_version}")
                            print(f"last_update_date: {last_update_date}")
                            print(f"Repository URL: {repo_url}")
                            print(f"Project Name: {project_name}")
                            print(f"{'-' * 100}")
                        # Implement update mechanism here

                    else:
                        if UPDATE_CHECK_DEBUG:
                            print("You have the latest version. Proceeding with execution.")
                    # Save the new version and timestamp to the local JSON file
                    save_last_check_info(current_timestamp, latest_version, last_update_date, repo_url, project_name)
                except TypeError as e:
                    if UPDATE_CHECK_DEBUG:
                        print(f"An exception occurred: {e}")
                    else:
                        pass  # Do nothing when DEBUG is False
                        return False, None, None, None

            else:
                if UPDATE_CHECK_DEBUG:
                    print("Error fetching online version or loading local version information. Proceeding with execution.")

        else:
            if UPDATE_CHECK_DEBUG:
                print(f"Check already performed within the last week. \n"
                      f"Latest version from local info: {local_latest_version}")


def main_tool_update_check(project_name, local_tool_version_f):
    try:
        update_needed = False
        # Create a separate thread for the update check
        update_thread = threading.Thread(target=update_check_thread, args=(project_name, local_tool_version_f))

        # Start the update check thread in the background
        update_thread.start()

        # check from local json if update is needed and display appropriate warning
        data = load_last_check_info()
        last_check_timestamp = data['last_check_timestamp']
        last_update_date = data['last_update_date']
        temp_json_latest_version = data['latest_version_local']
        repo_url = data['repo_url']

        if temp_json_latest_version is not None:
            if version_str_to_tuple(temp_json_latest_version) > version_str_to_tuple(local_tool_version_f):
                if UPDATE_CHECK_DEBUG:
                    print(f"New version available: {temp_json_latest_version}, while tool version is: {local_tool_version_f = }")
                update_needed = True
            else:
                if UPDATE_CHECK_DEBUG:
                    print(f"You have already the latest version, found from local-json: {temp_json_latest_version}. No need to update")
        # Wait for the update check thread to finish before exiting the main thread
        update_thread.join()

        if UPDATE_CHECK_DEBUG:
            print(f"\n{'='*100} \n{update_needed = } \n{temp_json_latest_version = } \n{last_update_date = } \n{repo_url = }\n{'='*100} ")
        return update_needed, temp_json_latest_version, last_update_date, repo_url
    except Exception as e:
        if UPDATE_CHECK_DEBUG:
            print(f"An exception occurred: {e}")
            return False, None, None, None
        else:
            pass  # Do nothing when DEBUG is False
            return False, None, None, None


if __name__ == "__main__":
    local_tool_version = '4.1.0_beta 1.2143.2023'

    print('Starting main')
    time.sleep(1)

    # example call of function:
    update_needed, temp_json_latest_version, last_update_date, repo_url = main_tool_update_check('tdt', local_tool_version)

    if update_needed:
        print(f"New version '{temp_json_latest_version} - {last_update_date}' of tool is available to be downloaded from '{repo_url}'.")

    time.sleep(2)

    print('Done...')
