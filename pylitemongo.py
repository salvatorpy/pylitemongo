# litepymongo.py
import os
import re
import time
import json
import sqlite3
import binascii
from typing import Optional, List, Tuple, Iterable, Any, Dict

# =========================
# Errors
# =========================
class MongoLiteError(Exception):
    """Base class for MongoLite errors."""
    pass

class DocumentNotFoundError(MongoLiteError):
    """Raised when no document matches the query."""
    pass

class InvalidQueryError(MongoLiteError):
    """Raised when query syntax is invalid."""
    pass

class InvalidUpdateError(MongoLiteError):
    """Raised when update operator is invalid."""
    pass

class DuplicateKeyError(MongoLiteError):
    """Raised when violating unique key (_id) constraint."""
    pass

class InvalidDocumentError(MongoLiteError):
    """Raised when document doesn't satisfy collection schema."""
    pass


# =========================
# Utils
# =========================
def generate_object_id() -> str:
    """Generate a 24-char hex string similar to Mongo ObjectId."""
    ts = int(time.time())
    rand = binascii.b2a_hex(os.urandom(8)).decode("ascii")
    return f"{ts:08x}{rand}"[:24]

def deep_get(doc: dict, dotted_key: str, default=None):
    parts = dotted_key.split(".")
    cur = doc
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

def deep_set(doc: dict, dotted_key: str, value):
    parts = dotted_key.split(".")
    cur = doc
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value

def deep_unset(doc: dict, dotted_key: str):
    parts = dotted_key.split(".")
    cur = doc
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            return
        cur = cur[p]
    cur.pop(parts[-1], None)

def is_array(x):
    return isinstance(x, list)


# =========================
# Results (pymongo-like)
# =========================
class InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class UpdateResult:
    def __init__(self, matched_count, modified_count, upserted_id=None):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.upserted_id = upserted_id

class DeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


# =========================
# Query engine
# =========================
COMPARATORS = {
    "$eq", "$ne", "$gt", "$gte", "$lt", "$lte",
    "$in", "$nin", "$exists", "$regex", "$size",
    "$all", "$elemMatch"
}
LOGICAL = {"$and", "$or", "$not"}

def match_query(doc: dict, query: dict) -> bool:
    if not isinstance(query, dict):
        raise InvalidQueryError("Query must be a dict.")
    for key, cond in query.items():
        if key in LOGICAL:
            if not _eval_logical(doc, key, cond):
                return False
        else:
            if not _eval_field(doc, key, cond):
                return False
    return True

def _eval_logical(doc: dict, op: str, clauses):
    if op in {"$and", "$or"}:
        if not isinstance(clauses, list):
            raise InvalidQueryError(f"{op} requires a list of clauses.")
        results = [match_query(doc, clause) for clause in clauses]
        return all(results) if op == "$and" else any(results)
    if op == "$not":
        if not isinstance(clauses, dict):
            raise InvalidQueryError("$not requires a single clause object.")
        return not match_query(doc, clauses)
    raise InvalidQueryError(f"Unsupported logical operator: {op}")

def _eval_field(doc: dict, dotted_key: str, cond):
    value = deep_get(doc, dotted_key, None)
    if isinstance(cond, dict):
        for op, arg in cond.items():
            if op not in COMPARATORS:
                raise InvalidQueryError(f"Unsupported operator: {op}")
            if not _eval_op(value, op, arg):
                return False
        return True
    else:
        return value == cond

def _eval_op(val, op, arg):
    if op == "$eq": return val == arg
    if op == "$ne": return val != arg
    if op == "$gt": return val is not None and val > arg
    if op == "$gte": return val is not None and val >= arg
    if op == "$lt": return val is not None and val < arg
    if op == "$lte": return val is not None and val <= arg
    if op == "$in": return val in arg
    if op == "$nin": return val not in arg
    if op == "$exists": return (val is not None) if arg else (val is None)
    if op == "$regex":
        if val is None or not isinstance(val, str):
            return False
        pattern, flags = _parse_regex(arg)
        return re.search(pattern, val, flags) is not None
    if op == "$size":
        if not hasattr(val, "__len__"):
            return False
        return len(val) == arg
    if op == "$all":
        if not is_array(val):
            return False
        return all(item in val for item in arg)
    if op == "$elemMatch":
        if not is_array(val):
            return False
        return any(match_query(elem, arg) if isinstance(elem, dict) else _match_scalar(elem, arg) for elem in val)
    return False

def _match_scalar(x, spec):
    if not isinstance(spec, dict):
        return x == spec
    for sop, sarg in spec.items():
        if sop == "$eq" and x == sarg: return True
        if sop == "$ne" and x != sarg: return True
        if sop == "$gt" and x > sarg: return True
        if sop == "$gte" and x >= sarg: return True
        if sop == "$lt" and x < sarg: return True
        if sop == "$lte" and x <= sarg: return True
        if sop == "$in" and x in sarg: return True
        if sop == "$nin" and x not in sarg: return True
    return False

def _parse_regex(arg):
    if isinstance(arg, str):
        return arg, 0
    if isinstance(arg, dict):
        pattern = arg.get("pattern", "")
        options = arg.get("options", "")
        flags = 0
        if "i" in options: flags |= re.IGNORECASE
        if "m" in options: flags |= re.MULTILINE
        if "s" in options: flags |= re.DOTALL
        return pattern, flags
    raise InvalidQueryError("$regex must be a string or dict {pattern, options}.")


# =========================
# Cursor
# =========================
class Cursor:
    def __init__(self, rows: List[Tuple[int, str]], projection: Optional[dict] = None,
                 sort: Optional[List[Tuple[str, int]]] = None, skip: int = 0, limit: int = 0):
        self._rows = rows  # list of (id, json_str)
        self._projection = projection
        self._sort = sort or []
        self._skip = max(0, skip)
        self._limit = max(0, limit)

    def project(self, doc):
        if not self._projection:
            return doc
        include = {k for k, v in self._projection.items() if v}
        exclude = {k for k, v in self._projection.items() if not v}
        if include:
            out = {}
            for k in include:
                val = deep_get(doc, k, None)
                if val is not None:
                    deep_set(out, k, val) if "." in k else out.__setitem__(k, val)
            if "_id" in self._projection and not self._projection["_id"]:
                out.pop("_id", None)
            return out
        if exclude:
            out = json.loads(json.dumps(doc))
            for k in exclude:
                deep_unset(out, k)
            return out
        return doc

    def sort_docs(self, docs: List[dict]) -> List[dict]:
        if not self._sort:
            return docs
        for key, direction in reversed(self._sort):
            reverse = direction < 0
            docs.sort(key=lambda d: deep_get(d, key, None), reverse=reverse)
        return docs

    def __iter__(self):
        docs = [json.loads(row[1]) for row in self._rows]
        docs = self.sort_docs(docs)
        if self._skip:
            docs = docs[self._skip:]
        if self._limit:
            docs = docs[:self._limit]
        for d in docs:
            yield self.project(d)

    def to_list(self, length: Optional[int] = None) -> List[dict]:
        out = []
        for idx, d in enumerate(self):
            if length is not None and idx >= length:
                break
            out.append(d)
        return out

    def count(self) -> int:
        return len(list(self))


# =========================
# Aggregation (basic)
# =========================
def aggregate_docs(docs: List[dict], pipeline: List[dict]) -> List[dict]:
    out = docs
    for stage in pipeline:
        if not isinstance(stage, dict) or len(stage) != 1:
            raise InvalidQueryError("Each pipeline stage must be a single-key dict.")
        op, spec = next(iter(stage.items()))
        if op == "$match":
            out = [d for d in out if match_query(d, spec)]
        elif op == "$project":
            projected = []
            for d in out:
                cur = {}
                for k, v in spec.items():
                    if v in (1, True):
                        val = deep_get(d, k, None)
                        if val is not None:
                            deep_set(cur, k, val) if "." in k else cur.__setitem__(k, val)
                    elif isinstance(v, dict) and "$literal" in v:
                        cur[k] = v["$literal"]
                    elif isinstance(v, dict) and "$concat" in v:
                        cur[k] = "".join(str(deep_get(d, p[1:], "")) if isinstance(p, str) and p.startswith("$") else str(p) for p in v["$concat"])
                projected.append(cur)
            out = projected
        elif op == "$sort":
            keys = list(spec.items())  # [(k, dir)]
            for k, direction in reversed(keys):
                reverse = direction < 0
                out.sort(key=lambda d: deep_get(d, k, None), reverse=reverse)
        elif op == "$skip":
            out = out[spec:] if spec > 0 else out
        elif op == "$limit":
            out = out[:spec] if spec > 0 else out
        elif op == "$group":
            out = _agg_group(out, spec)
        elif op == "$count":
            out = [{"count": len(out)}]
        elif op == "$unwind":
            path = spec if isinstance(spec, str) else spec.get("path")
            path = path[1:] if isinstance(path, str) and path.startswith("$") else path
            unwound = []
            for d in out:
                arr = deep_get(d, path, [])
                if not isinstance(arr, list): continue
                for item in arr:
                    nd = json.loads(json.dumps(d))
                    deep_set(nd, path, item)
                    unwound.append(nd)
            out = unwound
        else:
            raise InvalidQueryError(f"Unsupported aggregation stage: {op}")
    return out

def _agg_group(docs: List[dict], spec: dict) -> List[dict]:
    _id_expr = spec.get("_id", None)
    accumulators = {k: v for k, v in spec.items() if k != "_id"}

    def key_for(d):
        if isinstance(_id_expr, str) and _id_expr.startswith("$"):
            return deep_get(d, _id_expr[1:], None)
        return _id_expr

    buckets: Dict[Any, Dict[str, Any]] = {}
    for d in docs:
        k = key_for(d)
        if k not in buckets:
            buckets[k] = {"_id": k}
            for field, acc in accumulators.items():
                op, arg = next(iter(acc.items()))
                if op in ("$sum", "$avg"): buckets[k][field] = 0
                elif op == "$min": buckets[k][field] = None
                elif op == "$max": buckets[k][field] = None
                elif op == "$push": buckets[k][field] = []
                elif op == "$addToSet": buckets[k][field] = []
                else:
                    raise InvalidQueryError(f"Unsupported group accumulator: {op}")
            buckets[k]["__count"] = 0

        buckets[k]["__count"] += 1
        for field, acc in accumulators.items():
            op, arg = next(iter(acc.items()))
            val = deep_get(d, arg[1:], None) if isinstance(arg, str) and arg.startswith("$") else arg
            if op == "$sum":
                buckets[k][field] += (val or 0)
            elif op == "$avg":
                buckets[k][field] += (val or 0)
            elif op == "$min":
                buckets[k][field] = val if buckets[k][field] is None else min(buckets[k][field], val)
            elif op == "$max":
                buckets[k][field] = val if buckets[k][field] is None else max(buckets[k][field], val)
            elif op == "$push":
                buckets[k][field].append(val)
            elif op == "$addToSet":
                if val not in buckets[k][field]:
                    buckets[k][field].append(val)

    # finalize averages
    for k, b in buckets.items():
        for field, acc in accumulators.items():
            op = next(iter(acc.keys()))
            if op == "$avg":
                cnt = b["__count"]
                b[field] = (b[field] / cnt) if cnt else 0
        b.pop("__count", None)
    return list(buckets.values())


# =========================
# Bulk write models
# =========================
class InsertOne:
    def __init__(self, document): self.document = document
class UpdateOne:
    def __init__(self, filter, update, upsert=False):
        self.filter, self.update, self.upsert = filter, update, upsert
class DeleteOne:
    def __init__(self, filter): self.filter = filter

class BulkWriteResult:
    def __init__(self, inserted_count, matched_count, modified_count, deleted_count, upserted_ids):
        self.inserted_count = inserted_count
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.deleted_count = deleted_count
        self.upserted_ids = upserted_ids


# =========================
# Collection
# =========================
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    _id TEXT UNIQUE,
    document TEXT NOT NULL
);
"""

class Collection:
    def __init__(self, conn: sqlite3.Connection, name: str):
        self.conn = conn
        self.name = name
        self.conn.execute(CREATE_TABLE_SQL.format(table=self.name))
        self.conn.commit()
        self._schema = None  # optional JSON-schema-like

    # ----- Schema -----
    def set_schema(self, schema: dict):
        """Assign a lightweight JSON schema."""
        self._schema = schema

    def _validate(self, doc: dict):
        if self._schema is None: return
        required = self._schema.get("required", [])
        types = self._schema.get("properties", {})
        for key in required:
            if deep_get(doc, key, None) is None:
                raise InvalidDocumentError(f"Missing required field: {key}")
        for key, prop in types.items():
            expected = prop.get("type", None)
            if expected:
                val = deep_get(doc, key, None)
                if val is not None:
                    if expected == "string" and not isinstance(val, str): raise InvalidDocumentError(f"Field '{key}' must be string.")
                    if expected == "number" and not isinstance(val, (int, float)): raise InvalidDocumentError(f"Field '{key}' must be number.")
                    if expected == "array" and not isinstance(val, list): raise InvalidDocumentError(f"Field '{key}' must be array.")
                    if expected == "object" and not isinstance(val, dict): raise InvalidDocumentError(f"Field '{key}' must be object.")

    # ----- Insert -----
    def insert_one(self, document: dict) -> InsertOneResult:
        try:
            doc = dict(document)
            self._validate(doc)
            if "_id" not in doc:
                doc["_id"] = generate_object_id()
            doc_json = json.dumps(doc)
            self.conn.execute(f"INSERT INTO {self.name} (_id, document) VALUES (?, ?)", (doc["_id"], doc_json))
            self.conn.commit()
            return InsertOneResult(doc["_id"])
        except sqlite3.IntegrityError as e:
            raise DuplicateKeyError("Duplicate _id detected.") from e
        except Exception as e:
            raise MongoLiteError(f"Insert failed: {e}")

    def insert_many(self, documents: Iterable[dict]) -> List[InsertOneResult]:
        results = []
        try:
            for doc in documents:
                results.append(self.insert_one(doc))
            return results
        except Exception as e:
            raise MongoLiteError(f"Insert many failed: {e}")

    # ----- Find -----
    def find_one(self, query: dict, projection: Optional[dict] = None) -> Optional[dict]:
        try:
            cursor = self.conn.execute(f"SELECT id, document FROM {self.name}")
            for row in cursor:
                doc = json.loads(row[1])
                if match_query(doc, query):
                    return Cursor([(row[0], row[1])], projection=projection).to_list(1)[0]
            return None
        except Exception as e:
            raise MongoLiteError(f"Find one failed: {e}")

    def find(self, query: dict, projection: Optional[dict] = None,
             sort: Optional[List[Tuple[str,int]]] = None, skip: int = 0, limit: int = 0) -> Cursor:
        try:
            rows = list(self.conn.execute(f"SELECT id, document FROM {self.name}"))
            matched = [(rid, doc) for (rid, doc) in rows if match_query(json.loads(doc), query)]
            return Cursor(matched, projection=projection, sort=sort, skip=skip, limit=limit)
        except Exception as e:
            raise MongoLiteError(f"Find failed: {e}")

    def distinct(self, key: str, query: Optional[dict] = None) -> List[Any]:
        try:
            q = query or {}
            rows = list(self.conn.execute(f"SELECT document FROM {self.name}"))
            values = []
            for (doc_json,) in rows:
                doc = json.loads(doc_json)
                if match_query(doc, q):
                    val = deep_get(doc, key, None)
                    if val is not None:
                        if is_array(val):
                            values.extend(val)
                        else:
                            values.append(val)
            # unique preserving order
            seen = set()
            out = []
            for v in values:
                key = json.dumps(v, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    out.append(v)
            return out
        except Exception as e:
            raise MongoLiteError(f"Distinct failed: {e}")

    def count_documents(self, query: dict) -> int:
        return self.find(query).count()

    # ----- Delete -----
    def delete_one(self, query: dict) -> DeleteResult:
        try:
            cursor = self.conn.execute(f"SELECT id, document FROM {self.name}")
            for row in cursor:
                doc = json.loads(row[1])
                if match_query(doc, query):
                    self.conn.execute(f"DELETE FROM {self.name} WHERE id = ?", (row[0],))
                    self.conn.commit()
                    return DeleteResult(1)
            return DeleteResult(0)
        except Exception as e:
            raise MongoLiteError(f"Delete failed: {e}")

    def delete_many(self, query: dict) -> DeleteResult:
        try:
            cursor = self.conn.execute(f"SELECT id, document FROM {self.name}")
            ids_to_delete = []
            for row in cursor:
                doc = json.loads(row[1])
                if match_query(doc, query):
                    ids_to_delete.append(row[0])
            for rid in ids_to_delete:
                self.conn.execute(f"DELETE FROM {self.name} WHERE id = ?", (rid,))
            self.conn.commit()
            return DeleteResult(len(ids_to_delete))
        except Exception as e:
            raise MongoLiteError(f"Delete many failed: {e}")

    # ----- Update / Replace -----
    def update_one(self, query: dict, update: dict, upsert: bool = False) -> UpdateResult:
        try:
            cursor = self.conn.execute(f"SELECT id, document FROM {self.name}")
            for row in cursor:
                doc = json.loads(row[1])
                if match_query(doc, query):
                    new_doc = self._apply_update(doc, update, is_upsert=False)
                    self.conn.execute(f"UPDATE {self.name} SET document = ? WHERE id = ?", (json.dumps(new_doc), row[0]))
                    self.conn.commit()
                    return UpdateResult(matched_count=1, modified_count=1)
            if upsert:
                base_doc = {"_id": generate_object_id()}
                if "$setOnInsert" in update:
                    for k, v in update["$setOnInsert"].items():
                        deep_set(base_doc, k, v)
                upsert_update = {k: v for k, v in update.items() if k != "$setOnInsert"}
                upserted = self._apply_update(base_doc, upsert_update, is_upsert=True)
                self.insert_one(upserted)
                return UpdateResult(matched_count=0, modified_count=0, upserted_id=upserted["_id"])
            return UpdateResult(matched_count=0, modified_count=0)
        except InvalidUpdateError as e:
            raise
        except Exception as e:
            raise MongoLiteError(f"Update one failed: {e}")

    def update_many(self, query: dict, update: dict) -> UpdateResult:
        try:
            cursor = self.conn.execute(f"SELECT id, document FROM {self.name}")
            matched = 0
            modified = 0
            for row in cursor:
                doc = json.loads(row[1])
                if match_query(doc, query):
                    matched += 1
                    new_doc = self._apply_update(doc, update, is_upsert=False)
                    if new_doc != doc:
                        modified += 1
                    self.conn.execute(f"UPDATE {self.name} SET document = ? WHERE id = ?", (json.dumps(new_doc), row[0]))
            self.conn.commit()
            return UpdateResult(matched_count=matched, modified_count=modified)
        except InvalidUpdateError as e:
            raise
        except Exception as e:
            raise MongoLiteError(f"Update many failed: {e}")

    def replace_one(self, query: dict, replacement: dict, upsert: bool = False) -> UpdateResult:
        if not isinstance(replacement, dict) or any(k.startswith("$") for k in replacement.keys()):
            raise InvalidUpdateError("Replacement document must be a plain dict without update operators.")
        try:
            cursor = self.conn.execute(f"SELECT id, document FROM {self.name}")
            for row in cursor:
                doc = json.loads(row[1])
                if match_query(doc, query):
                    rep = dict(replacement)
                    if "_id" not in rep:
                        rep["_id"] = doc.get("_id")
                    self.conn.execute(f"UPDATE {self.name} SET document = ? WHERE id = ?", (json.dumps(rep), row[0]))
                    self.conn.commit()
                    return UpdateResult(matched_count=1, modified_count=1)
            if upsert:
                if "_id" not in replacement:
                    replacement = dict(replacement)
                    replacement["_id"] = generate_object_id()
                self.insert_one(replacement)
                return UpdateResult(matched_count=0, modified_count=0, upserted_id=replacement["_id"])
            return UpdateResult(matched_count=0, modified_count=0)
        except Exception as e:
            raise MongoLiteError(f"Replace one failed: {e}")

    # ----- FindOneAndX -----
    def find_one_and_update(self, query: dict, update: dict, return_document: str = "after") -> Optional[dict]:
        try:
            cursor = self.conn.execute(f"SELECT id, document FROM {self.name}")
            for row in cursor:
                doc = json.loads(row[1])
                if match_query(doc, query):
                    new_doc = self._apply_update(doc, update, is_upsert=False)
                    self.conn.execute(f"UPDATE {self.name} SET document = ? WHERE id = ?", (json.dumps(new_doc), row[0]))
                    self.conn.commit()
                    return new_doc if return_document == "after" else doc
            return None
        except Exception as e:
            raise MongoLiteError(f"find_one_and_update failed: {e}")

    def find_one_and_delete(self, query: dict) -> Optional[dict]:
        try:
            cursor = self.conn.execute(f"SELECT id, document FROM {self.name}")
            for row in cursor:
                doc = json.loads(row[1])
                if match_query(doc, query):
                    self.conn.execute(f"DELETE FROM {self.name} WHERE id = ?", (row[0],))
                    self.conn.commit()
                    return doc
            return None
        except Exception as e:
            raise MongoLiteError(f"find_one_and_delete failed: {e}")

    def find_one_and_replace(self, query: dict, replacement: dict, return_document: str = "after") -> Optional[dict]:
        try:
            cursor = self.conn.execute(f"SELECT id, document FROM {self.name}")
            for row in cursor:
                doc = json.loads(row[1])
                if match_query(doc, query):
                    rep = dict(replacement)
                    if "_id" not in rep:
                        rep["_id"] = doc.get("_id")
                    self.conn.execute(f"UPDATE {self.name} SET document = ? WHERE id = ?", (json.dumps(rep), row[0]))
                    self.conn.commit()
                    return rep if return_document == "after" else doc
            return None
        except Exception as e:
            raise MongoLiteError(f"find_one_and_replace failed: {e}")

    # ----- Aggregation -----
    def aggregate(self, pipeline: List[dict]) -> List[dict]:
        try:
            rows = list(self.conn.execute(f"SELECT document FROM {self.name}"))
            docs = [json.loads(r[0]) for r in rows]
            return aggregate_docs(docs, pipeline)
        except Exception as e:
            raise MongoLiteError(f"Aggregation failed: {e}")

    # ----- Bulk write -----
    def bulk_write(self, requests: List[Any]) -> BulkWriteResult:
        inserted = matched = modified = deleted = 0
        upserted_ids = []
        try:
            self.conn.execute("BEGIN;")
            for req in requests:
                if isinstance(req, InsertOne):
                    self.insert_one(req.document)
                    inserted += 1
                elif isinstance(req, UpdateOne):
                    res = self.update_one(req.filter, req.update, upsert=req.upsert)
                    matched += res.matched_count
                    modified += res.modified_count
                    if res.upserted_id: upserted_ids.append(res.upserted_id)
                elif isinstance(req, DeleteOne):
                    res = self.delete_one(req.filter)
                    deleted += res.deleted_count
                else:
                    raise MongoLiteError("Unsupported bulk request type.")
            self.conn.execute("COMMIT;")
            return BulkWriteResult(inserted, matched, modified, deleted, upserted_ids)
        except Exception as e:
            self.conn.execute("ROLLBACK;")
            raise MongoLiteError(f"Bulk write failed: {e}")

    # ----- Internal: apply update operators -----
    def _apply_update(self, doc: dict, update: dict, is_upsert: bool) -> dict:
        if not isinstance(update, dict):
            raise InvalidUpdateError("Update must be a dict of operators.")
        new_doc = json.loads(json.dumps(doc))  # deep copy
        for op, changes in update.items():
            if op == "$set":
                for k, v in changes.items():
                    deep_set(new_doc, k, v)
            elif op == "$unset":
                for k in changes.keys():
                    deep_unset(new_doc, k)
            elif op == "$inc":
                for k, v in changes.items():
                    cur = deep_get(new_doc, k, 0)
                    if not isinstance(cur, (int, float)):
                        raise InvalidUpdateError(f"$inc requires numeric field: {k}")
                    deep_set(new_doc, k, cur + v)
            elif op == "$mul":
                for k, v in changes.items():
                    cur = deep_get(new_doc, k, 0)
                    if not isinstance(cur, (int, float)):
                        raise InvalidUpdateError(f"$mul requires numeric field: {k}")
                    deep_set(new_doc, k, cur * v)
            elif op == "$rename":
                for old, new in changes.items():
                    val = deep_get(new_doc, old, None)
                    if val is not None:
                        deep_unset(new_doc, old)
                        deep_set(new_doc, new, val)
            elif op == "$push":
                for k, v in changes.items():
                    arr = deep_get(new_doc, k, None)
                    if arr is None:
                        arr = []
                    if not isinstance(arr, list):
                        raise InvalidUpdateError(f"$push requires array field: {k}")
                    if isinstance(v, dict) and "$each" in v:
                        arr.extend(v["$each"])
                    else:
                        arr.append(v)
                    deep_set(new_doc, k, arr)
            elif op == "$pull":
                for k, v in changes.items():
                    arr = deep_get(new_doc, k, [])
                    if not isinstance(arr, list):
                        raise InvalidUpdateError(f"$pull requires array field: {k}")
                    if isinstance(v, dict):
                        new_arr = [x for x in arr if not _match_scalar(x, v)]
                    else:
                        new_arr = [x for x in arr if x != v]
                    deep_set(new_doc, k, new_arr)
            elif op == "$pullAll":
                for k, v in changes.items():
                    arr = deep_get(new_doc, k, [])
                    if not isinstance(arr, list):
                        raise InvalidUpdateError(f"$pullAll requires array field: {k}")
                    new_arr = [x for x in arr if x not in v]
                    deep_set(new_doc, k, new_arr)
            elif op == "$addToSet":
                for k, v in changes.items():
                    arr = deep_get(new_doc, k, [])
                    if not isinstance(arr, list):
                        raise InvalidUpdateError(f"$addToSet requires array field: {k}")
                    items = v["$each"] if isinstance(v, dict) and "$each" in v else [v]
                    for item in items:
                        if item not in arr:
                            arr.append(item)
                    deep_set(new_doc, k, arr)
            elif op == "$pop":
                for k, v in changes.items():
                    arr = deep_get(new_doc, k, [])
                    if not isinstance(arr, list):
                        raise InvalidUpdateError(f"$pop requires array field: {k}")
                    if arr:
                        if v == 1: arr.pop()         # last
                        elif v == -1: arr.pop(0)     # first
                        else: raise InvalidUpdateError("$pop value must be 1 or -1")
                    deep_set(new_doc, k, arr)
            elif op == "$setOnInsert":
                # handled in upsert path
                continue
            else:
                raise InvalidUpdateError(f"Unsupported update operator: {op}")
        return new_doc


# =========================
# Database and Client
# =========================
class _Transaction:
    def __init__(self, conn):
        self.conn = conn
    def __enter__(self):
        self.conn.execute("BEGIN;")
        return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.conn.execute("COMMIT;")
        else:
            self.conn.execute("ROLLBACK;")

class Database:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, isolation_level=None, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.collections = {}

    def __getitem__(self, coll_name: str) -> Collection:
        if coll_name not in self.collections:
            self.collections[coll_name] = Collection(self.conn, coll_name)
        return self.collections[coll_name]

    def list_collection_names(self) -> List[str]:
        return list(self.collections.keys())

    def transaction(self):
        return _Transaction(self.conn)

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

class MongoLiteClient:
    """
    Top-level client similar to pymongo.MongoClient.
    Usage:
        client = MongoLiteClient()
        db = client["my_db"]
        coll = db["my_coll"]
    """
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.databases = {}

    def __getitem__(self, db_name: str) -> Database:
        if db_name not in self.databases:
            db_path = os.path.join(self.base_dir, f"{db_name}.db")
            self.databases[db_name] = Database(db_path)
        return self.databases[db_name]

    def close(self):
        for db in self.databases.values():
            db.close()