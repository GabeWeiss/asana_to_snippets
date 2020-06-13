import asana
import datetime
import json
import os
import sys
import time

# Get the project ID from the URL in the Asana front-end and update here
# Right now, this only supports single project, but if there are folks
# that want it, I can update this to work across multiple projects
# Right now we're also not handling anything relating to assignee, but that
# might be another interesting thing to update
try:
    project_id = os.environ['ASANA_PROJECT_ID']
    access_token = os.environ['ASANA_TOKEN']
except:
    print("You need to set the environment variables for Asana: 'ASANA_TOKEN' and 'ASANA_PROJECT_ID'")

# Add any section names you want to skip processing
# for snippets. Case matters
skip_sections = []

# Represents how far back to fetch. Note that we're doing the past week
# but for say, perf season, setting this back to that time period means
# a nicely formatted dump of everything.
start_date = datetime.datetime.now() - datetime.timedelta(weeks=1)


def create_snippet(task, file):
    section = task['section']
    file.write(f" - ({section}) - {task['name']}\n")
    if task['notes']:
        file.write(f"   - {task['notes'].strip()}\n")
    subtasks = task['subtasks']
    # Don't print out my subtasks if the task is complete
    if task['completed']:
        return

    if subtasks:
        for subtask in subtasks:
            if subtask['completed']:
                file.write(f"   - *{subtask['name']} (COMPLETED)*\n")
            else:
                file.write(f"   - {subtask['name']}\n")

completed_tasks = []
new_tasks = []
modified_tasks = []

asana_client = asana.Client.access_token(access_token)
sections = asana_client.sections.get_sections_for_project(project_id)
for s in sections:
    # Honoe our skip sections if you don't want one showing up, add the section name to the
    # array above and then it won't show up in our report
    if s['name'] in skip_sections:
        continue
    tasks = asana_client.tasks.get_tasks_for_section(s['gid'],{'opt_fields':'name,notes,completed,created_at,modified_at,completed_at,subtasks,subtasks.name,subtasks.gid,subtasks.completed'})
    for task in tasks:
        task['section'] = s['name']
        if task['completed']:
            complete_time = datetime.datetime.strptime(task['completed_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
            if complete_time > start_date:
                completed_tasks.append(task)
            continue

        created_time = datetime.datetime.strptime(task['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        if created_time > start_date:
            new_tasks.append(task)
            continue

        modified_time = datetime.datetime.strptime(task['modified_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        if modified_time > start_date:
            modified_tasks.append(task)

snippets = open(f"Snippets_{start_date.strftime('%Y-%m-%d')}", "w")
snippets.write("**COMPLETED:**\n\n")
for t in completed_tasks:
    create_snippet(t, snippets)

snippets.write("\n**PROGRESS:**\n\n")
for t in modified_tasks:
    create_snippet(t, snippets)

snippets.write("\n**PLANNING:**\n\n")
for t in new_tasks:
    create_snippet(t, snippets)
