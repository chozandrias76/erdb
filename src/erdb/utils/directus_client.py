import requests
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager


def _get_type(schema_type: str) -> str:
    return {
        "array": "json",
        "object": "json",
        "number": "decimal"
    }.get(schema_type, schema_type)

def _get_pk_field() -> Dict:
    return {
        "field": "ascii_name",
        "type": "string",
        "schema": {
            "is_primary_key": True, 
            "is_nullable": False, 
        }
    }

def _get_fields(properties: Dict[str, Dict]) -> List[Dict]:
    ret = []

    for name, data in properties.items():
        if name.startswith("$"): # $schema/comments
            continue

        ret.append({
            "field": name,
            "type": _get_type(data.get("type", "string"))
        })

    return ret

@dataclass
class DirectusClient:
    endpoint: str
    access_token: str
    active_folders: List[str] = field(default_factory=list)

    def _get_active_parent(self) -> Dict:
        return {} if len(self.active_folders) == 0 else {"group": self.active_folders[-1]}

    def _call(self, method: str, path: str, ignore_errors: bool = False, **kwargs) -> requests.Response:
        func = {
            "GET": requests.get,
            "POST": requests.post,
            "DELETE": requests.delete
        }[method]

        resp = func(
            url=f"{self.endpoint}{path}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            verify=True,
            **kwargs
        )

        if not ignore_errors:
            assert resp.status_code in [200, 204], (resp.status_code, resp.text)

        return resp

    def _get(self, path: str, ignore_errors: bool = False, **kwargs) -> requests.Response:
        return self._call("GET", path, ignore_errors, **kwargs)

    def _post(self, path: str, ignore_errors: bool = False, **kwargs) -> requests.Response:
        return self._call("POST", path, ignore_errors, **kwargs)

    def _delete(self, path: str, ignore_errors: bool = False, **kwargs) -> requests.Response:
        return self._call("DELETE", path, ignore_errors, **kwargs)

    def _collection_exists(self, collection: str) -> bool:
        collections = [col["collection"] for col in self._get("/collections").json()["data"]]
        return collection in collections

    def _delete_collection(self, collection: str, ignore_errors: bool = False):
        self._delete(f"/collections/{collection}", ignore_errors=ignore_errors)

    def _create_collection(self, collection: str, properties: Dict[str, Dict]):
        self._post("/collections",
            json={
                "collection": collection,
                "meta": self._get_active_parent(),
                "schema": {},
                "fields": [_get_pk_field()] + _get_fields(properties)
            }
        )

        self._post("/permissions",
            json={
                "collection": collection,
                "action": "read",
                "role": None, # None - public
                "fields": ["*"]
            }
        )

    @contextmanager
    def enter_folder(self, name: str, collapsed: bool = True):
        self._delete(f"/collections/{name}", ignore_errors=True)
        self._post("/collections", ignore_errors=True,
            json={
                "collection": name,
                "meta": self._get_active_parent() | {"collapse": collapsed},
                "schema": None
            }
        )

        self.active_folders.append(name)
        yield
        del self.active_folders[-1]

    def update_collection(self, collection: str, properties: Dict[str, Dict]):
        print(f"Creating collection \"{collection}\"...", flush=True)

        self._delete_collection(collection, ignore_errors=True)
        self._create_collection(collection, properties)

    def import_data(self, collection: str, data: Dict[str, Dict]):
        if len(data) == 0:
            print("Skipping an attempt to import zero-length data", flush=True)
            return

        data: List[Dict] = [{"ascii_name": name} | props for name, props in data.items()]

        print(f"Importing {len(data)} items...", flush=True)
        self._post(f"/utils/import/{collection}",
            files={"file": (f"{collection}.json", json.dumps(data), "application/json")}
        )

    @classmethod
    @contextmanager
    def as_user(cls, endpoint: str, email: str, password: str) -> "DirectusClient":
        def fetch_tokens() -> Tuple[str, str]:
            resp = requests.post(f"{endpoint}/auth/login",
                json={"email": email, "password": password}
            )

            assert resp.status_code == 200, "Authentication failure"
            print(f"Logged in to Directus instance at \"{endpoint}\".", flush=True)

            auth = resp.json()["data"]
            return (auth["access_token"], auth["refresh_token"])

        def logout(refresh_token: str):
            requests.post(f"{endpoint}/auth/logout",
                json={"refresh_token": refresh_token}
            )
            print(f"Logged out from Directus.", flush=True)

        access_token, refresh_token = fetch_tokens()

        try:
            yield cls(endpoint, access_token)

        finally:
            logout(refresh_token)