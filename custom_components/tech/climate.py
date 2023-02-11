"""Support for Tech HVAC system."""
import logging
import json
from typing import List, Optional
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORT_HVAC = [HVAC_MODE_HEAT, HVAC_MODE_OFF]

ATTR_UNDERFLOOR_TEMP = "underfloor_temperature"
ATTR_UNDERFLOOR_WITHIN_LIMITS = "underfloor_within_limits"

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up entry."""
    _LOGGER.debug("Setting up entry, module udid: " + config_entry.data["udid"])
    api = hass.data[DOMAIN][config_entry.entry_id]
    zones = await api.get_module_zones(config_entry.data["udid"])

    entities = []
    for zone in zones:
        t = TechThermostat(
            zones[zone],
            api,
            config_entry,
        )
        if t.enabled:
            entities.append(t)
            entities.append(TechThermostatOn(t))
            entities.append(TechThermostatFloorWithinLimits(t))

    async_add_entities(entities, True)


class TechThermostatOn(BinarySensorEntity):
    """Representation of a Tech climate's on / off state."""

    def __init__(self, thermostat):
        self._thermostat = thermostat
        self._id = str(thermostat.unique_id) + "_on"
        self._name = "%s On" % thermostat.name

    @property
    def unique_id(self) -> str:
       """Return an unique ID."""
       return self._id

    @property
    def name(self):
       """Return the name of the device."""
       return self._name

    @property
    def is_on(self):
        return self._thermostat._mode != HVAC_MODE_OFF

    @property
    def icon(self) -> Optional[str]:
       """Return the icon to use in the frontend, if any."""
       return "mdi:hvac" if self.is_on else "mdi:hvac-off"

class TechThermostatFloorWithinLimits(BinarySensorEntity):
    """Binary sensor representing whether a Tech climate's floor is within limits."""

    def __init__(self, thermostat):
        self._thermostat = thermostat
        self._id = str(thermostat.unique_id) + "_floor_within_limits"
        self._name = "%s Floor Within Limits" % thermostat.name

    @property
    def unique_id(self) -> str:
       """Return an unique ID."""
       return self._id

    @property
    def name(self):
       """Return the name of the device."""
       return self._name

    @property
    def is_on(self):
       return self._thermostat._underfloor_within_limits

    @property
    def icon(self) -> Optional[str]:
       """Return the icon to use in the frontend, if any."""
       return "mdi:thumb-up" if self.is_on else "mdi:thermometer-alert"

class TechThermostat(ClimateEntity):
    """Representation of a Tech climate."""

    def __init__(self, device, api, config_entry):
        """Initialize the Tech device."""
        _LOGGER.debug("Init TechThermostat...")
        self._config_entry = config_entry
        self._api = api
        self._id = device["zone"]["id"]
        self.update_properties(device)

    def update_properties(self, device):
        self._name = device["description"]["name"]
        if device["zone"]["setTemperature"] is not None:
            self._target_temperature = device["zone"]["setTemperature"] / 10
        else:
            self._target_temperature = None
        if device["zone"]["currentTemperature"] is not None:
            self._temperature =  device["zone"]["currentTemperature"] / 10
        else:
            self._temperature = None
        state = device["zone"]["flags"]["relayState"]
        if state == "on":
            self._state = CURRENT_HVAC_HEAT
        elif state == "off":
            self._state = CURRENT_HVAC_IDLE
        else:
            self._state = CURRENT_HVAC_OFF
        mode = device["zone"]["zoneState"]
        if mode == "zoneOn" or mode == "noAlarm":
            self._mode = HVAC_MODE_HEAT
        else:
            self._mode = HVAC_MODE_OFF
        self._underfloor_temperature = None
        self._underfloor_within_limits = None
        if "underfloor" in device:
          underfloor = device["underfloor"]
          if "temperature" in underfloor:
            self._underfloor_temperature = underfloor["temperature"] / 10
          if "currentState" in underfloor:
            self._underfloor_within_limits = underfloor["currentState"] == "parametersReached"
        self._visibility = device["zone"]["visibility"]

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._id
    
    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE #| SUPPORT_PRESET_MODE

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.

        Need to be one of HVAC_MODE_*.
        """
        return self._mode

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        return SUPPORT_HVAC

    @property
    def hvac_action(self) -> Optional[str]:
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        return self._state

    async def async_update(self):
        """Call by the Tech device callback to update state."""
        _LOGGER.debug("Updating Tech zone: %s, udid: %s, id: %s", self._name, self._config_entry.data["udid"], self._id)
        device = await self._api.get_zone(self._config_entry.data["udid"], self._id)
        self.update_properties(device)

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def underfloor_temperature(self):
        """Return the underfloor temperature."""
        return self._underfloor_temperature

    @property
    def underfloor_within_limits(self):
        """Return boolean indicating whether underfloor temperature is within limits."""
        return self._underfloor_within_limits

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        attrs = {
          ATTR_UNDERFLOOR_TEMP: self.underfloor_temperature,
          ATTR_UNDERFLOOR_WITHIN_LIMITS: self.underfloor_within_limits,
        }
        if super().extra_state_attributes is not None:
          attrs.update(super().extra_state_attributes)
        return attrs

    @property
    def enabled(self):
        """Return boolean indicating whether entity is enabled = physically present."""
        return self._visibility

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature:
            _LOGGER.debug("%s: Setting temperature to %s", self._name, temperature)
            self._temperature = temperature
            await self._api.set_const_temp(self._config_entry.data["udid"], self._id, temperature)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        _LOGGER.debug("%s: Setting hvac mode to %s", self._name, hvac_mode)
        if hvac_mode == HVAC_MODE_OFF:
            await self._api.set_zone(self._config_entry.data["udid"], self._id, False)
        elif hvac_mode == HVAC_MODE_HEAT:
            await self._api.set_zone(self._config_entry.data["udid"], self._id, True)

