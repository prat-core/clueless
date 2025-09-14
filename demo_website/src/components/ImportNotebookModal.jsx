import React, { useState } from 'react';
import './ImportNotebookModal.css';

const ImportNotebookModal = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('upload');
  const [notebookTitle, setNotebookTitle] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  if (!isOpen) return null;

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
  };

  const handleCreate = () => {
    // Handle notebook creation logic here
    console.log('Creating notebook:', { title: notebookTitle, file: selectedFile });
    onClose();
  };

  const handleCancel = () => {
    setNotebookTitle('');
    setSelectedFile(null);
    onClose();
  };

  return (
    <div className="modal-overlay">
      <div className="import-notebook-modal">
        <div className="modal-header">
          <h2 className="modal-title">Import notebook</h2>
          <button className="close-button" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-tabs">
          <button 
            className={`tab-button ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            📤 Upload file
          </button>
          <button 
            className={`tab-button ${activeTab === 'url' ? 'active' : ''}`}
            onClick={() => setActiveTab('url')}
          >
            🔗 From URL
          </button>
        </div>

        <div className="modal-content">
          {activeTab === 'upload' && (
            <>
              <div className="form-section">
                <label className="form-label">File (.ipynb)</label>
                <div className="file-upload-area">
                  <input
                    type="file"
                    accept=".ipynb"
                    onChange={handleFileSelect}
                    className="file-input"
                    id="notebook-file"
                  />
                  <label htmlFor="notebook-file" className="file-upload-button">
                    Choose file
                  </label>
                  {selectedFile && (
                    <span className="selected-file-name">{selectedFile.name}</span>
                  )}
                </div>
              </div>

              <div className="form-section">
                <label className="form-label">Notebook title</label>
                <input
                  type="text"
                  className="title-input"
                  placeholder="Enter notebook title"
                  value={notebookTitle}
                  onChange={(e) => setNotebookTitle(e.target.value)}
                />
              </div>
            </>
          )}

          {activeTab === 'url' && (
            <>
              <div className="form-section">
                <label className="form-label">URL</label>
                <input
                  type="url"
                  className="url-input"
                  placeholder="Enter notebook URL"
                />
              </div>

              <div className="form-section">
                <label className="form-label">Notebook title</label>
                <input
                  type="text"
                  className="title-input"
                  placeholder="Enter notebook title"
                  value={notebookTitle}
                  onChange={(e) => setNotebookTitle(e.target.value)}
                />
              </div>
            </>
          )}
        </div>

        <div className="modal-footer">
          <button className="cancel-button" onClick={handleCancel}>
            Cancel
          </button>
          <button className="create-button" onClick={handleCreate}>
            Create
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImportNotebookModal;
