from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List

from src.llm.base_client import BaseLLMClient
from src.schemas import ModelAnswer, QuestionSample


def run_models_for_samples(
    samples: Iterable[QuestionSample],
    clients: List[BaseLLMClient],
    max_workers: int = 4,
) -> List[ModelAnswer]:
    tasks = [(sample, client) for sample in samples for client in clients]
    results: List[ModelAnswer] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(client.answer, sample) for sample, client in tasks]
        for future in as_completed(futures):
            results.append(future.result())
    return results
