import argparse
import asana
import datetime
import json
import os
import re
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--start", help="This should be a date in the format yyyy-mm-dd")
parser.add_argument("-e", "--end", help="This should be a date in the format yyyy-mm-dd")
parser.add_argument("-w", "--weeks", help="How many weeks to fetch")
parser.add_argument("-d", "--debug", help="Turn on debugging output.", action='store_true')
args = parser.parse_args()

def debugging():
    return args.debug

out_file = None
if debugging():
    out_file = open("log.html", "w")
    out_file.write("<html>\n")
    out_file.write("<head>\n")
    out_file.write('''<style>
    li.completed {
        color: red;
        font-style: italic;
    }
    li.progress {
        color: darkgoldenrod;
    }
    li.planned {
        color: darkgreen;
    }
    li.skipped {
        color: red;
        font-style: italic;
    }
</style>
'''
    )
    out_file.write("</head>\n<body>\n")

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
skip_sections = [
    "Next '20 Demo",
    "DIY Home Video Studio",
    "Set up OBS"
]

# Get our bounds for time established. Default is one week back from "now"
start_date = datetime.datetime.now() - datetime.timedelta(weeks=1)
end_date = datetime.datetime.now()
weeks = 1

if args.weeks:
    try:
        weeks = int(args.weeks)
    except:
        print("Weeks must be a number")
        sys.exit(1)

if args.start:
    try:
        start_date = datetime.datetime.strptime(args.start, "%Y-%m-%d")
    except:
        print("Format for date must be yyyy-mm-dd")
        sys.exit(1)
    if not args.end:
        end_date = start_date + datetime.timedelta(weeks=weeks)

if args.end:
    if args.end == "now" or args.end == "today":
        end_date = datetime.datetime.now()
    else:
        try:
            end_date = datetime.datetime.strptime(args.end, "%Y-%m-%d")
        except:
            print("Format for date must be yyyy/mm/dd")
            sys.exit(1)
    if not args.start:
        start_date = end_date - datetime.timedelta(weeks=weeks)

if debugging():
    out_file.write(f"<h2>Fetching snippets from {start_date} to {end_date}</h2>\n")

def create_snippet(task, file):
    section = task['section']
    notes = None
    highlight = False
    show_notes = True
    if task['notes']:
        notes = task['notes'].strip()
        if re.search("#nolist", notes):
            return
        if re.search("#nonotes", notes):
            show_notes = False

        n = len(notes)
        notes = re.sub("[\n]*#highlight", "", notes)
        # test if we did in fact remove anything
        if len(notes) < n:
            highlight = True

    file.write(f" - ")
    if highlight:
        file.write("**")
    file.write(f"({section}) - {task['name']}")
    if highlight:
        file.write("**")
    file.write("\n")
    if notes and show_notes:
        file.write(f"   - {notes}\n")
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
    section_name = s['name']
    if debugging():
        out_file.write(f"<h3>Section: {section_name}</h3>\n")
    # Honoe our skip sections if you don't want one showing up, add the section name to the
    # array above and then it won't show up in our report
    if section_name in skip_sections:
        if debugging():
            out_file.write(f"<ul><li class='skipped'>Skipping</li></ul>\n")
        continue

    tasks = asana_client.tasks.get_tasks_for_section(s['gid'],{'opt_fields':'name,notes,completed,created_at,modified_at,completed_at,subtasks,subtasks.name,subtasks.gid,subtasks.completed'})
    if debugging():
        out_file.write("<ul>\n")
    for task in tasks:
        task['section'] = section_name
        if task['completed']:
            complete_time = datetime.datetime.strptime(task['completed_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
            if debugging():
                out_file.write(f"<li class='completed'>Task: {task['name']}</li>\n")
            if complete_time > start_date and complete_time < end_date:
                completed_tasks.append(task)
            continue

        created_time = datetime.datetime.strptime(task['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        if created_time > start_date and created_time < end_date:
            new_tasks.append(task)
            if debugging():
                out_file.write(f"<li class='planned'>Task: {task['name']}</li>\n")
            continue

        modified_time = datetime.datetime.strptime(task['modified_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        if modified_time > start_date and modified_time < end_date:
            modified_tasks.append(task)
            if debugging():
                out_file.write(f"<li class='progress'>Task: {task['name']}</li>\n")
    if debugging():
        out_file.write("</ul>\n")

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

if debugging():
    out_file.write("</body>\n</html>\n")