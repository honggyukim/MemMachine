#!/bin/sh -x

curl -X POST "http://127.0.0.1:8080/api/v2/projects/list" \
-H "Content-Type: application/json" \
-d '{}'
