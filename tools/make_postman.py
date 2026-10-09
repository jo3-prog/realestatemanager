"""
Turns docs/openapi.json into a Postman collection.

Usage (from the project root):
    python manage.py spectacular --format openapi-json --file docs/openapi.json
    python tools/make_postman.py

Then in Postman: Import -> docs/RealEstateAPI.postman_collection.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
schema = json.loads((ROOT / "docs" / "openapi.json").read_text())


def resolve(ref_or_schema):
    if "$ref" in ref_or_schema:
        node = schema
        for part in ref_or_schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        return node
    return ref_or_schema


def example_value(prop):
    prop = resolve(prop)
    if "enum" in prop:
        return prop["enum"][0]
    if "allOf" in prop:
        return example_value(prop["allOf"][0])
    t = prop.get("type")
    fmt = prop.get("format")
    if t == "string":
        return {"email": "user@example.com", "date-time": "2030-01-01T10:00:00Z",
                "password": "StrongPass#123", "binary": ""}.get(fmt, "string")
    if t in ("integer", "number"):
        return 1
    if t == "boolean":
        return True
    if t == "array":
        return [example_value(prop.get("items", {}))]
    return None


def example_body(op):
    content = op.get("requestBody", {}).get("content", {})
    if "application/json" not in content:
        return None
    body_schema = resolve(content["application/json"]["schema"])
    return {name: example_value(p) for name, p in body_schema.get("properties", {}).items()
            if not resolve(p).get("readOnly")}


folders = {}
for path, methods in schema["paths"].items():
    for method, op in methods.items():
        if method not in ("get", "post", "put", "patch", "delete"):
            continue
        url_path = path.strip("/")
        for param in [p for p in op.get("parameters", []) if p["in"] == "path"]:
            url_path = url_path.replace("{%s}" % param["name"], ":%s" % param["name"])
        query = [{"key": p["name"], "value": "", "disabled": True}
                 for p in op.get("parameters", []) if p["in"] == "query"]
        item = {"name": f"{method.upper()} /{path.strip('/')}/", "request": {
            "method": method.upper(),
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "url": {"raw": "{{base_url}}/" + url_path + "/", "host": ["{{base_url}}"],
                    "path": url_path.split("/") + [""], "query": query,
                    "variable": [{"key": p["name"], "value": "1"} for p in op.get("parameters", []) if p["in"] == "path"]},
            "description": op.get("description") or op.get("summary", ""),
        }}
        body = example_body(op)
        if body is not None:
            item["request"]["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2),
                                       "options": {"raw": {"language": "json"}}}
        elif "multipart/form-data" in op.get("requestBody", {}).get("content", {}):
            item["request"]["header"] = []
            item["request"]["body"] = {"mode": "formdata", "formdata": [{"key": "images", "type": "file"}]}
        if path.startswith("/api/auth/login") :
            # Test script saves the token automatically after login
            item["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "const data = pm.response.json();",
                "if (data.access) { pm.collectionVariables.set('access_token', data.access); }",
                "if (data.refresh) { pm.collectionVariables.set('refresh_token', data.refresh); }"]}}]
        tag = (op.get("tags") or ["other"])[0]
        folders.setdefault(tag, []).append(item)

collection = {
    "info": {"name": "Real Estate Sales & Leasing API",
             "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
    "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}]},
    "variable": [{"key": "base_url", "value": "http://127.0.0.1:8000"},
                 {"key": "access_token", "value": ""}, {"key": "refresh_token", "value": ""}],
    "item": [{"name": tag, "item": items} for tag, items in sorted(folders.items())],
}
out = ROOT / "docs" / "RealEstateAPI.postman_collection.json"
out.write_text(json.dumps(collection, indent=2))
print(f"Wrote {out.name}: {sum(len(v) for v in folders.values())} requests in {len(folders)} folders")
