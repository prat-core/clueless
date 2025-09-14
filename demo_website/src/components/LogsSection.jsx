import React from 'react';
import './LogsSection.css';

const LogsSection = () => {
  return (
    <div className="logs-section">
      <div className="logs-header">
        <h1 className="logs-title">Logs</h1>
        <p className="logs-description">
          These are all running and recently stopped Modal apps.
        </p>
      </div>

      <div className="logs-table-container">
        <table className="logs-table">
          <thead>
            <tr className="logs-table-header">
              <th className="logs-table-header-cell">Name</th>
              <th className="logs-table-header-cell">State</th>
              <th className="logs-table-header-cell">Created</th>
              <th className="logs-table-header-cell">Stopped</th>
            </tr>
          </thead>
          <tbody>
            <tr className="logs-empty-row">
              <td colSpan="4" className="logs-empty-message">
                When you run or deploy an app, the logs can be found here.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LogsSection;
