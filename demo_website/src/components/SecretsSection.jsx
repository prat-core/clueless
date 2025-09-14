import React from 'react';
import './SecretsSection.css';

const SecretsSection = ({ onCreateSecret }) => {
  return (
    <div className="secrets-section">
      <div className="secrets-header">
        <div className="secrets-title-section">
          <h1 className="secrets-title">Secrets</h1>
          <p className="secrets-subtitle">Securely manage your credentials.</p>
        </div>
        <button 
          className="create-secret-btn"
          onClick={onCreateSecret}
        >
          Create new secret
        </button>
      </div>
      
      <div className="secrets-content">
        <div className="secrets-icon">
          🔗
        </div>
        <h2 className="create-first-secret">Create your first secret</h2>
        <p className="secrets-description">
          Use secrets to add sensitive information like API keys into the environment variables of your Modal Functions.
        </p>
        <div className="secrets-buttons">
          <button className="get-started-btn">Get started</button>
          <button className="view-docs-btn">View Docs</button>
        </div>
      </div>
    </div>
  );
};

export default SecretsSection;
