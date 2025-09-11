import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import Editor from '@monaco-editor/react';

interface CodeViewerProps {
  code: string;
  language?: string;
  title?: string;
  height?: string | number;
  readOnly?: boolean;
  onChange?: (value: string) => void;
}

const CodeViewer: React.FC<CodeViewerProps> = ({
  code,
  language = 'st',
  title,
  height = 400,
  readOnly = true,
  onChange,
}) => {
  return (
    <Paper sx={{ overflow: 'hidden' }}>
      {title && (
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6">{title}</Typography>
        </Box>
      )}
      <Editor
        height={height}
        language={language}
        value={code}
        onChange={(value) => onChange && onChange(value || '')}
        theme="vs-dark"
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          roundedSelection: false,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          wordWrap: 'on',
          folding: true,
          lineDecorationsWidth: 10,
          lineNumbersMinChars: 3,
        }}
      />
    </Paper>
  );
};

export default CodeViewer;
