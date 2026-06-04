"""Human behavior mimicry for Playwright automation."""

import asyncio
import math
import random
from typing import Any, Sequence

from playwright.async_api import ElementHandle, Page

from src.logger import get_logger

# Fallback logger if one is not passed
default_logger = get_logger()


class BehaviorMimicry:
    """Provides methods to simulate human-like interactions in Playwright."""

    @staticmethod
    def _cubic_bezier(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
        """Calculate the coordinate on a cubic bezier curve at time t (0.0 to 1.0)."""
        return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3

    async def move_mouse_human_like(
        self,
        page: Page,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        steps: int = 50,
        logger: Any = default_logger,
    ) -> None:
        """Move the mouse using a Bezier curve instead of a straight line."""
        logger.debug("mouse_move_start", start=(start_x, start_y), end=(end_x, end_y))

        # Random control points to curve the path
        cp1_x = start_x + (end_x - start_x) * random.uniform(0.1, 0.4)
        cp1_y = start_y + (end_y - start_y) * random.uniform(0.1, 0.4) + random.uniform(-100, 100)

        cp2_x = start_x + (end_x - start_x) * random.uniform(0.6, 0.9)
        cp2_y = start_y + (end_y - start_y) * random.uniform(0.6, 0.9) + random.uniform(-100, 100)

        for i in range(1, steps + 1):
            t = i / steps
            x = self._cubic_bezier(t, start_x, cp1_x, cp2_x, end_x)
            y = self._cubic_bezier(t, start_y, cp1_y, cp2_y, end_y)
            await page.mouse.move(x, y)
            # Simulate variable polling rate/processing delay
            await asyncio.sleep(random.uniform(0.005, 0.015))

    async def type_human_like(
        self, page: Page, selector: str, text: str, logger: Any = default_logger
    ) -> None:
        """Type text with variable delays and occasional stutters."""
        logger.debug("typing_start", length=len(text))
        await page.focus(selector)

        for char in text:
            await page.keyboard.type(char)
            # Normal delay
            delay = random.uniform(0.05, 0.20)

            # 5% chance of a longer pause (stutter/thinking)
            if random.random() < 0.05:
                delay += random.uniform(0.3, 0.8)
                logger.debug("typing_stutter_simulated", added_delay=round(delay, 2))

            await asyncio.sleep(delay)

    async def scroll_human_like(
        self, page: Page, distance: int, logger: Any = default_logger
    ) -> None:
        """Scroll down the page with variable speeds and random pauses."""
        logger.debug("scroll_start", distance=distance)
        scrolled = 0

        while scrolled < distance:
            # Scroll chunk between 100 and 400 pixels
            chunk = random.randint(100, 400)
            if scrolled + chunk > distance:
                chunk = distance - scrolled

            await page.mouse.wheel(0, chunk)
            scrolled += chunk

            # Pause between scroll wheel "ticks"
            pause = random.uniform(0.1, 0.5)

            # 10% chance to stop scrolling to "read"
            if random.random() < 0.10:
                pause += random.uniform(1.0, 3.0)
                logger.debug("scroll_reading_pause", duration=round(pause, 2))

            await asyncio.sleep(pause)

    async def click_random_offset(
        self, element: ElementHandle, logger: Any = default_logger
    ) -> None:
        """Click an element at a random offset within its bounding box, not dead center."""
        box = await element.bounding_box()
        if not box:
            logger.warning("click_random_offset_failed", reason="No bounding box")
            await element.click()  # Fallback
            return

        # Add a 10% padding to avoid clicking exactly on the absolute edge
        pad_x = box["width"] * 0.1
        pad_y = box["height"] * 0.1

        offset_x = random.uniform(pad_x, box["width"] - pad_x)
        offset_y = random.uniform(pad_y, box["height"] - pad_y)

        logger.debug(
            "click_random_offset", box=box, offset=(round(offset_x, 1), round(offset_y, 1))
        )
        await element.click(position={"x": offset_x, "y": offset_y})

    async def random_action_delay(self, logger: Any = default_logger) -> None:
        """Insert a random delay between 2 to 5 seconds between major actions."""
        delay = random.uniform(2.0, 5.0)
        logger.debug("major_action_delay", duration=round(delay, 2))
        await asyncio.sleep(delay)
