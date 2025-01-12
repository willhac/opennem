from typing import Optional

from opennem.api.schema import ApiBase


class Photo(ApiBase):
    hash_id: str
    width: int
    height: int
    photo_url: Optional[str]

    license_type: Optional[str]
    license_link: Optional[str]
    author: Optional[str]
    author_link: Optional[str]

    is_primary: Optional[bool]
    order: Optional[int]
