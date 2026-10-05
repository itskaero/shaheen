"""Paginated /help (docs/DECISIONS.md ADR-121)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.content.help_embeds import HELP_SECTIONS, build_help_page, help_pages, is_staff_section
from bot.views.help import HelpPaginator

_MAX_FIELD_VALUE = 1024
_MAX_DESCRIPTION = 4096
_MAX_EMBED_TOTAL = 6000


def test_members_never_see_staff_only_pages() -> None:
    member_pages = help_pages(staff=False)
    staff_pages = help_pages(staff=True)
    assert member_pages[0] is None and staff_pages[0] is None  # the overview comes first
    assert not any(p is not None and is_staff_section(p) for p in member_pages)
    assert len(staff_pages) == 1 + len(HELP_SECTIONS)
    assert any(p is not None and p.key == "staff_teams" for p in staff_pages)


def test_every_page_fits_discord_limits_and_says_where_it_is() -> None:
    pages = help_pages(staff=True)
    for i in range(len(pages)):
        embed = build_help_page(pages, i)
        assert embed.footer.text is not None
        assert embed.footer.text.startswith(f"Page {i + 1} of {len(pages)}")
        assert len(embed.description or "") <= _MAX_DESCRIPTION
        assert all(len(f.value or "") <= _MAX_FIELD_VALUE for f in embed.fields)
        assert len(embed) <= _MAX_EMBED_TOTAL


def test_overview_lists_every_category_it_pages_through() -> None:
    pages = help_pages(staff=False)
    overview = build_help_page(pages, 0)
    titles = [field.name.split(" · ")[0] for field in overview.fields]
    assert titles == [p.title for p in pages[1:] if p is not None]


def _interaction(user_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        response=SimpleNamespace(edit_message=AsyncMock(), send_message=AsyncMock()),
    )


async def test_buttons_page_and_stop_at_the_ends() -> None:
    pages = help_pages(staff=False)
    view = HelpPaginator(pages, author_id=7)
    assert view.previous.disabled and not view.next.disabled
    assert view.counter.label == f"1 / {len(pages)}"

    click = _interaction(7)
    await view.show(click, 1)  # type: ignore[arg-type]
    assert view.index == 1 and not view.previous.disabled
    click.response.edit_message.assert_awaited_once()

    await view.show(_interaction(7), 999)  # type: ignore[arg-type]
    assert view.index == len(pages) - 1 and view.next.disabled


async def test_only_the_member_who_asked_can_turn_pages() -> None:
    view = HelpPaginator(help_pages(staff=False), author_id=7)
    stranger = _interaction(8)
    assert await view.interaction_check(stranger) is False  # type: ignore[arg-type]
    stranger.response.send_message.assert_awaited_once()
    assert await view.interaction_check(_interaction(7)) is True  # type: ignore[arg-type]


async def test_opens_on_the_requested_category_and_the_menu_follows() -> None:
    pages = help_pages(staff=False)
    start = next(i for i, p in enumerate(pages) if p is not None and p.key == "play")
    view = HelpPaginator(pages, author_id=7, start=start)
    assert view.embed().title == pages[start].title  # type: ignore[union-attr]
    defaults = [option.value for option in view.menu.options if option.default]
    assert defaults == [str(start)]
