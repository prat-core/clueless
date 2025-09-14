import React, { useState } from 'react';
import './NotebooksSection.css';
import ImportNotebookModal from './ImportNotebookModal';

const NotebooksSection = () => {
  const [selectedFilter, setSelectedFilter] = useState('All notebooks');
  const [sortBy, setSortBy] = useState('Most recent');
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  const notebooks = [
    {
      id: 1,
      title: "Ritesh's notebook – Sep 13",
      type: 'CPU',
      user: 'ritesh3280',
      timeAgo: '14 minutes ago',
      thumbnail: '/api/placeholder/80/60',
      color: '#4ade80'
    },
    {
      id: 2,
      title: "Ritesh's notebook – Sep 13", 
      type: 'CPU',
      user: 'ritesh3280',
      timeAgo: 'about 2 hours ago',
      thumbnail: '/api/placeholder/80/60',
      color: '#8b5cf6'
    }
  ];

  const sidebarItems = [
    { name: 'All notebooks', count: 2, icon: '📓' },
    { name: 'Created by you', count: 2, icon: '👤' },
    { name: 'Featured examples', count: null, icon: '⭐' }
  ];

  return (
    <div className="notebooks-section">
      <div className="notebooks-header">
        <div className="notebooks-title-section">
          <div className="notebooks-icon">📓</div>
          <h1 className="notebooks-title">Notebooks</h1>
        </div>
        <div className="notebooks-actions">
          <button 
            className="import-notebook-btn"
            onClick={() => setIsImportModalOpen(true)}
          >
            📥 Import notebook
          </button>
          <button className="create-notebook-btn">
            ➕ Create notebook
          </button>
        </div>
      </div>

      <div className="notebooks-description">
        <p>
          High-performance notebooks, backed by Modal's GPU cloud. Launch in seconds. Use custom 
          images, collaborate in real time, and attach petabyte-scale storage. If you're new, create your first 
          notebook with one click, or <a href="#" className="docs-link">check out our docs</a>.
        </p>
      </div>

      <div className="notebooks-content">
        <div className="notebooks-sidebar">
          {sidebarItems.map((item, index) => (
            <div 
              key={index}
              className={`sidebar-item ${selectedFilter === item.name ? 'active' : ''}`}
              onClick={() => setSelectedFilter(item.name)}
            >
              <span className="sidebar-icon">{item.icon}</span>
              <span className="sidebar-name">{item.name}</span>
              {item.count !== null && <span className="sidebar-count">{item.count}</span>}
            </div>
          ))}
        </div>

        <div className="notebooks-main">
          <div className="notebooks-controls">
            <div className="viewing-count">
              Viewing {notebooks.length} notebooks.
            </div>
            <div className="notebooks-controls-right">
              <div className="sort-control">
                <span className="sort-icon">📊</span>
                <span>Sort: </span>
                <select 
                  value={sortBy} 
                  onChange={(e) => setSortBy(e.target.value)}
                  className="sort-select"
                >
                  <option>Most recent</option>
                  <option>Oldest</option>
                  <option>Name A-Z</option>
                  <option>Name Z-A</option>
                </select>
              </div>
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

          <div className="notebooks-grid">
            {notebooks.map((notebook) => (
              <div key={notebook.id} className="notebook-card">
                <div className="notebook-thumbnail">
                  <div 
                    className="thumbnail-placeholder"
                    style={{ backgroundColor: notebook.color }}
                  ></div>
                </div>
                <div className="notebook-info">
                  <div className="notebook-header-row">
                    <h3 className="notebook-title">{notebook.title}</h3>
                    <button className="notebook-menu">⋯</button>
                  </div>
                  <div className="notebook-type">{notebook.type}</div>
                  <div className="notebook-meta">
                    <span className="notebook-user">
                      <span className="user-indicator" style={{ backgroundColor: notebook.color }}></span>
                      {notebook.user}
                    </span>
                    <span className="notebook-time">{notebook.timeAgo}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <ImportNotebookModal 
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
      />
    </div>
  );
};

export default NotebooksSection;
