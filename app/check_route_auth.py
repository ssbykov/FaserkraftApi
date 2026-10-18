from fastapi.routing import APIRoute
from starlette.routing import Mount

from app.api.api_v1.dependencies import get_current_employee_any
from app.api.api_v1.fastapi_users import current_user
from app.api.dependencies.mobile_sessions import (
    get_current_mobile_employee,
)
from app.main import main_app


def calls(dep):
    yield dep.call
    for sub in dep.dependencies:
        yield from calls(sub)


def iter_routes(routes, prefix=""):
    for route in routes:
        if isinstance(route, APIRoute):
            yield prefix + route.path, route
        elif isinstance(route, Mount):
            yield from iter_routes(route.routes, prefix + route.path)


found = list(iter_routes(main_app.routes))
print(f"APIRoute found: {len(found)}")

if not found:
    for route in main_app.routes[:15]:
        print(type(route).__name__, getattr(route, "path", None))

ordered = sorted(found, key=lambda item: (item[0], sorted(item[1].methods or [])))

for path, route in ordered:
    dependencies = set(calls(route.dependant))
    if get_current_employee_any in dependencies:
        kind = "ANY"
    elif get_current_mobile_employee in dependencies:
        kind = "MOBILE"
    elif current_user in dependencies:
        kind = "STANDARD"
    else:
        kind = "NONE"
    methods = ",".join(sorted(route.methods or []))
    print(f"{kind:9} {methods:8} {path}")

print("--- CHECK users/* and logout ---")
for path, route in ordered:
    if not path.startswith(("/api/v1/users", "/api/v1/auth/logout")):
        continue
    names = {getattr(c, "__name__", "") for c in calls(route.dependant)}
    guards = sorted(
        n
        for n in names
        if "current" in n or ("user" in n.lower() and "manager" not in n.lower())
    )
    label = "PROTECTED" if guards else "OPEN"
    print(f"CHECK {label:9} {sorted(route.methods)[0]:6} {path} {guards}")