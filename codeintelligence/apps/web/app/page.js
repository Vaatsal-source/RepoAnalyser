"use client";

import { useState } from "react";
import { ingestRepository, searchCodebase } from "../src/services/codeIntelApi";
import ReactMarkdown from "react-markdown";

export default function Home() {
  // Ingestion State
  const [repoUrl, setRepoUrl] = useState("");
  const [repoId, setRepoId] = useState("");
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestStatus, setIngestStatus] = useState("");

  // Chat State
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! Codebase synced successfully. Ask me anything about your files, architecture, or variable layouts.",
    },
  ]);
  const [userQuery, setUserQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  // Trigger Backend Parsing and Multi-Cloud Storage Sync
  const handleIngest = async (e) => {
    e.preventDefault();
    if (!repoUrl || !repoId) {
      alert("Please fill out both the Repository ID and Git URL targets.");
      return;
    }

    setIsIngesting(true);
    setIngestStatus(
      "🔄 Cloning repository, parsing AST, and distributing cloud contexts...",
    );

    try {
      const data = await ingestRepository(repoUrl, repoId);
      setIngestStatus(
        `✅ Successfully indexed workspace! Managed ${data.files_indexed} source files.`,
      );
    } catch (err) {
      setIngestStatus(`❌ Ingestion broken: ${err.message}`);
    } finally {
      setIsIngesting(false);
    }
  };

  // Trigger Gemini Vector Embed Search and Completion
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!userQuery.trim()) return;

    const currentQuery = userQuery;
    setUserQuery(""); // Reset input layout

    // Append user prompt instantly to chat array
    setMessages((prev) => [...prev, { role: "user", content: currentQuery }]);
    setIsSearching(true);

    try {
      const data = await searchCodebase(currentQuery);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `❌ Network request layer failed to pull context: ${err.message}`,
        },
      ]);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col font-sans">
      {/* HEADER BAR */}
      <header className="border-b border-neutral-800 bg-neutral-900/50 p-4 backdrop-blur">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <h1 className="text-xl font-bold tracking-tight text-emerald-400 font-mono">
            🧠 CodeIntel . Core
          </h1>
          <div className="text-xs text-neutral-400 font-mono">
            System Engine Matrix: Gemini Cloud 2.5
          </div>
        </div>
      </header>

      <div className="max-w-6xl w-full mx-auto p-4 grid grid-cols-1 md:grid-cols-3 gap-6 flex-1 items-stretch">
        {/* LEFT COLUMN: CONTROL & INGESTION BLOCK */}
        <div className="md:col-span-1 flex flex-col gap-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 shadow-lg">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-400 mb-4 font-mono">
              📁 Pipeline Workspace Ingestion
            </h2>
            <form onSubmit={handleIngest} className="flex flex-col gap-3">
              <div>
                <label className="block text-xs text-neutral-500 font-mono mb-1">
                  WORKSPACE REPO ID
                </label>
                <input
                  type="text"
                  value={repoId}
                  onChange={(e) => setRepoId(e.target.value)}
                  placeholder="e.g., custom-app-sync"
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg p-2 text-sm text-neutral-200 focus:outline-none focus:border-emerald-500 transition-colors font-mono"
                />
              </div>
              <div>
                <label className="block text-xs text-neutral-500 font-mono mb-1">
                  GIT TARGET URL
                </label>
                <input
                  type="url"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/..."
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg p-2 text-sm text-neutral-200 focus:outline-none focus:border-emerald-500 transition-colors font-mono"
                />
              </div>
              <button
                type="submit"
                disabled={isIngesting}
                className="w-full mt-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-800 disabled:text-neutral-500 text-neutral-950 text-sm p-2 rounded-lg transition-colors cursor-pointer font-semibold font-mono"
              >
                {isIngesting ? "Processing Matrix..." : "Index Repository"}
              </button>
            </form>

            {ingestStatus && (
              <div className="mt-4 p-3 rounded-lg bg-neutral-950 border border-neutral-800 text-xs font-mono whitespace-pre-wrap leading-relaxed text-neutral-300">
                {ingestStatus}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: INTERACTIVE AGENT CONTEXT CHAT FEED */}
        <div className="md:col-span-2 flex flex-col bg-neutral-900 border border-neutral-800 rounded-xl shadow-lg overflow-hidden h-[75vh]">
          {/* CHAT DISPLAY FEED */}
          <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex flex-col max-w-[85%] rounded-xl p-4 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-emerald-950/40 border border-emerald-800/50 self-end text-neutral-100"
                    : "bg-neutral-950 border border-neutral-800 self-start text-neutral-300"
                }`}
              >
                <span className="text-[10px] font-mono tracking-widest uppercase mb-1 block text-neutral-500">
                  {msg.role === "user" ? "👨‍💻 Developer" : "🤖 CodeIntel Agent"}
                </span>
                <div className="prose prose-invert text-sm max-w-none font-sans space-y-2">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>
            ))}

            {isSearching && (
              <div className="bg-neutral-950 border border-neutral-800 rounded-xl p-4 text-sm self-start text-neutral-500 animate-pulse font-mono max-w-[85%]">
                🤖 Vector-space lookup complete. Synthesizing cross-cluster
                engineering answer...
              </div>
            )}
          </div>

          {/* PROMPT ACTION FOOTER */}
          <form
            onSubmit={handleSendMessage}
            className="p-4 border-t border-neutral-800 bg-neutral-950 flex gap-2"
          >
            <input
              type="text"
              value={userQuery}
              onChange={(e) => setUserQuery(e.target.value)}
              placeholder="Ask a question about the layout structuring, dependencies or styles..."
              className="flex-1 bg-neutral-900 border border-neutral-800 rounded-lg px-4 py-2 text-sm text-neutral-200 focus:outline-none focus:border-emerald-500 transition-colors"
              disabled={isSearching}
            />
            <button
              type="submit"
              disabled={isSearching || !userQuery.trim()}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-800 text-neutral-950 px-4 py-2 rounded-lg text-sm font-semibold transition-colors font-mono cursor-pointer"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}
