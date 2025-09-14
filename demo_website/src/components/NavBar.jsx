import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './NavBar.css';

const NavBar = () => {
  const [activeDropdown, setActiveDropdown] = useState(null);
  const navigate = useNavigate();

  const toggleDropdown = (dropdownName) => {
    setActiveDropdown(activeDropdown === dropdownName ? null : dropdownName);
  };

  const handleSettingsClick = () => {
    setActiveDropdown(null);
    navigate('/settings/profile');
  };

  return (
    <div className="navbar">
      <div className="navbar-left">
        {/* Logo */}
        <div className="logo">
          <div className="logo-icon">🟢</div>
        </div>

        {/* User Profile Section */}
        <div className="dropdown-container">
          <button 
            className="profile-button"
            onClick={() => toggleDropdown('profile')}
          >
            <span className="username">ritesh3280</span>
            <span className="plan-badge">Starter</span>
            <span className="dropdown-arrow">▼</span>
          </button>
          {activeDropdown === 'profile' && (
            <div className="dropdown-menu">
              <div className="dropdown-item">Upgrade workspace</div>
              <div className="dropdown-item">Manage workspace</div>
            </div>
          )}
        </div>

        {/* Workspace Section */}
        <div className="dropdown-container">
          <button 
            className="workspace-button"
            onClick={() => toggleDropdown('workspace')}
          >
            <span>main</span>
            <span className="dropdown-arrow">▼</span>
          </button>
          {activeDropdown === 'workspace' && (
            <div className="dropdown-menu">
              <div className="dropdown-item">Create environment</div>
            </div>
          )}
        </div>
      </div>

      <div className="navbar-right">
        {/* Credits Section */}
        <div className="dropdown-container">
          <button 
            className="credits-button"
            onClick={() => toggleDropdown('credits')}
          >
            <span>credits remaining $5.00</span>
            <span className="dropdown-arrow">▼</span>
          </button>
          {activeDropdown === 'credits' && (
            <div className="dropdown-menu">
              <div className="dropdown-item">Usage</div>
              <div className="dropdown-item">Billing</div>
            </div>
          )}
        </div>

        {/* Slack Communities */}
        <div className="nav-item">
          <span>Slack Communities</span>
        </div>

        {/* Docs */}
        <div className="nav-item">
          <span>Docs</span>
        </div>

        {/* User Avatar */}
        <div className="dropdown-container">
          <button 
            className="avatar-button"
            onClick={() => toggleDropdown('avatar')}
          >
            <div className="avatar">R</div>
          </button>
          {activeDropdown === 'avatar' && (
            <div className="dropdown-menu dropdown-menu-right">
              <div className="dropdown-item" onClick={handleSettingsClick}>Settings</div>
              <div className="dropdown-item">Logout</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default NavBar;
