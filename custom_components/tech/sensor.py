"""Provides sensor for selected attributes of Tech Thermostat."""
import logging
from typing import Optional
from homeassistant.components.binary_sensor import BinarySensorEntity, \
    BinarySensorDeviceClass
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up entry."""
    _LOGGER.debug("Setting up entry, module udid: " + config_entry.data["udid"])
    api = hass.data[DOMAIN][config_entry.entry_id]
    module_udid = config_entry.data["udid"]
    zones = await api.get_module_zones(module_udid)

    entities = []
    for zoneID in zones:
        zone = zones[zoneID]
        id, name = zone["zone"]["id"], zone["description"]["name"]

        entities.append(GenericTechBinarySensor(
            api=api,
            module_uuid=module_udid,
            zone=zone,
            path="zone.zoneState",
            id="%s_on" % id,
            name="%s On" % name,
            device_class=BinarySensorDeviceClass.RUNNING,
            transformer=lambda v: v != "zoneOff",
            icon_on="mdi:hvac",
            icon_off="mdi:hvac-off"
        ))
        entities.append(GenericTechBinarySensor(
            api=api,
            module_uuid=module_udid,
            zone=zone,
            path="underfloor.currentState",
            id="%s_floor_within_limits" % id,
            name="%s Floor Within Limits" % name,
            transformer=lambda v: v == "parametersReached",
            icon_on="mdi:thumb-up",
            icon_off="mdi:thermometer-alert"
        ))
        entities.append(GenericTechSensor(
            api=api,
            module_uuid=module_udid,
            zone=zone,
            path="underfloor.temperature",
            id="%s_floor_temperature" % id,
            name="%s Floor Temperature" % name,
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class="measurement",
            transformer=lambda v: v / 10
        ))

    async_add_entities(entities, True)


class TechZonePropertyBase:
    """Base class for a sensor based on tech zone property."""

    def __init__(self, api, module_uuid, zone, path, transformer=None):
        self._api = api
        self._module_uuid = module_uuid
        self._zone_id = zone["zone"]["id"]
        self._path = path.split(".")
        self._transformer = transformer
        self._value = None

        self.update_value(zone)

    def update_value(self, zone):
        self._value = None
        value = zone
        for field in self._path:
            if field not in value:
                return
            value = value[field]
        if self._transformer is not None:
            value = self._transformer(value)
        self._value = value

    async def async_update(self):
        """Updates the state"""
        zone = await self._api.get_zone(self._module_uuid, self._zone_id)
        self.update_value(zone)

    @property
    def value(self):
        return self._value


class GenericTechBinarySensor(TechZonePropertyBase, BinarySensorEntity):
    """Representation of a generic tech binary sensor"""

    def __init__(
            self,
            api,
            module_uuid,
            zone,
            path,
            id,
            name,
            device_class=None,
            transformer=None,
            icon_on=None,
            icon_off=None):
        super(GenericTechBinarySensor, self).__init__(
            api=api,
            module_uuid=module_uuid,
            zone=zone,
            path=path,
            transformer=transformer,
        )
        self._attr_unique_id = id
        self._attr_name = name
        self._attr_device_class = device_class
        self._icon_on = icon_on
        self._icon_off = icon_off

    @property
    def is_on(self):
        return self._value

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        if self.is_on:
            return self._icon_on
        return self._icon_off


class GenericTechSensor(TechZonePropertyBase, SensorEntity):
    """Representation of a generic tech binary sensor"""

    def __init__(
            self,
            api,
            module_uuid,
            zone,
            path,
            id,
            name,
            unit,
            device_class=None,
            state_class=None,
            transformer=None):
        super(GenericTechSensor, self).__init__(
            api=api,
            module_uuid=module_uuid,
            zone=zone,
            path=path,
            transformer=transformer,
        )
        self._attr_unique_id = id
        self._attr_name = name
        self._attr_device_class = device_class
        self._state_class = state_class
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return self._value
