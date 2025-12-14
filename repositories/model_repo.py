from database.models import LLMModell, TTSModell
from .base_repo import BaseRepo

class LLMRepo(BaseRepo):
    def __init__(self, db):
        super().__init__(db, LLMModell)
    
class TTSRepo(BaseRepo):
    def __init__(self, db):
        super().__init__(db, TTSModell)
    