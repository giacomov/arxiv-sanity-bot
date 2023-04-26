import os
import base64
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from mockfirestore import MockFirestore

from arxiv_sanity_bot.store.store import DocumentStore


FIREBASE_COLLECTION = 'test_collection'


def get_resource(resource):
    current_file_dir = Path(__file__).parent

    # Create the path to the resource file
    return current_file_dir / "resources" / resource

@pytest.fixture(scope='module')
def store():
    firebase_credentials = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "123",
        "private_key": open(get_resource("fake_private_key.pem")).read(),
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project.iam.gserviceaccount.com"
    }

    os.environ['FIREBASE_CREDENTIALS'] = base64.b64encode(json.dumps(firebase_credentials).encode()).decode()

    with patch("firebase_admin.initialize_app") as mock_initialize_app:
        with patch("firebase_admin.firestore.client", return_value=MockFirestore()) as mock_client:

            store = DocumentStore.from_env_variable()

            yield store


def test_set_and_get(store):

    item = {
        'one': 'two'
    }

    store['hey'] = item

    assert store['hey'] == item


def test_membership(store):

    item1 = {
        'one': 'two'
    }

    item2 = {
        'three': 'four'
    }

    store['one'] = item1
    store['two'] = item2

    assert 'one' in store
    assert 'two' in store
    assert 'three' not in store
