import React from 'react';
import './StorageSection.css';

const StorageSection = () => {
  const storageOptions = [
    {
      title: 'Volumes',
      icon: '📁',
      description: 'Store files that are read more than they are written, like model weights and database dumps.',
      docsCount: 3
    },
    {
      title: 'Queues',
      icon: '📊',
      description: 'Pass data through your system with first-in-first-out ordering.',
      docsCount: 3
    },
    {
      title: 'Dicts',
      icon: '📋',
      description: 'Store Python objects for distributed access.',
      docsCount: 3
    }
  ];

  return (
    <div className="storage-section">
      <div className="storage-header">
        <div className="storage-header-left">
          <h1 className="storage-title">Storage</h1>
          <p className="storage-subtitle">
            Persist and communicate data created or processed by your Modal Apps.
          </p>
        </div>
        <div className="storage-header-right">
          <div className="search-control">
            <input 
              type="text" 
              placeholder="Search (⌘K)"
              className="search-input"
            />
            <span className="search-icon">🔍</span>
          </div>
        </div>
      </div>

      <div className="storage-content">
        <div className="storage-container">
          <div className="storage-intro">
            <div className="storage-icon-large">
              💾
            </div>
            <h2 className="storage-intro-title">Storage in Modal</h2>
            <p className="storage-intro-description">
              Modal offers three storage options: Volumes, Dicts, and Queues. Each has unique characteristics.
            </p>
          </div>

          <div className="storage-options">
            {storageOptions.map((option, index) => (
              <div key={index} className="storage-option-card">
                <div className="storage-option-header">
                  <div className="storage-option-icon">{option.icon}</div>
                  <div className="storage-option-title-section">
                    <h3 className="storage-option-title">{option.title}</h3>
                    <div className="docs-link">
                      Docs <span className="docs-count">{option.docsCount}</span> ↗
                    </div>
                  </div>
                </div>
                <p className="storage-option-description">
                  {option.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StorageSection;
