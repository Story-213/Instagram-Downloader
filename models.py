from datetime import datetime
from app import db

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instagram_url = db.Column(db.String(255), nullable=False)
    shortcode = db.Column(db.String(100), nullable=False)
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='pending')  # pending, completed, failed
    
    def __repr__(self):
        return f'<Video {self.shortcode}>'
