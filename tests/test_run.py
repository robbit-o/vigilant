from unittest import mock

from vigilant import run


@mock.patch("vigilant.run.collector")
@mock.patch("vigilant.run.upload")
def test_main(
    upload_finances_data: mock.MagicMock,
    collector: mock.MagicMock,
) -> None:
    run.main()

    collector.collect.assert_called_once()
    upload_finances_data.main.assert_called_once()
