"""미니 쇼핑몰 서버 실행 진입점. 표준 라이브러리만 사용한다.

실행: python main.py --port 8000
"""

from __future__ import annotations

import argparse
import logging
import os

from minishop.server import run
from minishop.store import Store

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    parser = argparse.ArgumentParser(description="미니 쇼핑몰 백엔드")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--uploads", default=os.path.join(BASE_DIR, "uploads"),
                        help="프로필 사진 저장 디렉터리")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(Store(args.uploads), args.host, args.port)


if __name__ == "__main__":
    main()
