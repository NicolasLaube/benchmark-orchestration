from orchestrator.loaders.loader_queue import JsonlQueueLoader

loader = JsonlQueueLoader()
jobs = loader.load("data/queue.jsonl")

for job in jobs:
    print(job)