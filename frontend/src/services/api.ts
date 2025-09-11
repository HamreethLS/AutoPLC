import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const apiService = {
  // System Health
  getSystemHealth: async () => {
    return apiClient.get('/api/system/health');
  },

  // Projects
  getProjects: async () => {
    return apiClient.get('/api/projects');
  },

  getRecentProjects: async () => {
    return apiClient.get('/api/projects/recent');
  },

  getProject: async (projectId: string) => {
    return apiClient.get(`/api/projects/${projectId}`);
  },

  createProject: async (projectData: any) => {
    return apiClient.post('/api/projects', projectData);
  },

  updateProject: async (projectId: string, projectData: any) => {
    return apiClient.put(`/api/projects/${projectId}`, projectData);
  },

  deleteProject: async (projectId: string) => {
    return apiClient.delete(`/api/projects/${projectId}`);
  },

  // Code Generation
  generateCode: async (data: { requirements: string; language: string; project_id?: string }) => {
    return apiClient.post('/api/code/generate', data);
  },

  validateCode: async (code: string) => {
    return apiClient.post('/api/code/validate', { code });
  },

  simulateCode: async (code: string) => {
    return apiClient.post('/api/code/simulate', { code });
  },

  debugCode: async (code: string, errors: any[]) => {
    return apiClient.post('/api/code/debug', { code, errors });
  },

  // Workflows
  getWorkflows: async () => {
    return apiClient.get('/api/workflows');
  },

  getWorkflow: async (workflowId: string) => {
    return apiClient.get(`/api/workflows/${workflowId}`);
  },

  createWorkflow: async (workflowData: any) => {
    return apiClient.post('/api/workflows', workflowData);
  },

  getWorkflowStats: async () => {
    return apiClient.get('/api/workflows/stats');
  },

  // Monitoring
  getTelemetryData: async (timeRange?: string) => {
    const params = timeRange ? { time_range: timeRange } : {};
    return apiClient.get('/api/monitor/telemetry', { params });
  },

  getAlerts: async () => {
    return apiClient.get('/api/monitor/alerts');
  },

  getMetrics: async () => {
    return apiClient.get('/api/monitor/metrics');
  },

  // Agent Management
  getAgents: async () => {
    return apiClient.get('/api/agents');
  },

  getAgentStatus: async (agentId: string) => {
    return apiClient.get(`/api/agents/${agentId}/status`);
  },

  restartAgent: async (agentId: string) => {
    return apiClient.post(`/api/agents/${agentId}/restart`);
  },

  // Deployments
  getDeployments: async () => {
    return apiClient.get('/api/deployments');
  },

  createDeployment: async (deploymentData: any) => {
    return apiClient.post('/api/deployments', deploymentData);
  },

  getDeploymentStatus: async (deploymentId: string) => {
    return apiClient.get(`/api/deployments/${deploymentId}/status`);
  },

  rollbackDeployment: async (deploymentId: string, reason: string) => {
    return apiClient.post(`/api/deployments/${deploymentId}/rollback`, { reason });
  },

  // Knowledge Base
  searchKnowledge: async (query: string) => {
    return apiClient.get('/api/knowledge/search', { params: { query } });
  },

  getKnowledgeDocuments: async () => {
    return apiClient.get('/api/knowledge/documents');
  },

  uploadKnowledgeDocument: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/api/knowledge/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // Code Versions
  getCodeVersions: async (projectId: string) => {
    return apiClient.get(`/api/projects/${projectId}/versions`);
  },

  createCodeVersion: async (projectId: string, versionData: any) => {
    return apiClient.post(`/api/projects/${projectId}/versions`, versionData);
  },

  getCodeVersion: async (projectId: string, versionId: string) => {
    return apiClient.get(`/api/projects/${projectId}/versions/${versionId}`);
  },

  // Simulation Results
  getSimulationResults: async (projectId: string) => {
    return apiClient.get(`/api/projects/${projectId}/simulations`);
  },

  // Validation Results
  getValidationResults: async (projectId: string) => {
    return apiClient.get(`/api/projects/${projectId}/validations`);
  },

  // WebSocket connection for real-time updates
  connectWebSocket: (onMessage: (data: any) => void) => {
    const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws';
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    return ws;
  },
};

export default apiService;
