from database.models import Textbeitrag
from .base_repo import BaseRepo

class TextRepo(BaseRepo):
    def __init__(self, db):
        super().__init__(db, Textbeitrag)
    
    def get_by_user_id(self, user_id):
        return self.db.query(Textbeitrag).filter_by(userId=user_id).all()
