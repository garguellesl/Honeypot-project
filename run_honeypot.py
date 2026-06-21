#!/usr/bin/env python3
"""
run_honeypot.py
Punto de entrada: arranca los honeypots Telnet y SSH y los deja corriendo
hasta que se pulse Ctrl+C.

Uso:
    python run_honeypot.py
    python run_honeypot.py --telnet-port 2323 --ssh-port 2222
"""

import argparse
import signal
import sys
import time

from honeypot import logger, ssh_honeypot, telnet_honeypot


def main():
    parser = argparse.ArgumentParser(description="IoT Honeypot")
    parser.add_argument("--telnet-port", type=int, default=2323)
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    logger.init_db()

    telnet_honeypot.serve(host=args.host, port=args.telnet_port)
    ssh_honeypot.serve(host=args.host, port=args.ssh_port)

    print("Honeypot activo. Ctrl+C para detener.")

    def _shutdown(signum, frame):
        print("\nDeteniendo honeypot...")
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
