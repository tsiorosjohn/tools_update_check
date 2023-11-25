import os
import json
import time
import threading
import re
from urllib import request, error
from datetime import datetime
from typing import Union


def upd_chk_main_tool_update_check(project_name, local_tool_version_f, online_check_frequency: Union[int, str] = 30, print_update_warning=True):
    """
    Check if update to latest version is needed for appropriate tool.
    One function with sub-functions for easy porting to different projects
    Args:
        project_name: online JSON is a dict of all projects. Choose which is the one of interest
        local_tool_version_f: actual local tool version; could be outdated
        online_check_frequency: how often online JSON of latest versions have to be checked ('always', or <int>: days)
        print_update_warning: False if no print warning is necessary (e.g. need to handle proprietary the warning, or 'use-case' of calling with '-v' args cli)

    Returns:
        update_needed: bool
        temp_json_latest_version: latest version of tool (as depicted in temp JSON file; if online has not been performed might not be the actual updated one)
        last_update_date: last date that updated version was released
        repo_url: download URL of latest tool
    """
    UPDATE_CHECK_NEEDED = True  # Set to 'True' if you need periodic checks for tool-updates, or 'False' if you need to disable the update-check
    UPDATE_CHECK_LAST_CHECK_FILE = "update_last_check.json"
    UPDATE_CHECK_URL = "https://raw.githubusercontent.com/tsiorosjohn/tools_update_check/master/latest_versions.json"
    UPDATE_CHECK_PROXY_ADDRESS = 'http://10.158.100.2:8080'
    UPDATE_CHECK_DEBUG = True  # todo: 3. change to False for production
    UPDATE_CHECK_TIMEOUT = 4  # Seconds to wait urlopen prior to timeout (not works for WSL2)

    # Lock for thread-safe access to shared resources
    update_check_lock = threading.Lock()

    def upd_chk_version_str_to_tuple(version_str):
        """
        Take string-version first 'semantic' part (major.minor.patch) and convert this to tuple in order to be able to compare this later
        Args:
            version_str: Version has to be in format, e.g.: '1.2.3' or '1.2.3_beta 23.01.1983'
        Returns:
            Semantic version part only converted in tuple
        """
        # Use regular expression to extract the version number
        version_match = re.match(r'^(\d+\.\d+\.\d+)', version_str)

        if version_match:
            version_number = version_match.group(1)
            return tuple(map(int, version_number.split('.')))
        else:
            if UPDATE_CHECK_DEBUG:
                print(f"Invalid version string: {version_str}")
            return None

    def upd_chk_check_online_version(project_name_f):
        """
        JSON format API:
              "test": {
                "latest_version": "1.7.2",
                "last_update_date": "20.12.2022",
                "repo_url": "https://test.com",
                "note": "extra note/comment that might be need to be communicated as well"
                }
        Args:
            project_name_f: 'key' of dictionary is the project name

        Returns:
            latest_version, last_update_date, repo_url, note ...or 4-None in case of error
        """
        try:  # try to read the online json
            try:  # attempt initially to connect without proxy
                response = request.urlopen(UPDATE_CHECK_URL, timeout=UPDATE_CHECK_TIMEOUT)
            except Exception as e_without_proxy:
                if UPDATE_CHECK_DEBUG:
                    print(f"{int(time.time())}: Error without proxy: {e_without_proxy}")
                # If the request without a proxy fails, try with a proxy
                try:
                    # Create a proxy handler
                    proxy_handler = request.ProxyHandler({'http': UPDATE_CHECK_PROXY_ADDRESS, 'https': UPDATE_CHECK_PROXY_ADDRESS})
                    # Create an opener with the proxy handler
                    opener = request.build_opener(proxy_handler)
                    # Install the opener
                    request.install_opener(opener)
                    # Open the URL with the proxy
                    response = request.urlopen(UPDATE_CHECK_URL, timeout=UPDATE_CHECK_TIMEOUT)
                    http_status_code = response.getcode()
                    if UPDATE_CHECK_DEBUG:
                        print(f"{int(time.time())}: WITH PROXY: {http_status_code = } // Got result with proxy!!!: {UPDATE_CHECK_PROXY_ADDRESS}")

                except Exception as e_with_proxy:
                    if UPDATE_CHECK_DEBUG:
                        print(f"{int(time.time())}: Error with proxy: {e_with_proxy}")
                    return None, None, None, None

            online_data = json.loads(response.read().decode('utf-8'))
            online_data_project = online_data[project_name_f]
            latest_version = online_data_project.get("latest_version", "")
            last_update_date = online_data_project.get("last_update_date", "")
            repo_url = online_data_project.get("repo_url", "")
            note_f = online_data_project.get("note", "")
            return latest_version, last_update_date, repo_url, note_f
        except (error.URLError, json.JSONDecodeError) as ex:
            if UPDATE_CHECK_DEBUG:
                print(f"Error checking online version: {ex}")
            return None, None, None, None

    def upd_chk_save_last_check_info(last_check_timestamp, last_check_timestamp_h, online_check_frequency_f, latest_version, last_update_date, repo_url,
                                     project_name_f, note_f):
        """
        Saves retrieved info in local json file
        """
        data_d = {"last_check_timestamp": last_check_timestamp, "last_check_timestamp_human_readable": last_check_timestamp_h,
                  "online_check_frequency_days": online_check_frequency_f, "latest_version_local": latest_version, "last_update_date": last_update_date,
                  "repo_url": repo_url, "project_name": project_name_f, "note": note_f}
        with open(UPDATE_CHECK_LAST_CHECK_FILE, 'w') as file:
            json.dump(data_d, file, indent=2)

    def upd_chk_load_last_check_info(create_if_missing=False):
        """
        Load local json file and get info. E.g. last timestamp
        Args:
            create_if_missing: Is needed as function is called from thread and in main function later, so in order to avoid re-creation of empty file twice!
        Returns:
            data dictionary: with info from local json file (this can be either actual data ...or empty json if it has just re-created)
        """
        data_f = {}
        if os.path.exists(UPDATE_CHECK_LAST_CHECK_FILE):
            with open(UPDATE_CHECK_LAST_CHECK_FILE, 'r') as file:
                try:
                    data_f = json.load(file)
                    return data_f
                except json.JSONDecodeError:
                    if UPDATE_CHECK_DEBUG:
                        print("Error decoding JSON in last_check.json. Creating a new one.")
        elif create_if_missing:
            if UPDATE_CHECK_DEBUG:
                print("last_check.json not found. Creating a new one.")
            # Create a new last_check.json file with default values
            default_timestamp = 0
            default_version = None
            data_f = {"last_check_timestamp": default_timestamp, "last_check_timestamp_human_readable": default_timestamp, "last_update_date": '',
                      "latest_version_local": default_version, "repo_url": '',
                      "project_name": '', "note": ''}
            with open(UPDATE_CHECK_LAST_CHECK_FILE, 'w') as file:
                json.dump(data_f, file, indent=2)

        return data_f

    def upd_chk_update_check_thread(project_name_f, local_tool_vers, online_check_frequency_f):
        """
        Start a thread and check online if latest_version exists.
        If yes, store this in local json. Tool will get the info from local_json in next tool run and compare this with tool version
        """
        if not UPDATE_CHECK_NEEDED:
            if UPDATE_CHECK_DEBUG:
                print(f"{UPDATE_CHECK_NEEDED = }. Exiting...")
            exit(0)

        with update_check_lock:
            data_d = upd_chk_load_last_check_info(create_if_missing=True)
            # last_check_timestamp, local_latest_version = data.get("last_check_timestamp", 0), data.get("latest_version_local")
            last_check_timestamp, local_latest_version = data_d.get("last_check_timestamp", 0), data_d.get("latest_version_local")
            current_timestamp = time.time()
            human_readable_timestamp = datetime.fromtimestamp(current_timestamp).strftime('%Y-%m-%d %H:%M:%S')

            if online_check_frequency_f == 'always':
                delay_check_in_seconds = 1
            else:
                # delay_check_in_seconds = int(online_check_frequency) * 24 * 60 * 60  # Approximate seconds for those number of days
                delay_check_in_seconds = 15  # for test purposes  # todo: 4. comment this. Set actual days of check frequency

            # check online if delay_check_in_seconds has been elapsed - else, try to compare from locally stored (previously retrieved) 'local_latest_version'
            if current_timestamp - last_check_timestamp >= delay_check_in_seconds:
                if UPDATE_CHECK_DEBUG:
                    print(f"{int(time.time())}:  {current_timestamp - last_check_timestamp = } ...checking online...")
                latest_version, last_update_date, repo_url, note_f = upd_chk_check_online_version(project_name_f)

                if latest_version is not None:
                    try:
                        if upd_chk_version_str_to_tuple(latest_version) > upd_chk_version_str_to_tuple(local_tool_vers):
                            if UPDATE_CHECK_DEBUG:
                                print(f"{'-' * 40} Checking online!!! {'-' * 40}")
                                print(f"New version available: {latest_version}")
                                print(f"last_update_date: {last_update_date}")
                                print(f"Repository URL: {repo_url}")
                                print(f"Project Name: {project_name_f}")
                                print(f"Note: {note_f}")
                                print(f"{'-' * 100}")
                            # Implement update mechanism here

                        else:
                            if UPDATE_CHECK_DEBUG:
                                print("You have the latest version. Proceeding with execution.")
                        # Save the new version and timestamp to the local JSON file
                        upd_chk_save_last_check_info(current_timestamp, human_readable_timestamp, online_check_frequency_f, latest_version, last_update_date,
                                                     repo_url, project_name_f, note_f)
                    except TypeError as ex:
                        if UPDATE_CHECK_DEBUG:
                            print(f"An exception occurred: {ex}")
                        else:
                            pass  # Do nothing when DEBUG is False
                            return False, None, None, None

                else:
                    if UPDATE_CHECK_DEBUG:
                        print("Error fetching online version or loading local version information. Proceeding with execution.")
                    # Error fetching online version or loading local version. Update current_timestamp in order to avoid constant checking which can cause delays
                    # if issue is relevant with & without proxy resolution:
                    upd_chk_save_last_check_info(current_timestamp, human_readable_timestamp, online_check_frequency_f, "0.0.0", "", "", project_name_f, "")

            else:
                if UPDATE_CHECK_DEBUG:
                    print(
                        f"Online check already performed at {human_readable_timestamp}, i.e. within the last {online_check_frequency} days. No need to re-check online!!!\n"
                        f"Latest version retrieved from local JSON temp file: '{local_latest_version}'")

    try:
        update_needed_f = False
        # Create a separate thread for the update check
        # update_thread = threading.Thread(target=upd_chk_update_check_thread, args=(project_name, local_tool_version_f, online_check_frequency))
        upd_chk_update_check_thread(project_name, local_tool_version_f, online_check_frequency)

        # Start the update check thread in the background
        # update_thread.start()

        # check from local json if update is needed and display appropriate warning
        data = upd_chk_load_last_check_info()
        last_update_date_f = data['last_update_date']
        temp_json_latest_version_f = data['latest_version_local']
        repo_url_f = data['repo_url']
        note = data['note']

        if temp_json_latest_version_f is not None:
            if upd_chk_version_str_to_tuple(temp_json_latest_version_f) > upd_chk_version_str_to_tuple(local_tool_version_f):
                if UPDATE_CHECK_DEBUG:
                    print(f"New version available: {temp_json_latest_version_f}, while tool version is: {local_tool_version_f = }")
                update_needed_f = True
            else:
                if UPDATE_CHECK_DEBUG:
                    if temp_json_latest_version_f == '0.0.0':  # hardcoded value in case it's not possible to fetch actual version from GitHub
                        print(f"\nVersion: {temp_json_latest_version_f}, found from local-json. \n"
                              f"Seems that there was not possible to fetch actual version from GitHub...so, check is abandoned...")
                    else:
                        print(f"You have already the latest version, found from local-json: {temp_json_latest_version_f}. No need to update")
        # Wait for the update check thread to finish before exiting the main thread
        # update_thread.join()

        if UPDATE_CHECK_DEBUG:
            print(f"\n{'=' * 100} \n{update_needed_f = } \n{temp_json_latest_version_f = } \n{last_update_date_f = } \n{repo_url_f = }\n{'=' * 100} ")

        if update_needed_f and print_update_warning:
            print(f"New version '{temp_json_latest_version_f} - {last_update_date_f}' of tool is available to be downloaded from '{repo_url_f}'.\n"
                  f"{note}")
        return update_needed_f, temp_json_latest_version_f, last_update_date_f, repo_url_f, note
    except Exception as e:
        if UPDATE_CHECK_DEBUG:
            print(f"An exception occurred: {e}")
            return False, None, None, None
        else:
            pass  # Do nothing when DEBUG is False
            return False, None, None, None, None


if __name__ == "__main__":
    local_tool_version = '1.6.0_beta 1.2143.2023'

    print('Starting main')
    time.sleep(1)

    # example call of function:
    # update_needed, temp_json_latest_version, last_update_date, repo_url = upd_chk_main_tool_update_check('tdt', local_tool_version, 1)

    # todo: 1. add update_last_check.json to .gitignore file!!!
    # todo: 2. add relevant imports to project

    # todo: 5. Thread usage is needed in __main__ to avoid freezing the main program
    # todo: 6. a) change 'test' to correct project
    # todo: 6. b) Set to e.g. 15 days or 1 month for WSL2 tools, as there may be delay issues or proxy which adds delay to WSL2!
    upd_main_thread = threading.Thread(target=upd_chk_main_tool_update_check, args=('test', local_tool_version, 15))
    upd_main_thread.start()

    time.sleep(2)
    print('Main program Done...')

    # todo: 7. add thread.join at the end of main:

    # todo: 8. It may be needed just after update-check thread (upd_main_thread.start()) and prior starting of main tool,
    # in order to give time for update-thread to print the check info prior of starting of the tool:
    time.sleep(0.05)

    upd_main_thread.join(timeout=5)

    ### alternative usage (e.g. in GUIs / tkinter), when there is NO need for multi-threading:
    # warn_text = ''
    # try:
    #     update_needed_f, temp_json_latest_version_f, last_update_date_f, repo_url_f, note = upd_chk_main_tool_update_check('tdt', VERSION_DATE, 1)
    #     if update_needed_f:
    #         warn_text = f"New version '{temp_json_latest_version_f} - {last_update_date_f}' of tool is available to be downloaded!\n {note}"
    # except Exception as e:
    #     pass
