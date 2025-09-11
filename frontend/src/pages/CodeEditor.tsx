import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  PlayArrow as RunIcon,
  Save as SaveIcon,
  Download as DownloadIcon,
  Upload as UploadIcon,
  Settings as SettingsIcon,
  BugReport as DebugIcon,
  Visibility as PreviewIcon,
} from '@mui/icons-material';
import Editor from '@monaco-editor/react';
import { useQuery, useMutation } from 'react-query';
import { apiService } from '../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 0 }}>{children}</Box>}
    </div>
  );
}

const CodeEditor: React.FC = () => {
  const [requirements, setRequirements] = useState('');
  const [plcLanguage, setPlcLanguage] = useState('ST');
  const [generatedCode, setGeneratedCode] = useState('');
  const [validationResults, setValidationResults] = useState<any>(null);
  const [simulationResults, setSimulationResults] = useState<any>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [projectName, setProjectName] = useState('Untitled Project');

  const editorRef = useRef<any>(null);

  const generateCodeMutation = useMutation(
    (data: { requirements: string; language: string }) =>
      apiService.generateCode(data),
    {
      onSuccess: (data) => {
        setGeneratedCode(data.code);
        setIsGenerating(false);
      },
      onError: () => {
        setIsGenerating(false);
      },
    }
  );

  const validateCodeMutation = useMutation(
    (code: string) => apiService.validateCode(code),
    {
      onSuccess: (data) => {
        setValidationResults(data);
        setIsValidating(false);
      },
      onError: () => {
        setIsValidating(false);
      },
    }
  );

  const simulateCodeMutation = useMutation(
    (code: string) => apiService.simulateCode(code),
    {
      onSuccess: (data) => {
        setSimulationResults(data);
        setIsSimulating(false);
      },
      onError: () => {
        setIsSimulating(false);
      },
    }
  );

  const handleGenerateCode = () => {
    if (!requirements.trim()) return;
    
    setIsGenerating(true);
    generateCodeMutation.mutate({
      requirements: requirements,
      language: plcLanguage,
    });
  };

  const handleValidateCode = () => {
    if (!generatedCode.trim()) return;
    
    setIsValidating(true);
    validateCodeMutation.mutate(generatedCode);
  };

  const handleSimulateCode = () => {
    if (!generatedCode.trim()) return;
    
    setIsSimulating(true);
    simulateCodeMutation.mutate(generatedCode);
  };

  const handleEditorDidMount = (editor: any, monaco: any) => {
    editorRef.current = editor;
    
    // Configure ST language support
    monaco.languages.register({ id: 'st' });
    monaco.languages.setMonarchTokensProvider('st', {
      tokenizer: {
        root: [
          [/\b(PROGRAM|END_PROGRAM|FUNCTION|END_FUNCTION|FUNCTION_BLOCK|END_FUNCTION_BLOCK|VAR|END_VAR|IF|THEN|ELSE|ELSIF|END_IF|WHILE|DO|END_WHILE|FOR|TO|BY|END_FOR|CASE|OF|END_CASE|REPEAT|UNTIL|END_REPEAT)\b/, 'keyword'],
          [/\b(BOOL|INT|DINT|REAL|LREAL|STRING|TIME|DATE|TOD|DT|BYTE|WORD|DWORD)\b/, 'type'],
          [/\b(TRUE|FALSE)\b/, 'constant'],
          [/\b\d+\b/, 'number'],
          [/'[^']*'/, 'string'],
          [/\/\/.*$/, 'comment'],
          [/\(\*[\s\S]*?\*\)/, 'comment'],
        ],
      },
    });
  };

  const handleSaveProject = () => {
    // Implement save functionality
    console.log('Saving project:', projectName);
  };

  const handleDownloadCode = () => {
    const element = document.createElement('a');
    const file = new Blob([generatedCode], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `${projectName}.st`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const getValidationSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h5">{projectName}</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Save Project">
              <IconButton onClick={handleSaveProject}>
                <SaveIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Download Code">
              <IconButton onClick={handleDownloadCode} disabled={!generatedCode}>
                <DownloadIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Settings">
              <IconButton onClick={() => setSettingsOpen(true)}>
                <SettingsIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
      </Box>

      <Grid container sx={{ flex: 1, height: 0 }}>
        {/* Left Panel - Requirements & Controls */}
        <Grid item xs={12} md={4} sx={{ borderRight: 1, borderColor: 'divider', display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h6" gutterBottom>
              Requirements
            </Typography>
            
            <TextField
              multiline
              rows={8}
              fullWidth
              variant="outlined"
              placeholder="Describe your PLC program requirements here..."
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              sx={{ mb: 2 }}
            />

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>PLC Language</InputLabel>
              <Select
                value={plcLanguage}
                label="PLC Language"
                onChange={(e) => setPlcLanguage(e.target.value)}
              >
                <MenuItem value="ST">Structured Text (ST)</MenuItem>
                <MenuItem value="LD">Ladder Diagram (LD)</MenuItem>
                <MenuItem value="FBD">Function Block Diagram (FBD)</MenuItem>
                <MenuItem value="IL">Instruction List (IL)</MenuItem>
              </Select>
            </FormControl>

            <Button
              variant="contained"
              startIcon={isGenerating ? <CircularProgress size={20} /> : <RunIcon />}
              onClick={handleGenerateCode}
              disabled={!requirements.trim() || isGenerating}
              fullWidth
              sx={{ mb: 2 }}
            >
              {isGenerating ? 'Generating...' : 'Generate Code'}
            </Button>

            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Button
                variant="outlined"
                startIcon={isValidating ? <CircularProgress size={16} /> : <DebugIcon />}
                onClick={handleValidateCode}
                disabled={!generatedCode || isValidating}
                size="small"
                fullWidth
              >
                Validate
              </Button>
              <Button
                variant="outlined"
                startIcon={isSimulating ? <CircularProgress size={16} /> : <PreviewIcon />}
                onClick={handleSimulateCode}
                disabled={!generatedCode || isSimulating}
                size="small"
                fullWidth
              >
                Simulate
              </Button>
            </Box>

            {/* Validation Results */}
            {validationResults && (
              <Card sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    Validation Results
                  </Typography>
                  {validationResults.issues && validationResults.issues.length > 0 ? (
                    validationResults.issues.map((issue: any, index: number) => (
                      <Alert
                        key={index}
                        severity={getValidationSeverityColor(issue.severity) as any}
                        sx={{ mb: 1 }}
                      >
                        <Typography variant="body2">
                          Line {issue.line}: {issue.message}
                        </Typography>
                      </Alert>
                    ))
                  ) : (
                    <Alert severity="success">
                      Code validation passed successfully!
                    </Alert>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Simulation Results */}
            {simulationResults && (
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    Simulation Results
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    <Chip
                      label={`Status: ${simulationResults.status}`}
                      color={simulationResults.status === 'passed' ? 'success' : 'error'}
                      size="small"
                    />
                    <Chip
                      label={`Cycle Time: ${simulationResults.cycle_time_ms}ms`}
                      size="small"
                    />
                    <Chip
                      label={`Tests: ${simulationResults.tests_passed}/${simulationResults.total_tests}`}
                      size="small"
                    />
                  </Box>
                </CardContent>
              </Card>
            )}
          </Box>
        </Grid>

        {/* Right Panel - Code Editor & Results */}
        <Grid item xs={12} md={8} sx={{ display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
              <Tab label="Generated Code" />
              <Tab label="Simulation Output" />
              <Tab label="Debug Info" />
            </Tabs>
          </Box>

          <Box sx={{ flex: 1 }}>
            <TabPanel value={activeTab} index={0}>
              <Editor
                height="100%"
                language="st"
                value={generatedCode}
                onChange={(value) => setGeneratedCode(value || '')}
                onMount={handleEditorDidMount}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  roundedSelection: false,
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  wordWrap: 'on',
                }}
              />
            </TabPanel>

            <TabPanel value={activeTab} index={1}>
              <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
                {simulationResults ? (
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      Simulation Output
                    </Typography>
                    <pre style={{ 
                      backgroundColor: '#1e1e1e', 
                      color: '#d4d4d4', 
                      padding: '16px', 
                      borderRadius: '4px',
                      overflow: 'auto',
                      fontSize: '12px',
                      fontFamily: 'monospace'
                    }}>
                      {simulationResults.output || 'No simulation output available'}
                    </pre>
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Run simulation to see output
                  </Typography>
                )}
              </Box>
            </TabPanel>

            <TabPanel value={activeTab} index={2}>
              <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
                <Typography variant="h6" gutterBottom>
                  Debug Information
                </Typography>
                {validationResults || simulationResults ? (
                  <Box>
                    {validationResults && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Validation Debug Info
                        </Typography>
                        <pre style={{ 
                          backgroundColor: '#1e1e1e', 
                          color: '#d4d4d4', 
                          padding: '16px', 
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontFamily: 'monospace'
                        }}>
                          {JSON.stringify(validationResults, null, 2)}
                        </pre>
                      </Box>
                    )}
                    {simulationResults && (
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Simulation Debug Info
                        </Typography>
                        <pre style={{ 
                          backgroundColor: '#1e1e1e', 
                          color: '#d4d4d4', 
                          padding: '16px', 
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontFamily: 'monospace'
                        }}>
                          {JSON.stringify(simulationResults, null, 2)}
                        </pre>
                      </Box>
                    )}
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No debug information available
                  </Typography>
                )}
              </Box>
            </TabPanel>
          </Box>
        </Grid>
      </Grid>

      {/* Settings Dialog */}
      <Dialog open={settingsOpen} onClose={() => setSettingsOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Project Settings</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Project Name"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsOpen(false)}>Cancel</Button>
          <Button onClick={() => setSettingsOpen(false)} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CodeEditor;
