#!/usr/bin/python2
import requests
import optparse
import sys
from lxml import etree



#################################################################
#################   FILL THIS OUT!!!         ####################
#################################################################
workspaces =  [{'id': 000000000000, 'name': 'Personal Projects'}]
access_token = "0000000000000000000000000000000000"
#################################################################

auth = { "Authorization" : "Bearer {}".format(access_token) }
url_base = "https://app.asana.com/"
def get_task_menu(task):
    task_menu = etree.Element(
        "menu", 
        label="{}".format(task["name"]),
        id="{}".format(task["id"])
    )

    # list of info for task
    if task["due_on"] is None: task["due_on"] = "eh.. whenever"
    for k in [ 
        "Due: {}".format(task["due_on"]), 
        "Assignee: {}".format(task["assignee"]["name"])
        ]:
        task_menu.append(etree.Element(
            "item", 
            label="{}".format(k)
    ))
    task_menu.append(make_completion_marker(task))


    return task_menu

def make_completion_marker(task):
    execute = etree.Element("execute")
    execute.text="{} -c {}".format(sys.argv[0], task["id"])
    action = etree.Element(
        "action", 
        name="Execute",
    )
    action.append(execute)

    exe_item = etree.Element(
        "item", 
        label =" == Mark Completed == ",
    )
    exe_item.append(action)
    return exe_item

def get_sep_menu(task, root):
    try: 
        seperator = task["memberships"][0]["section"]["name"]
        seperator_id = task["memberships"][0]["section"]["id"]
    except IndexError: return None
    except TypeError: return None

    for sep_menu in root.findall("menu"):
        # print "\tif sep_menu: {} in sep_menu.attrib.values(): {}".format(seperator, sep_menu.attrib.values())
        if seperator in sep_menu.attrib.values(): 
            # print "true"
            return sep_menu

    # we have not seen this seperator yet
    # so we add it
    # print "adding new seperator"
    sep_menu = etree.Element(
        "menu",
        label="{}".format(seperator),
        id="{}".format(seperator_id)
    )
    # print etree.tostring(sep_menu, pretty_print=True)
    root.append(sep_menu)
    return sep_menu

def get_proj_menu(task, root):
    try: 
        project = task["projects"][0]["name"]
        project_id = task["projects"][0]["id"]
    except IndexError: 
        project = "No Project"
        import random
        project_id = random.random()

    # have we seen this project before?
    for proj_menu in root.findall("menu"):
        if project in proj_menu.attrib.values(): return proj_menu

    # we have not seen this project yet
    # so we add it
    proj_menu = etree.Element(
        "menu",
        label="{}".format(project),
        id="{}".format(project_id)
    )
    root.append(proj_menu)
    return proj_menu


    
# get tasks that are not archived
def get_projects(archived=False):
    res = requests.get("{}api/1.0/projects".format(url_base), params={"archived":archived}, headers=auth)
    if res.status_code == 200:
        return res.json()["data"]
    else:
        return None

# get tasks for project id 
def get_tasks(pro_id, completed=False):
    res = requests.get("{}api/1.0/projects/{}/tasks".format(url_base, pro_id), headers=auth, params={"opt_fields" : "completed,name,assignee"})
    if res.status_code == 200:
        return res.json()["data"]
    else:
        return None

def get_me():
    res = requests.get("{}api/1.0/users/me".format(url_base), headers=auth)
    print res.json()
    exit(0)

def mark_completed(task_id):
    res = requests.put("{}api/1.0/tasks/{}".format(url_base, task_id), headers=auth, data={ "completed" : "True" })
    # print res.json()
    exit(0)
    

def get_asigned_tasks(workspace, who="me", archived=False, completed=False ):
    params={
        "archived" : archived,
        "completed" : completed,
        "opt_fields" : "completed,name,assignee.name,projects.name,due_on,memberships.section.name",
        "assignee" : who,
        "workspace" : workspace
        }
    res = requests.get("{}api/1.0/tasks/".format(url_base), headers=auth, params=params)
    # print res.json()
    if res.status_code == 200:
        return res.json()["data"]
    else:
        return None

    
    
    

def main():
    parser = optparse.OptionParser('usage %prog [-p | -t <plugin_id>]')
    parser.add_option('-p', action="store_true", dest="plugins", default=False, help='list plugins\n')
    parser.add_option('-m', action="store_true", dest="me", default=False, help='list info on you\n')
    parser.add_option('-t', dest="tasks", type='int', default=None, help='List tasks for this pluginid\n')
    parser.add_option('-c', dest="mark", type='int', default=None, help='Mark this task completed\n')
    (options, args) = parser.parse_args()
    if options.me: get_me()
    elif options.mark != None: mark_completed(options.mark)
    elif options.plugins:
        projects = get_projects()
        if projects == None:
            exit(2)
        root = etree.Element("openbox_pipe_menu")
        for i in projects:
            root.append(etree.Element(
                "menu", 
                execute="{} -t {}".format(sys.argv[0], i["id"]),
                label="{}".format(i["name"]),
                id="{}".format(i["name"])
            ))
        sys.stdout.write(etree.tostring(root, pretty_print=True))
    elif options.tasks != None:
        tasks = get_tasks(options.tasks)
        if tasks == None:
            exit(3)
        root = etree.Element("openbox_pipe_menu")
        for i in tasks:
            if not i["completed"]:
                root.append(etree.Element(
                    "item", 
                    label="{}".format(i["name"])
                ))
        print etree.tostring(root, pretty_print=True)
    else:   
        if workspaces == None: exit(3)

        root = etree.Element("openbox_pipe_menu")
        for work in workspaces:
            # name workspace
            root.append(etree.Element(
                "separator", 
                label="{}".format(work["name"])
            ))
            tasks = get_asigned_tasks(work["id"])
            assert tasks != None

            tasks.sort(key=lambda x: (x["due_on"] is None, x['due_on']), reverse=False)
            for task in tasks:
                if task["completed"]: continue

                # remove tasks that are seperators...
                try: 
                    if task["name"][-1] == ":": continue
                except IndexError: 
                    continue

                proj_menu = get_proj_menu(task, root)
                task_menu = get_task_menu(task)
                sep_menu = get_sep_menu(task, proj_menu)

                # if it has a seperator make a sub menu
                if sep_menu is None:
                    proj_menu.append( task_menu )
                else:
                    sep_menu.append( task_menu )

        print etree.tostring(root, pretty_print=True)
        

if __name__ == '__main__':
    main()


