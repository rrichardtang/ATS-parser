"""The skill taxonomy's term/alias groups, shared by both corpus builders.

Lived inline in scripts/build_taxonomy.py until the personal-corpus builder
(scripts/build_user_corpus.py) needed the same groups against a different corpus --
moved here so the two scripts can't silently drift apart on what a term's aliases
are.
"""
from __future__ import annotations

# Terms are grouped so coverage can be reported per area -- a resume strong on
# serving but silent on evaluation is a specific, fixable gap, not a low score.
GROUPS: dict[str, dict[str, list[str]]] = {
    "core_ml": {
        "pytorch": ["pytorch", "torch"],
        "transformers": ["transformers", "huggingface", "hugging face"],
        "fine-tuning": ["fine-tuning", "fine tune", "finetuning", "fine-tune"],
        "lora": ["lora", "qlora", "parameter-efficient", "peft"],
        "training": ["training", "train", "distributed data parallel"],
        "distillation": ["distillation", "distil"],
        "quantization": ["quantization", "quantized", "quantisation"],
        "rlhf": ["rlhf", "dpo", "preference optimization"],
        "classification": ["classification", "classifier"],
        "embeddings": ["embedding", "embeddings"],
    },
    "llm_systems": {
        "rag": ["rag", "retrieval-augmented", "retrieval augmented"],
        "vector-db": ["pgvector", "pinecone", "weaviate", "qdrant", "faiss", "vector database", "vector db"],
        "reranking": ["rerank", "reranking", "cross-encoder", "colbert"],
        "hybrid-search": ["bm25", "hybrid search", "dense retrieval", "sparse retrieval"],
        "chunking": ["chunking", "chunk"],
        "prompt-engineering": ["prompt engineering", "prompting", "prompt"],
        "function-calling": ["function calling", "tool use", "structured output", "json schema"],
        "agents": ["agent", "agents", "planning loop"],
        "llm-apis": ["openai", "anthropic", "gemini", "claude", "gpt-4", "open-weight"],
        "context": ["kv cache", "context window", "token budget"],
    },
    "serving": {
        "vllm": ["vllm", "tgi", "text generation inference"],
        "triton": ["triton", "onnx", "tensorrt"],
        "fastapi": ["fastapi", "flask", "rest api"],
        "docker": ["docker", "container"],
        "kubernetes": ["kubernetes", "k8s"],
        "gpu": ["gpu", "cuda", "a100", "h100", "a10g", "nccl"],
        "latency": ["latency", "p50", "p95", "p99", "throughput", "qps", "rps"],
        "batching": ["batching", "continuous batching", "dynamic batching"],
        "caching": ["caching", "cache", "redis"],
        "streaming": ["streaming", "server-sent", "websocket"],
    },
    "evaluation": {
        "eval-harness": ["evaluation", "eval", "evals", "eval harness", "evaluation harness"],
        "golden-dataset": ["golden dataset", "golden set", "test set", "held-out", "benchmark"],
        "llm-as-judge": ["llm-as-judge", "llm as judge", "judge model"],
        "retrieval-metrics": ["recall@k", "mrr", "ndcg", "precision", "recall", "f1"],
        "groundedness": ["groundedness", "faithfulness", "hallucination"],
        "ab-testing": ["a/b test", "ab test", "online metric", "offline metric"],
        "annotation": ["annotation", "annotator", "labelling", "labeling", "ground truth"],
        "regression-suite": ["regression", "ci gating", "regression suite"],
    },
    "data": {
        "sql": ["sql", "postgres", "postgresql", "bigquery", "snowflake"],
        "spark": ["spark", "pyspark", "databricks"],
        "pipelines": ["airflow", "dagster", "dbt", "pipeline", "etl"],
        "feature-store": ["feature store", "feature engineering"],
        "storage": ["parquet", "object storage", "s3", "dataset versioning"],
        "ray": ["ray", "slurm", "kubeflow"],
    },
    "mlops": {
        "experiment-tracking": ["weights & biases", "wandb", "mlflow", "experiment tracking"],
        "cicd": ["ci/cd", "continuous integration", "continuous delivery"],
        "monitoring": ["monitoring", "observability", "prometheus", "grafana", "langsmith", "tracing"],
        "drift": ["drift", "data drift", "model drift"],
        "cost": ["cost per request", "cost", "token spend", "spend"],
        "oncall": ["on-call", "oncall", "incident", "sla", "slo", "uptime"],
        "registry": ["model registry", "versioning", "rollback"],
    },
    "foundation": {
        "python": ["python"],
        "cloud": ["aws", "gcp", "azure", "cloud"],
        "terraform": ["terraform", "infrastructure as code"],
        "go-rust": ["golang", " go ", "rust"],
        "typescript": ["typescript", "javascript", "react"],
        "testing": ["unit test", "integration test", "pytest"],
    },
}
