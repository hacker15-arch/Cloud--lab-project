from fastapi.testclient import TestClient


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
    user_id = "alice"

    # 1. Upload
    put_res = client.put(f"/objects/{object_name}?user_id={user_id}", content=payload)
    assert put_res.status_code == 201
    put_data = put_res.json()
    assert put_data["object_name"] == object_name
    assert put_data["size"] == len(payload)
    assert put_data["status"] == "stored"

    # 2. Download
    get_res = client.get(f"/objects/{object_name}?user_id={user_id}")
    assert get_res.status_code == 200
    assert get_res.content == payload


def test_upload_multipart_form(client: TestClient):
    """Test multipart/form-data upload using POST."""
    object_name = "form_upload.txt"
    file_bytes = b"Uploaded via multipart form data."
    user_id = "alice"

    files = {"file": ("form_upload.txt", file_bytes, "text/plain")}
    post_res = client.post(f"/objects/{object_name}?user_id={user_id}", files=files)
    assert post_res.status_code == 201
    assert post_res.json()["size"] == len(file_bytes)

    # Verify download
    get_res = client.get(f"/objects/{object_name}?user_id={user_id}")
    assert get_res.status_code == 200
    assert get_res.content == file_bytes


def test_object_metadata_and_head(client: TestClient):
    """Test GET metadata and HEAD request for object headers."""
    object_name = "data.json"
    payload = b'{"key": "value", "id": 12345}'
    user_id = "alice"

    client.put(f"/objects/{object_name}?user_id={user_id}", content=payload)

    # Test GET metadata
    meta_res = client.get(f"/objects/{object_name}/metadata?user_id={user_id}")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert meta["object_name"] == object_name
    assert meta["size"] == len(payload)
    assert "created_at" in meta
    assert "modified_at" in meta

    # Test HEAD request
    head_res = client.head(f"/objects/{object_name}?user_id={user_id}")
    assert head_res.status_code == 200
    assert head_res.headers["content-length"] == str(len(payload))
    assert "last-modified" in head_res.headers


def test_list_objects(client: TestClient):
    """Test listing stored objects."""
    user_id = "alice"

    # Initially empty
    list_res = client.get(f"/objects?user_id={user_id}")
    assert list_res.status_code == 200
    assert list_res.json()["count"] == 0

    # Upload two objects
    client.put(f"/objects/file1.bin?user_id={user_id}", content=b"123")
    client.put(f"/objects/file2.bin?user_id={user_id}", content=b"456789")

    list_res = client.get(f"/objects?user_id={user_id}")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["count"] == 2
    names = {item["object_name"] for item in data["objects"]}
    assert "file1.bin" in names
    assert "file2.bin" in names


def test_user_objects_are_isolated(client: TestClient):
    """Different users should only see their own uploaded objects."""
    user_a = "user_a"
    user_b = "user_b"

    client.put(f"/objects/shared.txt?user_id={user_a}", content=b"from-user-a")
    client.put(f"/objects/shared.txt?user_id={user_b}", content=b"from-user-b")

    user_a_objects = client.get(f"/objects?user_id={user_a}")
    assert user_a_objects.status_code == 200
    user_a_names = {item["object_name"] for item in user_a_objects.json()["objects"]}
    assert user_a_names == {"shared.txt"}

    user_b_objects = client.get(f"/objects?user_id={user_b}")
    assert user_b_objects.status_code == 200
    user_b_names = {item["object_name"] for item in user_b_objects.json()["objects"]}
    assert user_b_names == {"shared.txt"}

    # Each user should only see their own file even when filenames collide.
    assert client.get(f"/objects/shared.txt?user_id={user_a}").content == b"from-user-a"
    assert client.get(f"/objects/shared.txt?user_id={user_b}").content == b"from-user-b"


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
    user_id = "alice"

    put_res = client.put(f"/objects/{object_name}?user_id={user_id}", content=payload)
    assert put_res.status_code == 201

    get_res = client.get(f"/objects/{object_name}?user_id={user_id}")
    assert get_res.status_code == 200
    assert get_res.content == payload


def test_delete_object(client: TestClient):
    """Test deleting an object and verifying subsequent 404."""
    object_name = "delete_me.txt"
    payload = b"Temporary data"
    user_id = "alice"

    client.put(f"/objects/{object_name}?user_id={user_id}", content=payload)

    # Delete
    del_res = client.delete(f"/objects/{object_name}?user_id={user_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Attempt download after deletion
    get_res = client.get(f"/objects/{object_name}?user_id={user_id}")
    assert get_res.status_code == 404

    # Deleting again returns 404
    del_res_2 = client.delete(f"/objects/{object_name}?user_id={user_id}")
    assert del_res_2.status_code == 404


def test_path_traversal_protection(client: TestClient):
    """Verify that path traversal attempts are rejected."""
    # Attempt to upload outside storage path
    response = client.put("/objects/../../escaped.txt?user_id=alice", content=b"malicious")
    assert response.status_code in (400, 404)
