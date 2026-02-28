# TasteBot Project Memory

## Project Summary
Federated learning system for restaurant success prediction. Customers chat with a local LLM (gemma3:4b via ollama) over Status-IM (decentralized p2p), embeddings are extracted, and a HGTConv GNN is trained per-restaurant with Flower FL + FedAvg.

## Key Commands
- `poetry install` — install dependencies
- `poetry tastebot-build` — compile all native libs (Go, proto, FalkorDB, Redis)
- `poetry tastebot-configure` — configure tendermint + redis from .env + pyproject.toml
- `poetry run server` — start Flower SuperLink (FL server)
- `poetry run neighbor` — start PSI gRPC server (port 50051)
- `poetry run client` — start main TasteBot client

## Important Files
- `client.py` — `TasteBot` singleton, main orchestrator
- `config.py` — `ConfigOptions` singleton; reads `pyproject.toml` + `.env`
- `server.py` — `FLServer` wrapper around Flower SuperLink
- `embeddings.py` — `EmbeddingOps` singleton; saves `.pt` and `.npz` embedding files
- `ai/restaurant_model.py` — `AIModel` ollama chat/generate wrapper; stop-words trigger summary/feedback
- `ai/client.py` — `AIClient` thread managing per-customer bot sessions
- `fl/client_app.py` — `RestaurantClient(NumPyClient)` for Flower
- `fl/server_app.py` — FedAvg server strategy on global SWGDataset
- `fl/task.py` — `load_data` → `SWGDatasetLocal`; `SWG` model factory
- `ml/swg_ml_local.py` — `SWG` HGTConv model + `train_local`/`test_local`
- `ml/swg_db_local.py` — `SWGDatasetLocal` builds local hetero subgraph
- `ml/swg_db.py` — `SWGDataset` global Swiggy dataset graph
- `p2p/neighbor_restaurant.py` — PSI gRPC server (RestaurantNeighbor)
- `tools/poetry/poetry_tastebot_plugin/plugin.py` — Poetry plugin (`tastebot-build`, `tastebot-configure` commands)

## Architecture Notes
- `TasteBot` runs three threads: `init_thread` (login), `run_thread` (customer events + orders), `post_thread`
- Customer stop-word = customer's emojiHash; triggers chat summary → customer embedding
- Neighbor stop-word = neighbor restaurant's emojiHash; triggers feedback → restaurant embedding
- Embeddings stored in `~/.cache/tastebot-<hash>/embeddings/` (1024-dim, mxbai-embed-large)
- Custom Flower fork (`flwr-1.19.6`) required for SuperNode API integration
- Proto import paths patched post-generation: `psi_pb2` → `p2p.psi_pb2`, etc.

## Config
- `pyproject.toml` `[tool.tastebot.app.*]` — restaurant, kg, im, fl, p2p, embeddings sections
- `.env` secrets: `RESTAURANT_PASSWORD`, `KG_DB_PASSWORD`, `PROJECT_FILE`
- After configure: `TASTEBOT_ROOTDIR`, `TMHOME`, `REDIS_CONFIGDIR` appended to `.env`

## Native Libraries Built
- `im/libs/libstatus.so.0` — status-go v10.29.6
- `im/libs/status-backend`
- `p2p/libs/libgowaku.so.0` — Waku v2
- `p2p/libs/libconsensus.so.0` — Tendermint v0.34.24
- `ai/libs/falkordb-x64.so` — FalkorDB module
- `ai/libs/redis-server` — Redis 7.4.4

## External Dependencies (must be running)
- Ollama with `gemma3:4b`, `swigg1.0-gemma3:4b`, `mxbai-embed-large`
- Redis+FalkorDB (started from `ai/libs/redis-server`)
- Flower SuperLink (`poetry run server`)

## User Preferences
- Committed CLAUDE.md on 2026-02-28 (commit 871e7b3)
