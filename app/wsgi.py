import os

from main import build_store, create_app

app = create_app(build_store(), debug_endpoints=os.environ.get("ENABLE_DEBUG") == "true")
