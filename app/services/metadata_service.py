from ..repositories import MetadataRepository
from ..models import MetadataState, MetadataDocument


class MetadataService:
    """
    Service whihc provides methods to retrieve and create metadata records,
    as well as utility functions for URL normalization.
    """

    def __init__(self, repo: MetadataRepository):
        self.repo = repo

    async def get_metadata(self, url: str):
        """
        Queries the repository for an existing metadata record associated with the URL.
        
        Args:
            url (str): The URL for which to retrieve metadata.
        Returns:
            tuple: A tuple containing:
                - MetadataState: The state indicating if metadata was found or accepted.
                - dict or None: The metadata record if found, otherwise None.
        """
        record = await self.repo.get_url_metadata(url)
        if not record:
            return MetadataState.ACCEPTED, None

        return MetadataState.FOUND, record

    async def create_metadata(self, url: str):
        """
        Creates a new metadata document and stores it in the repository.
        Returns a DUPLICATE state if a record with the same URL already exists.
        
        Args:
            url (str): The URL for which to create metadata.
        Returns:
            tuple: A tuple containing:
                - MetadataState: The state indicating if creation was successful or if it's a duplicate.
                - dict or None: A dictionary with the created record (including 'id' and url) if successful, otherwise None.
        """
        record = MetadataDocument(url=url).model_dump()
        _id = await self.repo.create_url_metadata(record)
        if _id is None:  # duplicate record
            return MetadataState.DUPLICATE, None

        return MetadataState.ACCEPTED, {"id": _id, **record}

    def remove_trailing_slash_to_url(self, url: str) -> str:
        return url.rstrip("/")
