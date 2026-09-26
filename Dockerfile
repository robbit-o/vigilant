FROM thehale/python-poetry:2.4.1-py3.12-slim AS build-deps

RUN apt update -y && apt upgrade -y
# RUN apt install -y build-essential libpq-dev

RUN poetry self add poetry-plugin-export

ADD . vigilant
WORKDIR /vigilant
RUN poetry export -o /requirements.txt --without-hashes --without-urls


FROM python:3.12-slim AS build-service

RUN apt update -y && apt upgrade -y

# Create app folder
RUN mkdir -p -m 777 /var/lib/vigilant

# Install Playwright Browser and Driver
# Keep this layer before the dependencies to reuse the cached browser
# download when only the source code changes. PLAYWRIGHT_VERSION must match
# the version locked in poetry.lock.
ARG PLAYWRIGHT_VERSION=1.61.0
RUN pip install --no-cache-dir --upgrade "playwright==${PLAYWRIGHT_VERSION}" && \
    playwright install chromium --with-deps

# Install dependencies
COPY --from=build-deps /requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy app source code
ADD vigilant /vigilant

CMD ["uvicorn", "vigilant.app:app", "--host", "0.0.0.0", "--port", "8080"]
