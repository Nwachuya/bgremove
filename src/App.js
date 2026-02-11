import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [selectedImage, setSelectedImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [imageId, setImageId] = useState(null);
  const [status, setStatus] = useState('');
  const [processedImageUrl, setProcessedImageUrl] = useState('');
  const [loading, setLoading] = useState(false);

  const handleImageChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedImage(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result);
        setProcessedImageUrl(''); // Reset processed image
        setImageId(null);
      };
      reader.readAsDataURL(file);
    }
  };

  const uploadImage = async () => {
    if (!selectedImage) {
      alert('Please select an image first');
      return;
    }

    setLoading(true);
    setStatus('Uploading image...');

    const formData = new FormData();
    formData.append('image', selectedImage);

    try {
      const response = await axios.post('http://localhost:5000/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setImageId(response.data.image_id);
      setStatus('Image uploaded successfully! Click "Remove Background" to process.');
    } catch (error) {
      console.error('Error uploading image:', error);
      setStatus('Error uploading image: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const processImage = async () => {
    if (!imageId) {
      alert('Please upload an image first');
      return;
    }

    setLoading(true);
    setStatus('Processing image...');

    try {
      const response = await axios.post(`http://localhost:5000/process/${imageId}`);
      
      // Set the processed image URL
      setProcessedImageUrl(`http://localhost:5000/download/${response.data.processed_filename}`);
      setStatus('Background removed successfully!');
    } catch (error) {
      console.error('Error processing image:', error);
      setStatus('Error processing image: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const downloadImage = () => {
    if (processedImageUrl) {
      const link = document.createElement('a');
      link.href = processedImageUrl;
      link.download = 'background_removed.png';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Background Removal Tool</h1>
        <p>Upload an image, remove the background, and download the result</p>
      </header>

      <main>
        <div className="upload-section">
          <input
            type="file"
            accept="image/*"
            onChange={handleImageChange}
            disabled={loading}
          />
          <button onClick={uploadImage} disabled={!selectedImage || loading}>
            Upload Image
          </button>
        </div>

        {previewUrl && (
          <div className="preview-section">
            <h2>Original Image Preview</h2>
            <img src={previewUrl} alt="Original preview" style={{ maxWidth: '300px', maxHeight: '300px' }} />
          </div>
        )}

        {imageId && (
          <div className="process-section">
            <button onClick={processImage} disabled={loading}>
              Remove Background
            </button>
          </div>
        )}

        {processedImageUrl && (
          <div className="result-section">
            <h2>Processed Image</h2>
            <img src={processedImageUrl} alt="Processed" style={{ maxWidth: '300px', maxHeight: '300px' }} />
            <button onClick={downloadImage}>Download Result</button>
          </div>
        )}

        {status && (
          <div className="status-section">
            <p>{status}</p>
          </div>
        )}

        {loading && (
          <div className="loading-section">
            <p>Processing...</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;