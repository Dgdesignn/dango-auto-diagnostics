"""Controlo manual do simulador; nunca envia comandos para a ECU."""

import argparse
import http.client
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "cycle", "resolve", "reset", "shutdown"))
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Porta invalida.")
    connection = http.client.HTTPConnection("127.0.0.1", args.port, timeout=3)
    try:
        connection.request("POST", "/control", json.dumps({"action": args.action}),
                           {"Authorization": "Bearer " + args.token, "Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            parser.exit(1, "Pedido de controlo recusado.\n")
        print(json.dumps(json.loads(response.read(8192)), indent=2, ensure_ascii=False))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
