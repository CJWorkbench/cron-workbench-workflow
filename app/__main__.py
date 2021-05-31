#!/usr/bin/env python3

import datetime
import logging
import io
import os
import sys

import pg8000
import httpx
import tusclient.uploader


logger = logging.getLogger(__name__)


try:
    WorkflowsUrl = os.environ["WORKFLOWS_URL"]
    WorkflowsApiToken = os.environ["WORKFLOWS_API_TOKEN"]
    StepsUrl = os.environ["STEPS_URL"]
    StepsApiToken = os.environ["STEPS_API_TOKEN"]
    UsersUrl = os.environ["USERS_URL"]
    UsersApiToken = os.environ["USERS_API_TOKEN"]
    DatabaseHost = os.environ["DATABASE_HOST"]
    DatabaseName = os.environ["DATABASE_NAME"]
    DatabaseUser = os.environ["DATABASE_USER"]
    DatabasePassword = os.environ["DATABASE_PASSWORD"]
except KeyError as err:
    logger.error("Error: required %s environment variable", err.args[0])
    sys.exit(1)


def query_csv(cursor, sql: str) -> io.BytesIO:
    """
    Execute an SQL COPY TO STDOUT query and return the result as a CSV fileobj.

    Remember: in CSV, there's no NULL. The output will be an empty string.
    """
    retval = io.BytesIO()
    cursor.execute(sql, stream=retval)
    n_bytes = retval.tell()
    retval.seek(0)
    return retval, n_bytes


def generate_csv_filename(basename: str) -> str:
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%MZ")
    return f"{basename}-{timestamp}.csv"


def regenerate_steps_csv(cursor):
    logger.info("Querying Steps")
    fileobj, n_bytes = query_csv(
        cursor,
        """
        COPY (
            SELECT
                step.id AS step_id,
                tab.workflow_id,
                tab.position + 1 AS tab_number,
                tab.name AS tab_name,
                step."order" + 1 AS step_position,
                step.module_id_name AS module,
                step.fetch_errors,
                step.last_relevant_delta_id = step.cached_render_result_delta_id AS is_rendered,
                step.cached_render_result_errors::TEXT AS render_error,
                step.is_busy,
                step.notifications AS has_notifications,
                CASE step.auto_update_data
                    WHEN TRUE THEN update_interval
                    ELSE NULL
                END AS autofetch_every_n_seconds,
                step.is_collapsed,
                step.slug
            FROM step
            INNER JOIN tab ON step.tab_id = tab.id
            WHERE
                NOT step.is_deleted
                AND NOT tab.is_deleted
            ORDER BY tab.workflow_id, tab.position, step."order"
        ) TO STDOUT WITH CSV HEADER
        """,
    )
    filename = generate_csv_filename("steps")
    upload(fileobj, filename, n_bytes=n_bytes, url=StepsUrl, api_token=StepsApiToken)


def regenerate_users_csv(cursor):
    logger.info("Querying Users")
    fileobj, n_bytes = query_csv(
        cursor,
        """
        COPY (
            SELECT
                auth_user.id AS user_id,
                auth_user.email,
                TO_CHAR(auth_user.last_login, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS last_logged_in_at,
                auth_user.username,
                auth_user.first_name,
                auth_user.last_name,
                TO_CHAR(auth_user.date_joined, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS created_at,
                auth_user.is_active,
                user_profile.get_newsletter,
                user_profile.locale_id,
                user_profile.stripe_customer_id,
                TO_CHAR(MAX(subscription.renewed_at), 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS last_subscription
            FROM auth_user
            LEFT JOIN cjworkbench_userprofile user_profile ON auth_user.id = user_profile.user_id
            LEFT JOIN subscription ON auth_user.id = subscription.user_id
            GROUP BY
                auth_user.id,
                auth_user.email,
                auth_user.last_login,
                auth_user.username,
                auth_user.first_name,
                auth_user.last_name,
                auth_user.date_joined,
                auth_user.is_active,
                user_profile.get_newsletter,
                user_profile.locale_id,
                user_profile.stripe_customer_id
            ORDER BY auth_user.id
        ) TO STDOUT WITH CSV HEADER
        """,
    )
    filename = generate_csv_filename("steps")
    upload(fileobj, filename, n_bytes=n_bytes, url=UsersUrl, api_token=UsersApiToken)


def regenerate_workflows_csv(cursor):
    logger.info("Querying Workflows")
    fileobj, n_bytes = query_csv(
        cursor,
        """
        COPY (
            SELECT
                id AS workflow_id,
                owner_id AS user_id,
                anonymous_owner_session_key,
                TO_CHAR(last_viewed_at, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS last_viewed_at,
                TO_CHAR(creation_date, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS created_at,
                lesson_slug
            FROM workflow
            ORDER BY id
        ) TO STDOUT WITH CSV HEADER
        """,
    )
    filename = generate_csv_filename("workflows")
    upload(
        fileobj,
        filename,
        n_bytes=n_bytes,
        url=WorkflowsUrl,
        api_token=WorkflowsApiToken,
    )


def upload(
    fileobj: io.BytesIO, filename: str, n_bytes: int, url: str, api_token: str
) -> None:
    # 1. Authorize upload to S3
    credentials_response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {api_token}"},
        json={"filename": filename, "size": n_bytes},
    )
    credentials_response.raise_for_status()  # expect 200 OK
    tus_upload_url = credentials_response.json()["tusUploadUrl"]

    # 2. TUS-upload
    uploader = tusclient.uploader.Uploader(
        file_stream=fileobj, url=tus_upload_url, retries=2
    )
    uploader.upload()


def main():
    logger.info("Connecting to database at %s", DatabaseHost)
    with pg8000.connect(
        user=DatabaseUser,
        host=DatabaseHost,
        database=DatabaseName,
        password=DatabasePassword,
    ) as conn:  # or raise
        logger.info("Getting cursor")
        with conn.cursor() as cursor:
            regenerate_steps_csv(cursor)
            regenerate_workflows_csv(cursor)
            regenerate_users_csv(cursor)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
