from orchestrator.loaders.loader_queue import LoaderJsonlQueue

loader = LoaderJsonlQueue()
jobs = loader.load("data/queue.jsonl")

for job in jobs:
    print(job)
