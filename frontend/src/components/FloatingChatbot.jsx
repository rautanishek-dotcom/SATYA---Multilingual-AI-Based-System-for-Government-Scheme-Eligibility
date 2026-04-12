import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const FloatingChatbot = () => {
  const { t, i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { text: t('ChatWelcome'), isBot: true }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [welcomeMessage, setWelcomeMessage] = useState(t('ChatWelcome'));
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Fetch localized initial suggestions and greeting
    const fetchLocalization = async () => {
      try {
        const langCode = i18n.language || 'en';
        const response = await fetch(`http://localhost:5000/api/chatbot/suggestions?lang=${langCode}`);
        const data = await response.json();
        if (data.suggestions) setSuggestions(data.suggestions);
        if (data.welcome_message) setWelcomeMessage(data.welcome_message);
      } catch (err) {
        console.error('Localization fetch error:', err);
      }
    };
    fetchLocalization();
  }, [i18n.language, t]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Language sync: Fetch new suggestions and update greeting when language changes
  useEffect(() => {
    const fetchSuggestions = async () => {
      try {
        const langCode = i18n.language || 'en';
        const res = await fetch(`http://localhost:5000/api/chatbot/suggestions?lang=${langCode}`);
        const data = await res.json();
        if (data.suggestions) {
          setSuggestions(data.suggestions);
        }
      } catch (error) {
        console.error("Failed to fetch suggestions:", error);
      }
    };

    fetchSuggestions();

    // If chat is fresh (only greeting), update the greeting to current language
    setMessages(prev => {
      if (prev.length === 1 && prev[0].isBot) {
        return [{ text: t('ChatWelcome'), isBot: true }];
      }
      return prev;
    });
  }, [i18n.language, t]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (customQuery) => {
    const userMsg = (customQuery || input).trim();
    if (!userMsg) return;
    
    setMessages(prev => [...prev, { text: userMsg, isBot: false }]);
    setInput('');
    setIsLoading(true);
    setSuggestions([]);

    try {
      const langCode = i18n.language || 'en';
      const response = await fetch('http://localhost:5000/api/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: userMsg,
          lang: langCode
        })
      });
      const data = await response.json();
      
      setMessages(prev => [...prev, { text: data.response, isBot: true }]);
      
      // Update suggestions if returned
      if (data.suggestions && data.suggestions.length > 0) {
        setSuggestions(data.suggestions);
      }
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { text: t('ChatError', "I am currently having some technical difficulties. Please try again or select from the options below."), isBot: true }]);
      // Keep existing suggestions or show common ones if empty
      if (!suggestions || suggestions.length === 0) {
          setSuggestions([
            "Main Menu",
            "List All Schemes",
            "What is SATYA?",
            "How to check my eligibility?",
            "What is Ayushman Bharat?"
          ]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  const handleSuggestionClick = (question) => {
    handleSend(question);
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
                <circle cx="450" cy="300" r="92.5" fill="none" stroke="#000080" strokeWidth="6.5"/>
              </svg>
              <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--text-light)' }}>{t('ChatAssistant', 'SATYA Assistant')}</h3>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button style={styles.closeBtn} onClick={() => setIsOpen(false)}>
                <X size={20} color="var(--text-muted)" />
              </button>
            </div>
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
                {msg.text.split('\n').map((line, i) => (
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

            {/* Suggestion Chips */}
            {suggestions.length > 0 && !isLoading && (
              <div style={styles.suggestionsContainer}>
                <span style={styles.suggestionsLabel}>💡 Suggested Questions:</span>
                <div style={styles.suggestionsGrid}>
                  {suggestions.map((q, idx) => (
                    <button
                      key={idx}
                      style={styles.suggestionChip}
                      onClick={() => handleSuggestionClick(q)}
                      onMouseEnter={(e) => {
                        e.target.style.background = 'rgba(79, 70, 229, 0.25)';
                        e.target.style.borderColor = 'var(--primary-color)';
                        e.target.style.color = '#fff';
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.background = 'rgba(79, 70, 229, 0.08)';
                        e.target.style.borderColor = 'rgba(79, 70, 229, 0.3)';
                        e.target.style.color = 'var(--text-muted)';
                      }}
                    >
                      {q}
                    </button>
                  ))}
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
              placeholder={t('ChatPlaceholder', 'Ask about schemes...')} 
              style={styles.input}
            />
            <button onClick={() => handleSend()} className="btn-primary" style={styles.sendBtn} disabled={isLoading}>
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
    width: '380px',
    height: '550px',
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
  langSelect: {
    padding: '4px 8px',
    borderRadius: '4px',
    background: 'rgba(255, 255, 255, 0.1)',
    border: '1px solid var(--border-color)',
    color: 'var(--text-light)',
    fontSize: '0.75rem',
    outline: 'none',
    cursor: 'pointer',
  },
  closeBtn: {
    background: 'transparent',
    padding: '5px',
  },
  messageArea: {
    flex: 1,
    padding: '15px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  messageBubble: {
    padding: '12px 16px',
    borderRadius: '15px',
    maxWidth: '85%',
    fontSize: '0.9rem',
    lineHeight: 1.5,
    wordBreak: 'break-word',
  },
  inputArea: {
    padding: '12px 15px',
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
    fontSize: '0.9rem',
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
  },
  suggestionsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    padding: '5px 0',
  },
  suggestionsLabel: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    fontWeight: 600,
    letterSpacing: '0.03em',
  },
  suggestionsGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
  },
  suggestionChip: {
    padding: '6px 12px',
    borderRadius: '20px',
    border: '1px solid rgba(79, 70, 229, 0.3)',
    background: 'rgba(79, 70, 229, 0.08)',
    color: 'var(--text-muted)',
    fontSize: '0.75rem',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    textAlign: 'left',
    lineHeight: 1.3,
  },
};

export default FloatingChatbot;
