import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export default function CodeBlock({ filename, code, language = 'json' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-container">
      {filename && (
        <div className="code-header">
          <span className="code-filename">{filename}</span>
          <button className="copy-button" onClick={handleCopy} title="Copy code">
            {copied ? (
              <>
                <Check size={14} className="copy-icon-success" />
                <span className="copy-text">Copied!</span>
              </>
            ) : (
              <>
                <Copy size={14} />
                <span className="copy-text">Copy</span>
              </>
            )}
          </button>
        </div>
      )}
      <pre className={`code-content language-${language}`}>
        <code>{code}</code>
      </pre>
    </div>
  );
}

export function CommandBox({ command, output, outputHeaders, outputRows }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="command-box-wrapper">
      <div className="command-box">
        <span className="command-prompt">$</span>
        <code className="command-text">{command}</code>
        <button className="command-copy-btn" onClick={handleCopy} title="Copy command">
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
      </div>

      {output && (
        <div className="command-output">
          <pre>{output}</pre>
        </div>
      )}

      {outputHeaders && outputRows && (
        <div className="terminal-table-wrapper">
          <table className="terminal-table">
            <thead>
              <tr>
                {outputHeaders.map((h, i) => (
                  <th key={i}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {outputRows.map((row, rIdx) => (
                <tr key={rIdx}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx}>
                      {typeof cell === 'string' && (cell === 'SchedulingGated' || cell === 'PASS' || cell === 'FAIL') ? (
                        <span className={`badge-status badge-${cell.toLowerCase()}`}>{cell}</span>
                      ) : (
                        cell
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

