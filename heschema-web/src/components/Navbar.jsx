import React from 'react';
import { BookOpen, Terminal, Search, ShieldCheck } from 'lucide-react';

function GithubIcon({ size = 16 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

export default function Navbar({ activeTab, setActiveTab, onOpenSearch }) {
  return (
    <header className="k8s-navbar">
      <div className="navbar-container">
        {/* Brand */}
        <div className="navbar-brand" onClick={() => setActiveTab('docs')}>
          <div className="brand-logo">
            <ShieldCheck className="brand-icon" size={24} />
          </div>
          <div className="brand-text">
            <span className="brand-title">HESchema</span>
            <span className="brand-badge">v1.0.0</span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="navbar-nav">
          <button
            type="button"
            className={`nav-link ${activeTab === 'docs' ? 'active' : ''}`}
            onClick={() => setActiveTab('docs')}
          >
            <BookOpen size={16} />
            <span>Docs</span>
          </button>

          <button
            type="button"
            className={`nav-link ${activeTab === 'playground' ? 'active' : ''}`}
            onClick={() => setActiveTab('playground')}
          >
            <Terminal size={16} />
            <span>Playground</span>
            <span className="live-pill">Interactive</span>
          </button>

          <a
            href="https://github.com/HarshPopat23/HESchema-"
            target="_blank"
            rel="noopener noreferrer"
            className="nav-link github-link"
          >
            <GithubIcon size={16} />
            <span>GitHub</span>
          </a>
        </nav>

        {/* Right Actions with Interactive Working Search */}
        <div className="navbar-actions">
          <button 
            type="button"
            className="search-trigger-btn" 
            onClick={onOpenSearch}
            title="Search documentation (Press '/' or Ctrl+K)"
          >
            <Search size={15} />
            <span>Search docs...</span>
            <kbd className="kbd-shortcut">/</kbd>
          </button>

          <div className="status-indicator" title="Localhost client & engine active">
            <span className="status-dot"></span>
            <span className="status-text">Localhost Active</span>
          </div>
        </div>
      </div>
    </header>
  );
}
