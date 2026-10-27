import { useState, useRef, useEffect } from 'react';
import { apiClient, API_BASE_URL, type Message, type ChatSession } from './api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface AttachedDoc {
  filename: string;
  chunks_count?: number;
}

export default function App() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  
  // Pending document attached in the input composer before sending
  const [attachedDoc, setAttachedDoc] = useState<AttachedDoc | null>(null);
  // Active document indexed in the current session
  const [sessionDoc, setSessionDoc] = useState<AttachedDoc | null>(null);
  
  // Title Editing State
  const [editingSessionId, setEditingSessionId] = useState<number | null>(null);
  const [editTitleText, setEditTitleText] = useState('');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { 
    fetchSessions(); 
  }, []);

  // Synchronize messages and session document when switching sessions
  useEffect(() => {
    if (activeSessionId && !isLoading) {
      fetchMessages(activeSessionId);
      fetchSessionDocuments(activeSessionId);
    } else if (!activeSessionId) {
      setMessages([]);
      setSessionDoc(null);
      setAttachedDoc(null);
    }
  }, [activeSessionId, isLoading]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchSessions = async () => {
    try {
      const res = await apiClient.get('/sessions/');
      setSessions(res.data);
      if (res.data.length > 0 && !activeSessionId) {
        setActiveSessionId(res.data[0].id);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  const fetchMessages = async (sessionId: number) => {
    try {
      const res = await apiClient.get(`/sessions/${sessionId}/messages`);
      setMessages(res.data);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const fetchSessionDocuments = async (sessionId: number) => {
    try {
      const res = await apiClient.get(`/sessions/${sessionId}/documents`);
      if (res.data && res.data.length > 0) {
        setSessionDoc(res.data[0]);
      } else {
        setSessionDoc(null);
      }
    } catch (error) {
      setSessionDoc(null);
    }
  };

  const handleNewChat = async () => {
    try {
      const res = await apiClient.post('/sessions/?title=New Chat');
      setSessions([res.data, ...sessions]);
      setActiveSessionId(res.data.id);
      setMessages([]);
      setAttachedDoc(null);
      setSessionDoc(null);
      if (window.innerWidth < 768) setIsSidebarOpen(false);
      textInputRef.current?.focus();
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: number) => {
    e.stopPropagation();
    try {
      await apiClient.delete(`/sessions/${sessionId}`);
      const remainingSessions = sessions.filter(s => s.id !== sessionId);
      setSessions(remainingSessions);
      if (activeSessionId === sessionId) {
        if (remainingSessions.length > 0) {
          setActiveSessionId(remainingSessions[0].id);
        } else {
          setActiveSessionId(null);
          setMessages([]);
          setAttachedDoc(null);
          setSessionDoc(null);
        }
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const submitRename = async (sessionId: number) => {
    if (!editTitleText.trim()) {
      setEditingSessionId(null);
      return;
    }
    try {
      await apiClient.put(`/sessions/${sessionId}?title=${encodeURIComponent(editTitleText.trim())}`);
      setSessions(sessions.map(s => s.id === sessionId ? { ...s, title: editTitleText.trim() } : s));
    } catch (error) {
      console.error('Failed to rename session:', error);
    } finally {
      setEditingSessionId(null);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    let currentSessionId = activeSessionId;

    try {
      setIsUploading(true);
      if (!currentSessionId) {
        const cleanName = file.name.replace(/\.[^/.]+$/, "");
        const sessionRes = await apiClient.post(`/sessions/?title=Doc: ${encodeURIComponent(cleanName.slice(0, 24))}`);
        currentSessionId = sessionRes.data.id;
        setActiveSessionId(currentSessionId);
        setSessions(prev => [sessionRes.data, ...prev]);
      }

      const formData = new FormData();
      formData.append('file', file);

      const uploadRes = await apiClient.post(`/sessions/${currentSessionId}/upload`, formData);
      const chunksCount = uploadRes.data?.chunks_count;

      // Pin the attached document in the composer input box ready to be sent
      const docInfo = { filename: file.name, chunks_count: chunksCount };
      setAttachedDoc(docInfo);
      setSessionDoc(docInfo);
      fetchSessions();
      textInputRef.current?.focus();
    } catch (error: any) {
      console.error('Upload Error:', error);
      const errorMsg = error.response?.data?.detail || 'Ensure it is a valid PDF with extractable text.';
      alert(`Error uploading ${file.name}: ${errorMsg}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRemoveAttachment = () => {
    setAttachedDoc(null);
  };

  const executePrompt = async (promptText: string) => {
    if (!promptText.trim() || isLoading) return;

    const userText = promptText.trim();
    const docToSend = attachedDoc?.filename;
    setInput('');
    let currentSessionId = activeSessionId;

    try {
      if (!currentSessionId) {
        const sessionRes = await apiClient.post('/sessions/?title=New Chat');
        currentSessionId = sessionRes.data.id;
        setActiveSessionId(currentSessionId);
        setSessions(prev => [sessionRes.data, ...prev]);
      }

      // Attach file to message and clear from input composer (ChatGPT & Claude behavior)
      const tempUserMsg: Message = { role: 'user', content: userText, file_name: docToSend };
      setMessages((prev) => [...prev, tempUserMsg]);
      setIsLoading(true);
      setAttachedDoc(null); // Document moves into the sent message bubble!
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      const res = await fetch(`${API_BASE_URL}/sessions/${currentSessionId}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content: userText, file_name: docToSend })
      });

      if (!res.body) throw new Error('No response body received.');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let streamedContent = '';
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split(/\r?\n\r?\n/);
        
        buffer = parts.pop() || '';

        for (const part of parts) {
          const trimmed = part.trim();
          if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.slice(6);
            try {
              const token = JSON.parse(dataStr);
              streamedContent += token;
              setMessages((prev) => {
                const newMsgs = [...prev];
                newMsgs[newMsgs.length - 1] = { role: 'assistant', content: streamedContent };
                return newMsgs;
              });
            } catch (e) {
              console.error('SSE Parsing Error:', e);
            }
          }
        }
      }
      fetchSessions(); 
      if (currentSessionId) fetchSessionDocuments(currentSessionId);
    } catch (error) {
      console.error('Streaming Error:', error);
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Error: Unable to stream response.' }]);
    } finally {
      setIsLoading(false);
      textInputRef.current?.focus();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executePrompt(input);
  };

  return (
    <div className="flex h-screen bg-white font-sans text-gray-900">
      {isSidebarOpen && <div className="fixed inset-0 bg-black/20 z-10 md:hidden" onClick={() => setIsSidebarOpen(false)} />}

      {/* Sidebar */}
      <aside className={`fixed md:static inset-y-0 left-0 z-20 w-64 bg-gray-50 border-r border-gray-200 flex flex-col transform transition-transform duration-200 ease-in-out ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <div className="p-4 flex items-center justify-between border-b border-gray-100">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-lg bg-black text-white flex items-center justify-center font-bold text-xs">⚡</span>
            <span className="font-semibold text-gray-800">ChatNexus</span>
          </div>
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden text-gray-500 hover:text-gray-800">✕</button>
        </div>
        
        <div className="px-3 py-3">
          <button onClick={handleNewChat} className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-white border border-gray-200 shadow-xs rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-100/80 transition-colors">
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 space-y-1">
          {sessions.map(session => (
            <div key={session.id} className={`group flex items-center justify-between w-full px-3 py-2 rounded-xl text-sm transition-colors ${activeSessionId === session.id ? 'bg-gray-200/80 text-gray-900 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}>
              
              {editingSessionId === session.id ? (
                <input
                  autoFocus
                  value={editTitleText}
                  onChange={(e) => setEditTitleText(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') submitRename(session.id); else if (e.key === 'Escape') setEditingSessionId(null); }}
                  onBlur={() => submitRename(session.id)}
                  className="w-full bg-white border border-gray-300 rounded px-1.5 py-0.5 outline-none text-gray-900 text-sm"
                />
              ) : (
                <span 
                  className="truncate pr-2 cursor-pointer flex-1"
                  onClick={() => { setActiveSessionId(session.id); if (window.innerWidth < 768) setIsSidebarOpen(false); }}
                  onDoubleClick={() => { setEditingSessionId(session.id); setEditTitleText(session.title); }}
                  title="Double-click to rename"
                >
                  {session.title || "New Chat"}
                </span>
              )}

              {!editingSessionId && (
                <button onClick={(e) => handleDeleteSession(e, session.id)} className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-600 transition-opacity p-1" title="Delete chat">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                </button>
              )}
            </div>
          ))}
        </div>
      </aside>

      {/* Main Chat View */}
      <main className="flex-1 flex flex-col min-w-0 relative bg-white">
        {/* Top Header Bar */}
        <header className="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-gray-100 bg-white">
          <div className="flex items-center gap-3">
            <button onClick={() => setIsSidebarOpen(true)} className="md:hidden text-gray-500 hover:text-gray-800">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
            </button>
            <span className="font-semibold text-gray-800 text-sm">
              {sessions.find(s => s.id === activeSessionId)?.title || "ChatNexus"}
            </span>
          </div>

          {/* Active Session Context Badge */}
          {sessionDoc && (
            <div className="flex items-center gap-1.5 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg text-xs text-emerald-800 shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-medium truncate max-w-[200px]" title={sessionDoc.filename}>{sessionDoc.filename}</span>
              <span className="text-[10px] text-emerald-600 bg-emerald-100/60 px-1.5 py-0.2 rounded">active</span>
            </div>
          )}
        </header>

        {/* Message Log */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 scroll-smooth">
          <div className="max-w-3xl mx-auto space-y-6">
            
            {/* Empty State */}
            {messages.length === 0 && !isLoading && (
              <div className="h-[60vh] flex flex-col items-center justify-center text-center px-4 space-y-5">
                <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center text-2xl shadow-xs">
                  {attachedDoc || sessionDoc ? "📄" : "⚡"}
                </div>
                
                {attachedDoc || sessionDoc ? (
                  <div className="space-y-3 max-w-lg">
                    <h2 className="text-lg font-semibold text-gray-800">
                      {(attachedDoc || sessionDoc)?.filename}
                    </h2>
                    <p className="text-sm text-gray-500">
                      Document uploaded & indexed into pgvector. Ask any question below with 100% fidelity and zero hallucinations.
                    </p>

                    {/* Quick suggested prompt buttons */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 text-left">
                      <button
                        onClick={() => executePrompt("Summarize this document thoroughly, highlighting key objectives, scope, and findings.")}
                        className="p-2.5 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl text-xs text-gray-700 transition-colors"
                      >
                        📋 Comprehensive Summary
                      </button>
                      <button
                        onClick={() => executePrompt("What are the key technical specifications, architecture, and requirements?")}
                        className="p-2.5 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl text-xs text-gray-700 transition-colors"
                      >
                        🛠️ Technical Specs & Architecture
                      </button>
                      <button
                        onClick={() => executePrompt("List all team members, authors, stakeholders, or organizations mentioned.")}
                        className="p-2.5 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl text-xs text-gray-700 transition-colors"
                      >
                        👥 Authors & Stakeholders
                      </button>
                      <button
                        onClick={() => executePrompt("What are the deliverables, timelines, milestones, or conclusions in this document?")}
                        className="p-2.5 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl text-xs text-gray-700 transition-colors"
                      >
                        🎯 Deliverables & Timeline
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <h2 className="text-lg font-semibold text-gray-800">ChatNexus AI Assistant</h2>
                    <p className="text-sm text-gray-500 max-w-md">
                      Ask any question, or click the paperclip icon below to upload a resume or PDF for grounded document analysis.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Messages */}
            {messages.map((msg, idx) => (
              <div key={msg.id || idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[90%] sm:max-w-[85%] px-5 py-3.5 rounded-2xl ${msg.role === 'user' ? 'bg-gray-100 text-gray-900 rounded-br-sm' : 'bg-transparent text-gray-800'}`}>
                  {msg.role === 'user' ? (
                    <div>
                      {/* Attached Document Card in Message Bubble (ChatGPT / Claude style) */}
                      {msg.file_name && (
                        <div className="inline-flex items-center gap-2 bg-white border border-gray-200 px-3 py-1.5 rounded-xl text-xs font-medium text-gray-800 mb-2 shadow-2xs">
                          <span className="w-5 h-5 rounded bg-red-50 text-red-600 flex items-center justify-center font-bold text-[9px]">PDF</span>
                          <span className="truncate max-w-[240px]" title={msg.file_name}>{msg.file_name}</span>
                        </div>
                      )}
                      <p className="whitespace-pre-wrap leading-relaxed text-[15px]">{msg.content}</p>
                    </div>
                  ) : (
                    <div className="prose prose-sm max-w-none text-[15px] leading-relaxed">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          code({ node, inline, className, children, ...props }: any) {
                            const match = /language-(\w+)/.exec(className || '');
                            return !inline && match ? (
                              <SyntaxHighlighter style={vscDarkPlus as any} language={match[1]} PreTag="div" {...props}>
                                {String(children).replace(/\n$/, '')}
                              </SyntaxHighlighter>
                            ) : (
                              <code className={`${className} bg-gray-100 px-1 py-0.5 rounded text-red-600 font-mono text-sm`} {...props}>
                                {children}
                              </code>
                            );
                          }
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        </div>

        {/* ChatGPT & Claude Style Attached Document Composer */}
        <div className="p-4 bg-white border-t border-gray-100">
          <div className="max-w-3xl mx-auto">
            <form onSubmit={handleSubmit} className="bg-gray-50 rounded-2xl border border-gray-200 p-2.5 shadow-xs focus-within:border-gray-400 focus-within:ring-1 focus-within:ring-gray-300 transition-all">
              
              {/* Document Attachment Pill (Uploading state) */}
              {isUploading && (
                <div className="flex items-center gap-2 px-2 py-1 mb-2">
                  <div className="inline-flex items-center gap-2 bg-white border border-gray-200 px-3 py-1.5 rounded-xl text-xs text-gray-600 shadow-xs">
                    <svg className="w-3.5 h-3.5 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span className="font-medium">Uploading & Indexing document...</span>
                  </div>
                </div>
              )}

              {/* Document Attachment Pill (Active state in composer - ready to send) */}
              {attachedDoc && !isUploading && (
                <div className="flex items-center gap-2 px-2 py-1 mb-2">
                  <div className="inline-flex items-center gap-2.5 bg-white border border-gray-200 px-3 py-1.5 rounded-xl text-xs text-gray-800 shadow-xs">
                    <div className="w-6 h-6 rounded-lg bg-red-50 flex items-center justify-center text-red-600 font-bold text-[10px]">
                      PDF
                    </div>
                    <span className="font-medium truncate max-w-[220px]" title={attachedDoc.filename}>
                      {attachedDoc.filename}
                    </span>
                    <span className="text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full font-medium">
                      Attached
                    </span>
                    <button
                      type="button"
                      onClick={handleRemoveAttachment}
                      className="text-gray-400 hover:text-red-500 hover:bg-gray-100 rounded-md p-1 transition-colors"
                      title="Detach document from input"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              )}

              {/* Hidden file input */}
              <input 
                type="file" 
                accept=".pdf" 
                ref={fileInputRef} 
                onChange={handleFileUpload} 
                className="hidden" 
              />
              
              {/* Input & Action controls row */}
              <div className="flex items-center gap-2 px-1">
                <button 
                  type="button" 
                  onClick={() => fileInputRef.current?.click()} 
                  disabled={isLoading || isUploading}
                  className="p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-200/60 rounded-full disabled:opacity-30 transition-colors flex-shrink-0"
                  title="Attach resume or document (PDF)"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                </button>

                <input 
                  ref={textInputRef}
                  type="text" 
                  value={input} 
                  onChange={(e) => setInput(e.target.value)} 
                  placeholder={
                    isUploading 
                      ? "Uploading document..." 
                      : attachedDoc 
                        ? `Ask anything about ${attachedDoc.filename}...` 
                        : sessionDoc
                          ? `Ask anything about ${sessionDoc.filename}...`
                          : "Message ChatNexus or attach a resume (PDF)..."
                  } 
                  className="w-full bg-transparent border-none focus:outline-none text-[15px] text-gray-900 placeholder-gray-400 py-1" 
                  disabled={isLoading || isUploading} 
                />
                
                <button 
                  type="submit" 
                  disabled={isLoading || isUploading || !input.trim()} 
                  className="p-2 bg-black text-white rounded-full hover:bg-gray-800 disabled:opacity-30 transition-colors flex-shrink-0"
                  title="Send query"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                  </svg>
                </button>
              </div>
            </form>
            <div className="text-center mt-2 text-xs text-gray-400">
              ChatNexus V2 • Grounded Document Intelligence • Zero Hallucinations
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}