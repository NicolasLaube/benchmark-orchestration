from orchestrator.loaders.loader_benchmark import LoaderCsvBenchmark
from orchestrator.loaders.loader_queue import LoaderJsonlQueue

loaderQueue = LoaderJsonlQueue()
loaderBenchmark = LoaderCsvBenchmark()
jobs = loaderQueue.load("data/queue.jsonl")

oneJob = jobs[0]

questions = loaderBenchmark.load(oneJob)

for index, question in enumerate(questions, start=1):
    if index > 5:
        break
    print(f"Question {index}: {question}")
