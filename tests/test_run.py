from unittest import mock

from vigilant import run


@mock.patch("vigilant.run.SyncService")
@mock.patch("vigilant.run.get_enabled_scrapers")
@mock.patch("vigilant.run.clear_resources")
def test_main(
    clear_resources: mock.MagicMock,
    get_enabled_scrapers: mock.MagicMock,
    MockSyncService: mock.MagicMock,
) -> None:
    mock_scraper = mock.MagicMock()
    get_enabled_scrapers.return_value = {"BancoChile": mock_scraper}

    run.main()

    clear_resources.assert_called_once()
    get_enabled_scrapers.assert_called_once()
    MockSyncService.assert_called_once_with(
        mock_scraper, run.MAPPING_CONFIG["BancoChile"]
    )
    MockSyncService.return_value.sync_bank.assert_called_once()
