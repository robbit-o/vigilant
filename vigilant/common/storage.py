import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Final

from google.cloud import storage

from vigilant.common.values import settings, IOResources

DEFAULT_PATH: Final[str] = "."
VIDEO_CONTENT_TYPE: Final[str] = "video/webm"


class Storage(ABC):
    @abstractmethod
    def save_image(self, data: bytes, path: str) -> str: ...

    @abstractmethod
    def save_video(self, source: str, path: str) -> str: ...


class LocalStorage(Storage):
    def save_image(self, data: bytes, path: str = DEFAULT_PATH) -> str:
        """Save image in local file system

        Args:
            data (bytes): Image data
            path (str, optional): Path where to save the image. Defaults to DEFAULT_PATH.

        Returns:
            str: Path where the image was saved
        """
        image_path = Path(path)
        image_path.parents[0].mkdir(parents=True, exist_ok=True)

        image_path.write_bytes(data)
        return image_path.as_posix()

    def save_video(self, source: str, path: str = DEFAULT_PATH) -> str:
        """Move video file into the local file system

        Args:
            source (str): Path of the recorded video file
            path (str, optional): Path where to save the video. Defaults to DEFAULT_PATH.

        Returns:
            str: Path where the video was saved
        """
        video_path = Path(path)
        video_path.parents[0].mkdir(parents=True, exist_ok=True)

        shutil.move(source, video_path)
        return video_path.as_posix()


class GoogleCloudStorage(Storage):
    def __init__(self):
        storage_client = storage.Client()
        self.bucket: storage.Bucket = storage_client.bucket(settings.BUCKET_NAME)

    def save_image(self, data: bytes, path: str = "") -> str:
        """Save image in GCS bucket

        Args:
            data (bytes): Image data
            path (str, optional): Path where to save the image. Defaults to "".

        Returns:
            str: URI of the image as GCS object
        """
        blob: storage.Blob = self.bucket.blob(path)
        blob.upload_from_string(data, content_type="image/png")

        return self._build_object_uri(path)

    def save_video(self, source: str, path: str = "") -> str:
        """Upload video file to GCS bucket

        Args:
            source (str): Path of the recorded video file
            path (str, optional): Path where to save the video. Defaults to "".

        Returns:
            str: URI of the video as GCS object
        """
        blob: storage.Blob = self.bucket.blob(path)
        blob.upload_from_filename(source, content_type=VIDEO_CONTENT_TYPE)

        return self._build_object_uri(path)

    @staticmethod
    def _build_object_uri(object_path: str) -> str:
        GCS_BASE_URL: Final[str] = "https://storage.cloud.google.com"

        return f"{GCS_BASE_URL}/{settings.BUCKET_NAME}/{object_path}"


def clear_resources() -> None:
    """Setup resources directory for data persistence"""
    shutil.rmtree(IOResources.DATA_PATH, ignore_errors=True)
    shutil.rmtree(IOResources.OUTPUT_PATH, ignore_errors=True)

    IOResources.DATA_PATH.mkdir(parents=True, exist_ok=True)
    IOResources.OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
