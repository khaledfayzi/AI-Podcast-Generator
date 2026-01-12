from sqlalchemy.orm import Session

class BaseRepo:
    def __init__(self, db, model):
        self.db = db
        self.model = model
    
    def get_all(self):
        """
        Liefert alle Objekte des Modells
        """
        return self.db.query(self.model).all()
        
    def get_by_id(self, id):
        """
        Liefert das Objekt mit der angegebenen ID
        """
        return self.db.query(self.model).get(id)
        
    def add(self, obj):
        """
        Fügt ein neues Objekt hinzu
        """
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
        
    def delete(self, obj):
        """
        Löscht ein Objekt
        """
        self.db.delete(obj)
        self.db.commit()