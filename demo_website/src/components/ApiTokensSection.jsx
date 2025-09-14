import React, { useState } from 'react';
import './ApiTokensSection.css';

const ApiTokensSection = () => {
  const [tokens, setTokens] = useState([
    {
      id: 'ak-WAzquwJOYPtDA2LKTzAmX4',
      created: '7 minutes ago',
      lastUsed: ''
    }
  ]);

  const generateRandomToken = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let token = 'ak-';
    for (let i = 0; i < 22; i++) {
      token += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return token;
  };

  const handleCreateToken = () => {
    const newToken = {
      id: generateRandomToken(),
      created: 'Just now',
      lastUsed: ''
    };
    setTokens([newToken, ...tokens]);
  };

  return (
    <div className="api-tokens-section">
      <div className="api-tokens-header">
        <div className="header-left">
          <div className="user-avatar">R</div>
          <div className="header-text">
            <span className="username">ritesh3280</span>
            <span className="separator">/</span>
            <span className="section-title">API Tokens</span>
          </div>
        </div>
        <button className="new-token-btn" onClick={handleCreateToken}>
          New Token
        </button>
      </div>

      <div className="tokens-description">
        Below are your {tokens.length} active tokens in the ritesh3280 workspace.
      </div>

      <div className="tokens-table-container">
        <table className="tokens-table">
          <thead>
            <tr className="tokens-table-header">
              <th className="tokens-table-header-cell">Token ID</th>
              <th className="tokens-table-header-cell">Created</th>
              <th className="tokens-table-header-cell">Last used</th>
            </tr>
          </thead>
          <tbody>
            {tokens.map((token, index) => (
              <tr key={index} className="tokens-table-row">
                <td className="tokens-table-cell token-id">{token.id}</td>
                <td className="tokens-table-cell">{token.created}</td>
                <td className="tokens-table-cell">{token.lastUsed || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ApiTokensSection;
