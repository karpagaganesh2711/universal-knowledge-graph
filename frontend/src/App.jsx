import { useCallback, useRef, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";

import "./App.css";


const API_URL = "http://127.0.0.1:8000";

const SUPPORTED_EXTENSIONS = [
  "pdf",
  "docx",
  "txt",
];


function App() {
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);

  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);

  const [error, setError] = useState("");
  const [selectedNode, setSelectedNode] = useState(null);


  const handleFile = useCallback((selectedFile) => {
    if (!selectedFile) {
      return;
    }

    const fileName = selectedFile.name || "";
    const extension = fileName
      .split(".")
      .pop()
      .toLowerCase();

    if (!SUPPORTED_EXTENSIONS.includes(extension)) {
      setError(
        "Unsupported file type. Please upload PDF, DOCX, or TXT."
      );

      return;
    }

    setFile(selectedFile);
    setAnalysis(null);
    setSelectedNode(null);
    setError("");
  }, []);


  const handleFileInput = (event) => {
    const selectedFile = event.target.files?.[0];

    handleFile(selectedFile);
  };


  const handleDrop = (event) => {
    event.preventDefault();

    setDragging(false);

    const droppedFile = event.dataTransfer.files?.[0];

    handleFile(droppedFile);
  };


  const handleDragOver = (event) => {
    event.preventDefault();

    setDragging(true);
  };


  const handleDragLeave = () => {
    setDragging(false);
  };


  const openFilePicker = () => {
    fileInputRef.current?.click();
  };


  const removeFile = () => {
    setFile(null);
    setAnalysis(null);
    setSelectedNode(null);
    setError("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };


  const analyzeDocument = async () => {
    if (!file || loading) {
      return;
    }

    setLoading(true);
    setError("");
    setAnalysis(null);
    setSelectedNode(null);

    const formData = new FormData();

    formData.append("file", file);


    try {
      const response = await fetch(
        `${API_URL}/documents/analyze`,
        {
          method: "POST",
          body: formData,
        }
      );


      let data;

      try {
        data = await response.json();
      } catch {
        throw new Error(
          "Backend returned an invalid response."
        );
      }


      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Document analysis failed."
        );
      }


      if (!data.graph) {
        throw new Error(
          "Backend response does not contain a knowledge graph."
        );
      }


      setAnalysis(data);

    } catch (requestError) {
      console.error(requestError);

      setError(
        requestError.message ||
        "Unable to connect to the backend."
      );

    } finally {
      setLoading(false);
    }
  };


  const graphElements = analysis
    ? [
        ...analysis.graph.nodes.map((node) => ({
          data: {
            id: node.id,
            label: node.label,
            type: node.type,
            description: node.description,
          },
        })),

        ...analysis.graph.relationships.map(
          (relationship, index) => ({
            data: {
              id: `relationship-${index}`,
              source: relationship.source,
              target: relationship.target,
              label: relationship.relationship,
            },
          })
        ),
      ]
    : [];


  const graphStyle = [
    {
      selector: "node",

      style: {
        "background-color": "#11161c",
        "border-color": "#ff3b30",
        "border-width": 2,

        width: 46,
        height: 46,

        label: "data(label)",

        color: "#f5f5f5",

        "font-family": "Rajdhani, sans-serif",
        "font-size": 11,
        "font-weight": 600,

        "text-wrap": "wrap",
        "text-max-width": 120,

        "text-valign": "bottom",
        "text-halign": "center",

        "text-margin-y": 9,

        "text-outline-color": "#07090c",
        "text-outline-width": 4,

        "overlay-opacity": 0,
      },
    },


    {
      selector: 'node[type = "ORG"]',

      style: {
        "background-color": "#681c1a",
        "border-color": "#ff4d43",

        shape: "roundrectangle",

        width: 54,
        height: 42,
      },
    },


    {
      selector: 'node[type = "CONCEPT"]',

      style: {
        "background-color": "#121a22",
        "border-color": "#ff9f43",

        shape: "ellipse",
      },
    },


    {
      selector: "node:selected",

      style: {
        "background-color": "#e83229",
        "border-color": "#ffffff",

        "border-width": 3,

        width: 58,
        height: 58,

        "font-size": 12,
      },
    },


    {
      selector: "edge",

      style: {
        width: 1.5,

        "line-color": "#8d302c",

        "target-arrow-color": "#ff493f",
        "target-arrow-shape": "triangle",

        "curve-style": "bezier",

        label: "data(label)",

        color: "#ffb09c",

        "font-family": "Rajdhani, sans-serif",
        "font-size": 10,
        "font-weight": 600,

        "text-background-color": "#07090c",
        "text-background-opacity": 0.95,
        "text-background-padding": 4,

        "text-rotation": "autorotate",
      },
    },
  ];


  const graphLayout = {
    name: "cose",

    animate: true,
    animationDuration: 700,

    nodeRepulsion: 8500,
    idealEdgeLength: 145,

    edgeElasticity: 100,

    gravity: 0.25,

    numIter: 1000,

    padding: 70,
  };


  return (
    <div className="app-shell">

      <div className="grid-overlay" />
      <div className="scan-line" />


      <header className="topbar">

        <div className="brand-block">

          <div className="brand">
            K-GRAPH
          </div>

          <div className="subtitle">
            UNIVERSAL KNOWLEDGE INTELLIGENCE SYSTEM
          </div>

        </div>


        <div className="system-status">

          <span className="status-dot" />

          SYSTEM ONLINE

        </div>

      </header>


      {!analysis && (
        <main className="landing">

          <section className="hero">

            <div className="hero-kicker">
              DOCUMENT INTELLIGENCE ENGINE
            </div>


            <h1>
              Turn information
              <br />
              <span>into connections.</span>
            </h1>


            <p>
              Transform documents into concepts,
              entities and semantic relationships
              using an intelligent knowledge graph engine.
            </p>

          </section>


          <section
            className={`drop-zone ${
              dragging ? "dragging" : ""
            }`}

            onClick={openFilePicker}

            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >

            <input
              ref={fileInputRef}

              type="file"

              accept=".pdf,.docx,.txt"

              hidden

              onChange={handleFileInput}
            />


            <div className="upload-icon">
              ↑
            </div>


            <div className="drop-title">
              DROP DOCUMENT HERE
            </div>


            <div className="drop-description">
              or click to browse your system
            </div>


            <div className="supported">
              PDF&nbsp;&nbsp;•&nbsp;&nbsp;
              DOCX&nbsp;&nbsp;•&nbsp;&nbsp;
              TXT
            </div>

          </section>


          {file && (
            <section className="selected-file">

              <div className="selected-file-info">

                <div className="file-label">
                  SELECTED DOCUMENT
                </div>

                <div className="file-name">
                  {file.name}
                </div>

              </div>


              <button
                type="button"
                className="remove-button"

                onClick={(event) => {
                  event.stopPropagation();
                  removeFile();
                }}
              >
                REMOVE
              </button>

            </section>
          )}


          {file && (
            <button
              type="button"

              className="analyze-button"

              disabled={loading}

              onClick={analyzeDocument}
            >

              {loading
                ? "ANALYZING DOCUMENT..."
                : "INITIATE ANALYSIS"}

            </button>
          )}


          {error && (
            <div className="error-box">
              <strong>ERROR</strong>
              <span>{error}</span>
            </div>
          )}

        </main>
      )}


      {analysis && (
        <main className="workspace">

          <section className="workspace-header">

            <div>

              <div className="workspace-kicker">
                KNOWLEDGE GRAPH GENERATED
              </div>

              <h2>
                {analysis.filename}
              </h2>

            </div>


            <button
              type="button"

              className="new-document"

              onClick={removeFile}
            >
              NEW DOCUMENT
            </button>

          </section>


          <section className="dashboard">

            <aside className="sidebar">


              <div className="panel">

                <div className="panel-title">
                  ANALYSIS
                </div>


                <div className="metric">
                  <span>WORDS</span>

                  <strong>
                    {analysis.words}
                  </strong>
                </div>


                <div className="metric">
                  <span>SENTENCES</span>

                  <strong>
                    {analysis.sentence_count}
                  </strong>
                </div>


                <div className="metric">
                  <span>NODES</span>

                  <strong>
                    {analysis.graph.node_count}
                  </strong>
                </div>


                <div className="metric">
                  <span>RELATIONSHIPS</span>

                  <strong>
                    {analysis.graph.relationship_count}
                  </strong>
                </div>

              </div>


              <div className="panel">

                <div className="panel-title">
                  DOCUMENT
                </div>


                <div className="document-info">
                  <span>TYPE</span>

                  <strong>
                    {analysis.file_type}
                  </strong>
                </div>


                <div className="document-info">
                  <span>CHARACTERS</span>

                  <strong>
                    {analysis.characters}
                  </strong>
                </div>


                <div className="document-info">
                  <span>STATUS</span>

                  <strong className="online">
                    GRAPH READY
                  </strong>
                </div>

              </div>


              {selectedNode && (
                <div className="panel selected-panel">

                  <div className="panel-title">
                    SELECTED NODE
                  </div>


                  <h3>
                    {selectedNode.label}
                  </h3>


                  <span className="node-type">
                    {selectedNode.type}
                  </span>


                  <p>
                    {selectedNode.description ||
                      "Knowledge graph concept."}
                  </p>

                </div>
              )}


              {!selectedNode && (
                <div className="panel instruction-panel">

                  <div className="panel-title">
                    GRAPH INTERACTION
                  </div>

                  <p>
                    Select any node in the graph
                    to inspect its semantic information.
                  </p>

                </div>
              )}

            </aside>


            <section className="graph-panel">

              <div className="graph-header">

                <span>
                  SEMANTIC RELATIONSHIP MAP
                </span>


                <span>
                  {
                    analysis.graph.semantic_relationship_count
                  }
                  {" "}
                  SEMANTIC EDGES
                </span>

              </div>


              <div className="graph-container">

                {graphElements.length > 0 ? (

                  <CytoscapeComponent

                    elements={graphElements}

                    stylesheet={graphStyle}

                    layout={graphLayout}

                    style={{
                      width: "100%",
                      height: "100%",
                    }}

                    cy={(cy) => {

                      cy.removeAllListeners(
                        "tap"
                      );


                      cy.on(
                        "tap",
                        "node",
                        (event) => {

                          const node =
                            event.target.data();

                          setSelectedNode(node);
                        }
                      );

                    }}

                  />

                ) : (

                  <div className="empty-graph">
                    NO GRAPH DATA AVAILABLE
                  </div>

                )}

              </div>

            </section>

          </section>

        </main>
      )}


      <footer>
        K-GRAPH&nbsp;&nbsp;/&nbsp;&nbsp;
        DOCUMENT
        →
        CONCEPT
        →
        RELATIONSHIP
        →
        KNOWLEDGE
      </footer>

    </div>
  );
}


export default App;