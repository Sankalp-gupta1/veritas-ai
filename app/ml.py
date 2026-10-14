"""CPU inference using pinned open models. Model weights stay local to the server."""

import json
from functools import lru_cache
from threading import Lock

import numpy as np
import onnxruntime as ort
from model2vec import StaticModel
from tokenizers import Tokenizer

from .config import MODEL_DIR


@lru_cache(maxsize=1)
def embedder():
    path = MODEL_DIR / "embedding"
    if not (path / "model.safetensors").exists():
        raise RuntimeError("Models are missing. Run python scripts/download_models.py.")
    return StaticModel.from_pretrained(path, normalize=True)


def embed(texts):
    return embedder().encode(texts, max_length=512, use_multiprocessing=False).astype(np.float32)


class PairModel:
    def __init__(self, name):
        folder = MODEL_DIR / name
        self.tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding(pad_id=0)
        self.lock = Lock()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(folder / "model_quantized.onnx"),
            options,
            providers=["CPUExecutionProvider"],
        )
        self.labels = json.loads((folder / "config.json").read_text()).get("id2label", {})

    def logits(self, pairs):
        outputs = []
        for start in range(0, len(pairs), 8):
            # Tokenizer configuration is mutable; guard encoding under concurrent requests.
            with self.lock:
                encoded = self.tokenizer.encode_batch(pairs[start : start + 8])
            data = {
                "input_ids": np.array([x.ids for x in encoded], dtype=np.int64),
                "attention_mask": np.array([x.attention_mask for x in encoded], dtype=np.int64),
                "token_type_ids": np.array([x.type_ids for x in encoded], dtype=np.int64),
            }
            inputs = {x.name: data[x.name] for x in self.session.get_inputs()}
            outputs.extend(self.session.run(None, inputs)[0].tolist())
        return np.array(outputs)


@lru_cache(maxsize=2)
def pair_model(name):
    return PairModel(name)


def rerank(question, passages):
    if not passages:
        return []
    logits = pair_model("reranker").logits([(question, p["text"]) for p in passages]).reshape(-1)
    scores = 1 / (1 + np.exp(-np.clip(logits, -50, 50)))
    return sorted(
        [dict(p, rerank_score=float(s)) for p, s in zip(passages, scores)],
        key=lambda p: p["rerank_score"],
        reverse=True,
    )


def infer_relations(pairs):
    """NLI is a fallible support classifier, never a calibrated truth probability."""
    if not pairs:
        return []
    model = pair_model("verifier")
    logits = model.logits(pairs)
    exp = np.exp(logits - logits.max(axis=1, keepdims=True))
    probabilities = exp / exp.sum(axis=1, keepdims=True)
    return [
        {model.labels[str(i)].lower(): float(value) for i, value in enumerate(row)}
        for row in probabilities
    ]
