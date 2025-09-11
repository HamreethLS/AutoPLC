import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Chip,
  LinearProgress,
  Alert,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  PlayArrow as RunningIcon,
  Schedule as PendingIcon,
} from '@mui/icons-material';

interface WorkflowStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  agent_role: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  result?: any;
}

interface WorkflowViewerProps {
  workflow: {
    id: string;
    name: string;
    status: string;
    steps: WorkflowStep[];
    progress: number;
  };
}

const WorkflowViewer: React.FC<WorkflowViewerProps> = ({ workflow }) => {
  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckIcon color="success" />;
      case 'running':
        return <RunningIcon color="info" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <PendingIcon color="disabled" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'info';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const activeStep = workflow.steps.findIndex(step => step.status === 'running');

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">{workflow.name}</Typography>
          <Chip
            label={workflow.status}
            color={getStatusColor(workflow.status) as any}
          />
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" gutterBottom>
            Progress: {Math.round(workflow.progress)}%
          </Typography>
          <LinearProgress variant="determinate" value={workflow.progress} />
        </Box>

        <Stepper activeStep={activeStep} orientation="vertical">
          {workflow.steps.map((step, index) => (
            <Step key={step.id}>
              <StepLabel
                icon={getStepIcon(step.status)}
                error={step.status === 'failed'}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="subtitle2">{step.name}</Typography>
                  <Chip label={step.agent_role} size="small" variant="outlined" />
                </Box>
              </StepLabel>
              <StepContent>
                <Box sx={{ mt: 1 }}>
                  {step.status === 'failed' && step.error_message && (
                    <Alert severity="error" sx={{ mb: 1 }}>
                      {step.error_message}
                    </Alert>
                  )}
                  
                  {step.started_at && (
                    <Typography variant="caption" color="text.secondary" display="block">
                      Started: {new Date(step.started_at).toLocaleString()}
                    </Typography>
                  )}
                  
                  {step.completed_at && (
                    <Typography variant="caption" color="text.secondary" display="block">
                      Completed: {new Date(step.completed_at).toLocaleString()}
                    </Typography>
                  )}
                  
                  {step.result && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Result:
                      </Typography>
                      <pre style={{
                        fontSize: '11px',
                        backgroundColor: '#f5f5f5',
                        padding: '8px',
                        borderRadius: '4px',
                        overflow: 'auto',
                        maxHeight: '200px',
                      }}>
                        {typeof step.result === 'string' 
                          ? step.result 
                          : JSON.stringify(step.result, null, 2)
                        }
                      </pre>
                    </Box>
                  )}
                </Box>
              </StepContent>
            </Step>
          ))}
        </Stepper>
      </CardContent>
    </Card>
  );
};

export default WorkflowViewer;
