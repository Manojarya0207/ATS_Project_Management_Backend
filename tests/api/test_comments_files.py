"""API tests: comments and file attachments."""

from __future__ import annotations

from tests.conftest import unwrap
from tests.factories import make_comment, make_member, make_project, make_task


async def test_comment_crud_and_ownership(
    client, db, admin_user, employee_user, admin_headers, employee_headers
):
    project = await make_project(db, creator=admin_user)
    await make_member(db, project=project, user=employee_user)
    task = await make_task(db, project=project, creator=admin_user)

    # Employee comments
    r = await client.post(
        f"/api/v1/tasks/{task.id}/comments",
        headers=employee_headers,
        json={"content": "First!"},
    )
    assert r.status_code == 201
    comment_id = unwrap(r)["id"]

    # Listing (ordered asc) with envelope
    await make_comment(db, task=task, user=admin_user, content="Second")
    r = await client.get(f"/api/v1/tasks/{task.id}/comments", headers=admin_headers)
    contents = [c["content"] for c in unwrap(r)]
    assert contents == ["First!", "Second"]

    # Author edits own comment
    r = await client.patch(
        f"/api/v1/comments/{comment_id}", headers=employee_headers, json={"content": "Edited"}
    )
    assert r.status_code == 200
    assert unwrap(r)["content"] == "Edited"

    # Admin can edit anyone's comment; author-only for others
    r = await client.patch(
        f"/api/v1/comments/{comment_id}", headers=admin_headers, json={"content": "Admin edit"}
    )
    assert r.status_code == 200

    # Author deletes
    r = await client.delete(f"/api/v1/comments/{comment_id}", headers=employee_headers)
    assert r.status_code == 204


async def test_non_author_cannot_edit_comment(
    client, db, admin_user, employee_user, employee_headers
):
    project = await make_project(db, creator=admin_user)
    await make_member(db, project=project, user=employee_user)
    task = await make_task(db, project=project, creator=admin_user)
    comment = await make_comment(db, task=task, user=admin_user)

    r = await client.patch(
        f"/api/v1/comments/{comment.id}", headers=employee_headers, json={"content": "Hijack"}
    )
    assert r.status_code == 403


async def test_file_upload_download_roundtrip(client, db, admin_user, admin_headers):
    project = await make_project(db, creator=admin_user)
    task = await make_task(db, project=project, creator=admin_user)

    r = await client.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=admin_headers,
        files={"file": ("report.txt", b"quarterly numbers", "text/plain")},
    )
    assert r.status_code == 201
    data = unwrap(r)
    assert data["original_filename"] == "report.txt"
    assert data["size_bytes"] == len(b"quarterly numbers")

    r = await client.get(f"/api/v1/files/{data['id']}/download", headers=admin_headers)
    assert r.status_code == 200
    assert r.content == b"quarterly numbers"  # raw stream, not enveloped


async def test_file_listing(client, db, admin_user, admin_headers):
    project = await make_project(db, creator=admin_user)
    task = await make_task(db, project=project, creator=admin_user)
    for name in ("a.txt", "b.txt"):
        await client.post(
            f"/api/v1/tasks/{task.id}/files",
            headers=admin_headers,
            files={"file": (name, b"x", "text/plain")},
        )
    r = await client.get(f"/api/v1/tasks/{task.id}/files", headers=admin_headers)
    assert len(unwrap(r)) == 2


async def test_non_member_cannot_access_files(
    client, db, admin_user, admin_headers, employee_headers
):
    project = await make_project(db, creator=admin_user)
    task = await make_task(db, project=project, creator=admin_user)
    r = await client.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=admin_headers,
        files={"file": ("secret.txt", b"secret", "text/plain")},
    )
    file_id = unwrap(r)["id"]

    r = await client.get(f"/api/v1/files/{file_id}/download", headers=employee_headers)
    assert r.status_code == 403
