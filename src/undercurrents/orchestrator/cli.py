import argparse
from pathlib import Path

from undercurrents.orchestrator.ollama_client import OllamaClient
from undercurrents.orchestrator.orchestrator import Orchestrator
from undercurrents.storage import db

DEFAULT_DB_PATH = "data/undercurrents.db"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="undercurrents-orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    chat_parser = subparsers.add_parser("chat")
    chat_parser.add_argument("--db-path", default=DEFAULT_DB_PATH)

    ask_parser = subparsers.add_parser("ask")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--db-path", default=DEFAULT_DB_PATH)

    args = parser.parse_args(argv)
    conn = db.get_connection(Path(args.db_path))
    db.initialize_schema(conn)
    db.ensure_songs_clustering_columns(conn)
    orchestrator = Orchestrator(OllamaClient())

    if args.command == "ask":
        answer, _ = orchestrator.ask(conn, args.question)
        print(answer)

    elif args.command == "chat":
        print("Undercurrents chat — ask about Tame Impala's live history. Ctrl+C to exit.")
        history: list[dict] = []
        while True:
            try:
                question = input("> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not question.strip():
                continue
            answer, history = orchestrator.ask(conn, question, history)
            print(answer)

    conn.close()


if __name__ == "__main__":
    main()
