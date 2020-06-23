"""Platform for cover integration."""
# credits to
# https://community.home-assistant.io/t/create-new-cover-component-not-working/50361/5

import logging
from datetime import timedelta

from homeassistant.components.cover import (SUPPORT_CLOSE, SUPPORT_OPEN,
                                            SUPPORT_STOP)
from homeassistant.util import Throttle

# from . import format_name
from .const import DOMAIN
from .vimar_entity import VimarEntity

try:
    from homeassistant.components.cover import CoverEntity
except ImportError:
    from homeassistant.components.cover import CoverDevice as CoverEntity


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=2)
PARALLEL_UPDATES = 3


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Cover platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Cover started!")
    covers = []

    vimarconnection = hass.data[DOMAIN]['connection']

    devices = hass.data[DOMAIN][discovery_info['hass_data_key']]

    if len(devices) != 0:
        for device_id, device in devices.items():
            covers.append(VimarCover(device, device_id, vimarconnection))

    if len(covers) != 0:
        # If your entities need to fetch data before being written to Home
        # Assistant for the first time, pass True to the add_entities method:
        # add_entities([MyEntity()], True).
        async_add_entities(covers)
    _LOGGER.info("Vimar Cover complete!")


# see: https://developers.home-assistant.io/docs/core/entity/cover
class VimarCover(VimarEntity, CoverEntity):
    """Provides a Vimar cover."""

    # see:
    # https://developers.home-assistant.io/docs/entity_index/#generic-properties
    # Return True if the state is based on our assumption instead of reading it from the device. this will ignore is_closed state
    assumed_state = True

    # Set entity_id, object_id manually due to possible duplicates
    entity_id = "cover." + "unset"

    # pylint: disable=no-self-use
    def __init__(self, device, device_id, vimarconnection):
        """Initialize the cover."""

        VimarEntity.__init__(self, device, device_id, vimarconnection)
        # set device type specific attributes

        # _state = False .. 0, stop has not been pressed
        # _state = True .. 1, stop has been pressed

        # _direction = 0 .. upwards
        # _direction = 1 .. downards
        self._direction = 0
        self.entity_id = "cover." + self._name.lower() + "_" + self._device_id

    # @property
    # def icon(self):
    #     """Icon to use in the frontend, if any."""
    #     if 'icon' in self._device and self._device['icon']:
    #         return self._device['icon']
    #     # return self.ICON
    #     return (ICON, ICON_ALT)[self.is_closed]

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        # if _state (stopped) is 1, than stopped was pressed, therefor it cannot be completely closed
        # if its 0, and direction 1, than it was going downwards and it was
        # never stopped, therefor it is closed now
        if self._state:
            self.assumed_state = True
            return False
        elif self._direction == 1:
            self.assumed_state = False
            return True
        else:
            self.assumed_state = False
            return False

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP

    # async getter and setter

    # def update(self):
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Fetch new state data for this cover.
        This is the only method that should fetch new data for Home Assistant.
        """
        # starttime = localtime()
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
        # _LOGGER.debug("Vimar Cover update finished after " +
        # str(mktime(localtime()) - mktime(starttime)) + "s " + self._name)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        if 'status' in self._device and self._device['status']:
            if 'up/down' in self._device['status']:
                self._direction = 1
                self._state = 0
                self._device['status']['up/down']['status_value'] = '1'
                # self._vimarconnection.set_device_status(self._device['status']['up/down']['status_id'], 1)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['up/down']['status_id'], 1)
                self.async_schedule_update_ha_state()

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        if 'status' in self._device and self._device['status']:
            if 'up/down' in self._device['status']:
                self._direction = 0
                self._state = 0
                self._device['status']['up/down']['status_value'] = '0'
                # self._vimarconnection.set_device_status(self._device['status']['up/down']['status_id'], 0)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['up/down']['status_id'], 0)
                self.async_schedule_update_ha_state()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        if 'status' in self._device and self._device['status']:
            if 'stop up/stop down' in self._device['status']:
                self._state = 1
                self.assumed_state = True
                self._device['status']['stop up/stop down']['status_value'] = '1'
                # self._vimarconnection.set_device_status(self._device['status']['stop up/stop down']['status_id'], 1)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['stop up/stop down']['status_id'], 1)
                self.async_schedule_update_ha_state()

    # private helper methods

    def _reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device and self._device['status']:
            if 'stop up/stop down' in self._device['status']:
                self._state = (
                    False, True)[
                    self._device['status']['stop up/stop down']
                    ['status_value'] != '0']
            if 'up/down' in self._device['status']:
                self._direction = int(
                    self._device['status']['up/down']['status_value'])
                # self.assumed_state = False

    @property
    def is_default_state(self):
        """Returns True of in default state - resulting in default icon"""
        return self.is_closed

# end class VimarCover
