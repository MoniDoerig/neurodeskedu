import { JSDOM } from 'jsdom';
import fs from 'fs';

/**
 * Parse an optional CLI JSON argument into an array of author names.
 * @param {string} rawAuthors
 * @returns {string[]}
 */
function parseAuthors(rawAuthors) {
  if (!rawAuthors || !rawAuthors.trim()) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawAuthors);
    if (Array.isArray(parsed)) {
      return parsed
        .map(author => String(author).trim())
        .filter(Boolean);
    }
    if (typeof parsed === 'string' && parsed.trim()) {
      return [parsed.trim()];
    }
  } catch (_err) {
    // Fall back to plain string handling.
  }

  return [rawAuthors.trim()];
}

/**
 * Upsert a single <meta> tag by attribute selector.
 * @param {Document} document
 * @param {string} attrName
 * @param {string} attrValue
 * @param {string} content
 */
function upsertMetaTag(document, attrName, attrValue, content) {
  if (!document.head) {
    return;
  }

  const selector = `meta[${attrName}="${attrValue}"]`;
  let tag = document.querySelector(selector);
  if (!tag) {
    tag = document.createElement('meta');
    tag.setAttribute(attrName, attrValue);
    document.head.appendChild(tag);
  }
  tag.setAttribute('content', content);
}

/**
 * Inject author metadata tags into the page head.
 * @param {Document} document
 * @param {string[]} authors
 */
function injectAuthorMetadata(document, authors) {
  if (!authors.length || !document.head) {
    return;
  }

  const joinedAuthors = authors.join(', ');
  upsertMetaTag(document, 'name', 'author', joinedAuthors);
  upsertMetaTag(document, 'property', 'article:author', joinedAuthors);

  document.querySelectorAll('meta[name="citation_author"]').forEach(tag => tag.remove());
  authors.forEach(author => {
    const citationTag = document.createElement('meta');
    citationTag.setAttribute('name', 'citation_author');
    citationTag.setAttribute('content', author);
    document.head.appendChild(citationTag);
  });
}

/**
 * Inject a DOI button and optional author metadata into an HTML file.
 * DOI injection is skipped when DOI is empty.
 * @param {string} doi
 * @param {string} htmlFilePath
 * @param {string[]} authors
 */
function injectPageMetadata(doi, htmlFilePath, authors) {
  if (!fs.existsSync(htmlFilePath)) {
    console.error('Error: File not found:', htmlFilePath);
    process.exit(1);
  }

  const htmlContent = fs.readFileSync(htmlFilePath, 'utf-8');
  const dom = new JSDOM(htmlContent);
  const document = dom.window.document;

  if (doi) {
    const container = document.querySelector('.article-header-buttons');
    if (!container) {
      console.warn(`Warning: .article-header-buttons not found in ${htmlFilePath}, skipping DOI button`);
    } else {
      const existingButton = Array.from(container.querySelectorAll('a')).find(a =>
        a.href.includes('doi.org')
      );

      if (existingButton) {
        existingButton.href = doi;
        existingButton.textContent = doi;
      } else {
        const link = document.createElement('a');
        link.textContent = doi;
        link.href = doi;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.className = 'btn btn-sm nav-link pst-navbar-icon theme-switch-button';

        container.prepend(link);
      }
      console.log(`DOI metadata injected for ${htmlFilePath}`);
    }
  }

  if (authors.length) {
    injectAuthorMetadata(document, authors);
    console.log(`Author metadata injected for ${htmlFilePath}: ${authors.join(', ')}`);
  }

  fs.writeFileSync(htmlFilePath, dom.serialize());
}

// --- CLI Entry Point ---
const [doi = '', htmlFilePath, rawAuthors = ''] = process.argv.slice(2);

if (!htmlFilePath) {
  console.error('Usage: node add-doi-button.js <DOI_OR_EMPTY> <HTML_FILE_PATH> <AUTHORS_JSON_OR_EMPTY>');
  process.exit(1);
}

const authors = parseAuthors(rawAuthors);
injectPageMetadata(doi, htmlFilePath, authors);
