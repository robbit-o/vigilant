import tempfile
from pathlib import Path
from unittest import mock

import pytest

from vigilant.common.storage import (
    settings,
    GoogleCloudStorage,
    LocalStorage,
    clear_resources,
)


def test_local_storage() -> None:
    _, image_path = tempfile.mkstemp(suffix=".png")
    image_data: bytes = b"rgb_data"

    storage = LocalStorage()
    saved_path: str = storage.save_image(image_data, image_path)

    image: bytes = Path(image_path).read_bytes()

    assert (
        image_path == saved_path and Path(image_path).exists() and image == image_data
    )


def test_local_storage_video(tmp_path: Path) -> None:
    video_data: bytes = b"webm_data"
    recorded_path: Path = tmp_path / "recorded.webm"
    recorded_path.write_bytes(video_data)

    video_path: Path = tmp_path / "screenshots" / "browser-20250101000000.webm"
    saved_path: str = LocalStorage().save_video(str(recorded_path), str(video_path))

    assert (
        saved_path == video_path.as_posix()
        and not recorded_path.exists()
        and video_path.read_bytes() == video_data
    )


def test_local_storage_video_without_parent(tmp_path: Path) -> None:
    recorded_path: Path = tmp_path / "recorded.webm"
    recorded_path.write_bytes(b"webm_data")

    video_path: Path = tmp_path / "browser.webm"
    LocalStorage().save_video(str(recorded_path), str(video_path))

    assert video_path.read_bytes() == b"webm_data"


class TestGoogleCloudStorage:
    @mock.patch("vigilant.common.storage.storage")
    def test_gcs_storage(
        self, gcs_storage: mock.MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, image_path = tempfile.mkstemp(suffix=".png")
        image_data: bytes = b"rgb_data"

        mock_bucket = mock.MagicMock()
        mock_bucket.blob.return_value.upload_from_string = lambda *args, **kwargs: Path(
            image_path
        ).write_bytes(image_data)
        mock_gcs_client = gcs_storage.Client.return_value
        mock_gcs_client.bucket.return_value = mock_bucket

        monkeypatch.setattr(
            "vigilant.common.storage.GoogleCloudStorage._build_object_uri",
            lambda *_: image_path,
        )

        storage = GoogleCloudStorage()
        saved_path: str = storage.save_image(image_data, image_path)

        image: bytes = Path(image_path).read_bytes()

        assert (
            image_path == saved_path
            and Path(image_path).exists()
            and image == image_data
        )

    def test_build_object_uri(_, monkeypatch: pytest.MonkeyPatch) -> None:
        bucket_name: str = "app_bucket"
        file_path: str = "path/path/image.png"

        monkeypatch.setattr(settings, "BUCKET_NAME", bucket_name)

        object_uri: str = GoogleCloudStorage._build_object_uri(file_path)

        assert f"{bucket_name}/{file_path}" in object_uri

    @mock.patch("vigilant.common.storage.storage")
    def test_gcs_storage_video(
        self, gcs_storage: mock.MagicMock, tmp_path: Path
    ) -> None:
        recorded_path: Path = tmp_path / "recorded.webm"
        recorded_path.write_bytes(b"webm_data")

        mock_bucket = mock.MagicMock()
        mock_gcs_client = gcs_storage.Client.return_value
        mock_gcs_client.bucket.return_value = mock_bucket

        storage = GoogleCloudStorage()
        saved_path: str = storage.save_video(
            str(recorded_path), "screenshots/browser-20250101000000.webm"
        )

        mock_bucket.blob.assert_called_once_with(
            "screenshots/browser-20250101000000.webm"
        )
        mock_bucket.blob.return_value.upload_from_filename.assert_called_once_with(
            str(recorded_path), content_type="video/webm"
        )
        assert "screenshots/browser-20250101000000.webm" in saved_path
        assert recorded_path.exists()


def test_clear_resources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tmp_data_path: Path = tmp_path / "data"
    tmp_data_file: Path = tmp_path / "test_file.txt"
    tmp_data_file.write_text("Hesitation is defeat!")

    tmp_output_path: Path = tmp_path / "output"
    tmp_output_file: Path = tmp_path / "test_file.txt"
    tmp_output_file.write_text("Hesitation is defeat!")

    monkeypatch.setattr("vigilant.common.values.IOResources.DATA_PATH", tmp_data_path)
    monkeypatch.setattr(
        "vigilant.common.values.IOResources.OUTPUT_PATH", tmp_output_path
    )

    clear_resources()

    assert tmp_data_path.exists() and not any(tmp_data_path.iterdir())
    assert tmp_output_path.exists() and not any(tmp_output_path.iterdir())
