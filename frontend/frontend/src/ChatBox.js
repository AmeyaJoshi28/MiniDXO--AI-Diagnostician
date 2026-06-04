import React, { useState, useEffect, useRef } from 'react';

function ChatBox({ onResponse }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Hello. I am MiniDXO. Please describe your health concerns or symptoms below.' }
  ]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const currentInput = input;
    setMessages(prev => [...prev, { role: 'user', text: currentInput }]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: currentInput }),
      });
      
      const data = await response.json();
      onResponse(data); // Sends data back to App.js sidebar

      setMessages(prev => [...prev, { role: 'assistant', text: data.reply }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', text: "<strong>Error:</strong> Could not connect to the diagnostic server." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-section">
      <div className="messages-container">
        {messages.map((m, i) => (
          <div key={i} className={`message-bubble ${m.role}`}>
            {m.role === 'assistant' ? (
              <div dangerouslySetInnerHTML={{ __html: m.text }} />
            ) : (
              m.text
            )}
          </div>
        ))}
        {loading && <div className="message-bubble assistant pulse">Analyzing symptoms...</div>}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <input 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}   
          placeholder="Describe how you are feeling..."
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading || !input.trim()}>
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}

export default ChatBox;
