"""Encrypt a legacy workspace in one transaction when its owner claims it.

There are no plaintext backups in the application. Database provider snapshots
may retain older versions until their retention window passes.
"""

import json

from psycopg.types.json import Jsonb

from . import vault


def encrypt_workspace(db, wid):
    db.execute("SELECT id FROM workspaces WHERE id=%s FOR UPDATE", (wid,))
    documents = db.execute("SELECT id,name,pdf FROM documents WHERE workspace_id=%s AND NOT encrypted FOR UPDATE", (wid,)).fetchall()
    for doc in documents:
        did = doc["id"]
        pages = db.execute("SELECT page_number,text FROM pages WHERE document_id=%s", (did,)).fetchall()
        for page in pages:
            db.execute("UPDATE pages SET text=%s WHERE document_id=%s AND page_number=%s", (vault.seal_text(page["text"], f"{wid}:page:{did}:{page['page_number']}"), did, page["page_number"]))
        chunks = db.execute("SELECT id,text FROM chunks WHERE document_id=%s", (did,)).fetchall()
        for chunk in chunks:
            db.execute("UPDATE chunks SET text=%s WHERE id=%s", (vault.seal_text(chunk["text"], f"{wid}:chunk:{chunk['id']}"), chunk["id"]))
        db.execute("UPDATE documents SET name=%s,pdf=%s,encrypted=true WHERE id=%s AND workspace_id=%s", (vault.seal_text(doc["name"], f"{wid}:document:{did}:name"), vault.seal(bytes(doc["pdf"]), f"{wid}:document:{did}:pdf"), did, wid))
    runs = db.execute("SELECT id,question,result FROM runs WHERE workspace_id=%s AND NOT encrypted FOR UPDATE", (wid,)).fetchall()
    for run in runs:
        rid, result = run["id"], run["result"]
        metadata = {"sealed": vault.seal_text(json.dumps(result), f"{wid}:run:{rid}:result"), **{k: result.get(k) for k in ("counts", "latency_ms", "abstained")}}
        db.execute("UPDATE runs SET question=%s,result=%s,encrypted=true WHERE id=%s AND workspace_id=%s", (vault.seal_text(run["question"], f"{wid}:run:{rid}:question"), Jsonb(metadata), rid, wid))
    return {"documents": len(documents), "answers": len(runs)}
