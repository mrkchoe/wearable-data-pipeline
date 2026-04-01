"""S3-compatible client (AWS or MinIO via endpoint URL)."""

from __future__ import annotations

import os
from typing import Iterator

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError


def get_s3_client() -> BaseClient:
    kwargs: dict = {}
    endpoint = (os.getenv("S3_ENDPOINT_URL") or "").strip()
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    region = (os.getenv("AWS_DEFAULT_REGION") or "us-east-1").strip()
    kwargs["region_name"] = region
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        **kwargs,
    )


def bucket_name() -> str:
    name = (os.getenv("S3_BUCKET") or "").strip()
    if not name:
        raise ValueError("S3_BUCKET must be set in environment.")
    return name


def s3_prefix() -> str:
    return (os.getenv("S3_PREFIX") or "raw").strip().strip("/")


def ensure_bucket(client: BaseClient, bucket: str, log) -> None:
    try:
        client.head_bucket(Bucket=bucket)
        log.info("Bucket exists: %s", bucket)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket", "NotFound"):
            log.info("Creating bucket: %s", bucket)
            client.create_bucket(Bucket=bucket)
        else:
            raise


def put_object_with_checksum(
    client: BaseClient,
    bucket: str,
    key: str,
    body: bytes,
    checksum_sha256: str,
    log,
) -> str | None:
    resp = client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        Metadata={"sha256": checksum_sha256},
    )
    etag = resp.get("ETag")
    if isinstance(etag, str):
        etag = etag.strip('"')
    log.info("Uploaded s3://%s/%s (%s bytes, etag=%s)", bucket, key, len(body), etag)
    return etag


def head_object_meta(client: BaseClient, bucket: str, key: str) -> dict | None:
    try:
        return client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def iter_objects_under(
    client: BaseClient,
    bucket: str,
    prefix: str,
) -> Iterator[dict]:
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents") or []:
            yield obj


def download_object_bytes(client: BaseClient, bucket: str, key: str) -> bytes:
    resp = client.get_object(Bucket=bucket, Key=key)
    body = resp["Body"]
    try:
        return body.read()
    finally:
        body.close()
