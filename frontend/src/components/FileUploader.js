import React, { useState, useRef } from 'react';
import './FileUploader.css';

function FileUploader({ type, onSuccess, user, registrationResults = [], onAllComplete }) {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [currentFileIndex, setCurrentFileIndex] = useState(0);
  const fileInputRef = useRef(null);

  const ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tif', 'tiff'];

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length > 0) {
      validateAndSetFiles(selectedFiles);
    }
  };

  const validateAndSetFiles = (selectedFiles) => {
    setError('');
    const newFiles = [];
    const newPreviews = [];

    for (const file of selectedFiles) {
      const fileExtension = file.name.split('.').pop().toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(fileExtension)) {
        setError(`${file.name}: Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`);
        continue;
      }

      if (file.size > 50 * 1024 * 1024) {
        setError(`${file.name}: File size must be less than 50MB`);
        continue;
      }

      newFiles.push(file);

      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        newPreviews.push(e.target.result);
        if (newPreviews.length === newFiles.length) {
          setPreviews(newPreviews);
        }
      };
      reader.readAsDataURL(file);
    }

    setFiles(newFiles);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const droppedFiles = Array.from(e.dataTransfer.files || []);
    if (droppedFiles.length > 0) {
      validateAndSetFiles(droppedFiles);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleSubmitAll = async () => {
    if (files.length === 0) {
      setError('Please select at least one file');
      return;
    }

    setLoading(true);
    setError('');
    setCurrentFileIndex(0);

    for (let i = 0; i < files.length; i++) {
      setCurrentFileIndex(i + 1);
      await uploadFile(files[i]);
    }

    setLoading(false);
  };

  const uploadFile = async (file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const endpoint =
        type === 'register'
          ? 'http://localhost:5000/api/media/register'
          : 'http://localhost:5000/api/media/check';

      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        onSuccess(data);
      } else {
        setError((prev) => prev + `${file.name}: ${data.message || 'Failed'}\n`);
      }
    } catch (err) {
      setError((prev) => prev + `${file.name}: Connection error\n`);
    }
  };

  return (
    <div className="file-uploader">
      {files.length === 0 ? (
        <>
          <div
            className="drop-zone"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            <div className="drop-zone-content">
              <h3>Drop images here or click to browse</h3>
              <p>Supported: JPG, PNG, GIF, BMP, WEBP, TIFF</p>
              <p className="file-size-hint">Max 50MB per file</p>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                accept={ALLOWED_EXTENSIONS.map((ext) => `.${ext}`).join(',')}
                className="hidden-input"
              />
            </div>
          </div>

          <button
            type="button"
            className="browse-button"
            onClick={() => fileInputRef.current?.click()}
          >
            Browse Files
          </button>
        </>
      ) : (
        <>
          <div className="files-list">
            <h3>{files.length} file(s) selected</h3>
            <div className="preview-grid">
              {previews.map((preview, index) => (
                <div key={index} className="preview-item">
                  <img src={preview} alt={files[index].name} className="preview-image" />
                  <p className="file-name">{files[index].name}</p>
                  <p className="file-size">
                    {(files[index].size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="button-group">
            <button
              type="button"
              className="change-button"
              onClick={() => {
                setFiles([]);
                setPreviews([]);
                setError('');
                fileInputRef.current?.click();
              }}
              disabled={loading}
            >
              Change Files
            </button>

            <button
              type="button"
              className="submit-button"
              onClick={handleSubmitAll}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  {type === 'register' ? `Registering ${currentFileIndex}/${files.length}...` : 'Checking...'}
                </>
              ) : (
                type === 'register' ? 'Register All' : 'Check Provenance'
              )}
            </button>
          </div>

          {registrationResults.length > 0 && (
            <div className="registration-summary">
              <h4>Uploaded: {registrationResults.length}/{files.length}</h4>
              {registrationResults.length === files.length && onAllComplete && (
                <button
                  type="button"
                  className="complete-button"
                  onClick={onAllComplete}
                >
                  Complete & Return Home
                </button>
              )}
            </div>
          )}
        </>
      )}

      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

export default FileUploader;
