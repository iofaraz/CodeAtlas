"""Streaming Stack Exchange XML parsing."""

from collections.abc import Iterator
from typing import BinaryIO

from lxml import etree


def iter_post_rows(source: str | BinaryIO) -> Iterator[dict[str, str]]:
    """Yield row attributes from Posts.xml without retaining the XML tree."""
    try:
        context = etree.iterparse(source, events=("end",), tag="row")
        for _, element in context:
            yield dict(element.attrib)
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]
    except (etree.XMLSyntaxError, OSError) as exc:
        raise ValueError(f"Invalid or unreadable XML input: {exc}") from exc
