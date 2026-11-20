import React, { useState, useMemo, useEffect } from 'react';
import { 
  ChevronRight, 
  ChevronDown, 
  Search, 
  Edit3, 
  PlusCircle, 
  AlertCircle, 
  Printer, 
  ExternalLink,
  BookOpen,
  Sparkles,
  ArrowRight,
  Code2,
  Cpu,
  BarChart2,
  FileCheck2,
  Terminal,
  Hash
} from 'lucide-react';
import { DOCS_SECTIONS, DOCS_PAGES } from '../data/docsContent';
import { KEYWORDS_DATA } from '../data/keywordsData';
import CodeBlock, { CommandBox } from './CodeBlock';
import KeywordPlayground from './KeywordPlayground';

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-');
}

export default function DocsLayout({ activePageId, setActivePageId, onOpenPlayground }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeHeadingId, setActiveHeadingId] = useState('');
  const [expandedSections, setExpandedSections] = useState({
    'getting-started': true,
    'concepts': true,
    'vocabularies': true,
    'keywords': true,
    'research': true,
    'examples': true
  });

  const toggleSection = (sectionId) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionId]: !prev[sectionId]
    }));
  };

  // Filtered navigation tree based on search query
  const filteredSections = useMemo(() => {
    if (!searchQuery.trim()) return DOCS_SECTIONS;
    const q = searchQuery.toLowerCase();
    return DOCS_SECTIONS.map(sec => {
      const matchingPages = sec.pages.filter(p => 
        p.title.toLowerCase().includes(q) || p.id.toLowerCase().includes(q)
      );
      return {
        ...sec,
        pages: matchingPages
      };
    }).filter(sec => sec.pages.length > 0);
  }, [searchQuery]);

  const activePage = DOCS_PAGES[activePageId] || DOCS_PAGES['overview'];
  const activeKeyword = activePageId.startsWith('kw-') && activePageId !== 'kw-contract-assertions'
    ? KEYWORDS_DATA[activePageId.replace('kw-', '')]
    : null;

  // DYNAMICALLY EXTRACT HEADINGS FOR "ON THIS PAGE" TABLE OF CONTENTS
  const pageHeadings = useMemo(() => {
    if (activeKeyword) {
      const headings = [
        { id: 'syntax-specification', text: 'Syntax Reference', level: 2 },
      ];
      if (activeKeyword.modeDetails) {
        headings.push({ id: 'mode-semantics', text: 'Comparison Modes', level: 2 });
      }
      headings.push(
        { id: 'edge-cases', text: 'Assertion Semantics & Edge Cases', level: 2 },
        { id: 'schema-example', text: 'Declarative Schema Example', level: 2 },
        { id: 'validation-check', text: 'Validation Check', level: 2 },
        { id: 'live-playground', text: 'Interactive Playground', level: 2 }
      );
      return headings;
    }

    if (!activePage || !activePage.content) return [];

    const lines = activePage.content.split('\n');
    const headings = [];

    for (const line of lines) {
      if (line.startsWith('## ')) {
        const text = line.replace('## ', '').trim();
        headings.push({ id: slugify(text), text, level: 2 });
      } else if (line.startsWith('### ')) {
        const text = line.replace('### ', '').trim();
        headings.push({ id: slugify(text), text, level: 3 });
      }
    }

    return headings;
  }, [activePage, activeKeyword]);

  // Set default active heading when page changes
  useEffect(() => {
    if (pageHeadings.length > 0) {
      setActiveHeadingId(pageHeadings[0].id);
    }
    // Scroll center content to top
    const mainEl = document.querySelector('.docs-center-content');
    if (mainEl) mainEl.scrollTop = 0;
  }, [activePageId, pageHeadings]);

  // Track active heading on scroll
  useEffect(() => {
    const handleScroll = () => {
      const headingElements = pageHeadings.map(h => document.getElementById(h.id)).filter(Boolean);
      const scrollPos = window.scrollY + 120;

      for (let i = headingElements.length - 1; i >= 0; i--) {
        const el = headingElements[i];
        if (el.offsetTop <= scrollPos) {
          setActiveHeadingId(el.id);
          break;
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [pageHeadings]);

  const scrollToHeading = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveHeadingId(id);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="docs-wrapper">
      {/* LEFT SIDEBAR */}
      <aside className="docs-left-sidebar">
        <div className="sidebar-search-box">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search this site"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button className="search-clear" onClick={() => setSearchQuery('')}>×</button>
          )}
        </div>

        <nav className="sidebar-nav-tree">
          {filteredSections.map(sec => {
            const isExpanded = !!expandedSections[sec.id] || !!searchQuery;
            return (
              <div key={sec.id} className="nav-tree-section">
                <div 
                  className="section-header"
                  onClick={() => toggleSection(sec.id)}
                >
                  <span className="caret-icon">
                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </span>
                  <span className="section-title">{sec.title}</span>
                </div>

                {isExpanded && (
                  <ul className="section-pages-list">
                    {sec.pages.map(page => (
                      <li key={page.id} className="page-item">
                        <button
                          type="button"
                          className={`page-link ${activePageId === page.id ? 'active' : ''}`}
                          onClick={() => setActivePageId(page.id)}
                        >
                          {page.keywordId && <span className="keyword-bullet">`</span>}
                          <span>{page.title}</span>
                          {page.keywordId && <span className="keyword-bullet">`</span>}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </nav>
      </aside>

      {/* CENTER CONTENT */}
      <main className="docs-center-content">
        {/* Breadcrumb Navigation */}
        <nav className="breadcrumbs" aria-label="Breadcrumbs">
          {activePage.breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={idx}>
              {idx > 0 && <span className="breadcrumb-separator">/</span>}
              <span className={`breadcrumb-item ${idx === activePage.breadcrumbs.length - 1 ? 'current' : ''}`}>
                {crumb}
              </span>
            </React.Fragment>
          ))}
        </nav>

        <header className="page-header">
          <h1 className="page-title">{activePage.title}</h1>
          {activePage.summary && <p className="page-lead">{activePage.summary}</p>}
        </header>

        {/* KUBERNETES DOCS HOME HUB CARDS (on overview page) */}
        {activePageId === 'overview' && (
          <div className="k8s-home-hub-cards">
            <div className="hub-card" onClick={() => setActivePageId('problem-statement')}>
              <div className="hub-card-icon"><Cpu size={24} /></div>
              <h3 className="hub-card-title">Core Concepts</h3>
              <p className="hub-card-text">Understand why ordinary JSON Schema fails for LLM tools, StateStore locking, and the execution boundary.</p>
              <span className="hub-card-link">Learn concepts →</span>
            </div>

            <div className="hub-card" onClick={() => setActivePageId('vocab-overview')}>
              <div className="hub-card-icon"><Code2 size={24} /></div>
              <h3 className="hub-card-title">Custom Vocabularies</h3>
              <p className="hub-card-text">Draft 2020-12 meta-schemas for cross-field comparisons, unique keys, ordering, and exact decimals.</p>
              <span className="hub-card-link">Explore vocabularies →</span>
            </div>

            <div className="hub-card" onClick={() => setActivePageId('controlled-eval')}>
              <div className="hub-card-icon"><BarChart2 size={24} /></div>
              <h3 className="hub-card-title">Empirical Research</h3>
              <p className="hub-card-text">Review 65-case and 2,160-slot evaluations, latency metrics, and honest negative findings.</p>
              <span className="hub-card-link">View research data →</span>
            </div>

            <div className="hub-card" onClick={() => setActivePageId('flight-booking-example')}>
              <div className="hub-card-icon"><FileCheck2 size={24} /></div>
              <h3 className="hub-card-title">Examples & Contracts</h3>
              <p className="hub-card-text">Production contracts for flight bookings, Peppol invoices, custom travel, and ML tensor alignment.</p>
              <span className="hub-card-link">Browse contracts →</span>
            </div>

            <div className="hub-card hub-card-accent" onClick={onOpenPlayground}>
              <div className="hub-card-icon"><Terminal size={24} /></div>
              <h3 className="hub-card-title">Interactive Playground</h3>
              <p className="hub-card-text">Test keyword assertions, simulate state mismatches (e.g. Pune vs Goa), and replay benchmark arms.</p>
              <span className="hub-card-link">Launch Playground →</span>
            </div>
          </div>
        )}

        {/* If Active Page is a Keyword Page */}
        {activeKeyword && (
          <div className="keyword-detail-section">
            <div className="keyword-meta-banner">
              <span className="pill-dialect">Dialect: {activeKeyword.vocabulary}</span>
              <span className="pill-id">Keyword: <code>{activeKeyword.name}</code></span>
            </div>

            <p className="keyword-desc">{activeKeyword.summary}</p>

            <h2 id="syntax-specification" className="docs-heading">
              Syntax & Operands Reference
              <a href="#syntax-specification" className="heading-anchor"><Hash size={16} /></a>
            </h2>
            <div className="table-wrapper">
              <table className="k8s-docs-table">
                <thead>
                  <tr>
                    <th>Operand</th>
                    <th>Expected Type</th>
                    <th>Semantic Meaning</th>
                  </tr>
                </thead>
                <tbody>
                  {activeKeyword.operands.map((op, i) => (
                    <tr key={i}>
                      <td><code>{op.name}</code></td>
                      <td><span className="type-badge">{op.type}</span></td>
                      <td>{op.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {activeKeyword.modeDetails && (
              <>
                <h2 id="mode-semantics" className="docs-heading">
                  Coordinate & Comparison Modes
                  <a href="#mode-semantics" className="heading-anchor"><Hash size={16} /></a>
                </h2>
                <div className="table-wrapper">
                  <table className="k8s-docs-table">
                    <thead>
                      <tr>
                        <th>Mode</th>
                        <th>Operators / Formats</th>
                        <th>Behavioral Rules</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activeKeyword.modeDetails.map((m, i) => (
                        <tr key={i}>
                          <td><code>{m.mode}</code></td>
                          <td><code>{m.operators}</code></td>
                          <td>{m.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            <h2 id="edge-cases" className="docs-heading">
              Assertion Semantics & Edge Cases
              <a href="#edge-cases" className="heading-anchor"><Hash size={16} /></a>
            </h2>
            <ul className="edge-cases-list">
              {activeKeyword.edgeCases.map((ec, i) => (
                <li key={i}>{ec}</li>
              ))}
            </ul>

            <h2 id="schema-example" className="docs-heading">
              Declarative Schema Example
              <a href="#schema-example" className="heading-anchor"><Hash size={16} /></a>
            </h2>
            <p>To use this keyword in JSON Schema Draft 2020-12, define the dialect meta-schema in <code>$schema</code>:</p>

            <CodeBlock 
              filename={`schemas/${activeKeyword.id}-example.json`}
              code={JSON.stringify(activeKeyword.exampleSchema, null, 2)}
              language="json"
            />

            <h2 id="validation-check" className="docs-heading">
              Validation Check
              <a href="#validation-check" className="heading-anchor"><Hash size={16} /></a>
            </h2>
            <p>After declaring the schema, you can check sample instance state:</p>
            <CommandBox 
              command={`heschema validate --schema schemas/${activeKeyword.id}-example.json --data instance.json`}
              outputHeaders={['NAME', 'READY', 'STATUS', 'RESTARTS', 'AGE']}
              outputRows={[
                [`${activeKeyword.id}-check`, '1/1', 'PASS', '0', '12ms']
              ]}
            />

            <h2 id="live-playground" className="docs-heading">
              Interactive Keyword Playground
              <a href="#live-playground" className="heading-anchor"><Hash size={16} /></a>
            </h2>
            <p>Experiment with schema rules and test instance vectors live in your browser:</p>
            <KeywordPlayground keywordData={activeKeyword} />
          </div>
        )}

        {/* Regular Markdown / Content Pages */}
        {!activeKeyword && (
          <div className="docs-prose">
            {/* Show Kubernetes-inspired example code block on problem-statement */}
            {activePageId === 'problem-statement' && (
              <>
                <div className="alert alert-warning">
                  <strong>Safety Principle:</strong> A valid schema does not guarantee a safe or factually accurate LLM action.
                </div>

                <p>Consider an LLM tool-calling agent configured with the following scheduling and trip contract:</p>
                <CodeBlock 
                  filename="pods/pod-with-scheduling-gates.yaml"
                  code={`apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  schedulingGates:
    - name: example.com/foo
    - name: example.com/bar
  containers:
    - name: pause
      image: registry.k8s.io/pause:3.6`}
                  language="yaml"
                />

                <p>After the Pod's creation, you can check its state using:</p>
                <CommandBox 
                  command="kubectl get pod test-pod"
                  outputHeaders={['NAME', 'READY', 'STATUS', 'RESTARTS', 'AGE']}
                  outputRows={[
                    ['test-pod', '0/1', 'SchedulingGated', '0', '7s']
                  ]}
                />
                <p>The output reveals it's in <code>SchedulingGated</code> state, waiting for explicit external gate confirmation before execution.</p>
              </>
            )}

            {/* Render page markdown text with distinct heading IDs and anchor links */}
            <div className="markdown-body">
              {renderFormattedContent(activePage.content)}
            </div>

            <div className="docs-footer-cta">
              <div className="cta-box">
                <Sparkles className="cta-icon" size={24} />
                <div className="cta-content">
                  <h4>Want to test these schemas interactively?</h4>
                  <p>Open the live HESchema Playground to test contracts, confirmed state mismatches, and 3-arm experiments.</p>
                </div>
                <button className="cta-btn" onClick={onOpenPlayground}>
                  <span>Launch Playground</span>
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* RIGHT SIDEBAR ("ON THIS PAGE") */}
      <aside className="docs-right-sidebar">
        <div className="page-actions-block">
          <a
            href="https://github.com/HarshPopat23/HESchema-/blob/main/README.md"
            target="_blank"
            rel="noopener noreferrer"
            className="action-link"
          >
            <Edit3 size={14} />
            <span>Edit this page</span>
          </a>
          <a
            href="https://github.com/HarshPopat23/HESchema-/issues/new"
            target="_blank"
            rel="noopener noreferrer"
            className="action-link"
          >
            <PlusCircle size={14} />
            <span>Create child page</span>
          </a>
          <a
            href="https://github.com/HarshPopat23/HESchema-/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="action-link"
          >
            <AlertCircle size={14} />
            <span>Create an issue</span>
          </a>
          <button className="action-link btn-print" onClick={handlePrint}>
            <Printer size={14} />
            <span>Print entire section</span>
          </button>
        </div>

        {/* DYNAMIC TOC BASED ON EXACT ACTIVE PAGE HEADINGS */}
        <div className="toc-block">
          <h4 className="toc-title">ON THIS PAGE</h4>
          {pageHeadings.length === 0 ? (
            <p className="toc-empty">No sections on this page</p>
          ) : (
            <ul className="toc-list">
              {pageHeadings.map(heading => (
                <li 
                  key={heading.id} 
                  className={`toc-item level-${heading.level}`}
                >
                  <a
                    href={`#${heading.id}`}
                    className={`toc-link ${activeHeadingId === heading.id ? 'active' : ''}`}
                    onClick={(e) => {
                      e.preventDefault();
                      scrollToHeading(heading.id);
                    }}
                  >
                    {heading.text}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
}

function renderFormattedContent(content) {
  if (!content) return null;

  const lines = content.split('\n');
  const elements = [];
  let buffer = [];
  let inCodeBlock = false;
  let codeLang = '';
  let keyIndex = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <CodeBlock
            key={keyIndex++}
            code={buffer.join('\n')}
            language={codeLang || 'text'}
          />
        );
        buffer = [];
        inCodeBlock = false;
      } else {
        if (buffer.length > 0) {
          elements.push(<p key={keyIndex++} dangerouslySetInnerHTML={{ __html: formatInline(buffer.join(' ')) }} />);
          buffer = [];
        }
        codeLang = line.replace('```', '').trim();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      buffer.push(line);
      continue;
    }

    // Heading Level 2 (##)
    if (line.startsWith('## ')) {
      if (buffer.length > 0) {
        elements.push(<p key={keyIndex++} dangerouslySetInnerHTML={{ __html: formatInline(buffer.join(' ')) }} />);
        buffer = [];
      }
      const text = line.replace('## ', '').trim();
      const slug = slugify(text);
      elements.push(
        <h2 key={keyIndex++} id={slug} className="docs-heading">
          {text}
          <a href={`#${slug}`} className="heading-anchor" title={`Link to ${text}`}><Hash size={18} /></a>
        </h2>
      );
      continue;
    }

    // Heading Level 3 (###)
    if (line.startsWith('### ')) {
      if (buffer.length > 0) {
        elements.push(<p key={keyIndex++} dangerouslySetInnerHTML={{ __html: formatInline(buffer.join(' ')) }} />);
        buffer = [];
      }
      const text = line.replace('### ', '').trim();
      const slug = slugify(text);
      elements.push(
        <h3 key={keyIndex++} id={slug} className="docs-heading">
          {text}
          <a href={`#${slug}`} className="heading-anchor" title={`Link to ${text}`}><Hash size={15} /></a>
        </h3>
      );
      continue;
    }

    // GitHub style alerts
    if (line.startsWith('> [!NOTE]') || line.startsWith('> [!IMPORTANT]') || line.startsWith('> [!WARNING]')) {
      if (buffer.length > 0) {
        elements.push(<p key={keyIndex++} dangerouslySetInnerHTML={{ __html: formatInline(buffer.join(' ')) }} />);
        buffer = [];
      }
      const alertType = line.includes('WARNING') ? 'warning' : (line.includes('IMPORTANT') ? 'important' : 'note');
      const alertLines = [];
      i++;
      while (i < lines.length && lines[i].startsWith('>')) {
        alertLines.push(lines[i].replace(/^>\s?/, ''));
        i++;
      }
      i--; // adjust loop
      elements.push(
        <div key={keyIndex++} className={`alert alert-${alertType}`}>
          <div dangerouslySetInnerHTML={{ __html: formatInline(alertLines.join(' ')) }} />
        </div>
      );
      continue;
    }

    // Markdown Table Detection
    if (line.startsWith('|') && line.endsWith('|')) {
      if (buffer.length > 0) {
        elements.push(<p key={keyIndex++} dangerouslySetInnerHTML={{ __html: formatInline(buffer.join(' ')) }} />);
        buffer = [];
      }
      const tableLines = [line];
      while (i + 1 < lines.length && lines[i + 1].startsWith('|')) {
        i++;
        tableLines.push(lines[i]);
      }
      elements.push(renderMarkdownTable(tableLines, keyIndex++));
      continue;
    }

    // Unordered lists
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      if (buffer.length > 0) {
        elements.push(<p key={keyIndex++} dangerouslySetInnerHTML={{ __html: formatInline(buffer.join(' ')) }} />);
        buffer = [];
      }
      const listItems = [line.trim().substring(2)];
      while (i + 1 < lines.length && (lines[i + 1].trim().startsWith('- ') || lines[i + 1].trim().startsWith('* '))) {
        i++;
        listItems.push(lines[i].trim().substring(2));
      }
      elements.push(
        <ul key={keyIndex++} className="docs-list">
          {listItems.map((item, idx) => (
            <li key={idx} dangerouslySetInnerHTML={{ __html: formatInline(item) }} />
          ))}
        </ul>
      );
      continue;
    }

    if (!line.trim()) {
      if (buffer.length > 0) {
        elements.push(<p key={keyIndex++} dangerouslySetInnerHTML={{ __html: formatInline(buffer.join(' ')) }} />);
        buffer = [];
      }
      continue;
    }

    buffer.push(line);
  }

  if (buffer.length > 0) {
    elements.push(<p key={keyIndex++} dangerouslySetInnerHTML={{ __html: formatInline(buffer.join(' ')) }} />);
  }

  return elements;
}

function formatInline(str) {
  return str
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
}

function renderMarkdownTable(lines, key) {
  if (lines.length < 2) return null;
  const parseRow = (line) => line.split('|').slice(1, -1).map(c => c.trim());
  const headers = parseRow(lines[0]);
  const rows = lines.slice(2).map(parseRow);

  return (
    <div key={key} className="table-wrapper">
      <table className="k8s-docs-table">
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={i} dangerouslySetInnerHTML={{ __html: formatInline(h) }} />
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rI) => (
            <tr key={rI}>
              {row.map((cell, cI) => (
                <td key={cI} dangerouslySetInnerHTML={{ __html: formatInline(cell) }} />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
