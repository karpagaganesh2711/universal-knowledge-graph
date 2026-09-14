import { useCallback, useRef, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";

import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const SUPPORTED_EXTENSIONS = ["pdf", "docx", "txt"];

function App() {
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [intelligence, setIntelligence] = useState(null);

  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);

  const [error, setError] = useState("");
  const [selectedNode, setSelectedNode] = useState(null);

  const [graphFilter, setGraphFilter] = useState("all");

  const handleFile = useCallback((selectedFile) => {
    if (!selectedFile) return;

    const extension = selectedFile.name
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
    setIntelligence(null);
    setSelectedNode(null);
    setGraphFilter("all");
    setError("");
  }, []);

  const handleFileInput = (event) => {
    handleFile(event.target.files?.[0]);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    handleFile(event.dataTransfer.files?.[0]);
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
    setIntelligence(null);
    setSelectedNode(null);
    setGraphFilter("all");
    setError("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const fetchIntelligence = async () => {
    const [
      statsResponse,
      nodesResponse,
      relationshipsResponse,
    ] = await Promise.all([
      fetch(`${API_URL}/graph/stats`),
      fetch(`${API_URL}/graph/important-nodes?limit=5`),
      fetch(`${API_URL}/graph/strongest-relationships?limit=5`),
    ]);

    if (
      !statsResponse.ok ||
      !nodesResponse.ok ||
      !relationshipsResponse.ok
    ) {
      throw new Error(
        "Graph intelligence API returned an invalid response."
      );
    }

    const [
      stats,
      importantNodes,
      strongestRelationships,
    ] = await Promise.all([
      statsResponse.json(),
      nodesResponse.json(),
      relationshipsResponse.json(),
    ]);

    return {
      stats,
      importantNodes: importantNodes.nodes || [],
      strongestRelationships:
        strongestRelationships.relationships || [],
    };
  };

  const analyzeDocument = async () => {
    if (!file || loading) return;

    setLoading(true);
    setError("");
    setAnalysis(null);
    setIntelligence(null);
    setSelectedNode(null);
    setGraphFilter("all");

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
          data.detail || "Document analysis failed."
        );
      }

      if (!data.graph) {
        throw new Error(
          "Backend response does not contain a knowledge graph."
        );
      }

      setAnalysis(data);

      try {
        const graphIntelligence =
          await fetchIntelligence();

        setIntelligence(graphIntelligence);
      } catch (intelligenceError) {
        console.error(
          "Graph intelligence unavailable:",
          intelligenceError
        );

        setIntelligence({
          stats: {
            node_count: data.graph.node_count,
            relationship_count:
              data.graph.relationship_count,
            semantic_relationship_count:
              data.graph.semantic_relationship_count,
            average_relationship_confidence:
              data.graph.average_relationship_confidence,
            average_relationship_score:
              data.graph.average_relationship_score,
          },
          importantNodes:
            data.graph.most_important_nodes || [],
          strongestRelationships: [],
        });
      }
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

  const allNodes = analysis?.graph?.nodes || [];
  const allRelationships =
    analysis?.graph?.relationships || [];

  /*
   * GRAPH FILTERING
   *
   * ALL       → every extracted node
   * CONNECTED → nodes participating in relationships
   * IMPORTANT → nodes with meaningful importance
   */

  const rankedImportantNodes =
  intelligence?.importantNodes ||
  analysis?.graph?.most_important_nodes ||
  [];

const importantNodeIds = new Set(
  rankedImportantNodes
    .slice(0, 10)
    .map((node) => node.id)
);

  const visibleNodes = allNodes.filter((node) => {
    const degree = node.degree ?? 0;
    const importance = node.importance ?? 0;

    if (graphFilter === "connected") {
      return degree > 0;
    }

    if (graphFilter === "important") {
  return importantNodeIds.has(node.id);
}

    return true;
  });

  const visibleNodeIds = new Set(
    visibleNodes.map((node) => node.id)
  );

  const visibleRelationships = allRelationships.filter(
    (relationship) =>
      visibleNodeIds.has(relationship.source) &&
      visibleNodeIds.has(relationship.target)
  );

  const graphElements = [
    ...visibleNodes.map((node) => ({
      data: {
        id: node.id,
        label: node.label,
        type: node.type,
        description: node.description,
        aliases: node.aliases || [],
        degree: node.degree ?? 0,
        importance: node.importance ?? 0,
      },
    })),

    ...visibleRelationships.map(
      (relationship, index) => ({
        data: {
          id: `relationship-${index}`,
          source: relationship.source,
          target: relationship.target,
          label: relationship.relationship,
          confidence:
            relationship.confidence ?? 0,
          score: relationship.score ?? 0,
        },
      })
    ),
  ];

  const graphStyle = [
    {
      selector: "node",

      style: {
        "background-color": "#11161c",
        "border-color": "#ff3b30",
        "border-width": 2,

        /*
         * Node size is controlled by importance.
         * More important concepts become visually larger.
         */
        width: "mapData(importance, 0, 0.25, 32, 72)",
        height: "mapData(importance, 0, 0.25, 32, 72)",

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

        width: 64,
        height: 64,

        "font-size": 12,
      },
    },

    {
      selector: "edge",

      style: {
        /*
         * Stronger relationships become thicker.
         */
        width: "mapData(score, 0, 1, 1, 4)",

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

    nodeRepulsion: 9500,
    idealEdgeLength: 155,

    edgeElasticity: 100,

    gravity: 0.22,

    numIter: 1200,

    padding: 70,
  };

  const stats = intelligence?.stats || analysis?.graph;

  const importantNodes =
    intelligence?.importantNodes ||
    analysis?.graph?.most_important_nodes ||
    [];

  const strongestRelationships =
    intelligence?.strongestRelationships || [];

  return (
    <div className="app-shell">
      <div className="grid-overlay" />
      <div className="scan-line" />

      <header className="topbar">
        <div className="brand-block">
          <div className="brand">K-GRAPH</div>

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

            <div className="upload-icon">↑</div>

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

              <h2>{analysis.filename}</h2>
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
                  <strong>{analysis.words}</strong>
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
                  GRAPH INTELLIGENCE
                </div>

                <div className="metric">
                  <span>CONFIDENCE</span>

                  <strong>
                    {stats
                      ? `${Math.round(
                          stats.average_relationship_confidence *
                            100
                        )}%`
                      : "--"}
                  </strong>
                </div>

                <div className="metric">
                  <span>GRAPH SCORE</span>

                  <strong>
                    {stats
                      ? stats.average_relationship_score.toFixed(
                          3
                        )
                      : "--"}
                  </strong>
                </div>

                <div className="metric">
                  <span>SEMANTIC EDGES</span>

                  <strong>
                    {stats?.semantic_relationship_count ??
                      "--"}
                  </strong>
                </div>
              </div>

              <div className="panel intelligence-panel">
                <div className="panel-title">
                  TOP CONCEPTS
                </div>

                {importantNodes.length > 0 ? (
                  <div className="intelligence-list">
                    {importantNodes.map(
                      (node, index) => (
                        <div
                          className="intelligence-row"
                          key={node.id}
                        >
                          <span className="rank">
                            {String(index + 1).padStart(
                              2,
                              "0"
                            )}
                          </span>

                          <span className="intelligence-name">
                            {node.id}
                          </span>

                          <strong>
                            {Number(
                              node.importance || 0
                            ).toFixed(3)}
                          </strong>
                        </div>
                      )
                    )}
                  </div>
                ) : (
                  <div className="intelligence-empty">
                    NO INTELLIGENCE DATA
                  </div>
                )}
              </div>

              {selectedNode && (
                <div className="panel selected-panel">
                  <div className="panel-title">
                    SELECTED NODE
                  </div>

                  <h3>{selectedNode.label}</h3>

                  <span className="node-type">
                    {selectedNode.type}
                  </span>

                  <div className="selected-node-stats">
                    <div>
                      <span>DEGREE</span>

                      <strong>
                        {selectedNode.degree ?? 0}
                      </strong>
                    </div>

                    <div>
                      <span>IMPORTANCE</span>

                      <strong>
                        {Number(
                          selectedNode.importance || 0
                        ).toFixed(3)}
                      </strong>
                    </div>
                  </div>

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
                    Select any node in the graph to inspect
                    its semantic information.
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
                  {visibleRelationships.length} /{" "}
                  {analysis.graph.relationship_count} EDGES
                </span>
              </div>

              <div className="graph-controls">
                <span className="graph-control-label">
                  VIEW
                </span>

                <button
                  type="button"
                  className={
                    graphFilter === "all"
                      ? "graph-filter active"
                      : "graph-filter"
                  }
                  onClick={() =>
                    setGraphFilter("all")
                  }
                >
                  ALL NODES
                </button>

                <button
                  type="button"
                  className={
                    graphFilter === "connected"
                      ? "graph-filter active"
                      : "graph-filter"
                  }
                  onClick={() =>
                    setGraphFilter("connected")
                  }
                >
                  CONNECTED
                </button>

                <button
                  type="button"
                  className={
                    graphFilter === "important"
                      ? "graph-filter active"
                      : "graph-filter"
                  }
                  onClick={() =>
                    setGraphFilter("important")
                  }
                >
                  IMPORTANT
                </button>

                <span className="graph-count">
                  {visibleNodes.length} NODES
                </span>
              </div>

              <div className="graph-container">
                {graphElements.length > 0 ? (
                  <CytoscapeComponent
  key={`${graphFilter}-${visibleNodes.length}-${visibleRelationships.length}`}
  elements={graphElements}
                    stylesheet={graphStyle}
                    layout={graphLayout}
                    style={{
                      width: "100%",
                      height: "100%",
                    }}
                    cy={(cy) => {
                      cy.removeAllListeners("tap");

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

              {strongestRelationships.length > 0 && (
                <div className="strongest-panel">
                  <div className="panel-title">
                    STRONGEST RELATIONSHIPS
                  </div>

                  <div className="relationship-list">
                    {strongestRelationships.map(
                      (relationship, index) => (
                        <div
                          className="relationship-row"
                          key={`${relationship.source}-${relationship.target}-${index}`}
                        >
                          <span className="relationship-source">
                            {relationship.source}
                          </span>

                          <span className="relationship-arrow">
                            →
                          </span>

                          <span className="relationship-type">
                            {relationship.relationship}
                          </span>

                          <span className="relationship-arrow">
                            →
                          </span>

                          <span className="relationship-target">
                            {relationship.target}
                          </span>

                          <strong>
                            {Number(
                              relationship.score || 0
                            ).toFixed(3)}
                          </strong>
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}
            </section>
          </section>
        </main>
      )}

      <footer>
        K-GRAPH&nbsp;&nbsp;/&nbsp;&nbsp;
        DOCUMENT → CONCEPT → RELATIONSHIP → KNOWLEDGE
      </footer>
    </div>
  );
}

export default App;
