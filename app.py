from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import cv2
import numpy as np
from PIL import Image
import sqlite3
import os
import io
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

DATABASE = 'database.db'

def init_db():
    """Initialize the SQLite database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create table for storing image information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed BOOLEAN DEFAULT FALSE
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def remove_background(image_path):
    """Remove background from image using OpenCV"""
    # Read the image
    img = cv2.imread(image_path)
    
    # Create a mask using GrabCut algorithm
    mask = np.zeros(img.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    
    # Define rectangle around the main object (this is a simplified approach)
    height, width = img.shape[:2]
    rect = (width//4, height//4, width//2, height//2)
    
    # Apply GrabCut
    cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
    
    # Modify mask to keep only the sure foreground
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
    
    # Apply mask to image
    img = img * mask2[:, :, np.newaxis]
    
    # Create alpha channel for transparency
    b_channel, g_channel, r_channel = cv2.split(img)
    alpha_channel = np.ones(b_channel.shape, dtype=b_channel.dtype) * 255
    alpha_channel = cv2.bitwise_and(alpha_channel, alpha_channel, mask=mask2 * 255)
    
    # Merge channels to create RGBA image
    img_RGBA = cv2.merge((b_channel, g_channel, r_channel, alpha_channel))
    
    return img_RGBA

@app.route('/upload', methods=['POST'])
def upload_image():
    """Endpoint to upload an image"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    if file:
        # Generate unique filename
        unique_filename = str(uuid.uuid4()) + '_' + file.filename
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Save uploaded file
        file.save(filepath)
        
        # Store in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO images (filename, original_filename, processed) VALUES (?, ?, ?)',
            (unique_filename, file.filename, False)
        )
        conn.commit()
        image_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'image_id': image_id,
            'filename': unique_filename
        }), 200

@app.route('/process/<int:image_id>', methods=['POST'])
def process_image(image_id):
    """Endpoint to process an uploaded image and remove background"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM images WHERE id = ?', (image_id,))
    image_record = cursor.fetchone()
    conn.close()
    
    if not image_record:
        return jsonify({'error': 'Image not found'}), 404
    
    original_filepath = os.path.join(UPLOAD_FOLDER, image_record['filename'])
    
    if not os.path.exists(original_filepath):
        return jsonify({'error': 'Original image file not found'}), 404
    
    # Process the image to remove background
    processed_img = remove_background(original_filepath)
    
    # Generate processed filename
    base_name, ext = os.path.splitext(image_record['filename'])
    processed_filename = base_name + '_processed.png'
    processed_filepath = os.path.join(PROCESSED_FOLDER, processed_filename)
    
    # Save processed image
    cv2.imwrite(processed_filepath, processed_img)
    
    # Update database record
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE images SET processed = ? WHERE id = ?',
        (True, image_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'processed_filename': processed_filename
    }), 200

@app.route('/download/<filename>', methods=['GET'])
def download_image(filename):
    """Endpoint to download processed image"""
    filepath = os.path.join(PROCESSED_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(filepath, as_attachment=True)

@app.route('/status/<int:image_id>', methods=['GET'])
def get_status(image_id):
    """Endpoint to check processing status of an image"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM images WHERE id = ?', (image_id,))
    image_record = cursor.fetchone()
    conn.close()
    
    if not image_record:
        return jsonify({'error': 'Image not found'}), 404
    
    return jsonify({
        'id': image_record['id'],
        'filename': image_record['filename'],
        'original_filename': image_record['original_filename'],
        'processed': bool(image_record['processed']),
        'upload_date': image_record['upload_date']
    }), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)