"""Run: python -m clarify_api → http://127.0.0.1:8788/"""

from __future__ import annotations

import uvicorn

from clarify_api.app import create_app


def main() -> None:
    uvicorn.run(create_app(), host="127.0.0.1", port=8788)


if __name__ == "__main__":
    main()
