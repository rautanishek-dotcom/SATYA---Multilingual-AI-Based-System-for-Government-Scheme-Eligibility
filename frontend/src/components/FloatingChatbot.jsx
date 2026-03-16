import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Minimize2 } from 'lucide-react';

const FloatingChatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { text: "Hello! I am SATYA, your Govt Schemes Assistant. How can I help you today?", isBot: true }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    
    const userMsg = input.trim();
    setMessages(prev => [...prev, { text: userMsg, isBot: false }]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:5000/api/chatbot/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMsg })
      });
      const data = await response.json();
      
      setMessages(prev => [...prev, { text: data.response, isBot: true }]);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { text: "Sorry, I am having trouble connecting to the server.", isBot: true }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div style={styles.wrapper}>
      {/* Chat Button */}
      {!isOpen && (
        <button className="btn-primary" style={styles.chatBtn} onClick={() => setIsOpen(true)}>
          <MessageSquare size={24} color="white" />
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="glass-card animate-fade-in" style={styles.chatWindow}>
          <div style={styles.header}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="14" viewBox="0 0 900 600" style={{ borderRadius: '1px' }}>
                <rect width="900" height="200" fill="#FF9933"/>
                <rect y="200" width="900" height="200" fill="#FFFFFF"/>
                <rect y="400" width="900" height="200" fill="#138808"/>
                <circle cx="450" cy="300" r="92.5" fill="none" stroke="#000080" stroke-width="6.5"/>
              </svg>
              <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--text-light)' }}>SATYA Assistant</h3>
            </div>
            <button style={styles.closeBtn} onClick={() => setIsOpen(false)}>
              <X size={20} color="var(--text-muted)" />
            </button>
          </div>

          <div style={styles.messageArea}>
            {messages.map((msg, idx) => (
              <div key={idx} style={{ 
                ...styles.messageBubble, 
                backgroundColor: msg.isBot ? 'var(--surface-hover)' : 'var(--primary-color)',
                alignSelf: msg.isBot ? 'flex-start' : 'flex-end',
                borderBottomLeftRadius: msg.isBot ? '0' : '15px',
                borderBottomRightRadius: msg.isBot ? '15px' : '0',
                color: msg.isBot ? 'var(--text-light)' : 'white',
                border: msg.isBot ? '1px solid var(--border-color)' : 'none'
              }}>
                {msg.text.split('\\n').map((line, i) => (
                  <span key={i} style={{ display: 'block' }}>{line}</span>
                ))}
              </div>
            ))}
            {isLoading && (
              <div style={{ ...styles.messageBubble, backgroundColor: 'rgba(255, 255, 255, 0.05)', alignSelf: 'flex-start', borderBottomLeftRadius: 0, border: '1px solid var(--border-color)' }}>
                 <div style={styles.typingIndicator}>
                   <span>.</span><span>.</span><span>.</span>
                 </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div style={styles.inputArea}>
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about schemes..." 
              style={styles.input}
            />
            <button onClick={handleSend} className="btn-primary" style={styles.sendBtn} disabled={isLoading}>
              <Send size={18} color="white" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const styles = {
  wrapper: {
    position: 'fixed',
    bottom: '30px',
    right: '30px',
    zIndex: 9999,
  },
  chatBtn: {
    width: '60px',
    height: '60px',
    borderRadius: '50%',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    boxShadow: '0 10px 25px rgba(79, 70, 229, 0.5)',
  },
  chatWindow: {
    width: '350px',
    height: '500px',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)',
  },
  header: {
    padding: '15px 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid var(--border-color)',
    background: 'var(--surface-dark)',
  },
  closeBtn: {
    background: 'transparent',
    padding: '5px',
  },
  messageArea: {
    flex: 1,
    padding: '20px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '15px',
  },
  messageBubble: {
    padding: '12px 16px',
    borderRadius: '15px',
    maxWidth: '85%',
    fontSize: '0.95rem',
    lineHeight: 1.4,
    wordBreak: 'break-word',
  },
  inputArea: {
    padding: '15px',
    borderTop: '1px solid var(--border-color)',
    display: 'flex',
    gap: '10px',
    background: 'var(--surface-dark)',
  },
  input: {
    flex: 1,
    padding: '10px 15px',
    borderRadius: '100px',
    border: '1px solid var(--border-color)',
    background: 'rgba(0, 0, 0, 0.2)',
    color: 'var(--text-light)',
    outline: 'none',
  },
  sendBtn: {
    width: '42px',
    height: '42px',
    borderRadius: '50%',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 0,
  },
  typingIndicator: {
    display: 'flex',
    gap: '3px',
    fontWeight: 'bold',
  }
};

// Simple global keyframes for typing animation could be added here

export default FloatingChatbot;
