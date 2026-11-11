#!/bin/sh
# Runs as the one-shot `minio-init` service (deploy/docker-compose.prod.yml) on every `up`; safe to
# repeat. With MinIO's root credentials it makes sure that:
#   - the media bucket exists and is private (no anonymous access),
#   - the app's own user (STORAGE_ACCESS_KEY / STORAGE_SECRET_KEY) exists, and
#   - that user can only read, write, list and delete objects in that one bucket: it can't
#     create or delete buckets, touch other buckets, change policies or administer MinIO.
# The root credentials are given to this service and to MinIO itself, never to the backend or
# the workers. Secrets come from deploy/.env and are never printed.
set -eu

if [ -z "${MINIO_ROOT_USER:-}" ] || [ -z "${MINIO_ROOT_PASSWORD:-}" ]; then
    echo "minio-init: MINIO_ROOT_USER/MINIO_ROOT_PASSWORD not set; skipping (see deploy/README.md, «کاربر جدا برای MinIO»)."
    exit 0
fi
if [ "${STORAGE_ACCESS_KEY:-}" = "$MINIO_ROOT_USER" ]; then
    echo "minio-init: the app still uses the root account; skipping. Give it its own STORAGE_ACCESS_KEY (deploy/README.md)."
    exit 0
fi

BUCKET=${STORAGE_BUCKET_NAME:?STORAGE_BUCKET_NAME is required}
export MC_CONFIG_DIR=/tmp/mc
mc alias set local "${MINIO_ENDPOINT:-http://minio:9000}" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null

mc mb --ignore-existing "local/$BUCKET" >/dev/null
mc anonymous set none "local/$BUCKET" >/dev/null

cat > /tmp/app-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetBucketLocation", "s3:ListBucket", "s3:ListBucketMultipartUploads"],
      "Resource": ["arn:aws:s3:::$BUCKET"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"],
      "Resource": ["arn:aws:s3:::$BUCKET/*"]
    }
  ]
}
EOF
mc admin policy create local amozeshyar-app /tmp/app-policy.json >/dev/null

# Adds the user, or re-sets its secret, so deploy/.env stays the source of truth after a rotation.
mc admin user add local "$STORAGE_ACCESS_KEY" "$STORAGE_SECRET_KEY" >/dev/null
mc admin policy attach local amozeshyar-app --user "$STORAGE_ACCESS_KEY" >/dev/null 2>&1 || true
rm -f /tmp/app-policy.json
echo "minio-init: bucket «$BUCKET» private; app user limited to it."
