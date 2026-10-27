import { useState, useRef, useEffect } from 'react';
import { apiClient, type Message, type ChatSession } from './api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

export default function App() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  
  // Title Editing State
  const [editingSessionId, setEditingSessionId] = useState<number | null>(null);
  const [editTitleText, setEditTitleText] = useState('');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { 
    fetchSessions(); 
  }, []);

  // Prevent wiping the screen while streaming is active
  useEffect(() => {
    if (activeSessionId && !isLoading) {
      fetchMessages(activeSessionId);
    } else if (!activeSessionId) {
      setMessages([]);
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

  const handleNewChat = async () => {
    try {
      const res = await apiClient.post('/sessions/?title=New Chat');
      setSessions([res.data, ...sessions]);
      setActiveSessionId(res.data.id);
      setMessages([]);
      if (window.innerWidth < 768) setIsSidebarOpen(false);
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
        if (remainingSessions.length > 0) setActiveSessionId(remainingSessions[0].id);
        else { setActiveSessionId(null); setMessages([]); }
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userText = input.trim();
    setInput('');
    let currentSessionId = activeSessionId;

    try {
      if (!currentSessionId) {
        const sessionRes = await apiClient.post('/sessions/?title=New Chat');
        currentSessionId = sessionRes.data.id;
        setActiveSessionId(currentSessionId);
        setSessions(prev => [sessionRes.data, ...prev]);
      }

      const tempUserMsg: Message = { role: 'user', content: userText };
      setMessages((prev) => [...prev, tempUserMsg]);
      setIsLoading(true);
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      const res = await fetch(`http://localhost:8000/sessions/${currentSessionId}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content: userText })
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
        const parts = buffer.split('\n\n');
        
        buffer = parts.pop() || '';

        for (const part of parts) {
          if (part.startsWith('data: ')) {
            const dataStr = part.replace('data: ', '');
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
    } catch (error) {
      console.error('Streaming Error:', error);
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Error: Unable to stream response.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-white font-sans text-gray-900">
      {isSidebarOpen && <div className="fixed inset-0 bg-black/20 z-10 md:hidden" onClick={() => setIsSidebarOpen(false)} />}

      <aside className={`fixed md:static inset-y-0 left-0 z-20 w-64 bg-gray-50 border-r border-gray-200 flex flex-col transform transition-transform duration-200 ease-in-out ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <div className="p-4 flex items-center justify-between">
          <span className="font-semibold text-gray-700">ChatNexus</span>
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden text-gray-500">✕</button>
        </div>
        
        <div className="px-3 pb-4">
          <button onClick={handleNewChat} className="w-full flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 shadow-sm rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 space-y-1">
          {sessions.map(session => (
            <div key={session.id} className={`group flex items-center justify-between w-full px-3 py-2 rounded-md text-sm transition-colors ${activeSessionId === session.id ? 'bg-gray-200 text-gray-900 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}>
              
              {editingSessionId === session.id ? (
                <input
                  autoFocus
                  value={editTitleText}
                  onChange={(e) => setEditTitleText(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') submitRename(session.id); else if (e.key === 'Escape') setEditingSessionId(null); }}
                  onBlur={() => submitRename(session.id)}
                  className="w-full bg-white border border-gray-300 rounded px-1 py-0.5 outline-none text-gray-900"
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
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                </button>
              )}
            </div>
          ))}
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-w-0 relative">
        <header className="md:hidden flex items-center justify-between p-4 border-b border-gray-200">
          <button onClick={() => setIsSidebarOpen(true)} className="text-gray-500"><svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg></button>
          <span className="font-medium text-gray-700">ChatNexus</span>
          <div className="w-6" />
        </header>

        <div className="flex-1 overflow-y-auto p-4 scroll-smooth">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.length === 0 && !isLoading ? (
              <div className="h-[50vh] flex flex-col items-center justify-center text-gray-400 space-y-4">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                </div>
                <p>How can I help you today?</p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={msg.id || idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[90%] sm:max-w-[85%] px-5 py-3.5 rounded-2xl ${msg.role === 'user' ? 'bg-gray-100 text-gray-900 rounded-br-sm' : 'bg-transparent text-gray-800'}`}>
                    {msg.role === 'user' ? (
                      <p className="whitespace-pre-wrap leading-relaxed text-[15px]">{msg.content}</p>
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
              ))
            )}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        </div>

        <div className="p-4 bg-white border-t border-gray-100">
          <div className="max-w-3xl mx-auto">
            <form onSubmit={handleSubmit} className="flex items-center gap-2 bg-gray-50 rounded-full border border-gray-200 px-4 py-2 shadow-sm focus-within:border-gray-400 transition-all">
              <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Message ChatNexus..." className="w-full bg-transparent border-none focus:outline-none text-[15px] text-gray-900 placeholder-gray-400 py-1" disabled={isLoading} />
              <button type="submit" disabled={isLoading || !input.trim()} className="p-2 bg-black text-white rounded-full hover:bg-gray-800 disabled:opacity-30 transition-colors flex-shrink-0">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>
              </button>
            </form>
            <div className="text-center mt-2 text-xs text-gray-400">ChatNexus V2. AI can make mistakes. Check important info.</div>
          </div>
        </div>
      </main>
    </div>
  );
}