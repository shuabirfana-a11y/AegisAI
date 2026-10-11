"""Local CPU inference. Requests never download or execute external code."""
from pathlib import Path
from functools import lru_cache
MODEL='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
CACHE=Path(__file__).resolve().parents[3]/'work'/'phase9_model_cache'

class LocalEmbedding:
    model=MODEL
    dimension=384
    def __init__(self):
        from fastembed import TextEmbedding
        self._model=TextEmbedding(MODEL,cache_dir=str(CACHE),threads=2,local_files_only=True)
    def passages(self,texts):return [x.tolist() for x in self._model.passage_embed(texts)]
    def query(self,text):return next(self._model.query_embed(text)).tolist()

@lru_cache(maxsize=1)
def local_embedding():return LocalEmbedding()
