import mimetypes
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from app.api.auth import get_authenticated_user_id
from app.config import settings
from app.core.consistency import QuorumNotSatisfiedError, consistency_manager
from app.core.integrity import integrity_manager
from app.core.lock_manager import lock_manager
from app.core.partition import SplitBrainFencingError
from app.core.replication import replication_manager
from app.models.schemas import (
    ObjectDeleteResponse,
    ObjectHistoryResponse,
    ObjectIntegrityReport,
    ObjectListResponse,
    ObjectMetadata,
    ObjectUploadResponse,
)

router = APIRouter(tags=["Objects"])


def _normalize_user_id(user_id: Optional[str]) -> Optional[str]:
    """Normalize an incoming user identifier for ownership scoping."""
    if user_id is None:
        return None
    cleaned = str(user_id).strip()
    return cleaned or None


def _scoped_object_name(object_name: str, user_id: Optional[str]) -> str:
    """Prefix an object name with the user's ID so each account has isolated storage."""
    clean_name = object_name.strip("/")
    if not user_id:
        return clean_name
    user_prefix = f"{user_id}/"
    if clean_name.startswith(user_prefix):
        return clean_name
    return f"{user_prefix}{clean_name}"


def _display_object_name(object_name: str, user_id: Optional[str]) -> str:
    """Strip the user namespace before returning data to the client."""
    clean_name = object_name.strip("/")
    if not user_id:
        return clean_name
    user_prefix = f"{user_id}/"
    if clean_name.startswith(user_prefix):
        return clean_name[len(user_prefix):]
    return clean_name


@router.get("/objects", response_model=ObjectListResponse)
async def list_objects(
    request: Request,
    user_id: Optional[str] = Query(None, alias="user_id"),
):
    """List objects for the authenticated user only."""
    normalized_user_id = _normalize_user_id(get_authenticated_user_id(user_id, request.headers.get("authorization")))
    if not normalized_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: user_id is missing.",
        )

    objects = replication_manager.list_all_objects()
    filtered = [obj for obj in objects if obj.object_name.startswith(f"{normalized_user_id}/")]
    for obj in filtered:
        obj.object_name = _display_object_name(obj.object_name, normalized_user_id)
    return ObjectListResponse(count=len(filtered), objects=filtered)


@router.get("/admin/quorum/validate")
async def validate_quorum_config(
    write_quorum: int = Query(2, ge=1),
    read_quorum: int = Query(2, ge=1),
    replication_factor: int = Query(3, ge=1),
):
    """Validate whether write_quorum and read_quorum satisfy strict quorum consistency W + R > N."""
    try:
        return consistency_manager.validate_quorum(
            write_quorum=write_quorum,
            read_quorum=read_quorum,
            replication_factor=replication_factor,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/objects/{object_name:path}/versions", response_model=ObjectHistoryResponse)
async def get_object_versions(
    object_name: str,
    request: Request,
    user_id: Optional[str] = Query(None, alias="user_id"),
):
    """Retrieve full version history for a specific object under the current user namespace."""
    normalized_user_id = _normalize_user_id(get_authenticated_user_id(user_id, request.headers.get("authorization")))
    if not normalized_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: user_id is missing.",
        )

    scoped_name = _scoped_object_name(object_name, normalized_user_id)
    history = replication_manager.get_object_history(scoped_name)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object '{object_name}' not found",
        )
    history.object_name = _display_object_name(history.object_name, normalized_user_id)
    return history


@router.get("/objects/{object_name:path}/metadata", response_model=ObjectMetadata)
async def get_object_metadata(
    object_name: str,
    request: Request,
    user_id: Optional[str] = Query(None, alias="user_id"),
):
    """Retrieve metadata, version, checksum, and replica locations for an object."""
    normalized_user_id = _normalize_user_id(get_authenticated_user_id(user_id, request.headers.get("authorization")))
    if not normalized_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: user_id is missing.",
        )

    scoped_name = _scoped_object_name(object_name, normalized_user_id)
    try:
        meta = replication_manager.get_object_metadata(scoped_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object '{object_name}' not found in cluster metadata",
        )
    meta.object_name = _display_object_name(meta.object_name, normalized_user_id)
    return meta


@router.get("/objects/{object_name:path}/verify", response_model=ObjectIntegrityReport)
async def verify_object_integrity(
    object_name: str,
    request: Request,
    version: Optional[int] = Query(None, ge=1),
    user_id: Optional[str] = Query(None, alias="user_id"),
):
    """Perform on-demand SHA-256 integrity verification across all replicas of an object."""
    normalized_user_id = _normalize_user_id(get_authenticated_user_id(user_id, request.headers.get("authorization")))
    if not normalized_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: user_id is missing.",
        )

    scoped_name = _scoped_object_name(object_name, normalized_user_id)
    try:
        report = integrity_manager.verify_object_integrity(scoped_name, version=version)
        report.object_name = _display_object_name(report.object_name, normalized_user_id)
        return report
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.head("/objects/{object_name:path}")
async def head_object(
    object_name: str,
    request: Request,
    user_id: Optional[str] = Query(None, alias="user_id"),
):
    """Fast check for object existence, size, version, and checksum headers."""
    normalized_user_id = _normalize_user_id(get_authenticated_user_id(user_id, request.headers.get("authorization")))
    if not normalized_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: user_id is missing.",
        )

    scoped_name = _scoped_object_name(object_name, normalized_user_id)
    try:
        meta = replication_manager.get_object_metadata(scoped_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object '{object_name}' not found",
        )

    content_type, _ = mimetypes.guess_type(object_name)
    headers = {
        "Content-Length": str(meta.size),
        "Content-Type": content_type or "application/octet-stream",
        "Last-Modified": meta.modified_at.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "ETag": f'"{meta.checksum}"' if meta.checksum else "",
        "X-Vault-Version": str(meta.version),
        "X-Vault-Checksum": meta.checksum or "",
        "X-Vault-Replicas": ",".join(meta.replicas),
        "X-Vault-Replication-Factor": str(meta.replication_factor),
    }
    return Response(status_code=status.HTTP_200_OK, headers=headers)


@router.get("/objects/{object_name:path}")
async def download_object(
    object_name: str,
    request: Request,
    version: Optional[int] = Query(None, ge=1),
    read_quorum: Optional[int] = Query(None, ge=1),
    user_id: Optional[str] = Query(None, alias="user_id"),
):
    """Download an object's contents (latest or specific version) via streaming response enforcing read quorum."""
    normalized_user_id = _normalize_user_id(get_authenticated_user_id(user_id, request.headers.get("authorization")))
    if not normalized_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: user_id is missing.",
        )

    scoped_name = _scoped_object_name(object_name, normalized_user_id)
    rq = read_quorum
    if rq is None and "x-vault-read-quorum" in request.headers:
        try:
            rq = int(request.headers["x-vault-read-quorum"])
        except ValueError:
            pass

    async with lock_manager.read_lock(scoped_name):
        try:
            source_node, stream, quorum_achieved = await replication_manager.read_object_chunks(
                scoped_name, version=version, read_quorum=rq, chunk_size=settings.CHUNK_SIZE
            )
            meta = replication_manager.get_object_metadata(scoped_name)
            content_type, _ = mimetypes.guess_type(object_name)

            headers = {
                "Content-Disposition": f'attachment; filename="{object_name}"',
                "Content-Length": str(meta.size) if (meta and version is None) else "",
                "X-Vault-Served-By": source_node,
                "X-Vault-Version": str(version if version is not None else (meta.version if meta else 1)),
                "X-Vault-Checksum": meta.checksum or "" if (meta and version is None) else "",
                "X-Vault-Read-Quorum-Achieved": quorum_achieved,
            }

            return StreamingResponse(
                stream,
                media_type=content_type or "application/octet-stream",
                headers=headers,
            )
        except QuorumNotSatisfiedError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            )
        except FileNotFoundError:
            ver_str = f" (version {version})" if version else ""
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object '{object_name}'{ver_str} not found on any replica node",
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/objects/{object_name:path}", response_model=ObjectUploadResponse, status_code=status.HTTP_201_CREATED)
@router.post("/objects/{object_name:path}", response_model=ObjectUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_object(
    object_name: str,
    request: Request,
    response: Response,
    replication_factor: Optional[int] = Query(None, ge=1, le=10),
    write_quorum: Optional[int] = Query(None, ge=1),
    user_id: Optional[str] = Query(None, alias="user_id"),
):
    """Upload an object, create a new version, compute SHA-256, and replicate to nodes with write quorum."""
    normalized_user_id = _normalize_user_id(get_authenticated_user_id(user_id, request.headers.get("authorization")))
    if not normalized_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: user_id is missing.",
        )

    scoped_name = _scoped_object_name(object_name, normalized_user_id)
    rf = replication_factor
    if rf is None and "x-vault-replication-factor" in request.headers:
        try:
            rf = int(request.headers["x-vault-replication-factor"])
        except ValueError:
            pass

    wq = write_quorum
    if wq is None and "x-vault-write-quorum" in request.headers:
        try:
            wq = int(request.headers["x-vault-write-quorum"])
        except ValueError:
            pass

    content_type = request.headers.get("content-type", "")

    async with lock_manager.write_lock(scoped_name):
        try:
            if "multipart/form-data" in content_type:
                form = await request.form()
                file = form.get("file")
                if not file:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Form upload missing 'file' field",
                    )
                content = await file.read()
                upload_content_type = file.content_type
            else:
                content = await request.body()
                upload_content_type = content_type or None

            record = replication_manager.replicate_write(
                object_name=scoped_name,
                data=content,
                replication_factor=rf,
                write_quorum=wq,
                content_type=upload_content_type,
            )

            response.headers["X-Vault-Write-Quorum-Achieved"] = record.get("write_quorum_achieved", "")

            return ObjectUploadResponse(
                object_id=record["object_id"],
                object_name=_display_object_name(record["object_name"], normalized_user_id),
                version=record["version"],
                size=record["size"],
                checksum=record["checksum"],
                status="stored",
                message=f"Successfully stored version {record['version']} on {len(record['replicas'])} node(s)",
                replicas=record["replicas"],
                replication_factor=record["replication_factor"],
            )
        except (QuorumNotSatisfiedError, SplitBrainFencingError) as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store and replicate object: {str(e)}",
            )


@router.delete("/objects/{object_name:path}", response_model=ObjectDeleteResponse)
async def delete_object(
    object_name: str,
    request: Request,
    user_id: Optional[str] = Query(None, alias="user_id"),
):
    """Delete an object, its versions, and metadata across the cluster."""
    normalized_user_id = _normalize_user_id(get_authenticated_user_id(user_id, request.headers.get("authorization")))
    if not normalized_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: user_id is missing.",
        )

    scoped_name = _scoped_object_name(object_name, normalized_user_id)
    async with lock_manager.write_lock(scoped_name):
        try:
            deleted_from = replication_manager.delete_replicas(scoped_name)
            if not deleted_from:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Object '{object_name}' not found",
                )
            return ObjectDeleteResponse(
                object_name=_display_object_name(object_name, normalized_user_id),
                status="deleted",
                message=f"Object '{object_name}' and its versions deleted from {len(deleted_from)} node(s)",
                deleted_from_nodes=deleted_from,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

