# tools_update_check
Public repo for check in various tools if update to latest version is needed

```json
{
  "test": {
    "latest_version": "1.7.2",
    "last_update_date": "20.12.2022",
    "repo_url": "https://test.com",
    "note": "extra note/comment that might be need to be communicated as well"
  }
}
```

#### Note: Below TODO parts needs to be updated in the actual project accordingly:
1. Add `update_last_check.json` to .gitignore file!!!
2. Add relevant imports
3. `UPDATE_CHECK_DEBUG = True  # todo: change to False for production`
4. `delay_check_in_seconds = 10  # for test purposes  # todo: comment this`
5. Thread usage is needed in __main__ to avoid freezing the main program (`threading.Thread(target=upd_chk_main_tool_update_check`)
6. `upd_main_thread = threading.Thread(target=upd_chk_main_tool_update_check, args=('test', local_tool_version, 15))` 
   - todo: change to correct project
   - todo: change days from 15 to appropriate frequency that update check is needed 
7. todo: add `thread.join` at the end of main
8. `UPDATE_CHECK_NEEDED = True`: Set to `True` if you need periodic checks for tool-updates, or `False` if you don't need the update-check