from __future__ import annotations

from typing import Any

import requests
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_ENABLE_LATEST_MESSAGE,
    DEFAULT_HOST,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_ENABLE_LATEST_MESSAGE,
    MIN_REFRESH_INTERVAL,
    MAX_REFRESH_INTERVAL,
    VALIDATION_NODES,
)

_LOGGER = logging.getLogger(__name__)


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class AlreadyLoggedIn(Exception):
    """Error to indicate another session is active."""


class LoginThrottled(Exception):
    """Error to indicate login has been throttled."""


def _validate_input(client, data: dict[str, Any]) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    result = client.get_device_data(VALIDATION_NODES)
    if not result:
        raw_message = client.last_error or ""
        message = raw_message.lower()
        if "其他地方登录" in raw_message or "already logged in elsewhere" in message:
            raise AlreadyLoggedIn
        if "1分钟后再试" in raw_message or "failed attempts" in message:
            raise LoginThrottled
        if "password" in message or "auth" in message or "用户名或密码错误" in raw_message:
            raise InvalidAuth
        raise CannotConnect

    serial = result.get("SerialNumber") or data[CONF_HOST]
    title = result.get("ModelName") or f"Fiberhome CPE ({data[CONF_HOST]})"
    return {"title": title, "serial": serial}


class FiberhomeCPEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fiberhome CPE."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        client = None

        if user_input is not None:
            try:
                from .api import FiberhomeCPEClient

                client = FiberhomeCPEClient(
                    user_input[CONF_HOST],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                info = await self.hass.async_add_executor_job(
                    _validate_input, client, user_input
                )
            except InvalidAuth:
                errors["base"] = "auth"
            except AlreadyLoggedIn:
                errors["base"] = "already_logged_in"
            except LoginThrottled:
                errors["base"] = "login_throttled"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except requests.RequestException:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["serial"])
                self._abort_if_unique_id_configured()
                self.hass.data.setdefault(DOMAIN, {}).setdefault(
                    "validated_clients", {}
                )[info["serial"]] = client
                return self.async_create_entry(title=info["title"], data=user_input)
            finally:
                if client is not None and errors:
                    await self.hass.async_add_executor_job(client.close)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(
                    CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL
                ): vol.All(int, vol.Range(min=MIN_REFRESH_INTERVAL, max=MAX_REFRESH_INTERVAL)),
                vol.Optional(
                    CONF_ENABLE_LATEST_MESSAGE, default=DEFAULT_ENABLE_LATEST_MESSAGE
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return FiberhomeCPEOptionsFlow(config_entry)


class FiberhomeCPEOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__(config_entry)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        client = None

        if user_input is not None:
            try:
                from .api import FiberhomeCPEClient

                client = FiberhomeCPEClient(
                    user_input[CONF_HOST],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                await self.hass.async_add_executor_job(_validate_input, client, user_input)
            except InvalidAuth:
                errors["base"] = "auth"
            except AlreadyLoggedIn:
                errors["base"] = "already_logged_in"
            except LoginThrottled:
                errors["base"] = "login_throttled"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except requests.RequestException:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error updating options")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)
            finally:
                if client is not None:
                    await self.hass.async_add_executor_job(client.close)

        host_default = self.config_entry.options.get(
            CONF_HOST, self.config_entry.data.get(CONF_HOST, DEFAULT_HOST)
        )
        username_default = self.config_entry.options.get(
            CONF_USERNAME, self.config_entry.data.get(CONF_USERNAME, "")
        )
        password_default = self.config_entry.options.get(
            CONF_PASSWORD, self.config_entry.data.get(CONF_PASSWORD, "")
        )
        refresh_default = self.config_entry.options.get(
            CONF_REFRESH_INTERVAL,
            self.config_entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
        )
        enable_sms_default = self.config_entry.options.get(
            CONF_ENABLE_LATEST_MESSAGE,
            self.config_entry.data.get(
                CONF_ENABLE_LATEST_MESSAGE, DEFAULT_ENABLE_LATEST_MESSAGE
            ),
        )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, 
                    default=host_default
                ): str,
                vol.Required(
                    CONF_USERNAME, 
                    default=username_default
                ): str,
                vol.Required(
                    CONF_PASSWORD, 
                    default=password_default
                ): str,
                vol.Required(
                    CONF_REFRESH_INTERVAL,
                    default=refresh_default,
                ): vol.All(int, vol.Range(min=MIN_REFRESH_INTERVAL, max=MAX_REFRESH_INTERVAL)),
                vol.Optional(
                    CONF_ENABLE_LATEST_MESSAGE,
                    default=enable_sms_default,
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
