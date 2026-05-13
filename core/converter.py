"""
Format converter.
Converts downloaded manga images to EPUB, CBZ, PDF, or organized images.
Full Apple Books EPUB compatibility with proper reading direction metadata.
"""

import os
import io
import zipfile
import shutil
import uuid
import time
from typing import Dict, List, Optional
from pathlib import Path


class Converter:
    """
    Converts chapter images into EPUB, CBZ, PDF, or organized image folders.
    Ensures Apple Books compatibility for EPUB output.
    """

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def convert(
        self,
        chapter_images: Dict[float, List[str]],
        title: str,
        output_dir: str,
        output_format: str,
        metadata: Dict = None,
    ) -> str:
        """
        Convert chapter images to the specified format.
        chapter_images: {chapter_number: [image_paths]}
        Returns output file path.
        """
        metadata = metadata or {}
        os.makedirs(output_dir, exist_ok=True)

        fmt = output_format.lower().strip(".")
        safe_title = self._safe_filename(title)

        if fmt == "epub":
            return self._to_epub(chapter_images, safe_title, output_dir, metadata)
        elif fmt == "cbz":
            return self._to_cbz(chapter_images, safe_title, output_dir, metadata)
        elif fmt == "pdf":
            return self._to_pdf(chapter_images, safe_title, output_dir, metadata)
        elif fmt in ("images", "img"):
            return self._to_images(chapter_images, safe_title, output_dir, metadata)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def _to_cbz(
        self, chapter_images, title, output_dir, metadata
    ) -> str:
        """Create CBZ archive."""
        output_path = os.path.join(output_dir, f"{title}.cbz")
        compression = self.config.get("cbz_compression", 0)
        compress_type = (
            zipfile.ZIP_DEFLATED if compression > 0 else zipfile.ZIP_STORED
        )

        with zipfile.ZipFile(output_path, "w", compress_type) as zf:
            # Add ComicInfo.xml
            comic_info = self._generate_comic_info(title, chapter_images, metadata)
            zf.writestr("ComicInfo.xml", comic_info)

            page_num = 0
            for ch_num in sorted(chapter_images.keys()):
                images = chapter_images[ch_num]
                ch_str = (
                    str(int(ch_num)) if ch_num == int(ch_num)
                    else str(ch_num)
                )
                for img_path in images:
                    if not os.path.exists(img_path):
                        continue
                    ext = os.path.splitext(img_path)[1]
                    archive_name = f"Ch_{ch_str.zfill(4)}/{page_num:05d}{ext}"
                    zf.write(img_path, archive_name)
                    page_num += 1

        self.logger.info(f"[Converter] CBZ created: {output_path}")
        return output_path

    def _generate_comic_info(self, title, chapter_images, metadata) -> str:
        """Generate ComicInfo.xml for CBZ."""
        total_pages = sum(len(imgs) for imgs in chapter_images.values())
        direction = metadata.get("reading_direction", "rtl")
        manga_val = "YesAndRightToLeft" if direction == "rtl" else "Yes"

        xml = f"""<?xml version="1.0" encoding="utf-8"?>
<ComicInfo xmlns:xsd="http://www.w3.org/2001/XMLSchema"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Title>{self._xml_escape(title)}</Title>
  <PageCount>{total_pages}</PageCount>
  <Manga>{manga_val}</Manga>
  <LanguageISO>{metadata.get('language', 'en')}</LanguageISO>
</ComicInfo>"""
        return xml

    def _to_epub(
        self, chapter_images, title, output_dir, metadata
    ) -> str:
        """
        Create EPUB 3.0 with full Apple Books compatibility.
        Proper reading direction, fixed layout, cover page.
        """
        output_path = os.path.join(output_dir, f"{title}.epub")
        book_id = str(uuid.uuid4())
        direction = metadata.get("reading_direction", "rtl")
        language = metadata.get("language", "en")
        vertical = direction == "vertical" or self.config.get("epub_vertical_mode", False)
        apple_compat = self.config.get("epub_apple_books_compat", True)

        page_width = self.config.get("epub_page_width", 800)
        page_height = self.config.get("epub_page_height", 1200)

        # Determine page progression direction
        if direction == "rtl":
            ppd = "rtl"
        elif direction == "ltr" or vertical:
            ppd = "ltr"
        else:
            ppd = "rtl"

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # mimetype must be first and uncompressed
            zf.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)

            # META-INF/container.xml
            container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
            zf.writestr("META-INF/container.xml", container_xml)

            # Apple Books display options
            if apple_compat:
                apple_display = """<?xml version="1.0" encoding="UTF-8"?>
<display_options>
  <platform name="*">
    <option name="fixed-layout">true</option>
    <option name="open-to-spread">false</option>
    <option name="orientation-lock">portrait</option>
  </platform>
</display_options>"""
                zf.writestr(
                    "META-INF/com.apple.ibooks.display-options.xml",
                    apple_display,
                )

            # Collect all pages
            all_pages = []
            page_counter = 0
            for ch_num in sorted(chapter_images.keys()):
                images = chapter_images[ch_num]
                for img_path in images:
                    if not os.path.exists(img_path):
                        continue
                    ext = os.path.splitext(img_path)[1].lower()
                    media_type = {
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".png": "image/png",
                        ".webp": "image/webp",
                        ".gif": "image/gif",
                    }.get(ext, "image/jpeg")

                    img_filename = f"img_{page_counter:05d}{ext}"
                    xhtml_filename = f"page_{page_counter:05d}.xhtml"
                    img_archive = f"OEBPS/images/{img_filename}"

                    zf.write(img_path, img_archive)

                    all_pages.append({
                        "img_filename": img_filename,
                        "xhtml_filename": xhtml_filename,
                        "media_type": media_type,
                        "page_num": page_counter,
                        "chapter": ch_num,
                    })
                    page_counter += 1

            if not all_pages:
                raise Exception("No images to include in EPUB")

            # Generate cover
            cover_page = all_pages[0]
            if self.config.get("epub_generate_cover", True) and metadata.get("cover_path"):
                cover_path = metadata["cover_path"]
                if os.path.exists(cover_path):
                    ext = os.path.splitext(cover_path)[1].lower()
                    zf.write(cover_path, f"OEBPS/images/cover{ext}")

            # XHTML pages
            for page in all_pages:
                xhtml = self._generate_epub_page(
                    page, page_width, page_height, vertical
                )
                zf.writestr(f"OEBPS/{page['xhtml_filename']}", xhtml)

            # CSS
            css = self._generate_epub_css(page_width, page_height, vertical)
            zf.writestr("OEBPS/style.css", css)

            # content.opf
            opf = self._generate_opf(
                book_id, title, language, ppd,
                all_pages, page_width, page_height, apple_compat,
            )
            zf.writestr("OEBPS/content.opf", opf)

            # toc.ncx
            ncx = self._generate_ncx(book_id, title, chapter_images, all_pages)
            zf.writestr("OEBPS/toc.ncx", ncx)

            # nav.xhtml
            nav = self._generate_nav(title, chapter_images, all_pages)
            zf.writestr("OEBPS/nav.xhtml", nav)

        self.logger.info(f"[Converter] EPUB created: {output_path}")
        return output_path

    def _generate_epub_page(self, page, width, height, vertical) -> str:
        """Generate XHTML page for a single image."""
        img_src = f"images/{page['img_filename']}"

        if vertical:
            body_style = (
                "margin:0; padding:0; text-align:center; "
                "display:flex; justify-content:center; align-items:flex-start;"
            )
            img_style = "max-width:100%; height:auto; display:block;"
        else:
            body_style = (
                "margin:0; padding:0; "
                "display:flex; justify-content:center; align-items:center; "
                f"width:{width}px; height:{height}px;"
            )
            img_style = "max-width:100%; max-height:100%; object-fit:contain;"

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width={width}, height={height}"/>
  <link rel="stylesheet" type="text/css" href="style.css"/>
  <title>Page {page['page_num'] + 1}</title>
</head>
<body style="{body_style}">
  <div class="page-container">
    <img src="{img_src}" alt="Page {page['page_num'] + 1}" style="{img_style}"/>
  </div>
</body>
</html>"""

    def _generate_epub_css(self, width, height, vertical) -> str:
        """Generate CSS for EPUB."""
        if vertical:
            return f"""
@page {{
  margin: 0;
  padding: 0;
}}
body {{
  margin: 0;
  padding: 0;
}}
.page-container {{
  text-align: center;
  width: 100%;
}}
img {{
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0 auto;
}}"""
        else:
            return f"""
@page {{
  width: {width}px;
  height: {height}px;
  margin: 0;
  padding: 0;
}}
body {{
  margin: 0;
  padding: 0;
  width: {width}px;
  height: {height}px;
}}
.page-container {{
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}}
img {{
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}}"""

    def _generate_opf(
        self, book_id, title, language, ppd,
        pages, width, height, apple_compat,
    ) -> str:
        """Generate OPF package document."""
        manifest_items = []
        spine_items = []

        # CSS
        manifest_items.append(
            '    <item id="css" href="style.css" media-type="text/css"/>'
        )

        # Nav
        manifest_items.append(
            '    <item id="nav" href="nav.xhtml" '
            'media-type="application/xhtml+xml" properties="nav"/>'
        )

        # Pages and images
        for page in pages:
            page_id = f"page_{page['page_num']:05d}"
            img_id = f"img_{page['page_num']:05d}"

            manifest_items.append(
                f'    <item id="{page_id}" href="{page["xhtml_filename"]}" '
                f'media-type="application/xhtml+xml"/>'
            )
            manifest_items.append(
                f'    <item id="{img_id}" href="images/{page["img_filename"]}" '
                f'media-type="{page["media_type"]}"/>'
            )
            spine_items.append(
                f'    <itemref idref="{page_id}"/>'
            )

        # Cover image
        if pages:
            manifest_items.append(
                f'    <item id="cover-image" href="images/{pages[0]["img_filename"]}" '
                f'media-type="{pages[0]["media_type"]}" properties="cover-image"/>'
            )

        manifest_str = "\n".join(manifest_items)
        spine_str = "\n".join(spine_items)

        meta_tags = f"""    <meta property="dcterms:modified">{time.strftime('%Y-%m-%dT%H:%M:%SZ')}</meta>
    <meta property="rendition:layout">pre-paginated</meta>
    <meta property="rendition:orientation">portrait</meta>
    <meta property="rendition:spread">none</meta>"""

        if apple_compat:
            meta_tags += """
    <meta name="book-type" content="comic"/>"""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0"
         unique-identifier="bookid" dir="{ppd}"
         prefix="rendition: http://www.idpf.org/vocab/rendition/#">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="bookid">urn:uuid:{book_id}</dc:identifier>
    <dc:title>{self._xml_escape(title)}</dc:title>
    <dc:language>{language}</dc:language>
    <dc:creator>Mangadeck</dc:creator>
{meta_tags}
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
{manifest_str}
  </manifest>
  <spine page-progression-direction="{ppd}" toc="ncx">
{spine_str}
  </spine>
</package>"""

    def _generate_ncx(self, book_id, title, chapter_images, all_pages) -> str:
        """Generate NCX table of contents."""
        nav_points = []
        play_order = 1

        # Group pages by chapter
        chapter_first_page = {}
        for page in all_pages:
            ch = page["chapter"]
            if ch not in chapter_first_page:
                chapter_first_page[ch] = page

        for ch_num in sorted(chapter_first_page.keys()):
            page = chapter_first_page[ch_num]
            ch_str = (
                str(int(ch_num)) if ch_num == int(ch_num)
                else str(ch_num)
            )
            nav_points.append(f"""    <navPoint id="ch_{ch_str}" playOrder="{play_order}">
      <navLabel><text>Chapter {ch_str}</text></navLabel>
      <content src="{page['xhtml_filename']}"/>
    </navPoint>""")
            play_order += 1

        nav_str = "\n".join(nav_points)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:{book_id}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{self._xml_escape(title)}</text></docTitle>
  <navMap>
{nav_str}
  </navMap>
</ncx>"""

    def _generate_nav(self, title, chapter_images, all_pages) -> str:
        """Generate EPUB3 navigation document."""
        nav_items = []
        chapter_first_page = {}
        for page in all_pages:
            ch = page["chapter"]
            if ch not in chapter_first_page:
                chapter_first_page[ch] = page

        for ch_num in sorted(chapter_first_page.keys()):
            page = chapter_first_page[ch_num]
            ch_str = (
                str(int(ch_num)) if ch_num == int(ch_num)
                else str(ch_num)
            )
            nav_items.append(
                f'      <li><a href="{page["xhtml_filename"]}">Chapter {ch_str}</a></li>'
            )

        nav_str = "\n".join(nav_items)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <meta charset="UTF-8"/>
  <title>{self._xml_escape(title)}</title>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
{nav_str}
    </ol>
  </nav>
</body>
</html>"""

    def _to_pdf(
        self, chapter_images, title, output_dir, metadata
    ) -> str:
        """Create PDF from chapter images."""
        output_path = os.path.join(output_dir, f"{title}.pdf")

        try:
            from PIL import Image

            all_image_paths = []
            for ch_num in sorted(chapter_images.keys()):
                all_image_paths.extend(chapter_images[ch_num])

            if not all_image_paths:
                raise Exception("No images for PDF")

            valid_images = []
            for path in all_image_paths:
                if os.path.exists(path):
                    try:
                        img = Image.open(path)
                        if img.mode == "RGBA":
                            bg = Image.new("RGB", img.size, (255, 255, 255))
                            bg.paste(img, mask=img.split()[3])
                            img = bg
                        elif img.mode != "RGB":
                            img = img.convert("RGB")
                        valid_images.append(img)
                    except Exception:
                        continue

            if not valid_images:
                raise Exception("No valid images for PDF")

            # Auto page size or configured
            page_size = self.config.get("pdf_page_size", "auto")
            margin = self.config.get("pdf_margin", 0)

            if page_size == "auto":
                # Use first image dimensions as reference
                first = valid_images[0]

            first_img = valid_images[0]
            remaining = valid_images[1:] if len(valid_images) > 1 else []

            first_img.save(
                output_path, "PDF", save_all=True,
                append_images=remaining,
                resolution=150.0,
            )

            # Close images
            for img in valid_images:
                img.close()

            self.logger.info(f"[Converter] PDF created: {output_path}")
            return output_path

        except ImportError:
            self.logger.error(
                "[Converter] Pillow required for PDF. Install: pip install Pillow"
            )
            raise Exception("Pillow library required for PDF conversion")

    def _to_images(
        self, chapter_images, title, output_dir, metadata
    ) -> str:
        """Organize images into chapter folders."""
        images_output = os.path.join(output_dir, f"{title}_images")
        os.makedirs(images_output, exist_ok=True)

        for ch_num in sorted(chapter_images.keys()):
            ch_str = (
                str(int(ch_num)) if ch_num == int(ch_num)
                else str(ch_num)
            )
            ch_dir = os.path.join(images_output, f"Chapter_{ch_str.zfill(4)}")
            os.makedirs(ch_dir, exist_ok=True)

            for i, img_path in enumerate(chapter_images[ch_num]):
                if os.path.exists(img_path):
                    ext = os.path.splitext(img_path)[1]
                    dst = os.path.join(ch_dir, f"page_{i + 1:04d}{ext}")
                    shutil.copy2(img_path, dst)

        self.logger.info(f"[Converter] Images organized: {images_output}")
        return images_output

    def _safe_filename(self, name: str) -> str:
        import re
        safe = re.sub(r'[<>:"/\\|?*]', '', name)
        safe = safe.strip(". ")
        return safe[:200] if safe else "manga"

    def _xml_escape(self, text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )