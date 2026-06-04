import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.auth.behavior_mimicry import BehaviorMimicry
from src.logger import get_logger

logger = get_logger()


@pytest.fixture
def mimicry():
    return BehaviorMimicry()


@pytest.fixture
def mock_page():
    page = AsyncMock()
    page.mouse = AsyncMock()
    page.keyboard = AsyncMock()
    return page


@pytest.mark.asyncio
@patch("src.auth.behavior_mimicry.asyncio.sleep", new_callable=AsyncMock)
async def test_random_action_delay(mock_sleep, mimicry):
    await mimicry.random_action_delay(logger=logger)
    mock_sleep.assert_called_once()
    args, _ = mock_sleep.call_args
    delay = args[0]
    assert 2.0 <= delay <= 5.0


@pytest.mark.asyncio
@patch("src.auth.behavior_mimicry.asyncio.sleep", new_callable=AsyncMock)
async def test_move_mouse_human_like(mock_sleep, mimicry, mock_page):
    steps = 10
    await mimicry.move_mouse_human_like(mock_page, 0, 0, 100, 100, steps=steps, logger=logger)
    assert mock_page.mouse.move.call_count == steps
    assert mock_sleep.call_count == steps

    # Check the final move is at the destination
    args, _ = mock_page.mouse.move.call_args
    assert args[0] == 100
    assert args[1] == 100


@pytest.mark.asyncio
@patch("src.auth.behavior_mimicry.random.random", return_value=0.01)  # Force stutter
@patch("src.auth.behavior_mimicry.asyncio.sleep", new_callable=AsyncMock)
async def test_type_human_like(mock_sleep, mock_random, mimicry, mock_page):
    text = "hello"
    await mimicry.type_human_like(mock_page, "#input", text, logger=logger)

    assert mock_page.focus.call_count == 1
    assert mock_page.keyboard.type.call_count == len(text)
    assert mock_sleep.call_count == len(text)

    # Check that a stutter delay occurred (delay > 0.3)
    # mock_sleep arguments should show at least one > 0.3
    delays = [call.args[0] for call in mock_sleep.mock_calls]
    assert any(d > 0.3 for d in delays)


@pytest.mark.asyncio
@patch("src.auth.behavior_mimicry.asyncio.sleep", new_callable=AsyncMock)
async def test_scroll_human_like(mock_sleep, mimicry, mock_page):
    await mimicry.scroll_human_like(mock_page, 500, logger=logger)
    assert mock_page.mouse.wheel.call_count > 0
    assert mock_sleep.call_count > 0


@pytest.mark.asyncio
async def test_click_random_offset(mimicry):
    mock_element = AsyncMock()
    mock_element.bounding_box.return_value = {"x": 10, "y": 10, "width": 100, "height": 50}

    await mimicry.click_random_offset(mock_element, logger=logger)

    mock_element.click.assert_called_once()
    kwargs = mock_element.click.call_args.kwargs
    pos = kwargs.get("position")
    assert pos is not None

    # 10% padding of 100w x 50h is 10 and 5.
    # Therefore offset_x should be between 10 and 90, offset_y between 5 and 45
    assert 10 <= pos["x"] <= 90
    assert 5 <= pos["y"] <= 45


@pytest.mark.asyncio
async def test_click_random_offset_no_box(mimicry):
    mock_element = AsyncMock()
    mock_element.bounding_box.return_value = None

    await mimicry.click_random_offset(mock_element, logger=logger)

    mock_element.click.assert_called_once_with()  # Fallback without position
