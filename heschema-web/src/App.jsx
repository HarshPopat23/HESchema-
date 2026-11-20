import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import DocsLayout from './components/DocsLayout';
import FullPlayground from './components/FullPlayground';
import SearchModal from './components/SearchModal';
import './index.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('docs'); // 'docs' | 'playground'
  const [activeDocPage, setActiveDocPage] = useState('overview');
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // Global Keyboard Shortcut Listener for '/' and 'Ctrl+K' / 'Cmd+K'
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't intercept if user is typing in an active input or textarea
      const targetTag = e.target.tagName.toLowerCase();
      const isInput = targetTag === 'input' || targetTag === 'textarea';

      if ((e.key === '/' && !isInput) || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k')) {
        e.preventDefault();
        setIsSearchOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleOpenPlayground = () => {
    setActiveTab('playground');
  };

  const handleSelectPageFromSearch = (pageId) => {
    setActiveTab('docs');
    setActiveDocPage(pageId);
    setIsSearchOpen(false);
  };

  return (
    <div className="heschema-app">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenSearch={() => setIsSearchOpen(true)}
      />

      <div className="main-viewport">
        {activeTab === 'docs' && (
          <DocsLayout
            activePageId={activeDocPage}
            setActivePageId={setActiveDocPage}
            onOpenPlayground={handleOpenPlayground}
          />
        )}

        {activeTab === 'playground' && (
          <FullPlayground />
        )}
      </div>

      {/* Global Interactive Search Modal */}
      <SearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelectPage={handleSelectPageFromSearch}
      />
    </div>
  );
}
