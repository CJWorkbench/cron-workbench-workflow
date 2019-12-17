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
- ``WORKFLOW_ID``: Workflow where our results will go.
- ``WORKFLOWS_STEP_ID``: the Upload Step where we will send the Workflows CSV.
- ``WORKFLOWS_API_TOKEN``: the upload-API token for ``WORKFLOWS_STEP_ID``. Keep it secret!
- ``STEPS_STEP_ID``: the Upload Step where we will send the Steps CSV.
- ``WORKFLOWS_API_TOKEN``: the upload-API token for ``STEPS_STEP_ID``. Keep it secret!
