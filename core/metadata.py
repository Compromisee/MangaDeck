"""
Metadata and cover generation manager.
Handles cover creation, metadata embedding for EPUB/PDF/CBZ.
"""

import os
from typing import Dict, Optional, List


class MetadataManager:
    """
    Manages manga metadata and auto-generates covers
    when none are available from the source.
    """

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self._pil_available = None

    def _check_pil(self) -> bool:
        if self._pil_available is None:
            try:
                from PIL import Image, ImageDraw, ImageFont
                self._pil_available = True
            except ImportError:
                self._pil_available = False
        return self._pil_available

    def generate_cover(
        self,
        title: str,
        output_path: str,
        width: int = 800,
        height: int = 1200,
        first_page_path: str = None,
    ) -> Optional[str]:
        """
        Generate a cover image.
        If first_page_path is provided, uses it as background.
        Otherwise creates a minimal text-based cover.
        Returns path to cover image or None.
        """
        if not self._check_pil():
            return first_page_path

        from PIL import Image, ImageDraw, ImageFont

        try:
            if first_page_path and os.path.exists(first_page_path):
                # Use first page as cover, add title overlay
                img = Image.open(first_page_path)
                img = img.convert("RGB")
                img = img.resize((width, height), Image.LANCZOS)
            else:
                # Create minimal cover
                img = Image.new("RGB", (width, height), (20, 20, 30))

            draw = ImageDraw.Draw(img)

            # Try to load a system font
            font_large = None
            font_small = None
            font_sizes = [48, 36, 24]

            for size in font_sizes:
                try:
                    font_large = ImageFont.truetype(
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                        size,
                    )
                    font_small = ImageFont.truetype(
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        size // 2,
                    )
                    break
                except (IOError, OSError):
                    try:
                        font_large = ImageFont.truetype("arial.ttf", size)
                        font_small = ImageFont.truetype("arial.ttf", size // 2)
                        break
                    except (IOError, OSError):
                        continue

            if not font_large:
                font_large = ImageFont.load_default()
                font_small = font_large

            # Draw semi-transparent overlay at bottom
            overlay_top = height - 200
            for y in range(overlay_top, height):
                alpha = min(200, int((y - overlay_top) / 200 * 200))
                for x in range(width):
                    r, g, b = img.getpixel((x, y))
                    r = int(r * (255 - alpha) / 255)
                    g = int(g * (255 - alpha) / 255)
                    b = int(b * (255 - alpha) / 255)
                    img.putpixel((x, y), (r, g, b))

            # Draw title
            text_y = height - 160
            # Word wrap
            lines = self._wrap_text(title, font_large, width - 40)
            for line in lines[:3]:
                bbox = draw.textbbox((0, 0), line, font=font_large)
                tw = bbox[2] - bbox[0]
                tx = (width - tw) // 2
                draw.text((tx, text_y), line, fill=(255, 255, 255), font=font_large)
                text_y += bbox[3] - bbox[1] + 8

            # Mangadeck watermark
            draw.text(
                (20, height - 30), "Mangadeck",
                fill=(100, 130, 200), font=font_small,
            )

            img.save(output_path, "JPEG", quality=90)
            img.close()
            return output_path

        except Exception as e:
            self.logger.warning(f"[Metadata] Cover generation failed: {e}")
            return first_page_path

    def _wrap_text(self, text, font, max_width):
        """Simple word-wrap for cover text."""
        from PIL import ImageDraw, Image

        dummy = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy)
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        dummy.close()
        return lines

    def build_metadata(
        self,
        title: str,
        authors: List[str] = None,
        genres: List[str] = None,
        description: str = "",
        language: str = "en",
        reading_direction: str = "rtl",
        status: str = "unknown",
        source: str = "",
        chapter_count: int = 0,
        cover_path: str = None,
    ) -> Dict:
        """Build a standardized metadata dictionary."""
        return {
            "title": title,
            "authors": authors or [],
            "genres": genres or [],
            "description": description,
            "language": language,
            "reading_direction": reading_direction,
            "status": status,
            "source": source,
            "chapter_count": chapter_count,
            "cover_path": cover_path,
            "generator": "Mangadeck",
        }

    def get_reading_direction(self, manga_type: str, genres: List[str] = None) -> str:
        """Determine reading direction from manga type and genres."""
        config_dir = self.config.get("reading_direction", "auto")
        if config_dir != "auto":
            return config_dir

        if manga_type in ("manhwa", "manhua"):
            return "vertical"

        if genres:
            genre_lower = [g.lower() for g in genres]
            if "long strip" in genre_lower or "webtoon" in genre_lower:
                return "vertical"

        return "rtl"