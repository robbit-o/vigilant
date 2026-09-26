# Vigilant

<p align="left">
    <a href="https://www.python.org/doc/versions/" target="_blank">
        <img
            alt="Python Version from PEP 621 TOML"
            src="https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Frobbit-o%2Fvigilant%2Fmain%2Fpyproject.toml&logo=Python&labelColor=ffde57&color=4584b6"
            alt="Python version"
        />
    </a>
    <a href="https://codecov.io/gh/robbit-o/vigilant">
        <img
            src="https://codecov.io/gh/robbit-o/vigilant/graph/badge.svg?token=VIWE3BIDB3"
            alt="Code coverage"
        />
    </a>
</p>

## Authenticate with user credentials

```shell
gcloud auth application-default login \
    --client-id-file credentials.json \
    --billing-project ${GCLOUD_PROJECT} \
    --scopes https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive
```

## Run application

```shell
poetry run vigilant
```

### Command line options

| Option | Description |
| --- | --- |
| `--show-window` | Shows the browser window instead of running headless, with a slightly reduced 16:9 size (`1536x864`) |
| `-w`, `--width` | Browser window width in pixels, the height is derived from the 16:9 ratio when omitted |
| `-h`, `--height` | Browser window height in pixels, the width is derived from the 16:9 ratio when omitted |
| `-s`, `--scrapers` | Enabled scrapers, overrides the `ENABLED_SCRAPERS` environment variable |

Enabled scrapers are repeated or comma separated options:

```shell
poetry run vigilant -s BancoChile -s BancoFalabella
poetry run vigilant -s BancoChile,BancoFalabella --show-window -w 1280
```

## Start service locally

```shell
poetry run uvicorn vigilant.app:app --host 0.0.0.0 --port 8080 --reload
```

## Start service in container with local changes

```shell
docker compose up --watch
```

***Note:** I'm using a volume created by gcloud-cli-persistence to store my
gcloud credentials, check where your's are stored and update them the compose file.*
