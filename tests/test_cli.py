from unittest import mock

import click
import pytest
import typer
from typer.testing import CliRunner

from vigilant import cli
from vigilant.common import options
from vigilant.common.values import collector, settings
from vigilant.core.collector.main import SCRAPER_REGISTRY

runner: CliRunner = CliRunner()


@pytest.fixture(autouse=True)
def reset_config() -> None:
    options.configure(options.BrowserOptions())
    collector.ENABLED_SCRAPERS = ["BancoChile", "BancoFalabella"]


@mock.patch("vigilant.cli.run.main")
def test_main_defaults(mock_run_main: mock.MagicMock) -> None:
    result = runner.invoke(cli.app)

    assert result.exit_code == 0
    assert options.current == options.BrowserOptions()
    assert collector.ENABLED_SCRAPERS == ["BancoChile", "BancoFalabella"]
    mock_run_main.assert_called_once_with()


@mock.patch("vigilant.cli.run.main")
def test_main_show_window(mock_run_main: mock.MagicMock) -> None:
    result = runner.invoke(cli.app, ["--show-window"])

    assert result.exit_code == 0
    assert options.current == options.BrowserOptions(False, 1536, 864)
    mock_run_main.assert_called_once_with()


@mock.patch("vigilant.cli.run.main")
def test_main_show_window_with_width(mock_run_main: mock.MagicMock) -> None:
    result = runner.invoke(cli.app, ["--show-window", "--width", "1280"])

    assert result.exit_code == 0
    assert options.current == options.BrowserOptions(False, 1280, 720)
    mock_run_main.assert_called_once_with()


@mock.patch("vigilant.cli.run.main")
def test_main_size(mock_run_main: mock.MagicMock) -> None:
    result = runner.invoke(cli.app, ["-w", "1280", "-h", "720"])

    assert result.exit_code == 0
    assert options.current == options.BrowserOptions(True, 1280, 720)
    mock_run_main.assert_called_once_with()


@mock.patch("vigilant.cli.run.main")
def test_main_width_only(mock_run_main: mock.MagicMock) -> None:
    result = runner.invoke(cli.app, ["--width", "1280"])

    assert result.exit_code == 0
    assert options.current == options.BrowserOptions(True, 1280, 720)
    mock_run_main.assert_called_once_with()


@mock.patch("vigilant.cli.run.main")
def test_main_scrapers(mock_run_main: mock.MagicMock) -> None:
    result = runner.invoke(cli.app, ["-s", "BancoChile", "-s", "BancoFalabella"])

    assert result.exit_code == 0
    assert collector.ENABLED_SCRAPERS == ["BancoChile", "BancoFalabella"]
    mock_run_main.assert_called_once_with()


@mock.patch("vigilant.cli.run.main")
def test_main_scrapers_comma_separated(mock_run_main: mock.MagicMock) -> None:
    result = runner.invoke(cli.app, ["--scrapers", "BancoChile, BancoFalabella"])

    assert result.exit_code == 0
    assert collector.ENABLED_SCRAPERS == ["BancoChile", "BancoFalabella"]
    mock_run_main.assert_called_once_with()


@mock.patch("vigilant.cli.run.main")
def test_main_scrapers_override(mock_run_main: mock.MagicMock) -> None:
    result = runner.invoke(cli.app, ["-s", "BancoFalabella"])

    assert result.exit_code == 0
    assert collector.ENABLED_SCRAPERS == ["BancoFalabella"]
    mock_run_main.assert_called_once_with()


@mock.patch("vigilant.cli.run.main")
def test_main_unknown_scraper(mock_run_main: mock.MagicMock) -> None:
    result = runner.invoke(
        cli.app, ["-s", "BancoChile", "-s", "Nope"], standalone_mode=False
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, click.BadParameter)
    assert result.exception.message == (
        f"Unknown scrapers: Nope. Available scrapers: {', '.join(SCRAPER_REGISTRY)}"
    )
    assert collector.ENABLED_SCRAPERS == ["BancoChile", "BancoFalabella"]
    mock_run_main.assert_not_called()


@mock.patch("vigilant.cli.run.main")
def test_main_record_video(mock_run_main: mock.MagicMock) -> None:
    result = runner.invoke(cli.app, ["--record-video"])

    assert result.exit_code == 0
    assert options.current.record_video is True
    mock_run_main.assert_called_once_with()


@mock.patch("vigilant.cli.run.main")
def test_main_no_record_video_overrides_env(
    mock_run_main: mock.MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "BROWSER_RECORD_VIDEO", True)

    result = runner.invoke(cli.app, ["--no-record-video"])

    assert result.exit_code == 0
    assert options.current.record_video is False
    mock_run_main.assert_called_once_with()


@mock.patch("vigilant.cli.run.main")
def test_main_record_video_from_env(mock_run_main: mock.MagicMock) -> None:
    result = runner.invoke(cli.app)

    assert result.exit_code == 0
    assert options.current.record_video is False
    mock_run_main.assert_called_once_with()


def test_main_help() -> None:
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0

    command: click.Command = typer.main.get_command(cli.app)
    flags: set[str] = {
        option
        for parameter in command.params
        for option in (*parameter.opts, *parameter.secondary_opts)
    }

    assert {
        "--show-window",
        "--width",
        "--height",
        "--scrapers",
    } <= flags
