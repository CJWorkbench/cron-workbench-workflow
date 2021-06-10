Workflow Updater
================

Analyze data *about* Workbench, *in* Workbench!

Connects to the Workbench Postgres database to gather information, then feeds it into a Workflow described by environment variables.

Usage
-----

``docker run -it --rm --env [ENV VARS] $(docker build -q .)``

Environment variables
---------------------

- ``DATABASE_HOST``: Postgres server hostname
- ``DATABASE_USER``: Postgres server username
- ``DATABASE_NAME``: Postgres database name
- ``DATABASE_PASSWORD``: Postgres database password
- ``STEPS_URL``: URL of the Upload Step where we will send the Steps CSV.
- ``STEPS_API_TOKEN``: the upload-step API token for ``STEPS_URL``. Keep it secret!
- ``USERS_URL``: the Upload Step where we will send the Workflows CSV.
- ``USERS_API_TOKEN``: the upload-step API token for ``USERS_URL``. Keep it secret!
- ``WORKFLOWS_URL``: the Upload Step where we will send the Workflows CSV.
- ``WORKFLOWS_API_TOKEN``: the upload-step API token for ``WORKFLOWS_URL``. Keep it secret!

Deployment
----------

1. ``git push``. Google Cloud Build will build a new image with this SHA1.
2. Edit the ``cron-workbench-workflow`` Kubernetes cronjob to use the SHA1.
