import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import requests
import typer
from rich.progress import Progress

from quillion_cli.utils.file_downloader import (
    downloads_assets,
    get_release_assets,
    ASSETS,
    REPO_URL,
)


class TestFileDownloader:
    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary project directory for testing."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        return project_dir

    @pytest.fixture
    def mock_release_assets(self):
        """Mock release assets data."""
        return [
            {
                "name": "package.json",
                "browser_download_url": "https://github.com/base-of-base/quillion-core/releases/download/v1.0.0/package.json",
                "size": 1024,
            },
            {
                "name": "quillion.d.ts",
                "browser_download_url": "https://github.com/base-of-base/quillion-core/releases/download/v1.0.0/quillion.d.ts",
                "size": 2048,
            },
            {
                "name": "quillion.js",
                "browser_download_url": "https://github.com/base-of-base/quillion-core/releases/download/v1.0.0/quillion.js",
                "size": 4096,
            },
            {
                "name": "quillion_bg.wasm",
                "browser_download_url": "https://github.com/base-of-base/quillion-core/releases/download/v1.0.0/quillion_bg.wasm",
                "size": 8192,
            },
            {
                "name": "quillion_bg.wasm.d.ts",
                "browser_download_url": "https://github.com/base-of-base/quillion-core/releases/download/v1.0.0/quillion_bg.wasm.d.ts",
                "size": 512,
            },
            {
                "name": "extra_file.txt",
                "browser_download_url": "https://github.com/base-of-base/quillion-core/releases/download/v1.0.0/extra_file.txt",
                "size": 100,
            },
        ]

    @pytest.fixture
    def mock_release_data(self, mock_release_assets):
        """Mock full release data."""
        return {"tag_name": "v1.0.0", "assets": mock_release_assets}

    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_get_release_assets_success(self, mock_requests_get, mock_release_data):
        """Test successful retrieval of release assets."""
        mock_response = Mock()
        mock_response.json.return_value = mock_release_data
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        assets = get_release_assets()

        mock_requests_get.assert_called_once_with(REPO_URL, timeout=30)
        assert assets == mock_release_data["assets"]
        assert len(assets) == 6

    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_get_release_assets_no_assets(self, mock_requests_get):
        """Test retrieval when no assets are found."""
        mock_response = Mock()
        mock_response.json.return_value = {"assets": []}
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        assets = get_release_assets()

        assert assets == []

    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_get_release_assets_request_exception(self, mock_requests_get):
        """Test handling of request exceptions."""
        mock_requests_get.side_effect = requests.exceptions.RequestException(
            "Network error"
        )

        with pytest.raises(requests.exceptions.RequestException):
            get_release_assets()

    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_get_release_assets_http_error(self, mock_requests_get):
        """Test handling of HTTP errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_requests_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            get_release_assets()

    @patch("quillion_cli.utils.file_downloader.get_release_assets")
    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_downloads_assets_success(
        self, mock_requests_get, mock_get_assets, temp_project_dir, mock_release_assets
    ):
        """Test successful download of all assets."""
        mock_get_assets.return_value = mock_release_assets

        mock_responses = []
        for asset in mock_release_assets:
            mock_response = Mock()
            mock_response.content = f"content_{asset['name']}".encode()
            mock_response.raise_for_status.return_value = None
            mock_responses.append(mock_response)

        mock_requests_get.side_effect = mock_responses

        downloads_assets(temp_project_dir)

        q_dir = temp_project_dir / ".q"
        pkg_dir = q_dir / "pkg"
        assert q_dir.exists()
        assert pkg_dir.exists()

        for asset_name in ASSETS:
            asset_file = pkg_dir / asset_name
            assert asset_file.exists()
            assert asset_file.read_text() == f"content_{asset_name}"

        extra_file = pkg_dir / "extra_file.txt"
        assert not extra_file.exists()

        assert mock_requests_get.call_count == len(ASSETS)

    @patch("quillion_cli.utils.file_downloader.get_release_assets")
    def test_downloads_assets_no_assets_found(self, mock_get_assets, temp_project_dir):
        """Test behavior when no assets are found in release."""
        mock_get_assets.return_value = []

        with patch("quillion_cli.utils.file_downloader.debugger") as mock_debugger:
            with pytest.raises(typer.Exit):
                downloads_assets(temp_project_dir)

            mock_debugger.error.assert_called_once_with(
                "No assets found in the release"
            )

    @patch("quillion_cli.utils.file_downloader.get_release_assets")
    def test_downloads_assets_none_assets(self, mock_get_assets, temp_project_dir):
        """Test behavior when assets is None."""
        mock_get_assets.return_value = None

        with patch("quillion_cli.utils.file_downloader.debugger") as mock_debugger:
            with pytest.raises(typer.Exit):
                downloads_assets(temp_project_dir)

            mock_debugger.error.assert_called_once_with(
                "No assets found in the release"
            )

    @patch("quillion_cli.utils.file_downloader.get_release_assets")
    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_downloads_assets_partial_assets(
        self, mock_requests_get, mock_get_assets, temp_project_dir
    ):
        """Test download when only some required assets are available."""
        partial_assets = [
            {
                "name": "package.json",
                "browser_download_url": "https://github.com/base-of-base/quillion-core/releases/download/v1.0.0/package.json",
                "size": 1024,
            },
            {
                "name": "quillion.js",
                "browser_download_url": "https://github.com/base-of-base/quillion-core/releases/download/v1.0.0/quillion.js",
                "size": 4096,
            },
        ]
        mock_get_assets.return_value = partial_assets

        mock_responses = []
        for asset in partial_assets:
            mock_response = Mock()
            mock_response.content = f"content_{asset['name']}".encode()
            mock_response.raise_for_status.return_value = None
            mock_responses.append(mock_response)

        mock_requests_get.side_effect = mock_responses

        downloads_assets(temp_project_dir)

        pkg_dir = temp_project_dir / ".q" / "pkg"

        assert (pkg_dir / "package.json").exists()
        assert (pkg_dir / "quillion.js").exists()

        for asset_name in ASSETS:
            if asset_name not in ["package.json", "quillion.js"]:
                assert not (pkg_dir / asset_name).exists()

    @patch("quillion_cli.utils.file_downloader.get_release_assets")
    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_downloads_assets_download_failure(
        self, mock_requests_get, mock_get_assets, temp_project_dir, mock_release_assets
    ):
        """Test behavior when asset download fails."""
        mock_get_assets.return_value = mock_release_assets

        mock_responses = [
            Mock(content=b"content_package.json", raise_for_status=Mock()),
            Mock(content=b"content_quillion.d.ts", raise_for_status=Mock()),
            Mock(
                raise_for_status=Mock(
                    side_effect=requests.exceptions.HTTPError("404 Not Found")
                )
            ),
        ]
        mock_requests_get.side_effect = mock_responses

        with pytest.raises(requests.exceptions.HTTPError):
            downloads_assets(temp_project_dir)

    @patch("quillion_cli.utils.file_downloader.get_release_assets")
    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_downloads_assets_existing_directories(
        self, mock_requests_get, mock_get_assets, temp_project_dir, mock_release_assets
    ):
        """Test that existing directories are handled properly."""
        mock_get_assets.return_value = mock_release_assets

        q_dir = temp_project_dir / ".q"
        pkg_dir = q_dir / "pkg"
        q_dir.mkdir()
        pkg_dir.mkdir()

        existing_file = pkg_dir / "package.json"
        existing_file.write_text("old_content")

        mock_responses = []
        for asset in mock_release_assets:
            mock_response = Mock()
            mock_response.content = f"new_content_{asset['name']}".encode()
            mock_response.raise_for_status.return_value = None
            mock_responses.append(mock_response)

        mock_requests_get.side_effect = mock_responses

        downloads_assets(temp_project_dir)

        assert existing_file.exists()
        assert existing_file.read_text() == "new_content_package.json"

    @patch("quillion_cli.utils.file_downloader.get_release_assets")
    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_downloads_assets_progress_tracking(
        self, mock_requests_get, mock_get_assets, temp_project_dir, mock_release_assets
    ):
        """Test that progress is properly tracked."""
        mock_get_assets.return_value = mock_release_assets

        mock_responses = []
        for asset in mock_release_assets:
            mock_response = Mock()
            mock_response.content = f"content_{asset['name']}".encode()
            mock_response.raise_for_status.return_value = None
            mock_responses.append(mock_response)

        mock_requests_get.side_effect = mock_responses

        with patch("quillion_cli.utils.file_downloader.Progress") as mock_progress:
            mock_progress_instance = MagicMock()
            mock_progress.return_value.__enter__.return_value = mock_progress_instance
            mock_progress_instance.add_task.return_value = "task_id"

            downloads_assets(temp_project_dir)

            mock_progress.assert_called_once()
            mock_progress_instance.add_task.assert_called_once_with(
                "Downloading internal assets", total=len(ASSETS)
            )
            assert mock_progress_instance.update.call_count == len(ASSETS)

    @patch("quillion_cli.utils.file_downloader.get_release_assets")
    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_downloads_assets_correct_urls_called(
        self, mock_requests_get, mock_get_assets, temp_project_dir, mock_release_assets
    ):
        """Test that correct URLs are called for download."""
        mock_get_assets.return_value = mock_release_assets

        mock_responses = []
        for asset in mock_release_assets:
            mock_response = Mock()
            mock_response.content = f"content_{asset['name']}".encode()
            mock_response.raise_for_status.return_value = None
            mock_responses.append(mock_response)

        mock_requests_get.side_effect = mock_responses

        downloads_assets(temp_project_dir)

        expected_calls = []
        for asset in mock_release_assets:
            if asset["name"] in ASSETS:
                expected_calls.append(call(asset["browser_download_url"], timeout=30))

        mock_requests_get.assert_has_calls(expected_calls, any_order=True)

    @patch("quillion_cli.utils.file_downloader.get_release_assets")
    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_downloads_assets_file_write_error(
        self, mock_requests_get, mock_get_assets, temp_project_dir, mock_release_assets
    ):
        """Test behavior when file writing fails."""
        mock_get_assets.return_value = mock_release_assets

        mock_response = Mock()
        mock_response.content = b"test_content"
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        with patch("builtins.open", side_effect=IOError("Disk full")):
            with pytest.raises(IOError):
                downloads_assets(temp_project_dir)

    def test_assets_constant(self):
        """Test that ASSETS constant contains expected values."""
        expected_assets = [
            "package.json",
            "quillion.d.ts",
            "quillion.js",
            "quillion_bg.wasm",
            "quillion_bg.wasm.d.ts",
        ]
        assert ASSETS == expected_assets

    def test_repo_url_constant(self):
        """Test that REPO_URL constant is correct."""
        expected_url = (
            "https://api.github.com/repos/base-of-base/quillion-core/releases/latest"
        )
        assert REPO_URL == expected_url

    @patch("quillion_cli.utils.file_downloader.get_release_assets")
    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_integration_flow(
        self, mock_requests_get, mock_get_assets, temp_project_dir, mock_release_data
    ):
        """Test the complete flow from API call to file download."""
        mock_get_assets.return_value = mock_release_data["assets"]

        download_responses = []
        for asset in mock_release_data["assets"]:
            if asset["name"] in ASSETS:
                mock_download = Mock()
                mock_download.content = f"download_{asset['name']}".encode()
                mock_download.raise_for_status.return_value = None
                download_responses.append(mock_download)

        mock_requests_get.side_effect = download_responses

        downloads_assets(temp_project_dir)

        pkg_dir = temp_project_dir / ".q" / "pkg"
        for asset_name in ASSETS:
            asset_file = pkg_dir / asset_name
            assert asset_file.exists()
            file_content = asset_file.read_text()
            assert file_content == f"download_{asset_name}"

        assert mock_requests_get.call_count == len(ASSETS)

    @patch("quillion_cli.utils.file_downloader.requests.get")
    def test_integration_flow_both_functions(
        self, mock_requests_get, temp_project_dir, mock_release_data
    ):
        """Test the complete flow testing both functions together."""
        api_response = Mock()
        api_response.json.return_value = mock_release_data
        api_response.raise_for_status.return_value = None

        download_responses = []
        for asset in mock_release_data["assets"]:
            if asset["name"] in ASSETS:
                mock_download = Mock()
                mock_download.content = f"download_{asset['name']}".encode()
                mock_download.raise_for_status.return_value = None
                download_responses.append(mock_download)

        mock_requests_get.side_effect = [api_response] + download_responses

        assets = get_release_assets()
        assert assets == mock_release_data["assets"]

        new_download_responses = []
        for asset in mock_release_data["assets"]:
            if asset["name"] in ASSETS:
                mock_download = Mock()
                mock_download.content = f"download_{asset['name']}".encode()
                mock_download.raise_for_status.return_value = None
                new_download_responses.append(mock_download)

        mock_requests_get.side_effect = [api_response] + new_download_responses

        downloads_assets(temp_project_dir)

        pkg_dir = temp_project_dir / ".q" / "pkg"
        for asset_name in ASSETS:
            assert (pkg_dir / asset_name).exists()
