"""
Federated learning scaffolding for MedVerse, using the Flower framework.

Entry points:
  • src/federated/client.py  — FlowerClient that trains on the local
                               aegis_local.db and uploads gradients only.
  • src/federated/server.py  — FedAvg orchestrator; run alongside the
                               FastAPI backend (or on a separate host).

Run (once `pip install flwr` is in place):

    # Aggregator (once, on the coordinator machine)
    python -m src.federated.server

    # Participant (on each device, pointing at its own SQLite file)
    python -m src.federated.client --server-address <host>:8080
"""
