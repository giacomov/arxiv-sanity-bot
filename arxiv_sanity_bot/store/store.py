import base64
import json
from typing import Any

import firebase_admin  # type: ignore
from firebase_admin import credentials, firestore  # type: ignore

from arxiv_sanity_bot.config import FIREBASE_COLLECTION
from arxiv_sanity_bot.logger import get_logger

import os


logger = get_logger(__name__)


class DocumentStore:
    def __init__(self, firebase_credentials):
        cred = credentials.Certificate(firebase_credentials)
        firebase_admin.initialize_app(cred)
        self._client = firestore.client()

    @classmethod
    def from_env_variable(
        cls, env_variable_name: str = "FIREBASE_CREDENTIALS"
    ) -> "DocumentStore":
        return cls(
            firebase_credentials=cls._decode_credentials_from_env_variable(
                env_variable_name
            )
        )

    @staticmethod
    def _decode_credentials_from_env_variable(env_variable_name: str) -> dict[str, Any]:
        return json.loads(base64.b64decode(os.environ[env_variable_name]))

    def __setitem__(self, document_id: str, document_data: dict[str, Any]):
        doc_ref = self._client.collection(FIREBASE_COLLECTION).document(document_id)
        doc_ref.set(document_data)

        logger.info(f"Document created with ID: {document_id}")

    def __getitem__(self, document_id: str) -> dict[str, Any] | None:
        doc_ref = self._client.collection(FIREBASE_COLLECTION).document(document_id)
        return doc_ref.get().to_dict()

    def __contains__(self, document_id: str) -> bool:
        doc_ref = self._client.collection(FIREBASE_COLLECTION).document(document_id)
        return doc_ref.get().exists
