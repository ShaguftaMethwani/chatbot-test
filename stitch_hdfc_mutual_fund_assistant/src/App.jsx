import { useState, useRef, useEffect } from 'react';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const chatContainerRef = useRef(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const showToast = (message) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(''), 3000);
  };

  const handleSend = async (text) => {
    const messageText = text || input.trim();
    if (!messageText) return;

    // Add user message
    const newMessages = [...messages, { role: 'user', content: messageText }];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText }),
      });

      if (!response.ok) {
        throw new Error('API request failed');
      }

      const data = await response.json();
      
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          content: data.answer,
          source: data.source,
          lastUpdated: data.last_updated,
          refused: data.refused,
        },
      ]);
    } catch (error) {
      console.error('Chat error:', error);
      showToast('Failed to connect to API.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    handleSend();
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden antialiased font-body-md bg-background text-on-background">
      {/* TopAppBar */}
      <header className="fixed top-0 w-full z-50 bg-surface/80 dark:bg-surface/80 backdrop-blur-xl border-b border-white/10 shadow-sm flex justify-between items-center px-container-padding py-md">
        <div className="flex flex-col">
          <h1 className="text-headline-md font-headline-md font-bold text-primary dark:text-primary">HDFC Mutual Fund Assistant</h1>
          <p className="text-label-sm font-label-sm text-on-surface-variant mt-1">Answers are AI-generated based on official fund documents. Not investment advice.</p>
        </div>
        <div className="hidden md:flex gap-sm">
          <button className="p-2 rounded-full hover:bg-white/5 transition-colors text-on-surface-variant hover:text-primary active:opacity-80">
            <span className="material-symbols-outlined">info</span>
          </button>
          <button className="p-2 rounded-full hover:bg-white/5 transition-colors text-on-surface-variant hover:text-primary active:opacity-80">
            <span className="material-symbols-outlined">help</span>
          </button>
        </div>
      </header>

      {/* Main Chat Area */}
      <main ref={chatContainerRef} className="flex-1 overflow-y-auto scrollbar-hide pt-[100px] pb-[140px] md:pb-[100px] px-container-padding flex flex-col gap-chat-gap max-w-4xl mx-auto w-full">
        
        {messages.length === 0 ? (
          /* Empty State Suggestions */
          <div className="flex flex-col items-center justify-center h-full mt-xl">
            <span className="material-symbols-outlined text-[64px] text-primary/20 mb-md" style={{fontVariationSettings: "'FILL' 1"}}>assured_workload</span>
            <h2 className="text-headline-xl-mobile md:text-headline-xl font-headline-xl text-center mb-lg">How can I help you <br/>invest today?</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-md w-full mt-xl">
              {[
                "What is the expense ratio for HDFC Mid Cap?",
                "What's the exit load for the Small Cap fund?",
                "Tell me about the ELSS Tax Saver fund."
              ].map((suggestion, idx) => (
                <button 
                  key={idx}
                  onClick={() => handleSend(suggestion)}
                  className="glass-panel p-md rounded-lg text-left hover:bg-white/10 transition-all hover:scale-[1.02] active:scale-95 group flex flex-col justify-between min-h-[120px]"
                >
                  <span className="text-body-md font-body-md group-hover:text-primary transition-colors">{suggestion}</span>
                  <span className="material-symbols-outlined self-end text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity">arrow_forward</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Chat Messages */
          <div className="flex flex-col gap-chat-gap mt-4">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex w-full message-enter ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'user' ? (
                  <div className="user-bubble max-w-[85%] md:max-w-[75%] rounded-2xl rounded-tr-sm px-lg py-md shadow-md text-body-md">
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                ) : (
                  <div className={`glass-modal max-w-[85%] md:max-w-[75%] rounded-2xl rounded-tl-sm px-lg py-md shadow-md text-body-md text-on-surface flex flex-col gap-2 ${msg.refused ? 'border-error/50 shadow-[0_0_15px_rgba(255,180,171,0.1)]' : ''}`}>
                    {msg.refused && (
                      <div className="flex items-center gap-2 text-error mb-1">
                        <span className="material-symbols-outlined text-[18px]">warning</span>
                        <span className="text-label-sm uppercase tracking-wider font-bold">Safety Guideline</span>
                      </div>
                    )}
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                    
                    {(msg.source || msg.lastUpdated) && (
                      <div className="mt-3 pt-3 border-t border-white/10 flex flex-wrap gap-2 items-center text-label-sm text-on-surface-variant">
                        {msg.source && (
                          <a href={msg.source} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-primary transition-colors bg-white/5 px-2 py-1 rounded">
                            <span className="material-symbols-outlined text-[14px]">link</span>
                            Source Document
                          </a>
                        )}
                        {msg.lastUpdated && (
                          <span className="flex items-center gap-1 bg-white/5 px-2 py-1 rounded">
                            <span className="material-symbols-outlined text-[14px]">update</span>
                            Updated: {msg.lastUpdated}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            
            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex w-full justify-start message-enter">
                <div className="glass-modal max-w-[85%] md:max-w-[75%] rounded-2xl rounded-tl-sm px-lg py-md shadow-md flex items-center gap-2">
                  <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <circle className="typing-dot" cx="4" cy="12" r="3" />
                    <circle className="typing-dot" cx="12" cy="12" r="3" />
                    <circle className="typing-dot" cx="20" cy="12" r="3" />
                  </svg>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Input Area */}
      <div className="fixed bottom-[80px] md:bottom-0 left-0 w-full z-40 bg-gradient-to-t from-background via-background to-transparent pb-md pt-xl px-container-padding">
        <div className="max-w-4xl mx-auto relative">
          <form onSubmit={handleSubmit} className="relative flex items-center">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              placeholder="Ask about HDFC Mutual Funds..." 
              className="w-full bg-surface-container-highest/80 backdrop-blur-md border border-white/10 rounded-full py-4 pl-6 pr-16 text-body-md focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent placeholder-on-surface-variant transition-shadow shadow-[0_0_15px_rgba(168,85,247,0.05)] focus:shadow-[0_0_20px_rgba(168,85,247,0.15)] text-on-surface disabled:opacity-50"
            />
            <button 
              type="submit" 
              disabled={isLoading || !input.trim()}
              className="absolute right-2 p-2 gradient-btn rounded-full flex items-center justify-center w-10 h-10 shadow-lg active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-white">send</span>
            </button>
          </form>
        </div>
      </div>

      {/* BottomNavBar (Mobile Only) */}
      <nav className="fixed bottom-0 left-0 w-full z-50 flex justify-around items-center h-16 bg-surface-container/90 dark:bg-surface-container/90 backdrop-blur-xl border-t border-white/5 shadow-[0_-8px_30px_rgb(0,0,0,0.12)] md:hidden rounded-t-lg">
        <a href="#" className="flex flex-col items-center justify-center text-primary font-bold active:scale-95 duration-200 w-1/3">
          <span className="material-symbols-outlined" style={{fontVariationSettings: "'FILL' 1"}}>chat_bubble</span>
          <span className="text-label-sm font-label-sm mt-1">Chat</span>
        </a>
        <a href="#" className="flex flex-col items-center justify-center text-on-surface-variant hover:text-primary/80 active:scale-95 duration-200 w-1/3">
          <span className="material-symbols-outlined">account_balance_wallet</span>
          <span className="text-label-sm font-label-sm mt-1">Portfolio</span>
        </a>
        <a href="#" className="flex flex-col items-center justify-center text-on-surface-variant hover:text-primary/80 active:scale-95 duration-200 w-1/3">
          <span className="material-symbols-outlined">trending_up</span>
          <span className="text-label-sm font-label-sm mt-1">Markets</span>
        </a>
      </nav>

      {/* Toast Notification */}
      <div className={`fixed top-24 left-1/2 transform -translate-x-1/2 bg-error-container text-on-error-container px-md py-sm rounded-full shadow-lg border border-error/20 flex items-center gap-sm transition-opacity duration-300 z-50 ${toastMessage ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}>
        <span className="material-symbols-outlined text-error">error</span>
        <span className="text-label-sm font-label-sm">{toastMessage}</span>
      </div>
    </div>
  );
}

export default App;
