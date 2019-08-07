#!/bin/bash

set -e
# test for needed commands; "set -e" means we'll exit if any are missing
type gcloud >/dev/null
type kubectl >/dev/null

echo 'Finding latest passing sha1 on master...' >&2
SHA=$(gcloud builds list --filter='source:github_cjworkbench_cron-workbench-workflow AND source.repoSource.branchName=master status=SUCCESS' --sort-by="~startTime" --limit=1 --format='get(results.images[0].name)' | cut -f1)
echo "$SHA"

echo -n "Setting cronjob/cron-workbench-workflow image to $SHA..." >&2
kubectl -n production set image cronjob/cron-workbench-workflow cron-workbench-workflow=gcr.io/cj-workbench/cron-workbench-workflow:$SHA >/dev/null
echo ' done' >&2
