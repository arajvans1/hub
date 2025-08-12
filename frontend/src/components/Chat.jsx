import React, { useState, useRef, useEffect } from 'react';
import { Box, TextField, IconButton, Typography, Paper } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import Message from './Message';
import TypingIndicator from './TypingIndicator';

const USER_AVATAR = 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f464.svg';
const ASSISTANT_AVATAR = 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f4bb.svg';

const Chat = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! How can I help you today?', avatar: ASSISTANT_AVATAR, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = { role: 'user', content: input, avatar: USER_AVATAR, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply, avatar: ASSISTANT_AVATAR, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Unable to get response.', avatar: ASSISTANT_AVATAR, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }]);
    }
    setIsTyping(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Box sx={{
      width: '100vw',
      height: '100vh',
      minHeight: '100vh',
      bgcolor: '#ececf1',
      fontFamily: 'Inter, Roboto, Arial, sans-serif',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <Box sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: 56,
        bgcolor: '#fff',
        borderBottom: '1px solid #e0e3e7',
        display: 'flex',
        alignItems: 'center',
        px: 3,
        zIndex: 10,
      }}>
        <Typography variant="h6" fontWeight={700} color="primary.main" fontSize={18}>
          SAP S/4HANA Assistant
        </Typography>
      </Box>

      {/* Chat area */}
      <Box sx={{
        flex: 1,
        mt: '56px',
        mb: '72px',
        px: { xs: 1, sm: 0 },
        py: 2,
        overflowY: 'auto',
        bgcolor: '#ececf1',
        display: 'flex',
        flexDirection: 'column',
        gap: 0.5,
      }}>
        {messages.map((msg, idx) => (
          <Message
            key={idx}
            role={msg.role}
            content={msg.content}
            avatar={msg.avatar}
            time={msg.time}
          />
        ))}
        {isTyping && <TypingIndicator avatar={ASSISTANT_AVATAR} />}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input bar fixed at bottom */}
      <Box sx={{
        position: 'fixed',
        left: 0,
        bottom: 0,
        width: '100vw',
        height: 72,
        bgcolor: '#fff',
        borderTop: '1px solid #e0e3e7',
        display: 'flex',
        alignItems: 'center',
        px: 3,
        zIndex: 10,
      }}>
        <TextField
          fullWidth
          multiline
          minRows={1}
          maxRows={3}
          variant="outlined"
          placeholder="Type your message..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          sx={{
            bgcolor: '#f5f7fa',
            borderRadius: 2,
            fontSize: 15,
            py: 0.5,
          }}
        />
        <IconButton color="primary" onClick={sendMessage} sx={{ ml: 1, bgcolor: '#e3eafc', borderRadius: 2, p: 0.5 }}>
          <SendIcon fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  );
};

export default Chat;
