import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './CreateSecretForm.css';

const CreateSecretForm = () => {
  const { type } = useParams();
  const navigate = useNavigate();
  const [secretName, setSecretName] = useState('');
  const [envVars, setEnvVars] = useState([
    { key: '', value: '' }
  ]);

  // Get integration details based on type
  const getIntegrationDetails = (type) => {
    const integrations = {
      'discord': {
        name: 'Discord',
        icon: '💬',
        color: '#5865f2',
        defaultName: 'discord-secret',
        defaultVars: [
          { key: 'DISCORD_PUBLIC_KEY', value: '' },
          { key: 'DISCORD_BOT_TOKEN', value: '' }
        ]
      },
      'custom': {
        name: 'Custom',
        icon: '🔧',
        color: '#4ade80',
        defaultName: 'my-secret',
        defaultVars: [
          { key: '', value: '' }
        ]
      },
      'aws': {
        name: 'AWS',
        icon: '☁️',
        color: '#f59e0b',
        defaultName: 'aws-secret',
        defaultVars: [
          { key: 'AWS_ACCESS_KEY_ID', value: '' },
          { key: 'AWS_SECRET_ACCESS_KEY', value: '' }
        ]
      },
      'github': {
        name: 'GitHub',
        icon: '🐙',
        color: '#ffffff',
        defaultName: 'github-secret',
        defaultVars: [
          { key: 'GITHUB_TOKEN', value: '' }
        ]
      }
    };
    return integrations[type] || integrations['custom'];
  };

  const integration = getIntegrationDetails(type);

  // Initialize with default values
  React.useEffect(() => {
    setSecretName(integration.defaultName);
    setEnvVars(integration.defaultVars);
  }, [type]);

  const handleAddVariable = () => {
    setEnvVars([...envVars, { key: '', value: '' }]);
  };

  const handleRemoveVariable = (index) => {
    if (envVars.length > 1) {
      setEnvVars(envVars.filter((_, i) => i !== index));
    }
  };

  const handleVariableChange = (index, field, value) => {
    const newEnvVars = [...envVars];
    newEnvVars[index][field] = value;
    setEnvVars(newEnvVars);
  };

  const handleBack = () => {
    navigate('/secrets/create');
  };

  const handleDone = () => {
    // Here you would typically save the secret
    console.log('Creating secret:', { name: secretName, envVars });
    navigate('/secrets');
  };

  return (
    <div className="create-secret-form">
      <div className="form-header">
        <button className="back-button" onClick={handleBack}>
          ← Back
        </button>
        <div className="form-title-section">
          <h2 className="form-title">Create new secret</h2>
          <div className="integration-badge">
            <span className="integration-icon" style={{ backgroundColor: integration.color }}>
              {integration.icon}
            </span>
            <span className="integration-name">{integration.name}</span>
          </div>
        </div>
      </div>

      <div className="form-content">
        <div className="form-section">
          <h3 className="section-title">Name</h3>
          <p className="section-description">
            Choose a unique name to reference this secret in your code.
          </p>
          <input
            type="text"
            className="secret-name-input"
            value={secretName}
            onChange={(e) => setSecretName(e.target.value)}
            placeholder="Enter secret name"
          />
        </div>

        <div className="form-section">
          <div className="section-header">
            <h3 className="section-title">Environment variables</h3>
            <button className="help-button">
              ⓘ Where do I find this?
            </button>
          </div>
          <p className="section-description">
            Assign environment variables to this secret.
          </p>

          <div className="env-vars-container">
            <div className="env-vars-header">
              <span className="env-var-label">Key</span>
              <span className="env-var-label">Value</span>
            </div>
            
            {envVars.map((envVar, index) => (
              <div key={index} className="env-var-row">
                <input
                  type="text"
                  className="env-var-input"
                  value={envVar.key}
                  onChange={(e) => handleVariableChange(index, 'key', e.target.value)}
                  placeholder="Enter key"
                />
                <input
                  type="text"
                  className="env-var-input"
                  value={envVar.value}
                  onChange={(e) => handleVariableChange(index, 'value', e.target.value)}
                  placeholder="Enter value"
                />
                <button
                  className="remove-var-button"
                  onClick={() => handleRemoveVariable(index)}
                  disabled={envVars.length === 1}
                >
                  ⊖
                </button>
              </div>
            ))}
          </div>

          <div className="form-actions">
            <button className="add-another-button" onClick={handleAddVariable}>
              + Add another
            </button>
            <button className="import-env-button">
              📄 Import .env
            </button>
          </div>
        </div>

        <div className="form-footer">
          <button className="done-button" onClick={handleDone}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

export default CreateSecretForm;
