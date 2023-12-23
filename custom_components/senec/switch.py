"""Platform for Senec Switches."""
import asyncio
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import slugify
from homeassistant.const import STATE_ON, STATE_OFF, CONF_TYPE

from typing import Literal
from . import SenecDataUpdateCoordinator, SenecEntity
from .const import DOMAIN, MAIN_SWITCH_TYPES, CONF_SYSTYPE_INVERTER, CONF_SYSTYPE_WEB, ExtSwitchEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistantType, config_entry: ConfigEntry, async_add_entities):
    """Initialize sensor platform from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    if CONF_TYPE in config_entry.data and config_entry.data[CONF_TYPE] == CONF_SYSTYPE_INVERTER:
        _LOGGER.info("No switches for Inverters...")
    elif CONF_TYPE in config_entry.data and config_entry.data[CONF_TYPE] == CONF_SYSTYPE_WEB:
        _LOGGER.info("No switches for WebPortal...")
    else:
        entities = []
        for description in MAIN_SWITCH_TYPES:
            entity = SenecSwitch(coordinator, description)
            entities.append(entity)
        async_add_entities(entities)


class SenecSwitch(SenecEntity, SwitchEntity):
    def __init__(
            self,
            coordinator: SenecDataUpdateCoordinator,
            description: ExtSwitchEntityDescription
    ):
        """Initialize a singular value sensor."""
        super().__init__(coordinator=coordinator, description=description)
        if (hasattr(self.entity_description, 'entity_registry_enabled_default')):
            self._attr_entity_registry_enabled_default = self.entity_description.entity_registry_enabled_default
        else:
            self._attr_entity_registry_enabled_default = True

        title = self.coordinator._config_entry.title
        key = self.entity_description.key.lower()
        name = self.entity_description.name
        self.entity_id = f"switch.{slugify(title)}_{key}"

        # we use the "key" also as our internal translation-key - and EXTREMELY important we have
        # to set the '_attr_has_entity_name' to trigger the calls to the localization framework!
        self._attr_translation_key = key
        self._attr_has_entity_name = True

    async def async_turn_on(self, **kwargs):  # pylint: disable=unused-argument
        """Turn on the switch."""
        try:
            if self.entity_description.array_key is not None:
                await self.coordinator._async_switch_array_to_state(self.entity_description.array_key, self.entity_description.array_pos, True)
            else:
                await self.coordinator._async_switch_to_state(self.entity_description.key, True)
            self.async_schedule_update_ha_state(force_refresh=True)
            if hasattr(self.entity_description, 'update_after_switch_delay_in_sec') and self.entity_description.update_after_switch_delay_in_sec > 0:
                await asyncio.sleep(self.entity_description.update_after_switch_delay_in_sec)
                self.async_schedule_update_ha_state(force_refresh=True)


        except ValueError:
            return "unavailable"

    async def async_turn_off(self, **kwargs):  # pylint: disable=unused-argument
        """Turn off the switch."""
        try:
            if self.entity_description.array_key is not None:
                await self.coordinator._async_switch_array_to_state(self.entity_description.array_key, self.entity_description.array_pos, False)
            else:
                await self.coordinator._async_switch_to_state(self.entity_description.key, False)
            self.async_schedule_update_ha_state(force_refresh=True)
            if hasattr(self.entity_description, 'update_after_switch_delay_in_sec') and self.entity_description.update_after_switch_delay_in_sec > 0:
                await asyncio.sleep(self.entity_description.update_after_switch_delay_in_sec)
                self.async_schedule_update_ha_state(force_refresh=True)

        except ValueError:
            return "unavailable"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        # return self.coordinator.data.get("title", "") == "foo"
        try:
            if self.entity_description.array_key is not None:
                value = getattr(self.coordinator.senec, self.entity_description.array_key)[self.entity_description.array_pos] == 1
            else:
                value = getattr(self.coordinator.senec, self.entity_description.key)
            if value is None or value == "":
                value = None
            else:
                self._attr_is_on = value
        except KeyError:
            value = None
        except TypeError:
            return None
        return value

    @property
    def state(self) -> Literal["on", "off"] | None:
        """Return the state."""
        if (is_on := self.is_on) is None:
            return None
        return STATE_ON if is_on else STATE_OFF
