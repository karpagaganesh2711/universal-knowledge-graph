import { useState } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = (selectedFile) => {
    if (!selectedFile) return;

    const allowedTypes = [
      "application/pdf",
      "text/plain",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];

    if (!allowedTypes.includes(selectedFile.type)) {
      alert("Please upload a PDF, DOCX, or TXT file.");
      return;
    }

    setFile(selectedFile);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);

    const droppedFile = event.dataTransfer.files[0];
    handleFile(droppedFile);
  };

  const handleFileInput = (event) => {
    const selectedFile = event.target.files[0];
    handleFile(selectedFile);
  };

  const removeFile = () => {
    setFile(null);
  };

  return (
    <div className="app">
      {/* HUD Background */}
      <div className="grid-background"></div>
      <div className="scan-line"></div>

      {/* Header */}
      <header className="top-bar">
        <div className="brand">
          <div className="brand-symbol">◈</div>

          <div>
            <div className="brand-name">K-GRAPH</div>
            <div className="brand-subtitle">
              KNOWLEDGE INTELLIGENCE SYSTEM
            </div>
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot"></span>
          SYSTEM ONLINE
        </div>
      </header>

      {/* Main */}
      <main className="main-content">
        <section className="hero-section">
          <div className="system-label">
            <span></span>
            INTELLIGENCE CORE / INITIALIZATION
          </div>

          <h1>
            Turn information
            <br />
            into <span>connections.</span>
          </h1>

          <p className="hero-description">
            Upload your information and let the system discover
            entities, concepts, and relationships hidden inside it.
          </p>

          {/* Upload Zone */}
          <div
            className={`upload-zone ${isDragging ? "dragging" : ""}`}
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            {!file ? (
              <>
                <div className="upload-icon">◇</div>

                <h2>UPLOAD DATA</h2>

                <p>
                  Drop your document here
                  <br />
                  or select a file from your system
                </p>

                <label className="upload-button">
                  SELECT DOCUMENT
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={handleFileInput}
                    hidden
                  />
                </label>

                <div className="supported-files">
                  PDF&nbsp;&nbsp; / &nbsp;&nbsp;DOCX&nbsp;&nbsp; / &nbsp;&nbsp;TXT
                </div>
              </>
            ) : (
              <div className="file-selected">
                <div className="file-icon">▣</div>

                <div className="file-information">
                  <div className="file-name">{file.name}</div>

                  <div className="file-size">
                    {(file.size / 1024).toFixed(1)} KB
                  </div>
                </div>

                <button
                  className="remove-button"
                  onClick={removeFile}
                  type="button"
                >
                  REMOVE
                </button>
              </div>
            )}
          </div>

          {/* Future Processing Button */}
          <button
            className={`analyze-button ${file ? "active" : ""}`}
            disabled={!file}
          >
            <span>INITIATE ANALYSIS</span>
            <span className="arrow">→</span>
          </button>
        </section>

        {/* System Information */}
        <section className="system-panel">
          <div className="panel-item">
            <span className="panel-label">ENGINE</span>
            <span className="panel-value">K-GRAPH CORE</span>
          </div>

          <div className="panel-item">
            <span className="panel-label">NODES</span>
            <span className="panel-value">000</span>
          </div>

          <div className="panel-item">
            <span className="panel-label">RELATIONSHIPS</span>
            <span className="panel-value">000</span>
          </div>

          <div className="panel-item">
            <span className="panel-label">STATUS</span>
            <span className="panel-value online">READY</span>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="footer">
        <span>K-GRAPH // KNOWLEDGE INTELLIGENCE</span>

        <span>LOCAL PROCESSING SYSTEM</span>

        <span>v0.1.0</span>
      </footer>
    </div>
  );
}

export default App;