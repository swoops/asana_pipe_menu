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
        id="{}".format(task["name"])
    )


    # list of info for task
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
    except IndexError: return None
    except TypeError: return None

    for sep_menu in root.findall("menu"):
        if seperator in sep_menu.attrib.values(): 
            # print "true"
            return sep_menu

    # we have not seen this seperator yet
    # so we add it
    sep_menu = etree.Element(
        "menu",
        label="{}".format(seperator),
        id="{}".format(seperator)
    )
    root.append(sep_menu)
    return sep_menu

def get_proj_menu(task, root):
	try: project = task["projects"][0]["name"]
	except IndexError: project = "No Project"

	# have we seen this project before?
	for proj_menu in root.findall("menu"):
		if project in proj_menu.attrib.values(): return proj_menu

    # we have not seen this project yet
    # so we add it
	proj_menu = etree.Element(
		"menu",
		label="{}".format(project),
		id="{}".format(project)
	)
	root.append(proj_menu)
	return proj_menu


    
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
    parser = optparse.OptionParser('usage %prog [-m | -c <task_id>]')
    parser.add_option('-m', action="store_true", dest="me", default=False, help='list info on you, helps with filling in workspaces variable\n')
    parser.add_option('-c', dest="mark", type='int', default=None, help='Mark this task completed\n')
    (options, args) = parser.parse_args()
    if options.me: get_me()
    elif options.mark != None: mark_completed(options.mark)
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

            tasks.sort(key=lambda x: x["due_on"], reverse=False)
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
