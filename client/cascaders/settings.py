'''
Functions for dealing with settings files, the settings file is basically an
dict
'''
import os
import json
from logging import warn, debug

defaultSettings = {
        'autostart' : False,
        'cascSubjects' : [],
        'cascading' : False,
        'autocascade' : True,
        'asked_autocascade' : False,
        'asked_autostart' : False,
}

def getSettingsDirectory():
    dr = os.path.expanduser(os.path.join('.config', 'cascaders'))
    if not os.path.exists(dr):
        debug('creating directoires for config')
        os.makedirs(dr)
    return dr

def getSettingsFile():
    return os.path.join(getSettingsDirectory(), 'settings.json')

def loadSettings():
    try:
        with open(getSettingsFile()) as fh:
            fileStr = fh.read()
            try:
                settings = json.loads(fileStr)
            except ValueError:
                warn('Failed to decode json, using default settings')
                return defaultSettings

            for k, v in defaultSettings.iteritems():
                if not k in settings:
                    settings[k] = v
            return settings
    except IOError:
        debug('Failed to open file, probably doesn\'t exist')
        return defaultSettings

def saveSettings(settings):
    print settings
    with open(getSettingsFile(), 'wb') as f:
        return f.write(json.dumps(settings))

