import base64
import json

import firebase_admin
from firebase_admin import credentials, firestore

from arxiv_sanity_bot.config import FIREBASE_COLLECTION
from arxiv_sanity_bot.events import InfoEvent

import os


class DocumentStore:
    def __init__(self, firebase_credentials):
        cred = credentials.Certificate(firebase_credentials)
        firebase_admin.initialize_app(cred)
        self._client = firestore.client()

    @classmethod
    def from_env_variable(cls, env_variable_name="FIREBASE_CREDENTIALS"):
        return cls(
            firebase_credentials=cls._decode_credentials_from_env_variable(
                env_variable_name
            )
        )

    @staticmethod
    def _decode_credentials_from_env_variable(env_variable_name):
        return json.loads(base64.b64decode(os.environ[env_variable_name]))

    def __setitem__(self, document_id, document_data):
        doc_ref = self._client.collection(FIREBASE_COLLECTION).document(document_id)
        doc_ref.set(document_data)

        InfoEvent(msg=f"Document created with ID: {document_id}")

    def __getitem__(self, document_id):
        doc_ref = self._client.collection(FIREBASE_COLLECTION).document(document_id)
        return doc_ref.get().to_dict()

    def __contains__(self, document_id):
        doc_ref = self._client.collection(FIREBASE_COLLECTION).document(document_id)
        return doc_ref.get().exists
