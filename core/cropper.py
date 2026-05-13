"""
Auto-cropping engine.
Removes white/black borders from manga pages intelligently.
Prevents over-cropping with configurable minimum size ratios.
"""

import os
from typing import List, Optional, Tuple


class Cropper:
    """
    Intelligent auto-cropping for manga pages.
    Detects and removes uniform borders while preserving content.
    Enforces minimum size ratio to prevent over-cropping.
    """

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self._pil_available = None

    def _check_pil(self) -> bool:
        if self._pil_available is None:
            try:
                from PIL import Image, ImageStat
                self._pil_available = True
            except ImportError:
                self._pil_available = False
                self.logger.warning(
                    "[Cropper] Pillow not installed. Auto-crop disabled."
                )
        return self._pil_available

    def crop_images(self, image_paths: List[str]) -> List[str]:
        """
        Auto-crop a list of images. Modifies files in-place.
        Returns the same list of paths.
        """
        if not self.config.get("auto_crop", True):
            return image_paths

        if not self._check_pil():
            return image_paths

        threshold = self.config.get("crop_threshold", 10)
        min_ratio = self.config.get("crop_min_ratio", 0.70)
        padding = self.config.get("crop_padding", 2)

        cropped_paths = []
        for path in image_paths:
            if not os.path.exists(path):
                cropped_paths.append(path)
                continue
            try:
                result = self._crop_single(path, threshold, min_ratio, padding)
                cropped_paths.append(result or path)
            except Exception as e:
                self.logger.debug(f"[Cropper] Failed: {path} - {e}")
                cropped_paths.append(path)

        return cropped_paths

    def _crop_single(
        self, image_path: str, threshold: int, min_ratio: float, padding: int
    ) -> Optional[str]:
        """Crop a single image. Returns path or None on failure."""
        from PIL import Image, ImageStat

        img = Image.open(image_path)
        original_width, original_height = img.size

        # Skip small images
        if original_width < 100 or original_height < 100:
            img.close()
            return image_path

        # Convert to RGB for analysis
        if img.mode == "RGBA":
            analysis_img = Image.new("RGB", img.size, (255, 255, 255))
            analysis_img.paste(img, mask=img.split()[3])
        elif img.mode != "RGB":
            analysis_img = img.convert("RGB")
        else:
            analysis_img = img

        # Detect border color (sample corners)
        border_color = self._detect_border_color(analysis_img)

        # Find content bounding box
        bbox = self._find_content_bbox(
            analysis_img, border_color, threshold
        )

        if analysis_img is not img:
            analysis_img.close()

        if bbox is None:
            img.close()
            return image_path

        left, top, right, bottom = bbox

        # Add padding
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(original_width, right + padding)
        bottom = min(original_height, bottom + padding)

        crop_width = right - left
        crop_height = bottom - top

        # Check minimum ratio to prevent over-cropping
        width_ratio = crop_width / original_width
        height_ratio = crop_height / original_height

        if width_ratio < min_ratio or height_ratio < min_ratio:
            self.logger.debug(
                f"[Cropper] Skipping {os.path.basename(image_path)}: "
                f"crop too aggressive ({width_ratio:.2f}x, {height_ratio:.2f}x)"
            )
            img.close()
            return image_path

        # Skip if crop is negligible (less than 1% on each side)
        if width_ratio > 0.98 and height_ratio > 0.98:
            img.close()
            return image_path

        # Crop and save
        cropped = img.crop((left, top, right, bottom))
        img.close()

        # Save with same format
        ext = os.path.splitext(image_path)[1].lower()
        save_kwargs = {}
        if ext in (".jpg", ".jpeg"):
            save_kwargs["quality"] = self.config.get("jpeg_quality", 92)
            save_kwargs["optimize"] = True
        elif ext == ".png":
            save_kwargs["optimize"] = True
        elif ext == ".webp":
            save_kwargs["quality"] = self.config.get("webp_quality", 85)

        cropped.save(image_path, **save_kwargs)
        cropped.close()

        return image_path

    def _detect_border_color(self, img) -> Tuple[int, int, int]:
        """
        Detect the border color by sampling the edges of the image.
        Returns (r, g, b) tuple.
        """
        width, height = img.size
        samples = []

        # Sample corners and edges
        sample_size = min(20, width // 10, height // 10)
        if sample_size < 2:
            sample_size = 2

        regions = [
            (0, 0, sample_size, sample_size),  # top-left
            (width - sample_size, 0, width, sample_size),  # top-right
            (0, height - sample_size, sample_size, height),  # bottom-left
            (width - sample_size, height - sample_size, width, height),  # bottom-right
        ]

        from PIL import ImageStat

        for region in regions:
            try:
                crop = img.crop(region)
                stat = ImageStat.Stat(crop)
                samples.append(tuple(int(v) for v in stat.mean[:3]))
                crop.close()
            except Exception:
                continue

        if not samples:
            return (255, 255, 255)

        # Average the samples
        avg_r = sum(s[0] for s in samples) // len(samples)
        avg_g = sum(s[1] for s in samples) // len(samples)
        avg_b = sum(s[2] for s in samples) // len(samples)

        return (avg_r, avg_g, avg_b)

    def _find_content_bbox(
        self, img, border_color: Tuple[int, int, int], threshold: int
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Find the bounding box of non-border content.
        Uses row/column scanning for efficiency.
        Returns (left, top, right, bottom) or None.
        """
        from PIL import Image
        import struct

        width, height = img.size
        pixels = img.load()

        br, bg, bb = border_color

        def is_border_pixel(r, g, b):
            return (
                abs(r - br) <= threshold
                and abs(g - bg) <= threshold
                and abs(b - bb) <= threshold
            )

        def is_border_row(y, sample_step=1):
            count = 0
            total = 0
            for x in range(0, width, sample_step):
                r, g, b = pixels[x, y][:3]
                total += 1
                if is_border_pixel(r, g, b):
                    count += 1
            return count / total > 0.95 if total > 0 else True

        def is_border_col(x, sample_step=1):
            count = 0
            total = 0
            for y in range(0, height, sample_step):
                r, g, b = pixels[x, y][:3]
                total += 1
                if is_border_pixel(r, g, b):
                    count += 1
            return count / total > 0.95 if total > 0 else True

        # Use step size for performance on large images
        step = max(1, min(width, height) // 200)

        # Find top
        top = 0
        for y in range(height):
            if not is_border_row(y, step):
                top = y
                break
        else:
            return None  # Entire image is border

        # Find bottom
        bottom = height
        for y in range(height - 1, top, -1):
            if not is_border_row(y, step):
                bottom = y + 1
                break

        # Find left
        left = 0
        for x in range(width):
            if not is_border_col(x, step):
                left = x
                break

        # Find right
        right = width
        for x in range(width - 1, left, -1):
            if not is_border_col(x, step):
                right = x + 1
                break

        if right <= left or bottom <= top:
            return None

        return (left, top, right, bottom)

    def crop_single_file(self, image_path: str) -> str:
        """Crop a single file, returning the path."""
        if not self._check_pil():
            return image_path

        threshold = self.config.get("crop_threshold", 10)
        min_ratio = self.config.get("crop_min_ratio", 0.70)
        padding = self.config.get("crop_padding", 2)

        result = self._crop_single(image_path, threshold, min_ratio, padding)
        return result or image_path