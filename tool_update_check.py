import os
import json
import time
import threading
import re
from urllib import request, error

UPDATE_CHECK_LAST_CHECK_FILE = "update_last_check.json"
UPDATE_CHECK_URL = "https://raw.githubusercontent.com/tsiorosjohn/tools_update_check/master/latest_versions.json"
UPDATE_CHECK_DEBUG = True

# Lock for thread-safe access to shared resources
update_check_lock = threading.Lock()


def upd_chk_version_str_to_tuple(version_str):
    # Use regular expression to extract the version number
    version_match = re.match(r'^(\d+\.\d+\.\d+)', version_str)

    if version_match:
        version_number = version_match.group(1)
        return tuple(map(int, version_number.split('.')))
    else:
        if UPDATE_CHECK_DEBUG:
            print(f"Invalid version string: {version_str}")
        return None


def upd_chk_check_online_version(project_name):
    try:
        response = request.urlopen(UPDATE_CHECK_URL)
        online_data = json.loads(response.read().decode('utf-8'))
        online_data_project = online_data[project_name]
        latest_version = online_data_project.get("latest_version", "")
        last_update_date_f = online_data_project.get("last_update_date", "")
        repo_url_f = online_data_project.get("repo_url", "")
        return latest_version, last_update_date_f, repo_url_f
    except (error.URLError, json.JSONDecodeError) as e:
        if UPDATE_CHECK_DEBUG:
            print(f"Error checking online version: {e}")
        return None, None, None


def upd_chk_save_last_check_info(last_check_timestamp, latest_version, last_update_date_f, repo_url_f, project_name):
    data = {"last_check_timestamp": last_check_timestamp, "latest_version_local": latest_version, "last_update_date": last_update_date_f,
            "repo_url": repo_url_f,
            "project_name": project_name}
    with open(UPDATE_CHECK_LAST_CHECK_FILE, 'w') as file:
        json.dump(data, file, indent=4)


def upd_chk_load_last_check_info(create_if_missing=False):
    data = {}
    if os.path.exists(UPDATE_CHECK_LAST_CHECK_FILE):
        with open(UPDATE_CHECK_LAST_CHECK_FILE, 'r') as file:
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
        with open(UPDATE_CHECK_LAST_CHECK_FILE, 'w') as file:
            json.dump(data, file, indent=4)

    return data


def upd_chk_update_check_thread(project_name, local_tool_version_f, online_check_frequency):
    """
    Start a thread and check online if latest_version exists.
    If yes, store this in local json. Tool will get the info from local_json in next tool run and compare this with tool version
    """
    with update_check_lock:
        data = upd_chk_load_last_check_info(create_if_missing=True)
        # last_check_timestamp, local_latest_version = data.get("last_check_timestamp", 0), data.get("latest_version_local")
        last_check_timestamp, local_latest_version = data.get("last_check_timestamp", 0), data.get("latest_version_local")
        current_timestamp = time.time()
        if online_check_frequency == 'always':
            delay_check_in_seconds = 1
        else:
            # delay_check_in_seconds = int(online_check_frequency) * 24 * 60 * 60  # Approximate seconds for those number of days
            delay_check_in_seconds = 15  # for test purposes  # todo: comment this

        # check online if delay_check_in_seconds has been elapsed - else, try to compare from locally stored (previously retrieved) 'local_latest_version'
        if current_timestamp - last_check_timestamp >= delay_check_in_seconds:
            latest_version, last_update_date_f, repo_url_f = upd_chk_check_online_version(project_name)

            if latest_version is not None:
                try:
                    if upd_chk_version_str_to_tuple(latest_version) > upd_chk_version_str_to_tuple(local_tool_version_f):
                        if UPDATE_CHECK_DEBUG:
                            print(f"{'-' * 40} Checking online!!! {'-' * 40}")
                            print(f"New version available: {latest_version}")
                            print(f"last_update_date: {last_update_date_f}")
                            print(f"Repository URL: {repo_url_f}")
                            print(f"Project Name: {project_name}")
                            print(f"{'-' * 100}")
                        # Implement update mechanism here

                    else:
                        if UPDATE_CHECK_DEBUG:
                            print("You have the latest version. Proceeding with execution.")
                    # Save the new version and timestamp to the local JSON file
                    upd_chk_save_last_check_info(current_timestamp, latest_version, last_update_date_f, repo_url_f, project_name)
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
                print(f"Online check already performed within the last {online_check_frequency} days. No need to re-check online!!!\n"
                      f"Latest version retrieved from local JSON temp file: '{local_latest_version}'")


def upd_chk_main_tool_update_check(project_name, local_tool_version_f, online_check_frequency=7):
    """

    Args:
        project_name: online JSON is a dict of all projects. Choose which is the one of interest
        local_tool_version_f: actual local tool version; could be outdated
        online_check_frequency: how often online JSON of latest versions have to be checked ('always', or <int>: days)

    Returns:
        update_needed: bool
        temp_json_latest_version: latest version of tool (as depicted in temp JSON file; if online has not been performed might not be the actual updated one)
        last_update_date: last date that updated version was released
        repo_url: download URL of latest tool
    """
    try:
        update_needed_f = False
        # Create a separate thread for the update check
        update_thread = threading.Thread(target=upd_chk_update_check_thread, args=(project_name, local_tool_version_f, online_check_frequency))

        # Start the update check thread in the background
        update_thread.start()

        # check from local json if update is needed and display appropriate warning
        data = upd_chk_load_last_check_info()
        last_update_date_f = data['last_update_date']
        temp_json_latest_version_f = data['latest_version_local']
        repo_url_f = data['repo_url']

        if temp_json_latest_version_f is not None:
            if upd_chk_version_str_to_tuple(temp_json_latest_version_f) > upd_chk_version_str_to_tuple(local_tool_version_f):
                if UPDATE_CHECK_DEBUG:
                    print(f"New version available: {temp_json_latest_version_f}, while tool version is: {local_tool_version_f = }")
                update_needed_f = True
            else:
                if UPDATE_CHECK_DEBUG:
                    print(f"You have already the latest version, found from local-json: {temp_json_latest_version_f}. No need to update")
        # Wait for the update check thread to finish before exiting the main thread
        update_thread.join()

        if UPDATE_CHECK_DEBUG:
            print(f"\n{'=' * 100} \n{update_needed_f = } \n{temp_json_latest_version_f = } \n{last_update_date_f = } \n{repo_url_f = }\n{'=' * 100} ")
        return update_needed_f, temp_json_latest_version_f, last_update_date_f, repo_url_f
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
    update_needed, temp_json_latest_version, last_update_date, repo_url = upd_chk_main_tool_update_check('tdt', local_tool_version, 1)

    if update_needed:
        print(f"New version '{temp_json_latest_version} - {last_update_date}' of tool is available to be downloaded from '{repo_url}'.")

    time.sleep(2)

    print('Done...')
