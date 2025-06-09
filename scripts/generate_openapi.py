import pathlib
import sys

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover – dev helper
    sys.stderr.write("PyYAML is required for this script. Install with `poetry add pyyaml --group dev`\n")
    sys.exit(1)

from fastapi import FastAPI

# Import the FastAPI app lazily to avoid side-effects if the import fails
try:
    from app.main import app  # pylint: disable=import-error
except Exception as exc:  # pragma: no cover – surface helpful error
    sys.stderr.write(f"Unable to import FastAPI app: {exc}\n")
    sys.exit(1)

if not isinstance(app, FastAPI):
    sys.stderr.write("Imported object `app` is not a FastAPI instance.\n")
    sys.exit(1)

spec = app.openapi()
output_path = pathlib.Path("docs/killrvideo_openapi.yaml")
output_path.write_text(yaml.safe_dump(spec, sort_keys=False))
print(f"✔ OpenAPI spec written to {output_path}")

def main() -> None:  # Entry-point for poetry script
    """Generate docs/killrvideo_openapi.yaml from the running FastAPI app."""

    spec_dict = app.openapi()
    output_path.write_text(yaml.safe_dump(spec_dict, sort_keys=False))
    print(f"✔ OpenAPI spec written to {output_path}")

if __name__ == "__main__":
    main() 