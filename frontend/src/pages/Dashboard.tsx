import React from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Code as CodeIcon,
  Build as BuildIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import { apiService } from '../services/api';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const { data: systemHealth } = useQuery(
    'system-health',
    () => apiService.getSystemHealth(),
    { refetchInterval: 30000 }
  );

  const { data: recentProjects } = useQuery(
    'recent-projects',
    () => apiService.getRecentProjects()
  );

  const { data: workflowStats } = useQuery(
    'workflow-stats',
    () => apiService.getWorkflowStats()
  );

  const quickActions = [
    {
      title: 'New Project',
      description: 'Start a new PLC code generation project',
      icon: <CodeIcon />,
      action: () => navigate('/projects'),
      color: 'primary',
    },
    {
      title: 'Code Editor',
      description: 'Open the Monaco code editor',
      icon: <BuildIcon />,
      action: () => navigate('/editor'),
      color: 'secondary',
    },
    {
      title: 'System Monitor',
      description: 'View system health and metrics',
      icon: <SpeedIcon />,
      action: () => navigate('/monitor'),
      color: 'info',
    },
  ];

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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckIcon color="success" />;
      case 'running':
        return <PlayIcon color="info" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <WarningIcon color="warning" />;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      {/* Quick Actions */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {quickActions.map((action, index) => (
          <Grid item xs={12} md={4} key={index}>
            <Card
              sx={{
                cursor: 'pointer',
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'translateY(-2px)',
                },
              }}
              onClick={action.action}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Box sx={{ mr: 2, color: `${action.color}.main` }}>
                    {action.icon}
                  </Box>
                  <Typography variant="h6">{action.title}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {action.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* System Health */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Health
              </Typography>
              {systemHealth ? (
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Overall Status</Typography>
                    <Chip
                      label={systemHealth.status}
                      color={systemHealth.status === 'healthy' ? 'success' : 'error'}
                      size="small"
                    />
                  </Box>
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" gutterBottom>
                      CPU Usage: {systemHealth.metrics?.cpu_usage || 0}%
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={systemHealth.metrics?.cpu_usage || 0}
                      sx={{ mb: 1 }}
                    />
                    <Typography variant="body2" gutterBottom>
                      Memory Usage: {systemHealth.metrics?.memory_usage || 0}%
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={systemHealth.metrics?.memory_usage || 0}
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Active Agents: {systemHealth.active_agents || 0}
                  </Typography>
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Loading system health...
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Projects */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Projects
              </Typography>
              {recentProjects && recentProjects.length > 0 ? (
                <List dense>
                  {recentProjects.slice(0, 5).map((project: any, index: number) => (
                    <React.Fragment key={project.id}>
                      <ListItem>
                        <ListItemIcon>
                          {getStatusIcon(project.status)}
                        </ListItemIcon>
                        <ListItemText
                          primary={project.name}
                          secondary={`Updated: ${new Date(project.updated_at).toLocaleDateString()}`}
                        />
                        <Chip
                          label={project.status}
                          color={getStatusColor(project.status) as any}
                          size="small"
                        />
                      </ListItem>
                      {index < recentProjects.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No recent projects
                </Typography>
              )}
              <Button
                variant="outlined"
                size="small"
                sx={{ mt: 2 }}
                onClick={() => navigate('/projects')}
              >
                View All Projects
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Workflow Statistics */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Workflow Statistics
              </Typography>
              {workflowStats ? (
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="primary">
                        {workflowStats.total_workflows || 0}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Workflows
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="success.main">
                        {workflowStats.successful_workflows || 0}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Successful
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="info.main">
                        {workflowStats.running_workflows || 0}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Running
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="error.main">
                        {workflowStats.failed_workflows || 0}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Failed
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Loading workflow statistics...
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
