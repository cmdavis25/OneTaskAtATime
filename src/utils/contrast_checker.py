"""
WCAG 2.1 Color Contrast Checker for OneTaskAtATime.

Verifies color combinations meet WCAG AA standards (4.5:1 ratio).
"""

from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class ColorPair:
    """Represents a color pair to check."""
    name: str
    foreground_rgb: Tuple[int, int, int]
    background_rgb: Tuple[int, int, int]
    context: str  # "normal_text", "large_text", "ui_component"


@dataclass
class ContrastResult:
    """Result of a contrast check."""
    pair: ColorPair
    ratio: float
    required_ratio: float
    passes: bool


class ContrastChecker:
    """
    Utility for checking WCAG color contrast compliance.

    WCAG 2.1 AA Requirements:
    - Normal text: 4.5:1 minimum
    - Large text (18pt+): 3:1 minimum
    - UI components: 3:1 minimum
    """

    # Standard color pairs to check for the application
    STANDARD_PAIRS = [
        # Light theme
        ColorPair("Light theme - Normal text", (26, 26, 26), (255, 255, 255), "normal_text"),
        ColorPair("Light theme - Button text", (26, 26, 26), (245, 245, 245), "normal_text"),
        ColorPair("Light theme - Disabled text", (117, 117, 117), (255, 255, 255), "normal_text"),
        ColorPair("Light theme - Link text", (0, 102, 204), (255, 255, 255), "normal_text"),
        ColorPair("Light theme - Error text", (204, 0, 0), (255, 255, 255), "normal_text"),
        ColorPair("Light theme - Success text", (0, 153, 51), (255, 255, 255), "normal_text"),

        # Dark theme
        ColorPair("Dark theme - Normal text", (240, 240, 240), (43, 43, 43), "normal_text"),
        ColorPair("Dark theme - Button text", (240, 240, 240), (60, 63, 65), "normal_text"),
        ColorPair("Dark theme - Disabled text", (117, 117, 117), (43, 43, 43), "normal_text"),
        ColorPair("Dark theme - Link text", (85, 170, 255), (43, 43, 43), "normal_text"),
        ColorPair("Dark theme - Error text", (255, 102, 102), (43, 43, 43), "normal_text"),
        ColorPair("Dark theme - Success text", (102, 204, 102), (43, 43, 43), "normal_text"),
    ]

    @staticmethod
    def calculate_contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
        """
        Calculate WCAG contrast ratio between two RGB colors.

        Args:
            rgb1: First color as (r, g, b) tuple (0-255)
            rgb2: Second color as (r, g, b) tuple (0-255)

        Returns:
            Contrast ratio as float (1.0 to 21.0)
        """
        l1 = ContrastChecker._relative_luminance(rgb1)
        l2 = ContrastChecker._relative_luminance(rgb2)

        lighter = max(l1, l2)
        darker = min(l1, l2)

        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def _relative_luminance(rgb: Tuple[int, int, int]) -> float:
        """
        Calculate relative luminance of RGB color per WCAG formula.

        Args:
            rgb: Color as (r, g, b) tuple (0-255)

        Returns:
            Relative luminance (0-1)
        """
        # Convert to 0-1 range
        r, g, b = [x / 255.0 for x in rgb]

        # Apply gamma correction
        def gamma_correct(channel: float) -> float:
            if channel <= 0.03928:
                return channel / 12.92
            else:
                return ((channel + 0.055) / 1.055) ** 2.4

        r = gamma_correct(r)
        g = gamma_correct(g)
        b = gamma_correct(b)

        # Calculate luminance using WCAG formula
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    @staticmethod
    def get_required_ratio(context: str) -> float:
        """
        Get required contrast ratio for context.

        Args:
            context: Context type ("normal_text", "large_text", "ui_component")

        Returns:
            Required contrast ratio
        """
        ratios = {
            "normal_text": 4.5,
            "large_text": 3.0,
            "ui_component": 3.0
        }
        return ratios.get(context, 4.5)

    @staticmethod
    def check_pair(pair: ColorPair) -> ContrastResult:
        """
        Check if a color pair meets WCAG requirements.

        Args:
            pair: ColorPair to check

        Returns:
            ContrastResult with details
        """
        ratio = ContrastChecker.calculate_contrast_ratio(
            pair.foreground_rgb,
            pair.background_rgb
        )

        required = ContrastChecker.get_required_ratio(pair.context)
        passes = ratio >= required

        return ContrastResult(
            pair=pair,
            ratio=ratio,
            required_ratio=required,
            passes=passes
        )

    @staticmethod
    def check_all_standard_pairs() -> List[ContrastResult]:
        """
        Check all standard application color pairs.

        Returns:
            List of ContrastResult objects
        """
        results = []
        for pair in ContrastChecker.STANDARD_PAIRS:
            result = ContrastChecker.check_pair(pair)
            results.append(result)

        return results

    @staticmethod
    def rgb_from_hex(hex_color: str) -> Tuple[int, int, int]:
        """
        Convert hex color to RGB tuple.

        Args:
            hex_color: Hex color string (e.g., "#1A1A1A" or "1A1A1A")

        Returns:
            RGB tuple (r, g, b)
        """
        # Remove # if present
        hex_color = hex_color.lstrip('#')

        # Convert to RGB
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )

    @staticmethod
    def print_results(results: List[ContrastResult]):
        """
        Print contrast check results in formatted table.

        Args:
            results: List of ContrastResult objects
        """
        print("\nWCAG 2.1 AA Contrast Compliance Check")
        print("=" * 80)

        failing_count = 0

        for result in results:
            status = "✓ PASS" if result.passes else "✗ FAIL"
            if not result.passes:
                failing_count += 1

            print(f"\n{status} - {result.pair.name}")
            print(f"  Ratio: {result.ratio:.2f}:1 (Required: {result.required_ratio}:1)")
            print(f"  Foreground: RGB{result.pair.foreground_rgb}")
            print(f"  Background: RGB{result.pair.background_rgb}")

        print("\n" + "=" * 80)
        passing_count = len(results) - failing_count
        print(f"Results: {passing_count}/{len(results)} pairs pass WCAG AA")

        if failing_count > 0:
            print(f"⚠ {failing_count} pair(s) need adjustment")
        else:
            print("✓ All color pairs meet WCAG AA standards!")


if __name__ == "__main__":
    # Run contrast check when module is executed directly
    results = ContrastChecker.check_all_standard_pairs()
    ContrastChecker.print_results(results)
