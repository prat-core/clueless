import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import './SubNavBar.css';

const SubNavBar = ({ onTabChange }) => {
  const [activeTab, setActiveTab] = useState('Apps');
  const location = useLocation();

  const tabs = ['Apps', 'Logs', 'Secrets', 'Storage', 'Notebooks'];

  // Update active tab based on current route
  useEffect(() => {
    const pathToTab = {
      '/apps': 'Apps',
      '/logs': 'Logs',
      '/secrets': 'Secrets',
      '/secrets/create': 'Secrets',
      '/storage': 'Storage',
      '/notebooks': 'Notebooks'
    };
    
    const currentTab = pathToTab[location.pathname];
    if (currentTab) {
      setActiveTab(currentTab);
    }
  }, [location.pathname]);

  const handleTabClick = (tab) => {
    setActiveTab(tab);
    onTabChange(tab);
  };

  return (
    <div className="subnav-bar">
      <div className="subnav-tabs">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={`subnav-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => handleTabClick(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SubNavBar;
