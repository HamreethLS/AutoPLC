import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  CheckCircle as CheckIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { apiService } from '../services/api';
import { format } from 'date-fns';

const SystemMonitor: React.FC = () => {
  const [timeRange, setTimeRange] = useState('1h');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data: systemHealth, refetch: refetchHealth } = useQuery(
    'system-health',
    () => apiService.getSystemHealth(),
    {
      refetchInterval: autoRefresh ? 5000 : false,
    }
  );

  const { data: telemetryData, refetch: refetchTelemetry } = useQuery(
    ['telemetry', timeRange],
    () => apiService.getTelemetryData(timeRange),
    {
      refetchInterval: autoRefresh ? 10000 : false,
    }
  );

  const { data: alerts } = useQuery(
    'alerts',
    () => apiService.getAlerts(),
    {
      refetchInterval: autoRefresh ? 15000 : false,
    }
  );

  const { data: agents } = useQuery(
    'agents',
    () => apiService.getAgents(),
    {
      refetchInterval: autoRefresh ? 30000 : false,
    }
  );

  const handleRefresh = () => {
    refetchHealth();
    refetchTelemetry();
  };

  const getAlertSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'default';
    }
  };

  const getAgentStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'stopped':
        return 'error';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const getAgentStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <CheckIcon color="success" />;
      case 'stopped':
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <WarningIcon color="warning" />;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">System Monitor</Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              label="Time Range"
              onChange={(e) => setTimeRange(e.target.value)}
            >
              <MenuItem value="15m">15 minutes</MenuItem>
              <MenuItem value="1h">1 hour</MenuItem>
              <MenuItem value="6h">6 hours</MenuItem>
              <MenuItem value="24h">24 hours</MenuItem>
              <MenuItem value="7d">7 days</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            onClick={() => setAutoRefresh(!autoRefresh)}
            color={autoRefresh ? 'primary' : 'inherit'}
          >
            Auto Refresh: {autoRefresh ? 'ON' : 'OFF'}
          </Button>
          <Tooltip title="Refresh Now">
            <IconButton onClick={handleRefresh}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* System Health Overview */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Health
              </Typography>
              {systemHealth ? (
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="body2">Overall Status</Typography>
                    <Chip
                      label={systemHealth.status}
                      color={systemHealth.status === 'healthy' ? 'success' : 'error'}
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
                      sx={{ mb: 1 }}
                    />
                    
                    <Typography variant="body2" gutterBottom>
                      Disk Usage: {systemHealth.metrics?.disk_usage || 0}%
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={systemHealth.metrics?.disk_usage || 0}
                    />
                  </Box>

                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Active Agents
                      </Typography>
                      <Typography variant="h6">
                        {systemHealth.active_agents || 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Active Workflows
                      </Typography>
                      <Typography variant="h6">
                        {systemHealth.active_workflows || 0}
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Loading system health...
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Active Alerts */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Active Alerts
              </Typography>
              {alerts && alerts.length > 0 ? (
                <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                  {alerts.slice(0, 10).map((alert: any, index: number) => (
                    <Alert
                      key={index}
                      severity={getAlertSeverityColor(alert.severity) as any}
                      sx={{ mb: 1 }}
                    >
                      <Typography variant="body2" fontWeight="bold">
                        {alert.title}
                      </Typography>
                      <Typography variant="caption" display="block">
                        {alert.message}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {format(new Date(alert.timestamp), 'MMM dd, HH:mm:ss')}
                      </Typography>
                    </Alert>
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No active alerts
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Metrics Chart */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Performance Metrics
              </Typography>
              {telemetryData && telemetryData.length > 0 ? (
                <Box sx={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={telemetryData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="timestamp" 
                        tickFormatter={(value) => format(new Date(value), 'HH:mm')}
                      />
                      <YAxis />
                      <RechartsTooltip 
                        labelFormatter={(value) => format(new Date(value), 'MMM dd, HH:mm:ss')}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="cpu_usage" 
                        stackId="1"
                        stroke="#8884d8" 
                        fill="#8884d8" 
                        name="CPU Usage (%)"
                      />
                      <Area 
                        type="monotone" 
                        dataKey="memory_usage" 
                        stackId="1"
                        stroke="#82ca9d" 
                        fill="#82ca9d" 
                        name="Memory Usage (%)"
                      />
                      <Area 
                        type="monotone" 
                        dataKey="cycle_time_ms" 
                        stackId="2"
                        stroke="#ffc658" 
                        fill="#ffc658" 
                        name="Cycle Time (ms)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
              ) : (
                <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    No telemetry data available
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Agent Status */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Agent Status
              </Typography>
              {agents && agents.length > 0 ? (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Agent</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Last Heartbeat</TableCell>
                        <TableCell>Tasks Processed</TableCell>
                        <TableCell>Success Rate</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {agents.map((agent: any) => (
                        <TableRow key={agent.id}>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              {getAgentStatusIcon(agent.status)}
                              <Box sx={{ ml: 1 }}>
                                <Typography variant="subtitle2">
                                  {agent.name}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {agent.role}
                                </Typography>
                              </Box>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={agent.status}
                              color={getAgentStatusColor(agent.status) as any}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {agent.last_heartbeat 
                                ? format(new Date(agent.last_heartbeat), 'MMM dd, HH:mm:ss')
                                : 'Never'
                              }
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {agent.tasks_processed || 0}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {agent.success_rate ? `${(agent.success_rate * 100).toFixed(1)}%` : 'N/A'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => {/* Implement restart agent */}}
                              disabled={agent.status === 'running'}
                            >
                              Restart
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No agent data available
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SystemMonitor;
