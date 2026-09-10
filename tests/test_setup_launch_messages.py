"""Every text channel gets launch-mode content — docs/DECISIONS.md ADR-059.

A regression guard: if bot/constants.py grows a new text channel without
bot/cogs/setup.py's _launch_messages() being updated to match, /setup run
mode:launch would silently leave it empty again.
"""

from __future__ import annotations

from bot.cogs.setup import _LAUNCH_MESSAGE_CHANNELS, _launch_messages
from bot.constants import CATEGORIES


def _all_text_channel_keys() -> set[str]:
    return {
        channel.logical_key
        for category in CATEGORIES
        for channel in category.channels
        if channel.kind == "text"
    }


def test_every_text_channel_has_launch_content() -> None:
    text_keys = _all_text_channel_keys()
    messages = _launch_messages()
    assert text_keys == set(messages.keys())


def test_launch_message_channels_tuple_matches_the_dict() -> None:
    messages = _launch_messages()
    assert set(_LAUNCH_MESSAGE_CHANNELS) == set(messages.keys())


def test_every_launch_embed_has_a_title() -> None:
    """_already_posted's idempotency check matches on embed.title — a
    titleless embed would get re-posted forever on every /setup run.
    """
    for entries in _launch_messages().values():
        for embed, _view in entries:
            assert embed.title
