"""What every Clicker entity shares, and how platforms keep one per binding."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.const import STATE_ON
from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, SIGNAL_DATA_UPDATED
from .core.fan import Step
from .core.matcher import Match
from .core.models import Binding, Device, ModelError
from .core.onoff import OnOffPlan, OnOffRemote
from .hub import SIGNAL_REMOTE_PRESSED
from .runtime import ClickerConfigEntry, ClickerRuntime

_LOGGER = logging.getLogger(__name__)


class ClickerEntity[RemoteT](RestoreEntity):
    """An entity driven by one binding of a Clicker device.

    ``RemoteT`` is the platform's rules object, built from the binding's roles
    (``FanRemote``, ``OnOffRemote``). State is assumed (RF remotes don't
    report back) and restored across restarts; the device, binding and
    remote are swapped in place when the data changes.
    """

    _attr_assumed_state = True
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        runtime: ClickerRuntime,
        device: Device,
        binding: Binding,
        remote: RemoteT,
        key: str | None = None,
    ) -> None:
        self._runtime = runtime
        self.device = device
        self.binding = binding
        self.remote = remote
        self.key = key  # which of the binding's entities this is, when it has several
        self._attr_unique_id = binding.id if key is None else f"{binding.id}:{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id)}, name=device.name, model="RF remote"
        )
        self._set_name()

    @staticmethod
    def remote_for(binding: Binding) -> RemoteT:
        """Build the rules from a binding's roles; raise ModelError if unusable."""
        raise NotImplementedError

    @classmethod
    def split(cls, binding: Binding) -> dict[str | None, RemoteT]:
        """Return the entities a binding makes, by key: usually one, keyed None."""
        return {None: cls.remote_for(binding)}

    def _set_name(self) -> None:
        # The device's main entity takes the device name, as HA recommends.
        same = self.binding.name.casefold() == self.device.name.casefold()
        self._attr_name = None if same else self.binding.name

    def update_binding(self, device: Device, binding: Binding, remote: RemoteT) -> None:
        """Take the latest stored device and binding; the assumed state is kept."""
        self.device, self.binding, self.remote = device, binding, remote
        self._set_name()
        if self.hass is not None:
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        radio = self._runtime.data.radio(self.device.radio_id)
        return (
            radio is not None and radio.transmitter is not None and radio.id in self._runtime.links
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._runtime.entities[self.entity_id] = self
        self.async_on_remove(lambda: self._runtime.entities.pop(self.entity_id, None))
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_REMOTE_PRESSED, self._on_press)
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_DATA_UPDATED, self.async_write_ha_state)
        )

    @callback
    def _on_press(self, match: Match, _at: float, context: Context) -> None:
        if match.device_id != self.device.id:
            return
        roles = [role for role, cid in self.binding.roles.items() if cid == match.command_id]
        if roles and self.pressed(roles[0]):
            self.async_set_context(context)
            self.async_write_ha_state()

    def pressed(self, role: str) -> bool:
        """Apply a remote press of a bound button; return whether the state changed."""
        raise NotImplementedError

    async def async_send_steps(self, steps: list[Step]) -> None:
        """Send the commands bound to these roles, in order, through the device's radio."""
        sender = self._runtime.sender
        assert sender is not None
        radio = sender.radio_of(self.device)
        for step in steps:
            command = self.device.command(self.binding.roles[step.role])
            if command is None:
                raise ServiceValidationError(f"{self.binding.name}: {step.role} has no command")
            await sender.async_send(
                radio, command, context=self._context, pause_after_s=step.pause_after_s
            )

    async def async_set_assumed_state(self, **fields: Any) -> None:
        """Correct the assumed state without sending anything."""
        raise NotImplementedError


@callback
def async_track_bindings[EntityT: ClickerEntity[Any]](
    hass: HomeAssistant,
    entry: ClickerConfigEntry,
    platform: str,
    entity_class: type[EntityT],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Keep the entities of every ``platform`` binding, as bindings come and go."""
    runtime = entry.runtime_data
    entities: dict[tuple[str, str | None], EntityT] = {}
    refused: set[str] = set()  # bindings already reported as unusable

    @callback
    def _sync() -> None:
        usable: dict[tuple[str, str | None], tuple[Device, Binding, Any]] = {}
        for device in runtime.data.devices:
            for binding in device.bindings:
                if binding.platform != platform:
                    continue
                try:
                    for key, remote in entity_class.split(binding).items():
                        usable[binding.id, key] = (device, binding, remote)
                except ModelError as err:
                    if binding.id not in refused:
                        _LOGGER.warning(
                            "%s / %s: not a usable %s: %s", device.name, binding.name, platform, err
                        )
                    refused.add(binding.id)
        refused.intersection_update(b.id for d in runtime.data.devices for b in d.bindings)
        refused.difference_update(binding_id for binding_id, _key in usable)

        ent_reg = er.async_get(hass)
        for gone_key in set(entities) - set(usable):
            gone = entities.pop(gone_key)
            if gone.registry_entry is not None:
                ent_reg.async_remove(gone.entity_id)
            else:
                hass.async_create_task(gone.async_remove(force_remove=True))
        new: list[EntityT] = []
        for (binding_id, key), (device, binding, remote) in usable.items():
            if (entity := entities.get((binding_id, key))) is not None:
                entity.update_binding(device, binding, remote)
            else:
                entity = entity_class(runtime, device, binding, remote, key)
                entities[binding_id, key] = entity
                new.append(entity)
        if new:
            async_add_entities(new)

    _sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_DATA_UPDATED, _sync))


def unsupported(entity: ClickerEntity[Any], fields: dict[str, Any]) -> None:
    """Refuse assumed-state fields an entity doesn't have."""
    if fields:
        raise ServiceValidationError(
            f"{entity.entity_id} has no {', '.join(sorted(fields))} to set"
        )


class OnOffEntity(ClickerEntity[OnOffRemote]):
    """An on/off device (light, switch) driven by its remote's buttons."""

    _on = False

    @staticmethod
    def remote_for(binding: Binding) -> OnOffRemote:
        return OnOffRemote(binding.roles)

    @property
    def is_on(self) -> bool:
        return self._on

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._on = last.state == STATE_ON

    def pressed(self, role: str) -> bool:
        old, self._on = self._on, self.remote.pressed(self._on, role)
        return self._on != old

    async def _run(self, plan: OnOffPlan) -> None:
        """Show the new state, send; undo the state if sending fails."""
        steps, new = plan
        old, self._on = self._on, new
        self.async_write_ha_state()
        try:
            await self.async_send_steps(steps)
        except Exception:
            self._on = old
            self.async_write_ha_state()
            raise

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._run(self.remote.set(self._on, True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._run(self.remote.set(self._on, False))

    async def async_set_assumed_state(self, is_on: bool | None = None, **other: Any) -> None:
        """Correct the assumed state without sending anything (after a missed press)."""
        unsupported(self, other)
        if is_on is not None:
            self._on = is_on
        self.async_write_ha_state()
