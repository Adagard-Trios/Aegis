"""
src/federated/server.py

Flower federated-learning aggregator (FedAvg).

Launch:

    python -m src.federated.server --rounds 10 --address 0.0.0.0:8080
"""
from __future__ import annotations

import argparse
import logging
import os

logger = logging.getLogger(__name__)

try:
    import flwr as fl  # type: ignore
    _FLWR_AVAILABLE = True
except Exception:  # pragma: no cover
    _FLWR_AVAILABLE = False


def run_server(rounds: int, server_address: str) -> None:
    if not _FLWR_AVAILABLE:
        raise RuntimeError("flwr not installed. `pip install flwr`")

    strategy = fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=2,
        min_evaluate_clients=2,
        min_available_clients=2,
    )
    fl.server.start_server(
        server_address=server_address,
        config=fl.server.ServerConfig(num_rounds=rounds),
        strategy=strategy,
    )


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=int(os.environ.get("FL_ROUNDS", "10")))
    parser.add_argument("--address", default=os.environ.get("FL_ADDRESS", "0.0.0.0:8080"))
    args = parser.parse_args()
    run_server(args.rounds, args.address)
