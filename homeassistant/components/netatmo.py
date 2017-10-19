"""
Support for the Netatmo devices.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/netatmo/
"""
import logging
from datetime import timedelta
from urllib.error import HTTPError

import voluptuous as vol

from homeassistant.const import (
    CONF_API_KEY, CONF_PASSWORD, CONF_USERNAME, CONF_DISCOVERY)
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

REQUIREMENTS = [
    'https://github.com/jabesq/netatmo-api-python/archive/'
    'v0.9.2.zip#lnetatmo==0.9.2']

_LOGGER = logging.getLogger(__name__)

CONF_SECRET_KEY = 'secret_key'

DOMAIN = 'netatmo'

NETATMO_AUTH = 'netatmo_auth'
NETATMO_CAMERA_DATA = 'netatmo_camera_data'

DEFAULT_DISCOVERY = True

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)
MIN_TIME_BETWEEN_EVENT_UPDATES = timedelta(seconds=10)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_SECRET_KEY): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(CONF_DISCOVERY, default=DEFAULT_DISCOVERY): cv.boolean,
    })
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the Netatmo devices."""
    import lnetatmo

    try:
        hass.data[NETATMO_AUTH] = lnetatmo.ClientAuth(
            config[DOMAIN][CONF_API_KEY], config[DOMAIN][CONF_SECRET_KEY],
            config[DOMAIN][CONF_USERNAME], config[DOMAIN][CONF_PASSWORD],
            'read_station read_camera access_camera '
            'read_thermostat write_thermostat '
            'read_presence access_presence')
    except HTTPError:
        _LOGGER.error("Unable to connect to Netatmo API")
        return False

    hass.data[NETATMO_CAMERA_DATA] = CameraData(hass.data[NETATMO_AUTH])

    if config[DOMAIN][CONF_DISCOVERY]:
        for component in 'camera', 'sensor', 'binary_sensor', 'climate':
            discovery.load_platform(hass, component, DOMAIN, {}, config)

    return True


class CameraData(object):
    """Get the latest data from Netatmo."""

    def __init__(self, auth):
        """Initialize the data object."""
        self.auth = auth
        self.camera_data = None

    def get_camera_names(self, camera_home):
        """Return all camera available on the API as a list."""
        camera_names = []
        self.update()
        if not camera_home:
            for home in self.camera_data.cameras:
                for camera in self.camera_data.cameras[home].values():
                    camera_names.append(camera['name'])
        else:
            for camera in self.camera_data.cameras[camera_home].values():
                camera_names.append(camera['name'])
        return camera_names

    def get_module_names(self, camera_name, camera_home):
        """Return all module available on the API as a list."""
        module_names = []
        self.update()
        cam_id = self.camera_data.cameraByName(camera=camera_name,
                                               camera_home=camera_home)['id']
        for module in self.camera_data.modules.values():
            if cam_id == module['cam_id']:
                module_names.append(module['name'])
        return module_names

    def get_camera_type(self, camera_name=None, camera_home=None):
        """Return the type of camera"""
        return self.camera_data.cameraType(camera_name, camera_home)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Call the Netatmo API to update the data."""
        import lnetatmo
        self.camera_data = lnetatmo.CameraData(self.auth, size=100)

    @Throttle(MIN_TIME_BETWEEN_EVENT_UPDATES)
    def update_event(self):
        """Call the Netatmo API to update the events."""
        self.camera_data.updateEvent(cameratype=self.camera_type)
