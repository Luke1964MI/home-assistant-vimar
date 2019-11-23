"""Platform for cover integration."""
# credits to https://community.home-assistant.io/t/create-new-cover-component-not-working/50361/5

from homeassistant.components.cover import (
    CoverDevice, SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_STOP)
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
)
import homeassistant.helpers.config_validation as cv
import logging
import voluptuous as vol
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

# see: https://developers.home-assistant.io/docs/en/entity_cover.html

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Cover platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Cover started!")
    covers = []

    # _LOGGER.info("Vimar Plattform Config: ")
    # _LOGGER.info(config)
    # _LOGGER.info("discovery_info")
    # _LOGGER.info(discovery_info)
    # _LOGGER.info(hass.config)
    # this will give you overall hass config, not configuration.yml
    # hassconfig = hass.config.as_dict()

    # vimarconfig = config

    # # Verify that passed in configuration works
    # if not vimarconnection.is_valid_login():
    #     _LOGGER.error("Could not connect to Vimar Webserver "+ host)
    #     return False

    # _LOGGER.info(config)
    vimarconnection = hass.data[DOMAIN]['connection']
    
    # # load Main Groups
    # vimarconnection.getMainGroups()

    # # load devices
    # devices = vimarconnection.getDevices()
    # devices = hass.data[DOMAIN]['devices']
    devices = hass.data[DOMAIN][discovery_info['hass_data_key']]

    if len(devices) != 0:
        # for device_id, device_config in config.get(CONF_DEVICES, {}).items():
        # for device_id, device_config in devices.items():
        #     name = device_config['name']
        #     covers.append(VimarCover(name, device_id, vimarconnection))
        for device_id, device in devices.items():
            covers.append(VimarCover(device, device_id, vimarconnection))


    # fallback
    # if len(lights) == 0:
    #     # Config is empty so generate a default set of switches
    #     for room in range(1, 2):
    #         for device in range(1, 2):
    #             name = "Room " + str(room) + " Device " + str(device)
    #             device_id = "R" + str(room) + "D" + str(device)
    #             covers.append(VimarCover({'object_name': name}, device_id, link))

    if len(covers) != 0:
        async_add_entities(covers)
    _LOGGER.info("Vimar Cover complete!")

class VimarCover(CoverDevice):
    """ Provides a Vimar cover. """

    # pylint: disable=no-self-use
    def __init__(self, device, device_id, vimarconnection):
        """Initialize the cover."""
        self._device = device
        self._name = self._device['object_name']
        self._name = self._name.replace('ROLLLADEN', 'ROLLO')
        # change case
        self._name = self._name.title()
        self._device_id = device_id
        # _state = False .. 0, stop has not been pressed
        # _state = True .. 1, stop has been pressed
        self._state = False
        # _direction = 0 .. upwards
        # _direction = 1 .. downards
        self._direction = 0
        self._reset_status()
        self._vimarconnection = vimarconnection

    ####### default properties

    @property
    def should_poll(self):
        """ polling is needed for a Vimar device. """
        return True

    @property
    def name(self):
        """ Returns the name of the device. """
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if 'icon' in self._device and self._device['icon']:
            return self._device['icon']
        # return self.ICON
        return ("mdi:window-open","mdi:window-closed")[self.is_closed]

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device['device_class']

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return self._device_id
    
    @property
    def available(self):
        """Return True if entity is available."""
        return True


    ####### cover properties

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        # if _state (stopped) is 1, than stopped was pressed, therefor it should be open
        # if its 0, and direction 1, than it was going downwards and it was not stopped, therefor closed
        if self._state :
            return False
        elif self._direction:
            return True
        else:
            return False

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP

    ####### async getter and setter

    # def update(self):
    async def async_update(self):
        """Fetch new state data for this cover.
        This is the only method that should fetch new data for Home Assistant.
        """
        # self._light.update()
        # self._state = self._light.is_on()
        # self._brightness = self._light.brightness
        # self._device = self._vimarconnection.getDevice(self._device_id)
        # self._device['status'] = self._vimarconnection.getDeviceStatus(self._device_id)
        old_status = self._device['status']
        self._device['status'] = await self.hass.async_add_executor_job(self._vimarconnection.get_device_status, self._device_id)
        self._reset_status()
        if old_status != self._device['status']:
            self.async_schedule_update_ha_state()

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        if 'status' in self._device and self._device['status']:
            if 'up/down' in self._device['status']:
                self._direction = 1
                self._device['status']['up/down']['status_value'] = '1'
                # self._vimarconnection.set_device_status(self._device['status']['up/down']['status_id'], 1)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['up/down']['status_id'], 1)
                self.async_schedule_update_ha_state()

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        if 'status' in self._device and self._device['status']:
            if 'up/down' in self._device['status']:
                self._direction = 0
                self._device['status']['up/down']['status_value'] = '0'
                # self._vimarconnection.set_device_status(self._device['status']['up/down']['status_id'], 0)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['up/down']['status_id'], 0)
                self.async_schedule_update_ha_state()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        if 'status' in self._device and self._device['status']:
            if 'stop up/stop down' in self._device['status']:
                self._state = 1
                self._device['status']['stop up/stop down']['status_value'] = '1'
                # self._vimarconnection.set_device_status(self._device['status']['stop up/stop down']['status_id'], 1)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['stop up/stop down']['status_id'], 1)
                self.async_schedule_update_ha_state()

    ####### private helper methods

    def _reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device and self._device['status']:
            if 'stop up/stop down' in self._device['status']:
                self._state = (False, True)[self._device['status']['stop up/stop down']['status_value'] != '0']
            if 'up/down' in self._device['status']:
                self._direction = int(self._device['status']['up/down']['status_value'])
            

# end class VimarCover