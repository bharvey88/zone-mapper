"""
Frontend resource registration and optional Lovelace view seeding.

Bundles `zone-mapper-card.js` from `./www/` and registers it as a static path
plus an extra JS URL so the card is available on every dashboard without the
user needing to install the card repo separately.

Also provides `async_seed_default_view`, which appends a "Zone Mapper" view
with a placeholder card on the default storage-mode dashboard the first time a
config entry is set up. YAML-mode dashboards are never rewritten.

Lovelace internal APIs (``hass.data["lovelace"]``) are not part of HA's public
contract, so the seeding code is wrapped in a broad try/except: if HA ever
changes the shape of these internals, the integration logs a warning and keeps
working without the auto-view.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig

from .const import (
    AUTO_VIEW_ICON,
    AUTO_VIEW_PATH,
    AUTO_VIEW_PLACEHOLDER_LOCATION,
    AUTO_VIEW_TITLE,
    CARD_TYPE,
    DOMAIN,
    FRONTEND_REGISTERED_FLAG,
    FRONTEND_SCRIPT_FILENAME,
    FRONTEND_SCRIPT_URL_FMT,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def _read_integration_version() -> str:
    """Read the integration version from manifest.json for cache-busting URLs."""
    manifest_path = Path(__file__).parent / "manifest.json"
    try:
        with manifest_path.open(encoding="utf-8") as fh:
            return str(json.load(fh).get("version", "0"))
    except (OSError, ValueError) as exc:
        _LOGGER.debug("Zone Mapper: could not read manifest version: %s", exc)
        return "0"


async def async_register_card_resource(hass: HomeAssistant) -> None:
    """
    Serve the bundled card JS and register it as a dashboard-wide resource.

    Idempotent — safe to call across reloads.
    """
    integration_data = hass.data.setdefault(DOMAIN, {})
    if integration_data.get(FRONTEND_REGISTERED_FLAG):
        return

    version = _read_integration_version()
    url = FRONTEND_SCRIPT_URL_FMT.format(version=version)
    script_path = Path(__file__).parent / "www" / FRONTEND_SCRIPT_FILENAME

    if not script_path.is_file():
        _LOGGER.warning(
            "Zone Mapper: bundled card JS missing at %s; skipping resource"
            " registration. Install the zone-mapper-card manually to recover.",
            script_path,
        )
        return

    await hass.http.async_register_static_paths(
        [StaticPathConfig(url, str(script_path), cache_headers=False)]
    )
    add_extra_js_url(hass, url)
    integration_data[FRONTEND_REGISTERED_FLAG] = True
    _LOGGER.info("Zone Mapper: registered bundled card at %s", url)


def _placeholder_view() -> dict[str, Any]:
    """Return a Lovelace view dict containing a single placeholder card."""
    return {
        "title": AUTO_VIEW_TITLE,
        "path": AUTO_VIEW_PATH,
        "icon": AUTO_VIEW_ICON,
        "cards": [
            {
                "type": CARD_TYPE,
                "location": AUTO_VIEW_PLACEHOLDER_LOCATION,
            }
        ],
    }


def _config_contains_card(config: dict[str, Any]) -> bool:
    for view in config.get("views", []) or []:
        for card in view.get("cards", []) or []:
            if isinstance(card, dict) and card.get("type") == CARD_TYPE:
                return True
    return False


def _resolve_default_dashboard(hass: HomeAssistant) -> object | None:
    """Return the default Lovelace dashboard object, or None if unavailable."""
    lovelace_data = hass.data.get("lovelace")
    if lovelace_data is None:
        _LOGGER.debug("Zone Mapper: lovelace data not available yet.")
        return None
    dashboards = getattr(lovelace_data, "dashboards", None)
    if not isinstance(dashboards, dict):
        _LOGGER.warning(
            "Zone Mapper: unexpected lovelace dashboards shape; skipping"
            " auto-view seeding."
        )
        return None
    return dashboards.get(None) or dashboards.get("lovelace")


async def async_seed_default_view(hass: HomeAssistant) -> bool:  # noqa: PLR0911
    """
    Append a Zone Mapper view to the default dashboard if one isn't present.

    Returns True when the config entry should be marked as seeded (either the
    view was added, an existing view already contains the card, the dashboard
    is YAML-mode, or an unrecoverable error occurred and we want to stop
    retrying). Returns False only when the environment isn't ready yet and we
    should try again on the next setup.
    """
    try:
        default = _resolve_default_dashboard(hass)
        if default is None:
            return False

        mode = getattr(default, "mode", None)
        if mode == "yaml":
            _LOGGER.info(
                "Zone Mapper: default dashboard is YAML-mode; not rewriting it."
                " Add this card manually to any view:\n"
                "  - type: %s\n    location: %s",
                CARD_TYPE,
                AUTO_VIEW_PLACEHOLDER_LOCATION,
            )
            return True

        async_load = getattr(default, "async_load", None)
        async_save = getattr(default, "async_save", None)
        if async_load is None or async_save is None:
            _LOGGER.warning(
                "Zone Mapper: default dashboard missing load/save hooks;"
                " skipping auto-view seeding."
            )
            return True

        config = await async_load(force=False)
        if not isinstance(config, dict):
            _LOGGER.debug(
                "Zone Mapper: dashboard config not a dict (%s); skipping seed.",
                type(config).__name__,
            )
            return True

        if _config_contains_card(config):
            _LOGGER.debug("Zone Mapper: default dashboard already contains the card.")
            return True

        views = list(config.get("views") or [])
        views.append(_placeholder_view())
        await async_save({**config, "views": views})
    except Exception:  # noqa: BLE001
        _LOGGER.warning(
            "Zone Mapper: could not seed default Lovelace view; continuing"
            " without auto-view. Add `type: %s` manually to any dashboard.",
            CARD_TYPE,
            exc_info=True,
        )
        return True
    else:
        _LOGGER.info(
            "Zone Mapper: added '%s' view to the default dashboard. Delete it"
            " from the dashboard editor if you prefer to lay out the card"
            " yourself; it won't be re-added.",
            AUTO_VIEW_TITLE,
        )
        return True
