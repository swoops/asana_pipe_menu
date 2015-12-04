#!/usr/bin/python2
import requests
import optparse
import sys
import json
from lxml import etree
import os.path

# change this if you want the config file somewhere else
CONF_FILE = "{}/.config/asana_config".format(os.path.expanduser('~'))

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

def mark_completed(task_id):
    res = requests.put("{}api/1.0/tasks/{}".format(url_base, task_id), headers=auth, data={ "completed" : "True" })
    print res.json()
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

def make_config():
    print "config file will be located at: {}".format(CONF_FILE)
    access_token = raw_input("What is your api key\n")
    assert type(access_token) is str
    auth = { "Authorization" : "Bearer {}".format(access_token) }
    res = requests.get("{}api/1.0/users/me".format(url_base), headers=auth)
    if res.status_code != 200: 
        print "key not accepted"
        exit(3)
    cache_file = raw_input("where should I write the cache?\n")
    assert type(cache_file) is str
    data = { 
        "access_token" : access_token,
        "workspaces"   : res.json()["data"]["workspaces"],
        "cache_file"   : cache_file
    }

    with open(CONF_FILE, "w") as fp:
        fp.write(json.dumps(data))
    exit(0)

def get_update_element():
    execute = etree.Element("execute")
    execute.text="{} -u".format(sys.argv[0])
    action = etree.Element(
        "action", 
        name="Execute",
    )
    action.append(execute)

    exe_item = etree.Element(
        "item", 
        label ="Update Cache",
    )
    exe_item.append(action)
    return exe_item
    
def make_menu():
    # remove the cache file if it exits so people don't go
    # thinking things were updated already when we are still
    # waiting on the server
    if workspaces == None: exit(3)

    root = etree.Element("openbox_pipe_menu")
    root.append(get_update_element())
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


    with open(cache_file, "w") as fp:
        et = etree.ElementTree(root)
        et.write(fp, pretty_print=True)
    # print etree.tostring(root, pretty_print=True)

def main():
    parser = optparse.OptionParser('usage %prog [-p | -t <plugin_id>]')
    parser.add_option('-c', dest="mark", type='int', default=None, help='Mark this task completed\n')
    parser.add_option('-u', action="store_true", dest="update", default=False, help='update the cache file\n')
    (options, args) = parser.parse_args()
    if options.mark != None: 
        # first remove old file since that is faster then api request
        # and you don't want to get confused
        if os.path.isfile(cache_file): os.remove(cache_file)
        mark_completed(options.mark)
        make_menu()
    if options.update: 
        # first remove old file since that is faster then api request
        # and you don't want to get confused
        if os.path.isfile(cache_file): os.remove(cache_file)
        make_menu()
    else: 
        if not os.path.isfile(cache_file): 
            # file does not exist
            # could be it was not created yet, or it is being populated now
            root = etree.Element("openbox_pipe_menu")
            root.append(get_update_element())
            print(etree.tostring(root, pretty_print=True))
        else:
            with open(cache_file, "r") as fp: print fp.read()
        

if __name__ == '__main__':
    url_base = "https://app.asana.com/"
    try:
        json_data=open(CONF_FILE).read()
        data = json.loads(json_data)
        workspaces = data["workspaces"]
        access_token = data["access_token"]
        cache_file = data["cache_file"]
    except:
        ans = raw_input("Could not get your config file, should I make it for you? (y/n)\n")
        assert type(ans) is str
        if ans == "y" : make_config()
        else: exit(4)

    auth = { "Authorization" : "Bearer {}".format(access_token) }
    main()


