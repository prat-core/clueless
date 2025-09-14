import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './SettingsPage.css';
import ApiTokensSection from './ApiTokensSection';

const SettingsPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const getCurrentSection = () => {
    const path = location.pathname;
    if (path === '/settings' || path === '/settings/profile') return 'Profile';
    if (path === '/settings/workspaces') return 'Workspaces';
    if (path === '/settings/notifications') return 'Notifications';
    if (path === '/settings/usage-and-billing') return 'Usage and Billing';
    if (path === '/settings/plans') return 'Plans';
    if (path === '/settings/api-tokens') return 'API Tokens';
    if (path === '/settings/proxy-auth-tokens') return 'Proxy Auth Tokens';
    if (path === '/settings/domains') return 'Domains';
    if (path === '/settings/image-config') return 'Image Config';
    if (path === '/settings/proxies') return 'Proxies';
    return 'Profile';
  };

  const activeSection = getCurrentSection();

  const handleSectionClick = (sectionName) => {
    const routes = {
      'Profile': '/settings/profile',
      'Workspaces': '/settings/workspaces',
      'Notifications': '/settings/notifications',
      'Usage and Billing': '/settings/usage-and-billing',
      'Plans': '/settings/plans',
      'API Tokens': '/settings/api-tokens',
      'Proxy Auth Tokens': '/settings/proxy-auth-tokens',
      'Domains': '/settings/domains',
      'Image Config': '/settings/image-config',
      'Proxies': '/settings/proxies'
    };
    navigate(routes[sectionName]);
  };

  const sidebarItems = [
    {
      category: 'Account',
      items: [
        { name: 'Profile' },
        { name: 'Workspaces' },
        { name: 'Notifications' }
      ]
    },
    {
      category: 'Workspace',
      workspace: 'ritesh3280',
      items: [
        { name: 'Usage and Billing' },
        { name: 'Plans' },
        { name: 'API Tokens' },
        { name: 'Proxy Auth Tokens' },
        { name: 'Domains' },
        { name: 'Image Config' },
        { name: 'Proxies' }
      ]
    }
  ];

  return (
    <div className="settings-page">
      <div className="settings-sidebar">
        <div className="settings-header">
          <button className="back-button" onClick={() => navigate('/apps')}>
            ← Settings
          </button>
        </div>
        
        <div className="sidebar-content">
          {sidebarItems.map((section, sectionIndex) => (
            <div key={sectionIndex} className="sidebar-section">
              <div className="sidebar-section-header">
                {section.category}
                {section.workspace && (
                  <span className="workspace-name">@{section.workspace}</span>
                )}
              </div>
              
              <div className="sidebar-items">
                {section.items.map((item, itemIndex) => (
                  <div 
                    key={itemIndex}
                    className={`sidebar-item ${item.name === activeSection ? 'active' : ''}`}
                    onClick={() => handleSectionClick(item.name)}
                  >
                    <span className="sidebar-item-name">{item.name}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="settings-main">
        {activeSection === 'Profile' && (
          <div className="profile-section">
            <div className="profile-header">
              <h1 className="profile-title">Profile</h1>
              <p className="profile-subtitle">Manage your account profile.</p>
            </div>

            <div className="profile-content">
              <div className="profile-field">
                <div className="field-header">
                  <label className="field-label">Profile Picture</label>
                  <button className="edit-button">
                    ✏️ Edit
                  </button>
                </div>
                <div className="profile-picture">
                  <div className="profile-avatar">
                    R
                  </div>
                </div>
              </div>

              <div className="profile-field">
                <div className="field-header">
                  <label className="field-label">Email</label>
                  <button className="edit-button">
                    ✏️ Edit
                  </button>
                </div>
                <div className="field-value">
                  ritesh3280@gmail.com
                </div>
              </div>

              <div className="profile-field">
                <div className="field-header">
                  <label className="field-label">Timezone</label>
                  <span className="field-info">ℹ️</span>
                </div>
                <div className="field-value">
                  <select className="timezone-select">
                    <option>Auto-detect (Browser Local)</option>
                    <option>UTC</option>
                    <option>America/New_York</option>
                    <option>America/Los_Angeles</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeSection === 'API Tokens' && (
          <ApiTokensSection />
        )}

        {activeSection !== 'Profile' && activeSection !== 'API Tokens' && (
          <div className="section-placeholder">
            <h1>{activeSection}</h1>
            <p>This section is coming soon...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SettingsPage;
