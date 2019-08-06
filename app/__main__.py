#!/usr/bin/env python3

import datetime
import io
import os
import sys
import boto3
import botocore
import pg8000
import requests


UrlBase = "https://app.workbenchdata.com/api/v1"
# Load other constants from environment variables
try:
    WorkflowId = os.environ["WORKFLOW_ID"]
    WorkflowsStepId = os.environ["WORKFLOWS_STEP_ID"]
    WorkflowsApiToken = os.environ["WORKFLOWS_API_TOKEN"]
    StepsStepId = os.environ["STEPS_STEP_ID"]
    StepsApiToken = os.environ["STEPS_API_TOKEN"]
    DatabaseHost = os.environ["DATABASE_HOST"]
    DatabaseName = os.environ["DATABASE_NAME"]
    DatabaseUser = os.environ["DATABASE_USER"]
    DatabasePassword = os.environ["DATABASE_PASSWORD"]
except KeyError as err:
    print("Error: required %s environment variable" % err.args[0], file=sys.stderr)
    sys.exit(1)


def upload_api_url(step_id: str) -> str:
    return f"{UrlBase}/workflows/{WorkflowId}/steps/{step_id}/uploads"


def query_csv(cursor, sql: str) -> io.BytesIO:
    """
    Execute an SQL COPY TO STDOUT query and return the result as a CSV fileobj.

    Remember: in CSV, there's no NULL. The output will be an empty string.
    """
    retval = io.BytesIO()
    cursor.execute(sql, stream=retval)
    retval.seek(0)
    return retval


def generate_csv_filename(basename: str) -> str:
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%MZ")
    return f"{basename}-{timestamp}.csv"


def regenerate_workflows_csv(cursor):
    fileobj = query_csv(
        cursor,
        """
        COPY (
            SELECT
                id AS workflow_id,
                (
                    SELECT auth_user.email
                    FROM auth_user
                    WHERE auth_user.id = server_workflow.owner_id
                ) AS owner_email,
                anonymous_owner_session_key,
                last_viewed_at,
                creation_date AS created_at,
                lesson_slug
            FROM server_workflow
            ORDER BY id
        ) TO STDOUT WITH CSV HEADER
        """,
    )
    filename = generate_csv_filename("workflows")
    upload(fileobj, filename, WorkflowsStepId, WorkflowsApiToken)


def regenerate_steps_csv(cursor):
    fileobj = query_csv(
        cursor,
        """
        COPY (
            SELECT
                tab.workflow_id,
                tab.position + 1 AS tab_number,
                tab.name AS tab_name,
                step."order" + 1 AS step_position,
                step.module_id_name AS module,
                step.fetch_error,
                step.last_relevant_delta_id = step.cached_render_result_delta_id AS is_rendered,
                step.cached_render_result_error AS render_error,
                step.is_busy,
                step.notifications AS has_notifications,
                CASE step.auto_update_data
                    WHEN TRUE THEN update_interval
                    ELSE NULL
                END AS autofetch_every_n_seconds,
                step.is_collapsed,
                step.id AS step_id,
                step.slug
            FROM server_wfmodule step
            INNER JOIN server_tab tab ON step.tab_id = tab.id
            WHERE
                NOT step.is_deleted
                AND NOT tab.is_deleted
            ORDER BY tab.workflow_id, tab.position, step."order"
        ) TO STDOUT WITH CSV HEADER
        """,
    )
    filename = generate_csv_filename("steps")
    upload(fileobj, filename, StepsStepId, StepsApiToken)


def upload(fileobj: io.BytesIO, filename: str, step_id: str, api_token: str):
    # 1. Authorize upload to S3
    credentials_url = upload_api_url(step_id)
    credentials_response = requests.post(
        credentials_url, headers={"Authorization": f"Bearer {api_token}"}
    )
    credentials_response.raise_for_status()  # expect 200 OK
    s3_config = credentials_response.json()

    # 2. Upload to S3
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=s3_config["credentials"]["accessKeyId"],
        aws_secret_access_key=s3_config["credentials"]["secretAccessKey"],
        aws_session_token=s3_config["credentials"]["sessionToken"],
        region_name=s3_config["region"],
        endpoint_url=s3_config["endpoint"],
        config=botocore.client.Config(s3={"addressing_style": "path"}),
    )
    s3_client.upload_fileobj(fileobj, s3_config["bucket"], s3_config["key"])

    # 3. Tell Workbench about the upload
    finish_response = requests.post(
        s3_config["finishUrl"],
        headers={"Authorization": f"Bearer {api_token}"},
        json={"filename": filename},
    )
    finish_response.raise_for_status()  # expect 200 OK


def main():
    with pg8000.connect(
        user=DatabaseUser,
        host=DatabaseHost,
        database=DatabaseName,
        password=DatabasePassword,
    ) as conn:  # or raise
        with conn.cursor() as cursor:
            regenerate_workflows_csv(cursor)
            regenerate_steps_csv(cursor)


if __name__ == "__main__":
    main()
