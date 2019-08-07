#!/bin/bash

DIR="$(dirname "$0")"
WORKFLOWS_API_TOKEN=${1:?"Usage: $0 WORKFLOWS_API_TOKEN STEPS_API_TOKEN"}
STEPS_API_TOKEN=${2:?"Usage: $0 WORKFLOWS_API_TOKEN STEPS_API_TOKEN"}

kubectl -n production create secret generic cron-workbench-workflow-secrets \
  --from-literal=WORKFLOWS_API_TOKEN="$WORKFLOWS_API_TOKEN" \
  --from-literal=STEPS_API_TOKEN="$STEPS_API_TOKEN"

kubectl -n production apply -f "$DIR"/cron-workbench-workflow.yaml
