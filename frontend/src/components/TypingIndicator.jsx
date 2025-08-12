import React from 'react';
import { Box, Avatar, CircularProgress, Typography } from '@mui/material';

const TypingIndicator = ({ avatar }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', px: 2, mb: 1 }}>
    <Avatar src={avatar} sx={{ bgcolor: '#ececf1', mr: 2 }} />
    <CircularProgress size={18} sx={{ color: '#10a37f', mr: 1 }} />
    <Typography variant="body2" color="#10a37f">Thinking...</Typography>
  </Box>
);

export default TypingIndicator;
