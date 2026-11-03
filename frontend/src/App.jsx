import { useEffect, useRef, useState } from "react";
import { askQuestion, deleteDocument, getDocument, uploadDocument } from "./services/api.js";

const ACTIVE_DOCUMENT_KEY = "fomuwise.activeDocumentId";
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const tokenKey = (documentId) => "fomuwise.documentToken." + documentId;

function clearStoredWorkspace(documentId) {
  if (documentId) sessionStorage.removeItem(tokenKey(documentId));
  sessionStorage.removeItem(ACTIVE_DOCUMENT_KEY);
}

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) return Math.max(1, Math.round(bytes / 1024)) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

function Source({ page, quote }) {
  if (!quote) return null;
  return (
    <div className="source">
      <span className="source-page">Page {page}</span>
      <span className="source-quote">“{quote}”</span>
    </div>
  );
}

function SectionHeading({ eyebrow, title, count }) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
      </div>
      {typeof count === "number" && <span className="count-pill">{count}</span>}
    </div>
  );
}

function EmptyList({ children }) {
  return <p className="empty-note">{children}</p>;
}

function App() {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [documentData, setDocumentData] = useState(null);
  const [token, setToken] = useState("");
  const [loadingSaved, setLoadingSaved] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [checkedItems, setCheckedItems] = useState({});

  useEffect(() => {
    const activeId = sessionStorage.getItem(ACTIVE_DOCUMENT_KEY);
    const savedToken = activeId ? sessionStorage.getItem(tokenKey(activeId)) : "";
    if (!activeId || !savedToken) {
      setLoadingSaved(false);
      return;
    }

    getDocument(activeId, savedToken)
      .then((data) => {
        setDocumentData(data);
        setToken(savedToken);
      })
      .catch((restoreError) => {
        clearStoredWorkspace(activeId);
        if (restoreError.status !== 404 && restoreError.status !== 410) {
          setError(restoreError.message);
        }
      })
      .finally(() => setLoadingSaved(false));
  }, []);

  function selectFile(candidate) {
    setError("");
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".pdf")) {
      setFile(null);
      setError("Choose a PDF file. FomuWise currently supports text-based PDFs.");
      return;
    }
    if (candidate.size > MAX_UPLOAD_BYTES) {
      setFile(null);
      setError("This file is larger than the 10 MB upload limit.");
      return;
    }
    setFile(candidate);
  }

  function onDrop(event) {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files?.[0]);
  }

  async function onUpload(event) {
    event.preventDefault();
    if (!file || uploading) return;
    setUploading(true);
    setError("");
    setAnswer(null);
    try {
      if (documentData?.document_id) clearStoredWorkspace(documentData.document_id);
      const result = await uploadDocument(file);
      sessionStorage.setItem(tokenKey(result.document_id), result.access_token);
      sessionStorage.setItem(ACTIVE_DOCUMENT_KEY, result.document_id);
      setToken(result.access_token);
      setDocumentData(result);
      setCheckedItems({});
      setFile(null);
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setUploading(false);
    }
  }

  async function onAsk(event) {
    event.preventDefault();
    if (!documentData || !question.trim() || asking) return;
    setAsking(true);
    setError("");
    try {
      const result = await askQuestion(
        documentData.document_id,
        token,
        question.trim(),
      );
      setAnswer(result);
      setQuestion("");
    } catch (questionError) {
      setError(questionError.message);
    } finally {
      setAsking(false);
    }
  }

  async function onDelete() {
    if (!documentData || deleting) return;
    setDeleting(true);
    setError("");
    try {
      await deleteDocument(documentData.document_id, token);
      clearStoredWorkspace(documentData.document_id);
      setDocumentData(null);
      setToken("");
      setAnswer(null);
      setCheckedItems({});
      setFile(null);
    } catch (deleteError) {
      setError(deleteError.message);
    } finally {
      setDeleting(false);
    }
  }

  async function startNewNotice() {
    const oldDocumentId = documentData?.document_id;
    const oldToken = token;
    if (oldDocumentId) clearStoredWorkspace(oldDocumentId);
    setDocumentData(null);
    setToken("");
    setFile(null);
    setError("");
    setAnswer(null);
    setQuestion("");
    setCheckedItems({});
    if (oldDocumentId && oldToken) {
      try {
        await deleteDocument(oldDocumentId, oldToken);
      } catch {
        // The local session is cleared even if the workspace has already expired.
      }
    }
  }

  function toggleChecklistItem(index) {
    setCheckedItems((current) => ({ ...current, [index]: !current[index] }));
  }

  const analysis = documentData?.analysis;
  const requiredDocuments = analysis?.required_documents || [];
  const completedCount = Object.values(checkedItems).filter(Boolean).length;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="FomuWise home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 40 40" role="img">
              <path d="M11 8h18v5H16v6h11v5H16v9h-5V8Z" />
              <rect x="23" y="22" width="12" height="12" rx="2" />
              <path className="brand-check" d="m26.5 28 1.8 1.8 3.4-3.8" />
            </svg>
          </span>
          <span className="brand-name">Fomu<span>Wise</span></span>
        </a>
        <nav className="topbar-right" aria-label="Main navigation">
          <span className="desk-label">Bursary &amp; scholarship desk</span>
          <span className="secure-note"><span className="secure-dot" /> Private by design</span>
          <a className="help-link" href={documentData ? "#workspace-guide" : "#how-it-works"}>How FomuWise works </a>
        </nav>
      </header>

      <main id="top">
        {!documentData ? (
          <>
          <section className="hero-layout">
            <div className="hero-copy">
              <span className="hero-kicker"><span className="kicker-rule" aria-hidden="true" /> A clearer application desk</span>
              <h1>Read the notice.<br /><em>Know your next step.</em></h1>
              <p className="hero-intro">
                FomuWise turns bursary and scholarship notices into a clear, cited plan—so you can see what matters, what to gather, and when to act.
              </p>
              <div className="hero-manifesto">
                <span className="manifesto-mark" aria-hidden="true">F.</span>
                <p>Every detail stays close to its page in the original notice.</p>
              </div>
              <div className="trust-note">
                <span className="trust-icon" aria-hidden="true">✦</span>
                <span>Your original PDF is discarded after its text is extracted. Workspace data expires after 12 hours.</span>
              </div>
            </div>

            <div className="upload-card">
              <div className="upload-card-topline"><span>FOMUWISE / DOCUMENT INTAKE</span><span>01—03</span></div>
              <div className="card-heading">
                <div className="step-badge">01</div>
                <div>
                  <p className="eyebrow">Your application desk</p>
                  <h2>Start with the notice</h2>
                </div>
              </div>
              <form onSubmit={onUpload}>
                <input
                  ref={inputRef}
                  className="visually-hidden"
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={(event) => selectFile(event.target.files?.[0])}
                  aria-label="Choose a PDF notice"
                />
                <button
                  type="button"
                  className={"dropzone" + (dragging ? " is-dragging" : "")}
                  onClick={() => inputRef.current?.click()}
                  onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={onDrop}
                  aria-describedby="upload-hint"
                >
                  <span className="upload-icon-wrap" aria-hidden="true">
                    <svg viewBox="0 0 48 48">
                      <path d="M14 5h14l9 9v27H14a4 4 0 0 1-4-4V9a4 4 0 0 1 4-4Z" />
                      <path d="M28 5v10h9M18 28h14M18 34h10M24 18v8m-3-3 3-3 3 3" />
                    </svg>
                  </span>
                  {file ? (
                    <>
                      <strong className="selected-file">{file.name}</strong>
                      <span>{formatFileSize(file.size)} · Ready to analyse</span>
                    </>
                  ) : (
                    <>
                      <strong>Drop your notice here</strong>
                      <span>or <span className="browse-link">browse files</span></span>
                    </>
                  )}
                </button>
                <p className="upload-hint" id="upload-hint">PDF only · Up to 10 MB · Text-based PDFs only</p>
                <button className="button button-primary upload-button" type="submit" disabled={!file || uploading}>
                  {uploading ? (
                    <><span className="spinner" /> Reading your notice…</>
                  ) : (
                    <><span className="button-index" aria-hidden="true">01</span>Build my guide</>
                  )}
                </button>
              </form>
              <div className="privacy-banner">
                <span aria-hidden="true">▣</span>
                <p>Extracted text is sent to Google’s Gemini API using Gemma 4 to create your guide. Don’t upload information you aren’t allowed to share.</p>
              </div>
              {loadingSaved && <p className="restore-note">Checking for your current document…</p>}
              {error && <div className="error-banner" role="alert">{error}</div>}
            </div>
          </section>
          <section className="how-steps" id="how-it-works" aria-labelledby="process-heading">
            <div className="how-intro">
              <p className="eyebrow">The FomuWise method</p>
              <h2 id="process-heading">From notice<br />to next step.</h2>
              <p>A simple, careful reading of the document you already have.</p>
            </div>
            <div className="step-stories">
              <article className="step-story">
                <span className="editorial-index">01</span>
                <div><h3>Bring the notice</h3><p>Upload a text-based PDF. Your original file is discarded after its text is extracted.</p></div>
              </article>
              <article className="step-story">
                <span className="editorial-index">02</span>
                <div><h3>See what matters</h3><p>Get eligibility, required documents, dates and steps—with page references to check.</p></div>
              </article>
              <article className="step-story">
                <span className="editorial-index">03</span>
                <div><h3>Ask with context</h3><p>Ask follow-up questions grounded in that notice, then confirm details with its issuer.</p></div>
              </article>
            </div>
          </section>
          </>
        ) : (
          <section className="workspace" id="workspace-guide">
            <div className="workspace-layout">
              <aside className="workspace-sidebar" aria-label="Application workspace">
                <div className="sidebar-file">
                  <p className="eyebrow">Active notice</p>
                  <div className="sidebar-file-line"><span className="sidebar-file-icon" aria-hidden="true">PDF</span><span>FomuWise desk</span></div>
                  <strong title={documentData.filename}>{documentData.filename}</strong>
                  <span className="sidebar-file-meta">{documentData.page_count} {documentData.page_count === 1 ? "page" : "pages"} · {formatFileSize(documentData.file_size_bytes)}</span>
                </div>
                <nav className="workspace-nav" aria-label="Guide sections">
                  <a href="#workspace-overview"><span>01</span> Overview</a>
                  <a href="#requirements"><span>02</span> Eligibility</a>
                  <a href="#documents"><span>03</span> Documents</a>
                  <a href="#deadlines"><span>04</span> Important dates</a>
                  <a href="#application-steps"><span>05</span> Application steps</a>
                  <a href="#questions"><span>06</span> Ask the notice</a>
                </nav>
                <div className="sidebar-progress">
                  <div className="sidebar-progress-heading"><span>Checklist</span><strong>{completedCount}/{requiredDocuments.length}</strong></div>
                  <div className="sidebar-progress-track" role="progressbar" aria-label="Documents prepared" aria-valuemin="0" aria-valuemax={Math.max(requiredDocuments.length, 1)} aria-valuenow={completedCount}><span style={{ width: (requiredDocuments.length ? (completedCount / requiredDocuments.length) * 100 : 0) + "%" }} /></div>
                  <p>{requiredDocuments.length ? (requiredDocuments.length - completedCount) + " to prepare" : "No document list found"}</p>
                </div>
                <div className="sidebar-deadline">
                  <p className="eyebrow">Next date</p>
                  <strong>{analysis?.deadlines?.[0]?.date_text || "No deadline listed"}</strong>
                  {analysis?.deadlines?.[0]?.normalized_date && <span>{formatDate(analysis.deadlines[0].normalized_date)}</span>}
                </div>
                <button className="sidebar-delete" type="button" onClick={onDelete} disabled={deleting}>
                  {deleting ? "Deleting workspace…" : "Delete workspace"}
                </button>
              </aside>
              <div className="workspace-main">
            <div className="workspace-topline" id="workspace-overview">
              <div>
                <a className="back-link" href="#top" onClick={(event) => { event.preventDefault(); void startNewNotice(); }}>
                  New notice
                </a>
                <p className="eyebrow workspace-label">Your application guide</p>
                <h1 className="workspace-title">Your notice, made clear.</h1>
                <p className="workspace-subtitle">A cited guide to the requirements, dates, and next steps in your PDF.</p>
              </div>
            </div>

            <div className="document-strip">
              <div className="pdf-glyph" aria-hidden="true">PDF</div>
              <div className="document-meta">
                <strong>{documentData.filename}</strong>
                <span>{documentData.page_count} {documentData.page_count === 1 ? "page" : "pages"} · {formatFileSize(documentData.file_size_bytes)}</span>
              </div>
              <div className="expires-meta">
                <span className="secure-dot" />
                Expires {formatDate(documentData.expires_at)}
              </div>
            </div>

            {error && <div className="error-banner workspace-error" role="alert">{error}</div>}

            <div className="summary-card" id="summary">
              <div className="summary-icon" aria-hidden="true">✦</div>
              <div className="summary-content">
                <p className="eyebrow">The short version</p>
                <p className="summary-text">{analysis?.summary?.text || "No summary was verified for this notice."}</p>
                <Source page={analysis?.summary?.page_number} quote={analysis?.summary?.evidence_quote} />
              </div>
              <div className="summary-side-note">
                <span className="summary-side-number">{documentData.page_count.toString().padStart(2, "0")}</span>
                <span>source<br />pages</span>
              </div>
            </div>

            <div className="dashboard-grid">
              <section className="panel requirements-panel" id="requirements">
                <SectionHeading eyebrow="Before you apply" title="Eligibility" count={analysis?.eligibility_requirements?.length || 0} />
                {analysis?.eligibility_requirements?.length ? (
                  <ul className="detail-list">
                    {analysis.eligibility_requirements.map((item, index) => (
                      <li className="detail-item" key={index}>
                        <span className="list-marker" aria-hidden="true">✓</span>
                        <div><p>{item.text}</p><Source page={item.page_number} quote={item.evidence_quote} /></div>
                      </li>
                    ))}
                  </ul>
                ) : <EmptyList>No eligibility criteria were found in the notice.</EmptyList>}
              </section>

              <section className="panel documents-panel" id="documents">
                <SectionHeading eyebrow="Get ready" title="Your document list" count={requiredDocuments.length} />
                <p className="panel-description">Use this list to keep track as you gather each supporting document.</p>
                {requiredDocuments.length ? (
                  <ul className="checklist">
                    {requiredDocuments.map((item, index) => (
                      <li className={"checklist-item" + (checkedItems[index] ? " is-checked" : "")} key={index}>
                        <label>
                          <input
                            type="checkbox"
                            checked={Boolean(checkedItems[index])}
                            onChange={() => toggleChecklistItem(index)}
                          />
                          <span className="custom-check" aria-hidden="true">✓</span>
                          <span className="checklist-label">{item.text}</span>
                        </label>
                        <Source page={item.page_number} quote={item.evidence_quote} />
                      </li>
                    ))}
                  </ul>
                ) : <EmptyList>The notice did not list supporting documents.</EmptyList>}
                {requiredDocuments.length > 0 && (
                  <p className="checklist-progress">{completedCount} of {requiredDocuments.length} prepared</p>
                )}
              </section>

              <section className="panel deadlines-panel" id="deadlines">
                <SectionHeading eyebrow="Keep in mind" title="Important dates" count={analysis?.deadlines?.length || 0} />
                {analysis?.deadlines?.length ? (
                  <ul className="date-list">
                    {analysis.deadlines.map((item, index) => (
                      <li className="date-item" key={index}>
                        <span className="calendar-icon" aria-hidden="true"><span>{item.normalized_date ? item.normalized_date.slice(5, 7) : "!"}</span><b>{item.normalized_date ? item.normalized_date.slice(8, 10) : "—"}</b></span>
                        <div>
                          <strong>{item.date_text}</strong>
                          {item.normalized_date && <span className="normalized-date">{formatDate(item.normalized_date)}</span>}
                          <Source page={item.page_number} quote={item.evidence_quote} />
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : <EmptyList>No deadline was identified in the notice.</EmptyList>}
              </section>

              <section className="panel steps-panel" id="application-steps">
                <SectionHeading eyebrow="What to do" title="Application steps" count={analysis?.application_steps?.length || 0} />
                {analysis?.application_steps?.length ? (
                  <ol className="steps-list">
                    {analysis.application_steps.map((item, index) => (
                      <li className="step-item" key={index}>
                        <span className="step-number">{String(index + 1).padStart(2, "0")}</span>
                        <div><p>{item.text}</p><Source page={item.page_number} quote={item.evidence_quote} /></div>
                      </li>
                    ))}
                  </ol>
                ) : <EmptyList>No application steps were identified.</EmptyList>}
              </section>
            </div>

            {analysis?.warnings?.length > 0 && (
              <section className="panel warnings-panel">
                <SectionHeading eyebrow="Read carefully" title="Notes from the notice" count={analysis.warnings.length} />
                <ul className="detail-list">
                  {analysis.warnings.map((item, index) => (
                    <li className="detail-item" key={index}>
                      <span className="list-marker warning-marker" aria-hidden="true">!</span>
                      <div><p>{item.text}</p><Source page={item.page_number} quote={item.evidence_quote} /></div>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <section className="question-card" id="questions">
              <div className="question-intro">
                <span className="question-mark" aria-hidden="true">?</span>
                <div>
                  <p className="eyebrow">Still wondering?</p>
                  <h2>Ask about this notice</h2>
                  <p>FomuWise answers from this PDF only and shows the page it used.</p>
                </div>
              </div>
              <form className="question-form" onSubmit={onAsk}>
                <label className="visually-hidden" htmlFor="question-input">Your question</label>
                <input
                  id="question-input"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  minLength={5}
                  maxLength={500}
                  placeholder="e.g. What documents must I attach?"
                  required
                />
                <button className="button button-primary" type="submit" disabled={asking || question.trim().length < 5}>
                  {asking ? <><span className="spinner" /> Looking…</> : <><span className="button-index" aria-hidden="true">Q</span>Ask</>}
                </button>
              </form>
              {answer && (
                <div className={"answer-box" + (!answer.found ? " is-not-found" : "")} aria-live="polite">
                  <span className="answer-status">{answer.found ? "From your notice" : "Not in this notice"}</span>
                  <p>{answer.answer}</p>
                  {answer.sources?.map((source, index) => (
                    <Source key={index} page={source.page_number} quote={source.evidence_quote} />
                  ))}
                </div>
              )}
            </section>

            <div className="disclaimer">
              <span aria-hidden="true">ⓘ</span>
              <p>FomuWise explains the notice; it does not decide eligibility or submit your application. Confirm final requirements with the organisation that issued it.</p>
            </div>
              </div>
            </div>
          </section>
        )}
      </main>

      <footer className="site-footer" id="footer">
        <div className="footer-brand"><span className="footer-mark">F</span><strong>FomuWise</strong><span>Know what to do next.</span></div>
        <div className="footer-caption">Read closely. Apply confidently.</div>
      </footer>
    </div>
  );
}

export default App;
