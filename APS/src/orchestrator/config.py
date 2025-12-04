from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

try:
    import boto3  # optional; only used when running in AWS
except Exception:  # pragma: no cover
    boto3 = None  # type: ignore


@dataclass
class AppConfig:
    aws_region: str
    ocr_mode: str
    openai_model: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            ocr_mode=os.getenv("OCR_MODE", "auto"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )


def get_secret_env_or_aws(env_name: str, secret_arn_env: str) -> Optional[str]:
    """
    Secret resolution order:
      1) Return os.environ[env_name] if present
      2) Else, if os.environ[secret_arn_env] is set, fetch from AWS Secrets Manager.
         Accepted SecretString formats:
            - raw string
            - JSON object containing: env_name or 'value' or 'api_key' or 'token'
      3) Else, None
    """
    direct = os.getenv(env_name)
    if direct:
        return direct

    secret_arn = os.getenv(secret_arn_env)
    if not secret_arn or boto3 is None:
        return None

    region = os.getenv("AWS_REGION") or None
    client = boto3.client("secretsmanager", region_name=region) if region else boto3.client("secretsmanager")
    resp = client.get_secret_value(SecretId=secret_arn)
    secret = resp.get("SecretString")
    if not secret:
        blob = resp.get("SecretBinary")
        if blob:
            try:
                secret = blob.decode("utf-8")
            except Exception:
                return None

    if not secret:
        return None

    try:
        obj = json.loads(secret)
        for key in (env_name, "value", "api_key", "token"):
            if key in obj:
                return str(obj[key])
    except Exception:
        pass

    return secret
