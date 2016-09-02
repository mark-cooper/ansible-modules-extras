#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
DOCUMENTATION = '''

module: uptimerobot
short_description: Add, remove, pause and start Uptime Robot monitoring
description:
    - This module will let you add, remove, start and pause Uptime Robot Monitoring
author:
    - "Nate Kingsley (@nate-kingsley)"
    - "Mark Cooper (@mark-cooper)"
version_added: "1.9"
requirements:
    - Valid Uptime Robot API Key
options:
    state:
        description:
            - Define whether or not the monitor should exist, be removed, running or paused.
        required: true
        default: null
        choices: [ "started", "paused", "present", "absent" ]
        aliases: []
    monitorid:
        description:
            - ID of the monitor to start, pause or remove.
        required: false
        default: null
        choices: []
        aliases: []
    monitorname:
        description:
            - Name of the monitor (required for state present).
        required: false
        default: null
        choices: []
        aliases: []
        version_added: '2.2'
    monitorurl:
        description:
            - URL of the monitor to add (required for state present).
        required: false
        default: null
        choices: []
        aliases: []
        version_added: '2.2'
    monitorcontactid:
        description:
            - The id of the contact(s) to add to a new monitor (optional for state present).
        required: false
        default: null
        choices: []
        aliases: []
        version_added: '2.2'
    apikey:
        description:
            - Uptime Robot API key.
        required: true
        default: null
        choices: []
        aliases: []
notes:
    - Support for alert contacts has not yet been implemented.
'''

EXAMPLES = '''
# Add a monitor with the name 'google'.
- uptimerobot: monitorname=google
           monitorurl=https://www.google.com
           monitorcontactid=98765
           apikey=12345-1234512345
           state=present

# Remove the monitor with an ID of 12345.
- uptimerobot: monitorid=12345
           apikey=12345-1234512345
           state=absent

# Pause the monitor with an ID of 12345.
- uptimerobot: monitorid=12345
           apikey=12345-1234512345
           state=paused

# Start the monitor with an ID of 12345.
- uptimerobot: monitorid=12345
           apikey=12345-1234512345
           state=started

# For remove, pause and start a name or url can be used.
- uptimerobot: monitorname=google
           apikey=12345-1234512345
           state=started

'''

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        # Let snippet from module_utils/basic.py return a proper error in this case
        pass

import urllib
import time

API_BASE = "https://api.uptimerobot.com/"

API_ACTIONS = dict(
    status='getMonitors?',
    editMonitor='editMonitor?',
    newMonitor='newMonitor?',
    deleteMonitor='deleteMonitor?',
)

API_FORMAT = 'json'
API_NOJSONCALLBACK = 1
CHANGED_STATE = False
SUPPORTS_CHECK_MODE = False

def checkID(module, params):

    return doRequest(module, 'status', params)

def checkResult(module, result):

    if result['stat'] != "ok":
        module.fail_json(
            msg="failed",
            result=result['message']
        )

def checkStatus(module, info):

    if info['status'] != 200:
        module.fail_json(
            msg="failed",
            result=info['msg']
        )

def newMonitor(module, params):

    if not params['monitorAlertContacts']:
        del params['monitorAlertContacts']

    return doRequest(module, 'newMonitor', params)

def deleteMonitor(module, params):

    del params['monitors'] # not required
    return doRequest(module, 'deleteMonitor', params)

def startMonitor(module, params):

    params['monitorStatus'] = 1
    return doRequest(module, 'editMonitor', params)


def pauseMonitor(module, params):

    params['monitorStatus'] = 0
    return doRequest(module, 'editMonitor', params)

def doRequest(module, action, params):

    data = urllib.urlencode(params)
    full_uri = API_BASE + API_ACTIONS[action] + data
    req, info = fetch_url(module, full_uri)

    checkStatus(module, info)

    result = req.read()
    jsonresult = json.loads(result)
    req.close()
    return jsonresult

def main():

    module = AnsibleModule(
        argument_spec = dict(
            state            = dict(required=True, choices=['started', 'paused', 'present', 'absent']),
            apikey           = dict(required=True),
            monitorid        = dict(required=False),
            monitorname      = dict(required=False),
            monitorurl       = dict(required=False),
            monitorcontactid = dict(required=False),
        ),
        supports_check_mode=SUPPORTS_CHECK_MODE
    )

    result  = None
    changed = False

    state              = module.params['state']
    api_key            = module.params['apikey']
    monitor_id         = module.params['monitorid']
    monitor_name       = module.params['monitorname']
    monitor_url        = module.params['monitorurl']
    monitor_contact_id = module.params['monitorcontactid']

    if not monitor_id and not monitor_name and not monitor_url:
        module.fail_json(msg="at least one of monitorid, monitorname or monitorurl are required")

    # if no monitor id is provided see if we can find one by name or url
    # but only assign the id if exactly one monitor is found
    if not monitor_id:
        search_term = monitor_name
        if monitor_url:
            search_term = monitor_url

        params = dict(
            apiKey=api_key,
            search=search_term,
            format=API_FORMAT,
            noJsonCallback=API_NOJSONCALLBACK,
        )
        result = checkID(module, params)
        if 'monitors' in result:
            monitors = result['monitors']['monitor']
            if len(monitors) == 1:
                monitor_id = monitors[0]['id']
            else:
                module.fail_json(msg="unable to uniquely identify monitor")

    id_params = dict(
        apiKey=api_key,
        monitors=monitor_id,
        monitorID=monitor_id,
        format=API_FORMAT,
        noJsonCallback=API_NOJSONCALLBACK,
    )

    new_params = dict(
        apiKey=api_key,
        monitorFriendlyName=monitor_name,
        monitorURL=monitor_url,
        monitorAlertContacts=monitor_contact_id,
        monitorType=1,
        format=API_FORMAT,
        noJsonCallback=API_NOJSONCALLBACK,
    )

    status_codes = dict(
        paused='0',
        up='2',
    )

    if state == 'present':
        if not new_params['monitorFriendlyName'] or not new_params['monitorURL']:
            module.fail_json(msg="monitorname and monitorurl are required for state present")

        if not monitor_id:
            result = newMonitor(module, new_params)
            checkResult(module, result)
            changed = True

    if monitor_id:
        # confirm the monitor id is valid
        result = checkID(module, id_params)
        checkResult(module, result)
        monitor_status = result['monitors']['monitor'][0]['status']

        if state == 'started':
            if monitor_status != status_codes['up']:
                result = startMonitor(module, id_params)
                changed = True
        elif state == 'paused':
            if monitor_status != status_codes['paused']:
                result = pauseMonitor(module, id_params)
                changed = True
        elif state == 'absent':
            result = deleteMonitor(module, id_params)
            changed = True
        else:
            pass # should not be possible

        # check result again in case of subsequent id related errors
        checkResult(module, result)

    module.exit_json(
        msg="success",
        result=result['stat'],
        changed=changed,
    )

from ansible.module_utils.basic import *
from ansible.module_utils.urls import *
if __name__ == '__main__':
    main()
