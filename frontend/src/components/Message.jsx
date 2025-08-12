import React from 'react';
import { Box, Avatar, Typography, Paper } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const Message = ({ role, content, avatar, time }) => {
  const isUser = role === 'user';
  return (
    <Box sx={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems: 'flex-end',
      mb: 1.5,
      px: 2,
      width: '100%',
      maxWidth: '800px',
    }}>
      <Avatar src={avatar} sx={{ bgcolor: isUser ? '#10a37f' : '#ececf1', ml: isUser ? 2 : 0, mr: isUser ? 0 : 2 }} />
      <Paper elevation={2} sx={{
        p: 2,
        borderRadius: 3,
        bgcolor: isUser ? 'linear-gradient(135deg, #10a37f 0%, #43e7b6 100%)' : 'linear-gradient(135deg, #ececf1 0%, #f7f7f8 100%)',
        color: isUser ? '#fff' : '#222',
        maxWidth: '600px',
        wordBreak: 'break-word',
        boxShadow: isUser ? '0 2px 12px rgba(16,163,127,0.12)' : '0 2px 12px rgba(16,163,127,0.06)',
      }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        <Typography variant="caption" sx={{ opacity: 0.6, mt: 1, display: 'block', textAlign: isUser ? 'right' : 'left' }}>
          {time}
        </Typography>
      </Paper>
    </Box>
  );
};

export default Message;
