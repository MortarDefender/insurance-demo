"""File-backed storage for templates. This is the only persistent data in the
app. No client data is ever stored here."""

import json
import os
import uuid


class Store:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.q_dir = os.path.join(base_dir, "questionnaires")
        self.d_dir = os.path.join(base_dir, "documents")
        os.makedirs(self.q_dir, exist_ok=True)
        os.makedirs(self.d_dir, exist_ok=True)

    # ---- questionnaires ----
    def _q_path(self, qid):
        return os.path.join(self.q_dir, f"{qid}.json")

    def create_questionnaire(self, *, name, questions):
        qid = uuid.uuid4().hex
        data = {"id": qid, "name": name, "questions": questions}
        with open(self._q_path(qid), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return qid

    def get_questionnaire(self, qid):
        path = self._q_path(qid)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def list_questionnaires(self):
        items = []
        for name in os.listdir(self.q_dir):
            if name.endswith(".json"):
                with open(os.path.join(self.q_dir, name), encoding="utf-8") as f:
                    items.append(json.load(f))
        return items

    def update_questionnaire(self, qid, *, name, questions):
        if self.get_questionnaire(qid) is None:
            raise KeyError(qid)
        data = {"id": qid, "name": name, "questions": questions}
        with open(self._q_path(qid), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def delete_questionnaire(self, qid):
        path = self._q_path(qid)
        if os.path.exists(path):
            os.remove(path)

    # ---- documents ----
    def _d_json(self, did):
        return os.path.join(self.d_dir, f"{did}.json")

    def _d_file(self, did, ext):
        return os.path.join(self.d_dir, f"{did}.{ext}")

    def create_document(self, *, display_name, original_filename, file_bytes):
        did = uuid.uuid4().hex
        ext = original_filename.rsplit(".", 1)[-1].lower() if "." in \
            original_filename else "bin"
        with open(self._d_file(did, ext), "wb") as f:
            f.write(file_bytes)
        meta = {"id": did, "display_name": display_name,
                "original_filename": original_filename, "ext": ext}
        with open(self._d_json(did), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return did

    def get_document(self, did):
        path = self._d_json(did)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def read_document_bytes(self, did):
        meta = self.get_document(did)
        if meta is None:
            return None
        with open(self._d_file(did, meta["ext"]), "rb") as f:
            return f.read()

    def list_documents(self):
        items = []
        for name in os.listdir(self.d_dir):
            if name.endswith(".json"):
                with open(os.path.join(self.d_dir, name), encoding="utf-8") as f:
                    items.append(json.load(f))
        return items

    def delete_document(self, did):
        meta = self.get_document(did)
        if meta is None:
            return
        for path in (self._d_json(did), self._d_file(did, meta["ext"])):
            if os.path.exists(path):
                os.remove(path)
