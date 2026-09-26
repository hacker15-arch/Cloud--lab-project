from fastapi.testclient import TestClient


def register_user(client: TestClient, name: str, email: str, password: str = "secret123"):
    """Create a real backend user account and return the authenticated payload."""
    response = client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_root_endpoint(client: TestClient):
    """Test root information endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Vault" in data["service"]
    assert "version" in data


def test_health_check(client: TestClient):
    """Test health check returns 200 and storage is marked accessible."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["storage_accessible"] is True
    assert data["total_nodes"] == 5
    assert data["online_nodes"] == 5


def test_upload_and_download_raw_bytes(client: TestClient):
    """Test PUT upload with raw binary content and subsequent GET download."""
    object_name = "sample.txt"
    payload = b"Hello, Vault object storage!"
    user = register_user(client, "Alice", "alice@example.com")
    user_id = user["user_id"]
    headers = {"Authorization": f"Bearer {user['token']}"}

    # 1. Upload
    put_res = client.put(f"/objects/{object_name}?user_id={user_id}", content=payload, headers=headers)
    assert put_res.status_code == 201
    put_data = put_res.json()
    assert put_data["object_name"] == object_name
    assert put_data["size"] == len(payload)
    assert put_data["status"] == "stored"

    # 2. Download
    get_res = client.get(f"/objects/{object_name}?user_id={user_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.content == payload


def test_upload_multipart_form(client: TestClient):
    """Test multipart/form-data upload using POST."""
    object_name = "form_upload.txt"
    file_bytes = b"Uploaded via multipart form data."
    user = register_user(client, "Alice", "alice2@example.com")
    user_id = user["user_id"]
    headers = {"Authorization": f"Bearer {user['token']}"}

    files = {"file": ("form_upload.txt", file_bytes, "text/plain")}
    post_res = client.post(f"/objects/{object_name}?user_id={user_id}", files=files, headers=headers)
    assert post_res.status_code == 201
    assert post_res.json()["size"] == len(file_bytes)

    # Verify download
    get_res = client.get(f"/objects/{object_name}?user_id={user_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.content == file_bytes


def test_object_metadata_and_head(client: TestClient):
    """Test GET metadata and HEAD request for object headers."""
    object_name = "data.json"
    payload = b'{"key": "value", "id": 12345}'
    user = register_user(client, "Alice", "alice3@example.com")
    user_id = user["user_id"]
    headers = {"Authorization": f"Bearer {user['token']}"}

    client.put(f"/objects/{object_name}?user_id={user_id}", content=payload, headers=headers)

    # Test GET metadata
    meta_res = client.get(f"/objects/{object_name}/metadata?user_id={user_id}", headers=headers)
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert meta["object_name"] == object_name
    assert meta["size"] == len(payload)
    assert "created_at" in meta
    assert "modified_at" in meta

    # Test HEAD request
    head_res = client.head(f"/objects/{object_name}?user_id={user_id}", headers=headers)
    assert head_res.status_code == 200
    assert head_res.headers["content-length"] == str(len(payload))
    assert "last-modified" in head_res.headers


def test_list_objects(client: TestClient):
    """Test listing stored objects."""
    user = register_user(client, "Alice", "alice4@example.com")
    user_id = user["user_id"]
    headers = {"Authorization": f"Bearer {user['token']}"}

    # Initially empty
    list_res = client.get(f"/objects?user_id={user_id}", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["count"] == 0

    # Upload two objects
    client.put(f"/objects/file1.bin?user_id={user_id}", content=b"123", headers=headers)
    client.put(f"/objects/file2.bin?user_id={user_id}", content=b"456789", headers=headers)

    list_res = client.get(f"/objects?user_id={user_id}", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["count"] == 2
    names = {item["object_name"] for item in data["objects"]}
    assert "file1.bin" in names
    assert "file2.bin" in names


def test_user_objects_are_isolated(client: TestClient):
    """Different users should only see their own uploaded objects."""
    user_a = register_user(client, "Alice", "usera@example.com")
    user_b = register_user(client, "Bob", "userb@example.com")
    headers_a = {"Authorization": f"Bearer {user_a['token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['token']}"}

    client.put(f"/objects/shared.txt?user_id={user_a['user_id']}", content=b"from-user-a", headers=headers_a)
    client.put(f"/objects/shared.txt?user_id={user_b['user_id']}", content=b"from-user-b", headers=headers_b)

    user_a_objects = client.get(f"/objects?user_id={user_a['user_id']}", headers=headers_a)
    assert user_a_objects.status_code == 200
    user_a_names = {item["object_name"] for item in user_a_objects.json()["objects"]}
    assert user_a_names == {"shared.txt"}

    user_b_objects = client.get(f"/objects?user_id={user_b['user_id']}", headers=headers_b)
    assert user_b_objects.status_code == 200
    user_b_names = {item["object_name"] for item in user_b_objects.json()["objects"]}
    assert user_b_names == {"shared.txt"}

    # Each user should only see their own file even when filenames collide.
    assert client.get(f"/objects/shared.txt?user_id={user_a['user_id']}", headers=headers_a).content == b"from-user-a"
    assert client.get(f"/objects/shared.txt?user_id={user_b['user_id']}", headers=headers_b).content == b"from-user-b"


def test_objects_require_user_identity(client: TestClient):
    """Object access must include a user_id to enforce per-user privacy."""
    response = client.get("/objects")
    assert response.status_code == 401

    upload_response = client.put("/objects/private.txt", content=b"secret")
    assert upload_response.status_code == 401


def test_nested_path_object(client: TestClient):
    """Test uploading and retrieving objects with nested directory paths."""
    object_name = "documents/reports/2026/quarter1.pdf"
    payload = b"%PDF-1.4 simulated pdf bytes"
    user = register_user(client, "Alice", "alice5@example.com")
    user_id = user["user_id"]
    headers = {"Authorization": f"Bearer {user['token']}"}

    put_res = client.put(f"/objects/{object_name}?user_id={user_id}", content=payload, headers=headers)
    assert put_res.status_code == 201

    get_res = client.get(f"/objects/{object_name}?user_id={user_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.content == payload


def test_delete_object(client: TestClient):
    """Test deleting an object and verifying subsequent 404."""
    object_name = "delete_me.txt"
    payload = b"Temporary data"
    user = register_user(client, "Alice", "alice6@example.com")
    user_id = user["user_id"]
    headers = {"Authorization": f"Bearer {user['token']}"}

    client.put(f"/objects/{object_name}?user_id={user_id}", content=payload, headers=headers)

    # Delete
    del_res = client.delete(f"/objects/{object_name}?user_id={user_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Attempt download after deletion
    get_res = client.get(f"/objects/{object_name}?user_id={user_id}", headers=headers)
    assert get_res.status_code == 404

    # Deleting again returns 404
    del_res_2 = client.delete(f"/objects/{object_name}?user_id={user_id}", headers=headers)
    assert del_res_2.status_code == 404


def test_real_user_auth_keeps_other_users_private(client: TestClient):
    """Users must register and log in with their own identity, and each account sees only its own objects."""
    user_a = client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "secret123"},
    )
    user_b = client.post(
        "/auth/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "secret123"},
    )
    assert user_a.status_code == 200
    assert user_b.status_code == 200

    alice = user_a.json()
    bob = user_b.json()
    assert alice["user_id"] != bob["user_id"]

    upload_a = client.put(
        "/objects/shared.txt?user_id={user_id}".format(user_id=alice["user_id"]),
        content=b"alice-file",
        headers={"Authorization": f"Bearer {alice['token']}"},
    )
    upload_b = client.put(
        "/objects/shared.txt?user_id={user_id}".format(user_id=bob["user_id"]),
        content=b"bob-file",
        headers={"Authorization": f"Bearer {bob['token']}"},
    )
    assert upload_a.status_code == 201
    assert upload_b.status_code == 201

    list_a = client.get(
        "/objects",
        params={"user_id": alice["user_id"]},
        headers={"Authorization": f"Bearer {alice['token']}"},
    )
    list_b = client.get(
        "/objects",
        params={"user_id": bob["user_id"]},
        headers={"Authorization": f"Bearer {bob['token']}"},
    )
    assert list_a.status_code == 200
    assert list_b.status_code == 200
    assert {item["object_name"] for item in list_a.json()["objects"]} == {"shared.txt"}
    assert {item["object_name"] for item in list_b.json()["objects"]} == {"shared.txt"}
    assert client.get(
        "/objects/shared.txt",
        params={"user_id": alice["user_id"]},
        headers={"Authorization": f"Bearer {alice['token']}"},
    ).content == b"alice-file"
    assert client.get(
        "/objects/shared.txt",
        params={"user_id": bob["user_id"]},
        headers={"Authorization": f"Bearer {bob['token']}"},
    ).content == b"bob-file"


def test_path_traversal_protection(client: TestClient):
    """Verify that path traversal attempts are rejected."""
    user = register_user(client, "Alice", "alice7@example.com")
    headers = {"Authorization": f"Bearer {user['token']}"}
    # Attempt to upload outside storage path
    response = client.put(
        f"/objects/../../escaped.txt?user_id={user['user_id']}",
        content=b"malicious",
        headers=headers,
    )
    assert response.status_code in (400, 404)
