---
name: qdrant-up
description: Start (or reuse) the local Qdrant Docker container for ragforge development and confirm it is reachable on localhost:6333.
disable-model-invocation: true
---

Start the container, or create it if it doesn't exist, then wait until Qdrant is ready, all in one call:

```bash
docker start qdrant 2>/dev/null || docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_data:/qdrant/storage qdrant/qdrant
curl -sf --retry 5 --retry-connrefused --retry-delay 2 http://localhost:6333/collections
```

Report the existing collections. If `docker run` fails with "port is already allocated", tell the user and stop. Don't kill other processes.

Never remove the container or the `qdrant_data` volume unless the user explicitly asks.
