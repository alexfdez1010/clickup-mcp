# API coverage

Official API snapshot: **2026-10-06**.

The bundled catalog exposes **172 operations**: **137 v2** and **35 v3**.

Sources:

- [ClickUp API v2 OpenAPI](https://developer.clickup.com/openapi/clickup-api-v2-reference.json)
- [ClickUp API v3 OpenAPI](https://developer.clickup.com/openapi/ClickUp_PUBLIC_API_V3.yaml)

The only excluded operation is `GetAccessToken` (`POST /api/v2/oauth/token`). This server uses an existing personal API token from `CLICKUP_API_KEY`; it does not perform OAuth exchanges.

Coverage means every HTTP operation present in these snapshots is callable. ClickUp plan requirements, permissions, endpoint availability, and account limits still apply. Response schemas are not bundled; API responses are returned as received. Undocumented endpoints and features absent from these public specifications are not claimed as supported.

## Metadata corrections and limitations

- Local `$ref` inputs are expanded. Reference siblings and descriptions are retained. Recursive schema positions, if present in future specifications, are left unconstrained and marked with `x-clickup-recursive-reference` so recursion terminates without unresolved references.
- An input schema declaring `properties` without `type` is normalized to `type: object`.
- The v2 `CreateTaskAttachment` schema describes `attachment` as an array with empty item metadata. Items are normalized to binary strings, matching the [official attachment guide](https://developer.clickup.com/docs/attachments). Multipart parts use `attachment[0]`, `attachment[1]`, and so on.
- The v3 `postEntityAttachment` schema declares only an optional `filename`; it does not document the binary file part or its name. This catalog preserves that limitation. The multipart transport accepts explicitly named file parts; consult ClickUp for v3 file field requirements.
- `GetTasks` array filters `statuses`, `assignees`, `tags`, and `custom_items` use bracketed keys despite unbracketed OpenAPI names, following [the endpoint examples](https://developer.clickup.com/reference/gettasks). The same convention is applied to `watchers`, whose reference lists an array without a wire example. These parameters carry `x-clickup-serialization: bracket-array`.
- `custom_fields` for `GetTasks`, `GetFilteredTeamTasks`, and `GetTask` is corrected from an array of strings to an array of filter objects and carries `x-clickup-serialization: json`. This follows the [Custom Field filter guide](https://developer.clickup.com/docs/taskfilters) and the endpoint examples, which require a stringified JSON array containing `field_id`, `operator`, and `value`. The singular `custom_field` input retains its source schema.
- Parameter names, including bracketed array names, serialization settings, required flags, and deprecation flags are retained from the source. Operation parameters override matching path-level parameters.
- Reference links use lowercased operation IDs with apostrophes removed, matching the [official documentation index](https://developer.clickup.com/llms.txt) at snapshot time.

## Regenerate

```sh
uv sync --group dev
uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD
```

For a reproducible offline rebuild, retain both source snapshots and pass their paths:

```sh
uv run python scripts/update_catalog.py --v2 clickup-api-v2-reference.json \
  --v3 ClickUp_PUBLIC_API_V3.yaml --snapshot-date YYYY-MM-DD
```

The generator validates duplicate operation IDs, duplicate method/path pairs, unresolved references, and missing path parameters before writing either artifact.

## Operations

| Operation ID | Method | Path | API reference |
| --- | --- | --- | --- |
| `v2_AddDependency` | POST | `/api/v2/task/{task_id}/dependency` | [Add Dependency](https://developer.clickup.com/reference/adddependency) |
| `v2_AddGuestToFolder` | POST | `/api/v2/folder/{folder_id}/guest/{guest_id}` | [Add Guest To Folder](https://developer.clickup.com/reference/addguesttofolder) |
| `v2_AddGuestToList` | POST | `/api/v2/list/{list_id}/guest/{guest_id}` | [Add Guest To List](https://developer.clickup.com/reference/addguesttolist) |
| `v2_AddGuestToTask` | POST | `/api/v2/task/{task_id}/guest/{guest_id}` | [Add Guest To Task](https://developer.clickup.com/reference/addguesttotask) |
| `v2_AddTagToTask` | POST | `/api/v2/task/{task_id}/tag/{tag_name}` | [Add Tag To Task](https://developer.clickup.com/reference/addtagtotask) |
| `v2_AddTaskLink` | POST | `/api/v2/task/{task_id}/link/{links_to}` | [Add Task Link](https://developer.clickup.com/reference/addtasklink) |
| `v2_AddTaskToList` | POST | `/api/v2/list/{list_id}/task/{task_id}` | [Add Task To List](https://developer.clickup.com/reference/addtasktolist) |
| `v2_Addtagsfromtimeentries` | POST | `/api/v2/team/{team_id}/time_entries/tags` | [Add tags from time entries](https://developer.clickup.com/reference/addtagsfromtimeentries) |
| `v2_Changetagnamesfromtimeentries` | PUT | `/api/v2/team/{team_id}/time_entries/tags` | [Change tag names from time entries](https://developer.clickup.com/reference/changetagnamesfromtimeentries) |
| `v2_CreateChatViewComment` | POST | `/api/v2/view/{view_id}/comment` | [Create Chat View Comment](https://developer.clickup.com/reference/createchatviewcomment) |
| `v2_CreateChecklist` | POST | `/api/v2/task/{task_id}/checklist` | [Create Checklist](https://developer.clickup.com/reference/createchecklist) |
| `v2_CreateChecklistItem` | POST | `/api/v2/checklist/{checklist_id}/checklist_item` | [Create Checklist Item](https://developer.clickup.com/reference/createchecklistitem) |
| `v2_CreateFolder` | POST | `/api/v2/space/{space_id}/folder` | [Create Folder](https://developer.clickup.com/reference/createfolder) |
| `v2_CreateFolderFromTemplate` | POST | `/api/v2/space/{space_id}/folder_template/{template_id}` | [Create Folder from template](https://developer.clickup.com/reference/createfolderfromtemplate) |
| `v2_CreateFolderListFromTemplate` | POST | `/api/v2/folder/{folder_id}/list_template/{template_id}` | [Create List From Template in Folder](https://developer.clickup.com/reference/createfolderlistfromtemplate) |
| `v2_CreateFolderView` | POST | `/api/v2/folder/{folder_id}/view` | [Create Folder View](https://developer.clickup.com/reference/createfolderview) |
| `v2_CreateFolderlessList` | POST | `/api/v2/space/{space_id}/list` | [Create Folderless List](https://developer.clickup.com/reference/createfolderlesslist) |
| `v2_CreateGoal` | POST | `/api/v2/team/{team_id}/goal` | [Create Goal](https://developer.clickup.com/reference/creategoal) |
| `v2_CreateKeyResult` | POST | `/api/v2/goal/{goal_id}/key_result` | [Create Key Result](https://developer.clickup.com/reference/createkeyresult) |
| `v2_CreateList` | POST | `/api/v2/folder/{folder_id}/list` | [Create List](https://developer.clickup.com/reference/createlist) |
| `v2_CreateListComment` | POST | `/api/v2/list/{list_id}/comment` | [Create List Comment](https://developer.clickup.com/reference/createlistcomment) |
| `v2_CreateListView` | POST | `/api/v2/list/{list_id}/view` | [Create List View](https://developer.clickup.com/reference/createlistview) |
| `v2_CreateSpace` | POST | `/api/v2/team/{team_id}/space` | [Create Space](https://developer.clickup.com/reference/createspace) |
| `v2_CreateSpaceListFromTemplate` | POST | `/api/v2/space/{space_id}/list_template/{template_id}` | [Create List From Template in Space](https://developer.clickup.com/reference/createspacelistfromtemplate) |
| `v2_CreateSpaceTag` | POST | `/api/v2/space/{space_id}/tag` | [Create Space Tag](https://developer.clickup.com/reference/createspacetag) |
| `v2_CreateSpaceView` | POST | `/api/v2/space/{space_id}/view` | [Create Space View](https://developer.clickup.com/reference/createspaceview) |
| `v2_CreateTask` | POST | `/api/v2/list/{list_id}/task` | [Create Task](https://developer.clickup.com/reference/createtask) |
| `v2_CreateTaskAttachment` | POST | `/api/v2/task/{task_id}/attachment` | [Create Task Attachment](https://developer.clickup.com/reference/createtaskattachment) |
| `v2_CreateTaskComment` | POST | `/api/v2/task/{task_id}/comment` | [Create Task Comment](https://developer.clickup.com/reference/createtaskcomment) |
| `v2_CreateTaskFromTemplate` | POST | `/api/v2/list/{list_id}/taskTemplate/{template_id}` | [Create Task From Template](https://developer.clickup.com/reference/createtaskfromtemplate) |
| `v2_CreateTeamView` | POST | `/api/v2/team/{team_id}/view` | [Create Workspace (Everything level) View](https://developer.clickup.com/reference/createteamview) |
| `v2_CreateThreadedComment` | POST | `/api/v2/comment/{comment_id}/reply` | [Create Threaded Comment](https://developer.clickup.com/reference/createthreadedcomment) |
| `v2_CreateUserGroup` | POST | `/api/v2/team/{team_id}/group` | [Create Group](https://developer.clickup.com/reference/createusergroup) |
| `v2_CreateWebhook` | POST | `/api/v2/team/{team_id}/webhook` | [Create Webhook](https://developer.clickup.com/reference/createwebhook) |
| `v2_Createatimeentry` | POST | `/api/v2/team/{team_Id}/time_entries` | [Create a time entry](https://developer.clickup.com/reference/createatimeentry) |
| `v2_DeleteChecklist` | DELETE | `/api/v2/checklist/{checklist_id}` | [Delete Checklist](https://developer.clickup.com/reference/deletechecklist) |
| `v2_DeleteChecklistItem` | DELETE | `/api/v2/checklist/{checklist_id}/checklist_item/{checklist_item_id}` | [Delete Checklist Item](https://developer.clickup.com/reference/deletechecklistitem) |
| `v2_DeleteComment` | DELETE | `/api/v2/comment/{comment_id}` | [Delete Comment](https://developer.clickup.com/reference/deletecomment) |
| `v2_DeleteDependency` | DELETE | `/api/v2/task/{task_id}/dependency` | [Delete Dependency](https://developer.clickup.com/reference/deletedependency) |
| `v2_DeleteFolder` | DELETE | `/api/v2/folder/{folder_id}` | [Delete Folder](https://developer.clickup.com/reference/deletefolder) |
| `v2_DeleteGoal` | DELETE | `/api/v2/goal/{goal_id}` | [Delete Goal](https://developer.clickup.com/reference/deletegoal) |
| `v2_DeleteKeyResult` | DELETE | `/api/v2/key_result/{key_result_id}` | [Delete Key Result](https://developer.clickup.com/reference/deletekeyresult) |
| `v2_DeleteList` | DELETE | `/api/v2/list/{list_id}` | [Delete List](https://developer.clickup.com/reference/deletelist) |
| `v2_DeleteSpace` | DELETE | `/api/v2/space/{space_id}` | [Delete Space](https://developer.clickup.com/reference/deletespace) |
| `v2_DeleteSpaceTag` | DELETE | `/api/v2/space/{space_id}/tag/{tag_name}` | [Delete Space Tag](https://developer.clickup.com/reference/deletespacetag) |
| `v2_DeleteTask` | DELETE | `/api/v2/task/{task_id}` | [Delete Task](https://developer.clickup.com/reference/deletetask) |
| `v2_DeleteTaskLink` | DELETE | `/api/v2/task/{task_id}/link/{links_to}` | [Delete Task Link](https://developer.clickup.com/reference/deletetasklink) |
| `v2_DeleteTeam` | DELETE | `/api/v2/group/{group_id}` | [Delete Group](https://developer.clickup.com/reference/deleteteam) |
| `v2_DeleteView` | DELETE | `/api/v2/view/{view_id}` | [Delete View](https://developer.clickup.com/reference/deleteview) |
| `v2_DeleteWebhook` | DELETE | `/api/v2/webhook/{webhook_id}` | [Delete Webhook](https://developer.clickup.com/reference/deletewebhook) |
| `v2_DeleteatimeEntry` | DELETE | `/api/v2/team/{team_id}/time_entries/{timer_id}` | [Delete a time Entry](https://developer.clickup.com/reference/deleteatimeentry) |
| `v2_Deletetimetracked` | DELETE | `/api/v2/task/{task_id}/time/{interval_id}` | [Delete time tracked](https://developer.clickup.com/reference/deletetimetracked) |
| `v2_EditChecklist` | PUT | `/api/v2/checklist/{checklist_id}` | [Edit Checklist](https://developer.clickup.com/reference/editchecklist) |
| `v2_EditChecklistItem` | PUT | `/api/v2/checklist/{checklist_id}/checklist_item/{checklist_item_id}` | [Edit Checklist Item](https://developer.clickup.com/reference/editchecklistitem) |
| `v2_EditGuestOnWorkspace` | PUT | `/api/v2/team/{team_id}/guest/{guest_id}` | [Edit Guest On Workspace](https://developer.clickup.com/reference/editguestonworkspace) |
| `v2_EditKeyResult` | PUT | `/api/v2/key_result/{key_result_id}` | [Edit Key Result](https://developer.clickup.com/reference/editkeyresult) |
| `v2_EditSpaceTag` | PUT | `/api/v2/space/{space_id}/tag/{tag_name}` | [Edit Space Tag](https://developer.clickup.com/reference/editspacetag) |
| `v2_EditUserOnWorkspace` | PUT | `/api/v2/team/{team_id}/user/{user_id}` | [Edit User On Workspace](https://developer.clickup.com/reference/edituseronworkspace) |
| `v2_Edittimetracked` | PUT | `/api/v2/task/{task_id}/time/{interval_id}` | [Edit time tracked](https://developer.clickup.com/reference/edittimetracked) |
| `v2_GetAccessibleCustomFields` | GET | `/api/v2/list/{list_id}/field` | [Get List Custom Fields](https://developer.clickup.com/reference/getaccessiblecustomfields) |
| `v2_GetAuthorizedTeams` | GET | `/api/v2/team` | [Get Authorized Workspaces](https://developer.clickup.com/reference/getauthorizedteams) |
| `v2_GetAuthorizedUser` | GET | `/api/v2/user` | [Get Authorized User](https://developer.clickup.com/reference/getauthorizeduser) |
| `v2_GetBulkTasks'TimeinStatus` | GET | `/api/v2/task/bulk_time_in_status/task_ids` | [Get Bulk Tasks' Time in Status](https://developer.clickup.com/reference/getbulktaskstimeinstatus) |
| `v2_GetChatViewComments` | GET | `/api/v2/view/{view_id}/comment` | [Get Chat View Comments](https://developer.clickup.com/reference/getchatviewcomments) |
| `v2_GetCustomItems` | GET | `/api/v2/team/{team_id}/custom_item` | [Get Custom Task Types](https://developer.clickup.com/reference/getcustomitems) |
| `v2_GetCustomRoles` | GET | `/api/v2/team/{team_id}/customroles` | [Get Custom Roles](https://developer.clickup.com/reference/getcustomroles) |
| `v2_GetFilteredTeamTasks` | GET | `/api/v2/team/{team_Id}/task` | [Get Filtered Team Tasks](https://developer.clickup.com/reference/getfilteredteamtasks) |
| `v2_GetFolder` | GET | `/api/v2/folder/{folder_id}` | [Get Folder](https://developer.clickup.com/reference/getfolder) |
| `v2_GetFolderTemplates` | GET | `/api/v2/team/{team_id}/folder_template` | [Get Folder Templates](https://developer.clickup.com/reference/getfoldertemplates) |
| `v2_GetFolderViews` | GET | `/api/v2/folder/{folder_id}/view` | [Get Folder Views](https://developer.clickup.com/reference/getfolderviews) |
| `v2_GetFolderlessLists` | GET | `/api/v2/space/{space_id}/list` | [Get Folderless Lists](https://developer.clickup.com/reference/getfolderlesslists) |
| `v2_GetFolders` | GET | `/api/v2/space/{space_id}/folder` | [Get Folders](https://developer.clickup.com/reference/getfolders) |
| `v2_GetGoal` | GET | `/api/v2/goal/{goal_id}` | [Get Goal](https://developer.clickup.com/reference/getgoal) |
| `v2_GetGoals` | GET | `/api/v2/team/{team_id}/goal` | [Get Goals](https://developer.clickup.com/reference/getgoals) |
| `v2_GetGuest` | GET | `/api/v2/team/{team_id}/guest/{guest_id}` | [Get Guest](https://developer.clickup.com/reference/getguest) |
| `v2_GetList` | GET | `/api/v2/list/{list_id}` | [Get List](https://developer.clickup.com/reference/getlist) |
| `v2_GetListComments` | GET | `/api/v2/list/{list_id}/comment` | [Get List Comments](https://developer.clickup.com/reference/getlistcomments) |
| `v2_GetListMembers` | GET | `/api/v2/list/{list_id}/member` | [Get List Members](https://developer.clickup.com/reference/getlistmembers) |
| `v2_GetListTemplates` | GET | `/api/v2/team/{team_id}/list_template` | [Get List Templates](https://developer.clickup.com/reference/getlisttemplates) |
| `v2_GetListViews` | GET | `/api/v2/list/{list_id}/view` | [Get List Views](https://developer.clickup.com/reference/getlistviews) |
| `v2_GetLists` | GET | `/api/v2/folder/{folder_id}/list` | [Get Lists](https://developer.clickup.com/reference/getlists) |
| `v2_GetSpace` | GET | `/api/v2/space/{space_id}` | [Get Space](https://developer.clickup.com/reference/getspace) |
| `v2_GetSpaceTags` | GET | `/api/v2/space/{space_id}/tag` | [Get Space Tags](https://developer.clickup.com/reference/getspacetags) |
| `v2_GetSpaceViews` | GET | `/api/v2/space/{space_id}/view` | [Get Space Views](https://developer.clickup.com/reference/getspaceviews) |
| `v2_GetSpaces` | GET | `/api/v2/team/{team_id}/space` | [Get Spaces](https://developer.clickup.com/reference/getspaces) |
| `v2_GetTask` | GET | `/api/v2/task/{task_id}` | [Get Task](https://developer.clickup.com/reference/gettask) |
| `v2_GetTask'sTimeinStatus` | GET | `/api/v2/task/{task_id}/time_in_status` | [Get Task's Time in Status](https://developer.clickup.com/reference/gettaskstimeinstatus) |
| `v2_GetTaskComments` | GET | `/api/v2/task/{task_id}/comment` | [Get Task Comments](https://developer.clickup.com/reference/gettaskcomments) |
| `v2_GetTaskMembers` | GET | `/api/v2/task/{task_id}/member` | [Get Task Members](https://developer.clickup.com/reference/gettaskmembers) |
| `v2_GetTaskTemplates` | GET | `/api/v2/team/{team_id}/taskTemplate` | [Get Task Templates](https://developer.clickup.com/reference/gettasktemplates) |
| `v2_GetTasks` | GET | `/api/v2/list/{list_id}/task` | [Get Tasks](https://developer.clickup.com/reference/gettasks) |
| `v2_GetTeamViews` | GET | `/api/v2/team/{team_id}/view` | [Get Workspace (Everything level) Views](https://developer.clickup.com/reference/getteamviews) |
| `v2_GetTeams1` | GET | `/api/v2/group` | [Get Groups](https://developer.clickup.com/reference/getteams1) |
| `v2_GetThreadedComments` | GET | `/api/v2/comment/{comment_id}/reply` | [Get Threaded Comments](https://developer.clickup.com/reference/getthreadedcomments) |
| `v2_GetUser` | GET | `/api/v2/team/{team_id}/user/{user_id}` | [Get User](https://developer.clickup.com/reference/getuser) |
| `v2_GetView` | GET | `/api/v2/view/{view_id}` | [Get View](https://developer.clickup.com/reference/getview) |
| `v2_GetViewTasks` | GET | `/api/v2/view/{view_id}/task` | [Get View Tasks](https://developer.clickup.com/reference/getviewtasks) |
| `v2_GetWebhooks` | GET | `/api/v2/team/{team_id}/webhook` | [Get Webhooks](https://developer.clickup.com/reference/getwebhooks) |
| `v2_GetWorkspaceplan` | GET | `/api/v2/team/{team_id}/plan` | [Get Workspace Plan](https://developer.clickup.com/reference/getworkspaceplan) |
| `v2_GetWorkspaceseats` | GET | `/api/v2/team/{team_id}/seats` | [Get Workspace seats](https://developer.clickup.com/reference/getworkspaceseats) |
| `v2_Getalltagsfromtimeentries` | GET | `/api/v2/team/{team_id}/time_entries/tags` | [Get all tags from time entries](https://developer.clickup.com/reference/getalltagsfromtimeentries) |
| `v2_Getrunningtimeentry` | GET | `/api/v2/team/{team_id}/time_entries/current` | [Get running time entry](https://developer.clickup.com/reference/getrunningtimeentry) |
| `v2_Getsingulartimeentry` | GET | `/api/v2/team/{team_id}/time_entries/{timer_id}` | [Get singular time entry](https://developer.clickup.com/reference/getsingulartimeentry) |
| `v2_Gettimeentrieswithinadaterange` | GET | `/api/v2/team/{team_Id}/time_entries` | [Get time entries within a date range](https://developer.clickup.com/reference/gettimeentrieswithinadaterange) |
| `v2_Gettimeentryhistory` | GET | `/api/v2/team/{team_id}/time_entries/{timer_id}/history` | [Get time entry history](https://developer.clickup.com/reference/gettimeentryhistory) |
| `v2_Gettrackedtime` | GET | `/api/v2/task/{task_id}/time` | [Get tracked time](https://developer.clickup.com/reference/gettrackedtime) |
| `v2_InviteGuestToWorkspace` | POST | `/api/v2/team/{team_id}/guest` | [Invite Guest To Workspace](https://developer.clickup.com/reference/inviteguesttoworkspace) |
| `v2_InviteUserToWorkspace` | POST | `/api/v2/team/{team_id}/user` | [Invite User To Workspace](https://developer.clickup.com/reference/inviteusertoworkspace) |
| `v2_MoveFolder` | PUT | `/api/v2/folder/{folder_id}/position` | [Move Folder](https://developer.clickup.com/reference/movefolder) |
| `v2_RemoveCustomFieldValue` | DELETE | `/api/v2/task/{task_id}/field/{field_id}` | [Remove Custom Field Value](https://developer.clickup.com/reference/removecustomfieldvalue) |
| `v2_RemoveGuestFromFolder` | DELETE | `/api/v2/folder/{folder_id}/guest/{guest_id}` | [Remove Guest From Folder](https://developer.clickup.com/reference/removeguestfromfolder) |
| `v2_RemoveGuestFromList` | DELETE | `/api/v2/list/{list_id}/guest/{guest_id}` | [Remove Guest From List](https://developer.clickup.com/reference/removeguestfromlist) |
| `v2_RemoveGuestFromTask` | DELETE | `/api/v2/task/{task_id}/guest/{guest_id}` | [Remove Guest From Task](https://developer.clickup.com/reference/removeguestfromtask) |
| `v2_RemoveGuestFromWorkspace` | DELETE | `/api/v2/team/{team_id}/guest/{guest_id}` | [Remove Guest From Workspace](https://developer.clickup.com/reference/removeguestfromworkspace) |
| `v2_RemoveTagFromTask` | DELETE | `/api/v2/task/{task_id}/tag/{tag_name}` | [Remove Tag From Task](https://developer.clickup.com/reference/removetagfromtask) |
| `v2_RemoveTaskFromList` | DELETE | `/api/v2/list/{list_id}/task/{task_id}` | [Remove Task From List](https://developer.clickup.com/reference/removetaskfromlist) |
| `v2_RemoveUserFromWorkspace` | DELETE | `/api/v2/team/{team_id}/user/{user_id}` | [Remove User From Workspace](https://developer.clickup.com/reference/removeuserfromworkspace) |
| `v2_Removetagsfromtimeentries` | DELETE | `/api/v2/team/{team_id}/time_entries/tags` | [Remove tags from time entries](https://developer.clickup.com/reference/removetagsfromtimeentries) |
| `v2_SetCustomFieldValue` | POST | `/api/v2/task/{task_id}/field/{field_id}` | [Set Custom Field Value](https://developer.clickup.com/reference/setcustomfieldvalue) |
| `v2_SharedHierarchy` | GET | `/api/v2/team/{team_id}/shared` | [Shared Hierarchy](https://developer.clickup.com/reference/sharedhierarchy) |
| `v2_StartatimeEntry` | POST | `/api/v2/team/{team_Id}/time_entries/start` | [Start a time Entry](https://developer.clickup.com/reference/startatimeentry) |
| `v2_StopatimeEntry` | POST | `/api/v2/team/{team_id}/time_entries/stop` | [Stop a time Entry](https://developer.clickup.com/reference/stopatimeentry) |
| `v2_Tracktime` | POST | `/api/v2/task/{task_id}/time` | [Track time](https://developer.clickup.com/reference/tracktime) |
| `v2_UpdateComment` | PUT | `/api/v2/comment/{comment_id}` | [Update Comment](https://developer.clickup.com/reference/updatecomment) |
| `v2_UpdateFolder` | PUT | `/api/v2/folder/{folder_id}` | [Update Folder](https://developer.clickup.com/reference/updatefolder) |
| `v2_UpdateGoal` | PUT | `/api/v2/goal/{goal_id}` | [Update Goal](https://developer.clickup.com/reference/updategoal) |
| `v2_UpdateList` | PUT | `/api/v2/list/{list_id}` | [Update List](https://developer.clickup.com/reference/updatelist) |
| `v2_UpdateSpace` | PUT | `/api/v2/space/{space_id}` | [Update Space](https://developer.clickup.com/reference/updatespace) |
| `v2_UpdateTask` | PUT | `/api/v2/task/{task_id}` | [Update Task](https://developer.clickup.com/reference/updatetask) |
| `v2_UpdateTeam` | PUT | `/api/v2/group/{group_id}` | [Update Group](https://developer.clickup.com/reference/updateteam) |
| `v2_UpdateView` | PUT | `/api/v2/view/{view_id}` | [Update View](https://developer.clickup.com/reference/updateview) |
| `v2_UpdateWebhook` | PUT | `/api/v2/webhook/{webhook_id}` | [Update Webhook](https://developer.clickup.com/reference/updatewebhook) |
| `v2_UpdateatimeEntry` | PUT | `/api/v2/team/{team_id}/time_entries/{timer_id}` | [Update a time Entry](https://developer.clickup.com/reference/updateatimeentry) |
| `v2_getFolderAvailableFields` | GET | `/api/v2/folder/{folder_id}/field` | [Get Folder Custom Fields](https://developer.clickup.com/reference/getfolderavailablefields) |
| `v2_getSpaceAvailableFields` | GET | `/api/v2/space/{space_id}/field` | [Get Space Custom Fields](https://developer.clickup.com/reference/getspaceavailablefields) |
| `v2_getTeamAvailableFields` | GET | `/api/v2/team/{team_id}/field` | [Get Workspace Custom Fields](https://developer.clickup.com/reference/getteamavailablefields) |
| `v2_mergeTasks` | POST | `/api/v2/task/{task_id}/merge` | [Merge Tasks](https://developer.clickup.com/reference/mergetasks) |
| `v3_createChatChannel` | POST | `/api/v3/workspaces/{workspace_id}/chat/channels` | [Create a Channel](https://developer.clickup.com/reference/createchatchannel) |
| `v3_createChatMessage` | POST | `/api/v3/workspaces/{workspace_id}/chat/channels/{channel_id}/messages` | [Send a message](https://developer.clickup.com/reference/createchatmessage) |
| `v3_createChatReaction` | POST | `/api/v3/workspaces/{workspace_id}/chat/messages/{message_id}/reactions` | [Create a message reaction](https://developer.clickup.com/reference/createchatreaction) |
| `v3_createDirectMessageChatChannel` | POST | `/api/v3/workspaces/{workspace_id}/chat/channels/direct_message` | [Create a Direct Message](https://developer.clickup.com/reference/createdirectmessagechatchannel) |
| `v3_createDocPublic` | POST | `/api/v3/workspaces/{workspace_id}/docs` | [Create a Doc](https://developer.clickup.com/reference/createdocpublic) |
| `v3_createLocationChatChannel` | POST | `/api/v3/workspaces/{workspace_id}/chat/channels/location` | [Create a Channel on a Space, Folder, or List](https://developer.clickup.com/reference/createlocationchatchannel) |
| `v3_createPagePublic` | POST | `/api/v3/workspaces/{workspace_id}/docs/{doc_id}/pages` | [Create a Page](https://developer.clickup.com/reference/createpagepublic) |
| `v3_createReplyMessage` | POST | `/api/v3/workspaces/{workspace_id}/chat/messages/{message_id}/replies` | [Create a reply message](https://developer.clickup.com/reference/createreplymessage) |
| `v3_deleteChatChannel` | DELETE | `/api/v3/workspaces/{workspace_id}/chat/channels/{channel_id}` | [Delete a Channel](https://developer.clickup.com/reference/deletechatchannel) |
| `v3_deleteChatMessage` | DELETE | `/api/v3/workspaces/{workspace_id}/chat/messages/{message_id}` | [Delete a message](https://developer.clickup.com/reference/deletechatmessage) |
| `v3_deleteChatReaction` | DELETE | `/api/v3/workspaces/{workspace_id}/chat/messages/{message_id}/reactions/{reaction}` | [Delete a message reaction](https://developer.clickup.com/reference/deletechatreaction) |
| `v3_editPagePublic` | PUT | `/api/v3/workspaces/{workspace_id}/docs/{doc_id}/pages/{page_id}` | [Edit a Page](https://developer.clickup.com/reference/editpagepublic) |
| `v3_getChatChannel` | GET | `/api/v3/workspaces/{workspace_id}/chat/channels/{channel_id}` | [Retrieve a Channel](https://developer.clickup.com/reference/getchatchannel) |
| `v3_getChatChannelFollowers` | GET | `/api/v3/workspaces/{workspace_id}/chat/channels/{channel_id}/followers` | [Retrieve Channel followers](https://developer.clickup.com/reference/getchatchannelfollowers) |
| `v3_getChatChannelMembers` | GET | `/api/v3/workspaces/{workspace_id}/chat/channels/{channel_id}/members` | [Retrieve Channel members](https://developer.clickup.com/reference/getchatchannelmembers) |
| `v3_getChatChannels` | GET | `/api/v3/workspaces/{workspace_id}/chat/channels` | [Retrieve Channels](https://developer.clickup.com/reference/getchatchannels) |
| `v3_getChatMessageReactions` | GET | `/api/v3/workspaces/{workspace_id}/chat/messages/{message_id}/reactions` | [Retrieve message reactions](https://developer.clickup.com/reference/getchatmessagereactions) |
| `v3_getChatMessageReplies` | GET | `/api/v3/workspaces/{workspace_id}/chat/messages/{message_id}/replies` | [Retrieve message replies](https://developer.clickup.com/reference/getchatmessagereplies) |
| `v3_getChatMessageTaggedUsers` | GET | `/api/v3/workspaces/{workspace_id}/chat/messages/{message_id}/tagged_users` | [Retrieve message tagged users](https://developer.clickup.com/reference/getchatmessagetaggedusers) |
| `v3_getChatMessages` | GET | `/api/v3/workspaces/{workspace_id}/chat/channels/{channel_id}/messages` | [Retrieve Channel messages](https://developer.clickup.com/reference/getchatmessages) |
| `v3_getDocPageListingPublic` | GET | `/api/v3/workspaces/{workspace_id}/docs/{doc_id}/page_listing` | [Fetch PageListing for a Doc](https://developer.clickup.com/reference/getdocpagelistingpublic) |
| `v3_getDocPagesPublic` | GET | `/api/v3/workspaces/{workspace_id}/docs/{doc_id}/pages` | [Fetch Pages belonging to a Doc](https://developer.clickup.com/reference/getdocpagespublic) |
| `v3_getDocPublic` | GET | `/api/v3/workspaces/{workspace_id}/docs/{doc_id}` | [Fetch a Doc](https://developer.clickup.com/reference/getdocpublic) |
| `v3_getPagePublic` | GET | `/api/v3/workspaces/{workspace_id}/docs/{doc_id}/pages/{page_id}` | [Get page](https://developer.clickup.com/reference/getpagepublic) |
| `v3_getParentEntityAttachments` | GET | `/api/v3/workspaces/{workspace_id}/{entity_type}/{entity_id}/attachments` | [Get Attachments](https://developer.clickup.com/reference/getparententityattachments) |
| `v3_getSubtypes` | GET | `/api/v3/workspaces/{workspace_id}/comments/types/{comment_type}/subtypes` | [Get Post Subtype IDs](https://developer.clickup.com/reference/getsubtypes) |
| `v3_moveTask` | PUT | `/api/v3/workspaces/{workspace_id}/tasks/{task_id}/home_list/{list_id}` | [Move a task to a new List](https://developer.clickup.com/reference/movetask) |
| `v3_patchChatMessage` | PATCH | `/api/v3/workspaces/{workspace_id}/chat/messages/{message_id}` | [Update a message](https://developer.clickup.com/reference/patchchatmessage) |
| `v3_postEntityAttachment` | POST | `/api/v3/workspaces/{workspace_id}/{entity_type}/{entity_id}/attachments` | [Create an Attachment](https://developer.clickup.com/reference/postentityattachment) |
| `v3_publicPatchAcl` | PATCH | `/api/v3/workspaces/{workspace_id}/{object_type}/{object_id}/acls` | [Update privacy and access of an object or location](https://developer.clickup.com/reference/publicpatchacl) |
| `v3_queryAuditLog` | POST | `/api/v3/workspaces/{workspace_id}/auditlogs` | [Create Workspace-level audit logs](https://developer.clickup.com/reference/queryauditlog) |
| `v3_replaceTimeEstimatesByUser` | PUT | `/api/v3/workspaces/{workspace_id}/tasks/{task_id}/time_estimates_by_user` | [Replace task time estimates](https://developer.clickup.com/reference/replacetimeestimatesbyuser) |
| `v3_searchDocsPublic` | GET | `/api/v3/workspaces/{workspace_id}/docs` | [Search for Docs](https://developer.clickup.com/reference/searchdocspublic) |
| `v3_updateChatChannel` | PATCH | `/api/v3/workspaces/{workspace_id}/chat/channels/{channel_id}` | [Update a Channel](https://developer.clickup.com/reference/updatechatchannel) |
| `v3_updateTimeEstimatesByUser` | PATCH | `/api/v3/workspaces/{workspace_id}/tasks/{task_id}/time_estimates_by_user` | [Update task time estimates by user](https://developer.clickup.com/reference/updatetimeestimatesbyuser) |
