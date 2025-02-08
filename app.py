import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_sqlalchemy import SQLAlchemy
from utils.instagram import download_instagram_video
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Create downloads directory in static folder
DOWNLOAD_DIR = os.path.join(app.static_folder, 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instagram_downloader.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Import models after db initialization to avoid circular imports
from models import Video

# Create database tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    try:
        url = request.form.get('url')
        if not url:
            logger.error("No URL provided")
            return jsonify({'error': 'Please provide a valid Instagram URL'}), 400

        logger.debug(f"Processing download request for URL: {url}")

        # Extract shortcode from URL
        path = urlparse(url).path
        shortcode = path.split('/')[-2] if path.split('/')[-1] == '' else path.split('/')[-1]

        # Create database entry
        video = Video(instagram_url=url, shortcode=shortcode)
        db.session.add(video)
        db.session.commit()
        logger.debug(f"Created database entry for video with shortcode: {shortcode}")

        try:
            # Download video to static/downloads directory
            relative_path = download_instagram_video(url, DOWNLOAD_DIR)
            logger.debug(f"Download result path: {relative_path}")

            if relative_path:
                video.status = 'completed'
                video.file_path = relative_path
                db.session.commit()

                # Return the URL for the static file
                video_url = url_for('static', filename=relative_path)
                logger.debug(f"Generated video URL: {video_url}")

                return jsonify({
                    'success': True,
                    'message': 'Video downloaded successfully',
                    'video_url': video_url
                })
            else:
                video.status = 'failed'
                db.session.commit()
                logger.error("Video download failed")
                return jsonify({
                    'success': False,
                    'error': 'Failed to download video. Please check if the URL is correct and the video is public.'
                }), 400

        except Exception as e:
            video.status = 'failed'
            db.session.commit()
            logger.error(f"Error during video download: {str(e)}")
            raise e

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your request'
        }), 500

@app.route('/video/<path:filename>')
def serve_video(filename):
    try:
        video_path = os.path.join(app.static_folder, 'downloads', filename)
        logger.debug(f"Attempting to serve video from: {video_path}")
        if os.path.exists(video_path):
            return send_file(video_path)
        else:
            logger.error(f"Video file not found at: {video_path}")
            return jsonify({'error': 'Video not found'}), 404
    except Exception as e:
        logger.error(f"Error serving video: {str(e)}")
        return jsonify({'error': 'Video not found'}), 404

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html', error="Internal server error"), 500