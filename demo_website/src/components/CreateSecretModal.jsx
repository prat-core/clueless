import React from 'react';
import { useNavigate } from 'react-router-dom';
import './CreateSecretModal.css';

const CreateSecretModal = ({ onBack }) => {
  const navigate = useNavigate();

  const handleIntegrationClick = (integrationSlug) => {
    navigate(`/secrets/create/${integrationSlug}`);
  };

  const integrations = [
    {
      name: 'Custom',
      description: 'Custom environment variables for your Modal functions',
      icon: '🔧',
      color: '#4ade80',
      className: 'custom-integration-card'
    },
    {
      name: 'Copy from another environment',
      description: 'Copy a secret you\'ve already created in another environment',
      icon: '📋',
      color: '#4ade80',
      className: 'copy-integration-card'
    },
    {
      name: 'Anthropic',
      description: 'Access Anthropic\'s powerful language and multimodal models',
      icon: 'AI',
      color: '#d97706',
      className: 'anthropic-integration-card'
    },
    {
      name: 'AWS',
      description: 'Access your existing resources in AWS, such as S3 buckets',
      icon: '☁️',
      color: '#f59e0b',
      className: 'aws-integration-card'
    },
    {
      name: 'Discord',
      description: 'Receive interactions and send messages using Discord',
      icon: '💬',
      color: '#5865f2',
      className: 'discord-integration-card'
    },
    {
      name: 'GitHub',
      description: 'Access the GitHub API or private Git repositories',
      icon: '🐙',
      color: '#ffffff',
      className: 'github-integration-card'
    },
    {
      name: 'Google Cloud',
      description: 'Use Google Cloud products like BigQuery and Cloud Storage',
      icon: '🌐',
      color: '#4285f4',
      className: 'google-cloud-integration-card'
    },
    {
      name: 'Google Sheets',
      description: 'Interact with data in Google Sheets',
      icon: '📊',
      color: '#34a853',
      className: 'google-sheets-integration-card'
    },
    {
      name: 'Hugging Face',
      description: 'Use models from Hugging Face that require an access token',
      icon: '🤗',
      color: '#ff9500',
      className: 'hugging-face-integration-card'
    },
    {
      name: 'LangSmith',
      description: 'Monitor your LLM applications with LangSmith',
      icon: '🔍',
      color: '#ffffff',
      className: 'langsmith-integration-card'
    },
    {
      name: 'MongoDB',
      description: 'Connect to a MongoDB database',
      icon: '🍃',
      color: '#47a248',
      className: 'mongodb-integration-card'
    },
    {
      name: 'MySQL',
      description: 'Connect to a MySQL-compatible database, such as PlanetScale',
      icon: '🐬',
      color: '#4479a1',
      className: 'mysql-integration-card'
    },
    {
      name: 'OpenAI',
      description: 'Use the OpenAI API or Python package',
      icon: '🤖',
      color: '#ffffff',
      className: 'openai-integration-card'
    },
    {
      name: 'Postgres',
      description: 'Connect to a Postgres-compatible database',
      icon: '🐘',
      color: '#336791',
      className: 'postgres-integration-card'
    },
    {
      name: 'Slack',
      description: 'Send messages and access channels using Slack',
      icon: '💬',
      color: '#4a154b',
      className: 'slack-integration-card'
    },
    {
      name: 'Qdrant Cloud',
      description: 'High-performance vector search at scale',
      icon: '🔍',
      color: '#dc143c',
      className: 'qdrant-cloud-integration-card'
    },
    {
      name: 'Twilio',
      description: 'Use Twilio\'s API to send SMS messages',
      icon: '📱',
      color: '#f22f46',
      className: 'twilio-integration-card'
    },
    {
      name: 'Weights & Biases',
      description: 'Use Weights & Biases to track machine learning experiments',
      icon: '⚖️',
      color: '#ffbe00',
      className: 'weights-biases-integration-card'
    },
    {
      name: 'OpenTelemetry',
      description: 'Export application logs and metrics to OpenTelemetry',
      icon: '📊',
      color: '#f5a623',
      className: 'opentelemetry-integration-card'
    }
  ];

  return (
    <div className="create-secret-content">
      <div className="create-secret-header">
        <button className="back-button" onClick={onBack}>
          ← Back
        </button>
        <div className="create-secret-title-section">
          <h2 className="create-secret-title">Choose type</h2>
          <p className="create-secret-subtitle">
            Select from our prebuilt library of integration templates, or create a custom secret.
          </p>
        </div>
      </div>
      
      <div className="integrations-grid">
        {integrations.map((integration, index) => (
          <div 
            key={index} 
            className={`integration-card ${integration.className}`}
            onClick={() => handleIntegrationClick(integration.name.toLowerCase().replace(/\s+/g, '-'))}
          >
            <div className="integration-icon" style={{ backgroundColor: integration.color }}>
              {integration.icon}
            </div>
            <div className="integration-content">
              <h3 className="integration-name">{integration.name}</h3>
              <p className="integration-description">{integration.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CreateSecretModal;
