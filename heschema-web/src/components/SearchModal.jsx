import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Search, X, BookOpen, Layers, FileText, ArrowRight, CornerDownLeft, Sparkles } from 'lucide-react';
import { DOCS_SECTIONS, DOCS_PAGES } from '../data/docsContent';
import { KEYWORDS_DATA } from '../data/keywordsData';

export default function SearchModal({ isOpen, onClose, onSelectPage }) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => {
        if (inputRef.current) inputRef.current.focus();
      }, 50);
    }
  }, [isOpen]);

  // Build searchable index of all pages & keywords
  const searchIndex = useMemo(() => {
    const items = [];

    // Add documentation pages
    for (const [pageId, page] of Object.entries(DOCS_PAGES)) {
      items.push({
        id: pageId,
        type: 'doc',
        title: page.title,
        category: page.category || 'Documentation',
        summary: page.summary || '',
        content: page.content || '',
        breadcrumbs: page.breadcrumbs ? page.breadcrumbs.join(' > ') : 'Docs',
        icon: pageId.startsWith('kw-') ? 'keyword' : 'doc'
      });
    }

    // Add keyword specific entries
    for (const [kwId, kw] of Object.entries(KEYWORDS_DATA)) {
      items.push({
        id: `kw-${kwId}`,
        type: 'keyword',
        title: `${kw.name} (assertion keyword)`,
        category: `Custom Vocabulary: ${kw.vocabulary}`,
        summary: kw.summary,
        content: kw.edgeCases.join(' ') + ' ' + kw.operands.map(o => o.name + ' ' + o.description).join(' '),
        breadcrumbs: `Keywords > ${kw.name}`,
        icon: 'keyword'
      });
    }

    return items;
  }, []);

  // Filter items matching query
  const results = useMemo(() => {
    if (!query.trim()) {
      // Suggest popular pages when query is empty
      return searchIndex.filter(item => 
        ['overview', 'problem-statement', 'kw-compareFields', 'controlled-eval', 'h60-latency-study', 'flight-booking-example', 'kw-arithmeticEquals'].includes(item.id)
      );
    }

    const q = query.toLowerCase().trim();
    const scored = [];

    for (const item of searchIndex) {
      const titleLower = item.title.toLowerCase();
      const summaryLower = item.summary.toLowerCase();
      const contentLower = item.content.toLowerCase();
      const catLower = item.category.toLowerCase();

      let score = 0;
      let matchedIn = '';

      if (titleLower === q) score += 100;
      else if (titleLower.startsWith(q)) score += 60;
      else if (titleLower.includes(q)) score += 40;

      if (catLower.includes(q)) score += 20;

      if (summaryLower.includes(q)) {
        score += 25;
        matchedIn = item.summary;
      } else if (contentLower.includes(q)) {
        score += 15;
        // extract small snippet
        const idx = contentLower.indexOf(q);
        const start = Math.max(0, idx - 40);
        const end = Math.min(contentLower.length, idx + 80);
        matchedIn = '...' + item.content.slice(start, end).replace(/\n/g, ' ') + '...';
      }

      if (score > 0) {
        scored.push({
          ...item,
          score,
          snippet: matchedIn || item.summary
        });
      }
    }

    // Sort by score descending
    return scored.sort((a, b) => b.score - a.score).slice(0, 15);
  }, [query, searchIndex]);

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (results[selectedIndex]) {
        onSelectPage(results[selectedIndex].id);
        onClose();
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="search-modal-backdrop" onClick={onClose}>
      <div 
        className="search-modal-container"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="search-modal-header">
          <Search size={20} className="search-modal-icon" />
          <input
            ref={inputRef}
            type="text"
            className="search-modal-input"
            placeholder="Search documentation, keywords, research, examples..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
          />
          {query && (
            <button 
              type="button" 
              className="search-modal-clear"
              onClick={() => {
                setQuery('');
                if (inputRef.current) inputRef.current.focus();
              }}
            >
              <X size={16} />
            </button>
          )}
          <kbd className="modal-esc-badge" onClick={onClose}>ESC</kbd>
        </div>

        {/* Search Results List */}
        <div className="search-modal-body" ref={listRef}>
          <div className="search-results-label">
            {query.trim() ? (
              <span>{results.length} result{results.length === 1 ? '' : 's'} for "{query}"</span>
            ) : (
              <span className="flex-center gap-1"><Sparkles size={14} /> Recommended Quick Jumps</span>
            )}
          </div>

          {results.length === 0 ? (
            <div className="search-empty-state">
              <p>No results found for "<strong>{query}</strong>"</p>
              <p className="search-empty-sub">Try searching for keywords like <code>compareFields</code>, <code>Goa</code>, <code>latency</code>, <code>repair</code>, or <code>invoices</code>.</p>
            </div>
          ) : (
            <ul className="search-results-list">
              {results.map((item, idx) => (
                <li
                  key={`${item.id}-${idx}`}
                  className={`search-result-item ${selectedIndex === idx ? 'selected' : ''}`}
                  onClick={() => {
                    onSelectPage(item.id);
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  <div className="item-icon-wrapper">
                    {item.icon === 'keyword' ? (
                      <Layers size={18} className="item-icon keyword" />
                    ) : (
                      <FileText size={18} className="item-icon doc" />
                    )}
                  </div>

                  <div className="item-content-wrapper">
                    <div className="item-title-row">
                      <span className="item-title">{item.title}</span>
                      <span className="item-category-pill">{item.category}</span>
                    </div>

                    {item.snippet && (
                      <p className="item-snippet">{item.snippet}</p>
                    )}

                    <div className="item-breadcrumbs">{item.breadcrumbs}</div>
                  </div>

                  <div className="item-action-icon">
                    <CornerDownLeft size={14} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Modal Footer Keyboard Guide */}
        <div className="search-modal-footer">
          <div className="footer-keys">
            <span className="key-guide"><kbd>↑</kbd> <kbd>↓</kbd> to navigate</span>
            <span className="key-guide"><kbd>↵</kbd> to select</span>
            <span className="key-guide"><kbd>esc</kbd> to close</span>
          </div>
          <span className="footer-brand">HESchema Documentation Index</span>
        </div>
      </div>
    </div>
  );
}

