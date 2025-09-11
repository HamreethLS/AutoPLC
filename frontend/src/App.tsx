import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box } from '@mui/material';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import CodeEditor from './pages/CodeEditor';
import ProjectManager from './pages/ProjectManager';
import SystemMonitor from './pages/SystemMonitor';

function App() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Navbar />
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/editor" element={<CodeEditor />} />
          <Route path="/projects" element={<ProjectManager />} />
          <Route path="/monitor" element={<SystemMonitor />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;
