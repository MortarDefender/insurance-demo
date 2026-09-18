import io
import pytest
from store import Store


@pytest.fixture
def store(settings):
    return Store(settings.STORE_DIR)


def test_create_and_get_questionnaire(store):
    qid = store.create_questionnaire(
        name="Health Check",
        questions=[
            {"prompt": "Do you smoke?", "type": "yesno", "required": True},
            {"prompt": "Age", "type": "number", "required": True},
        ],
    )
    q = store.get_questionnaire(qid)
    assert q["name"] == "Health Check"
    assert q["id"] == qid
    assert len(q["questions"]) == 2
    assert q["questions"][0]["type"] == "yesno"


def test_list_questionnaires(store):
    store.create_questionnaire(name="A", questions=[])
    store.create_questionnaire(name="B", questions=[])
    items = store.list_questionnaires()
    names = sorted(i["name"] for i in items)
    assert names == ["A", "B"]


def test_update_questionnaire(store):
    qid = store.create_questionnaire(name="Old", questions=[])
    store.update_questionnaire(qid, name="New",
                               questions=[{"prompt": "Q", "type": "text",
                                           "required": False}])
    q = store.get_questionnaire(qid)
    assert q["name"] == "New"
    assert len(q["questions"]) == 1


def test_delete_questionnaire(store):
    qid = store.create_questionnaire(name="Bye", questions=[])
    store.delete_questionnaire(qid)
    assert store.get_questionnaire(qid) is None


def test_create_and_get_document(store):
    did = store.create_document(display_name="NDA",
                                original_filename="nda.pdf",
                                file_bytes=b"%PDF-1.4 fake")
    doc = store.get_document(did)
    assert doc["display_name"] == "NDA"
    assert doc["original_filename"] == "nda.pdf"
    assert doc["ext"] == "pdf"
    data = store.read_document_bytes(did)
    assert data == b"%PDF-1.4 fake"


def test_list_and_delete_document(store):
    did = store.create_document(display_name="Doc",
                                original_filename="d.docx",
                                file_bytes=b"zip")
    assert len(store.list_documents()) == 1
    store.delete_document(did)
    assert store.get_document(did) is None
    assert store.list_documents() == []
