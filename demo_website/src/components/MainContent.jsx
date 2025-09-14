import React, { useState } from 'react';
import './MainContent.css';

const MainContent = () => {
  const [expandedDropdown, setExpandedDropdown] = useState(null);

  const toggleDropdown = (dropdownId) => {
    setExpandedDropdown(expandedDropdown === dropdownId ? null : dropdownId);
  };

  return (
    <div className="main-content">
      <div className="content-container">
        <h1 className="main-heading">Create your first app</h1>
        <p className="welcome-message">Welcome to Modal! Let's get you set up to run an app.</p>
        
        <div className="dropdown-section">
          <div className="dropdown-box">
            <button 
              className="dropdown-header"
              onClick={() => toggleDropdown('python-client')}
            >
              <span className="dropdown-title">Download and configure the Python client</span>
              <span className={`dropdown-arrow ${expandedDropdown === 'python-client' ? 'expanded' : ''}`}>
                ▼
              </span>
            </button>
            {expandedDropdown === 'python-client' && (
              <div className="dropdown-content">
                <h3 className="content-heading">Run this in order to install the Python library locally:</h3>
                <div className="code-block">
                  <pre><span className="command">pip install modal</span></pre>
                </div>
                <div className="code-block">
                  <pre><span className="command">python3 -m modal setup</span></pre>
                </div>
                <p className="content-text">
                  The second command creates an API token by authenticating through your web browser. It will open a new tab, but you can close it when you are done.
                </p>
              </div>
            )}
          </div>

          <div className="dropdown-box">
            <button 
              className="dropdown-header"
              onClick={() => toggleDropdown('run-code')}
            >
              <span className="dropdown-title">Run some code</span>
              <span className={`dropdown-arrow ${expandedDropdown === 'run-code' ? 'expanded' : ''}`}>
                ▼
              </span>
            </button>
            {expandedDropdown === 'run-code' && (
              <div className="dropdown-content">
                <p className="content-text">
                  You're ready to run some code! To get started, here is a minimal script that computes the square of 42:
                </p>
                <div className="code-block">
                  <pre><span className="keyword">import</span> <span className="module">modal</span>

<span className="variable">app</span> <span className="operator">=</span> <span className="module">modal</span><span className="operator">.</span><span className="function">App</span><span className="bracket">(</span><span className="string">"example-get-started"</span><span className="bracket">)</span>


<span className="decorator">@app.function()</span>
<span className="keyword">def</span> <span className="function">square</span><span className="bracket">(</span><span className="parameter">x</span><span className="bracket">)</span><span className="operator">:</span>
    <span className="function">print</span><span className="bracket">(</span><span className="string">"This code is running on a remote worker!"</span><span className="bracket">)</span>
    <span className="keyword">return</span> <span className="parameter">x</span><span className="operator">**</span><span className="number">2</span>


<span className="decorator">@app.local_entrypoint()</span>
<span className="keyword">def</span> <span className="function">main</span><span className="bracket">()</span><span className="operator">:</span>
    <span className="function">print</span><span className="bracket">(</span><span className="string">"the square is"</span><span className="operator">,</span> <span className="variable">square</span><span className="operator">.</span><span className="function">remote</span><span className="bracket">(</span><span className="number">42</span><span className="bracket">)</span><span className="bracket">)</span></pre>
                </div>
                <p className="content-text">Save the code to a local file such as:</p>
                <div className="code-block">
                  <pre><span className="command">cat  get_started.py</span> <span className="comment"># At the prompt, paste the snippet and Ctrl-D to save it.</span></pre>
                </div>
                <p className="content-text">Now that the source code is saved locally, let's run it:</p>
                <div className="code-block">
                  <pre><span className="command">modal run get_started.py</span></pre>
                </div>
                <p className="content-text">Congratulations, you successfully executed a function on a remote worker!</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainContent;
